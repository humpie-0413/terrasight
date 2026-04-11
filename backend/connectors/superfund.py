"""EPA Superfund (SEMS / NPL) connector.

Source:  https://www.epa.gov/superfund
Cadence: monthly (site boundary refresh)
Tag:     observed
Auth:    none

=============================================================================
Verified endpoint (2026-04-12):
  EPA FAC_Superfund_Site_Boundaries_EPA_Public FeatureServer/0 (polygons)
  https://services.arcgis.com/cJ9YHowT8TU7DUyn/arcgis/rest/services/
      FAC_Superfund_Site_Boundaries_EPA_Public/FeatureServer/0/query

Smoke-tested with Houston bbox (west=-96.2, south=29.0, east=-94.5, north=30.5)
returning 5+ features including SOUTH CAVALCADE STREET, SHERIDAN DISPOSAL
SERVICES, SIKES DISPOSAL PITS etc. — all NPL_STATUS_CODE="F" (Final).

Property fields (32 total):
  OBJECTID, REGION_CODE, EPA_PROGRAM, EPA_ID, SITE_NAME, SITE_FEATURE_CLASS,
  SITE_FEATURE_TYPE, SITE_FEATURE_NAME, SITE_FEATURE_DESCRIPTION,
  NPL_STATUS_CODE, FEDERAL_FACILITY_DETER_CODE, LAST_CHANGE_DATE,
  ORIGINAL_CREATION_DATE, SITE_FEATURE_SOURCE, STREET_ADDR_TXT, ADDR_COMMENT,
  CITY_NAME, COUNTY, STATE_CODE, ZIP_CODE, SITE_CONTACT_NAME,
  PRIMARY_TELEPHONE_NUM, SITE_CONTACT_EMAIL, URL_ALIAS_TXT, FEATURE_INFO_URL,
  FEATURE_INFO_URL_DESC, GIS_AREA, GIS_AREA_UNITS, PROJECTION,
  SF_GEOSPATIAL_DATA_DISCLAIMER, Shape__Area, Shape__Length

NPL_STATUS_CODE vocabulary (not exhaustive):
  F = Final (on the National Priorities List)
  P = Proposed
  D = Deleted
  R = Removed / Not on NPL

=============================================================================
Landmines (discovered 2026-04-12):
  - Geometry is Polygon (site boundaries), NOT point. For Local Reports we
    need a lat/lon centroid — compute it as the mean of the first ring's
    vertices (closed ring, so the last == first — drop the duplicate first).
    We intentionally do NOT import shapely to keep deps light.
  - `inSR=4326` MUST be set explicitly. Omitting it defaults to Web Mercator
    and returns an empty feature list for WGS84 envelopes.
  - The bbox `geometry` param format is comma-joined `west,south,east,north`.
  - `exceededTransferLimit: true` can appear in the response — respect the
    `resultRecordCount` we pass; we do NOT page here (a single CBSA has at
    most a few dozen sites, well under the default 1000 cap).
  - Data disclaimer: "Data do not represent EPA's official position. Site
    listing status may change." — carried in ConnectorResult.notes.
=============================================================================
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from backend.connectors.base import BaseConnector, ConnectorResult

SUPERFUND_URL = (
    "https://services.arcgis.com/cJ9YHowT8TU7DUyn/arcgis/rest/services/"
    "FAC_Superfund_Site_Boundaries_EPA_Public/FeatureServer/0/query"
)


@dataclass
class SuperfundSite:
    name: str
    site_id: str
    lat: float | None
    lon: float | None
    city: str | None
    state: str | None
    npl_status: str | None
    address: str | None


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


class SuperfundConnector(BaseConnector):
    name = "superfund"
    source = "EPA SEMS / Superfund NPL"
    source_url = "https://www.epa.gov/superfund"
    cadence = "monthly"
    tag = "observed"

    async def fetch(
        self,
        west: float,
        south: float,
        east: float,
        north: float,
        limit: int = 100,
        **_: Any,
    ) -> dict:
        """Query EPA Superfund Site Boundaries FeatureServer for a bbox.

        Returns the parsed GeoJSON FeatureCollection dict.
        """
        params = {
            "where": "1=1",
            "outFields": (
                "SITE_NAME,EPA_ID,NPL_STATUS_CODE,STREET_ADDR_TXT,"
                "CITY_NAME,STATE_CODE,ZIP_CODE"
            ),
            "f": "geojson",
            "geometry": f"{west},{south},{east},{north}",
            "geometryType": "esriGeometryEnvelope",
            "inSR": "4326",
            "spatialRel": "esriSpatialRelIntersects",
            "resultRecordCount": str(max(1, min(int(limit), 500))),
        }
        timeout = httpx.Timeout(60.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(SUPERFUND_URL, params=params)
            response.raise_for_status()
            return response.json()

    def normalize(self, raw: dict) -> ConnectorResult:
        sites: list[SuperfundSite] = []
        features = (raw or {}).get("features") or []
        for feat in features:
            props = feat.get("properties") or {}
            geom = feat.get("geometry")
            lat, lon = _geometry_to_latlon(geom)

            name = (props.get("SITE_NAME") or "").strip() or "Unnamed Superfund Site"
            site_id = (props.get("EPA_ID") or "").strip()
            npl_status = (props.get("NPL_STATUS_CODE") or "").strip() or None
            address = (props.get("STREET_ADDR_TXT") or "").strip() or None
            city = (props.get("CITY_NAME") or "").strip() or None
            state = (props.get("STATE_CODE") or "").strip() or None

            sites.append(
                SuperfundSite(
                    name=name,
                    site_id=site_id,
                    lat=lat,
                    lon=lon,
                    city=city,
                    state=state,
                    npl_status=npl_status,
                    address=address,
                )
            )

        return ConnectorResult(
            values=sites,
            source=self.source,
            source_url=self.source_url,
            cadence=self.cadence,
            tag=self.tag,
            spatial_scope="US facilities within bbox",
            license="Public domain (US EPA)",
            notes=[
                "Data do not represent EPA's official position. "
                "Site listing status may change.",
                "NPL_STATUS_CODE: F=Final, P=Proposed, D=Deleted, R=Removed.",
                "Geometry is polygon site boundaries — lat/lon is a simple "
                "centroid of the first ring (not area-weighted).",
            ],
        )
