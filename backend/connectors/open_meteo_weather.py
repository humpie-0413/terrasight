"""Open-Meteo Weather API connector — global temperature, precipitation, wind grids.

Source:  https://open-meteo.com/en/docs
Data:    GFS/ECMWF/ICON models (0.25° resolution)
Cadence: Hourly updates
Tag:     forecast (model output)
Auth:    None required (free tier, non-commercial)

=============================================================================
Implementation notes (verified 2026-04-15):

- Same API pattern as Air Quality but different base URL.
- Point-based: must enumerate lat/lon pairs explicitly.
- POST up to ~1000 points, GET ~500.
- `current=temperature_2m,precipitation` returns latest values.
- Rate limit: ~15-20 requests/minute, hourly cap exists.
- `models=gfs_seamless` for global GFS model.

LANDMINES:
- Same rate limit issues as air quality API — use delays between batches
- Precipitation can be 0 for most of the globe at any given time
- Temperature uses °C by default (temperature_unit=celsius)
=============================================================================
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import httpx

from backend.connectors.base import BaseConnector, ConnectorResult

WEATHER_API_URL = "https://api.open-meteo.com/v1/forecast"

GRID_LAT_STEP = 5.0
GRID_LON_STEP = 5.0
BATCH_SIZE = 900


@dataclass
class WeatherPoint:
    lat: float
    lon: float
    value: float


def _build_global_grid() -> list[tuple[float, float]]:
    """Build a global lat/lon grid at 5° spacing."""
    points: list[tuple[float, float]] = []
    lat = -90.0
    while lat <= 90.0:
        lon = -180.0
        while lon < 180.0:
            points.append((lat, lon))
            lon += GRID_LON_STEP
        lat += GRID_LAT_STEP
    return points


class OpenMeteoWeatherConnector(BaseConnector):
    """Connector for Open-Meteo Weather Forecast API."""

    name = "open_meteo_weather"
    source = "Open-Meteo Weather (GFS/ECMWF)"
    source_url = "https://open-meteo.com/en/docs"
    cadence = "hourly"
    tag = "forecast"

    async def fetch(
        self,
        variable: str = "temperature_2m",
        **_: Any,
    ) -> list[dict[str, Any]]:
        """Fetch current values for the given variable on a global 5° grid.

        Args:
            variable: Open-Meteo parameter name
                (temperature_2m, precipitation, wind_speed_10m, etc.)
        """
        grid = _build_global_grid()
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
                    "current": [variable],
                    "forecast_days": 0,
                }

                for attempt in range(4):
                    resp = await client.post(WEATHER_API_URL, json=payload)
                    if resp.status_code == 429:
                        wait = 10 * (2 ** attempt)
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
                    await asyncio.sleep(2)

        return all_responses

    def normalize(
        self,
        raw: list[dict[str, Any]],
        variable: str = "temperature_2m",
    ) -> ConnectorResult:
        """Parse API responses into WeatherPoint list."""
        points: list[WeatherPoint] = []

        for entry in raw:
            lat = entry.get("latitude")
            lon = entry.get("longitude")
            current = entry.get("current", {})
            value = current.get(variable)

            if lat is None or lon is None or value is None:
                continue

            points.append(WeatherPoint(lat=float(lat), lon=float(lon), value=float(value)))

        return ConnectorResult(
            values=points,
            source=self.source,
            source_url=self.source_url,
            cadence=self.cadence,
            tag=self.tag,
            spatial_scope="Global (GFS/ECMWF model, sampled at 5° grid)",
            license="CC-BY 4.0 (Open-Meteo)",
            notes=[
                f"Global 5° grid: {len(points)} points with valid {variable} values.",
            ],
        )
