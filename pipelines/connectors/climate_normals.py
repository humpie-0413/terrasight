"""U.S. Climate Normals 1991-2020 connector.

Source:  https://www.ncei.noaa.gov/products/land-based-station/us-climate-normals
Cadence: 30-year baseline (static reference)
Tag:     derived (30-yr statistical summary)

Used for: Local Reports Block 2 baseline comparison against monthly CtaG
city series. Provides the 1991-2020 reference line for temperature and
precipitation.

=============================================================================
Verified 2026-04-10 / re-verified 2026-04-11:
  Base directory:
    https://www.ncei.noaa.gov/data/normals-monthly/1991-2020/access/
  Per-station file: `{STATION_ID}.csv`, e.g. USW00012918.csv.

Each station file has exactly 12 rows (one per month, DATE = "01".."12")
and ~260 columns. We only pull the four core normals:
    MLY-TAVG-NORMAL  (monthly mean temp, °F)
    MLY-TMAX-NORMAL  (monthly max temp,  °F)
    MLY-TMIN-NORMAL  (monthly min temp,  °F)
    MLY-PRCP-NORMAL  (monthly precip,    inches)
plus STATION, NAME, LATITUDE, LONGITUDE, ELEVATION, DATE.

Missing-value sentinels observed in NCEI normals files: -9999, -7777, and
the empty string (plus values are space-padded in the CSV, so we strip
before parsing). All of these are normalized to None.
=============================================================================
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from typing import Any

import httpx

from backend.connectors.base import BaseConnector, ConnectorResult

BASE_URL = "https://www.ncei.noaa.gov/data/normals-monthly/1991-2020/access/"

# Values NCEI uses to mark missing / unavailable normals.
_MISSING_SENTINELS = {"-9999", "-7777", ""}


@dataclass
class MonthlyNormal:
    month: int              # 1-12
    t_avg_f: float | None
    t_max_f: float | None
    t_min_f: float | None
    precip_in: float | None


@dataclass
class StationNormals:
    station_id: str         # e.g. "USW00012918"
    station_name: str       # e.g. "HOUSTON HOBBY AP, TX US"
    lat: float
    lon: float
    elevation_m: float
    monthly: list[MonthlyNormal]   # 12 entries, Jan → Dec
    annual_t_avg_f: float | None   # mean of available monthly averages
    annual_precip_in: float | None # sum of available monthly precip


def _parse_optional_float(raw: str | None) -> float | None:
    """Parse an NCEI normals cell into a float, or None if missing.

    Handles:
      - blank / None
      - space-padded numerics (e.g. "    55.0")
      - sentinels -9999 and -7777
    """
    if raw is None:
        return None
    cleaned = raw.strip()
    if cleaned in _MISSING_SENTINELS:
        return None
    try:
        value = float(cleaned)
    except ValueError:
        return None
    # Defensive: some NCEI products reuse -9999/-7777 as numeric floats
    # even where the string form might differ. Catch those too.
    if value <= -7000:
        return None
    return value


def _parse_required_float(raw: str | None, default: float = 0.0) -> float:
    """Parse a required float (station metadata) with a safe default."""
    parsed = _parse_optional_float(raw)
    return default if parsed is None else parsed


class ClimateNormalsConnector(BaseConnector):
    name = "climate_normals"
    source = "U.S. Climate Normals 1991-2020"
    source_url = (
        "https://www.ncei.noaa.gov/products/land-based-station/us-climate-normals"
    )
    cadence = "30-yr baseline"
    tag = "derived"

    async def fetch(self, station_id: str, **_: Any) -> str:
        """Download the per-station 1991-2020 monthly normals CSV.

        Parameters
        ----------
        station_id : str
            GHCND station identifier, e.g. "USW00012918".
        """
        url = f"{BASE_URL}{station_id}.csv"
        timeout = httpx.Timeout(30.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text

    def normalize(self, raw: str) -> ConnectorResult:
        """Parse the per-station CSV into a single StationNormals.

        The NCEI file has ~260 columns; we only inspect the handful needed
        for Local Reports Block 2. Missing normals (blank / -9999 / -7777)
        become None. Annual summaries are computed from whatever monthly
        values are available.
        """
        reader = csv.DictReader(io.StringIO(raw))
        rows = list(reader)

        if not rows:
            raise ValueError("Climate Normals CSV had no data rows")

        # Station-level metadata comes from the first row; it is identical
        # on all 12 rows by construction.
        first = rows[0]
        station_id = (first.get("STATION") or "").strip()
        station_name = (first.get("NAME") or "").strip()
        lat = _parse_required_float(first.get("LATITUDE"))
        lon = _parse_required_float(first.get("LONGITUDE"))
        elevation_m = _parse_required_float(first.get("ELEVATION"))

        monthly: list[MonthlyNormal] = []
        for row in rows:
            # Prefer DATE (MM), fall back to the lowercase "month" column
            # which NCEI also emits.
            raw_month = (row.get("DATE") or row.get("month") or "").strip()
            try:
                month_int = int(raw_month)
            except ValueError:
                continue
            if not 1 <= month_int <= 12:
                continue

            monthly.append(
                MonthlyNormal(
                    month=month_int,
                    t_avg_f=_parse_optional_float(row.get("MLY-TAVG-NORMAL")),
                    t_max_f=_parse_optional_float(row.get("MLY-TMAX-NORMAL")),
                    t_min_f=_parse_optional_float(row.get("MLY-TMIN-NORMAL")),
                    precip_in=_parse_optional_float(row.get("MLY-PRCP-NORMAL")),
                )
            )

        # Sort Jan → Dec so callers can assume stable ordering.
        monthly.sort(key=lambda m: m.month)

        # Annual averages use whatever months have values. If every month
        # is missing the metric, the annual summary is None.
        t_avg_values = [m.t_avg_f for m in monthly if m.t_avg_f is not None]
        precip_values = [m.precip_in for m in monthly if m.precip_in is not None]
        annual_t_avg_f = sum(t_avg_values) / len(t_avg_values) if t_avg_values else None
        annual_precip_in = sum(precip_values) if precip_values else None

        station = StationNormals(
            station_id=station_id,
            station_name=station_name,
            lat=lat,
            lon=lon,
            elevation_m=elevation_m,
            monthly=monthly,
            annual_t_avg_f=annual_t_avg_f,
            annual_precip_in=annual_precip_in,
        )

        return ConnectorResult(
            values=station,
            source=self.source,
            source_url=self.source_url,
            cadence=self.cadence,
            tag=self.tag,
            spatial_scope="Single GHCND station, 1991-2020 30-year normals",
            license="Public domain (NOAA NCEI)",
            notes=[
                "1991-2020 reference period; newer than the WMO 1961-1990 "
                "baseline still used by some products.",
                "Station normals; not representative of the full CBSA.",
                "Values in °F and inches (U.S. customary units, consistent "
                "with NCEI product).",
            ],
        )
