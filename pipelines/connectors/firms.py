"""NASA FIRMS (Fire Information for Resource Management System) v2 connector.

Source:  https://firms.modaps.eosdis.nasa.gov/
Cadence: near-real-time (~3h latency)
Tag:     near-real-time  (v2 vocabulary — see `docs/datasets/source-spike-matrix.md` §5)
Auth:    free MAP_KEY (register at https://firms.modaps.eosdis.nasa.gov/api/map_key/)

Contract:
    `normalize(raw_csv)` returns `ConnectorResult(values=list[dict])`, and
    every dict matches the pydantic `EventPoint` shape from
    `pipelines.contracts` (frozen in `docs/datasets/normalized-contracts.md` §3).

Endpoint:
    https://firms.modaps.eosdis.nasa.gov/api/area/csv/{MAP_KEY}/VIIRS_SNPP_NRT/world/{days}
        days ∈ [1..10] (NRT products)

CSV columns (VIIRS_SNPP_NRT):
    latitude, longitude, bright_ti4, scan, track, acq_date, acq_time,
    satellite, instrument, confidence, version, bright_ti5, frp, daynight

=============================================================================
LANDMINES (every one of these has drawn blood at least once):

1.  MAP_KEY is a URL PATH SEGMENT, not an Authorization header. Getting the
    header form right is irrelevant — FIRMS ignores headers entirely.

2.  Bad MAP_KEY returns **HTTP 400** with `"Invalid MAP_KEY"` in the body.
    NOT 401 and NOT 403 as you'd expect for auth. A 403 from FIRMS means
    something else (usually blocked transit, not credentials). The connector
    must detect the 400 + "Invalid MAP_KEY" pair and return
    `ConnectorResult(status="error", values=[], notes=["Invalid MAP_KEY"])`.

3.  Empty feed = header-only CSV (one header line, then EOF). That is a
    valid `status="ok", values=[]` response, not an error. The previous
    globe briefly treated it as an error and fell into a retry loop.

4.  VIIRS `confidence` is the string enum `n|l|h` (nominal/low/high), NOT
    a 0..100 integer as MODIS returns. Publishing the raw letter to the UI
    was a bug — we map to full words in `label`, keep raw in
    `properties.confidence_raw`.

5.  `acq_time` is given as HHMM WITHOUT a colon, often not zero-padded for
    pre-10:00 UTC. `"930"` → treat as `"0930"`. Combine with `acq_date`
    (`YYYY-MM-DD`) and suffix `:00Z` to produce ISO-8601 UTC.

6.  Full global 24h feed is ~30k+ rows during fire season (Amazon peaks
    >100k). Normalize() must be linear — no per-row `httpx` calls, no
    quadratic joins. The Worker caps size upstream via bbox/days.

7.  FIRMS returns `longitude` in -180..180 already, but at least one
    archived run had stray 360-offset rows. We clamp defensively
    (`lon = ((lon + 180) % 360) - 180`) before emitting.

8.  FIRMS occasionally returns `frp = ""` or absent (MODIS legacy rows).
    Treat missing/non-numeric as 0.0 and keep the row (the fire is still
    real; we just don't know its radiative power).

9.  Rate limit: 5,000 transactions / 10 minutes / MAP_KEY. The Worker cache
    (TTL 600s) keeps us well inside that.

10. Some CSV rows have trailing whitespace in `satellite` (`"N "`). We
    `.strip()` all string fields defensively.
=============================================================================
"""
from __future__ import annotations

import csv
import hashlib
import io
from typing import Any

import httpx

from pipelines.connectors.base import BaseConnector, ConnectorResult

FIRMS_BASE = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
DEFAULT_SOURCE = "VIIRS_SNPP_NRT"
DEFAULT_AREA = "world"
DEFAULT_DAYS = 1

_CONFIDENCE_MAP = {"n": "nominal", "l": "low", "h": "high"}

# Substring that signals a FIRMS "bad MAP_KEY" body. FIRMS returns plain text
# on error, not JSON, so we do a cheap substring test rather than parse.
_INVALID_KEY_MARKER = "Invalid MAP_KEY"


def detect_error_body(raw: str) -> str | None:
    """Return a short operator-facing string if `raw` looks like a FIRMS
    error body, else None.

    This is exposed separately so contract tests can drive it without
    hitting the network, and so the Worker could reuse the same detection
    rule (currently the Worker uses HTTP status directly — see
    `apps/worker/src/routes/fires.ts`).
    """
    if not raw:
        return None
    sample = raw[:512]
    if _INVALID_KEY_MARKER in sample:
        return "Invalid MAP_KEY"
    # FIRMS has also been seen returning "<!DOCTYPE html" on transient
    # gateway errors. Treat any HTML-shaped body as an error.
    stripped = sample.lstrip().lower()
    if stripped.startswith("<!doctype") or stripped.startswith("<html"):
        return "Upstream returned HTML (gateway error)"
    return None


def _clamp_lon(lon: float) -> float:
    """Defensive: FIRMS gives -180..180 but a handful of archived rows have
    drifted by 360. Normalize to -180..180."""
    if -180.0 <= lon <= 180.0:
        return lon
    return ((lon + 180.0) % 360.0) - 180.0


def _clamp_lat(lat: float) -> float:
    return max(-90.0, min(90.0, lat))


def _pad_time(hhmm: str) -> str:
    """`"930"` → `"0930"`. `"1045"` stays."""
    s = (hhmm or "").strip()
    if not s:
        return "0000"
    return s.zfill(4)


def _to_iso_utc(acq_date: str, acq_time: str) -> str:
    """Combine FIRMS `acq_date` (YYYY-MM-DD) + `acq_time` (HHMM) into
    ISO-8601 UTC. Returns `observedAt` string used in the EventPoint."""
    d = (acq_date or "").strip()
    t = _pad_time(acq_time)
    hh, mm = t[:2], t[2:4]
    return f"{d}T{hh}:{mm}:00Z"


def _confidence_word(raw: str) -> str:
    """`n|l|h` → `nominal|low|high`. Unknown values pass through unchanged
    so we don't silently lose information."""
    key = (raw or "").strip().lower()
    return _CONFIDENCE_MAP.get(key, key or "unknown")


def _stable_id(lat: float, lon: float, acq_date: str, acq_time: str) -> str:
    """Hash of the 4-tuple so re-runs produce identical IDs for the same
    observation — required by the spec for de-duplication across cache
    windows."""
    key = f"{lat}|{lon}|{acq_date}|{acq_time}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]


def _safe_float(value: object, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        s = str(value).strip()
        if not s:
            return default
        return float(s)
    except (ValueError, TypeError):
        return default


class FirmsConnector(BaseConnector):
    """FIRMS VIIRS_SNPP_NRT wildfire connector (v2 contract)."""

    name = "firms"
    source = "NASA FIRMS"
    source_url = "https://firms.modaps.eosdis.nasa.gov/"
    cadence = "NRT ~3h"
    tag = "near-real-time"

    async def fetch(
        self,
        map_key: str | None = None,
        days: int = DEFAULT_DAYS,
        source: str = DEFAULT_SOURCE,
        area: str = DEFAULT_AREA,
        **_: Any,
    ) -> str:
        """Fetch raw CSV from FIRMS area API.

        Landmine #2 handling: a 400 returned by FIRMS is a bad-MAP_KEY signal.
        We DO NOT raise — we return the body so `normalize()` can flag it
        as `status="error"`. All other 4xx/5xx raise transport errors the
        caller is expected to catch (graceful degradation belongs one level
        up, in the job or the Worker).
        """
        if not map_key:
            # No key supplied at all. Caller gets back an error-shaped CSV
            # stub; the Worker should short-circuit with `not_configured`
            # before ever calling `fetch`.
            return "Invalid MAP_KEY (no key supplied)"
        safe_days = max(1, min(10, int(days)))
        url = f"{FIRMS_BASE}/{map_key}/{source}/{area}/{safe_days}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            if response.status_code == 400:
                # Don't raise; let normalize() tag it as error.
                return response.text
            response.raise_for_status()
            return response.text

    def normalize(self, raw: str) -> ConnectorResult:
        """Transform raw FIRMS CSV into EventPoint-shaped dicts.

        - Empty/header-only CSV → `status="ok", values=[]` (landmine #3).
        - Body matches a FIRMS error marker → `status="error", values=[]`
          with a short note (landmine #2).
        - Otherwise, a list of dicts each matching
          `pipelines.contracts.EventPoint`.
        """
        err = detect_error_body(raw)
        if err is not None:
            return ConnectorResult(
                values=[],
                source=self.source,
                source_url=self.source_url,
                cadence=self.cadence,
                tag=self.tag,
                spatial_scope="global",
                license="public domain",
                status="error",
                notes=[err],
            )

        reader = csv.DictReader(io.StringIO(raw))
        events: list[dict] = []
        for row in reader:
            # `.strip()` every string cell — landmine #10.
            cleaned = {k: (v.strip() if isinstance(v, str) else v) for k, v in row.items()}
            try:
                lat_raw = float(cleaned["latitude"])
                lon_raw = float(cleaned["longitude"])
            except (KeyError, TypeError, ValueError):
                # Malformed row — skip silently. FIRMS never produces these
                # in practice, but a broken upstream shouldn't poison the
                # whole batch.
                continue
            lat = _clamp_lat(lat_raw)
            lon = _clamp_lon(lon_raw)
            frp = _safe_float(cleaned.get("frp"), 0.0)
            confidence_raw = cleaned.get("confidence") or ""
            confidence_word = _confidence_word(confidence_raw)
            acq_date = cleaned.get("acq_date") or ""
            acq_time = cleaned.get("acq_time") or ""

            label = f"FRP {frp:.1f} MW \u00b7 {confidence_word}"

            event: dict[str, object] = {
                "id": _stable_id(lat, lon, acq_date, acq_time),
                "type": "wildfire",
                "lat": lat,
                "lon": lon,
                "observedAt": _to_iso_utc(acq_date, acq_time),
                "severity": frp,
                "label": label,
                "properties": {
                    "brightness": _safe_float(
                        cleaned.get("bright_ti4") or cleaned.get("brightness"),
                        0.0,
                    ),
                    "daynight": cleaned.get("daynight") or "",
                    "confidence_raw": confidence_raw,
                    "scan": _safe_float(cleaned.get("scan"), 0.0),
                    "track": _safe_float(cleaned.get("track"), 0.0),
                },
            }
            events.append(event)

        return ConnectorResult(
            values=events,
            source=self.source,
            source_url=self.source_url,
            cadence=self.cadence,
            tag=self.tag,
            spatial_scope="global",
            license="public domain",
            status="ok",
            notes=[],
        )


__all__ = ["FirmsConnector", "detect_error_body"]
