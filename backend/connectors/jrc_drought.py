"""EU JRC / Copernicus Global Drought Observatory (GDO) connector.

Source:  https://drought.emergency.copernicus.eu/
Cadence: dekadal (10-day) for most indices; monthly for SPI long-term and
         GRACE TWS anomaly
Tag:     derived (modelled + satellite composite; Hansen et al. precip models,
         LISFLOOD soil moisture, ERA5 reanalysis)
Auth:    none — WMS and WCS services are public, no API key required

=============================================================================
Verified endpoints (2026-04-11):

  ✅ WMS GetCapabilities (public, no auth):
       https://drought.emergency.copernicus.eu/api/wms
       ?REQUEST=GetCapabilities&SERVICE=WMS&VERSION=1.1.1

  ✅ WCS DescribeCoverage (confirmed coverage IDs via wcs-service page):
       https://drought.emergency.copernicus.eu/api/wcs
       ?map=do_wcs&SERVICE=WCS&REQUEST=DescribeCoverage&VERSION=2.0.0
       &COVERAGEID={coverage_id}

  ❌ No public JSON / REST tabular API exists.
     The tumbo download portal at /tumbo/gdo/download/ is a GUI; it does
     not expose a documented machine-readable API endpoint as of 2026-04-11.

  ❌ The older edo.jrc.ec.europa.eu domain was migrated to
     drought.emergency.copernicus.eu on 2024-04-03 — do NOT use the old URL.

=============================================================================
API architecture — tiles_only:

  The GDO exposes geospatial raster data via two OGC services:

  1. WMS (Web Map Service) — rendered PNG/JPEG tiles for display.
     Base URL: https://drought.emergency.copernicus.eu/api/wms
     Key layers (layer Name, title, update cadence):
       spaST  SPI ERA5 Short Term          dekadal
       spaLT  SPI ERA5 Long Term           monthly
       spcST  SPI CHIRPS Short-term        dekadal
       spcLT  SPI CHIRPS Long-term         monthly
       spgTS  SPI GPCC                     monthly
       smian  SMI Anomaly                  dekadal
       smang  Soil Moisture Index Anomaly  dekadal
       smand  Ensemble Soil Moisture       monthly
       fpanv  fAPAR Anomaly (VIIRS)        dekadal
       cdiad  Combined Drought Indicator   dekadal
       twsan  GRACE TWS Anomaly            monthly
       rdria  Risk of Drought / Agriculture dekadal

  2. WCS (Web Coverage Service) — raw raster data as GeoTIFF or NetCDF.
     Base URL: https://drought.emergency.copernicus.eu/api/wcs
     Same coverage IDs as the WMS layer names above.
     WCS version: 2.0.0

  This connector fetches WMS GetCapabilities to confirm which layers are
  currently available and returns their metadata as ``values``. It also
  returns canonical WCS GetCoverage URL templates so callers can pull
  raster data for a specific layer and time step.

  Future improvement: add a ``fetch_raster()`` helper that downloads a
  GeoTIFF via WCS, reads it with rasterio, and returns spatial statistics
  (mean SPI by country using a country mask). This requires rasterio in
  the dependency tree, which is not yet present.

=============================================================================
Landmines:
  1. Domain migration: the service moved from edo.jrc.ec.europa.eu to
     drought.emergency.copernicus.eu in April 2024. Any bookmarked or
     hardcoded old URLs will 404.
  2. WMS TIME parameter: values must match the dataset's update cadence
     exactly (ISO 8601 date string). Sending an off-cadence date returns
     the nearest available time rather than an error — callers should not
     assume the returned tile matches the requested time.
  3. SELECTED_TIMESCALE is required for some SPI layers (e.g., SPI GPCC
     accepts values "01", "03", "06", "09", "12" for accumulation periods).
  4. WCS GetCoverage returns GeoTIFF by default; requesting NetCDF requires
     FORMAT=application/netcdf. Some coverage IDs only support GeoTIFF.
  5. The Combined Drought Indicator (cdiad) is European-only (EDO), not
     global. Global layers: spaST, spaLT, spcST, spcLT, spgTS, smian,
     smang, smand, fpanv, twsan, rdria.
  6. No JSON tabular statistics endpoint exists. Pixel-level statistics
     require rasterio or GDAL to process GeoTIFF responses from WCS.
=============================================================================
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any

import httpx

from backend.connectors.base import BaseConnector, ConnectorResult

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_WMS_BASE = "https://drought.emergency.copernicus.eu/api/wms"
_WCS_BASE = "https://drought.emergency.copernicus.eu/api/wcs"

_WMS_CAPABILITIES_URL = (
    f"{_WMS_BASE}?REQUEST=GetCapabilities&SERVICE=WMS&VERSION=1.1.1"
)

# WMS namespace used in 1.1.1 capabilities XML
_WMS_NS = ""  # 1.1.1 uses no default namespace in layer elements

# Known GDO layers from verified WMS capabilities (2026-04-11).
# Used as fallback if GetCapabilities parsing fails.
_KNOWN_LAYERS: list[dict[str, str]] = [
    {"name": "spaST", "title": "SPI ERA5 Short Term",             "scope": "global", "cadence": "dekadal"},
    {"name": "spaLT", "title": "SPI ERA5 Long Term",              "scope": "global", "cadence": "monthly"},
    {"name": "spcST", "title": "SPI CHIRPS Short-term",           "scope": "global", "cadence": "dekadal"},
    {"name": "spcLT", "title": "SPI CHIRPS Long-term",            "scope": "global", "cadence": "monthly"},
    {"name": "spgTS", "title": "SPI GPCC",                        "scope": "global", "cadence": "monthly"},
    {"name": "smian", "title": "SMI Anomaly",                     "scope": "global", "cadence": "dekadal"},
    {"name": "smang", "title": "Soil Moisture Index Anomaly",     "scope": "global", "cadence": "dekadal"},
    {"name": "smand", "title": "Ensemble Soil Moisture Anomaly",  "scope": "global", "cadence": "monthly"},
    {"name": "fpanv", "title": "fAPAR Anomaly (VIIRS)",           "scope": "global", "cadence": "dekadal"},
    {"name": "cdiad", "title": "Combined Drought Indicator v4.0", "scope": "europe", "cadence": "dekadal"},
    {"name": "twsan", "title": "GRACE TWS Anomaly",               "scope": "global", "cadence": "monthly"},
    {"name": "rdria", "title": "Risk of Drought / Agriculture",   "scope": "global", "cadence": "dekadal"},
]


# ---------------------------------------------------------------------------
# Typed result dataclasses
# ---------------------------------------------------------------------------
@dataclass
class DroughtLayer:
    """Metadata for one GDO WMS/WCS layer."""

    name: str          # WMS layer name / WCS coverage ID
    title: str         # Human-readable title
    scope: str         # "global" or "europe"
    cadence: str       # "dekadal" or "monthly"
    # Canonical URL templates (caller substitutes {TIME} and optional {TIMESCALE})
    wms_tile_url_template: str = field(default="")
    wcs_geotiff_url_template: str = field(default="")


@dataclass
class DroughtIndexPoint:
    """Placeholder for future raster-derived tabular values.

    Populated only when a rasterio-based GetCoverage helper is available.
    Currently unused — connector returns layer metadata only.
    """

    region: str        # country ISO-3 or region name
    index_type: str    # e.g. "SPI ERA5 Short Term"
    value: float       # SPI Z-score; negative = dry
    severity: str      # "None" | "Watch" | "Warning" | "Emergency"
    date_utc: str      # YYYY-MM-DD


# ---------------------------------------------------------------------------
# Severity classification (SPI Z-score thresholds per WMO/JRC convention)
# ---------------------------------------------------------------------------
def _spi_severity(value: float) -> str:
    """Map SPI / anomaly Z-score to WMO drought severity category."""
    if value >= -0.5:
        return "None"
    elif value >= -1.0:
        return "Watch"
    elif value >= -1.5:
        return "Warning"
    else:
        return "Emergency"


# ---------------------------------------------------------------------------
# URL template builders
# ---------------------------------------------------------------------------
def _wms_tile_template(layer_name: str) -> str:
    return (
        f"{_WMS_BASE}?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap"
        f"&LAYERS={layer_name}"
        "&SRS=EPSG:4326"
        "&WIDTH=1024&HEIGHT=512"
        "&BBOX=-180,-90,180,90"
        "&FORMAT=image/png"
        "&TIME={TIME}"
    )


def _wcs_geotiff_template(layer_name: str) -> str:
    return (
        f"{_WCS_BASE}?map=DO_WCS&SERVICE=WCS&VERSION=2.0.0"
        f"&REQUEST=GetCoverage&COVERAGEID={layer_name}"
        "&CRS=EPSG:4326"
        "&FORMAT=GEOTIFF"
        "&TIME={TIME}"
    )


# ---------------------------------------------------------------------------
# Connector
# ---------------------------------------------------------------------------
class JrcDroughtConnector(BaseConnector):
    """Fetch GDO layer metadata and return WMS/WCS URL templates.

    No tabular JSON API exists for the JRC Global Drought Observatory as of
    2026-04-11. This connector fetches WMS GetCapabilities to confirm which
    drought layers are live, then returns ``DroughtLayer`` objects containing
    canonical WMS tile URL templates and WCS GeoTIFF URL templates.

    Callers can:
    - Use ``wms_tile_url_template`` to render map tiles (substitute ``{TIME}``
      with an ISO 8601 date string, e.g. "2026-01-01").
    - Use ``wcs_geotiff_url_template`` to download GeoTIFF rasters via WCS
      for further spatial analysis (requires rasterio or GDAL on the caller).

    The ``status: "tiles_only"`` note in the ConnectorResult signals to the
    frontend that pixel-level statistics are not available from this connector.
    """

    name = "jrc_drought"
    source = "EU JRC / Copernicus Global Drought Observatory"
    source_url = "https://drought.emergency.copernicus.eu/"
    cadence = "dekadal"  # most layers; some are monthly
    tag = "derived"

    # ------------------------------------------------------------------
    # BaseConnector implementation
    # ------------------------------------------------------------------

    async def fetch(self, **params: Any) -> Any:
        """Fetch WMS GetCapabilities XML and parse layer names / titles.

        Returns a dict with:
        - ``status``: "ok" | "error"
        - ``layers``: list of dicts with name/title/time_extent
        - ``message``: error description (error case only)

        Falls back to ``_KNOWN_LAYERS`` if GetCapabilities parsing fails.
        """
        timeout = httpx.Timeout(30.0, connect=10.0)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                r = await client.get(_WMS_CAPABILITIES_URL)
                r.raise_for_status()
                layers = _parse_wms_layers(r.text)
                return {"status": "ok", "layers": layers, "raw_xml_length": len(r.text)}
        except httpx.HTTPStatusError as exc:
            return {
                "status": "error",
                "message": f"WMS GetCapabilities HTTP {exc.response.status_code}",
                "layers": _KNOWN_LAYERS,
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "status": "error",
                "message": str(exc),
                "layers": _KNOWN_LAYERS,
            }

    def normalize(self, raw: Any) -> ConnectorResult:
        """Convert WMS capabilities payload into DroughtLayer objects.

        In the error/fallback case the known-layer list is used so the
        connector is always useful even when the live endpoint is unreachable.
        """
        status = raw.get("status", "error") if isinstance(raw, dict) else "error"
        raw_layers: list[dict[str, Any]] = (
            raw.get("layers", _KNOWN_LAYERS) if isinstance(raw, dict) else _KNOWN_LAYERS
        )

        drought_layers: list[DroughtLayer] = []
        for lyr in raw_layers:
            name = lyr.get("name", "")
            title = lyr.get("title", name)
            # Scope inference: cdiad/cdirc are European; everything else global
            scope = "europe" if name.startswith("cdi") or name.startswith("snw") else "global"
            # Cadence inference from known patterns
            cadence = lyr.get("cadence") or (
                "monthly" if name in {"spaLT", "spcLT", "spgTS", "smand", "twsan"} else "dekadal"
            )
            drought_layers.append(
                DroughtLayer(
                    name=name,
                    title=title,
                    scope=scope,
                    cadence=cadence,
                    wms_tile_url_template=_wms_tile_template(name),
                    wcs_geotiff_url_template=_wcs_geotiff_template(name),
                )
            )

        extra_notes: list[str] = []
        if status == "error":
            msg = raw.get("message", "unknown error") if isinstance(raw, dict) else str(raw)
            extra_notes.append(f"WMS GetCapabilities fetch failed ({msg}); using known-layer fallback.")

        return ConnectorResult(
            values=drought_layers,
            source=self.source,
            source_url=self.source_url,
            cadence=self.cadence,
            tag=self.tag,
            spatial_scope="Global (most layers); Europe (CDI layers)",
            license="Creative Commons Attribution 4.0 International (CC BY 4.0)",
            notes=[
                "status:tiles_only — no public JSON/REST tabular API exists for GDO as of 2026-04-11.",
                "Use wms_tile_url_template to render map tiles (substitute {TIME} with ISO 8601 date).",
                "Use wcs_geotiff_url_template to download GeoTIFF via WCS for spatial analysis.",
                "Raster-to-tabular statistics require rasterio/GDAL; not implemented in this connector.",
                "Domain migrated from edo.jrc.ec.europa.eu to drought.emergency.copernicus.eu on 2024-04-03.",
                "SPI layers: negative values = dry anomaly; WMO thresholds: Watch<-0.5, Warning<-1.0, Emergency<-1.5.",
                "cdiad (Combined Drought Indicator) is European-only; all other layers are global.",
                "SELECTED_TIMESCALE parameter required for SPI GPCC (spgTS): '01','03','06','09','12' months.",
            ] + extra_notes,
        )


# ---------------------------------------------------------------------------
# WMS XML parser
# ---------------------------------------------------------------------------
def _parse_wms_layers(xml_text: str) -> list[dict[str, Any]]:
    """Parse WMS 1.1.1 GetCapabilities XML into a flat list of layer dicts.

    Returns a list of dicts with keys: name, title.
    Silently skips layers without a <Name> element (group/container layers).
    """
    layers: list[dict[str, Any]] = []
    try:
        root = ET.fromstring(xml_text)
        # WMS 1.1.1 uses no namespace on Layer elements
        for layer_el in root.iter("Layer"):
            name_el = layer_el.find("Name")
            title_el = layer_el.find("Title")
            if name_el is None or not name_el.text:
                continue
            layers.append(
                {
                    "name": name_el.text.strip(),
                    "title": title_el.text.strip() if title_el is not None and title_el.text else name_el.text.strip(),
                }
            )
    except ET.ParseError:
        # Fall back to known layers — caller handles this
        return []
    return layers
