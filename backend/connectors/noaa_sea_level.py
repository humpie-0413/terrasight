"""NOAA Laboratory for Satellite Altimetry — Global Mean Sea Level connector.

Source:   https://www.star.nesdis.noaa.gov/socd/lsa/SeaLevelRise/
Data URL: https://www.star.nesdis.noaa.gov/socd/lsa/SeaLevelRise/slr/slr_sla_gbl_free_all_66.csv
Cadence:  ~10-day (altimeter repeat cycle)
Tag:      observed

=============================================================================
Verified 2026-04-11:
  ✅ https://www.star.nesdis.noaa.gov/socd/lsa/SeaLevelRise/slr/slr_sla_gbl_free_all_66.csv

No auth, no API key. The "free_all_66" variant covers 66°S–66°N with the
annual cycle removed ("free" = free of seasonal signal).

Column format — CSV with header comment lines starting with `HDR`:
  - Column 0: decimal year (e.g. 1992.96140)
  - Remaining columns: per-mission SLA values in mm (TOPEX/Poseidon,
    Jason-1, Jason-2, Jason-3, Sentinel-6MF). Missions don't overlap in
    time; only one column will be non-empty per row.

The NOAA NESDIS LSA series is produced continuously since 1992 from
TOPEX/Poseidon → Jason → Sentinel-6 satellite altimeters.

Landmines / quirks:
  - The file URL changed from *_txj1j2_90.csv (old naming) to
    *_free_all_66.csv (current naming circa 2023+). Always use the
    current _free_all_66 variant; the old URL returns ECONNREFUSED.
  - Values are *anomalies* relative to a 1993–2012 mean (not absolute
    sea level). This is standard practice in altimetry.
  - Missing/gap values appear as empty CSV cells or "nan"; treat as None.
  - The NESDIS server occasionally refuses connections — caller should
    catch httpx.ConnectError and return status=error.
=============================================================================
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from typing import Any

import httpx

from backend.connectors.base import BaseConnector, ConnectorResult

GMSL_URL = (
    "https://www.star.nesdis.noaa.gov/socd/lsa/SeaLevelRise/slr/"
    "slr_sla_gbl_free_all_66.csv"
)

# Column indices in the CSV (after header rows are stripped)
_COL_YEAR_FRAC = 0
# Columns 1..N are per-mission SLA values; we merge them into one value per row.


@dataclass
class SeaLevelPoint:
    year_fraction: float  # decimal year (e.g. 2023.5)
    gmsl_mm: float        # global mean sea level anomaly in mm (re: 1993–2012 mean)
    uncertainty_mm: float  # placeholder — NESDIS CSV does not include formal unc
    date_str: str          # YYYY or YYYY-MM approximated from decimal year


def _decimal_year_to_date_str(dy: float) -> str:
    """Approximate ISO date string from decimal year (month precision)."""
    year = int(dy)
    month_frac = (dy - year) * 12.0
    month = max(1, min(12, int(month_frac) + 1))
    return f"{year:04d}-{month:02d}"


class NoaaSeaLevelConnector(BaseConnector):
    """NOAA NESDIS Laboratory for Satellite Altimetry global mean sea level connector.

    Returns a time series of SeaLevelPoint instances from 1992 to present
    (~10-day cadence, one value per altimeter pass cycle).
    No authentication required.
    """

    name = "noaa_sea_level"
    source = "NOAA NESDIS Laboratory for Satellite Altimetry"
    source_url = "https://www.star.nesdis.noaa.gov/socd/lsa/SeaLevelRise/"
    cadence = "~10-day (altimeter repeat cycle)"
    tag = "observed"

    async def fetch(self, **params: Any) -> str | dict:
        """Download the global mean sea level CSV from NOAA NESDIS.

        Returns the raw text on success, or a dict with status='error' on failure.
        """
        timeout = httpx.Timeout(45.0, connect=15.0)
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                response = await client.get(GMSL_URL)
                response.raise_for_status()
                return response.text
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            return {
                "status": "error",
                "message": (
                    f"NESDIS server connection failed: {exc}. "
                    "The star.nesdis.noaa.gov host occasionally refuses connections. "
                    "Retry later or check https://www.star.nesdis.noaa.gov/socd/lsa/SeaLevelRise/ "
                    "for service status."
                ),
            }
        except httpx.HTTPStatusError as exc:
            return {
                "status": "error",
                "message": f"HTTP {exc.response.status_code} from NESDIS sea level endpoint.",
            }

    def normalize(self, raw: Any) -> ConnectorResult:
        """Parse the NESDIS CSV into SeaLevelPoint instances.

        Handles graceful degradation if fetch() returned an error dict.
        """
        # --- Graceful degradation path ---
        if isinstance(raw, dict):
            return ConnectorResult(
                values=raw,
                source=self.source,
                source_url=self.source_url,
                cadence=self.cadence,
                tag=self.tag,
                spatial_scope="Global ocean (66°S–66°N)",
                license="Public domain (NOAA NESDIS)",
                notes=["Fetch failed — see values.message for details."],
            )

        # --- Normal parse path ---
        points: list[SeaLevelPoint] = []
        reader = csv.reader(io.StringIO(raw))

        for row in reader:
            if not row:
                continue
            first = row[0].strip()
            # Skip comment / header lines starting with HDR, #, or non-numeric
            if not first or first.upper().startswith("HDR") or first.startswith("#"):
                continue
            try:
                year_frac = float(first)
            except ValueError:
                continue

            # Collect the first non-empty, parseable SLA value from mission columns
            sla_mm: float | None = None
            for cell in row[1:]:
                cell = cell.strip()
                if not cell or cell.lower() in ("nan", "na", ""):
                    continue
                try:
                    val = float(cell)
                    sla_mm = val
                    break
                except ValueError:
                    continue

            if sla_mm is None:
                continue

            points.append(
                SeaLevelPoint(
                    year_fraction=year_frac,
                    gmsl_mm=sla_mm,
                    uncertainty_mm=0.0,  # NESDIS "free" file does not include formal unc
                    date_str=_decimal_year_to_date_str(year_frac),
                )
            )

        return ConnectorResult(
            values=points,
            source=self.source,
            source_url=self.source_url,
            cadence=self.cadence,
            tag=self.tag,
            spatial_scope="Global ocean (66°S–66°N)",
            license="Public domain (NOAA NESDIS)",
            notes=[
                "Values are sea level anomalies relative to the 1993–2012 mean. "
                "Missions: TOPEX/Poseidon (1992–2002), Jason-1 (2002–2008), "
                "Jason-2 (2008–2016), Jason-3 (2016–2022), Sentinel-6MF (2022–).",
                "Annual cycle removed ('free' variant, 66°S–66°N).",
                "uncertainty_mm is 0.0 — the NESDIS 'free' CSV does not include "
                "formal per-cycle uncertainty; use ±4–8 mm as a rough observational "
                "accuracy estimate.",
                "Known limitation: NESDIS server (star.nesdis.noaa.gov) occasionally "
                "refuses connections; implement caching / retry in the scheduler.",
            ],
        )
