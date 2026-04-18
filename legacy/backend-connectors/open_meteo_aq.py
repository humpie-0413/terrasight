"""Open-Meteo Air Quality API connector — global PM2.5, NO₂, O₃ grids.

Source:  https://open-meteo.com/en/docs/air-quality-api
Data:    CAMS Global (0.4° resolution, ~45km)
Cadence: Hourly updates
Tag:     forecast (CAMS model output)
Auth:    None required (free tier, non-commercial)

=============================================================================
Implementation notes (verified 2026-04-15):

- API is point-based: must enumerate lat/lon pairs explicitly.
- POST supports up to ~1000 points per request (413 above that).
- GET supports ~500 points before URI too long (414).
- Rate limit: ~15-20 requests/minute on free tier.
- `current=pm2_5` with `forecast_days=0` returns latest value.
- Multi-point response is a JSON array of objects.
- Latitude/longitude arrays must be same length (1:1 pairing).
- For a grid, must pre-compute cross-product of lat/lon ranges.

LANDMINES:
- latitude and longitude params must have same element count or 400 error
- ammonia is Europe-only (null globally)
- Request count per minute is limited, not point count per request
- POST Content-Type must be application/json (not form-encoded)
=============================================================================
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import httpx

from backend.connectors.base import BaseConnector, ConnectorResult

AQ_API_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

# Global grid at 5° spacing: 37 latitudes × 72 longitudes = 2,664 points
# Split into batches of ~900 for POST requests
GRID_LAT_STEP = 5.0
GRID_LON_STEP = 5.0
BATCH_SIZE = 900


@dataclass
class AqPoint:
    lat: float
    lon: float
    pm25: float


def _build_global_grid() -> list[tuple[float, float]]:
    """Build a global lat/lon grid at GRID_LAT_STEP/GRID_LON_STEP spacing."""
    points: list[tuple[float, float]] = []
    lat = -90.0
    while lat <= 90.0:
        lon = -180.0
        while lon < 180.0:
            points.append((lat, lon))
            lon += GRID_LON_STEP
        lat += GRID_LAT_STEP
    return points


class OpenMeteoAqConnector(BaseConnector):
    """Connector for Open-Meteo Air Quality API (CAMS global)."""

    name = "open_meteo_aq"
    source = "Open-Meteo Air Quality (CAMS Global)"
    source_url = "https://open-meteo.com/en/docs/air-quality-api"
    cadence = "hourly"
    tag = "forecast"

    async def fetch(
        self,
        variable: str = "pm2_5",
        **_: Any,
    ) -> list[dict[str, Any]]:
        """Fetch current values for the given variable on a global 5° grid.

        Args:
            variable: Open-Meteo parameter name (pm2_5, nitrogen_dioxide, ozone, etc.)

        Returns:
            List of response dicts from the API (one per batch).
        """
        grid = _build_global_grid()
        all_responses: list[dict[str, Any]] = []

        timeout = httpx.Timeout(60.0, connect=15.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            # Split into batches
            batches = [grid[i : i + BATCH_SIZE] for i in range(0, len(grid), BATCH_SIZE)]
            for batch_idx, batch in enumerate(batches):
                lats = [p[0] for p in batch]
                lons = [p[1] for p in batch]

                payload = {
                    "latitude": lats,
                    "longitude": lons,
                    "current": [variable],
                    "forecast_days": 0,
                    "domains": "cams_global",
                }

                # Retry with backoff on 429 rate limit
                for attempt in range(3):
                    resp = await client.post(AQ_API_URL, json=payload)
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

                # Delay between batches to stay within rate limits
                if batch_idx < len(batches) - 1:
                    await asyncio.sleep(4)

        return all_responses

    def normalize(
        self,
        raw: list[dict[str, Any]],
        variable: str = "pm2_5",
    ) -> ConnectorResult:
        """Parse API responses into AqPoint list."""
        points: list[AqPoint] = []

        for entry in raw:
            lat = entry.get("latitude")
            lon = entry.get("longitude")
            current = entry.get("current", {})
            value = current.get(variable)

            if lat is None or lon is None or value is None:
                continue

            points.append(AqPoint(lat=float(lat), lon=float(lon), pm25=float(value)))

        return ConnectorResult(
            values=points,
            source=self.source,
            source_url=self.source_url,
            cadence=self.cadence,
            tag=self.tag,
            spatial_scope="Global (CAMS 0.4° model, sampled at 5° grid)",
            license="CC-BY 4.0 (Open-Meteo / Copernicus CAMS)",
            notes=[
                f"Global 5° grid: {len(points)} points with valid {variable} values.",
                "Data from CAMS Global atmospheric composition model.",
                "Resolution: 0.4° native, queried at 5° intervals.",
            ],
        )
