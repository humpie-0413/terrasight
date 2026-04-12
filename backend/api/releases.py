"""Releases & emissions API — EPA TRI + GHGRP facility-level disclosures.

Endpoints (mounted at /api/releases in main.py):
  GET /tri?state=TX&limit=100   -> EPA TRI facility list (self-reported)
  GET /ghgrp?state=TX&limit=100 -> EPA GHGRP FLIGHT facility list + CO2e totals

Graceful degradation contract (per CLAUDE.md rule 5):
  - Never raises HTTPException for upstream errors; returns a dict with
    `status: "error"` and a `message` field instead.
  - Always exposes `source`, `source_url`, `cadence`, `tag` so the
    frontend can still render trust metadata when the dataset is empty.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, Query

from backend.connectors.ghgrp import GhgrpConnector
from backend.connectors.rcra import RcraConnector
from backend.connectors.tri import TriConnector

router = APIRouter()


def _error_response(connector: Any, message: str, key: str) -> dict[str, Any]:
    return {
        "source": connector.source,
        "source_url": connector.source_url,
        "cadence": connector.cadence,
        "tag": connector.tag,
        "count": 0,
        "configured": True,
        "status": "error",
        "message": message,
        key: [],
    }


@router.get("/tri")
async def get_tri(
    state: str = Query("TX", min_length=2, max_length=2, description="US state code (2 letters)"),
    limit: int = Query(100, ge=1, le=500, description="Max facilities to return"),
    year: int | None = Query(
        None,
        ge=1987,
        le=2100,
        description="Reporting year for chemical enrichment (optional)",
    ),
) -> dict[str, Any]:
    """EPA TRI facility list for a state (self-reported EPCRA 313)."""
    connector = TriConnector()
    try:
        raw = await connector.fetch(state=state, limit=limit, year=year)
        result = connector.normalize(raw)
    except Exception as exc:  # graceful — no 5xx to the client
        return _error_response(connector, str(exc), key="facilities")

    return {
        "source": result.source,
        "source_url": result.source_url,
        "cadence": result.cadence,
        "tag": result.tag,
        "spatial_scope": result.spatial_scope,
        "license": result.license,
        "count": len(result.values),
        "configured": True,
        "status": "ok",
        "state": state.upper(),
        "year": year,
        "facilities": [asdict(f) for f in result.values],
        "notes": result.notes,
    }


@router.get("/ghgrp")
async def get_ghgrp(
    state: str = Query("TX", min_length=2, max_length=2, description="US state code (2 letters)"),
    limit: int = Query(100, ge=1, le=500, description="Max facilities to return"),
    year: int | None = Query(
        None,
        ge=2010,
        le=2100,
        description="GHGRP reporting year (default: latest, 2023)",
    ),
) -> dict[str, Any]:
    """EPA GHGRP FLIGHT facility list + per-facility CO2e totals."""
    connector = GhgrpConnector()
    try:
        raw = await connector.fetch(state=state, limit=limit, year=year)
        result = connector.normalize(raw)
    except Exception as exc:
        return _error_response(connector, str(exc), key="facilities")

    return {
        "source": result.source,
        "source_url": result.source_url,
        "cadence": result.cadence,
        "tag": result.tag,
        "spatial_scope": result.spatial_scope,
        "license": result.license,
        "count": len(result.values),
        "configured": True,
        "status": "ok",
        "state": state.upper(),
        "year": raw.get("year") if isinstance(raw, dict) else year,
        "facilities": [asdict(f) for f in result.values],
        "notes": result.notes,
    }


@router.get("/rcra")
async def get_rcra(
    state: str = Query("TX", min_length=2, max_length=2, description="US state code (2 letters)"),
    limit: int = Query(100, ge=1, le=500, description="Max rows to return"),
    year: int | None = Query(
        None,
        ge=2001,
        le=2100,
        description="RCRA biennial report cycle year (optional)",
    ),
) -> dict[str, Any]:
    """EPA RCRA Biennial Report — hazardous waste generators by state."""
    connector = RcraConnector()
    try:
        raw = await connector.fetch(state=state, limit=limit, year=year)
        result = connector.normalize(raw)
    except Exception as exc:
        return _error_response(connector, str(exc), key="facilities")

    return {
        "source": result.source,
        "source_url": result.source_url,
        "cadence": result.cadence,
        "tag": result.tag,
        "spatial_scope": result.spatial_scope,
        "license": result.license,
        "count": len(result.values),
        "configured": True,
        "status": "ok",
        "state": state.upper(),
        "year": raw.get("year") if isinstance(raw, dict) else year,
        "facilities": [asdict(f) for f in result.values],
        "notes": result.notes,
    }
