"""Local Environmental Reports API — 6-block metro reports."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/{cbsa_slug}")
async def get_report(cbsa_slug: str) -> dict:
    """Return a full 6-block Local Environmental Report for a metro (CBSA)."""
    # TODO: orchestrate connector calls per block.
    return {
        "cbsa_slug": cbsa_slug,
        "meta": None,
        "blocks": {
            "air_quality": None,        # AirNow current + AirData annual
            "climate_locally": None,    # NOAA CtaG + Normals 1991-2020
            "facilities": None,         # EPA ECHO (regulatory disclaimer required)
            "water": None,              # USGS continuous + WQP discrete
            "methodology": None,
            "related": None,
        },
    }
