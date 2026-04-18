"""Environmental Data Atlas API — 8 categories (env-eng curriculum)."""
from fastapi import APIRouter

router = APIRouter()

CATEGORIES = [
    {"slug": "air", "title": "Air & Atmosphere"},
    {"slug": "water", "title": "Water Quality, Drinking Water & Wastewater"},
    {"slug": "hydrology", "title": "Hydrology & Floods"},
    {"slug": "coast-ocean", "title": "Coast & Ocean"},
    {"slug": "soil-land", "title": "Soil, Land & Site Condition"},
    {"slug": "waste", "title": "Waste & Materials"},
    {"slug": "emissions", "title": "Emissions, Energy & Facilities"},
    {"slug": "climate-hazards", "title": "Climate, Hazards & Exposure"},
]


@router.get("/categories")
async def list_categories() -> list[dict]:
    return CATEGORIES


@router.get("/{category_slug}")
async def get_category(category_slug: str) -> dict:
    """Return datasets under a category with mandatory trust metadata."""
    return {"slug": category_slug, "datasets": []}
