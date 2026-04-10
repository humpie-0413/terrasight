"""EPA ECHO (Enforcement and Compliance History Online) connector.

REST services base: http://ofmpub.epa.gov/echo/
Docs:               https://echo.epa.gov/tools/web-services
Cadence:            live feed
Tag:                regulatory (NOT environmental exposure)
Geo:                facility coordinates → aggregated to CBSA

=============================================================================
⚠️ HTTP ONLY — NOT HTTPS.
2026-04-10 API spike (Agent 4) verified: https://ofmpub.epa.gov → 404.
Use http://ofmpub.epa.gov/echo/... exactly. Do not upgrade the scheme.
=============================================================================

Verified endpoints (2026-04-10 spike):
- echo13_rest_services.get_facilities        — facility search
- echo13_rest_services.get_qid               — pagination iterator (QID ~30m TTL)
- echo13_rest_services.get_facility_info     — facility detail
- echo13_rest_services.get_download          — CSV export
- echo13_rest_services.get_enforcement_case_search
Bbox params: p_c1lon, p_c1lat, p_c2lon, p_c2lat.

MANDATORY disclaimer wherever this data is shown:
"Regulatory compliance ≠ environmental exposure or health risk."
"""
from typing import Any

from backend.connectors.base import BaseConnector, ConnectorResult

# NOTE: HTTP, not HTTPS. HTTPS returns 404. See module docstring.
BASE_URL = "http://ofmpub.epa.gov"


class EchoConnector(BaseConnector):
    name = "echo"
    source = "EPA ECHO"
    source_url = BASE_URL
    cadence = "live feed"
    tag = "observed"  # enforcement records are observed facts

    async def fetch(self, **params: Any) -> Any:
        raise NotImplementedError

    def normalize(self, raw: Any) -> ConnectorResult:
        raise NotImplementedError
