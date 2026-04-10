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

Response format: GeoJSON (default). One feature per observation (not grouped
per time series) — differs from legacy WaterML2; normalize in fetch().

Used for: Local Reports Block 4 "Hydrology NRT" (streamflow, stage).
"""
from typing import Any

from backend.connectors.base import BaseConnector, ConnectorResult

BASE_URL = "https://api.waterdata.usgs.gov/ogcapi/v0"


class UsgsConnector(BaseConnector):
    name = "usgs"
    source = "USGS Water Data (modernized API)"
    source_url = BASE_URL
    cadence = "15-min (continuous)"
    tag = "near-real-time"

    async def fetch(self, **params: Any) -> Any:
        raise NotImplementedError

    def normalize(self, raw: Any) -> ConnectorResult:
        raise NotImplementedError
