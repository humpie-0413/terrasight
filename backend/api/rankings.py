"""Fact Rankings API.

Per CLAUDE.md: each ranking must disclose source & criterion.
- EPA violations ranking → ECHO
- PM2.5 annual ranking → AirData/AQS
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/{ranking_slug}")
async def get_ranking(ranking_slug: str) -> dict:
    return {
        "slug": ranking_slug,
        "source": None,
        "criterion": None,
        "rows": [],
    }
