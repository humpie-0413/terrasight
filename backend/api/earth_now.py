"""Earth Now API — globe layers + this month's climate story."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/layers")
async def list_layers() -> list[dict]:
    """Return available globe layers with trust metadata."""
    return [
        {"id": "gibs-natural-earth", "title": "Natural Earth", "kind": "base", "tag": "observed", "default": True},
        {"id": "firms", "title": "Fires", "kind": "event", "tag": "observed", "cadence": "NRT ~3h", "default": True},
        {"id": "oisst", "title": "Ocean Heat", "kind": "continuous", "tag": "observed", "cadence": "daily"},
        {"id": "cams-smoke", "title": "Smoke", "kind": "continuous", "tag": "forecast", "cadence": "6-12h"},
        {"id": "openaq", "title": "Air monitors", "kind": "event", "tag": "observed", "cadence": "varies"},
    ]


@router.get("/story")
async def get_story() -> dict:
    """This month's climate story (preset-driven editorial)."""
    # TODO: load from editorial preset bank (5-10 presets)
    return {"title": None, "body": None, "preset_id": None, "globe_hint": None, "report_link": None}
