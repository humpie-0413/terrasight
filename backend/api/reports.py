"""Local Environmental Reports API — 6-block metro reports.

Orchestrates ECHO + AirNow + AirData + NOAA Normals + USGS + WQP calls in
parallel for a single CBSA, resolved via `data/cbsa_mapping.json`.

Each block degrades gracefully: a connector failure never 5xxs the whole
report — it is captured as a block-level error so the frontend can render
the healthy blocks plus a small error notice for the failing one.

Block map (CLAUDE.md → "3층: Local Environmental Reports"):
  0. Metro Header                 → CBSA mapping + rollup key signals
  1. Air Quality                  → AirNow (current) + AirData (annual, stub)
  2. Climate Change Locally       → Climate Normals + city time series (stub)
  3. Regulated Facilities         → EPA ECHO
  4. Water Snapshot               → USGS (NRT) + WQP (discrete)
  5. Methodology                  → block-level source/cadence table
  6. Related Content              → links (stub)
  7. Toxic Releases               → EPA TRI
  8. Site Cleanup                 → Superfund + Brownfields
  9. Facility GHG                 → EPA GHGRP
 10. Drinking Water               → EPA SDWIS
 11. PFAS Monitoring              → EPA PFAS Analytic Tools
 13. Active Weather Alerts        → NOAA NWS
 14. Hazards & Disasters          → OpenFEMA + USGS Earthquake
 15. Coastal Conditions            → NOAA CO-OPS (coastal CBSAs only)

Mandatory disclaimers from CLAUDE.md are attached to the relevant blocks.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from backend.config import get_settings
from backend.connectors.base import ConnectorResult
from backend.connectors.airnow import AirNowConnector, worst_reading
from backend.connectors.brownfields import BrownfieldsConnector
from backend.connectors.climate_normals import ClimateNormalsConnector
from backend.connectors.echo import EchoConnector
from backend.connectors.ghgrp import GhgrpConnector
from backend.connectors.nws_alerts import NwsAlertsConnector
from backend.connectors.pfas import PfasConnector
from backend.connectors.sdwis import SdwisConnector
from backend.connectors.superfund import SuperfundConnector
from backend.connectors.tri import TriConnector
from backend.connectors.usgs import UsgsConnector
from backend.connectors.wqp import WqpConnector
from backend.connectors.openfema import OpenfemaConnector
from backend.connectors.earthquake import EarthquakeConnector
from backend.connectors.coops import CoopsConnector
from backend.connectors.rcra import RcraConnector

router = APIRouter()

# CBSA mapping lives at repo-root /data; backend/api/reports.py is two
# levels deep. Resolve relative to the file path so this works regardless
# of the current working directory.
CBSA_MAPPING_PATH = Path(__file__).resolve().parents[2] / "data" / "cbsa_mapping.json"


def _load_cbsa_mapping() -> dict[str, dict[str, Any]]:
    """Load and index the CBSA mapping file by slug."""
    if not CBSA_MAPPING_PATH.exists():
        return {}
    raw = json.loads(CBSA_MAPPING_PATH.read_text(encoding="utf-8"))
    # File is keyed by CBSA code; re-index by slug for slug-based lookup.
    by_slug: dict[str, dict[str, Any]] = {}
    for key, entry in raw.items():
        if key.startswith("_"):
            continue
        slug = entry.get("slug")
        if slug:
            by_slug[slug] = entry
    return by_slug


def _dc_to_dict(value: Any) -> Any:
    """Recursively convert dataclasses (and lists thereof) to plain dicts."""
    if is_dataclass(value):
        return {k: _dc_to_dict(v) for k, v in asdict(value).items()}
    if isinstance(value, list):
        return [_dc_to_dict(v) for v in value]
    if isinstance(value, tuple):
        return [_dc_to_dict(v) for v in value]
    if isinstance(value, dict):
        return {k: _dc_to_dict(v) for k, v in value.items()}
    return value


def _block_from_result(result: Any) -> dict[str, Any]:
    """Wrap a ConnectorResult (or Exception) into a JSON-friendly block."""
    if isinstance(result, Exception):
        return {
            "status": "error",
            "error": f"{type(result).__name__}: {result}",
            "values": None,
        }
    return {
        "status": "ok",
        "values": _dc_to_dict(result.values),
        "source": result.source,
        "source_url": result.source_url,
        "cadence": result.cadence,
        "tag": result.tag,
        "spatial_scope": result.spatial_scope,
        "license": result.license,
        "notes": list(result.notes),
    }


def _build_toxic_releases_block(
    result: Any, rcra_result: Any = None, core_city: str | None = None
) -> dict[str, Any]:
    """Shape a TRI ConnectorResult into the `toxic_releases` block.

    Sort preference: facilities matching the CBSA's core city come
    first, then the rest preserved in connector order. Capped at 5.

    Optionally includes an `rcra_summary` sub-section when RCRA data
    is available.
    """
    if isinstance(result, Exception):
        return {
            "status": "error",
            "error": f"{type(result).__name__}: {result}",
            "values": None,
        }
    facilities = list(result.values)  # list[TriFacility]

    def _is_core(f: Any) -> bool:
        if not core_city or not getattr(f, "city", None):
            return False
        return core_city.lower() in f.city.lower()

    # Stable sort: city match first, preserve original order otherwise.
    sorted_facs = sorted(
        facilities, key=lambda f: (0 if _is_core(f) else 1)
    )
    top = [
        {
            "name": f.name,
            "city": f.city,
            "state": f.state,
            "chemicals": list(f.chemicals)[:5] if f.chemicals else [],
            "year": f.year,
        }
        for f in sorted_facs[:5]
    ]
    all_chems: set[str] = set()
    for f in facilities:
        for c in (f.chemicals or []):
            all_chems.add(c)

    # RCRA sub-section
    rcra_data = None
    if rcra_result and not isinstance(rcra_result, Exception) and hasattr(rcra_result, 'values'):
        handlers = rcra_result.values or []
        rcra_data = {
            "handler_count": len(handlers),
            "top_handlers": [
                {
                    "name": h.handler_name,
                    "city": h.city,
                    "state": h.state,
                    "waste_tons": h.waste_generated_tons,
                    "year": h.reporting_year,
                }
                for h in handlers[:5]
            ],
        }

    block = {
        "status": "ok",
        "values": {
            "facility_count": len(facilities),
            "top_facilities": top,
            "chemicals_sampled": len(all_chems),
            "rcra_summary": rcra_data,
        },
        "source": result.source,
        "source_url": result.source_url,
        "cadence": result.cadence,
        "tag": result.tag,
        "spatial_scope": result.spatial_scope,
        "license": result.license,
        "notes": list(result.notes),
    }
    return block


def _build_site_cleanup_block(
    superfund_result: Any, brownfields_result: Any
) -> dict[str, Any]:
    """Combine Superfund + Brownfields ConnectorResults into one block.

    status = "ok" if at least one succeeded. If both failed, "error".
    Notes list prepends a header line for each section so the frontend
    can disambiguate which notes came from where.
    """
    superfund_ok = not isinstance(superfund_result, Exception)
    brownfields_ok = not isinstance(brownfields_result, Exception)

    if not superfund_ok and not brownfields_ok:
        return {
            "status": "error",
            "error": (
                f"Superfund: {type(superfund_result).__name__}: {superfund_result}; "
                f"Brownfields: {type(brownfields_result).__name__}: {brownfields_result}"
            ),
            "values": None,
        }

    # Superfund section
    if superfund_ok:
        sf_values = list(superfund_result.values)
        sf_sites = [
            {
                "name": s.name,
                "lat": s.lat,
                "lon": s.lon,
                "city": s.city,
                "state": s.state,
                "npl_status": s.npl_status,
                "address": s.address,
            }
            for s in sf_values[:5]
        ]
        superfund_section = {"count": len(sf_values), "sites": sf_sites}
    else:
        superfund_section = {"count": 0, "sites": []}

    # Brownfields section
    if brownfields_ok:
        bf_values = list(brownfields_result.values)
        bf_sites = [
            {
                "name": s.name,
                "lat": s.lat,
                "lon": s.lon,
                "city": s.city,
                "state": s.state,
                "cleanup_status": s.cleanup_status,
            }
            for s in bf_values[:5]
        ]
        brownfields_section = {"count": len(bf_values), "sites": bf_sites}
    else:
        brownfields_section = {"count": 0, "sites": []}

    # Metadata: comma-joined source, stricter cadence ("monthly" is the
    # only cadence on both connectors, so trivially "monthly"), tag
    # pinned to "observed", notes concatenated with origin headers.
    sources: list[str] = []
    source_urls: list[str] = []
    licenses: list[str] = []
    scopes: list[str] = []
    notes: list[str] = []

    if superfund_ok:
        sources.append(superfund_result.source)
        source_urls.append(superfund_result.source_url)
        licenses.append(superfund_result.license)
        scopes.append(superfund_result.spatial_scope)
        notes.append("— Superfund —")
        notes.extend(list(superfund_result.notes))
    else:
        notes.append(
            f"Superfund unavailable: {type(superfund_result).__name__}: "
            f"{superfund_result}"
        )

    if brownfields_ok:
        sources.append(brownfields_result.source)
        source_urls.append(brownfields_result.source_url)
        licenses.append(brownfields_result.license)
        scopes.append(brownfields_result.spatial_scope)
        notes.append("— Brownfields —")
        notes.extend(list(brownfields_result.notes))
    else:
        notes.append(
            f"Brownfields unavailable: {type(brownfields_result).__name__}: "
            f"{brownfields_result}"
        )

    return {
        "status": "ok",
        "values": {
            "superfund": superfund_section,
            "brownfields": brownfields_section,
        },
        "source": ", ".join(sources) if sources else None,
        "source_url": ", ".join(source_urls) if source_urls else None,
        "cadence": "monthly",
        "tag": "observed",
        "spatial_scope": "; ".join(scopes) if scopes else None,
        "license": ", ".join(licenses) if licenses else None,
        "notes": notes,
    }


def _build_facility_ghg_block(result: Any) -> dict[str, Any]:
    """Shape a GHGRP ConnectorResult into the `facility_ghg` block."""
    if isinstance(result, Exception):
        return {
            "status": "error",
            "error": f"{type(result).__name__}: {result}",
            "values": None,
        }
    facilities = list(result.values)  # list[GhgrpFacility]

    # Sum totals, pick most-recent year, sort DESC (None → 0).
    totals_known = [
        f.total_co2e_tonnes
        for f in facilities
        if f.total_co2e_tonnes is not None
    ]
    total_co2e = round(sum(totals_known), 2) if totals_known else None
    years = [f.year for f in facilities if f.year is not None]
    latest_year = max(years) if years else None

    sorted_facs = sorted(
        facilities,
        key=lambda f: (f.total_co2e_tonnes or 0.0),
        reverse=True,
    )
    top = [
        {
            "name": f.name,
            "city": f.city,
            "state": f.state,
            "total_co2e_tonnes": f.total_co2e_tonnes,
            "year": f.year,
        }
        for f in sorted_facs[:5]
    ]

    return {
        "status": "ok",
        "values": {
            "facility_count": len(facilities),
            "total_co2e_tonnes": total_co2e,
            "year": latest_year,
            "top_facilities": top,
        },
        "source": result.source,
        "source_url": result.source_url,
        "cadence": result.cadence,
        "tag": result.tag,
        "spatial_scope": result.spatial_scope,
        "license": result.license,
        "notes": list(result.notes),
    }


def _build_drinking_water_block(result: Any) -> dict[str, Any]:
    """Shape an SDWIS ConnectorResult into the `drinking_water` block."""
    if isinstance(result, Exception):
        return {
            "status": "error",
            "error": f"{type(result).__name__}: {result}",
            "values": None,
        }
    systems = list(result.values)  # list[DrinkingWaterSystem]

    system_count = len(systems)
    violation_count = sum(s.violation_count or 0 for s in systems)
    systems_with_viol = [s for s in systems if (s.violation_count or 0) > 0]
    systems_with_violations = len(systems_with_viol)
    violation_rate_pct = (
        round(systems_with_violations / system_count * 100, 2)
        if system_count > 0
        else None
    )
    total_population_affected = sum(
        (s.population_served or 0) for s in systems_with_viol
    )

    # Recent violations: sort systems by latest_violation_date DESC
    # (None → "" so they sort last), take top 5.
    sorted_systems = sorted(
        systems_with_viol,
        key=lambda s: (s.latest_violation_date or ""),
        reverse=True,
    )
    recent = [
        {
            "pwsid": s.pwsid,
            "name": s.name,
            "city": s.city,
            "population_served": s.population_served,
            "primary_source": s.primary_source,
            "latest_violation_date": s.latest_violation_date,
            "violation_count": s.violation_count,
        }
        for s in sorted_systems[:5]
    ]

    return {
        "status": "ok",
        "values": {
            "system_count": system_count,
            "violation_count": violation_count,
            "systems_with_violations": systems_with_violations,
            "violation_rate_pct": violation_rate_pct,
            "recent_violations": recent,
            "total_population_affected": total_population_affected,
        },
        "source": result.source,
        "source_url": result.source_url,
        "cadence": result.cadence,
        "tag": result.tag,
        "spatial_scope": result.spatial_scope,
        "license": result.license,
        "notes": list(result.notes),
    }


async def _run_airnow(zip_code: str) -> dict[str, Any]:
    """Block 1 current AQI. Graceful 'not configured' when no key."""
    settings = get_settings()
    connector = AirNowConnector(api_key=settings.airnow_api_key)
    if not settings.airnow_api_key:
        return {
            "status": "not_configured",
            "error": None,
            "values": None,
            "source": connector.source,
            "source_url": connector.source_url,
            "cadence": connector.cadence,
            "tag": connector.tag,
            "message": (
                "AIRNOW_API_KEY is not configured. Register at "
                "https://docs.airnowapi.org/ and set AIRNOW_API_KEY in .env."
            ),
        }
    try:
        raw = await connector.fetch(zip_code=zip_code)
        result = connector.normalize(raw)
    except Exception as exc:  # noqa: BLE001 — block-level graceful fail
        return {
            "status": "error",
            "error": f"{type(exc).__name__}: {exc}",
            "values": None,
        }
    readings = result.values
    worst = worst_reading(readings)
    return {
        "status": "ok",
        "source": result.source,
        "source_url": result.source_url,
        "cadence": result.cadence,
        "tag": result.tag,
        "spatial_scope": result.spatial_scope,
        "license": result.license,
        "notes": list(result.notes),
        "values": {
            "readings": [_dc_to_dict(r) for r in readings],
            "headline": _dc_to_dict(worst) if worst else None,
        },
    }


async def _run_echo(bbox: dict[str, float]) -> Any:
    connector = EchoConnector()
    raw = await connector.fetch(
        west=bbox["west"],
        south=bbox["south"],
        east=bbox["east"],
        north=bbox["north"],
        response_set=100,
    )
    return connector.normalize(raw)


async def _run_usgs(bbox: dict[str, float]) -> Any:
    connector = UsgsConnector()
    raw = await connector.fetch(
        west=bbox["west"],
        south=bbox["south"],
        east=bbox["east"],
        north=bbox["north"],
    )
    return connector.normalize(raw)


async def _run_wqp(bbox: dict[str, float]) -> Any:
    connector = WqpConnector()
    raw = await connector.fetch(
        west=bbox["west"],
        south=bbox["south"],
        east=bbox["east"],
        north=bbox["north"],
    )
    return connector.normalize(raw)


async def _run_normals(station_id: str) -> Any:
    connector = ClimateNormalsConnector()
    raw = await connector.fetch(station_id=station_id)
    return connector.normalize(raw)


async def _run_tri(state: str, limit: int = 100, year: int | None = None) -> Any:
    """Block 3.5 — TRI toxic release facilities for a state."""
    connector = TriConnector()
    raw = await connector.fetch(state=state, limit=limit, year=year)
    return connector.normalize(raw)


async def _run_ghgrp(state: str, limit: int = 100, year: int = 2023) -> Any:
    """Block 3.7 — GHGRP/FLIGHT facility CO2e totals for a state."""
    connector = GhgrpConnector()
    raw = await connector.fetch(state=state, limit=limit, year=year)
    return connector.normalize(raw)


async def _run_superfund(bbox: dict[str, float], limit: int = 100) -> Any:
    """Block 3.6 — Superfund NPL site boundaries for a bbox."""
    connector = SuperfundConnector()
    raw = await connector.fetch(
        west=bbox["west"],
        south=bbox["south"],
        east=bbox["east"],
        north=bbox["north"],
        limit=limit,
    )
    return connector.normalize(raw)


async def _run_brownfields(bbox: dict[str, float], limit: int = 100) -> Any:
    """Block 3.6 — ACRES brownfields point layer for a bbox."""
    connector = BrownfieldsConnector()
    raw = await connector.fetch(
        west=bbox["west"],
        south=bbox["south"],
        east=bbox["east"],
        north=bbox["north"],
        limit=limit,
    )
    return connector.normalize(raw)


async def _run_sdwis(
    state: str, zip_prefixes: list[str], limit: int = 200
) -> Any:
    """Block 3.8 — SDWIS public water systems + violations.

    NOTE: the SdwisConnector.fetch() signature uses `zip_prefix_list`
    (per-prefix parallel fan-out). An empty list falls back to the
    state-only slow path, which is NOT what we want here — callers
    that pass an empty list should get an error block instead (handled
    upstream in get_report).
    """
    connector = SdwisConnector()
    raw = await connector.fetch(
        state=state,
        zip_prefix_list=zip_prefixes,
        limit=limit,
    )
    return connector.normalize(raw)


async def _run_nws_alerts(state: str | None = None, core_city: str | None = None) -> Any:
    """Fetch NWS active alerts, filtered to state/city relevance.

    NWS alerts are national — we fetch all and filter by area_desc
    mentioning the state or core city name. Requires no auth.
    """
    connector = NwsAlertsConnector()
    raw = await connector.fetch()
    result = connector.normalize(raw)
    # Filter alerts to those whose area_desc is relevant to this metro.
    if state or core_city:
        filtered: list[Any] = []
        for alert in result.values:
            area = (alert.area_desc or "").lower()
            if state and state.lower() in area:
                filtered.append(alert)
            elif core_city and core_city.lower() in area:
                filtered.append(alert)
        result = ConnectorResult(
            values=filtered,
            source=result.source,
            source_url=result.source_url,
            cadence=result.cadence,
            tag=result.tag,
            spatial_scope=result.spatial_scope,
            license=result.license,
            notes=result.notes,
        )
    return result


async def _run_pfas(bbox: dict[str, float], limit: int = 100) -> Any:
    """Fetch PFAS monitoring sites in bbox."""
    connector = PfasConnector()
    raw = await connector.fetch(
        west=bbox["west"],
        south=bbox["south"],
        east=bbox["east"],
        north=bbox["north"],
        limit=limit,
    )
    return connector.normalize(raw)


async def _run_openfema(state: str, years: int = 5, limit: int = 50):
    connector = OpenfemaConnector()
    raw = await connector.fetch(state=state, years=years, limit=limit)
    return connector.normalize(raw)


async def _run_earthquake(west, south, east, north, days=30, min_magnitude=2.5, limit=50):
    connector = EarthquakeConnector()
    raw = await connector.fetch(min_magnitude=min_magnitude, limit=limit, days=days)
    result = connector.normalize(raw)
    # Filter to bbox
    filtered = [e for e in result.values
                if south <= e.lat <= north and west <= e.lon <= east]
    return ConnectorResult(
        values=filtered, source=result.source, source_url=result.source_url,
        cadence=result.cadence, tag=result.tag, spatial_scope=result.spatial_scope,
        license=result.license, notes=result.notes)


async def _run_coops(west, south, east, north, limit=10):
    connector = CoopsConnector()
    raw = await connector.fetch(west=west, south=south, east=east, north=north, limit=limit)
    return connector.normalize(raw)


async def _run_rcra(state: str, limit: int = 50, year: int | None = None):
    connector = RcraConnector()
    raw = await connector.fetch(state=state, limit=limit, year=year)
    return connector.normalize(raw)


def _build_active_alerts_block(result: Any) -> dict[str, Any]:
    """Build Active Alerts block from NWS connector result."""
    if isinstance(result, Exception):
        return {
            "status": "error",
            "error": f"{type(result).__name__}: {result}",
            "values": None,
        }
    alerts = result.values if hasattr(result, "values") else []
    return {
        "status": "ok",
        "source": result.source,
        "source_url": result.source_url,
        "cadence": result.cadence,
        "tag": result.tag,
        "spatial_scope": result.spatial_scope,
        "license": result.license,
        "values": {
            "alert_count": len(alerts),
            "alerts": [
                {
                    "event": a.event,
                    "severity": a.severity,
                    "certainty": a.certainty,
                    "urgency": a.urgency,
                    "headline": a.headline,
                    "area_desc": a.area_desc,
                    "onset": a.onset,
                    "expires": a.expires,
                    "sender": a.sender,
                }
                for a in alerts[:20]  # cap at 20 alerts
            ],
        },
        "notes": list(result.notes),
    }


def _build_pfas_block(result: Any) -> dict[str, Any]:
    """Build PFAS Monitoring block from PFAS connector result."""
    if isinstance(result, Exception):
        return {
            "status": "error",
            "error": f"{type(result).__name__}: {result}",
            "values": None,
        }
    sites = result.values if hasattr(result, "values") else []
    # Aggregate stats
    unique_systems = len(set(s.site_id for s in sites if s.site_id))
    contaminants = [s.contaminant for s in sites if s.contaminant]
    unique_contaminants = list(set(contaminants))
    from collections import Counter

    most_frequent = Counter(contaminants).most_common(1)
    most_frequent_name = most_frequent[0][0] if most_frequent else None
    return {
        "status": "ok",
        "source": result.source,
        "source_url": result.source_url,
        "cadence": result.cadence,
        "tag": result.tag,
        "spatial_scope": result.spatial_scope,
        "license": result.license,
        "values": {
            "monitored_systems": unique_systems,
            "unique_contaminants": len(unique_contaminants),
            "most_frequent_contaminant": most_frequent_name,
            "total_samples": len(sites),
            "top_detections": [
                {
                    "system_name": s.name,
                    "system_id": s.site_id,
                    "contaminant": s.contaminant,
                    "city": s.city,
                    "state": s.state,
                }
                for s in sites[:10]
            ],
        },
        "notes": list(result.notes) + [
            "PFAS results are screening-level monitoring data. "
            "Detection does not imply a health risk at reported levels."
        ],
    }


def _build_hazards_block(openfema_res, earthquake_res) -> dict:
    """Build Hazards & Disasters block combining OpenFEMA + Earthquake."""
    disasters = []
    disaster_error = None
    if isinstance(openfema_res, Exception):
        disaster_error = str(openfema_res)
    elif hasattr(openfema_res, 'values'):
        disasters = openfema_res.values or []

    quakes = []
    quake_error = None
    if isinstance(earthquake_res, Exception):
        quake_error = str(earthquake_res)
    elif hasattr(earthquake_res, 'values'):
        quakes = earthquake_res.values or []

    if disaster_error and quake_error:
        return {"status": "error", "error": f"FEMA: {disaster_error}; USGS: {quake_error}", "values": None}

    # Stats
    from collections import Counter
    incident_types = [d.incident_type for d in disasters if d.incident_type]
    type_counts = Counter(incident_types)
    most_common = type_counts.most_common(1)
    most_common_type = most_common[0][0] if most_common else None

    largest_quake = max(quakes, key=lambda q: q.magnitude) if quakes else None

    return {
        "status": "ok",
        "source": "FEMA / USGS",
        "source_url": "https://www.fema.gov/disaster/declarations",
        "cadence": "Continuous / NRT",
        "tag": "observed",
        "values": {
            "total_disasters": len(disasters),
            "most_common_type": most_common_type,
            "largest_quake_magnitude": largest_quake.magnitude if largest_quake else None,
            "largest_quake_place": largest_quake.place if largest_quake else None,
            "recent_disasters": [
                {
                    "disaster_number": d.disaster_number,
                    "declaration_type": d.declaration_type,
                    "declaration_date": d.declaration_date,
                    "incident_type": d.incident_type,
                    "title": d.title,
                    "designated_area": d.designated_area,
                }
                for d in disasters[:10]
            ],
            "recent_earthquakes": [
                {
                    "magnitude": q.magnitude,
                    "place": q.place,
                    "depth_km": q.depth_km,
                    "time_utc": q.time_utc,
                }
                for q in quakes[:5]
            ],
        },
        "notes": [
            "Disaster declarations from OpenFEMA (last 5 years).",
            "Earthquakes from USGS FDSNWS (last 30 days, filtered to CBSA bbox).",
        ],
    }


def _build_coastal_block(coops_res) -> dict:
    """Build Coastal Conditions block from CO-OPS connector result."""
    if isinstance(coops_res, Exception):
        return {"status": "error", "error": str(coops_res), "values": None}
    stations = coops_res.values if hasattr(coops_res, 'values') else []
    return {
        "status": "ok",
        "source": coops_res.source if hasattr(coops_res, 'source') else "NOAA CO-OPS",
        "source_url": coops_res.source_url if hasattr(coops_res, 'source_url') else "https://tidesandcurrents.noaa.gov/",
        "cadence": coops_res.cadence if hasattr(coops_res, 'cadence') else "6-minute",
        "tag": "observed",
        "values": {
            "station_count": len(stations),
            "stations": [
                {
                    "station_id": s.station_id,
                    "name": s.name,
                    "lat": s.lat,
                    "lon": s.lon,
                    "water_level_ft": s.water_level_ft,
                    "water_temp_f": s.water_temp_f,
                    "timestamp": s.timestamp,
                }
                for s in stations[:10]
            ],
        },
        "notes": coops_res.notes if hasattr(coops_res, 'notes') else [],
    }


def _key_signals(
    air: dict[str, Any],
    echo: dict[str, Any],
    usgs: dict[str, Any],
    facility_ghg: dict[str, Any] | None = None,
    site_cleanup: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Block 0 rollup: mini-cards on the metro header.

    `usgs` is the flat hydrology block (not the combined water block).
    `facility_ghg` and `site_cleanup` are the new Phase E.1 blocks used
    to enrich the header — passed as None-safe optionals so existing
    callers do not break.
    """
    # AQI headline (if AirNow succeeded).
    aqi_card: dict[str, Any]
    if (
        air.get("status") == "ok"
        and air.get("values", {}).get("headline")
    ):
        headline = air["values"]["headline"]
        aqi_card = {
            "label": "Current AQI",
            "value": f"{headline['aqi']} · {headline['category']}",
            "tag": "observed",
            "source": "AirNow",
        }
    elif air.get("status") == "not_configured":
        aqi_card = {
            "label": "Current AQI",
            "value": "API key required",
            "tag": "observed",
            "source": "AirNow",
        }
    else:
        aqi_card = {
            "label": "Current AQI",
            "value": "—",
            "tag": "observed",
            "source": "AirNow",
        }

    # EPA facilities count.
    fac_card: dict[str, Any]
    if echo.get("status") == "ok" and echo.get("values"):
        vals = echo["values"]
        sampled = vals.get("sampled_facilities", 0)
        in_vio = vals.get("in_violation", 0)
        fac_card = {
            "label": "EPA facilities",
            "value": (
                f"{sampled} sampled · {in_vio} in violation"
            ),
            "tag": "observed",
            "source": "EPA ECHO",
        }
    else:
        fac_card = {
            "label": "EPA facilities",
            "value": "—",
            "tag": "observed",
            "source": "EPA ECHO",
        }

    # Water status (sites reporting streamflow).
    water_card: dict[str, Any]
    if usgs.get("status") == "ok" and usgs.get("values"):
        vals = usgs["values"]
        water_card = {
            "label": "Streamflow sites",
            "value": f"{vals['site_count']} NRT",
            "tag": "near-real-time",
            "source": "USGS",
        }
    else:
        water_card = {
            "label": "Streamflow sites",
            "value": "—",
            "tag": "near-real-time",
            "source": "USGS",
        }

    # Temperature trend placeholder (city time series connector is still
    # P1 — see CLAUDE.md Block 2). Card is rendered but value is a
    # placeholder so the layout stays stable.
    temp_card = {
        "label": "Temp anomaly",
        "value": "See Block 2",
        "tag": "near-real-time",
        "source": "NOAA",
    }

    # GHG facility total (new in Phase E.1).
    ghg_card: dict[str, Any]
    if (
        facility_ghg
        and facility_ghg.get("status") == "ok"
        and facility_ghg.get("values")
    ):
        ghg_vals = facility_ghg["values"]
        total = ghg_vals.get("total_co2e_tonnes")
        if total is not None:
            ghg_card = {
                "label": "GHG facility total (tCO\u2082e)",
                "value": f"{int(round(total)):,}",
                "tag": "observed",
                "source": "EPA GHGRP",
            }
        else:
            ghg_card = {
                "label": "GHG facility total (tCO\u2082e)",
                "value": "—",
                "tag": "observed",
                "source": "EPA GHGRP",
            }
    else:
        ghg_card = {
            "label": "GHG facility total (tCO\u2082e)",
            "value": "—",
            "tag": "observed",
            "source": "EPA GHGRP",
        }

    # Superfund sites (new in Phase E.1).
    superfund_card: dict[str, Any]
    if (
        site_cleanup
        and site_cleanup.get("status") == "ok"
        and site_cleanup.get("values")
    ):
        sf_count = (
            site_cleanup["values"].get("superfund", {}).get("count", 0)
        )
        superfund_card = {
            "label": "Superfund sites",
            "value": str(sf_count),
            "tag": "observed",
            "source": "EPA SEMS",
        }
    else:
        superfund_card = {
            "label": "Superfund sites",
            "value": "—",
            "tag": "observed",
            "source": "EPA SEMS",
        }

    return [aqi_card, temp_card, fac_card, water_card, ghg_card, superfund_card]


@router.get("/")
async def list_reports() -> list[dict[str, Any]]:
    """Return lightweight metadata for all available metros (home page cards)."""
    mapping = _load_cbsa_mapping()
    return [
        {
            "slug": cbsa["slug"],
            "name": cbsa["name"],
            "state": cbsa.get("state"),
            "population": cbsa.get("population"),
            "population_year": cbsa.get("population_year"),
            "climate_zone": cbsa.get("climate_zone"),
            "lat": cbsa.get("lat"),
            "lon": cbsa.get("lon"),
        }
        for cbsa in mapping.values()
    ]


@router.get("/search")
async def search_report(q: str) -> dict[str, Any]:
    """Match a ZIP code or metro name to a CBSA slug.

    ZIP: checks if q starts with any prefix in the CBSA's zip_prefixes list.
    Name: case-insensitive substring match on the CBSA name.
    Returns {slug, name} on match or {slug: null, message} when nothing found.
    """
    mapping = _load_cbsa_mapping()
    term = q.strip()
    # ZIP lookup (numeric input → prefix match)
    if term.isdigit():
        for cbsa in mapping.values():
            for prefix in cbsa.get("zip_prefixes", []):
                if term.startswith(prefix):
                    return {"slug": cbsa["slug"], "name": cbsa["name"]}
    # City / metro name substring match
    term_lower = term.lower()
    for cbsa in mapping.values():
        if term_lower in cbsa["name"].lower():
            return {"slug": cbsa["slug"], "name": cbsa["name"]}
    return {
        "slug": None,
        "message": f"No metro found for '{term}'. Try a ZIP code or city name.",
    }


@router.get("/{cbsa_slug}")
async def get_report(cbsa_slug: str) -> dict[str, Any]:
    """Return a full 6-block Local Environmental Report for a metro (CBSA)."""
    mapping = _load_cbsa_mapping()
    cbsa = mapping.get(cbsa_slug)
    if not cbsa:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Unknown CBSA slug '{cbsa_slug}'. Available: "
                f"{sorted(mapping.keys())}"
            ),
        )

    bbox = cbsa["bbox"]
    sample_zip = cbsa.get("airnow", {}).get("sample_zip")
    station_id = cbsa.get("noaa", {}).get("city_station_id")
    state = cbsa.get("state")
    zip_prefixes = cbsa.get("zip_prefixes", []) or []
    # Used for TRI "core city match" sorting. Derive from CBSA name
    # first token (e.g. "Houston-The Woodlands-Sugar Land" → "Houston").
    core_city = (cbsa.get("name") or "").split("-")[0].strip() or None

    # Launch every independent connector in parallel. `return_exceptions=True`
    # converts a single connector failure into an Exception instance we can
    # wrap as an error block instead of a 5xx.
    airnow_task = _run_airnow(sample_zip) if sample_zip else asyncio.sleep(0, result=None)
    echo_task = _run_echo(bbox)
    usgs_task = _run_usgs(bbox)
    wqp_task = _run_wqp(bbox)
    normals_task = (
        _run_normals(station_id)
        if station_id
        else asyncio.sleep(0, result=None)
    )
    # Phase E.1 connectors. State-scoped (TRI, GHGRP) and bbox-scoped
    # (Superfund, Brownfields) calls run alongside the existing set.
    # SDWIS is slow (~30 s for Houston) but runs in parallel — that is
    # the price of the existing block's zip-prefix fan-out.
    tri_task: Any = (
        _run_tri(state=state)
        if state
        else asyncio.sleep(0, result=None)
    )
    ghgrp_task: Any = (
        _run_ghgrp(state=state)
        if state
        else asyncio.sleep(0, result=None)
    )
    superfund_task = _run_superfund(bbox=bbox)
    brownfields_task = _run_brownfields(bbox=bbox)
    # Empty zip_prefixes → skip SDWIS (return a sentinel) rather than
    # paying the slow state-fallback cost. See `sdwis.py` landmine #12.
    sdwis_task: Any = (
        _run_sdwis(state=state, zip_prefixes=zip_prefixes)
        if (state and zip_prefixes)
        else asyncio.sleep(0, result=None)
    )

    # NWS alerts always run (no auth needed); PFAS uses bbox.
    nws_alerts_task = _run_nws_alerts(state=state, core_city=core_city)
    pfas_task = _run_pfas(bbox=bbox)

    # Hazards & Disasters: OpenFEMA (state-scoped) + Earthquake (bbox-filtered).
    openfema_task: Any = (
        _run_openfema(state=state)
        if state
        else asyncio.sleep(0, result=None)
    )
    earthquake_task = _run_earthquake(
        west=bbox["west"], south=bbox["south"],
        east=bbox["east"], north=bbox["north"],
    )

    # Coastal Conditions: CO-OPS tide stations — only for coastal CBSAs.
    is_coastal = cbsa.get("coastal", False)
    coops_task: Any = (
        _run_coops(
            west=bbox["west"], south=bbox["south"],
            east=bbox["east"], north=bbox["north"],
        )
        if is_coastal
        else asyncio.sleep(0, result=None)
    )

    # RCRA hazardous waste handlers (state-scoped).
    rcra_task: Any = (
        _run_rcra(state=state)
        if state
        else asyncio.sleep(0, result=None)
    )

    (
        airnow_res,
        echo_res,
        usgs_res,
        wqp_res,
        normals_res,
        tri_res,
        ghgrp_res,
        superfund_res,
        brownfields_res,
        sdwis_res,
        nws_alerts_res,
        pfas_res,
        openfema_res,
        earthquake_res,
        coops_res,
        rcra_res,
    ) = await asyncio.gather(
        airnow_task,
        echo_task,
        usgs_task,
        wqp_task,
        normals_task,
        tri_task,
        ghgrp_task,
        superfund_task,
        brownfields_task,
        sdwis_task,
        nws_alerts_task,
        pfas_task,
        openfema_task,
        earthquake_task,
        coops_task,
        rcra_task,
        return_exceptions=True,
    )

    # AirNow is already block-shaped by _run_airnow (it handles its own
    # graceful degradation). Any exception escaping that gets caught here.
    if isinstance(airnow_res, Exception):
        airnow_block: dict[str, Any] = {
            "status": "error",
            "error": f"{type(airnow_res).__name__}: {airnow_res}",
            "values": None,
        }
    elif airnow_res is None:
        airnow_block = {
            "status": "error",
            "error": "No sample_zip for this CBSA",
            "values": None,
        }
    else:
        airnow_block = airnow_res

    echo_block = _block_from_result(echo_res)

    usgs_block = _block_from_result(usgs_res)
    wqp_block = _block_from_result(wqp_res)

    # Climate block: Normals connector result (baseline) + a stub city
    # time series placeholder. City CtaG time series remains a P1 spike.
    if isinstance(normals_res, Exception):
        normals_block: dict[str, Any] = {
            "status": "error",
            "error": f"{type(normals_res).__name__}: {normals_res}",
            "values": None,
        }
    elif normals_res is None:
        normals_block = {
            "status": "error",
            "error": "No NOAA city_station_id for this CBSA",
            "values": None,
        }
    else:
        normals_block = _block_from_result(normals_res)

    climate_block: dict[str, Any] = {
        "status": normals_block["status"],
        "baseline": normals_block,
        "city_time_series": {
            "status": "pending",
            "message": (
                "City-level monthly time series pending (CtaG UI has no "
                "public REST API; NOAAGlobalTemp city product integration "
                "is deferred to P1)."
            ),
            "values": None,
        },
    }

    # Block 4: combine both water sources into one block with clear labels.
    water_block: dict[str, Any] = {
        "status": (
            "ok"
            if (usgs_block["status"] == "ok" or wqp_block["status"] == "ok")
            else "error"
        ),
        "hydrology_nrt": usgs_block,
        "water_quality_discrete": wqp_block,
        "disclaimer": (
            "USGS streamflow = continuous 15-minute instantaneous values. "
            "WQP water quality = discrete samples — dates vary."
        ),
    }

    # Phase E.1 blocks. Each block-shaper accepts an Exception and
    # returns a graceful error block, so no extra try/except needed.
    if tri_res is None:
        toxic_releases_block: dict[str, Any] = {
            "status": "error",
            "error": "No state configured for this CBSA",
            "values": None,
        }
    else:
        toxic_releases_block = _build_toxic_releases_block(
            tri_res, rcra_result=rcra_res, core_city=core_city
        )

    site_cleanup_block = _build_site_cleanup_block(
        superfund_res, brownfields_res
    )

    if ghgrp_res is None:
        facility_ghg_block: dict[str, Any] = {
            "status": "error",
            "error": "No state configured for this CBSA",
            "values": None,
        }
    else:
        facility_ghg_block = _build_facility_ghg_block(ghgrp_res)

    if sdwis_res is None:
        drinking_water_block: dict[str, Any] = {
            "status": "error",
            "error": (
                "No zip prefixes configured for this CBSA"
                if state
                else "No state or zip prefixes configured for this CBSA"
            ),
            "values": None,
        }
    else:
        drinking_water_block = _build_drinking_water_block(sdwis_res)

    # NWS Active Alerts and PFAS Monitoring blocks.
    active_alerts_block = _build_active_alerts_block(nws_alerts_res)
    pfas_block = _build_pfas_block(pfas_res)

    # Hazards & Disasters block (OpenFEMA + Earthquake).
    if openfema_res is None and isinstance(earthquake_res, Exception):
        hazards_block: dict[str, Any] = {
            "status": "error",
            "error": "No state configured for this CBSA and earthquake fetch failed",
            "values": None,
        }
    elif openfema_res is None:
        # No state → no FEMA data, but earthquake may have data
        hazards_block = _build_hazards_block(
            Exception("No state configured for FEMA lookup"), earthquake_res
        )
    else:
        hazards_block = _build_hazards_block(openfema_res, earthquake_res)

    # Coastal Conditions block — only for coastal CBSAs.
    if is_coastal:
        if coops_res is None:
            coastal_block: dict[str, Any] | None = {
                "status": "error",
                "error": "CO-OPS fetch returned None",
                "values": None,
            }
        else:
            coastal_block = _build_coastal_block(coops_res)
    else:
        coastal_block = None

    meta = {
        "cbsa_code": cbsa["cbsa_code"],
        "slug": cbsa["slug"],
        "name": cbsa["name"],
        "state": cbsa.get("state"),
        "population": cbsa.get("population"),
        "population_year": cbsa.get("population_year"),
        "climate_zone": cbsa.get("climate_zone"),
        "lat": cbsa.get("lat"),
        "lon": cbsa.get("lon"),
        "core_county": cbsa.get("core_county_name"),
        "core_county_fips": cbsa.get("core_county_fips"),
    }

    # Methodology block — single source of truth for the trust table the
    # frontend renders at the bottom of the page.
    methodology: list[dict[str, Any]] = []
    for block_name, block in [
        ("Air Quality (current)", airnow_block),
        ("Climate baseline", normals_block),
        ("Facilities", echo_block),
        ("Toxic releases (TRI)", toxic_releases_block),
        ("Site cleanup (Superfund + Brownfields)", site_cleanup_block),
        ("Facility GHG (GHGRP)", facility_ghg_block),
        ("Drinking water (SDWIS)", drinking_water_block),
        ("Active alerts (NWS)", active_alerts_block),
        ("PFAS monitoring", pfas_block),
        ("Streamflow (NRT)", usgs_block),
        ("Water quality (discrete)", wqp_block),
        ("Hazards & Disasters (FEMA + USGS)", hazards_block),
        ("RCRA hazardous waste", toxic_releases_block),
    ] + ([("Coastal Conditions (CO-OPS)", coastal_block)] if coastal_block else []):
        if block.get("status") == "ok":
            methodology.append(
                {
                    "block": block_name,
                    "source": block.get("source"),
                    "source_url": block.get("source_url"),
                    "cadence": block.get("cadence"),
                    "tag": block.get("tag"),
                    "spatial_scope": block.get("spatial_scope"),
                    "license": block.get("license"),
                }
            )

    # Phase E.1 disclaimers. Added conditionally so we don't show them
    # when the underlying block failed / was skipped.
    disclaimers = [
        "Regulatory compliance ≠ environmental exposure or health risk.",
        "Educational / exploratory use only — not a substitute for "
        "an official environmental assessment.",
        "Geographic units vary per block: CBSA bounding box for "
        "facilities/water, reporting area for AirNow, station for "
        "Climate Normals.",
    ]
    if drinking_water_block.get("status") == "ok":
        disclaimers.append(
            "SDWIS violations are regulatory compliance records. A "
            "violation does NOT necessarily indicate unsafe water at the tap."
        )
    if (
        site_cleanup_block.get("status") == "ok"
        and (site_cleanup_block.get("values") or {})
        .get("brownfields", {})
        .get("count", 0)
        > 0
    ):
        disclaimers.append(
            "Brownfields cleanup status is not available via the spatial "
            "point layer and is not reported per-site here."
        )

    return {
        "cbsa_slug": cbsa_slug,
        "meta": meta,
        "key_signals": _key_signals(
            airnow_block,
            echo_block,
            usgs_block,
            facility_ghg=facility_ghg_block,
            site_cleanup=site_cleanup_block,
        ),
        "blocks": {
            "air_quality": airnow_block,
            "climate_locally": climate_block,
            "facilities": echo_block,
            "toxic_releases": toxic_releases_block,
            "site_cleanup": site_cleanup_block,
            "facility_ghg": facility_ghg_block,
            "active_alerts": active_alerts_block,
            "pfas_monitoring": pfas_block,
            "drinking_water": drinking_water_block,
            "water": water_block,
            "hazards_disasters": hazards_block,
            **({"coastal_conditions": coastal_block} if coastal_block else {}),
            "methodology": {
                "status": "ok",
                "sources": methodology,
                "disclaimers": disclaimers,
            },
            "related": {
                "status": "pending",
                "message": (
                    "Related rankings + guides links pending (P1 — "
                    "rankings endpoint not yet populated)."
                ),
            },
        },
    }
