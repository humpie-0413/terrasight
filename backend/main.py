"""FastAPI entrypoint for EarthPulse backend."""
import json

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import (
    atlas,
    drinking_water,
    earth_now,
    layers,
    rankings,
    releases,
    reports,
    sites,
    trends,
)
from backend.config import get_settings


def _parse_origins(raw: str) -> list[str]:
    """Parse CORS_ORIGINS env var — handles plain URL, comma-list, or JSON array."""
    raw = raw.strip()
    if raw.startswith("["):
        return json.loads(raw)
    return [o.strip() for o in raw.split(",") if o.strip()]


settings = get_settings()
cors_origins = _parse_origins(settings.cors_origins)

app = FastAPI(title=settings.app_name, debug=settings.debug)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(trends.router, prefix="/api/trends", tags=["trends"])
app.include_router(earth_now.router, prefix="/api/earth-now", tags=["earth-now"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
app.include_router(atlas.router, prefix="/api/atlas", tags=["atlas"])
app.include_router(rankings.router, prefix="/api/rankings", tags=["rankings"])
app.include_router(layers.router, prefix="/api/layers", tags=["layers"])
# Phase D.1 — EPA regulatory + site datasets (TRI, GHGRP, Superfund, Brownfields, SDWIS)
app.include_router(releases.router, prefix="/api/releases", tags=["releases"])
app.include_router(sites.router, prefix="/api/sites", tags=["sites"])
app.include_router(
    drinking_water.router, prefix="/api/drinking-water", tags=["drinking-water"]
)
