"""NASA FIRMS (Fire Information for Resource Management System) connector.

Source:  https://firms.modaps.eosdis.nasa.gov/
Cadence: near-real-time (~3h latency)
Tag:     observed
Auth:    free MAP_KEY (register at https://firms.modaps.eosdis.nasa.gov/api/map_key/)

=============================================================================
Verified endpoint (2026-04-10 API spike, Agent 4):
  ✅ https://firms.modaps.eosdis.nasa.gov/api/area/csv/{MAP_KEY}/{SOURCE}/{AREA}/{DAYS}

Area format:
  - "world" for global
  - "west,south,east,north" for a bbox
  - 3-letter country code (ISO alpha-3)

DAYS: 1-10 (NRT products like VIIRS_SNPP_NRT).

CSV columns (VIIRS):
  latitude, longitude, bright_ti4, scan, track, acq_date, acq_time,
  satellite, instrument, confidence, version, bright_ti5, frp, daynight

"confidence" for VIIRS is a string enum: "n" (nominal), "l" (low), "h" (high).
"frp" is fire radiative power in MW — our primary "size" signal on the globe.

Rate limit: 5,000 transactions per 10 minutes per MAP_KEY.

For the Earth Now globe we pull 24h of global VIIRS_SNPP_NRT and sample the
top-N points by FRP — 30k+ raw hotspots would blow out the browser and you
can't see individual fires at globe resolution anyway.
=============================================================================
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from typing import Any

import httpx

from backend.connectors.base import BaseConnector, ConnectorResult

FIRMS_BASE = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
DEFAULT_SOURCE = "VIIRS_SNPP_NRT"
DEFAULT_AREA = "world"
DEFAULT_DAYS = 1


@dataclass
class FireHotspot:
    lat: float
    lon: float
    brightness: float   # VIIRS bright_ti4 (K) or MODIS brightness
    frp: float          # fire radiative power (MW)
    confidence: str     # "n"/"l"/"h" (VIIRS) or 0-100 (MODIS)
    acq_date: str       # YYYY-MM-DD
    acq_time: str       # HHMM UTC
    daynight: str       # "D" or "N"


class FirmsConnector(BaseConnector):
    name = "firms"
    source = "NASA FIRMS"
    source_url = "https://firms.modaps.eosdis.nasa.gov/"
    cadence = "NRT ~3h"
    tag = "observed"

    def __init__(self, map_key: str | None) -> None:
        self.map_key = map_key

    async def fetch(
        self,
        source: str = DEFAULT_SOURCE,
        area: str = DEFAULT_AREA,
        days: int = DEFAULT_DAYS,
        **_: Any,
    ) -> str:
        if not self.map_key:
            raise RuntimeError(
                "FIRMS_MAP_KEY is not configured. Register at "
                "https://firms.modaps.eosdis.nasa.gov/api/map_key/ and set "
                "FIRMS_MAP_KEY in backend/.env."
            )
        url = f"{FIRMS_BASE}/{self.map_key}/{source}/{area}/{days}"
        timeout = httpx.Timeout(60.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text

    def normalize(self, raw: str) -> ConnectorResult:
        reader = csv.DictReader(io.StringIO(raw))
        hotspots: list[FireHotspot] = []
        for row in reader:
            try:
                lat = float(row["latitude"])
                lon = float(row["longitude"])
                frp = float(row.get("frp") or 0.0)
                brightness = float(
                    row.get("bright_ti4") or row.get("brightness") or 0.0
                )
            except (ValueError, KeyError):
                continue
            hotspots.append(
                FireHotspot(
                    lat=lat,
                    lon=lon,
                    brightness=brightness,
                    frp=frp,
                    confidence=str(row.get("confidence", "")),
                    acq_date=str(row.get("acq_date", "")),
                    acq_time=str(row.get("acq_time", "")),
                    daynight=str(row.get("daynight", "")),
                )
            )
        return ConnectorResult(
            values=hotspots,
            source=self.source,
            source_url=self.source_url,
            cadence=self.cadence,
            tag=self.tag,
            spatial_scope="Global",
            license="Public domain (NASA FIRMS)",
            notes=[
                "VIIRS_SNPP_NRT active fire hotspots, previous 24h.",
                "Confidence field is enum (n/l/h) for VIIRS, 0-100 for MODIS.",
                "Globe shows top-N by FRP — full feed is too dense at globe scale.",
            ],
        )


def top_by_frp(hotspots: list[FireHotspot], limit: int = 1500) -> list[FireHotspot]:
    """Return the top-N hotspots by fire radiative power, descending."""
    return sorted(hotspots, key=lambda h: h.frp, reverse=True)[:limit]
