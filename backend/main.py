"""FastAPI entrypoint for EarthPulse backend."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import atlas, earth_now, rankings, reports, trends
from backend.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name, debug=settings.debug)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
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
