"""NSIDC Sea Ice Index connector.

Source:  https://nsidc.org/data/seaice_index
Dataset: G02135 v4.0 (AMSR2 passive microwave)
Cadence: daily; card displays 5-day running mean
Tag:     observed
Record start: 1978-10

=============================================================================
Verified 2026-04-10:
  ✅ https://noaadata.apps.nsidc.org/NOAA/G02135/north/daily/data/N_seaice_extent_daily_v4.0.csv
  ✅ https://noaadata.apps.nsidc.org/NOAA/G02135/south/daily/data/S_seaice_extent_daily_v4.0.csv

Public HTTPS, no auth, direct CSV. Columns:
    Year, Month, Day, Extent (10^6 sq km), Missing, Source Data

NOTE: The "Source Data" column contains comma-separated file paths wrapped
in brackets and quotes, so you MUST use a proper CSV parser — a naive
`line.split(',')` will mangle the extent column.

The home card uses the 5-day running mean of the Arctic extent (per
CLAUDE.md Climate Trends spec). We compute it client-side from the daily
file. For the 12-month sparkline we aggregate the daily series into
calendar-month means.

NSIDC recently downgraded dataset support to "Basic" due to funding cuts;
files still update daily as of verification. JAXA AMSR2 at University of
Bremen is an independent fallback.
=============================================================================
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from typing import Any

import httpx

from backend.connectors.base import BaseConnector, ConnectorResult

DAILY_ARCTIC_URL = (
    "https://noaadata.apps.nsidc.org/NOAA/G02135/north/daily/data/"
    "N_seaice_extent_daily_v4.0.csv"
)


@dataclass
class SeaIcePoint:
    year: int
    month: int
    day: int
    extent_million_km2: float  # 10^6 sq km

    @property
    def iso_date(self) -> str:
        return f"{self.year:04d}-{self.month:02d}-{self.day:02d}"

    @property
    def year_month(self) -> str:
        return f"{self.year:04d}-{self.month:02d}"


class NsidcConnector(BaseConnector):
    name = "nsidc"
    source = "NSIDC Sea Ice Index"
    source_url = "https://nsidc.org/data/seaice_index"
    cadence = "daily (5-day running mean)"
    tag = "observed"

    async def fetch(self, **params: Any) -> str:
        timeout = httpx.Timeout(30.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(DAILY_ARCTIC_URL)
            response.raise_for_status()
            return response.text

    def normalize(self, raw: str) -> ConnectorResult:
        """Parse daily CSV into a list of SeaIcePoint.

        The second row contains units (e.g. "YYYY, MM, DD, 10^6 sq km, ...").
        We skip rows whose first column is not an integer year.
        """
        reader = csv.reader(io.StringIO(raw))
        points: list[SeaIcePoint] = []
        for row in reader:
            if len(row) < 4:
                continue
            try:
                year = int(row[0].strip())
                month = int(row[1].strip())
                day = int(row[2].strip())
                extent = float(row[3].strip())
            except ValueError:
                # header row, unit row, or malformed line
                continue
            if extent <= 0:
                continue
            points.append(
                SeaIcePoint(
                    year=year,
                    month=month,
                    day=day,
                    extent_million_km2=extent,
                )
            )

        return ConnectorResult(
            values=points,
            source=self.source,
            source_url=self.source_url,
            cadence=self.cadence,
            tag=self.tag,
            spatial_scope="Arctic (Northern hemisphere)",
            license="Public domain (NSIDC / NOAA)",
            notes=[
                "Dataset G02135 v4.0 (AMSR2 passive microwave).",
                "Home card shows 5-day running mean; sparkline uses "
                "calendar-month means aggregated from the daily series.",
                "NSIDC support level downgraded to Basic in late 2025; "
                "JAXA AMSR2 at U. Bremen is an independent fallback.",
            ],
        )


def five_day_mean(points: list[SeaIcePoint]) -> float | None:
    """Trailing 5-day running mean of extent for the most recent observations."""
    if not points:
        return None
    window = points[-5:]
    return sum(p.extent_million_km2 for p in window) / len(window)


def monthly_means(points: list[SeaIcePoint]) -> list[tuple[str, float]]:
    """Collapse daily points into (YYYY-MM, mean_extent) tuples, ordered."""
    buckets: dict[str, list[float]] = {}
    order: list[str] = []
    for p in points:
        key = p.year_month
        if key not in buckets:
            buckets[key] = []
            order.append(key)
        buckets[key].append(p.extent_million_km2)
    return [(k, sum(buckets[k]) / len(buckets[k])) for k in order]
