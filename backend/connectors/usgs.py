"""USGS modernized Water Data API connector.

Source:  https://api.waterdata.usgs.gov/ (MODERNIZED, OGC API Features)
Legacy:  https://waterservices.usgs.gov/ (decommission 2027 Q1 — DO NOT USE)
Cadence: 15-minute interval (continuous)
Tag:     observed / near-real-time (for streamflow)

OGC API Features collections (verified 2026-04-10 spike):
- /collections/continuous/items     — 15-min instantaneous values (3-yr rolling window)
- /collections/daily/items          — daily rollups
- /collections/monitoring-locations/items
- /collections/time-series-metadata/items

Response format: GeoJSON. One Feature per (site, day, statistic) observation;
multiple statistics (mean=00003, max=00001, min=00002) can appear for the same
site/day, and features are NOT returned sorted by time — we sort and dedupe
per monitoring_location_id in normalize().

Observed feature.properties keys (daily collection, 2026-04-10 spike):
  id, time_series_id, monitoring_location_id, parameter_code, statistic_id,
  time, value (string), unit_of_measure, approval_status, qualifier,
  last_modified
Note: the feature itself does NOT carry a site_name — only the ID such as
"USGS-08067700". A separate lookup against /collections/monitoring-locations
would be required for a human-readable name; we fall back to the ID for now.

Used for: Local Reports Block 4 "Hydrology NRT" (streamflow).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from backend.connectors.base import BaseConnector, ConnectorResult

BASE_URL = "https://api.waterdata.usgs.gov/ogcapi/v0"
DAILY_ITEMS_PATH = "/collections/daily/items"
# 00060 = discharge, cubic feet per second (streamflow)
PARAMETER_CODE_DISCHARGE = "00060"


@dataclass
class StreamflowReading:
    monitoring_location_id: str  # USGS site ID (e.g. "USGS-08076000")
    site_name: str
    lat: float
    lon: float
    datetime_utc: str
    value_cfs: float  # discharge in cubic feet per second
    parameter_code: str  # "00060"


@dataclass
class UsgsWaterSummary:
    site_count: int
    latest_readings: list[StreamflowReading]  # one per site, most recent
    bbox: tuple[float, float, float, float]


class UsgsConnector(BaseConnector):
    name = "usgs"
    source = "USGS Water Data (modernized API)"
    source_url = BASE_URL
    cadence = "15-min (continuous)"
    tag = "near-real-time"

    async def fetch(
        self,
        west: float,
        south: float,
        east: float,
        north: float,
        days: int = 7,
        **_: Any,
    ) -> dict[str, Any]:
        # USGS OGC API accepts an RFC 3339 interval: "<start>/<end>".
        end = datetime.now(tz=timezone.utc)
        start = end - timedelta(days=days)
        datetime_range = (
            f"{start.strftime('%Y-%m-%dT%H:%M:%SZ')}/"
            f"{end.strftime('%Y-%m-%dT%H:%M:%SZ')}"
        )

        params = {
            "bbox": f"{west},{south},{east},{north}",
            "parameter_code": PARAMETER_CODE_DISCHARGE,
            "datetime": datetime_range,
            "limit": 100,
            "f": "json",
        }

        timeout = httpx.Timeout(30.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(
                BASE_URL + DAILY_ITEMS_PATH, params=params
            )
            response.raise_for_status()
            payload = response.json()

        # Stash the bbox on the raw payload so normalize() can surface it
        # without having to repeat the request arguments.
        payload["_bbox"] = (
            float(west),
            float(south),
            float(east),
            float(north),
        )
        return payload

    def normalize(self, raw: dict[str, Any]) -> ConnectorResult:
        features = raw.get("features") or []
        bbox: tuple[float, float, float, float] = raw.get("_bbox") or (
            0.0,
            0.0,
            0.0,
            0.0,
        )

        # Group by site, keep the most recent reading per site.
        latest_by_site: dict[str, StreamflowReading] = {}

        for feat in features:
            props = feat.get("properties") or {}
            geom = feat.get("geometry") or {}
            coords = geom.get("coordinates") or []

            site_id = str(props.get("monitoring_location_id") or "").strip()
            if not site_id:
                continue

            time_str = str(props.get("time") or "").strip()
            if not time_str:
                continue

            try:
                value_cfs = float(props.get("value"))
            except (TypeError, ValueError):
                continue

            try:
                lon = float(coords[0])
                lat = float(coords[1])
            except (TypeError, ValueError, IndexError):
                continue

            parameter_code = str(
                props.get("parameter_code") or PARAMETER_CODE_DISCHARGE
            )

            # Feature payload has no human-readable site name — fall back to
            # the USGS site ID. A monitoring-locations lookup could enrich
            # this later.
            site_name = site_id

            reading = StreamflowReading(
                monitoring_location_id=site_id,
                site_name=site_name,
                lat=lat,
                lon=lon,
                datetime_utc=time_str,
                value_cfs=value_cfs,
                parameter_code=parameter_code,
            )

            existing = latest_by_site.get(site_id)
            if existing is None or reading.datetime_utc > existing.datetime_utc:
                latest_by_site[site_id] = reading

        latest_readings = sorted(
            latest_by_site.values(),
            key=lambda r: r.datetime_utc,
            reverse=True,
        )

        summary = UsgsWaterSummary(
            site_count=len(latest_readings),
            latest_readings=latest_readings,
            bbox=bbox,
        )

        return ConnectorResult(
            values=summary,
            source=self.source,
            source_url=self.source_url,
            cadence=self.cadence,
            tag=self.tag,
            spatial_scope="Monitoring stations within CBSA bounding box",
            license="Public domain (USGS)",
            notes=[
                "Near-real-time streamflow (15-minute instantaneous).",
                "Continuous hydrologic measurement, distinct from WQP "
                "discrete samples.",
                "Daily-rollup collection; multiple statistics (mean/min/max) "
                "may coexist per site/day — we retain the most recent "
                "observation per monitoring location.",
                "Feature payload omits site_name; monitoring_location_id "
                "(e.g. 'USGS-08076000') is used as the display label.",
            ],
        )
