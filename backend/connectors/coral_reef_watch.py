"""NOAA Coral Reef Watch (CRW) Bleaching Heat Stress connector.

Source:    https://coralreefwatch.noaa.gov/
Data API:  ERDDAP — NOAA CoastWatch PFEG
Dataset:   NOAA_DHW  (https://coastwatch.pfeg.noaa.gov/erddap/griddap/NOAA_DHW)
Cadence:   daily (NRT, ~1–2 day lag)
Tag:       near-real-time

=============================================================================
Verified 2026-04-11:
  ✅ https://coastwatch.pfeg.noaa.gov/erddap/griddap/NOAA_DHW.html

No authentication required — ERDDAP is a public API.

ERDDAP griddap query format for a spatial subset in CSV:
  https://coastwatch.pfeg.noaa.gov/erddap/griddap/NOAA_DHW.csv
    ?CRW_BAA,CRW_DHW,CRW_SST,CRW_SSTANOMALY
    [(time_start):(time_end)]
    [(lat_min):(lat_max)]
    [(lon_min):(lon_max)]

Available variables (all gridded 0.05°, global, daily 1985–present):
  CRW_BAA        — Bleaching Alert Area (ubyte 0–4)
                    0=No Stress, 1=Watch, 2=Warning, 3=Alert Level 1, 4=Alert Level 2
  CRW_DHW        — Degree Heating Week (°C·weeks)
  CRW_SST        — Sea Surface Temperature (°C, CoralTemp v3.1)
  CRW_SSTANOMALY — SST anomaly vs. climatology (°C)

Default fetch behaviour:
  - Fetches the MOST RECENT available day of data.
  - Spatial subsetting: coral-reef latitude band only (-35° to +35°), full
    longitude range, to keep response size manageable (~minutes vs. hours for
    a full global pull). Full global pull (7,200 × 3,600 grid) at CSV is
    impractical from an API; use NetCDF/OPeNDAP for bulk.
  - Only pixels with CRW_BAA > 0 (any heat stress present) are returned to
    keep payload size reasonable. Pass include_no_stress=True to return all.

Landmines / quirks:
  - The ERDDAP endpoint times are at 12:00:00Z. Pass the date as
    YYYY-MM-DDT12:00:00Z in the time slice.
  - ERDDAP returns a 2-row CSV header: variable name row + units row.
    The actual data starts at row 3.
  - CRW_BAA scale in ERDDAP NOAA_DHW goes 0–4 (NOT 0–5 as sometimes cited
    in pre-2024 documentation). Alert Level 2 = category 4.
  - Retrieving even a coral-band strip (~35°S–35°N, full longitude) for one
    day produces ~4.4M grid cells. We coarsen to every 10th pixel (0.5°
    effective) via ERDDAP stride [1:10:1] on both lat and lon to return
    ~44k points in ~5 s; still geographically representative.
  - If the latest-day query fails (ERDDAP sometimes 404s on the last day),
    connector retries with yesterday's date automatically.
=============================================================================
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import httpx

from backend.connectors.base import BaseConnector, ConnectorResult

ERDDAP_BASE = "https://coastwatch.pfeg.noaa.gov/erddap/griddap/NOAA_DHW.csv"

# Coral reef latitude band (avoids Antarctic/Arctic which have no reefs)
LAT_MIN = -35.0
LAT_MAX = 35.0
LON_MIN = -180.0
LON_MAX = 180.0

# Stride: every 10th grid cell = ~0.5° effective resolution
STRIDE = 10


@dataclass
class CoralStationReading:
    lat: float
    lon: float
    bleaching_alert: int   # 0=No Stress, 1=Watch, 2=Warning, 3=Alert L1, 4=Alert L2
    dhw: float             # Degree Heating Weeks (°C·weeks)
    sst_c: float           # Sea Surface Temperature (°C)
    sst_anomaly_c: float   # SST anomaly vs. climatology (°C)
    date_utc: str          # ISO date string YYYY-MM-DD


def _build_url(dt: date) -> str:
    """Build an ERDDAP griddap CSV URL for the given date, coarsened by STRIDE."""
    t = f"{dt.isoformat()}T12:00:00Z"
    lat_q = f"[({LAT_MIN}):{STRIDE}:({LAT_MAX})]"
    lon_q = f"[({LON_MIN}):{STRIDE}:({LON_MAX})]"
    time_q = f"[({t}):1:({t})]"
    variables = "CRW_BAA,CRW_DHW,CRW_SST,CRW_SSTANOMALY"
    return f"{ERDDAP_BASE}?{variables}{time_q}{lat_q}{lon_q}"


class CoralReefWatchConnector(BaseConnector):
    """NOAA Coral Reef Watch daily bleaching heat stress connector.

    Pulls from the ERDDAP NOAA_DHW griddap dataset hosted by NOAA CoastWatch
    PFEG. No authentication required.

    fetch() returns raw CSV text (or an error dict on failure).
    normalize() parses it into a list of CoralStationReading instances,
    filtered to pixels with any heat stress (CRW_BAA > 0) by default.
    """

    name = "coral_reef_watch"
    source = "NOAA Coral Reef Watch (CoralTemp v3.1)"
    source_url = "https://coralreefwatch.noaa.gov/"
    cadence = "daily"
    tag = "near-real-time"

    async def fetch(
        self,
        *,
        target_date: date | None = None,
        include_no_stress: bool = False,
        **params: Any,
    ) -> Any:
        """Fetch CRW bleaching data for the given date (default: most recent day).

        Args:
            target_date: Date to fetch. Defaults to yesterday (ERDDAP NRT lag ~1 day).
            include_no_stress: If True, include all pixels regardless of alert level.

        Returns:
            dict with keys 'csv_text', 'date_fetched', 'include_no_stress'.
            On failure: dict with 'status': 'error' and 'message'.
        """
        if target_date is None:
            target_date = date.today() - timedelta(days=1)

        timeout = httpx.Timeout(60.0, connect=15.0)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            # Try the requested date, then fall back to one day earlier if 404
            for attempt_date in [target_date, target_date - timedelta(days=1)]:
                url = _build_url(attempt_date)
                try:
                    response = await client.get(url)
                    if response.status_code == 404:
                        continue
                    response.raise_for_status()
                    return {
                        "csv_text": response.text,
                        "date_fetched": attempt_date.isoformat(),
                        "include_no_stress": include_no_stress,
                    }
                except httpx.HTTPStatusError as exc:
                    if exc.response.status_code == 404:
                        continue
                    return {
                        "status": "error",
                        "message": (
                            f"ERDDAP HTTP {exc.response.status_code} for "
                            f"{attempt_date.isoformat()}: {exc}"
                        ),
                    }
                except (httpx.ConnectError, httpx.TimeoutException) as exc:
                    return {
                        "status": "error",
                        "message": (
                            f"ERDDAP connection failed: {exc}. "
                            "Endpoint: https://coastwatch.pfeg.noaa.gov/erddap/griddap/NOAA_DHW"
                        ),
                    }

        return {
            "status": "error",
            "message": (
                f"No data found for {target_date.isoformat()} or the previous day "
                "from NOAA CoastWatch ERDDAP. The NRT data may have a longer lag."
            ),
        }

    def normalize(self, raw: Any) -> ConnectorResult:
        """Parse ERDDAP CSV into CoralStationReading instances.

        ERDDAP CSV format:
          Row 0: variable names (time, latitude, longitude, CRW_BAA, CRW_DHW, CRW_SST, CRW_SSTANOMALY)
          Row 1: units (UTC, degrees_north, degrees_east, ...)
          Row 2+: data rows

        Pixels over land or ice have NaN values and are skipped.
        By default, only pixels with bleaching_alert > 0 are returned.
        """
        # --- Graceful degradation path ---
        if isinstance(raw, dict) and raw.get("status") == "error":
            return ConnectorResult(
                values=raw,
                source=self.source,
                source_url=self.source_url,
                cadence=self.cadence,
                tag=self.tag,
                spatial_scope="Coral reef latitudes (35°S–35°N), global",
                license="Public domain (NOAA)",
                notes=["Fetch failed — see values.message for details."],
            )

        csv_text: str = raw["csv_text"]
        date_fetched: str = raw["date_fetched"]
        include_no_stress: bool = raw.get("include_no_stress", False)

        readings: list[CoralStationReading] = []
        reader = csv.reader(io.StringIO(csv_text))
        rows = list(reader)

        # ERDDAP always emits a 2-row header before data
        data_rows = rows[2:] if len(rows) > 2 else []

        for row in data_rows:
            if len(row) < 7:
                continue
            # Columns: time, latitude, longitude, CRW_BAA, CRW_DHW, CRW_SST, CRW_SSTANOMALY
            try:
                lat = float(row[1])
                lon = float(row[2])
                baa = row[3].strip()
                dhw_raw = row[4].strip()
                sst_raw = row[5].strip()
                anom_raw = row[6].strip()
            except (IndexError, ValueError):
                continue

            # Skip NaN / missing pixels (land, ice, cloud-contaminated)
            if any(v.lower() in ("nan", "na", "") for v in (baa, dhw_raw, sst_raw, anom_raw)):
                continue

            try:
                baa_int = int(float(baa))
                dhw = float(dhw_raw)
                sst = float(sst_raw)
                anom = float(anom_raw)
            except ValueError:
                continue

            # Filter: skip no-stress pixels unless caller asked for all
            if not include_no_stress and baa_int == 0:
                continue

            readings.append(
                CoralStationReading(
                    lat=lat,
                    lon=lon,
                    bleaching_alert=baa_int,
                    dhw=dhw,
                    sst_c=sst,
                    sst_anomaly_c=anom,
                    date_utc=date_fetched,
                )
            )

        return ConnectorResult(
            values=readings,
            source=self.source,
            source_url=self.source_url,
            cadence=self.cadence,
            tag=self.tag,
            spatial_scope="Coral reef latitudes (35°S–35°N), global, ~0.5° stride",
            license="Public domain (NOAA Coral Reef Watch / CoastWatch PFEG)",
            notes=[
                f"Data date: {date_fetched}. "
                f"{'All pixels returned.' if include_no_stress else 'Only heat-stress pixels (BAA>0) returned.'}",
                "Bleaching Alert Area scale: 0=No Stress, 1=Watch, 2=Warning, "
                "3=Alert Level 1, 4=Alert Level 2.",
                "Spatial resolution coarsened to ~0.5° (stride-10 of 0.05° grid) "
                "for API practicality; full 5 km grid available via ERDDAP direct.",
                "Known limitation: cloud cover and other QC issues may produce "
                "gaps in the NRT product; gap-free climatology available separately.",
                "ERDDAP dataset: https://coastwatch.pfeg.noaa.gov/erddap/griddap/NOAA_DHW",
            ],
        )
