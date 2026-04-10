"""Climate Trends API — CO2 / Global Temp Anomaly / Arctic Sea Ice.

Three slow-moving signals surfaced by the home page Climate Trends strip.
The strip issues a single request to `GET /api/trends` which fans out to
all three connectors in parallel; individual endpoints remain available
for debugging and for deep-link contexts.
"""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException

from backend.connectors.noaa_ctag import NoaaCtagConnector
from backend.connectors.noaa_gml import NoaaGmlConnector
from backend.connectors.nsidc import NsidcConnector, five_day_mean, monthly_means

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


@router.get("")
async def get_trends() -> dict[str, Any]:
    """Fan-out endpoint for the Climate Trends home-page strip.

    Runs all three connectors in parallel. A failure in any single
    indicator is reported as `error` on its entry without blocking the
    others — the UI can render partial strips.
    """
    results = await asyncio.gather(
        _co2_payload(),
        _temperature_payload(),
        _sea_ice_payload(),
        return_exceptions=True,
    )
    indicators: list[dict[str, Any]] = []
    ids = ("co2", "temp", "sea-ice")
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
