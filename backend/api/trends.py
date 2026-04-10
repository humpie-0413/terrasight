"""Climate Trends API — CO2 / Global Temp Anomaly / Arctic Sea Ice."""
from fastapi import APIRouter, HTTPException

from backend.connectors.noaa_gml import NoaaGmlConnector

router = APIRouter()


@router.get("/co2")
async def get_co2() -> dict:
    """NOAA GML Mauna Loa — monthly, observed, since 1958.

    Returns the latest monthly mean plus a 12-month trailing window for the
    Climate Trends card sparkline. Source text file is public CDN, no auth.
    """
    connector = NoaaGmlConnector()
    try:
        result = await connector.run()
    except Exception as exc:  # httpx errors, parse errors
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch NOAA GML CO2 series: {exc}",
        ) from exc

    points = result.values
    if not points:
        raise HTTPException(status_code=502, detail="NOAA GML returned no data")

    latest = points[-1]
    sparkline = points[-12:]

    return {
        "id": "co2",
        "source": result.source,
        "source_url": result.source_url,
        "cadence": result.cadence,
        "tag": result.tag,
        "record_start": "1958",
        "unit": "ppm",
        "latest": {
            "date": latest.iso_month,
            "value": latest.value_ppm,
        },
        "series": [
            {"date": p.iso_month, "value": p.value_ppm} for p in sparkline
        ],
        "notes": result.notes,
    }


@router.get("/temperature")
async def get_temperature() -> dict:
    """NOAA Climate at a Glance — monthly, preliminary, since 1880."""
    return {
        "id": "temp",
        "source": "NOAA Climate at a Glance",
        "cadence": "monthly (preliminary)",
        "tag": "near-real-time",
        "record_start": "1880",
        "latest": None,
        "series": [],
    }


@router.get("/sea-ice")
async def get_sea_ice() -> dict:
    """NSIDC Sea Ice Index — daily 5-day mean, observed, since 1979."""
    return {
        "id": "sea-ice",
        "source": "NSIDC Sea Ice Index",
        "cadence": "daily (5-day running mean)",
        "tag": "observed",
        "record_start": "1979",
        "latest": None,
        "series": [],
    }
