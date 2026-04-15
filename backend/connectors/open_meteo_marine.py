"""Open-Meteo Marine API connector — global ocean current velocity & direction.

Source:  https://open-meteo.com/en/docs/marine-weather-api
Data:    ERA5-Ocean / ECMWF marine models
Cadence: Hourly updates
Tag:     forecast (model output)
Auth:    None required (free tier, non-commercial)

=============================================================================
Implementation notes (verified 2026-04-16):

- Same POST-batch pattern as the Weather and Air Quality connectors,
  but uses `marine-api.open-meteo.com` instead of `api.open-meteo.com`.
- `current=ocean_current_velocity,ocean_current_direction` returns the
  latest values for each requested point.
- ocean_current_velocity is in km/h; ocean_current_direction is degrees
  (0 = north, 90 = east).
- Grid is restricted to -80..+80 latitude (no data at poles) and covers
  all longitudes.  Land points return null and are filtered out.
- POST supports up to ~1000 lat/lon pairs per request; we use 900.

LANDMINES:
- Same rate limit as other Open-Meteo APIs — add delays between batches.
- Land grid points return null for both variables — must skip them.
- Direction convention is oceanographic ("going to"), not meteorological
  ("coming from").  Frontend should not flip the direction.
=============================================================================
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import httpx

from backend.connectors.base import BaseConnector, ConnectorResult

MARINE_API_URL = "https://marine-api.open-meteo.com/v1/marine"

GRID_LAT_MIN = -80.0
GRID_LAT_MAX = 80.0
GRID_LAT_STEP = 5.0
GRID_LON_STEP = 5.0
BATCH_SIZE = 900


@dataclass
class OceanCurrentPoint:
    lat: float
    lon: float
    velocity_kmh: float
    direction_deg: float  # degrees, 0=north, 90=east


def _build_ocean_grid() -> list[tuple[float, float]]:
    """Build a lat/lon grid at 5° spacing over ocean-plausible latitudes."""
    points: list[tuple[float, float]] = []
    lat = GRID_LAT_MIN
    while lat <= GRID_LAT_MAX:
        lon = -180.0
        while lon < 180.0:
            points.append((lat, lon))
            lon += GRID_LON_STEP
        lat += GRID_LAT_STEP
    return points


class OpenMeteoMarineConnector(BaseConnector):
    """Connector for Open-Meteo Marine API — ocean currents."""

    name = "open_meteo_marine"
    source = "Open-Meteo Marine (ERA5-Ocean/ECMWF)"
    source_url = "https://open-meteo.com/en/docs/marine-weather-api"
    cadence = "hourly"
    tag = "forecast"

    async def fetch(self, **_: Any) -> list[dict[str, Any]]:
        """Fetch current ocean_current_velocity and ocean_current_direction
        on a global 5° ocean grid.
        """
        grid = _build_ocean_grid()
        all_responses: list[dict[str, Any]] = []

        timeout = httpx.Timeout(60.0, connect=15.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            batches = [grid[i : i + BATCH_SIZE] for i in range(0, len(grid), BATCH_SIZE)]
            for batch_idx, batch in enumerate(batches):
                lats = [p[0] for p in batch]
                lons = [p[1] for p in batch]

                payload = {
                    "latitude": lats,
                    "longitude": lons,
                    "current": ["ocean_current_velocity", "ocean_current_direction"],
                    "forecast_days": 0,
                }

                for attempt in range(3):
                    resp = await client.post(MARINE_API_URL, json=payload)
                    if resp.status_code == 429:
                        wait = 5 * (2 ** attempt)  # 5, 10, 20s
                        await asyncio.sleep(wait)
                        continue
                    resp.raise_for_status()
                    break
                else:
                    resp.raise_for_status()

                data = resp.json()
                if isinstance(data, list):
                    all_responses.extend(data)
                else:
                    all_responses.append(data)

                if batch_idx < len(batches) - 1:
                    await asyncio.sleep(4)

        return all_responses

    def normalize(self, raw: list[dict[str, Any]], **_: Any) -> ConnectorResult:
        """Parse API responses into OceanCurrentPoint list.

        Land points (null velocity/direction) are dropped.
        """
        points: list[OceanCurrentPoint] = []

        for entry in raw:
            lat = entry.get("latitude")
            lon = entry.get("longitude")
            current = entry.get("current", {})
            velocity = current.get("ocean_current_velocity")
            direction = current.get("ocean_current_direction")

            if lat is None or lon is None:
                continue
            if velocity is None or direction is None:
                continue

            points.append(
                OceanCurrentPoint(
                    lat=float(lat),
                    lon=float(lon),
                    velocity_kmh=float(velocity),
                    direction_deg=float(direction),
                )
            )

        return ConnectorResult(
            values=points,
            source=self.source,
            source_url=self.source_url,
            cadence=self.cadence,
            tag=self.tag,
            spatial_scope="Global ocean grid (-80° to +80° lat, 5° spacing)",
            license="CC-BY 4.0 (Open-Meteo)",
            notes=[
                f"Global 5° ocean grid: {len(points)} points with valid current data.",
                "Land points filtered out (null values).",
            ],
        )
