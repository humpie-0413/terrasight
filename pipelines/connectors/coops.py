"""NOAA CO-OPS Tides & Currents connector — coastal water levels and temps.

Endpoints:
  Station list: https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations.json
  Data:         https://api.tidesandcurrents.noaa.gov/api/prod/datagetter
Docs:     https://tidesandcurrents.noaa.gov/api/
Cadence:  6-minute intervals
Tag:      observed
Auth:     none (application= param is for identification only)
Geo:      U.S. coastlines and territories

=============================================================================
Implementation notes:

Two-step fetch:
  1. GET stations.json from mdapi — returns ALL stations with lat/lon.
     Filter client-side by bounding box.
  2. For each station (up to `limit`), GET datagetter with
     date=latest&product=water_level and then water_temperature.
     Use asyncio.gather for parallelism.

Response JSON structure for datagetter:
  {"metadata": {...}, "data": [{"t": "2026-04-12 15:00", "v": "1.234",
   "s": "0.003", "f": "0,0,0,0", "q": "v"}]}
  The value "v" is a STRING — convert to float.
  If "v" is an empty string, the data is missing.

Landmines:
  - The mdapi stations endpoint sometimes returns stations with lat=0,
    lng=0. These are bogus — filter them out.
  - Some stations are decommissioned and have no recent data. If the
    latest response returns an empty "data" array (or no "data" key),
    skip the station gracefully.
  - water_temperature product uses the same response shape but may not
    be available at all stations. Treat missing temp as None.
=============================================================================
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import httpx

from backend.connectors.base import BaseConnector, ConnectorResult

STATIONS_URL = "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations.json"
DATAGETTER_URL = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"


@dataclass
class TideStation:
    station_id: str
    name: str
    lat: float
    lon: float
    state: str
    water_level_ft: float | None
    water_temp_f: float | None
    timestamp: str


class CoopsConnector(BaseConnector):
    name = "coops"
    source = "NOAA CO-OPS"
    source_url = "https://tidesandcurrents.noaa.gov/"
    cadence = "6-minute intervals"
    tag = "observed"

    async def fetch(
        self,
        west: float = -180.0,
        south: float = -90.0,
        east: float = 180.0,
        north: float = 90.0,
        limit: int = 20,
        **_: Any,
    ) -> dict[str, Any]:
        """Fetch station list filtered by bbox, then latest water level + temp."""
        timeout = httpx.Timeout(60.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            # Step 1: Get all stations
            resp = await client.get(STATIONS_URL)
            resp.raise_for_status()
            stations_data = resp.json()

            all_stations = stations_data.get("stations") or []

            # Filter by bbox, excluding bogus lat=0/lng=0 entries
            bbox_stations: list[dict[str, Any]] = []
            for s in all_stations:
                lat = s.get("lat", 0)
                lng = s.get("lng", 0)
                if lat == 0 and lng == 0:
                    continue
                if south <= lat <= north and west <= lng <= east:
                    bbox_stations.append(s)
                if len(bbox_stations) >= limit:
                    break

            # Step 2: Fetch latest water_level and water_temperature per station
            async def _fetch_station(station: dict[str, Any]) -> dict[str, Any] | None:
                station_id = str(station.get("id", ""))
                base_params = {
                    "station": station_id,
                    "date": "latest",
                    "datum": "MLLW",
                    "units": "english",
                    "time_zone": "gmt",
                    "format": "json",
                    "application": "TerraSight",
                }
                water_level: float | None = None
                water_temp: float | None = None
                timestamp = ""

                # Fetch water level
                try:
                    wl_params = {**base_params, "product": "water_level"}
                    wl_resp = await client.get(DATAGETTER_URL, params=wl_params)
                    wl_resp.raise_for_status()
                    wl_json = wl_resp.json()
                    wl_data = wl_json.get("data") or []
                    if wl_data:
                        v = wl_data[0].get("v", "")
                        if v != "":
                            water_level = float(v)
                            timestamp = wl_data[0].get("t", "")
                    else:
                        # No recent data — likely decommissioned station
                        return None
                except Exception:
                    # If water level fetch fails entirely, skip station
                    return None

                # Fetch water temperature (optional — not all stations have it)
                try:
                    wt_params = {**base_params, "product": "water_temperature"}
                    wt_resp = await client.get(DATAGETTER_URL, params=wt_params)
                    wt_resp.raise_for_status()
                    wt_json = wt_resp.json()
                    wt_data = wt_json.get("data") or []
                    if wt_data:
                        v = wt_data[0].get("v", "")
                        if v != "":
                            water_temp = float(v)
                except Exception:
                    pass  # Temperature not available at this station — fine

                return {
                    "station_id": station_id,
                    "name": station.get("name", ""),
                    "lat": station.get("lat", 0.0),
                    "lon": station.get("lng", 0.0),
                    "state": station.get("state", ""),
                    "water_level_ft": water_level,
                    "water_temp_f": water_temp,
                    "timestamp": timestamp,
                }

            results = await asyncio.gather(
                *[_fetch_station(s) for s in bbox_stations],
                return_exceptions=True,
            )

            # Filter out None / exceptions
            stations_out = [
                r for r in results if isinstance(r, dict)
            ]

            return {"stations": stations_out}

    def normalize(self, raw: dict[str, Any]) -> ConnectorResult:
        stations_raw = raw.get("stations") or []
        stations: list[TideStation] = []
        for s in stations_raw:
            stations.append(
                TideStation(
                    station_id=s["station_id"],
                    name=s["name"],
                    lat=float(s["lat"]),
                    lon=float(s["lon"]),
                    state=s.get("state", ""),
                    water_level_ft=s.get("water_level_ft"),
                    water_temp_f=s.get("water_temp_f"),
                    timestamp=s.get("timestamp", ""),
                )
            )
        return ConnectorResult(
            values=stations,
            source=self.source,
            source_url=self.source_url,
            cadence=self.cadence,
            tag=self.tag,
            spatial_scope="U.S. coastlines and territories",
            license="Public domain (NOAA)",
            notes=[
                "Two-step: station list from mdapi, then datagetter per station.",
                "water_level_ft is relative to MLLW datum in English units (feet).",
                "water_temp_f may be None if the station does not report temperature.",
                "Stations with lat=0/lng=0 are filtered out (bogus coordinates).",
                "Decommissioned stations with no recent data are skipped.",
            ],
        )
