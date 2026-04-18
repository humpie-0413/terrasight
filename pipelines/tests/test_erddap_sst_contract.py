"""Contract tests for the ERDDAP OISST point connector.

Locks the ``ErddapSstConnector`` output against the scalar-point envelope
in ``docs/datasets/normalized-contracts.md`` §2b and the pydantic mirror
in ``pipelines/contracts/__init__.py::SSTPoint``.

No network — every case is driven by a fixture in
``pipelines/tests/fixtures/erddap_sst/``.

Run:
    python -m pytest pipelines/tests/test_erddap_sst_contract.py -v
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pipelines.connectors.erddap_sst import (
    ERDDAP_BASE,
    SOURCE_LABEL,
    ErddapSstConnector,
    build_query_url,
)
from pipelines.contracts import SSTPoint

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "erddap_sst"


def _load(name: str) -> dict:
    path = FIXTURE_DIR / name
    assert path.exists(), f"Missing fixture: {path}"
    payload = json.loads(path.read_text(encoding="utf-8"))
    # Strip stamp keys before handing to normalize() — connector never sees
    # them on the wire.
    return {k: v for k, v in payload.items() if not k.startswith("_")}


# -----------------------------------------------------------------------------
# Happy path — successful ocean point.
# -----------------------------------------------------------------------------
def test_ocean_point_normalizes_to_ok_status() -> None:
    raw = _load("point-ocean.json")
    conn = ErddapSstConnector()
    result = conn.normalize(raw, lat_requested=35.0, lon_requested=-120.5)

    assert result.status == "ok", f"ConnectorResult status should be 'ok', got {result.status}"
    assert result.source == SOURCE_LABEL
    assert result.source_url == ERDDAP_BASE

    point = result.values
    assert isinstance(point, SSTPoint), "values must be a single SSTPoint, not a list"
    assert point.status == "ok"
    assert point.sst_c is not None
    assert isinstance(point.sst_c, float)
    assert -3.0 <= point.sst_c <= 40.0, "SST must be in plausible ocean range (°C)"


def test_ocean_point_preserves_requested_coords() -> None:
    raw = _load("point-ocean.json")
    conn = ErddapSstConnector()
    result = conn.normalize(raw, lat_requested=35.0, lon_requested=-120.5)
    point = result.values
    assert isinstance(point, SSTPoint)
    assert point.lat == 35.0
    assert point.lon == -120.5


def test_ocean_snapped_lon_is_in_180_range() -> None:
    """Contract §2b: ``snappedLon`` must be -180..180, NOT 0-360."""
    raw = _load("point-ocean.json")
    conn = ErddapSstConnector()
    result = conn.normalize(raw, lat_requested=35.0, lon_requested=-120.5)
    point = result.values
    assert isinstance(point, SSTPoint)
    assert point.snappedLon is not None
    assert -180.0 <= point.snappedLon <= 180.0, (
        f"snappedLon must be in [-180, 180], got {point.snappedLon} "
        "(forgot to unwrap from 0-360?)"
    )
    # Specific expected value: ERDDAP snapped to 239.625 -> -120.375.
    assert point.snappedLon == pytest.approx(-120.375)


def test_ocean_observed_at_is_iso8601_utc() -> None:
    raw = _load("point-ocean.json")
    conn = ErddapSstConnector()
    result = conn.normalize(raw, lat_requested=35.0, lon_requested=-120.5)
    point = result.values
    assert isinstance(point, SSTPoint)
    assert point.observed_at is not None
    # ERDDAP stamps ISO-8601 with trailing Z.
    assert point.observed_at.endswith("Z")
    assert "T" in point.observed_at


def test_ocean_point_roundtrips_through_pydantic() -> None:
    raw = _load("point-ocean.json")
    conn = ErddapSstConnector()
    result = conn.normalize(raw, lat_requested=35.0, lon_requested=-120.5)
    point = result.values
    assert isinstance(point, SSTPoint)
    dumped = point.model_dump()
    revalidated = SSTPoint.model_validate(dumped)
    assert revalidated == point


# -----------------------------------------------------------------------------
# Land/ice case — JSON null in sst column.
# -----------------------------------------------------------------------------
def test_land_null_normalizes_to_no_data() -> None:
    raw = _load("point-land-null.json")
    conn = ErddapSstConnector()
    result = conn.normalize(raw, lat_requested=40.0, lon_requested=-100.0)

    # Inner SSTPoint status is 'no_data' — this is the user-facing state.
    point = result.values
    assert isinstance(point, SSTPoint)
    assert point.status == "no_data", (
        f"Land/ice cell must produce SSTPoint.status='no_data', got {point.status}"
    )
    assert point.sst_c is None
    assert point.message is not None and len(point.message) > 0, (
        "no_data SSTPoint must carry a human-readable message"
    )


def test_land_null_preserves_snapped_coords_unwrapped() -> None:
    raw = _load("point-land-null.json")
    conn = ErddapSstConnector()
    result = conn.normalize(raw, lat_requested=40.0, lon_requested=-100.0)
    point = result.values
    assert isinstance(point, SSTPoint)
    assert point.snappedLat is not None
    assert point.snappedLon is not None
    assert -180.0 <= point.snappedLon <= 180.0
    # 260.125 → -99.875 after unwrap.
    assert point.snappedLon == pytest.approx(-99.875)


# -----------------------------------------------------------------------------
# Error case — malformed / transient upstream response.
# -----------------------------------------------------------------------------
def test_error_fixture_normalizes_to_error_status() -> None:
    raw = _load("point-error.json")
    conn = ErddapSstConnector()
    result = conn.normalize(raw, lat_requested=35.0, lon_requested=-120.5)

    point = result.values
    assert isinstance(point, SSTPoint)
    assert point.status == "error"
    assert point.sst_c is None
    assert point.message is not None and len(point.message) > 0


# -----------------------------------------------------------------------------
# Longitude wrap unit test — landmine (a).
# -----------------------------------------------------------------------------
def test_wrap_lon_converts_negative_to_0_360() -> None:
    """Landmine (a): ERDDAP lon is 0-360. -120.5 -> 239.5."""
    assert ErddapSstConnector._wrap_lon(-120.5) == 239.5


def test_wrap_lon_passes_positive_through_unchanged() -> None:
    assert ErddapSstConnector._wrap_lon(0.0) == 0.0
    assert ErddapSstConnector._wrap_lon(150.0) == 150.0
    assert ErddapSstConnector._wrap_lon(179.5) == 179.5


def test_unwrap_lon_converts_gt180_back_to_180_range() -> None:
    assert ErddapSstConnector._unwrap_lon(239.625) == pytest.approx(-120.375)
    assert ErddapSstConnector._unwrap_lon(180.0) == 180.0
    assert ErddapSstConnector._unwrap_lon(0.125) == 0.125


# -----------------------------------------------------------------------------
# URL composition — verifies landmines (a) + (b) are baked in.
# -----------------------------------------------------------------------------
def test_build_query_url_includes_zlev_dimension() -> None:
    """Landmine (b): zlev=(0.0) is mandatory."""
    url = build_query_url(lat=35.0, lon=-120.5)
    assert "(0.0)" in url, "zlev=(0.0) dimension must be present in query URL"


def test_build_query_url_wraps_negative_lon_to_0_360() -> None:
    """Landmine (a): URL must carry the 0-360 lon, not the user's."""
    url = build_query_url(lat=35.0, lon=-120.5)
    assert "(239.5)" in url, "negative lon must be wrapped to 0-360 before URL build"
    assert "(-120.5)" not in url, "raw negative lon must NOT leak into ERDDAP URL"


def test_build_query_url_uses_last_time_token() -> None:
    url = build_query_url(lat=35.0, lon=-120.5)
    assert "[last]" in url, "query must use the ERDDAP 'last' token for latest timestep"
