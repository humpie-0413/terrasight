"""Build static Local Environmental Reports as JSON.

v2 Step 5 — replaces the legacy runtime ``/api/reports/{slug}`` endpoint
with build-time ``data/reports/{slug}.json`` files plus a single
``data/reports/index.json`` manifest. Invoked from CI (future GitHub
Actions workflow) and locally via::

    python -m pipelines.jobs.build_reports
    python -m pipelines.jobs.build_reports --only new-york-newark-jersey-city,los-angeles-long-beach-anaheim,houston-the-woodlands-sugar-land
    python -m pipelines.jobs.build_reports --output-dir dist/data/reports

Outputs
-------
- ``data/reports/{slug}.json`` — one :class:`CityReport` per metro.
- ``data/reports/index.json`` — :class:`CityReportIndex` with per-report
  status + block counts.

Contract locks
--------------
- Block inclusion: ``docs/reports/report-block-policy.md`` §1.
- Schema shape: ``packages/schemas/src/index.ts`` + mirrored in
  ``pipelines/contracts/__init__.py``.
- City Comparison is never embedded — see ``pipelines/jobs/build_rankings.py``.

v2 Step 5 scope
---------------
Most blocks are produced in ``pending`` state because their v2
connectors have not yet been migrated. The scaffolding is what's
being shipped: schema, composer, every core block always present,
gate logic for optional blocks, and 3 verified sample outputs
(New York, Los Angeles, Houston).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from pipelines.contracts import (
    CityReport,
    CityReportBuildMeta,
    CityReportIndex,
    CityReportIndexEntry,
    CityReportIndexStatus,
    CityReportMeta,
    CityReportSummary,
)
from pipelines.transforms.block_composer import (
    ComposerInput,
    cbsa_from_mapping,
    compose_city_report_blocks,
)

# ---------------------------------------------------------------------------
# Paths + constants
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[2]
CBSA_MAPPING_PATH = REPO_ROOT / "data" / "cbsa_mapping.json"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "data" / "reports"

# Sample metros required by Step 5 acceptance (NY / LA / Houston).
STEP5_SAMPLE_SLUGS: tuple[str, ...] = (
    "new-york-newark-jersey-city",
    "los-angeles-long-beach-anaheim",
    "houston-the-woodlands-sugar-land",
)

# Bumped whenever the block set or composer contract changes. Readers
# can use this to detect stale artifacts.
PIPELINE_VERSION = "v2.step5.0"


# ---------------------------------------------------------------------------
# CBSA mapping loader
# ---------------------------------------------------------------------------

def load_cbsa_mapping(path: Path = CBSA_MAPPING_PATH) -> dict[str, dict]:
    """Return ``{cbsa_code: entry}`` from cbsa_mapping.json.

    Skips the top-level ``_comment`` field. Any entry missing the
    required keys (``slug``, ``name``, ``state``, ``lat``, ``lon``) is
    dropped with a warning — build_reports keeps going.
    """
    raw = json.loads(path.read_text(encoding="utf-8"))
    required = {"slug", "name", "state", "lat", "lon"}
    out: dict[str, dict] = {}
    for key, value in raw.items():
        if key.startswith("_") or not isinstance(value, dict):
            continue
        missing = required - value.keys()
        if missing:
            print(
                f"[warn] CBSA {key} missing required fields {missing} — skipping",
                file=sys.stderr,
            )
            continue
        out[key] = value
    return out


# ---------------------------------------------------------------------------
# Peer-slug resolution for related_cities gate.
# Same climate_zone OR same state, excluding self. Capped at 5 peers.
# ---------------------------------------------------------------------------

def _resolve_peer_slugs(
    cbsa_code: str, entry: dict, mapping: dict[str, dict], limit: int = 5
) -> list[str]:
    climate_zone = entry.get("climate_zone")
    state = entry.get("state")
    peers: list[str] = []
    for other_code, other in mapping.items():
        if other_code == cbsa_code:
            continue
        if not isinstance(other, dict) or "slug" not in other:
            continue
        if (
            climate_zone
            and other.get("climate_zone") == climate_zone
        ) or (
            state and other.get("state") == state
        ):
            peers.append(other["slug"])
            if len(peers) >= limit:
                break
    return peers


# ---------------------------------------------------------------------------
# Per-CBSA report builder
# ---------------------------------------------------------------------------

def build_one_report(
    cbsa_code: str, entry: dict, mapping: dict[str, dict], now_iso: str
) -> CityReport:
    ctx = cbsa_from_mapping(cbsa_code, entry)
    peer_slugs = _resolve_peer_slugs(cbsa_code, entry, mapping)
    # Step 5: no upstream connector results — every source is None. The
    # composer responds with pending blocks for all 8 core and absent
    # optional blocks whose gate depends on source data.
    composer_input = ComposerInput(ctx=ctx, peer_slugs=peer_slugs)
    blocks, availability = compose_city_report_blocks(composer_input)

    summary = _build_summary(ctx, blocks)

    meta = CityReportMeta(
        updatedAt=now_iso,
        build=CityReportBuildMeta(
            pipelineVersion=PIPELINE_VERSION,
            generatedAt=now_iso,
        ),
        optionalAvailability=availability,
    )

    return CityReport(
        slug=ctx.slug,
        cbsaCode=ctx.cbsa_code,
        city=ctx.name,
        region=ctx.state,
        country="US",
        coastal=ctx.coastal,
        lat=ctx.lat,
        lon=ctx.lon,
        population=ctx.population,
        populationYear=ctx.population_year,
        climateZone=ctx.climate_zone,
        summary=summary,
        blocks=blocks,
        meta=meta,
    )


def _build_summary(ctx, blocks) -> CityReportSummary:
    ok_count = sum(1 for b in blocks if b.status == "ok")
    pending_count = sum(1 for b in blocks if b.status == "pending")
    coastal_bullet = (
        "Coastal metro — tide gauge data available via the optional "
        "Coastal Conditions block."
        if ctx.coastal
        else "Inland metro — no coastal observations included."
    )
    population_bullet = (
        f"CBSA population ≈ {ctx.population:,} ({ctx.population_year or 'recent'})."
        if ctx.population
        else "Population estimate not available in the CBSA mapping."
    )
    return CityReportSummary(
        headline=(
            f"Environmental snapshot for {ctx.name} — {ok_count} of "
            f"{len(blocks)} blocks populated ({pending_count} pending "
            "upstream migration)."
        ),
        bullets=[
            coastal_bullet,
            population_bullet,
            f"Climate zone: {ctx.climate_zone or 'unspecified'}.",
            (
                "Report is statically generated — see Methodology block "
                "for trust-tag vocabulary and source list."
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Index entry shaper
# ---------------------------------------------------------------------------

def _classify_index_status(report: CityReport) -> CityReportIndexStatus:
    """Map block statuses → report-level rollup for the index.

    ok     — at least one core block ok AND no core block errored
    partial — core blocks are a mix of ok / pending / not_configured
    error  — ≥1 core block in 'error' state
    """
    core_ids = {
        "air_quality",
        "climate_locally",
        "hazards_disasters",
        "water",
        "industrial_emissions",
        "site_cleanup",
        "population_exposure",
        "methodology",
    }
    core_statuses = [b.status for b in report.blocks if b.id in core_ids]
    if "error" in core_statuses:
        return "error"
    if all(s == "ok" for s in core_statuses):
        return "ok"
    return "partial"


def _count_core_ok(report: CityReport) -> int:
    core_ids = {
        "air_quality",
        "climate_locally",
        "hazards_disasters",
        "water",
        "industrial_emissions",
        "site_cleanup",
        "population_exposure",
        "methodology",
    }
    return sum(
        1 for b in report.blocks if b.id in core_ids and b.status == "ok"
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


def write_reports(
    reports: list[CityReport], output_dir: Path, now_iso: str
) -> Path:
    """Write one report.json per CBSA + an index.json manifest.

    Returns the absolute path to the index file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    for report in reports:
        _write_json(output_dir / f"{report.slug}.json", report)

    index = CityReportIndex(
        generatedAt=now_iso,
        pipelineVersion=PIPELINE_VERSION,
        reports=[
            CityReportIndexEntry(
                slug=r.slug,
                cbsaCode=r.cbsaCode,
                city=r.city,
                region=r.region,
                updatedAt=r.meta.updatedAt,
                status=_classify_index_status(r),
                coreBlocksOk=_count_core_ok(r),
                coreBlocksTotal=8,
            )
            for r in reports
        ],
    )
    index_path = output_dir / "index.json"
    _write_json(index_path, index)
    return index_path


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

def _parse_only(value: str | None) -> set[str] | None:
    if not value:
        return None
    return {s.strip() for s in value.split(",") if s.strip()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--only",
        default=",".join(STEP5_SAMPLE_SLUGS),
        help=(
            "Comma-separated list of CBSA slugs to build. Defaults to the "
            "Step 5 sample set (NY/LA/Houston). Pass 'all' to build every "
            "CBSA in cbsa_mapping.json."
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory to write reports into (default: data/reports).",
    )
    args = parser.parse_args(argv)

    mapping = load_cbsa_mapping()
    if not mapping:
        print("[error] cbsa_mapping.json is empty or malformed", file=sys.stderr)
        return 2

    only = _parse_only(args.only)
    if only and "all" not in only:
        selected = {
            code: entry
            for code, entry in mapping.items()
            if entry["slug"] in only
        }
        missing = only - {entry["slug"] for entry in selected.values()}
        if missing:
            print(
                f"[warn] unknown slugs (skipping): {sorted(missing)}",
                file=sys.stderr,
            )
    else:
        selected = mapping

    if not selected:
        print("[error] no CBSAs selected — nothing to build", file=sys.stderr)
        return 2

    now_iso = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    reports = [
        build_one_report(code, entry, mapping, now_iso)
        for code, entry in selected.items()
    ]

    output_dir = Path(args.output_dir).resolve()
    index_path = write_reports(reports, output_dir, now_iso)

    print(
        f"[ok] built {len(reports)} report(s) → {output_dir} "
        f"(index: {index_path})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
