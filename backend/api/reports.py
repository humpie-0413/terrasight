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
from backend.connectors.airnow import AirNowConnector, worst_reading
from backend.connectors.climate_normals import ClimateNormalsConnector
from backend.connectors.echo import EchoConnector
from backend.connectors.usgs import UsgsConnector
from backend.connectors.wqp import WqpConnector

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


def _key_signals(
    air: dict[str, Any],
    echo: dict[str, Any],
    usgs: dict[str, Any],
) -> list[dict[str, Any]]:
    """Block 0 rollup: 4 mini-cards on the metro header.

    `usgs` is the flat hydrology block (not the combined water block).
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

    return [aqi_card, temp_card, fac_card, water_card]


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

    airnow_res, echo_res, usgs_res, wqp_res, normals_res = await asyncio.gather(
        airnow_task,
        echo_task,
        usgs_task,
        wqp_task,
        normals_task,
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
        ("Streamflow (NRT)", usgs_block),
        ("Water quality (discrete)", wqp_block),
    ]:
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

    return {
        "cbsa_slug": cbsa_slug,
        "meta": meta,
        "key_signals": _key_signals(airnow_block, echo_block, usgs_block),
        "blocks": {
            "air_quality": airnow_block,
            "climate_locally": climate_block,
            "facilities": echo_block,
            "water": water_block,
            "methodology": {
                "status": "ok",
                "sources": methodology,
                "disclaimers": [
                    "Regulatory compliance ≠ environmental exposure or health risk.",
                    "Educational / exploratory use only — not a substitute for "
                    "an official environmental assessment.",
                    "Geographic units vary per block: CBSA bounding box for "
                    "facilities/water, reporting area for AirNow, station for "
                    "Climate Normals.",
                ],
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
