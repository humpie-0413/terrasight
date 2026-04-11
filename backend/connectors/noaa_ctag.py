"""NOAA Global Temperature Anomaly connector.

Source:  NOAAGlobalTemp CDR v6.1 (NCEI)
Cadence: monthly (preliminary, subject to revision)
Tag:     near-real-time (preliminary monthly release)
Record start: 1850 (global land+ocean)

=============================================================================
BACKGROUND:
The CLAUDE.md spec names "NOAA Climate at a Glance (CtaG)" for the Climate
Trends global temperature anomaly card. CtaG itself has no public REST API
— it is a UI on top of the NOAAGlobalTemp CDR. Per the 2026-04-10 API spike
(Agent 2, recommended fallback), we pivot to NOAAGlobalTemp CDR NetCDF/ASCII
time series files hosted on ncei.noaa.gov.

Verified 2026-04-10:
  ✅ https://www.ncei.noaa.gov/data/noaa-global-surface-temperature/v6.1/
        access/timeseries/aravg.mon.land_ocean.90S.90N.v6.1.0.YYYYMM.asc

The filename embeds YYYYMM of the latest data month, so we scrape the
directory index to discover the current file.

Columns (monthly file, from 00_Readme_timeseries.txt):
    1: year
    2: month
    3: anomaly (K, i.e. °C above 1991-2020 baseline)
    4-10: error variances + diagnostics (ignored by us)

NOTE: NOAAGlobalTemp uses the 1991-2020 climatology as baseline. Many
popular products (HadCRUT, GISTEMP) use different baselines — remember
this when comparing magnitudes against other sources.

City-level time series (the original CtaG use case for Local Reports
Block 2):

  Verified 2026-04-11: NOAA Climate at a Glance city/time-series endpoint
  returns HTTP 404 for all URL patterns tested:
    - /access/monitoring/climate-at-a-glance/city/time-series/{USW_STATION}/…
    - /cag/city/time-series/{STATE-CODE}/…
  The CtaG city interface is JavaScript-rendered with no public REST/CSV
  API. Climate Normals (climate_normals.py) is the Block 2 baseline
  fallback and will remain so until NOAA exposes a programmatic city-
  series endpoint or a scraping solution is approved.
=============================================================================
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import httpx

from backend.connectors.base import BaseConnector, ConnectorResult

TIMESERIES_DIR = (
    "https://www.ncei.noaa.gov/data/noaa-global-surface-temperature/"
    "v6.1/access/timeseries/"
)
# Monthly, global (90S-90N), land+ocean merged.
FILE_PREFIX = "aravg.mon.land_ocean.90S.90N.v6.1.0."
FILE_PATTERN = re.compile(
    r'href="(aravg\.mon\.land_ocean\.90S\.90N\.v6\.1\.0\.(\d{6})\.asc)"'
)


@dataclass
class TempAnomalyPoint:
    year: int
    month: int
    anomaly_c: float  # °C vs 1991-2020 baseline

    @property
    def iso_month(self) -> str:
        return f"{self.year:04d}-{self.month:02d}"


class NoaaCtagConnector(BaseConnector):
    name = "noaa_ctag"
    # Surface label kept as "NOAA Global Temperature" for the user-facing card;
    # CLAUDE.md referenced CtaG, but CtaG is the UI — the data is NOAAGlobalTemp.
    source = "NOAA Global Temperature (NOAAGlobalTemp v6.1)"
    source_url = (
        "https://www.ncei.noaa.gov/products/land-based-station/"
        "noaa-global-temp"
    )
    cadence = "monthly (preliminary)"
    tag = "near-real-time"

    async def fetch(self, **params: Any) -> str:
        """Discover the latest monthly ASCII file and return its contents."""
        timeout = httpx.Timeout(30.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            # 1. Fetch directory index to find the most recent YYYYMM file.
            index_res = await client.get(TIMESERIES_DIR)
            index_res.raise_for_status()
            matches = FILE_PATTERN.findall(index_res.text)
            if not matches:
                raise RuntimeError(
                    f"No matching NOAAGlobalTemp monthly file found at {TIMESERIES_DIR}"
                )
            # Pick the lexicographically largest YYYYMM (safe: 6-digit numeric).
            latest_file = max(matches, key=lambda m: m[1])[0]

            # 2. Download the ASCII time series.
            data_res = await client.get(TIMESERIES_DIR + latest_file)
            data_res.raise_for_status()
            return data_res.text

    def normalize(self, raw: str) -> ConnectorResult:
        """Parse whitespace ASCII into a list of TempAnomalyPoint.

        Ignores rows with the -999 missing-value sentinel in the anomaly
        column (defensive — not observed in recent files).
        """
        points: list[TempAnomalyPoint] = []
        for line in raw.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            parts = stripped.split()
            if len(parts) < 3:
                continue
            try:
                year = int(parts[0])
                month = int(parts[1])
                anomaly = float(parts[2])
            except ValueError:
                continue
            if anomaly <= -900:  # -999 sentinel
                continue
            points.append(
                TempAnomalyPoint(
                    year=year,
                    month=month,
                    anomaly_c=anomaly,
                )
            )

        return ConnectorResult(
            values=points,
            source=self.source,
            source_url=self.source_url,
            cadence=self.cadence,
            tag=self.tag,
            spatial_scope="Global (90°S–90°N land + ocean)",
            license="Public domain (NOAA NCEI)",
            notes=[
                "Anomalies are °C relative to the 1991-2020 climatology.",
                "Sourced from NOAAGlobalTemp CDR v6.1; CtaG UI sits on top of "
                "this dataset but exposes no public REST API.",
                "Latest months are preliminary and subject to revision.",
            ],
        )
