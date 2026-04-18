"""Contract tests for the GIBS layer manifest module.

These tests lock the LayerManifest contract against
``docs/datasets/gibs-approved-layers.md`` and the pydantic mirror in
``pipelines/contracts/__init__.py``. They run purely offline — no
network, no fixtures beyond the JSON drops in
``pipelines/tests/fixtures/gibs/``.

Run:
    python -m pytest pipelines/tests/test_gibs_contract.py -v
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pipelines.connectors.gibs import (
    GIBS_MANIFESTS,
    all_manifests,
    get_manifest,
)
from pipelines.contracts import LayerLegend, LayerManifest

# ---------------------------------------------------------------------------
# The single source of truth for approved IDs. Any drift from this set
# means either gibs-approved-layers.md changed or someone edited gibs.py
# without reading it — both are review-gate failures.
# ---------------------------------------------------------------------------
APPROVED_IDS = {
    "BlueMarble_ShadedRelief_Bathymetry",
    "GHRSST_L4_MUR_Sea_Surface_Temperature",
    "MODIS_Terra_Aerosol",
    "MODIS_Aqua_Cloud_Fraction_Day",
    "VIIRS_SNPP_DayNightBand",
}

BANNED_IDS = {"VIIRS_SNPP_DayNightBand_ENCC"}

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "gibs"


def test_exactly_five_manifests() -> None:
    assert len(GIBS_MANIFESTS) == 5


def test_manifest_ids_match_approved_set_exactly() -> None:
    actual = {m.id for m in GIBS_MANIFESTS}
    assert actual == APPROVED_IDS, (
        f"Manifest id drift.\n  extras:  {actual - APPROVED_IDS}\n"
        f"  missing: {APPROVED_IDS - actual}"
    )


def test_no_encc_variant_in_manifests() -> None:
    actual = {m.id for m in GIBS_MANIFESTS}
    assert not (actual & BANNED_IDS), (
        f"Frozen ENCC variant must not appear in GIBS_MANIFESTS: "
        f"{actual & BANNED_IDS}"
    )


def test_all_manifests_roundtrip_through_pydantic() -> None:
    """Every manifest must survive model_dump() -> model_validate()."""
    for m in GIBS_MANIFESTS:
        dumped = m.model_dump()
        revalidated = LayerManifest.model_validate(dumped)
        assert revalidated == m, (
            f"Roundtrip mismatch for {m.id}: dump/validate produced "
            f"a different value."
        )


def test_get_manifest_returns_matching_layer() -> None:
    got = get_manifest("GHRSST_L4_MUR_Sea_Surface_Temperature")
    assert got.id == "GHRSST_L4_MUR_Sea_Surface_Temperature"
    assert got.coverage == "ocean-only"
    assert isinstance(got.legend, LayerLegend)


def test_get_manifest_rejects_encc_variant() -> None:
    """Landmine #1 — ENCC is frozen at 2023-07-07; we refuse to serve it."""
    with pytest.raises(KeyError):
        get_manifest("VIIRS_SNPP_DayNightBand_ENCC")


def test_get_manifest_unknown_id_raises_keyerror() -> None:
    with pytest.raises(KeyError):
        get_manifest("not_a_real_layer_xyz")


def test_all_manifests_returns_copy_not_reference() -> None:
    """Mutating the returned list must not mutate the module state."""
    copy = all_manifests()
    copy.clear()
    assert len(GIBS_MANIFESTS) == 5


def test_every_manifest_has_required_fields_populated() -> None:
    """Shape contract per gibs-approved-layers.md §2."""
    for m in GIBS_MANIFESTS:
        assert m.category == "imagery"
        assert m.kind == "continuous"
        assert m.enabled is True
        assert m.trustTag in {"observed", "near-real-time"}
        assert m.imagery is not None, f"{m.id}: imagery must be populated"
        assert m.imagery.type == "wmts"
        assert "{TileMatrix}" in m.imagery.urlTemplate
        assert "{TileRow}" in m.imagery.urlTemplate
        assert "{TileCol}" in m.imagery.urlTemplate
        assert m.eventApi is None, f"{m.id}: eventApi must be None for imagery"
        assert m.caveats, f"{m.id}: caveats must be non-empty"


def test_trust_tags_match_approval_doc() -> None:
    """BlueMarble = observed; daily NRT layers = near-real-time.

    Locked by ``docs/datasets/gibs-approved-layers.md`` §2.
    """
    assert get_manifest("BlueMarble_ShadedRelief_Bathymetry").trustTag == "observed"
    for layer_id in APPROVED_IDS - {"BlueMarble_ShadedRelief_Bathymetry"}:
        m = get_manifest(layer_id)
        assert m.trustTag == "near-real-time", (
            f"{layer_id}: approval doc requires trustTag='near-real-time', "
            f"got {m.trustTag!r}"
        )


def test_only_sst_carries_a_legend() -> None:
    with_legend = [m for m in GIBS_MANIFESTS if m.legend is not None]
    assert len(with_legend) == 1
    assert with_legend[0].id == "GHRSST_L4_MUR_Sea_Surface_Temperature"
    legend = with_legend[0].legend
    assert legend is not None
    assert legend.unit == "\u00b0C"
    assert legend.min == -2.0
    assert legend.max == 32.0
    assert legend.colormap == "thermal"


def test_night_lights_caveat_mentions_encc_freeze() -> None:
    nl = get_manifest("VIIRS_SNPP_DayNightBand")
    joined = " ".join(nl.caveats)
    assert "_ENCC" in joined
    assert "2023-07-07" in joined


def test_aod_title_matches_approval_table() -> None:
    aod = get_manifest("MODIS_Terra_Aerosol")
    assert aod.title == "Aerosol Proxy (AOD)"


def test_clouds_caveat_mentions_day_pass_limitation() -> None:
    clouds = get_manifest("MODIS_Aqua_Cloud_Fraction_Day")
    joined = " ".join(clouds.caveats).lower()
    assert "day" in joined and "night" in joined


def test_blue_marble_uses_default_date_token() -> None:
    bm = get_manifest("BlueMarble_ShadedRelief_Bathymetry")
    assert bm.imagery is not None
    # Static layer: date segment is the literal "default", not {Time}.
    assert "/default/default/" in bm.imagery.urlTemplate
    assert "{Time}" not in bm.imagery.urlTemplate


def test_daily_layers_use_time_token() -> None:
    for layer_id in APPROVED_IDS - {"BlueMarble_ShadedRelief_Bathymetry"}:
        m = get_manifest(layer_id)
        assert m.imagery is not None
        assert "{Time}" in m.imagery.urlTemplate, (
            f"{layer_id}: daily layer must carry {{Time}} date token."
        )


def test_manifest_fixture_matches_module_output() -> None:
    """Lock the committed fixture to whatever GIBS_MANIFESTS emits."""
    fixture_path = FIXTURE_DIR / "manifest.json"
    assert fixture_path.exists(), (
        f"Missing fixture: {fixture_path}. Regenerate via gibs.all_manifests()."
    )
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    fixture_data = payload["data"]
    module_data = [m.model_dump(mode="json") for m in GIBS_MANIFESTS]
    assert fixture_data == module_data


def test_legend_sst_fixture_matches_module_output() -> None:
    fixture_path = FIXTURE_DIR / "legend-sst.json"
    assert fixture_path.exists()
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    sst = get_manifest("GHRSST_L4_MUR_Sea_Surface_Temperature")
    assert sst.legend is not None
    assert payload["data"] == sst.legend.model_dump(mode="json")
