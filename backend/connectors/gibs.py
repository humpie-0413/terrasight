"""NASA GIBS (Global Imagery Browse Services) WMTS tile connector.

WMTS base: https://gibs.earthdata.nasa.gov/wmts/epsg{EPSG}/best/
Docs:      https://nasa-gibs.github.io/gibs-api-docs/
Cadence:   varies per layer
Tag:       observed / NRT
Auth:      none (public, CDN-backed)

=============================================================================
⚠️ There is NO layer literally named "Natural Earth" in GIBS
(verified 2026-04-10 API spike, Agent 4).

We use `BlueMarble_ShadedRelief_Bathymetry` as the globe base imagery and
keep the UI label as "Natural Earth" per the CLAUDE.md home wireframe.
=============================================================================

Tile URL template (REST):
    {WMTS_BASE}/{LayerIdentifier}/default/{Time}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.{ext}

Notable layers:
- BlueMarble_ShadedRelief_Bathymetry     — base imagery (UI label: "Natural Earth")
- MODIS_Terra_CorrectedReflectance_TrueColor — daily true color
- GetCapabilities: {WMTS_BASE}/wmts.cgi?request=GetCapabilities
"""
from typing import Any

from backend.connectors.base import BaseConnector, ConnectorResult

WMTS_BASE_4326 = "https://gibs.earthdata.nasa.gov/wmts/epsg4326/best"
WMTS_BASE_3857 = "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best"

# Default base imagery layer. UI label is "Natural Earth" per CLAUDE.md,
# but no GIBS layer is literally named that — Blue Marble is the closest.
DEFAULT_BASE_LAYER = "BlueMarble_ShadedRelief_Bathymetry"
DEFAULT_BASE_LAYER_UI_LABEL = "Natural Earth"


class GibsConnector(BaseConnector):
    name = "gibs"
    source = "NASA GIBS"
    source_url = WMTS_BASE_4326
    cadence = "varies"
    tag = "observed"

    async def fetch(self, **params: Any) -> Any:
        raise NotImplementedError

    def normalize(self, raw: Any) -> ConnectorResult:
        raise NotImplementedError
