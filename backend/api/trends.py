"""Climate Trends API — CO2 / Global Temp Anomaly / Arctic Sea Ice."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/co2")
async def get_co2() -> dict:
    """NOAA GML Mauna Loa — daily + monthly, observed, since 1958."""
    # TODO: delegate to NoaaGmlConnector
    return {
        "id": "co2",
        "source": "NOAA GML Mauna Loa",
        "cadence": "daily + monthly",
        "tag": "observed",
        "record_start": "1958",
        "latest": None,
        "series": [],
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
