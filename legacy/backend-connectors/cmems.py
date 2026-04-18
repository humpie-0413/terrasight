"""Copernicus Marine Service (CMEMS) Sea Level Anomaly connector.

Source:   https://marine.copernicus.eu/
Product:  SEALEVEL_GLO_PHY_L4_NRT_008_046
          "Global Ocean Gridded L4 Sea Surface Heights And Derived Variables NRT"
Cadence:  daily (NRT, ~1–2 day lag)
Tag:      observed  (satellite altimetry-derived)

=============================================================================
Infrastructure note (updated 2026-04-11 — CMEMS endpoint migration):

  The old THREDDS OPeNDAP endpoint at nrt.cmems-du.eu is DECOMMISSIONED.
  DNS for nrt.cmems-du.eu resolves to 172.67.145.239 (301Domains parking
  service) — all data requests return an HTML landing page, not data.

  New access pattern (Marine Data Store, post-2024):
    Auth:
      POST https://auth.marine.copernicus.eu/realms/MIS/protocol/openid-connect/token
      client_id=toolbox, grant_type=password
      (Keycloak OAuth2; realm is "MIS" — old docs showing keycloak.marine.copernicus.eu
       or realm "CMEMS" are stale)

    Data:
      ARCO Zarr on CloudFerro S3 at s3.waw3-1.cloudferro.com
        - Zarr metadata (.zattrs, .zmetadata): publicly accessible, no auth
        - Zarr data chunks: 403 AccessDenied — require S3 credentials
          managed internally by the copernicusmarine Python package

    No standalone REST subset API exists. The subset operation is
    implemented inside the copernicusmarine package only.

  This connector:
    1. Validates credentials via Keycloak (confirms account is working)
    2. Confirms service availability via public Zarr metadata
    3. Returns status='pending' since actual data chunks require
       the copernicusmarine package (not yet integrated)

  To fully enable this layer, add copernicusmarine to requirements.txt
  and rewrite the fetch() to use copernicusmarine.open_dataset().

Product dataset ID: cmems_obs-sl_glo_phy-ssh_nrt_allsat-l4-duacs-0.25deg_P1D
Variables: sla (sea level anomaly, m), adt (absolute dynamic topography, m),
           ugos, vgos (geostrophic velocity anomalies, m/s), err_sla (error, m)

Graceful degradation:
  - CMEMS_USERNAME / CMEMS_PASSWORD absent → status='not_configured'
  - Auth failure (401/400) → status='error' with message
  - Auth service unreachable → status='error' with message
  - Credentials valid but data access requires package → status='pending'
=============================================================================
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx

from backend.connectors.base import BaseConnector, ConnectorResult

# New Keycloak OAuth2 token endpoint (Marine Data Store, post-2024)
# Realm is "MIS" — old docs referencing keycloak.marine.copernicus.eu or realm "CMEMS" are stale.
_KEYCLOAK_TOKEN_URL = (
    "https://auth.marine.copernicus.eu/realms/MIS/protocol/openid-connect/token"
)

# Public Zarr metadata (no auth required) — confirms service availability.
# The 0.25° NRT L4 DUACS product. Version suffix _202311 indicates the processing version.
_ZARR_ZATTRS_URL = (
    "https://s3.waw3-1.cloudferro.com/mdl-arco-time-045/arco/"
    "SEALEVEL_GLO_PHY_L4_NRT_008_046/"
    "cmems_obs-sl_glo_phy-ssh_nrt_allsat-l4-duacs-0.25deg_P1D_202311/"
    "timeChunked.zarr/.zattrs"
)

PRODUCT_PAGE = (
    "https://data.marine.copernicus.eu/product/"
    "SEALEVEL_GLO_PHY_L4_NRT_008_046/description"
)


@dataclass
class SeaLevelAnomalyPoint:
    lat: float
    lon: float
    sla_m: float    # sea level anomaly in metres
    adt_m: float    # absolute dynamic topography in metres
    date_utc: str   # ISO date string YYYY-MM-DD


def _not_configured_result(source: str, source_url: str, cadence: str, tag: str) -> ConnectorResult:
    return ConnectorResult(
        values={
            "status": "not_configured",
            "message": (
                "CMEMS credentials are required but not set. "
                "Register for free at https://marine.copernicus.eu/ and set the "
                "environment variables CMEMS_USERNAME and CMEMS_PASSWORD. "
                "Then restart the backend service."
            ),
            "setup_steps": [
                "1. Visit https://marine.copernicus.eu/ → Register (free)",
                "2. Set CMEMS_USERNAME=<your_email> in your environment",
                "3. Set CMEMS_PASSWORD=<your_password> in your environment",
                "4. Product: SEALEVEL_GLO_PHY_L4_NRT_008_046",
            ],
        },
        source=source,
        source_url=source_url,
        cadence=cadence,
        tag=tag,
        spatial_scope="Global (0.25°)",
        license="Copernicus Marine Open Data Licence — free for registered users",
        notes=["Credentials not configured. See values.setup_steps."],
    )


class CmemsConnector(BaseConnector):
    """Copernicus Marine Service (CMEMS) sea level anomaly connector.

    Validates credentials via Keycloak and confirms data availability
    via public Zarr metadata. Returns status='pending' until the
    copernicusmarine package is integrated for actual data download.

    Requires CMEMS_USERNAME and CMEMS_PASSWORD environment variables.
    Returns status='not_configured' if credentials are absent.
    """

    name = "cmems"
    source = "Copernicus Marine Service (CMEMS)"
    source_url = "https://marine.copernicus.eu/"
    cadence = "daily"
    tag = "observed"

    def __init__(
        self,
        username: str | None = None,
        password: str | None = None,
    ) -> None:
        self.username: str | None = username or os.environ.get("CMEMS_USERNAME")
        self.password: str | None = password or os.environ.get("CMEMS_PASSWORD")

    async def fetch(self, **_params: Any) -> Any:
        """Validate CMEMS credentials and confirm data service availability.

        Returns a status dict:
          - 'not_configured': credentials missing
          - 'error': auth failed or service unreachable
          - 'pending': credentials valid, data requires copernicusmarine package
        """
        if not self.username or not self.password:
            return {"status": "not_configured"}

        timeout = httpx.Timeout(30.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            # Step 1: Validate credentials via Keycloak OAuth2
            try:
                token_resp = await client.post(
                    _KEYCLOAK_TOKEN_URL,
                    data={
                        "grant_type": "password",
                        "client_id": "toolbox",
                        "username": self.username,
                        "password": self.password,
                        "scope": "openid profile email",
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                if token_resp.status_code in (400, 401):
                    # 400 = invalid_grant (wrong credentials), 401 = unauthorized
                    body = token_resp.json() if token_resp.content else {}
                    error_desc = body.get("error_description", "invalid credentials")
                    return {
                        "status": "error",
                        "message": (
                            f"CMEMS authentication failed: {error_desc}. "
                            "Check CMEMS_USERNAME and CMEMS_PASSWORD."
                        ),
                    }
                token_resp.raise_for_status()
                credentials_valid = True
            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                return {
                    "status": "error",
                    "message": (
                        f"CMEMS auth service unreachable: {exc}. "
                        "The Marine Data Store Keycloak endpoint may be temporarily down."
                    ),
                }
            except httpx.HTTPStatusError as exc:
                return {
                    "status": "error",
                    "message": (
                        f"CMEMS auth HTTP {exc.response.status_code}: {exc}"
                    ),
                }

            # Step 2: Confirm data availability via public Zarr metadata
            data_service_ok = False
            try:
                meta_resp = await client.get(_ZARR_ZATTRS_URL)
                data_service_ok = meta_resp.status_code == 200
            except Exception:
                pass  # non-critical — credentials already validated

        return {
            "status": "pending",
            "credentials_valid": credentials_valid,
            "data_service_ok": data_service_ok,
            "message": (
                "CMEMS credentials are valid and the Marine Data Store is reachable. "
                "Sea level anomaly data is available but requires the copernicusmarine "
                "Python package to download data chunks from the CloudFerro S3 store. "
                "Full integration is planned for a future release."
            ),
        }

    def normalize(self, raw: Any) -> ConnectorResult:
        """Pass through status dicts; return empty list for actual data (future)."""
        if isinstance(raw, dict):
            status = raw.get("status", "error")
            if status == "not_configured":
                return _not_configured_result(
                    self.source, self.source_url, self.cadence, self.tag
                )
            # error or pending — pass through the dict
            return ConnectorResult(
                values=raw,
                source=self.source,
                source_url=self.source_url,
                cadence=self.cadence,
                tag=self.tag,
                spatial_scope="Global (0.25°)",
                license="Copernicus Marine Open Data Licence — free for registered users",
                notes=[
                    f"Status: {status}.",
                    "Full data access requires copernicusmarine package integration.",
                    "Product: SEALEVEL_GLO_PHY_L4_NRT_008_046 (DUACS L4 altimetry, 0.25°).",
                ],
            )

        # Future: actual SeaLevelAnomalyPoint list from copernicusmarine
        points: list[SeaLevelAnomalyPoint] = raw if isinstance(raw, list) else []
        return ConnectorResult(
            values=points,
            source=self.source,
            source_url=self.source_url,
            cadence=self.cadence,
            tag=self.tag,
            spatial_scope="Global (0.25° L4 gridded altimetry)",
            license="Copernicus Marine Open Data Licence — free for registered users",
            notes=[
                "Product: SEALEVEL_GLO_PHY_L4_NRT_008_046.",
                "sla_m: sea level anomaly (m) vs. 1993–2012 mean.",
                "Data from merged multi-mission altimetry (DUACS processing).",
            ],
        )
