"""USGS Earthquake summary-feed connector (v2).

Source:  https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson
Docs:    https://earthquake.usgs.gov/earthquakes/feed/v1.0/
Cadence: ~1-5 min regeneration (treated as 5 min for Worker cache)
Tag:     observed
Auth:    none
Geo:     global

=============================================================================
Response format: GeoJSON FeatureCollection. Each feature is one earthquake
event. The summary feed is the preferred endpoint for v2 over the FDSNWS
query endpoint because it is CDN-cached, already sliced to a time-window,
and cheap to refresh aggressively.

Every feature has:
  - properties.mag (float | null — null for analyst-pending events)
  - properties.place (string)
  - properties.time (int, **ms since epoch**, NOT seconds — landmine)
  - properties.updated (int, ms since epoch)
  - properties.url (event detail page)
  - properties.tsunami (0 | 1)
  - properties.felt (int | null — number of "did you feel it?" reports)
  - properties.sig (int — USGS significance score)
  - properties.status ("automatic" | "reviewed")
  - properties.type (typically "earthquake" but can be other seismic events)
  - geometry.coordinates [lon, lat, depth_km] — **this order is canonical
    for every GeoJSON source, but is flipped from the more common lat/lon
    convention; see landmine #2 below.**

Severity class mapping (stored as `properties.severity_class` on the
normalized EventPoint):

  mag >= 6.0   -> "major"
  4.5 <= mag   -> "moderate"
  2.5 <= mag   -> "light"
  mag <  2.5   -> "micro"

(We drop features with `mag: null` before classification — see landmine #3.)

=============================================================================
Known landmines (carried over from v1 `docs/connectors.md` Phase D.2 plus
new observations from the v2 fixture work):

  1. `properties.time` is milliseconds since epoch, NOT seconds. A naive
     `datetime.fromtimestamp(t)` gives a date in the year ~58,300. Always
     divide by 1000 before constructing the datetime.
  2. `geometry.coordinates` is `[longitude, latitude, depth_km]` — GeoJSON
     standard. Swapping these produces valid-looking but transposed output
     (e.g. a feature "off the coast of Samoa" ends up in Kazakhstan).
  3. Some features carry `"mag": null` when the event is analyst-pending
     (origin solved but no magnitude yet). These MUST be filtered out
     before classification / display, otherwise the label reads "MNone"
     and the severity_class assignment throws. v1 silently coerced to 0.0
     and leaked micro-labeled events with no real magnitude into the UI.
  4. `properties.type` is usually "earthquake" but the summary feed
     also includes quarry blasts, mining explosions, rockbursts, and
     sonic booms. v2 normalizer keeps them all under `type="earthquake"`
     per the frozen EventPoint contract, but records the original
     USGS `type` in `properties.event_type` for downstream filtering.
  5. Feature ids are network-prefixed (e.g. `hv74937737` for Hawaiian
     Volcano Observatory). They are stable across reruns — use them
     as the EventPoint id verbatim.
=============================================================================
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from pipelines.connectors.base import BaseConnector, ConnectorResult

USGS_SUMMARY_FEED = (
    "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"
)


def _classify_severity(mag: float) -> str:
    """Map magnitude to severity class (see module docstring)."""
    if mag >= 6.0:
        return "major"
    if mag >= 4.5:
        return "moderate"
    if mag >= 2.5:
        return "light"
    return "micro"


def _truncate(text: str, limit: int = 80) -> str:
    if len(text) <= limit:
        return text
    # Leave room for the ellipsis character.
    return text[: max(0, limit - 1)].rstrip() + "\u2026"


class UsgsConnector(BaseConnector):
    """USGS Earthquakes summary-feed connector."""

    name = "usgs"
    source = "USGS Earthquake"
    source_url = USGS_SUMMARY_FEED
    cadence = "5 min"
    tag = "observed"

    async def fetch(self, **params: Any) -> dict[str, Any]:
        """Fetch the all-day summary feed. Returns the raw GeoJSON dict."""
        timeout = httpx.Timeout(30.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(USGS_SUMMARY_FEED)
            response.raise_for_status()
            return response.json()

    def normalize(self, raw: dict[str, Any]) -> ConnectorResult:
        """Normalize a USGS GeoJSON response into EventPoint-shaped dicts.

        Features with `mag: null` (analyst-pending origins) are filtered
        out. Empty feeds return status='ok' with an empty `values` list —
        an empty result is not an error.
        """
        features = raw.get("features") or []
        values: list[dict[str, Any]] = []
        filtered_null_mag = 0

        for feat in features:
            props = feat.get("properties") or {}
            geom = feat.get("geometry") or {}
            coords = geom.get("coordinates") or []

            mag_raw = props.get("mag")
            if mag_raw is None:
                # Landmine #3: analyst-pending events. Skip.
                filtered_null_mag += 1
                continue
            try:
                mag = float(mag_raw)
            except (TypeError, ValueError):
                filtered_null_mag += 1
                continue

            try:
                # Landmine #2: coordinates are [lon, lat, depth_km].
                lon = float(coords[0])
                lat = float(coords[1])
                depth_km = float(coords[2]) if len(coords) > 2 else 0.0
            except (TypeError, ValueError, IndexError):
                continue

            time_ms = props.get("time")
            if time_ms is None:
                continue
            try:
                # Landmine #1: `time` is ms since epoch, not seconds.
                observed_at = (
                    datetime.fromtimestamp(int(time_ms) / 1000, tz=timezone.utc)
                    .isoformat()
                    .replace("+00:00", "Z")
                )
            except (TypeError, ValueError, OSError):
                continue

            feature_id = feat.get("id")
            if not feature_id:
                continue
            feature_id = str(feature_id)

            place = str(props.get("place") or "").strip()
            label = _truncate(
                f"M{mag:.1f} \u2014 {place}" if place else f"M{mag:.1f}"
            )

            severity_class = _classify_severity(mag)

            # Landmine #4: preserve the USGS `type` separately — the
            # EventPoint contract collapses all seismic events under
            # `"earthquake"`, but operators often want to distinguish.
            event_type = str(props.get("type") or "earthquake")

            point = {
                "id": feature_id,
                "type": "earthquake",
                "lat": lat,
                "lon": lon,
                "observedAt": observed_at,
                "severity": mag,
                "label": label,
                "properties": {
                    "depth_km": depth_km,
                    "url": str(props.get("url") or ""),
                    "tsunami": int(props.get("tsunami") or 0),
                    "felt": props.get("felt"),
                    "sig": props.get("sig"),
                    "status": str(props.get("status") or ""),
                    "severity_class": severity_class,
                    "event_type": event_type,
                },
            }
            values.append(point)

        notes: list[str] = []
        if filtered_null_mag:
            notes.append(
                f"Filtered {filtered_null_mag} analyst-pending feature(s) "
                "with mag=null before classification."
            )

        return ConnectorResult(
            values=values,
            source=self.source,
            source_url=self.source_url,
            cadence=self.cadence,
            tag=self.tag,
            spatial_scope="global",
            license="public domain",
            status="ok",
            notes=notes,
        )
