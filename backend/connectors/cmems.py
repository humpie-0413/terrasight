"""Copernicus Marine Service (CMEMS) Sea Level Anomaly connector.

Source:   https://marine.copernicus.eu/
Product:  SEALEVEL_GLO_PHY_L4_NRT_008_046
          "Global Ocean Gridded L4 Sea Surface Heights And Derived Variables NRT"
Cadence:  daily (NRT, ~1–2 day lag)
Tag:      observed  (satellite altimetry-derived)

=============================================================================
Auth status (verified 2026-04-11):
  ⚠️  CMEMS requires a FREE registered account.
     All data-download services (OPeNDAP, Subset, Files) require
     CMEMS credentials. A registration-free WMTS endpoint exists for
     *map tiles only* (not numerical data).

  Authentication: HTTP Basic Auth (username + password) sent via the
  Copernicus Marine Toolbox or direct HTTPS calls to the OPeNDAP endpoint.

  New (post-2023) endpoint pattern uses the copernicusmarine Python package
  or equivalent REST calls to:
    https://nrt.cmems-du.eu/thredds/dodsC/
      cmems_obs-sl_glo_phy-ssh_nrt_allsat-l4-duacs-0.25deg_P1D
  This is the primary NRT L4 gridded SSH/SLA product (daily, 0.25°).

  Product dataset ID: cmems_obs-sl_glo_phy-ssh_nrt_allsat-l4-duacs-0.25deg_P1D
  Variables: sla (sea level anomaly, m), adt (absolute dynamic topography, m),
             ugos, vgos (geostrophic velocity anomalies, m/s),
             err_sla (formal mapping error, m)

  Graceful degradation: if CMEMS_USERNAME or CMEMS_PASSWORD env vars are
  absent, returns status='not_configured' with setup instructions.
  On auth failure (401), returns status='error'.

Landmines / quirks:
  - CMEMS renamed products in 2023; old product ID
    SEALEVEL_GLO_PHY_L4_NRT_OBSERVATIONS_008_046 now resolves to
    SEALEVEL_GLO_PHY_L4_NRT_008_046. Both may appear in docs.
  - The OPeNDAP URL above may change with product reprocessing versions;
    check https://data.marine.copernicus.eu/product/SEALEVEL_GLO_PHY_L4_NRT_008_046/services
    for the current dataset ID.
  - SLA values are in metres (not mm). Multiply by 1000 for mm if needed.
  - Global 0.25° grid = 1440 × 721 cells per day; fetch a bounding box
    rather than the full global field to keep response times reasonable.
  - The Copernicus Marine Toolbox (pip install copernicusmarine) is the
    recommended Python access method; this connector uses httpx + OPeNDAP
    ASCII to avoid a heavyweight dependency.
=============================================================================
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import httpx

from backend.connectors.base import BaseConnector, ConnectorResult

# NRT L4 gridded SSH/SLA dataset — daily, 0.25°, global
_OPENDAP_BASE = (
    "https://nrt.cmems-du.eu/thredds/dodsC/"
    "cmems_obs-sl_glo_phy-ssh_nrt_allsat-l4-duacs-0.25deg_P1D"
)

# OPeNDAP ASCII (text) endpoint — append .ascii to the dataset path
_ASCII_URL = _OPENDAP_BASE + ".ascii"

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
                "4. (Optional) Install the official client: pip install copernicusmarine",
                "5. Product: SEALEVEL_GLO_PHY_L4_NRT_008_046",
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

    Fetches the daily NRT L4 gridded sea level anomaly product
    (SEALEVEL_GLO_PHY_L4_NRT_008_046) via OPeNDAP ASCII.

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

    async def fetch(
        self,
        *,
        target_date: date | None = None,
        lat_min: float = -90.0,
        lat_max: float = 90.0,
        lon_min: float = -180.0,
        lon_max: float = 180.0,
        **params: Any,
    ) -> Any:
        """Fetch sea level anomaly data from CMEMS OPeNDAP ASCII endpoint.

        Args:
            target_date: Date to fetch (default: 2 days ago, to account for NRT lag).
            lat_min, lat_max, lon_min, lon_max: Bounding box (default: global).

        Returns:
            dict with 'raw_text', 'date_fetched', and bounding box params on success.
            dict with 'status': 'not_configured' if credentials are absent.
            dict with 'status': 'error' on HTTP / connection failure.
        """
        if not self.username or not self.password:
            return {"status": "not_configured"}

        if target_date is None:
            target_date = date.today() - timedelta(days=2)

        # OPeNDAP ASCII constraint expression for a lat/lon bounding box
        # Format: variable[time_index][lat_range][lon_range]
        # We query sla and adt for the given day; use a simple date-based request.
        # The ASCII endpoint accepts OPeNDAP CE (Constraint Expression) syntax.
        constraint = (
            f"?sla[0][({lat_min}):1:({lat_max})][({lon_min}):1:({lon_max})],"
            f"adt[0][({lat_min}):1:({lat_max})][({lon_min}):1:({lon_max})]"
        )
        # For date selection we use the THREDDS catalog time-based URL pattern
        # (date suffix on the dataset path, which CMEMS OPeNDAP supports)
        date_str = target_date.strftime("%Y%m%d")
        dataset_url = (
            "https://nrt.cmems-du.eu/thredds/dodsC/"
            f"cmems_obs-sl_glo_phy-ssh_nrt_allsat-l4-duacs-0.25deg_P1D_{date_str}.ascii"
        )

        auth = (self.username, self.password)
        timeout = httpx.Timeout(120.0, connect=20.0)

        try:
            async with httpx.AsyncClient(
                timeout=timeout, follow_redirects=True, auth=auth
            ) as client:
                response = await client.get(dataset_url + constraint)
                if response.status_code == 401:
                    return {
                        "status": "error",
                        "message": (
                            "CMEMS authentication failed (HTTP 401). "
                            "Check CMEMS_USERNAME and CMEMS_PASSWORD environment variables."
                        ),
                    }
                if response.status_code == 403:
                    return {
                        "status": "error",
                        "message": (
                            "CMEMS access denied (HTTP 403). "
                            "Your account may need to accept product-specific Terms of Use "
                            "for SEALEVEL_GLO_PHY_L4_NRT_008_046. "
                            "Log in at https://data.marine.copernicus.eu/ and accept the "
                            "terms for the product before retrying."
                        ),
                    }
                if response.status_code == 404:
                    return {
                        "status": "error",
                        "message": (
                            f"CMEMS: no data found for {target_date.isoformat()} "
                            f"(HTTP 404). The NRT product may have a longer lag."
                        ),
                    }
                response.raise_for_status()
                return {
                    "raw_text": response.text,
                    "date_fetched": target_date.isoformat(),
                    "lat_min": lat_min,
                    "lat_max": lat_max,
                    "lon_min": lon_min,
                    "lon_max": lon_max,
                }
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            return {
                "status": "error",
                "message": (
                    f"CMEMS OPeNDAP connection failed: {exc}. "
                    f"Endpoint: {dataset_url}"
                ),
            }
        except httpx.HTTPStatusError as exc:
            return {
                "status": "error",
                "message": f"CMEMS HTTP {exc.response.status_code}: {exc}",
            }

    def normalize(self, raw: Any) -> ConnectorResult:
        """Parse CMEMS OPeNDAP ASCII response into SeaLevelAnomalyPoint instances.

        OPeNDAP ASCII format interleaves variable names, array dimensions, and
        comma-separated values. We do a simple line-by-line parse for the
        grid values.

        Handles graceful degradation for not_configured and error states.
        """
        # --- not_configured path ---
        if isinstance(raw, dict) and raw.get("status") == "not_configured":
            return _not_configured_result(
                self.source, self.source_url, self.cadence, self.tag
            )

        # --- error path ---
        if isinstance(raw, dict) and raw.get("status") == "error":
            return ConnectorResult(
                values=raw,
                source=self.source,
                source_url=self.source_url,
                cadence=self.cadence,
                tag=self.tag,
                spatial_scope="Global (0.25°)",
                license="Copernicus Marine Open Data Licence — free for registered users",
                notes=["Fetch failed — see values.message for details."],
            )

        # --- Normal parse path ---
        raw_text: str = raw.get("raw_text", "")
        date_fetched: str = raw.get("date_fetched", "unknown")

        # Detect HTML redirect/error page (THREDDS login or Cloudflare block)
        if raw_text.lstrip().startswith(("<!DOCTYPE", "<html", "<HTML", "<!doctype")):
            return ConnectorResult(
                values={
                    "status": "error",
                    "message": (
                        "CMEMS THREDDS returned an HTML page instead of OPeNDAP data. "
                        "This usually means the server requires product Terms of Use "
                        "acceptance. Log in at https://data.marine.copernicus.eu/ → "
                        "My account → accept terms for SEALEVEL_GLO_PHY_L4_NRT_008_046, "
                        "then retry."
                    ),
                },
                source=self.source,
                source_url=self.source_url,
                cadence=self.cadence,
                tag=self.tag,
                spatial_scope="Global (0.25°)",
                license="Copernicus Marine Open Data Licence",
                notes=["THREDDS returned HTML — product ToU acceptance needed."],
            )

        points: list[SeaLevelAnomalyPoint] = []

        # OPeNDAP ASCII is complex to parse generically; provide a minimal parse
        # that extracts (lat, lon, sla, adt) triplets.
        # The format looks like:
        #   Dataset {
        #       Array { Float32 sla[latitude=721][longitude=1440]; } sla;
        #       ...
        #   } ...;
        #   sla, [721][1440]
        #   <csv of values row by row>
        #   ...
        # We parse the value blocks for 'sla' and 'adt'.
        sla_values: list[float] = []
        adt_values: list[float] = []
        lat_values: list[float] = []
        lon_values: list[float] = []
        current_var: str | None = None
        in_data = False

        for line in raw_text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            # Detect variable name lines (start of a data block)
            if stripped.startswith("sla,"):
                current_var = "sla"
                in_data = False
                continue
            if stripped.startswith("adt,"):
                current_var = "adt"
                in_data = False
                continue
            if stripped.startswith("latitude,"):
                current_var = "latitude"
                in_data = False
                continue
            if stripped.startswith("longitude,"):
                current_var = "longitude"
                in_data = False
                continue
            # The dimension line like "[721][1440]" signals data follows
            if stripped.startswith("[") and current_var:
                in_data = True
                continue
            if in_data and current_var:
                # Parse comma-separated floats
                for token in stripped.split(","):
                    token = token.strip()
                    if not token:
                        continue
                    try:
                        val = float(token)
                        if current_var == "sla":
                            sla_values.append(val)
                        elif current_var == "adt":
                            adt_values.append(val)
                        elif current_var == "latitude":
                            lat_values.append(val)
                        elif current_var == "longitude":
                            lon_values.append(val)
                    except ValueError:
                        in_data = False  # hit a non-numeric line — end of block
                        current_var = None

        # Reconstruct grid points if we have coordinate arrays
        n_lat = len(lat_values)
        n_lon = len(lon_values)
        if n_lat > 0 and n_lon > 0 and len(sla_values) == n_lat * n_lon:
            for i, lat in enumerate(lat_values):
                for j, lon in enumerate(lon_values):
                    idx = i * n_lon + j
                    sla = sla_values[idx]
                    adt = adt_values[idx] if idx < len(adt_values) else float("nan")
                    # Skip fill values (CMEMS uses ~9.96921e+36 as _FillValue)
                    if abs(sla) > 1e10 or abs(adt) > 1e10:
                        continue
                    points.append(
                        SeaLevelAnomalyPoint(
                            lat=lat,
                            lon=lon,
                            sla_m=sla,
                            adt_m=adt,
                            date_utc=date_fetched,
                        )
                    )
        else:
            # Parse failed or empty — return raw text in values for debugging
            points = []  # type: ignore[assignment]
            return ConnectorResult(
                values={
                    "status": "error",
                    "message": (
                        "CMEMS OPeNDAP ASCII parse failed: could not extract grid arrays. "
                        "The OPeNDAP ASCII response format may have changed. "
                        "Consider switching to the copernicusmarine Python package for robust access."
                    ),
                    "raw_preview": raw_text[:2000],
                },
                source=self.source,
                source_url=self.source_url,
                cadence=self.cadence,
                tag=self.tag,
                spatial_scope="Global (0.25°)",
                license="Copernicus Marine Open Data Licence — free for registered users",
                notes=["OPeNDAP ASCII parse failed. See values.message."],
            )

        return ConnectorResult(
            values=points,
            source=self.source,
            source_url=self.source_url,
            cadence=self.cadence,
            tag=self.tag,
            spatial_scope="Global (0.25° L4 gridded altimetry)",
            license="Copernicus Marine Open Data Licence — free for registered users",
            notes=[
                f"Data date: {date_fetched}. Product: SEALEVEL_GLO_PHY_L4_NRT_008_046.",
                "sla_m: sea level anomaly (m) vs. 1993–2012 mean. "
                "adt_m: absolute dynamic topography (m).",
                "Data from merged multi-mission altimetry (DUACS processing, CNES/CLS).",
                "Known limitation: NRT product has ~1–2 day lag; coastlines and "
                "shallow seas have reduced accuracy. For climate analysis use the "
                "reprocessed MY product (SEALEVEL_GLO_PHY_L4_MY_008_047).",
                "Note: OPeNDAP ASCII endpoint URL may change with product version updates; "
                "check https://data.marine.copernicus.eu/product/SEALEVEL_GLO_PHY_L4_NRT_008_046/services "
                "for the current dataset ID.",
            ],
        )
