"""NOAA GML Mauna Loa CO2 connector.

Source:  https://gml.noaa.gov/ccgg/trends/data.html
Cadence: monthly (daily also available)
Tag:     observed
Record start: 1958 (March)

=============================================================================
Verified 2026-04-10 (first vertical slice):
  ✅ https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_mm_mlo.txt   (monthly)
  ✅ https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_daily_mlo.txt (daily)

No auth, no API key, public CDN. Whitespace-separated text with `#`
comment lines. Columns for monthly file:
    year  month  decimal_date  monthly_avg  deseasonalized  ndays  stdev  unc

Missing / interpolated values use negative sentinels (-9.99, -0.99) in the
stdev/unc columns only; monthly_avg is always populated for every row.

NOTE: Measurements were suspended Nov 2022 – Jul 2023 due to the Mauna Loa
eruption; those months come from the Maunakea Observatories site ~21 miles
north. NOAA treats the series as continuous.
=============================================================================
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from backend.connectors.base import BaseConnector, ConnectorResult

MONTHLY_URL = "https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_mm_mlo.txt"


@dataclass
class Co2Point:
    year: int
    month: int
    decimal_date: float
    value_ppm: float  # monthly mean (column 4, "average")

    @property
    def iso_month(self) -> str:
        return f"{self.year:04d}-{self.month:02d}"


class NoaaGmlConnector(BaseConnector):
    name = "noaa_gml"
    source = "NOAA GML Mauna Loa"
    source_url = "https://gml.noaa.gov/ccgg/trends/"
    cadence = "monthly"
    tag = "observed"

    async def fetch(self, **params: Any) -> str:
        """Download the raw monthly CO2 text file from NOAA GML."""
        timeout = httpx.Timeout(30.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(MONTHLY_URL)
            response.raise_for_status()
            return response.text

    def normalize(self, raw: str) -> ConnectorResult:
        """Parse the whitespace text file into a list of Co2Point.

        Skips `#` comment lines. Each data row has 7 whitespace-separated
        columns; we keep year, month, decimal_date, and monthly average.
        """
        points: list[Co2Point] = []
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
            # Defensive: ignore missing-value sentinels if NOAA ever uses them
            # in the monthly_avg column.
            if monthly_avg <= 0:
                continue
            points.append(
                Co2Point(
                    year=year,
                    month=month,
                    decimal_date=decimal_date,
                    value_ppm=monthly_avg,
                )
            )

        return ConnectorResult(
            values=points,
            source=self.source,
            source_url=self.source_url,
            cadence=self.cadence,
            tag=self.tag,
            spatial_scope="Mauna Loa, Hawaii (global background proxy)",
            license="Public domain (NOAA GML)",
            notes=[
                "Values are monthly means constructed from daily means.",
                "Nov 2022 – Jul 2023 observations are from Maunakea Observatories "
                "due to the Mauna Loa eruption; NOAA treats the series as continuous.",
            ],
        )
