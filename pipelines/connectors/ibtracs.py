"""NOAA IBTrACS (International Best Track Archive for Climate Stewardship) connector.

Source:  https://www.ncei.noaa.gov/products/international-best-track-archive
Cadence: Active storms updated approximately every 6 hours; historical best-track
         is post-analysis (best-track finalized weeks to months after storm ends).
Tag:     observed  (WMO agency consensus best-track positions and intensities)
Auth:    None required — public data.

=============================================================================
Verified endpoints (2026-04-11 spike):

  ACTIVE CSV (storms currently active or recently active, ~50KB):
    https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-stewardship-ibtracs/v04r01/access/csv/ibtracs.ACTIVE.list.v04r01.csv
    HTTP 200, Content-Type: text/csv, ~52 KB (as of 2026-04-09).
    Updated: Thu, 09 Apr 2026 — confirms near-real-time refresh.

  LAST3YEARS CSV (~8.8 MB):
    https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-stewardship-ibtracs/v04r01/access/csv/ibtracs.last3years.list.v04r01.csv
    HTTP 200, Content-Type: text/csv.
    NOTE: The URL uses "last3years" (not "LAST3YR"). The alternate form
    "ibtracs.LAST3YR.list.v04r01.csv" returns HTTP 404.

CSV header layout — TWO rows, not one:
  Row 0: column names (e.g. SID, SEASON, NAME, ISO_TIME, LAT, LON, ...)
  Row 1: units row (e.g. , Year, , , , , ..., degrees_north, degrees_east, kts, mb, ...)
  The units row must be skipped or DictReader will treat it as a data row.

Key columns used by this connector:
  SID         — unique storm ID, e.g. "2026092S11074"
  SEASON      — year integer
  NUMBER      — storm number within season
  BASIN       — 2-letter basin code: NA, EP, WP, NI, SI, SP, SA
  NAME        — storm name (UNNAMED if not named)
  ISO_TIME    — observation time, format "YYYY-MM-DD HH:MM:SS" UTC
  LAT         — latitude, degrees north (WMO consensus)
  LON         — longitude, degrees east (WMO consensus)
  WMO_WIND    — max sustained wind speed, knots (WMO consensus); blank if unknown
  WMO_PRES    — minimum central pressure, hPa (WMO consensus); blank if unknown
  USA_SSHS    — Saffir-Simpson Hurricane Wind Scale category assigned by NHC/JTWC:
                 -5 = unknown, -4 = post-tropical, -3 = misc., -2 = subtropical,
                 -1 = tropical depression, 0 = tropical storm, 1-5 = hurricane cat.

LANDMINES:
  - CSV has two header rows. Using csv.reader to skip row 1 before DictReader.
  - Many numeric fields are blank strings for non-WMO basins or old storms.
    Always guard with `or 0` / try/except on float conversion.
  - WMO_WIND and WMO_PRES are consensus values; USA_WIND/USA_PRES are
    NHC-only and may differ. We use WMO values for cross-basin consistency.
  - USA_SSHS is only set when USA_AGENCY is authoritative (NHC/JTWC).
    For other basins it may be blank or -5.
  - ACTIVE file can be empty (no active storms) — normalize() must handle 0 rows.
  - The ACTIVE CSV is refreshed ~6h; LAST3YEARS is refreshed less frequently.
  - File size: ACTIVE ~50KB (fine), LAST3YEARS ~8.8MB (use 120s timeout).
  - TRACK_TYPE = "PROVISIONAL" for in-progress observations; "main" for best-track.
=============================================================================
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from typing import Any

import httpx

from backend.connectors.base import BaseConnector, ConnectorResult

# Verified working URLs (2026-04-11 spike)
ACTIVE_URL = (
    "https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-"
    "stewardship-ibtracs/v04r01/access/csv/ibtracs.ACTIVE.list.v04r01.csv"
)
LAST3YEARS_URL = (
    "https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-"
    "stewardship-ibtracs/v04r01/access/csv/ibtracs.last3years.list.v04r01.csv"
)


def _safe_float(value: str, default: float = 0.0) -> float:
    """Convert a potentially blank/whitespace IBTrACS field to float."""
    try:
        return float(value.strip())
    except (ValueError, AttributeError):
        return default


def _safe_int(value: str, default: int = -5) -> int:
    """Convert a potentially blank IBTrACS integer field."""
    try:
        return int(float(value.strip()))
    except (ValueError, AttributeError):
        return default


@dataclass
class StormTrackPoint:
    """Single 6-hourly observation along a storm track."""

    iso_time: str    # "YYYY-MM-DD HH:MM:SS" UTC, from ISO_TIME column
    lat: float       # degrees north (WMO consensus LAT)
    lon: float       # degrees east (WMO consensus LON)
    wind_kt: float   # max sustained wind in knots (WMO_WIND); 0 if missing
    pres_hpa: float  # minimum central pressure in hPa (WMO_PRES); 0 if missing
    sshs: int        # Saffir-Simpson category (USA_SSHS); -5 if unknown/not set
    track_type: str  # "main", "PROVISIONAL", "spur", etc.


@dataclass
class TropicalStorm:
    """A single tropical cyclone with all its track points."""

    sid: str     # unique storm ID, e.g. "2024101N10324"
    name: str    # storm name ("UNNAMED" when not officially named)
    season: int  # calendar year
    basin: str   # 2-letter WMO basin: NA EP WP NI SI SP SA
    track: list[StormTrackPoint] = field(default_factory=list)

    @property
    def latest_point(self) -> StormTrackPoint | None:
        """Most recent track observation (last row for this SID in the CSV)."""
        return self.track[-1] if self.track else None

    @property
    def peak_wind_kt(self) -> float:
        """Maximum wind speed recorded across all track points."""
        return max((p.wind_kt for p in self.track), default=0.0)

    @property
    def peak_sshs(self) -> int:
        """Highest Saffir-Simpson category recorded across all track points."""
        return max((p.sshs for p in self.track), default=-5)


def _parse_csv(raw: str) -> list[TropicalStorm]:
    """Parse IBTrACS CSV text into a list of TropicalStorm objects.

    The CSV has two header rows:
      Row 0 — column names
      Row 1 — units (must be skipped before parsing data rows)
    """
    lines = io.StringIO(raw)

    # Read row 0 as the header
    reader = csv.reader(lines)
    try:
        header = next(reader)
    except StopIteration:
        return []

    # Skip row 1 (units row) — it looks like: " ,Year, , , , ,..."
    try:
        next(reader)
    except StopIteration:
        return []

    # Now wrap the remaining lines with DictReader using the captured header
    remaining_text = lines.read()
    dict_reader = csv.DictReader(io.StringIO(remaining_text), fieldnames=header)

    storms: dict[str, TropicalStorm] = {}
    for row in dict_reader:
        sid = row.get("SID", "").strip()
        if not sid:
            continue

        if sid not in storms:
            storms[sid] = TropicalStorm(
                sid=sid,
                name=row.get("NAME", "UNNAMED").strip() or "UNNAMED",
                season=_safe_int(row.get("SEASON", ""), default=0),
                basin=row.get("BASIN", "").strip(),
            )

        try:
            point = StormTrackPoint(
                iso_time=row.get("ISO_TIME", "").strip(),
                lat=_safe_float(row.get("LAT", "")),
                lon=_safe_float(row.get("LON", "")),
                wind_kt=_safe_float(row.get("WMO_WIND", ""), default=0.0),
                pres_hpa=_safe_float(row.get("WMO_PRES", ""), default=0.0),
                sshs=_safe_int(row.get("USA_SSHS", ""), default=-5),
                track_type=row.get("TRACK_TYPE", "").strip(),
            )
            storms[sid].track.append(point)
        except Exception:
            # Malformed row — skip silently
            continue

    return list(storms.values())


class IbtracsCsvConnector(BaseConnector):
    """Connector for NOAA IBTrACS tropical storm best-track data.

    By default fetches the ACTIVE storms CSV (~50KB, refreshed ~6h) which is
    suitable for a globe overlay.  Set ``use_last3years=True`` to fetch the
    full last-3-years archive (~8.8MB) for historical track rendering.
    """

    name = "ibtracs"
    source = "NOAA IBTrACS v04r01"
    source_url = "https://www.ncei.noaa.gov/products/international-best-track-archive"
    cadence = "NRT ~6h (active storms)"
    tag = "observed"

    def __init__(self, use_last3years: bool = False) -> None:
        self.use_last3years = use_last3years

    async def fetch(self, use_last3years: bool | None = None, **_: Any) -> str:
        """Download IBTrACS CSV and return raw text.

        Args:
            use_last3years: If True, fetch last-3-years archive instead of active.
                            Overrides instance-level setting if provided.
        """
        want_last3 = use_last3years if use_last3years is not None else self.use_last3years
        url = LAST3YEARS_URL if want_last3 else ACTIVE_URL
        # Last3years is ~8.8MB; active is ~50KB. Use a generous timeout for both.
        timeout = httpx.Timeout(120.0, connect=15.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text

    def normalize(self, raw: str) -> ConnectorResult:
        """Parse IBTrACS CSV text into a ConnectorResult with TropicalStorm values."""
        storms = _parse_csv(raw)

        source_label = (
            "IBTrACS last-3-years archive" if self.use_last3years else "IBTrACS active storms"
        )

        return ConnectorResult(
            values=storms,
            source=self.source,
            source_url=self.source_url,
            cadence=self.cadence,
            tag=self.tag,
            spatial_scope="Global",
            license="Public domain (NOAA NCEI)",
            notes=[
                f"{source_label}: {len(storms)} storm(s) parsed.",
                "WMO_WIND and WMO_PRES are multi-agency consensus values in knots / hPa.",
                "USA_SSHS is the Saffir-Simpson category from NHC/JTWC; may be -5 (unknown) "
                "for non-Atlantic/East-Pacific basins or older records.",
                "TRACK_TYPE='PROVISIONAL' means the observation is in-progress and may be revised.",
                "Active file (~50KB) is refreshed ~6h; last-3-years file (~8.8MB) less frequently.",
                "Many numeric fields are blank for non-WMO-agency basins — treated as 0 or -5.",
            ],
        )
