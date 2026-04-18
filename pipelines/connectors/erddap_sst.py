"""NOAA OISST point-query connector — NOAA CoastWatch ERDDAP griddap.

Product: NOAA 1/4° Daily Optimum Interpolation SST v2.1 (AVHRR-Only)
Envelope: ``SSTPoint`` (scalar-point envelope, ``normalized-contracts.md`` §2b)
Trust tag: ``observed``
Cadence: ``daily`` (1-day latency, NRT aggregate)
Spatial scope: ocean 0.25°

=============================================================================
STEP-2 LANDMINES (verified via live spike 2026-04-17, see
``data/fixtures/oisst/point-sample.json`` ``_meta.notes`` and
``docs/datasets/source-spike-matrix.md`` §1.2):

(a) LON 0-360 WRAP IS MANDATORY.
    ERDDAP stores longitude on a 0-360° grid (0.125° to 359.875°). Clients
    routinely pass -180..180. A naive URL built on the user's lon yields
    ``status: 400 Bad Request — Your query produced no matching results``.
    Always wrap with ``lon_erddap = lon + 360 if lon < 0 else lon`` before
    interpolating into the URL template.

(b) zlev=(0.0) IS MANDATORY — DEGENERATE DEPTH DIMENSION.
    The griddap variable signature is ``sst[time][zlev][lat][lon]``. Even
    though OISST is a surface product with a single z level, the zlev
    dimension is not implicit. Omitting ``[(0.0)]`` produces
    ``status: 400 Bad Request — nDimensions...``. Never drop the zlev slot.

(c) LAND / ICE CELLS RETURN JSON ``null`` (NOT HTTP 404).
    ERDDAP returns a fully-formed JSON document with ``table.rows[0][4]``
    set to JSON ``null`` for any grid cell over land or persistent sea
    ice. We MUST detect this and return ``SSTPoint(status='no_data', ...)``
    with a friendly message. It is the graceful case — not an error —
    and the UI is expected to render "Location is land or ice" instead
    of an error toast.

(d) TWO DATASET IDs — NRT vs FINAL.
    - ``ncdcOisst21NrtAgg`` — Near-Real-Time aggregate, ~1-day lag. Used
      for the live Globe click-to-value flow. Trust tag still
      ``observed`` (NOAA's NRT product is a real measurement, not a
      forecast).
    - ``ncdcOisst21Agg`` — Final aggregate, ~14-day lag, quality-checked.
      Appropriate for Report/Atlas long-term use, NOT the Globe click.

    This connector defaults to the NRT aggregate. If the product is ever
    switched to Final, update ``ERDDAP_BASE`` and the ``source`` string
    in one place below. The cadence string stays ``daily``; only the
    source label / URL shifts.

Additional implementation notes:
- ERDDAP JSON output path segment is ``.json``. Query syntax uses
  ``sst[last][(0.0)][(lat)][(lon)]`` with ``(value)`` meaning "nearest
  grid-cell centre to this decimal". ERDDAP snaps to the centre and
  returns that snapped value in the ``latitude`` / ``longitude`` columns.
- We convert the snapped ``longitude`` column BACK to -180..180 before
  returning; the ``SSTPoint`` envelope requires -180..180 per contract
  §2b.
- Time column is ISO-8601 with ``Z``. No conversion needed.
- No auth, no API key. CORS is permissive for JSON responses.
=============================================================================
"""
from __future__ import annotations

from typing import Any

import httpx

from pipelines.connectors.base import BaseConnector, ConnectorResult
from pipelines.contracts import SSTPoint

# -----------------------------------------------------------------------------
# Module-level constants (URL composition lives in ONE place).
# Switching the NRT vs Final aggregate only requires changing these.
# -----------------------------------------------------------------------------
ERDDAP_BASE = "https://coastwatch.pfeg.noaa.gov/erddap/griddap/ncdcOisst21NrtAgg"

SOURCE_LABEL = "NOAA OISST v2.1"
CADENCE_LABEL = "daily"
SPATIAL_SCOPE = "ocean 0.25°"
LICENSE_LABEL = "public domain"
TRUST_TAG = "observed"

# Latitude / longitude bounds inside ERDDAP's 0.25° grid (user-side).
LAT_MIN = -89.875
LAT_MAX = 89.875
LON_MIN = -179.875
LON_MAX = 179.875


def _wrap_lon(lon: float) -> float:
    """Convert user -180..180 longitude to ERDDAP 0-360.

    Landmine (a): ERDDAP stores longitude on a 0-360 grid. Never call
    ERDDAP with a negative lon.
    """
    return lon + 360.0 if lon < 0 else lon


def _unwrap_lon(lon_360: float) -> float:
    """Convert ERDDAP 0-360 longitude back to -180..180.

    The SST scalar-point envelope (``normalized-contracts.md`` §2b) is
    unambiguous: ``snappedLon`` is -180..180.
    """
    return lon_360 - 360.0 if lon_360 > 180.0 else lon_360


def build_query_url(lat: float, lon: float) -> str:
    """Compose the ERDDAP JSON query URL for a single (lat, lon) point.

    Landmines (a) + (b) live here:
    - lon is wrapped to 0-360
    - ``zlev=(0.0)`` is always included

    The ``last`` token returns the most recently published daily timestep
    for the chosen aggregate.
    """
    lon_360 = _wrap_lon(lon)
    # ERDDAP griddap extraction syntax:
    #   sst[time][zlev][lat][lon]  with (value) = snap to nearest centre.
    # Reference-style bracket syntax — httpx will URL-encode for the wire.
    return (
        f"{ERDDAP_BASE}.json?"
        f"sst[last][(0.0)][({lat})][({lon_360})]"
    )


class ErddapSstConnector(BaseConnector):
    """Single-point SST connector — ERDDAP griddap → ``SSTPoint`` envelope.

    Usage::

        conn = ErddapSstConnector()
        raw = await conn.fetch(lat=35.0, lon=-120.5)
        result = conn.normalize(raw, lat_requested=35.0, lon_requested=-120.5)
        point = result.values  # <-- SSTPoint, NOT a list.
    """

    name = "erddap_sst"
    source = SOURCE_LABEL
    source_url = ERDDAP_BASE
    cadence = CADENCE_LABEL
    tag = TRUST_TAG  # type: ignore[assignment]

    # Exposed as instance/staticmethods so unit tests can assert the wrap
    # math directly — see ``test_erddap_sst_contract.py``.
    _wrap_lon = staticmethod(_wrap_lon)
    _unwrap_lon = staticmethod(_unwrap_lon)

    async def fetch(self, lat: float, lon: float, **_: Any) -> dict:  # type: ignore[override]
        """Fetch a single ERDDAP point result as parsed JSON.

        Raises ``httpx.HTTPError`` on transport / non-2xx response — caller
        (or ``run()``) wraps the exception into a graceful SSTPoint error.
        """
        url = build_query_url(lat=lat, lon=lon)
        timeout = httpx.Timeout(15.0, connect=5.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()

    def _build_result(
        self,
        point: SSTPoint,
        *,
        status: str,
        notes: list[str] | None = None,
    ) -> ConnectorResult:
        """Wrap an SSTPoint into a ConnectorResult with our locked metadata."""
        return ConnectorResult(
            values=point,
            source=SOURCE_LABEL,
            source_url=ERDDAP_BASE,
            cadence=CADENCE_LABEL,
            tag=TRUST_TAG,  # type: ignore[arg-type]
            spatial_scope=SPATIAL_SCOPE,
            license=LICENSE_LABEL,
            status=status,  # type: ignore[arg-type]
            notes=notes or [],
        )

    def normalize(  # type: ignore[override]
        self,
        raw: dict,
        lat_requested: float,
        lon_requested: float,
    ) -> ConnectorResult:
        """Transform an ERDDAP JSON body into a ``ConnectorResult``
        whose ``values`` is a single ``SSTPoint``.

        Behaviour:
        - Happy path → ``status='ok'``, full population.
        - JSON null in sst column → ``status='no_data'``, sst_c=None,
          friendly ``message``. The user clicked land / ice.
        - Any parse / shape failure → ``status='error'``, sst_c=None.
        """
        try:
            table = raw["table"]
            column_names: list[str] = table["columnNames"]
            rows: list[list[Any]] = table["rows"]

            if not rows:
                # Empty rows is a weird but possible edge case for points
                # strictly outside the domain. Treat as no_data — UX
                # difference vs error is meaningful.
                point = SSTPoint(
                    status="no_data",
                    source=SOURCE_LABEL,
                    source_url=ERDDAP_BASE,
                    cadence=CADENCE_LABEL,
                    tag=TRUST_TAG,  # type: ignore[arg-type]
                    lat=lat_requested,
                    lon=lon_requested,
                    sst_c=None,
                    message="ERDDAP returned no rows for this location.",
                )
                return self._build_result(
                    point,
                    status="ok",
                    notes=["Empty rows array — returned as no_data."],
                )

            row = rows[0]
            # Resolve columns by name — ERDDAP order is stable (time, zlev,
            # latitude, longitude, sst) but by-name guards against future
            # rearrangement.
            idx = {name: i for i, name in enumerate(column_names)}
            sst_raw = row[idx["sst"]]
            time_raw = row[idx["time"]]
            snapped_lat_raw = row[idx["latitude"]]
            snapped_lon_raw = row[idx["longitude"]]

            # Landmine (c): land / ice cells → JSON null (not 404).
            if sst_raw is None:
                point = SSTPoint(
                    status="no_data",
                    source=SOURCE_LABEL,
                    source_url=ERDDAP_BASE,
                    cadence=CADENCE_LABEL,
                    tag=TRUST_TAG,  # type: ignore[arg-type]
                    lat=lat_requested,
                    lon=lon_requested,
                    snappedLat=float(snapped_lat_raw),
                    snappedLon=_unwrap_lon(float(snapped_lon_raw)),
                    sst_c=None,
                    observed_at=str(time_raw) if time_raw is not None else None,
                    message="Location is land or ice — no ocean SST available.",
                )
                return self._build_result(
                    point,
                    status="ok",
                    notes=["Land/ice cell — JSON null in sst column (expected)."],
                )

            point = SSTPoint(
                status="ok",
                source=SOURCE_LABEL,
                source_url=ERDDAP_BASE,
                cadence=CADENCE_LABEL,
                tag=TRUST_TAG,  # type: ignore[arg-type]
                lat=lat_requested,
                lon=lon_requested,
                snappedLat=float(snapped_lat_raw),
                snappedLon=_unwrap_lon(float(snapped_lon_raw)),
                sst_c=float(sst_raw),
                observed_at=str(time_raw),
                message=None,
            )
            return self._build_result(point, status="ok")
        except Exception as exc:  # noqa: BLE001 — graceful-degradation contract
            point = SSTPoint(
                status="error",
                source=SOURCE_LABEL,
                source_url=ERDDAP_BASE,
                cadence=CADENCE_LABEL,
                tag=TRUST_TAG,  # type: ignore[arg-type]
                lat=lat_requested,
                lon=lon_requested,
                sst_c=None,
                message=f"ERDDAP normalize failed: {exc}",
            )
            return self._build_result(
                point,
                status="error",
                notes=[f"normalize exception: {exc!r}"],
            )

    async def run(  # type: ignore[override]
        self,
        lat: float,
        lon: float,
        **_: Any,
    ) -> ConnectorResult:
        """Full transport + normalize flow. Transport failure is caught
        and returned as a graceful SSTPoint error (per the
        ``normalized-contracts.md`` §6 graceful-degradation rule)."""
        try:
            raw = await self.fetch(lat=lat, lon=lon)
        except Exception as exc:  # noqa: BLE001
            point = SSTPoint(
                status="error",
                source=SOURCE_LABEL,
                source_url=ERDDAP_BASE,
                cadence=CADENCE_LABEL,
                tag=TRUST_TAG,  # type: ignore[arg-type]
                lat=lat,
                lon=lon,
                sst_c=None,
                message=f"ERDDAP fetch failed: {exc}",
            )
            return self._build_result(
                point,
                status="error",
                notes=[f"fetch exception: {exc!r}"],
            )
        return self.normalize(raw, lat_requested=lat, lon_requested=lon)


__all__ = [
    "ERDDAP_BASE",
    "SOURCE_LABEL",
    "CADENCE_LABEL",
    "SPATIAL_SCOPE",
    "LICENSE_LABEL",
    "TRUST_TAG",
    "ErddapSstConnector",
    "build_query_url",
]
