"""EPA PFAS Analytic Tools connector.

Source:  https://www.epa.gov/pfas
Cadence: quarterly
Tag:     observed
Auth:    none

=============================================================================
Verified endpoint (2026-04-12):
  EPA PFAS Analytic Tools ArcGIS FeatureServer
  https://services.arcgis.com/cJ9YHowT8TU7DUyn/arcgis/rest/services/
      PFAS_Analytic_Tools_Layers/FeatureServer

  Available layers (from FeatureServer?f=json):
    1  PAT_Unregulated_Contaminant_Monitoring  ← DEFAULT (UCMR5 drinking water)
    2  PAT_Superfund_Sites_w_PFAS_Detections
    3  PAT_Industry_Sectors
    4  TRI_Offsite_Transfers
    5  PAT_TRI_Waste_Management
    6  PAT_TRI_OnSite_Releases
    7  PAT_TRI_Offsite_Transfer_Lines
    9  PAT_eManifest_Transfers_Destinations
    10 PAT_eManifest_Transfers_Generators
    11 PAT_eManifest_Transfers
    12 PAT_Spills
    13 PAT_Federal_Sites
    14 PAT_Greenhouse_Gas_Emissions
    15 PAT_Discharge_Monitoring_Reports
    16 PAT_Chemical_Data_Reporting
    17 PAT_Water_Quality_Portal

  Layer 0 does NOT exist — querying it returns 400 Bad Request.

Smoke-tested with Houston bbox (west=-96.2, south=29.0, east=-94.5, north=30.5)
returning 5 features from Layer 1 (UCMR5), e.g. CITY OF LAKE JACKSON
(TX0200006), Contaminant=PFHxS, Analytical_Result_Value=11 ng/L.

Property fields (Layer 1, 33 total):
  OBJECTID, F_PWS_ID, PWS_Name, Size, EPA_Region, State, ZIP_Codes_Served,
  Population_Served, Population_Served_Year, Latitude, Longitude,
  UCMR_Geolocation_Method, Facility_ID, Facility_Name, Facility_Water_Type,
  Sample_Point_ID, Sample_Point_Name, Sample_Point_Type, Collection_Date,
  Sample_ID, Contaminant, CAS_Number, Minimum_Reporting_Level__ng_L_,
  Result_At_or_Above_UCMR_MRL, Result_Above_HBSL, Method_ID,
  Analytical_Result_Value__ng_L_, Sample_Event_Code, Monitoring_Requirement,
  Most_Recent_Sample, Potential_PFAS_Sources, PFAS_Treatment, UCMR_Cycle

=============================================================================
Landmines (discovered 2026-04-12):
  - Layer 0 does NOT exist — returns 400 Bad Request. Default must be layer 1.
  - `inSR=4326` MUST be set explicitly — omitting it defaults to Web Mercator
    and returns empty results for WGS84 envelopes.
  - The exact layer ID and service name may change. The connector defaults to
    layer 1 (UCMR5) but accepts a configurable layer_id. If the primary URL
    returns 400 or 404, it returns an empty list with an informative note —
    no exception raised.
  - State field has a leading space (e.g. " TX") — must strip.
  - Field names vary across layers. The normalize() method tries multiple
    ArcGIS naming patterns for resilient parsing.
  - Geometry is Point for layer 1; other layers may have Polygon — handler
    supports both (centroid for polygons, same as Superfund).
  - `exceededTransferLimit: true` can appear — we respect resultRecordCount
    and do NOT page (metro-scale queries are well under server caps).
  - Each row is a sample result (not a unique site). Multiple rows can share
    the same F_PWS_ID for different contaminants/dates. De-duplication is the
    caller's responsibility.
=============================================================================
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from backend.connectors.base import BaseConnector, ConnectorResult

# Primary FeatureServer URL — layer ID appended at query time.
PFAS_BASE_URL = (
    "https://services.arcgis.com/cJ9YHowT8TU7DUyn/arcgis/rest/services/"
    "PFAS_Analytic_Tools_Layers/FeatureServer"
)

# Fallback: service discovery endpoint (lists all available services).
PFAS_DISCOVERY_URL = (
    "https://services.arcgis.com/cJ9YHowT8TU7DUyn/arcgis/rest/services"
)

DEFAULT_LAYER_ID = 1


@dataclass
class PfasSite:
    name: str
    site_id: str
    lat: float | None
    lon: float | None
    city: str | None
    state: str | None
    site_type: str | None
    contaminant: str | None


def _polygon_centroid(coords: Any) -> tuple[float | None, float | None]:
    """Simple arithmetic centroid of the first ring of a polygon / multipolygon.

    Accepts Esri/GeoJSON coordinate structures:
      - Polygon: [ [ [x,y], [x,y], ... ] ]
      - MultiPolygon: [ [ [ [x,y], ... ] ], ... ]

    Returns (lat, lon) tuple, or (None, None) if malformed.
    This is NOT a true area-weighted centroid — good enough for marker
    placement at metro scale and avoids pulling in shapely.
    """
    try:
        ring = coords
        # Drill into first ring, handling MultiPolygon depth.
        while (
            isinstance(ring, list)
            and ring
            and isinstance(ring[0], list)
            and ring[0]
            and isinstance(ring[0][0], list)
        ):
            ring = ring[0]
        if not isinstance(ring, list) or not ring:
            return None, None
        # Drop duplicate closing vertex if present.
        pts = ring[:-1] if len(ring) > 1 and ring[0] == ring[-1] else ring
        if not pts:
            return None, None
        xs = [float(p[0]) for p in pts if isinstance(p, (list, tuple)) and len(p) >= 2]
        ys = [float(p[1]) for p in pts if isinstance(p, (list, tuple)) and len(p) >= 2]
        if not xs or not ys:
            return None, None
        return sum(ys) / len(ys), sum(xs) / len(xs)
    except (TypeError, ValueError, IndexError):
        return None, None


def _geometry_to_latlon(geometry: dict | None) -> tuple[float | None, float | None]:
    """Extract (lat, lon) from a GeoJSON geometry — supports Point/Polygon/MultiPolygon."""
    if not geometry:
        return None, None
    gtype = geometry.get("type")
    coords = geometry.get("coordinates")
    if coords is None:
        return None, None
    if gtype == "Point":
        try:
            return float(coords[1]), float(coords[0])
        except (TypeError, ValueError, IndexError):
            return None, None
    if gtype in ("Polygon", "MultiPolygon"):
        return _polygon_centroid(coords)
    return None, None


def _first_match(props: dict, candidates: list[str]) -> str | None:
    """Return the first non-empty string value matching any candidate key (case-insensitive)."""
    # Build a lowercase lookup for the property keys.
    lower_map: dict[str, str] = {k.lower(): k for k in props}
    for candidate in candidates:
        real_key = lower_map.get(candidate.lower())
        if real_key is not None:
            val = (str(props[real_key]).strip()) if props[real_key] is not None else ""
            if val:
                return val
    return None


class PfasConnector(BaseConnector):
    name = "pfas"
    source = "EPA PFAS Analytic Tools"
    source_url = "https://www.epa.gov/pfas"
    cadence = "quarterly"
    tag = "observed"

    def __init__(self, layer_id: int = DEFAULT_LAYER_ID) -> None:
        self.layer_id = layer_id

    async def fetch(
        self,
        west: float,
        south: float,
        east: float,
        north: float,
        limit: int = 100,
        **_: Any,
    ) -> dict:
        """Query EPA PFAS Analytic Tools FeatureServer for a bbox.

        Tries the primary PFAS_Analytic_Tools_Layers URL first.  If the
        primary 404s (layer structure changed), returns a minimal dict
        with an empty features list and an error note — no exception raised,
        per graceful degradation rule (CLAUDE.md #5).
        """
        params = {
            "where": "1=1",
            "outFields": "*",
            "f": "geojson",
            "geometry": f"{west},{south},{east},{north}",
            "geometryType": "esriGeometryEnvelope",
            "inSR": "4326",
            "spatialRel": "esriSpatialRelIntersects",
            "resultRecordCount": str(max(1, min(int(limit), 500))),
        }
        timeout = httpx.Timeout(60.0, connect=10.0)
        query_url = f"{PFAS_BASE_URL}/{self.layer_id}/query"

        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.get(query_url, params=params)
                if response.status_code in (400, 404):
                    # Layer structure may have changed — return graceful empty.
                    return {
                        "features": [],
                        "_error": (
                            f"Primary PFAS FeatureServer layer {self.layer_id} "
                            f"returned {response.status_code}. The layer structure "
                            f"may have changed. "
                            f"Check {PFAS_DISCOVERY_URL}?f=json for current layers."
                        ),
                    }
                response.raise_for_status()
                data = response.json()

                # ArcGIS sometimes returns an error object instead of features.
                if "error" in data:
                    err_msg = data["error"].get("message", "Unknown ArcGIS error")
                    return {
                        "features": [],
                        "_error": f"ArcGIS error: {err_msg}",
                    }
                return data

            except httpx.HTTPStatusError:
                # Re-raise non-404 HTTP errors for the endpoint handler to catch.
                raise
            except httpx.TimeoutException:
                return {
                    "features": [],
                    "_error": "PFAS FeatureServer request timed out (60s).",
                }

    def normalize(self, raw: dict) -> ConnectorResult:
        sites: list[PfasSite] = []
        notes: list[str] = []
        features = (raw or {}).get("features") or []

        # Carry through any fetch-time error notes.
        if raw and raw.get("_error"):
            notes.append(raw["_error"])

        for feat in features:
            props = feat.get("properties") or {}
            geom = feat.get("geometry")
            lat, lon = _geometry_to_latlon(geom)

            # Resilient field extraction — try multiple ArcGIS naming patterns.
            # Layer 1 (UCMR5) uses PWS_Name, F_PWS_ID, State, Contaminant,
            # Facility_Water_Type; other layers may use different names.
            name = _first_match(
                props,
                ["PWS_Name", "Facility_Name", "SITE_NAME", "FacilityName", "Name",
                 "FACILITY_NAME", "PWS_NAME", "SystemName", "SYSTEM_NAME", "PWSName"],
            ) or "Unnamed PFAS Site"

            site_id = _first_match(
                props,
                ["F_PWS_ID", "EPA_ID", "Facility_ID", "FacilityID", "REGISTRY_ID",
                 "PGM_SYS_ID", "PWSID", "PWSId", "FRS_ID"],
            ) or ""

            state = _first_match(props, ["State", "STATE", "STATE_CODE", "PrimacyAgency"])
            city = _first_match(props, ["CITY", "CITY_NAME", "City", "CityServed"])
            contaminant = _first_match(
                props,
                ["Contaminant", "CONTAMINANT", "CHEMICAL_NAME", "PFAS_CHEMICAL",
                 "AnalyteName", "Analyte", "ANALYTE_NAME", "ContaminantName"],
            )
            site_type = _first_match(
                props,
                ["Facility_Water_Type", "SITE_TYPE", "FacilityType", "SOURCE_TYPE",
                 "SystemType", "SYSTEM_TYPE", "FacilityTypeCode", "Size"],
            )

            sites.append(
                PfasSite(
                    name=name,
                    site_id=site_id,
                    lat=lat,
                    lon=lon,
                    city=city,
                    state=state,
                    site_type=site_type,
                    contaminant=contaminant,
                )
            )

        if not notes:
            notes = [
                "PFAS monitoring data from EPA PFAS Analytic Tools.",
                "Geometry may be Point or Polygon - lat/lon is a simple centroid "
                "for polygons (not area-weighted).",
                "Each row is a sample result, not a unique site. Multiple rows "
                "may share the same PWS ID for different contaminants or dates.",
            ]

        return ConnectorResult(
            values=sites,
            source=self.source,
            source_url=self.source_url,
            cadence=self.cadence,
            tag=self.tag,
            spatial_scope="U.S. facilities and monitoring sites",
            license="Public domain (US EPA)",
            notes=notes,
        )
