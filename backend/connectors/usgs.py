"""USGS modernized Water Data API connector.

Source:  https://waterservices.usgs.gov/ (LEGACY — decommission 2027 Q1)
         https://api.waterdata.usgs.gov/ (MODERNIZED — use this)
Cadence: 15-minute interval (continuous)
Tag:     observed (near-real-time for streamflow)

IMPORTANT: Use modernized API only. Legacy WaterServices sunsets 2027 Q1.
Used for: Local Reports Block 4 "Hydrology NRT" (streamflow, stage).
"""
from typing import Any

from backend.connectors.base import BaseConnector, ConnectorResult


class UsgsConnector(BaseConnector):
    name = "usgs"
    source = "USGS Water Data (modernized API)"
    source_url = "https://api.waterdata.usgs.gov/"
    cadence = "15-min (continuous)"
    tag = "near-real-time"

    async def fetch(self, **params: Any) -> Any:
        raise NotImplementedError

    def normalize(self, raw: Any) -> ConnectorResult:
        raise NotImplementedError
