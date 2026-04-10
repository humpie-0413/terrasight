"""NOAA OISST daily SST connector — via NOAA CoastWatch ERDDAP.

Product: NOAA 1/4° Daily Optimum Interpolation SST v2.1 (AVHRR-Only)
Cadence: daily (1-day latency for NRT; final after ~2 weeks)
Tag:     observed (NRT)

=============================================================================
BLOCKER RESOLUTION (2026-04-10 OISST blocker spike):

The canonical NCEI THREDDS endpoint documented on the OISST product page is
DEAD:
  ❌ https://www.ncei.noaa.gov/thredds/dodsC/model-oisst-daily/ → OPeNDAP error
  ❌ https://www.ncei.noaa.gov/thredds-ocean/fileServer/oisst-daily/... → 404

Verified live alternative: NOAA CoastWatch ERDDAP griddap server.
  ✅ https://coastwatch.pfeg.noaa.gov/erddap/griddap/ncdcOisst21NrtAgg  (NRT)
  ✅ https://coastwatch.pfeg.noaa.gov/erddap/griddap/ncdcOisst21Agg     (final, 2-week delay)

ERDDAP advantages over THREDDS:
- No auth, no Earthdata login
- URL-based bbox + time slicing (%5B...%5D syntax = [start:stride:stop])
- CSV / JSON / NetCDF / PNG / WMS tile output
=============================================================================

Implementation notes (verified 2026-04-10 via curl subagent):
- ERDDAP griddap CSV returns 2 header rows (column names + units) before data
- Land cells are the literal string "NaN" — must filter before float()
- Longitude uses 0-360 convention; we convert to -180..180 for the globe
- `(last)` time syntax works — returns latest valid daily file (~2-day latency)
- Stride=20 over a 1440x720 grid yields ~1,700 ocean points in ~2s,
  which is a comfortable browser load for hexbin/point rendering on a globe
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from typing import Any

import httpx

from backend.connectors.base import BaseConnector, ConnectorResult

ERDDAP_BASE = "https://coastwatch.pfeg.noaa.gov/erddap"

# Dataset IDs
DATASET_NRT = "ncdcOisst21NrtAgg"   # Near-real-time (1-day latency)
DATASET_FINAL = "ncdcOisst21Agg"    # Final (~2-week delay)

# Default: use NRT for Earth Now layer (freshness matters more than stability here)
DEFAULT_DATASET = DATASET_NRT

# Query template for ERDDAP griddap CSV.
# Syntax: sst[time][zlev][lat_start:stride:lat_stop][lon_start:stride:lon_stop]
# - (last) = most recent time step
# - zlev = 0.0 (surface only)
# - stride controls downsampling; 20 ~= 5° resolution, ~1,700 ocean points
DEFAULT_STRIDE = 20


@dataclass
class SstPoint:
    lat: float
    lon: float   # -180..180 (already converted from ERDDAP's 0-360)
    sst_c: float


class OisstConnector(BaseConnector):
    name = "oisst"
    source = "NOAA OISST v2.1 (via CoastWatch ERDDAP)"
    source_url = f"{ERDDAP_BASE}/griddap/{DEFAULT_DATASET}.html"
    cadence = "daily (1-day latency, NRT)"
    tag = "observed"

    async def fetch(self, stride: int = DEFAULT_STRIDE, **_: Any) -> str:
        """Pull the latest SST grid from ERDDAP at the given stride."""
        # ERDDAP griddap CSV query — brackets pre-encoded for httpx/curl parity.
        # sst[(last)][(0.0)][(-89.875):stride:(89.875)][(0.125):stride:(359.875)]
        query = (
            f"sst%5B(last)%5D%5B(0.0)%5D"
            f"%5B(-89.875):{stride}:(89.875)%5D"
            f"%5B(0.125):{stride}:(359.875)%5D"
        )
        url = f"{ERDDAP_BASE}/griddap/{DEFAULT_DATASET}.csv?{query}"
        timeout = httpx.Timeout(30.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text

    def normalize(self, raw: str) -> ConnectorResult:
        points: list[SstPoint] = []
        latest_time: str | None = None

        reader = csv.reader(io.StringIO(raw))
        header: list[str] | None = None
        for i, row in enumerate(reader):
            if i == 0:
                header = row  # time,zlev,latitude,longitude,sst
                continue
            if i == 1:
                # Units row: UTC,m,degrees_north,degrees_east,degree_C
                continue
            if not row or len(row) < 5:
                continue

            time_val, _zlev, lat_str, lon_str, sst_str = row[:5]

            # Land / sea-ice cells are literal "NaN" — drop them.
            if sst_str == "NaN":
                continue
            try:
                lat = float(lat_str)
                lon360 = float(lon_str)
                sst = float(sst_str)
            except ValueError:
                continue

            # Convert ERDDAP 0-360 longitude to -180..180 for the globe.
            lon = lon360 if lon360 <= 180.0 else lon360 - 360.0

            if latest_time is None:
                latest_time = time_val

            points.append(SstPoint(lat=lat, lon=lon, sst_c=sst))

        return ConnectorResult(
            values=points,
            source=self.source,
            source_url=self.source_url,
            cadence=self.cadence,
            tag=self.tag,
            spatial_scope="Global ocean (0.25° native grid, downsampled)",
            license="Public domain (NOAA)",
            notes=[
                f"ERDDAP griddap, latest timestep: {latest_time or 'unknown'}",
                "Land and sea-ice cells filtered out (NaN in source).",
                f"Grid stride: {DEFAULT_STRIDE} (~5° spacing, ~1,700 ocean points).",
                "Longitude converted from 0-360 to -180..180 for map overlay.",
            ],
        )


def summarize(points: list[SstPoint]) -> dict:
    """Summary stats for the response payload (min/max/mean for color ramp)."""
    if not points:
        return {"count": 0, "min_c": None, "max_c": None, "mean_c": None}
    temps = [p.sst_c for p in points]
    return {
        "count": len(points),
        "min_c": round(min(temps), 2),
        "max_c": round(max(temps), 2),
        "mean_c": round(sum(temps) / len(temps), 2),
    }
