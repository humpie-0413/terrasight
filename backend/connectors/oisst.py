"""NOAA OISST daily SST connector.

Source:  https://www.ncei.noaa.gov/products/optimum-interpolation-sst
Cadence: daily
Tag:     observed
"""
from typing import Any

from backend.connectors.base import BaseConnector, ConnectorResult


class OisstConnector(BaseConnector):
    name = "oisst"
    source = "NOAA OISST"
    source_url = "https://www.ncei.noaa.gov/products/optimum-interpolation-sst"
    cadence = "daily"
    tag = "observed"

    async def fetch(self, **params: Any) -> Any:
        raise NotImplementedError

    def normalize(self, raw: Any) -> ConnectorResult:
        raise NotImplementedError
