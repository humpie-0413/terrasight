"""Climate Trends API — CO₂ / Global Temp / Sea Ice / CH₄ / Sea Level Rise / US Drought.

Six slow-moving signals surfaced by the home page Climate Trends strip.
The strip issues a single request to `GET /api/trends` which fans out to
all six connectors in parallel; individual endpoints remain available
for debugging and for deep-link contexts.
"""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from backend.connectors.noaa_ctag import NoaaCtagConnector
from backend.connectors.noaa_gml import NoaaGmlConnector
from backend.connectors.noaa_gml_ch4 import NoaaGmlCh4Connector
from backend.connectors.noaa_sea_level import NoaaSeaLevelConnector
from backend.connectors.nsidc import NsidcConnector, five_day_mean, monthly_means
from backend.connectors.usdm import UsdmConnector

router = APIRouter()


async def _co2_payload() -> dict[str, Any]:
    connector = NoaaGmlConnector()
    result = await connector.run()
    points = result.values
    if not points:
        raise HTTPException(status_code=502, detail="NOAA GML returned no data")

    latest = points[-1]
    sparkline = points[-12:]
    return {
        "id": "co2",
        "label": "CO₂",
        "unit": "ppm",
        "source": result.source,
        "source_url": result.source_url,
        "cadence": result.cadence,
        "tag": result.tag,
        "record_start": "1958",
        "latest": {"date": latest.iso_month, "value": latest.value_ppm},
        "series": [
            {"date": p.iso_month, "value": p.value_ppm} for p in sparkline
        ],
        "notes": result.notes,
    }


async def _temperature_payload() -> dict[str, Any]:
    connector = NoaaCtagConnector()
    result = await connector.run()
    points = result.values
    if not points:
        raise HTTPException(
            status_code=502, detail="NOAAGlobalTemp returned no data"
        )

    latest = points[-1]
    sparkline = points[-12:]
    return {
        "id": "temp",
        "label": "Global Temp Anomaly",
        "unit": "°C",
        "source": result.source,
        "source_url": result.source_url,
        "cadence": result.cadence,
        "tag": result.tag,
        "record_start": "1850",
        "baseline": "1991-2020",
        "latest": {"date": latest.iso_month, "value": latest.anomaly_c},
        "series": [
            {"date": p.iso_month, "value": p.anomaly_c} for p in sparkline
        ],
        "notes": result.notes,
    }


async def _sea_ice_payload() -> dict[str, Any]:
    connector = NsidcConnector()
    result = await connector.run()
    points = result.values
    if not points:
        raise HTTPException(status_code=502, detail="NSIDC returned no data")

    # Headline value: 5-day running mean of most recent daily observations.
    latest_point = points[-1]
    latest_value = five_day_mean(points)

    # Sparkline: last 12 calendar-month means derived from the daily file.
    monthly = monthly_means(points)[-12:]

    return {
        "id": "sea-ice",
        "label": "Arctic Sea Ice",
        "unit": "million km²",
        "source": result.source,
        "source_url": result.source_url,
        "cadence": result.cadence,
        "tag": result.tag,
        "record_start": "1979",
        "latest": {
            "date": latest_point.iso_date,
            "value": latest_value,
            "window": "5-day mean",
        },
        "series": [{"date": ym, "value": v} for ym, v in monthly],
        "notes": result.notes,
    }


async def _ch4_payload() -> dict[str, Any]:
    connector = NoaaGmlCh4Connector()
    result = await connector.run()
    points = result.values
    if not points:
        raise HTTPException(status_code=502, detail="NOAA GML CH4 returned no data")
    latest = points[-1]
    sparkline = points[-12:]
    return {
        "id": "ch4",
        "label": "CH₄ (Methane)",
        "unit": "ppb",
        "source": result.source,
        "source_url": result.source_url,
        "cadence": result.cadence,
        "tag": result.tag,
        "record_start": "1983",
        "latest": {"date": latest.iso_month, "value": latest.value_ppb},
        "series": [{"date": p.iso_month, "value": p.value_ppb} for p in sparkline],
        "notes": result.notes,
    }


async def _sea_level_payload() -> dict[str, Any]:
    connector = NoaaSeaLevelConnector()
    result = await connector.run()
    if isinstance(result.values, dict):
        raise HTTPException(
            status_code=502,
            detail=f"NOAA sea level fetch failed: {result.values.get('message', 'unknown error')}",
        )
    points = result.values
    if not points:
        raise HTTPException(status_code=502, detail="NOAA sea level returned no data")
    latest = points[-1]
    sparkline = points[-24:]
    return {
        "id": "sea-level",
        "label": "Sea Level Rise",
        "unit": "mm",
        "source": result.source,
        "source_url": result.source_url,
        "cadence": result.cadence,
        "tag": result.tag,
        "record_start": "1992",
        "baseline": "1993–2012 mean",
        "latest": {"date": latest.date_str, "value": round(latest.gmsl_mm, 1)},
        "series": [{"date": p.date_str, "value": round(p.gmsl_mm, 1)} for p in sparkline],
        "notes": result.notes,
    }


async def _drought_payload() -> dict[str, Any]:
    connector = UsdmConnector()
    result = await connector.run(weeks=52)
    points = result.values
    if not points:
        raise HTTPException(status_code=502, detail="USDM returned no data")

    # Sort by map_date ascending to ensure chronological order.
    points.sort(key=lambda s: s.map_date)

    # Moderate drought or worse = D1 + D2 + D3 + D4 area percent.
    series = []
    for p in points:
        val = round(p.d1_pct + p.d2_pct + p.d3_pct + p.d4_pct, 2)
        # map_date arrives as ISO datetime e.g. "2023-06-27T00:00:00";
        # extract just the date portion.
        date_str = p.map_date[:10] if len(p.map_date) >= 10 else p.map_date
        series.append({"date": date_str, "value": val})

    latest_entry = series[-1]
    return {
        "id": "drought",
        "label": "US Drought",
        "unit": "% area ≥D1",
        "source": result.source,
        "source_url": result.source_url,
        "cadence": result.cadence,
        "tag": result.tag,
        "record_start": "2000",
        "latest": {"date": latest_entry["date"], "value": latest_entry["value"]},
        "series": series,
        "notes": ["D1+D2+D3+D4 area percent = moderate drought or worse."],
    }


@router.get("")
async def get_trends() -> dict[str, Any]:
    """Fan-out endpoint for the Climate Trends home-page strip.

    Runs all six connectors in parallel. A failure in any single
    indicator is reported as `error` on its entry without blocking the
    others — the UI can render partial strips.
    """
    results = await asyncio.gather(
        _co2_payload(),
        _temperature_payload(),
        _sea_ice_payload(),
        _ch4_payload(),
        _sea_level_payload(),
        _drought_payload(),
        return_exceptions=True,
    )
    indicators: list[dict[str, Any]] = []
    ids = ("co2", "temp", "sea-ice", "ch4", "sea-level", "drought")
    for indicator_id, outcome in zip(ids, results):
        if isinstance(outcome, Exception):
            indicators.append({"id": indicator_id, "error": str(outcome)})
        else:
            indicators.append(outcome)
    return {"indicators": indicators}


@router.get("/co2")
async def get_co2() -> dict[str, Any]:
    """NOAA GML Mauna Loa — monthly, observed, since 1958."""
    try:
        return await _co2_payload()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Failed to fetch CO₂ series: {exc}"
        ) from exc


@router.get("/temperature")
async def get_temperature() -> dict[str, Any]:
    """NOAAGlobalTemp CDR v6.1 — monthly preliminary anomaly, since 1850."""
    try:
        return await _temperature_payload()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch temperature anomaly series: {exc}",
        ) from exc


@router.get("/sea-ice")
async def get_sea_ice() -> dict[str, Any]:
    """NSIDC Sea Ice Index — daily Arctic extent, 5-day mean headline."""
    try:
        return await _sea_ice_payload()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Failed to fetch sea ice series: {exc}"
        ) from exc


@router.get("/ch4")
async def get_ch4() -> dict[str, Any]:
    """NOAA GML global CH₄ monthly mean — observed, since 1983."""
    try:
        return await _ch4_payload()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch CH4 series: {exc}") from exc


@router.get("/sea-level")
async def get_sea_level() -> dict[str, Any]:
    """NOAA NESDIS GMSL — observed altimetry, since 1992."""
    try:
        return await _sea_level_payload()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch sea level series: {exc}") from exc


@router.get("/drought")
async def get_drought() -> dict[str, Any]:
    """US Drought Monitor — weekly CONUS drought severity, since 2000."""
    try:
        return await _drought_payload()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch drought series: {exc}") from exc


# ─── Born-in helpers ──────────────────────────────────────────────────────────

async def _fetch_co2_all() -> list:
    connector = NoaaGmlConnector()
    result = await connector.run()
    return result.values


async def _fetch_temp_all() -> list:
    connector = NoaaCtagConnector()
    result = await connector.run()
    return result.values


async def _fetch_ice_all() -> list:
    connector = NsidcConnector()
    result = await connector.run()
    return result.values


@router.get("/born-in")
async def get_born_in(
    year: int = Query(..., ge=1850, le=2025, description="Birth year"),
) -> dict[str, Any]:
    """Birth-year vs now: CO₂, global temperature, Arctic sea ice.

    Record constraints applied automatically:
    - CO₂: starts 1958 (Mauna Loa). Years before 1958 clamped.
    - Temp: starts 1850 (NOAAGlobalTemp). No clamping needed.
    - Sea ice: starts 1979 (NSIDC AMSR2). Years before 1979 clamped.
      Uses September mean (traditional annual minimum metric).

    'then' = annual mean for birth year (September mean for sea ice).
    'now' = most recent available value.
    """
    co2_pts, temp_pts, ice_pts = await asyncio.gather(
        _fetch_co2_all(),
        _fetch_temp_all(),
        _fetch_ice_all(),
        return_exceptions=True,
    )

    indicators: list[dict[str, Any]] = []

    # ── CO₂ ──────────────────────────────────────────────────────────────────
    CO2_START = 1958
    co2_year = max(year, CO2_START)
    if not isinstance(co2_pts, Exception) and co2_pts:
        then_pts = [p for p in co2_pts if p.year == co2_year]
        if then_pts:
            then_val = round(sum(p.value_ppm for p in then_pts) / len(then_pts), 2)
            now_pt = co2_pts[-1]
            now_val = round(now_pt.value_ppm, 2)
            delta = round(now_val - then_val, 2)
            indicators.append({
                "id": "co2",
                "label": "CO₂ Concentration",
                "unit": "ppm",
                "record_start": CO2_START,
                "birth_year_used": co2_year,
                "clamped": co2_year != year,
                "then": {"date": str(co2_year), "value": then_val},
                "now": {"date": now_pt.iso_month, "value": now_val},
                "delta_abs": delta,
                "delta_pct": round(delta / then_val * 100, 1),
            })
        else:
            indicators.append({"id": "co2", "error": f"No data for {co2_year}"})
    else:
        indicators.append({"id": "co2", "error": str(co2_pts)})

    # ── Temperature ───────────────────────────────────────────────────────────
    TEMP_START = 1850
    temp_year = max(year, TEMP_START)
    if not isinstance(temp_pts, Exception) and temp_pts:
        then_pts = [p for p in temp_pts if p.year == temp_year]
        if then_pts:
            then_val = round(sum(p.anomaly_c for p in then_pts) / len(then_pts), 2)
            now_pt = temp_pts[-1]
            now_val = round(now_pt.anomaly_c, 2)
            delta = round(now_val - then_val, 2)
            indicators.append({
                "id": "temp",
                "label": "Global Temp Anomaly",
                "unit": "°C vs 1991–2020",
                "record_start": TEMP_START,
                "birth_year_used": temp_year,
                "clamped": False,
                "then": {"date": str(temp_year), "value": then_val},
                "now": {"date": now_pt.iso_month, "value": now_val},
                "delta_abs": delta,
                "delta_pct": None,  # anomaly: % change is not meaningful
            })
        else:
            indicators.append({"id": "temp", "error": f"No data for {temp_year}"})
    else:
        indicators.append({"id": "temp", "error": str(temp_pts)})

    # ── Sea Ice (September mean — annual minimum) ─────────────────────────────
    ICE_START = 1979
    ice_year = max(year, ICE_START)
    if not isinstance(ice_pts, Exception) and ice_pts:
        sept_then = [p for p in ice_pts if p.year == ice_year and p.month == 9]
        # Most recent year that has September data
        max_sept_year = max((p.year for p in ice_pts if p.month == 9), default=None)
        sept_now = (
            [p for p in ice_pts if p.year == max_sept_year and p.month == 9]
            if max_sept_year else []
        )
        if sept_then and sept_now:
            then_val = round(
                sum(p.extent_million_km2 for p in sept_then) / len(sept_then), 2
            )
            now_val = round(
                sum(p.extent_million_km2 for p in sept_now) / len(sept_now), 2
            )
            delta = round(now_val - then_val, 2)
            indicators.append({
                "id": "sea-ice",
                "label": "Arctic Sea Ice (Sep)",
                "unit": "million km²",
                "record_start": ICE_START,
                "birth_year_used": ice_year,
                "clamped": ice_year != year,
                "then": {"date": f"Sep {ice_year}", "value": then_val},
                "now": {"date": f"Sep {max_sept_year}", "value": now_val},
                "delta_abs": delta,
                "delta_pct": round(delta / then_val * 100, 1) if then_val else None,
            })
        else:
            indicators.append({
                "id": "sea-ice",
                "error": f"No September data for {ice_year}",
            })
    else:
        indicators.append({"id": "sea-ice", "error": str(ice_pts)})

    return {"year": year, "indicators": indicators}
