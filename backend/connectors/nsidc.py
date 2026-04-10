"""NSIDC Sea Ice Index connector.

Source:  https://nsidc.org/data/seaice_index
Cadence: daily (5-day running mean)
Tag:     observed
Record start: 1979
"""
from typing import Any

from backend.connectors.base import BaseConnector, ConnectorResult


class NsidcConnector(BaseConnector):
    name = "nsidc"
    source = "NSIDC Sea Ice Index"
    source_url = "https://nsidc.org/data/seaice_index"
    cadence = "daily (5-day running mean)"
    tag = "observed"

    async def fetch(self, **params: Any) -> Any:
        raise NotImplementedError

    def normalize(self, raw: Any) -> ConnectorResult:
        raise NotImplementedError
