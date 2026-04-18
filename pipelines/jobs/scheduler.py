"""APScheduler jobs — periodic data refresh per connector cadence.

Cadence matrix (matches CLAUDE.md P0 table):
- CO2 (NOAA GML): daily + monthly
- Temp (NOAA CtaG): monthly
- Sea Ice (NSIDC): daily
- FIRMS: every 3 hours
- AirNow: hourly
- OpenAQ: every 30 min (aggregator)
- OISST: daily
- CAMS: 6h
- EPA ECHO: daily
- AirData/AQS: annual refresh
- USGS: every 15 min
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()


def register_jobs() -> None:
    # TODO: register per-connector refresh jobs.
    pass


def start() -> None:
    register_jobs()
    scheduler.start()
