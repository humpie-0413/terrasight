"""NOAA GML Global CH₄ Monthly Mean connector.

Source:   https://gml.noaa.gov/ccgg/trends/ch4/
Data URL: https://gml.noaa.gov/webdata/ccgg/trends/ch4/ch4_mm_gl.txt
Cadence:  monthly
Tag:      observed

=============================================================================
Verified 2026-04-11:
  ✅ https://gml.noaa.gov/webdata/ccgg/trends/ch4/ch4_mm_gl.txt  (monthly global)

No auth, no API key, public CDN — same CDN pattern as co2_mm_mlo.txt.
Whitespace-separated text with `#` comment lines. Columns:
    year  month  decimal  average  average_unc  trend  trend_unc

Values are in ppb (nanomol/mol = parts per billion). Record starts 1983-07.

Landmines / quirks:
  - Missing-value sentinel is not documented for ch4_mm_gl but the CO₂
    convention uses -9.99 / -0.99 for stdev/unc; the average column is
    always populated for real rows.
  - ch4_mm_gl.txt is a *global* marine surface network mean, NOT a single
    station (unlike Mauna Loa CO₂). This is the preferred series for
    trend communication.
=============================================================================
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from backend.connectors.base import BaseConnector, ConnectorResult

MONTHLY_URL = "https://gml.noaa.gov/webdata/ccgg/trends/ch4/ch4_mm_gl.txt"


@dataclass
class Ch4Point:
    year: int
    month: int
    decimal_date: float
    value_ppb: float  # monthly global mean CH₄ in ppb

    @property
    def iso_month(self) -> str:
        return f"{self.year:04d}-{self.month:02d}"


class NoaaGmlCh4Connector(BaseConnector):
    """NOAA GML global CH₄ monthly mean connector.

    Returns a time series of Ch4Point dataclass instances spanning 1983–present.
    No authentication required.
    """

    name = "noaa_gml_ch4"
    source = "NOAA GML Global CH₄"
    source_url = "https://gml.noaa.gov/ccgg/trends/ch4/"
    cadence = "monthly"
    tag = "observed"

    async def fetch(self, **params: Any) -> str:
        """Download the raw monthly CH₄ global mean text file from NOAA GML."""
        timeout = httpx.Timeout(30.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(MONTHLY_URL)
            response.raise_for_status()
            return response.text

    def normalize(self, raw: str) -> ConnectorResult:
        """Parse the whitespace text file into a list of Ch4Point.

        Skips `#` comment lines. Each data row has 7 whitespace-separated
        columns; we keep year, month, decimal, and global monthly average.
        Rows with a non-positive average are skipped (missing-value defence).
        """
        points: list[Ch4Point] = []
        for line in raw.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            parts = stripped.split()
            if len(parts) < 4:
                continue
            try:
                year = int(parts[0])
                month = int(parts[1])
                decimal_date = float(parts[2])
                monthly_avg = float(parts[3])
            except ValueError:
                continue
            # Guard against any sentinel values (e.g. -9.99 or -999)
            if monthly_avg <= 0:
                continue
            points.append(
                Ch4Point(
                    year=year,
                    month=month,
                    decimal_date=decimal_date,
                    value_ppb=monthly_avg,
                )
            )

        return ConnectorResult(
            values=points,
            source=self.source,
            source_url=self.source_url,
            cadence=self.cadence,
            tag=self.tag,
            spatial_scope="Global (marine surface network composite)",
            license="Public domain (NOAA GML)",
            notes=[
                "Values are global monthly means derived from NOAA's marine surface "
                "air sampling network (~100 sites worldwide).",
                "Units: nanomol/mol (ppb). Record begins July 1983.",
                "Known limitation: global mean smooths over regional hotspots "
                "(e.g. Arctic wetland pulses, fossil fuel basins).",
            ],
        )
