"""NASA GIBS (Global Imagery Browse Services) WMTS tile connector.

WMTS base: https://gibs.earthdata.nasa.gov/wmts/epsg{EPSG}/best/
Docs:      https://nasa-gibs.github.io/gibs-api-docs/
Cadence:   varies per layer
Tag:       observed / NRT
Auth:      none (public, CDN-backed)

=============================================================================
WARNING: There is NO layer literally named "Natural Earth" in GIBS
(verified 2026-04-10 API spike, Agent 4).

We use `BlueMarble_ShadedRelief_Bathymetry` as the globe base imagery and
keep the UI label as "Natural Earth" per the CLAUDE.md home wireframe.
=============================================================================

Tile URL template (REST):
    {WMTS_BASE}/{LayerIdentifier}/default/{Time}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.{ext}

Notable layers:
- BlueMarble_ShadedRelief_Bathymetry     -- base imagery (UI label: "Natural Earth")
- MODIS_Terra_CorrectedReflectance_TrueColor -- daily true color
- GetCapabilities: {WMTS_BASE}/wmts.cgi?request=GetCapabilities

=============================================================================
LAYER CATALOG verification log (2026-04-11, GetCapabilities + live tile probes):
  BlueMarble_ShadedRelief_Bathymetry     -- 500m / image/jpeg / static (no Time dim)
  MODIS_Terra_Aerosol                    -- 2km  / image/png  / daily   (HTTP 200 verified)
  MERRA2_Dust_Surface_Mass_Concentration_PM25_Monthly -- 2km / image/png / monthly
      NOTE: dust-fraction only, not total PM2.5. Time format must be YYYY-MM-DD.
  OCO-2_Carbon_Dioxide_Total_Column_Average -- 500m / image/png / daily (HTTP 200 verified)
  MODIS_Combined_Flood_2-Day             -- 250m / image/png  / daily   (HTTP 200 verified)
  TROPOMI_L2_Nitrogen_Dioxide_Tropospheric_Column -- 2km / image/png / daily
      (TROPOMI CH4 / methane is NOT available in GIBS as of 2026-04-11 GetCapabilities)
=============================================================================
"""
from typing import Any

from backend.connectors.base import BaseConnector, ConnectorResult

WMTS_BASE_4326 = "https://gibs.earthdata.nasa.gov/wmts/epsg4326/best"
WMTS_BASE_3857 = "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best"

DEFAULT_BASE_LAYER = "BlueMarble_ShadedRelief_Bathymetry"
DEFAULT_BASE_LAYER_UI_LABEL = "Natural Earth"

# ---------------------------------------------------------------------------
# LAYER_CATALOG
#
# Verified against GIBS WMTS GetCapabilities (epsg4326/best) on 2026-04-11.
# TileMatrixSet and Format values come directly from the XML; availability
# was additionally confirmed by live HTTP-200 tile probes where noted.
#
# Tile URL pattern (REST):
#   {WMTS_BASE_4326}/{id}/default/{Time}/{tile_matrix_set}/{z}/{y}/{x}.{ext}
#
# For static layers (temporal=False) omit the {Time} segment.
# ---------------------------------------------------------------------------
LAYER_CATALOG: dict[str, dict] = {
    "blue_marble": {
        "id": "BlueMarble_ShadedRelief_Bathymetry",
        "title": "Blue Marble Shaded Relief and Bathymetry",
        "description": (
            "NASA Blue Marble composite (MODIS) with shaded relief and ocean "
            "bathymetry. Used as the globe base imagery; UI label: 'Natural Earth'."
        ),
        "tag": "observed",
        "cadence": "static",
        "tile_matrix_set": "500m",
        "format": "image/jpeg",
        "temporal": False,
        "spatial_scope": "Global",
        "notes": [
            "No Time dimension -- this is a static basemap composite.",
            "UI label 'Natural Earth' per design spec; no GIBS layer is literally "
            "named 'Natural Earth' (verified 2026-04-10).",
        ],
        "available": True,
        "unavailable_reason": None,
    },
    "modis_aod": {
        "id": "MODIS_Terra_Aerosol",
        "title": "Dark Target Aerosol Optical Depth (Land and Ocean, MODIS, Terra)",
        "description": (
            "Daily aerosol optical depth at 550 nm from MODIS Terra Dark Target "
            "algorithm, covering land and ocean. Proxy for aerosol loading / air "
            "quality."
        ),
        "tag": "observed",
        "cadence": "daily",
        "tile_matrix_set": "2km",
        "format": "image/png",
        "temporal": True,
        "spatial_scope": "Global",
        "notes": [
            "Available from 2000-02-24 to present.",
            "HTTP 200 tile probe confirmed 2026-04-11.",
        ],
        "available": True,
        "unavailable_reason": None,
    },
    "pm25": {
        "id": "MERRA2_Dust_Surface_Mass_Concentration_PM25_Monthly",
        "title": "Dust Surface Mass Concentration (Monthly, PM2.5, MERRA-2)",
        "description": (
            "Monthly mean surface mass concentration of dust in the PM2.5 size "
            "fraction (particles <= 2.5 um), from the MERRA-2 v5.12.4 reanalysis. "
            "Dust-fraction only -- does not represent total PM2.5."
        ),
        "tag": "derived",
        "cadence": "monthly",
        "tile_matrix_set": "2km",
        "format": "image/png",
        "temporal": True,
        "spatial_scope": "Global",
        "notes": [
            "Dust fraction only -- excludes sulfate, sea-salt, black carbon, etc.",
            "Time dimension: YYYY-MM-DD (first day of month). "
            "Range: 1980-01-01 to ~present.",
            "HTTP 200 tile probe confirmed 2026-04-11 (date format YYYY-MM-DD).",
        ],
        "available": True,
        "unavailable_reason": None,
    },
    "oco2_xco2": {
        "id": "OCO-2_Carbon_Dioxide_Total_Column_Average",
        "title": "Carbon Dioxide Total Column Average (OCO-2)",
        "description": (
            "Daily column-averaged dry-air mole fraction of CO2 (XCO2) from the "
            "Orbiting Carbon Observatory-2 (OCO-2). Sparse orbital swath coverage "
            "per day; near-global coverage over ~16 days."
        ),
        "tag": "observed",
        "cadence": "daily",
        "tile_matrix_set": "500m",
        "format": "image/png",
        "temporal": True,
        "spatial_scope": "Global",
        "notes": [
            "Swath data -- large data gaps per day are expected.",
            "Available from 2014-09-06 to ~present.",
            "HTTP 200 tile probe confirmed 2026-04-11.",
        ],
        "available": True,
        "unavailable_reason": None,
    },
    "tropomi_ch4": {
        "id": None,
        "title": "TROPOMI CH4 (Methane Column)",
        "description": (
            "Tropospheric column methane from Sentinel-5P TROPOMI. Not available "
            "as a GIBS WMTS layer as of 2026-04-11."
        ),
        "tag": "observed",
        "cadence": "daily",
        "tile_matrix_set": None,
        "format": None,
        "temporal": True,
        "spatial_scope": "Global",
        "notes": [
            "TROPOMI in GIBS only provides NO2 and SO2 layers (verified "
            "GetCapabilities 2026-04-11). CH4 data must be sourced from "
            "Copernicus GES DISC (S5P_L2__CH4____HiR) directly.",
        ],
        "available": False,
        "unavailable_reason": (
            "TROPOMI CH4 not in GIBS GetCapabilities as of 2026-04-11. "
            "Available TROPOMI layers: TROPOMI_L2_Nitrogen_Dioxide_Tropospheric_Column, "
            "TROPOMI_L2_Sulfur_Dioxide_Total_Vertical_Column."
        ),
    },
    "modis_flood": {
        "id": "MODIS_Combined_Flood_2-Day",
        "title": "Flood 2-Day Window (MODIS, Terra + Aqua)",
        "description": (
            "Near-real-time surface water / flood extent derived from combined "
            "MODIS Terra and Aqua observations over a 2-day composite window "
            "(MCDWD product). Useful for monitoring active flood events."
        ),
        "tag": "near-real-time",
        "cadence": "daily",
        "tile_matrix_set": "250m",
        "format": "image/png",
        "temporal": True,
        "spatial_scope": "Global",
        "notes": [
            "2-day composite; 3-day composite also available as "
            "MODIS_Combined_Flood_3-Day.",
            "Coverage starts 2021-01-01.",
            "HTTP 200 tile probe confirmed 2026-04-11.",
        ],
        "available": True,
        "unavailable_reason": None,
    },
}


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
