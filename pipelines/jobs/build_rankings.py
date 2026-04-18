"""Build static cross-city ranking tables as JSON.

v2 Step 5 — consumes ``data/reports/*.json`` produced by
:mod:`pipelines.jobs.build_reports` and emits one file per ranking
metric under ``data/rankings/``. Never rewrites the underlying report
files (see ``docs/reports/report-block-policy.md`` §2).

Usage
-----
::

    python -m pipelines.jobs.build_rankings
    python -m pipelines.jobs.build_rankings --reports-dir dist/data/reports --output-dir dist/data/rankings

Outputs
-------
- ``data/rankings/{metric}.json`` — :class:`Ranking` per metric.
- ``data/rankings/index.json`` — :class:`RankingsIndex` manifest.

Step 5 scope
------------
Four ranking metrics (``air_quality_pm25``, ``emissions_ghg_total``,
``water_violations_count``, ``disaster_declarations_10y``). Source
blocks are mostly in ``pending`` state at Step 5, so most ranking rows
will have ``value=null`` and ``rank=null``. The scaffolding proves the
pipeline topology and locks the contract — once the underlying
connectors migrate, the rankings populate without any schema change.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from pipelines.contracts import (
    CityReport,
    Ranking,
    RankingMetric,
    RankingRow,
    RankingsIndex,
    RankingsIndexEntry,
    ReportBlock,
    TrustTag,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORTS_DIR = REPO_ROOT / "data" / "reports"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "data" / "rankings"

PIPELINE_VERSION = "v2.step5.0"


# ---------------------------------------------------------------------------
# Metric definitions — maps each RankingMetric to (block_id, metric_label,
# unit, direction). The extractor reads the corresponding block from each
# report, looks for a metric with the given label, and collects its value.
# ``direction`` indicates which end of the ranking is "best" (asc = lower
# value is better, e.g., pollution; desc = higher is better).
# ---------------------------------------------------------------------------
_METRIC_DEFS: dict[RankingMetric, dict] = {
    "air_quality_pm25": {
        "title": "PM2.5 Annual Mean",
        "block_id": "air_quality",
        "metric_label": "PM2.5 annual mean",
        "unit": "µg/m³",
        "direction": "asc",
    },
    "emissions_ghg_total": {
        "title": "GHG Facility Emissions (Total)",
        "block_id": "industrial_emissions",
        "metric_label": "Reported GHG emissions (CO₂e)",
        "unit": "metric tons CO₂e",
        "direction": "asc",
    },
    "water_violations_count": {
        "title": "Drinking Water Violations",
        "block_id": "water",
        "metric_label": "Active SDWIS violations",
        "unit": "violations",
        "direction": "asc",
    },
    "disaster_declarations_10y": {
        "title": "Federal Disaster Declarations (10-year)",
        "block_id": "hazards_disasters",
        "metric_label": "Declarations (10-year)",
        "unit": "events",
        "direction": "asc",
    },
}


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def _iter_report_files(reports_dir: Path):
    for path in sorted(reports_dir.glob("*.json")):
        if path.name == "index.json":
            continue
        yield path


def load_reports(reports_dir: Path) -> list[CityReport]:
    reports: list[CityReport] = []
    for path in _iter_report_files(reports_dir):
        raw = json.loads(path.read_text(encoding="utf-8"))
        try:
            reports.append(CityReport.model_validate(raw))
        except Exception as exc:  # noqa: BLE001 — broad is fine at CLI layer
            print(
                f"[warn] {path.name} failed schema validation: {exc!s}",
                file=sys.stderr,
            )
    return reports


# ---------------------------------------------------------------------------
# Metric extraction
# ---------------------------------------------------------------------------

def _find_block(report: CityReport, block_id: str) -> ReportBlock | None:
    for b in report.blocks:
        if b.id == block_id:
            return b
    return None


def _extract_value(
    report: CityReport, block_id: str, metric_label: str
) -> tuple[float | None, TrustTag]:
    """Pull a numeric metric out of a report block.

    Returns ``(value_or_None, trust_tag)``. ``value`` is None when:
    - the block is absent from this report
    - the block exists but is not ``status='ok'``
    - no metric with that label is present
    - the metric value cannot be coerced to float

    ``trust_tag`` falls back to the block's block-level tag, or to
    ``derived`` if the block is missing entirely.
    """
    block = _find_block(report, block_id)
    if block is None:
        return None, "derived"
    if block.status != "ok":
        return None, block.trustTag
    for m in block.metrics:
        if m.label != metric_label:
            continue
        tag: TrustTag = m.trustTag or block.trustTag
        try:
            return float(m.value), tag  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return None, tag
    return None, block.trustTag


# ---------------------------------------------------------------------------
# Ranking builder — one metric at a time.
# ---------------------------------------------------------------------------

def build_one_ranking(
    metric: RankingMetric, reports: list[CityReport], now_iso: str
) -> Ranking:
    spec = _METRIC_DEFS[metric]
    rows: list[RankingRow] = []
    for report in reports:
        value, tag = _extract_value(
            report, spec["block_id"], spec["metric_label"]
        )
        rows.append(
            RankingRow(
                slug=report.slug,
                city=report.city,
                region=report.region,
                value=value,
                unit=spec["unit"],
                rank=None,
                trustTag=tag,
            )
        )
    # Sort and assign ranks. Nulls drop to the bottom and keep rank=None.
    ranked = [r for r in rows if r.value is not None]
    ranked.sort(
        key=lambda r: r.value,  # type: ignore[arg-type,return-value]
        reverse=spec["direction"] == "desc",
    )
    for i, r in enumerate(ranked, start=1):
        r.rank = i
    unranked = [r for r in rows if r.value is None]
    ordered = ranked + unranked

    return Ranking(
        metric=metric,
        title=spec["title"],
        direction=spec["direction"],
        unit=spec["unit"],
        generatedAt=now_iso,
        pipelineVersion=PIPELINE_VERSION,
        n=len(ordered),
        rows=ordered,
    )


# ---------------------------------------------------------------------------
# File IO
# ---------------------------------------------------------------------------

def _write_json(path: Path, model) -> None:
    payload = model.model_dump(mode="json", exclude_none=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def write_rankings(
    rankings: list[Ranking], output_dir: Path, now_iso: str
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    index_entries: list[RankingsIndexEntry] = []
    for r in rankings:
        file_name = f"{r.metric}.json"
        _write_json(output_dir / file_name, r)
        index_entries.append(
            RankingsIndexEntry(
                metric=r.metric,
                title=r.title,
                file=file_name,
                nCbsa=r.n,
                generatedAt=r.generatedAt,
            )
        )
    index = RankingsIndex(
        generatedAt=now_iso,
        pipelineVersion=PIPELINE_VERSION,
        files=index_entries,
    )
    index_path = output_dir / "index.json"
    _write_json(index_path, index)
    return index_path


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reports-dir",
        default=str(DEFAULT_REPORTS_DIR),
        help="Directory holding per-CBSA report.json files (default: data/reports).",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory to write ranking files into (default: data/rankings).",
    )
    args = parser.parse_args(argv)

    reports_dir = Path(args.reports_dir).resolve()
    output_dir = Path(args.output_dir).resolve()

    if not reports_dir.exists():
        print(
            f"[error] reports directory not found: {reports_dir}",
            file=sys.stderr,
        )
        return 2

    reports = load_reports(reports_dir)
    if not reports:
        print(
            f"[error] no valid reports in {reports_dir}", file=sys.stderr
        )
        return 2

    now_iso = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    rankings = [
        build_one_ranking(metric, reports, now_iso)
        for metric in _METRIC_DEFS.keys()
    ]

    index_path = write_rankings(rankings, output_dir, now_iso)

    populated = sum(
        1 for r in rankings for row in r.rows if row.value is not None
    )
    print(
        f"[ok] built {len(rankings)} ranking(s) from {len(reports)} report(s), "
        f"{populated} populated row(s) → {output_dir} (index: {index_path})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
