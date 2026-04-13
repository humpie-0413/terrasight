"""Earth Now Integrated API — derived layers that combine multiple connectors.

These endpoints aggregate and cross-reference raw Earth Now data sources
into higher-level grids suitable for heatmap / choropleth visualization
on the globe. Every response carries tag="derived" because the output
is computed from upstream observed/NRT feeds.
"""
from __future__ import annotations

import asyncio
import math
from typing import Any

from fastapi import APIRouter, Query

from backend.config import get_settings
from backend.connectors.coral_reef_watch import CoralReefWatchConnector
from backend.connectors.firms import FirmsConnector, top_by_frp
from backend.connectors.oisst import OisstConnector

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _grid_key(lat: float, lon: float, resolution: float) -> tuple[float, float]:
    """Snap a point to the south-west corner of its grid cell."""
    return (
        math.floor(lat / resolution) * resolution,
        math.floor(lon / resolution) * resolution,
    )


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


# ---------------------------------------------------------------------------
# 1. Ocean Health — SST × Coral DHW integrated stress grid
# ---------------------------------------------------------------------------

@router.get("/ocean-health")
async def ocean_health() -> dict[str, Any]:
    """Combine OISST SST and Coral Reef Watch DHW into a unified ocean
    stress grid at 2° resolution.

    Stress score formula (simplified):
        sst_anomaly = sst_c - 25.0  (25 °C ≈ approximate global mean SST)
        stress = clamp((sst_anomaly / 5.0) * 0.4 + (dhw / 8.0) * 0.6, 0, 1)

    Graceful degradation: if one connector fails the other still contributes
    partial data.
    """
    RESOLUTION = 2.0
    APPROX_MEAN_SST = 25.0

    # -- Parallel fetch from both connectors --------------------------------
    sst_connector = OisstConnector()
    coral_connector = CoralReefWatchConnector()

    sst_error: str | None = None
    coral_error: str | None = None
    sst_points: list[Any] = []
    coral_points: list[Any] = []

    async def _fetch_sst() -> None:
        nonlocal sst_points, sst_error
        try:
            raw = await sst_connector.fetch()
            result = sst_connector.normalize(raw)
            sst_points = result.values if isinstance(result.values, list) else []
        except Exception as exc:
            sst_error = f"OISST fetch failed: {exc}"

    async def _fetch_coral() -> None:
        nonlocal coral_points, coral_error
        try:
            raw = await coral_connector.fetch(include_no_stress=True)
            result = coral_connector.normalize(raw)
            if isinstance(result.values, dict):
                # Connector returned an error dict instead of a list
                coral_error = result.values.get("message", "Coral Reef Watch returned error")
                return
            coral_points = result.values
        except Exception as exc:
            coral_error = f"Coral Reef Watch fetch failed: {exc}"

    await asyncio.gather(_fetch_sst(), _fetch_coral())

    # -- Build the 2° grid --------------------------------------------------
    # Each cell accumulates SST and DHW values for averaging.
    grid: dict[tuple[float, float], dict[str, Any]] = {}

    for pt in sst_points:
        # Only include cells within the ocean-health lat band
        if pt.lat < -60.0 or pt.lat > 60.0:
            continue
        key = _grid_key(pt.lat, pt.lon, RESOLUTION)
        cell = grid.setdefault(key, {
            "sst_values": [],
            "dhw_values": [],
            "source_count": 0,
        })
        cell["sst_values"].append(pt.sst_c)

    for pt in coral_points:
        if pt.lat < -60.0 or pt.lat > 60.0:
            continue
        key = _grid_key(pt.lat, pt.lon, RESOLUTION)
        cell = grid.setdefault(key, {
            "sst_values": [],
            "dhw_values": [],
            "source_count": 0,
        })
        cell["dhw_values"].append(pt.dhw)

    # -- Compute per-cell stress score --------------------------------------
    output_grid: list[dict[str, Any]] = []

    for (lat, lon), cell in grid.items():
        sst_vals = cell["sst_values"]
        dhw_vals = cell["dhw_values"]

        if not sst_vals and not dhw_vals:
            continue

        avg_sst: float | None = None
        avg_dhw: float | None = None
        source_count = 0

        if sst_vals:
            avg_sst = sum(sst_vals) / len(sst_vals)
            source_count += 1
        if dhw_vals:
            avg_dhw = sum(dhw_vals) / len(dhw_vals)
            source_count += 1

        # Stress formula components (use 0 contribution if data missing)
        sst_anomaly = (avg_sst - APPROX_MEAN_SST) if avg_sst is not None else 0.0
        sst_component = (sst_anomaly / 5.0) * 0.4
        dhw_component = ((avg_dhw / 8.0) * 0.6) if avg_dhw is not None else 0.0
        stress = _clamp(sst_component + dhw_component)

        entry: dict[str, Any] = {
            "lat": lat,
            "lon": lon,
            "stress_score": round(stress, 4),
            "source_count": source_count,
        }
        if avg_sst is not None:
            entry["sst_c"] = round(avg_sst, 2)
        if avg_dhw is not None:
            entry["dhw"] = round(avg_dhw, 2)

        output_grid.append(entry)

    # -- Stats --------------------------------------------------------------
    stress_values = [c["stress_score"] for c in output_grid]
    stats: dict[str, Any] = {}
    if stress_values:
        stats = {
            "min_stress": round(min(stress_values), 4),
            "max_stress": round(max(stress_values), 4),
            "mean_stress": round(sum(stress_values) / len(stress_values), 4),
        }
    else:
        stats = {"min_stress": None, "max_stress": None, "mean_stress": None}

    # -- Build notes (graceful degradation) ---------------------------------
    notes: list[str] = []
    status = "ok"
    if sst_error and coral_error:
        status = "error"
        notes.append(sst_error)
        notes.append(coral_error)
    elif sst_error:
        status = "partial"
        notes.append(sst_error)
        notes.append("Grid contains only Coral Reef Watch DHW data (SST unavailable).")
    elif coral_error:
        status = "partial"
        notes.append(coral_error)
        notes.append("Grid contains only OISST SST data (Coral DHW unavailable).")
    else:
        notes.append("Both SST and Coral DHW sources integrated successfully.")

    return {
        "source": "NOAA OISST + Coral Reef Watch (integrated)",
        "cadence": "daily",
        "tag": "derived",
        "status": status,
        "count": len(output_grid),
        "grid": output_grid,
        "stats": stats,
        "notes": notes,
    }


# ---------------------------------------------------------------------------
# 2. Fire Density — FIRMS points aggregated into a density grid
# ---------------------------------------------------------------------------

@router.get("/fire-density")
async def fire_density(
    resolution: int = Query(2, ge=1, le=5, description="Grid cell size in degrees"),
) -> dict[str, Any]:
    """Aggregate NASA FIRMS fire hotspots into a density grid.

    Each grid cell reports fire_count, avg_frp, max_frp, and total_frp
    for all hotspots that fall within it. Empty cells are omitted.

    Graceful degradation: returns an empty grid with an error note when
    FIRMS is unconfigured or the upstream fetch fails.
    """
    settings = get_settings()
    connector = FirmsConnector(map_key=settings.firms_map_key)

    fire_error: str | None = None
    hotspots: list[Any] = []

    if not settings.firms_map_key:
        fire_error = (
            "FIRMS_MAP_KEY is not configured. Register at "
            "https://firms.modaps.eosdis.nasa.gov/api/map_key/ "
            "and set FIRMS_MAP_KEY in the project-root .env."
        )
    else:
        try:
            raw = await connector.fetch(days=1)
            result = connector.normalize(raw)
            # Use top 2000 fires by FRP for the density grid
            hotspots = top_by_frp(result.values, limit=2000)
        except Exception as exc:
            fire_error = f"FIRMS fetch failed: {exc}"

    # -- Build grid ---------------------------------------------------------
    grid: dict[tuple[float, float], dict[str, Any]] = {}

    for h in hotspots:
        key = _grid_key(h.lat, h.lon, float(resolution))
        cell = grid.setdefault(key, {
            "fire_count": 0,
            "frp_values": [],
        })
        cell["fire_count"] += 1
        cell["frp_values"].append(h.frp)

    # -- Aggregate per cell -------------------------------------------------
    output_grid: list[dict[str, Any]] = []
    total_fires = 0
    max_density = 0

    for (lat, lon), cell in grid.items():
        count = cell["fire_count"]
        frps = cell["frp_values"]
        total_fires += count
        if count > max_density:
            max_density = count

        output_grid.append({
            "lat": lat,
            "lon": lon,
            "fire_count": count,
            "avg_frp": round(sum(frps) / len(frps), 2),
            "max_frp": round(max(frps), 2),
            "total_frp": round(sum(frps), 2),
        })

    # -- Response -----------------------------------------------------------
    notes: list[str] = []
    status = "ok"
    if fire_error:
        status = "error" if not settings.firms_map_key else "error"
        notes.append(fire_error)
    else:
        notes.append(
            f"Aggregated {total_fires} fire hotspots into "
            f"{len(output_grid)} grid cells at {resolution}° resolution."
        )

    configured = settings.firms_map_key is not None

    return {
        "source": "NASA FIRMS (aggregated)",
        "cadence": "NRT ~3h",
        "tag": "derived",
        "status": status,
        "configured": configured,
        "count": len(output_grid),
        "resolution_deg": resolution,
        "grid": output_grid,
        "stats": {
            "total_fires": total_fires,
            "max_density": max_density,
        },
        "notes": notes,
    }
