"""NOAA Climate at a Glance connector.

Source:  https://www.ncei.noaa.gov/access/monitoring/climate-at-a-glance/
Cadence: monthly
Tag:     near-real-time (preliminary)
Record start: 1880 (global), city time series for Local Reports.
"""
from typing import Any

from backend.connectors.base import BaseConnector, ConnectorResult


class NoaaCtagConnector(BaseConnector):
    name = "noaa_ctag"
    source = "NOAA Climate at a Glance"
    source_url = "https://www.ncei.noaa.gov/access/monitoring/climate-at-a-glance/"
    cadence = "monthly (preliminary)"
    tag = "near-real-time"

    async def fetch(self, **params: Any) -> Any:
        raise NotImplementedError

    def normalize(self, raw: Any) -> ConnectorResult:
        raise NotImplementedError
