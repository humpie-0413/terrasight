"""U.S. Climate Normals 1991-2020 connector.

Source:  https://www.ncei.noaa.gov/products/land-based-station/us-climate-normals
Cadence: 30-year baseline (static reference)
Tag:     derived (30-yr statistical summary)

Used for: Local Reports Block 2 baseline comparison against monthly CtaG city series.
"""
from typing import Any

from backend.connectors.base import BaseConnector, ConnectorResult


class ClimateNormalsConnector(BaseConnector):
    name = "climate_normals"
    source = "U.S. Climate Normals 1991-2020"
    source_url = "https://www.ncei.noaa.gov/products/land-based-station/us-climate-normals"
    cadence = "30-yr baseline"
    tag = "derived"

    async def fetch(self, **params: Any) -> Any:
        raise NotImplementedError

    def normalize(self, raw: Any) -> ConnectorResult:
        raise NotImplementedError
