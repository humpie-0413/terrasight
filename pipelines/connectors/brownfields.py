"""EPA Brownfields (ACRES) connector.

Source:  https://www.epa.gov/brownfields
Cadence: monthly
Tag:     observed
Auth:    none

=============================================================================
Verified endpoint (2026-04-12):
  EPA EMEF efpoints MapServer, layer 5 = Brownfields (points)
  https://geopub.epa.gov/arcgis/rest/services/EMEF/efpoints/MapServer/5/query

The parent MapServer at .../MapServer?f=json lists:
  0 Superfund, 1 Toxic releases, 2 Water dischargers, 3 Air pollution,
  4 Hazardous waste, 5 Brownfields — all esriGeometryPoint.

Property fields (16 total):
  OBJECTID, registry_id, primary_name, location_address, city_name,
  county_name, state_code, epa_region, postal_code, latitude, longitude,
  pgm_sys_acrnm (= "ACRES"), pgm_sys_id, fips_code, huc_code, facility_url

Cleanup status is NOT provided on this point-layer — the ACRES back-end
has cleanup activity status, but the spatial service exposes location
attributes only. We set cleanup_status=None and surface this as a landmine.

=============================================================================
Landmines (discovered 2026-04-12):
  - Brownfields sit at MapServer layer ID 5 under the EMEF efpoints service.
    If the ID shifts, inspect MapServer?f=json and update SITE_LAYER_ID.
  - `cleanup_status` is NOT in this layer's schema. The Brownfields cleanup
    state lives in the ACRES program database (different endpoint). We
    return None and call it out in notes. A future pass can join on
    registry_id / pgm_sys_id against the ACRES Envirofacts REST API.
  - `inSR=4326` MUST be passed explicitly; otherwise empty results for
    WGS84 bbox queries.
  - MapServer returns GeoJSON where coordinates are [lon, lat] — standard.
  - ACRES is grantee-reported; coverage is not exhaustive (carried in notes).
=============================================================================
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from backend.connectors.base import BaseConnector, ConnectorResult

BROWNFIELDS_URL = (
    "https://geopub.epa.gov/arcgis/rest/services/EMEF/efpoints/MapServer/5/query"
)


@dataclass
class BrownfieldsSite:
    name: str
    site_id: str
    lat: float | None
    lon: float | None
    city: str | None
    state: str | None
    cleanup_status: str | None


def _point_latlon(geometry: dict | None) -> tuple[float | None, float | None]:
    """Extract (lat, lon) from a GeoJSON Point geometry."""
    if not geometry:
        return None, None
    if geometry.get("type") != "Point":
        return None, None
    coords = geometry.get("coordinates")
    try:
        return float(coords[1]), float(coords[0])
    except (TypeError, ValueError, IndexError):
        return None, None


class BrownfieldsConnector(BaseConnector):
    name = "brownfields"
    source = "EPA ACRES (Brownfields)"
    source_url = "https://www.epa.gov/brownfields"
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
        """Query the EPA Brownfields point layer for a bbox.

        Returns the parsed GeoJSON FeatureCollection dict.
        """
        params = {
            "where": "1=1",
            "outFields": (
                "registry_id,primary_name,location_address,city_name,"
                "state_code,pgm_sys_id,pgm_sys_acrnm"
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
            response = await client.get(BROWNFIELDS_URL, params=params)
            response.raise_for_status()
            return response.json()

    def normalize(self, raw: dict) -> ConnectorResult:
        sites: list[BrownfieldsSite] = []
        features = (raw or {}).get("features") or []
        for feat in features:
            props = feat.get("properties") or {}
            lat, lon = _point_latlon(feat.get("geometry"))

            name = (props.get("primary_name") or "").strip() or "Unnamed Brownfields Site"
            # Prefer the ACRES program-system id, fall back to FRS registry_id.
            site_id = (
                (props.get("pgm_sys_id") or "").strip()
                or (props.get("registry_id") or "").strip()
            )
            city = (props.get("city_name") or "").strip() or None
            state = (props.get("state_code") or "").strip() or None

            sites.append(
                BrownfieldsSite(
                    name=name,
                    site_id=site_id,
                    lat=lat,
                    lon=lon,
                    city=city,
                    state=state,
                    # This spatial layer does not expose cleanup status; the
                    # attribute lives in the ACRES program DB (separate API).
                    cleanup_status=None,
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
                "ACRES is grantee-reported; coverage is not exhaustive.",
                "cleanup_status is not exposed by the spatial point layer; "
                "join on pgm_sys_id against the ACRES program DB to populate.",
            ],
        )
