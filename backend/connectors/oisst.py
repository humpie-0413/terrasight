"""NOAA OISST daily SST connector — via NOAA CoastWatch ERDDAP.

Product: NOAA 1/4° Daily Optimum Interpolation SST v2.1 (AVHRR-Only)
Cadence: daily (1-day latency for NRT; final after ~2 weeks)
Tag:     observed (NRT) / derived (gap-filled OI product, but treated as observed per spec)

=============================================================================
BLOCKER RESOLUTION (2026-04-10 OISST blocker spike):

The canonical NCEI THREDDS endpoint documented on the OISST product page is
DEAD:
  ❌ https://www.ncei.noaa.gov/thredds/dodsC/model-oisst-daily/ → OPeNDAP error
  ❌ https://www.ncei.noaa.gov/thredds-ocean/fileServer/oisst-daily/... → 404

Verified live alternative: NOAA CoastWatch ERDDAP griddap server.
  ✅ https://coastwatch.pfeg.noaa.gov/erddap/griddap/ncdcOisst21NrtAgg  (NRT)
  ✅ https://coastwatch.pfeg.noaa.gov/erddap/griddap/ncdcOisst21Agg     (final, 2-week delay)

Live sample call (verified 2026-04-10, returned SST for 2026-04-08):
  curl "https://coastwatch.pfeg.noaa.gov/erddap/griddap/ncdcOisst21NrtAgg.csv\\
        ?sst%5B(last)%5D%5B(0.0)%5D%5B(0):(0.25)%5D%5B(0):(0.25)%5D"

ERDDAP advantages over THREDDS:
- No auth, no Earthdata login
- URL-based bbox + time slicing (%5B...%5D syntax = [start:stride:stop])
- CSV / JSON / NetCDF / PNG / WMS tile output
- WMS tile endpoint available for Earth Now globe layer:
  https://coastwatch.pfeg.noaa.gov/erddap/wms/ncdcOisst21NrtAgg/request

Fallback (if ERDDAP also degrades):
- NASA PODAAC GHRSST AVHRR_OI-NCEI-L4-GLOB-v2.1 (same underlying product,
  different distributor) — requires NASA Earthdata Login, use earthaccess lib.
  CMR collection id: C2036881712-POCLOUD
=============================================================================

Used for: Earth Now "Ocean Heat" layer.
"""
from typing import Any

from backend.connectors.base import BaseConnector, ConnectorResult

ERDDAP_BASE = "https://coastwatch.pfeg.noaa.gov/erddap"

# Dataset IDs
DATASET_NRT = "ncdcOisst21NrtAgg"   # Near-real-time (1-day latency)
DATASET_FINAL = "ncdcOisst21Agg"    # Final (~2-week delay)

# Default: use NRT for Earth Now layer (freshness matters more than stability here)
DEFAULT_DATASET = DATASET_NRT

# WMS endpoint for globe layer rendering
WMS_ENDPOINT = f"{ERDDAP_BASE}/wms/{DEFAULT_DATASET}/request"


class OisstConnector(BaseConnector):
    name = "oisst"
    source = "NOAA OISST v2.1 (via CoastWatch ERDDAP)"
    source_url = f"{ERDDAP_BASE}/griddap/{DEFAULT_DATASET}"
    cadence = "daily (1-day latency, NRT)"
    tag = "observed"

    async def fetch(self, **params: Any) -> Any:
        raise NotImplementedError

    def normalize(self, raw: Any) -> ConnectorResult:
        raise NotImplementedError
