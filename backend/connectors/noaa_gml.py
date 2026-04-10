"""NOAA GML Mauna Loa CO2 connector.

Source:  https://gml.noaa.gov/ccgg/trends/data.html
Cadence: daily + monthly
Tag:     observed
Record start: 1958
"""
from typing import Any

from backend.connectors.base import BaseConnector, ConnectorResult


class NoaaGmlConnector(BaseConnector):
    name = "noaa_gml"
    source = "NOAA GML Mauna Loa"
    source_url = "https://gml.noaa.gov/ccgg/trends/"
    cadence = "daily + monthly"
    tag = "observed"

    async def fetch(self, **params: Any) -> Any:
        # TODO: GET co2_trend_gl.txt / co2_mm_mlo.txt
        raise NotImplementedError

    def normalize(self, raw: Any) -> ConnectorResult:
        raise NotImplementedError
