"""Contract tests for the v2 Report build pipeline.

Locks the CityReport + index.json contract against the zod schema in
``packages/schemas/src/index.ts`` and the block-inclusion rules in
``docs/reports/report-block-policy.md``. Purely offline — no network,
no real connectors. Tests run against fresh in-memory composer output
and against the committed Step 5 samples.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from pipelines.contracts import (
    CityReport,
    CityReportIndex,
    OptionalAvailabilityMap,
)
from pipelines.jobs.build_reports import (
    PIPELINE_VERSION,
    STEP5_SAMPLE_SLUGS,
    build_one_report,
    load_cbsa_mapping,
)
from pipelines.transforms.block_composer import (
    CORE_BLOCK_ORDER,
    ComposerInput,
    cbsa_from_mapping,
    combine_trust_tags,
    compose_city_report_blocks,
    gate_coastal_conditions,
    gate_pfas_monitoring,
    gate_related_cities,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
REPORTS_DIR = REPO_ROOT / "data" / "reports"


# ---------------------------------------------------------------------------
# In-memory composer tests
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def mapping() -> dict[str, dict]:
    return load_cbsa_mapping()


def _compose_for(mapping: dict[str, dict], slug: str):
    code_entry = next(
        (c, e) for c, e in mapping.items() if e["slug"] == slug
    )
    ctx = cbsa_from_mapping(*code_entry)
    blocks, avail = compose_city_report_blocks(ComposerInput(ctx=ctx))
    return ctx, blocks, avail


def test_core_blocks_always_present_and_ordered(mapping):
    """§1.1 — 8 core blocks in fixed order, every CBSA."""
    for entry in mapping.values():
        _, blocks, _ = _compose_for(mapping, entry["slug"])
        first_eight = tuple(b.id for b in blocks[:8])
        assert first_eight == CORE_BLOCK_ORDER, (
            f"{entry['slug']}: core order {first_eight} != {CORE_BLOCK_ORDER}"
        )


def test_city_comparison_never_embedded(mapping):
    """§2 — city_comparison block is NEVER in blocks[]."""
    for entry in mapping.values():
        _, blocks, avail = _compose_for(mapping, entry["slug"])
        ids = {b.id for b in blocks}
        assert "city_comparison" not in ids, (
            f"{entry['slug']}: city_comparison leaked into blocks[]"
        )
        assert avail.city_comparison == "external"


def test_optional_availability_has_five_keys(mapping):
    for entry in mapping.values():
        _, _, avail = _compose_for(mapping, entry["slug"])
        keys = set(avail.model_dump().keys())
        assert keys == {
            "pfas_monitoring",
            "coastal_conditions",
            "disaster_history_detailed",
            "city_comparison",
            "related_cities",
        }


def test_coastal_gate_matches_cbsa_flag(mapping):
    """§1.2 — coastal_conditions gate = ctx.coastal."""
    for entry in mapping.values():
        ctx, _, avail = _compose_for(mapping, entry["slug"])
        expected = "included" if ctx.coastal else "absent"
        assert avail.coastal_conditions == expected, (
            f"{entry['slug']}: coastal={ctx.coastal} → "
            f"expected {expected}, got {avail.coastal_conditions}"
        )


def test_pfas_gate_false_without_pfas_source(mapping):
    """§1.2 — PFAS gate defaults to False when no PFAS data supplied."""
    for entry in mapping.values():
        ctx = cbsa_from_mapping(
            next(c for c, e in mapping.items() if e["slug"] == entry["slug"]),
            entry,
        )
        assert gate_pfas_monitoring(ctx, None) is False


def test_related_cities_gate_tracks_peer_slugs(mapping):
    """§1.2 — related_cities gate = bool(peer_slugs)."""
    assert gate_related_cities(None, []) is False  # type: ignore[arg-type]
    assert gate_related_cities(None, ["x", "y"]) is True  # type: ignore[arg-type]


def test_combine_trust_tags_weakest_wins():
    """§4 — observed > near-real-time > forecast > compliance > derived."""
    assert combine_trust_tags(["observed"]) == "observed"
    assert combine_trust_tags(["observed", "near-real-time"]) == "near-real-time"
    assert combine_trust_tags(["observed", "compliance"]) == "compliance"
    assert combine_trust_tags(["near-real-time", "derived"]) == "derived"
    assert combine_trust_tags([]) == "derived"


def test_methodology_block_is_always_ok(mapping):
    for entry in mapping.values():
        _, blocks, _ = _compose_for(mapping, entry["slug"])
        methodology = next(b for b in blocks if b.id == "methodology")
        assert methodology.status == "ok"
        assert methodology.trustTag == "derived"


def test_block_status_vocabulary(mapping):
    """§3 — every block status ∈ {ok, error, not_configured, pending}."""
    allowed = {"ok", "error", "not_configured", "pending"}
    for entry in mapping.values():
        _, blocks, _ = _compose_for(mapping, entry["slug"])
        for b in blocks:
            assert b.status in allowed, f"{b.id}: status={b.status}"


def test_compose_to_cityreport_roundtrip(mapping):
    """Full composer output survives pydantic CityReport.model_validate."""
    for entry in list(mapping.values())[:5]:
        code = next(c for c, e in mapping.items() if e["slug"] == entry["slug"])
        report = build_one_report(code, entry, mapping, "2026-04-18T00:00:00+00:00")
        dumped = report.model_dump(mode="json")
        revalidated = CityReport.model_validate(dumped)
        assert revalidated == report


# ---------------------------------------------------------------------------
# Committed-sample tests (Step 5 acceptance)
# ---------------------------------------------------------------------------
def test_step5_samples_exist():
    for slug in STEP5_SAMPLE_SLUGS:
        path = REPORTS_DIR / f"{slug}.json"
        assert path.exists(), f"sample missing: {path}"
    assert (REPORTS_DIR / "index.json").exists()


def test_step5_samples_pass_schema():
    for slug in STEP5_SAMPLE_SLUGS:
        raw = json.loads(
            (REPORTS_DIR / f"{slug}.json").read_text(encoding="utf-8")
        )
        report = CityReport.model_validate(raw)
        assert report.slug == slug
        assert report.country == "US"
        assert report.meta.build.pipelineVersion == PIPELINE_VERSION


def test_step5_index_pass_schema():
    raw = json.loads(
        (REPORTS_DIR / "index.json").read_text(encoding="utf-8")
    )
    idx = CityReportIndex.model_validate(raw)
    assert idx.pipelineVersion == PIPELINE_VERSION
    slugs = {entry.slug for entry in idx.reports}
    assert set(STEP5_SAMPLE_SLUGS).issubset(slugs)


def test_step5_sample_optional_availability_shapes():
    for slug in STEP5_SAMPLE_SLUGS:
        raw = json.loads(
            (REPORTS_DIR / f"{slug}.json").read_text(encoding="utf-8")
        )
        avail = OptionalAvailabilityMap.model_validate(
            raw["meta"]["optionalAvailability"]
        )
        # All three samples (NY/LA/Houston) are coastal, so coastal_conditions
        # must be 'included'. city_comparison is always 'external'.
        assert avail.coastal_conditions == "included", slug
        assert avail.city_comparison == "external", slug
        # PFAS is a v2-gate False until connector lands.
        assert avail.pfas_monitoring == "absent", slug
