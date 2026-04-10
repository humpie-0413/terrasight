# Data Sources & Connector Catalog

Detailed per-source reference for every P0/P1/P2 dataset in EarthPulse.
Connector implementations live in `backend/connectors/`; this file is the
source of truth for cadence, trust tag, and update rhythm.

## Trust-tag vocabulary (5 levels)

| Tag | Color | Meaning |
|---|---|---|
| observed | 🟢 | Direct instrument measurement |
| near-real-time | 🟡 | Processed within a few hours |
| forecast/model | 🟠 | CAMS, GFS etc. — model output |
| derived | 🔵 | Calculated from observed values |
| estimated | ⚪ | Statistical / ML inference |

Every data surface in the UI must attach one of these tags. The
`backend/connectors/base.py::ConnectorResult.tag` field enforces this
at the type level (`Literal["observed", ...]`).

---

## P0 — MVP spine

### Earth Now (globe layers)

| Source | Purpose | Cadence | Tag |
|---|---|---|---|
| NASA GIBS / Worldview | Base imagery | varies | observed / NRT |
| NASA FIRMS | Wildfires / thermal anomalies | NRT ~3h | observed |
| AirNow | Current AQI (reports) | hourly | observed |
| OpenAQ v3 | Global air monitors (home globe) | varies | observed |
| NOAA OISST | Daily SST | daily | observed |
| CAMS | Smoke / atmospheric composition | 6–12h | forecast/model |

### Climate Trends (3 cards)

| Card | Source | Cadence | Tag | Record start |
|---|---|---|---|---|
| CO₂ concentration | NOAA GML Mauna Loa | daily + monthly | observed | 1958 |
| Global temp anomaly | NOAA CtaG (via NOAAGlobalTemp CDR v6.1) | monthly | NRT / preliminary | 1850 |
| Arctic sea ice | NSIDC Sea Ice Index (G02135 v4.0, 5-day mean) | daily | observed | 1978 |

### Local Reports

| Source | Purpose | Cadence | Tag |
|---|---|---|---|
| AirNow | Current AQI | hourly | observed |
| EPA AirData / AQS | Annual AQI, PM2.5 | annual | observed |
| NOAA CtaG | City temperature time series | monthly | observed |
| U.S. Climate Normals 1991-2020 | Reference baseline | 30-yr | derived |
| EPA ECHO | Facilities / violations / enforcement | live feed | regulatory |
| USGS modernized OGC API | Continuous hydrology | 15-min | observed |
| WQP `/wqx3/` beta | Discrete water-quality samples | discrete | observed |

### Story Panel

Preset-driven editorial — 5 to 10 seasonal / event templates sitting on
top of Earth Now layers. Currently one hardcoded preset ("2026 Wildfire
Season") at `/api/earth-now/story`.

---

## P1 — Differentiators

- Worldview additional imagery layers
- ECHO fact rankings (EPA violations)
- AirData PM2.5 annual rankings
- Born-in Interactive (CO₂ / temp / sea ice then vs now)
- Educational guide series

## P2 — Expansion

- Soil / Land (SoilGrids)
- Waste & Materials (hazardous waste, TRI)
- Climate TRACE emissions facility map
- Global Local Report expansion
- Custom aggregate environmental indicators

---

## Verified endpoint quirks (from the 2026-04-10 API spike)

These are the landmines; every connector touching the listed source must
handle them exactly as described.

### EPA ECHO
- **HTTP only** — `https://ofmpub.epa.gov/...` returns 404. Use
  `http://ofmpub.epa.gov/echo/echo13_rest_services.get_facilities`.
- Bounding-box params: `p_c1lon`, `p_c1lat` (W/S) / `p_c2lon`, `p_c2lat`
  (E/N). `Output=JSON` + `responseset=N` returns the first response with
  QueryID, Totals, and the first N facilities.
- Facility-level violation flags (`CurrVioFlag`, `Over3yrsFormalActions`,
  `Over3yrsEnfAmt`) live on each facility object in the first response —
  no QID second-hop needed for counts.
- Some deployment networks block `ofmpub.epa.gov`; the connector must
  surface a timeout as a block-level error and the orchestrator must
  degrade the report gracefully.

### USGS modernized Water Data
- Base: `https://api.waterdata.usgs.gov/ogcapi/v0/`. Legacy
  `waterservices.usgs.gov/` is scheduled for 2027 Q1 decommission.
- Use `/collections/daily/items?bbox=W,S,E,N&parameter_code=00060&datetime=<start>/<end>`.
- Feature property names observed live: `monitoring_location_id`, `time`
  (YYYY-MM-DD), `value` (string), `unit_of_measure`, `parameter_code`,
  `statistic_id`, `approval_status`.
- **Feature payload has no site_name** — a second lookup against
  `/collections/monitoring-locations/items` is required for
  human-readable labels; we fall back to the USGS site ID for now.
- Features are NOT time-sorted; `datetime` interval is essential and we
  dedupe per `monitoring_location_id` in `normalize()`.

### WQP (Water Quality Portal)
- **Use `/wqx3/` beta endpoints, NOT `/data/`.** The legacy
  `/data/` path serves WQX 2.2 only and is missing all USGS data added
  or modified after 2024-03-11.
- `/wqx3/Result/search` returns **HTTP 500** without
  `dataProfile=basicPhysChem`. Always include it.
- WQX 3.0 column renames (critical — the 2.2 names silently fall
  through as `None`):
  - `Location_Identifier` (was `MonitoringLocationIdentifier`)
  - `Result_Characteristic` (was `CharacteristicName`)
  - `Result_Measure` (was `ResultMeasureValue`)
  - `Result_MeasureUnit` (was `ResultMeasure/MeasureUnitCode`)
  - `Activity_StartDate`, `ProviderName`, `Location_Name` unchanged
- **`providers=NWIS,STORET` (comma-joined) matches zero rows.** WQP
  treats the comma as a literal character. Emit `providers=NWIS` and
  `providers=STORET` as separate repeated params via an httpx list of
  tuples.
- Dates use `MM-DD-YYYY`, not ISO.

### U.S. Climate Normals 1991-2020
- Per-station CSVs at `https://www.ncei.noaa.gov/data/normals-monthly/1991-2020/access/{STATION_ID}.csv`.
- Each file has exactly 12 monthly rows (`DATE = "01".."12"`) and ~260
  columns. We extract `STATION`, `NAME`, `LATITUDE`, `LONGITUDE`,
  `ELEVATION`, plus `MLY-TAVG-NORMAL`, `MLY-TMAX-NORMAL`,
  `MLY-TMIN-NORMAL`, `MLY-PRCP-NORMAL`.
- Missing-value sentinels: `-9999`, `-7777`, blank. Numeric cells are
  space-padded; strip before parsing.
- `USW00012918` is Houston **Hobby** AP, not Intercontinental.

### NOAA GML Mauna Loa
- Direct file: `co2_mm_mlo.txt`. Comment lines prefixed with `#`. No
  auth.

### NOAAGlobalTemp CDR (CtaG pivot)
- CtaG UI has no public REST API. Pivot to
  `ncei.noaa.gov/data/noaa-global-surface-temperature/v6.1/access/timeseries/aravg.mon.land_ocean.90S.90N.v6.1.0.YYYYMM.asc`.
- Filename embeds data-month; scrape the directory index to discover
  the latest file.
- Anomalies are °C relative to the **1991-2020** climatology (many
  other products use 1961-1990 — do not cross-compare magnitudes).

### NSIDC Sea Ice
- `N_seaice_extent_daily_v4.0.csv` at `noaadata.apps.nsidc.org`. The
  "Source Data" column contains commas — parse via `csv` module, not
  naive `.split(",")`.

### NOAA OISST
- PODAAC GHRSST is a fallback. Primary is **NOAA CoastWatch ERDDAP
  griddap CSV** at `ncdcOisst21NrtAgg`, stride 20, two header rows,
  filter NaN land cells, convert 0–360 lon to -180..180.

### NASA FIRMS
- Area API: `api/area/csv/{MAP_KEY}/{SOURCE}/{AREA}/{DAYS}`. Full
  global 24h VIIRS is 30k+ points — cap to top N by FRP before
  sending to the browser.

### OpenAQ v3
- v1/v2 retired 2025-01-31. Use `/locations?parameters_id=2&limit=1000`
  for PM2.5 — the single call returns station + coords + latest reading
  inline, no second hop to `/measurements`.
- `X-API-Key` header, ~2000 req/hr.

### AirNow
- Verified: `https://www.airnowapi.org/aq/observation/zipCode/current/`.
  `format=application/json`, `zipCode`, `distance` (miles, default 25),
  `API_KEY`. ~500 req/hr/endpoint.
- Response is one observation per pollutant; the connector picks the
  worst (max AQI) as the headline, matching how AirNow itself
  summarizes a reporting area.

### CAMS
- No public WMS tile endpoint without a Copernicus ADS account. The
  Smoke toggle on the globe ships **disabled** with a tooltip; full
  cdsapi integration is deferred to P1. MODIS AOD from NASA GIBS is a
  possible substitute but not CAMS.

### NASA GIBS (base imagery)
- Public WMTS + WMS, no auth. Default home base:
  `BlueMarble_ShadedRelief_Bathymetry`. `Access-Control-Allow-Origin: *`.

---

## API key registration (free)

| Source | Env var | Register |
|---|---|---|
| NASA FIRMS | `FIRMS_MAP_KEY` | https://firms.modaps.eosdis.nasa.gov/api/map_key/ |
| OpenAQ v3 | `OPENAQ_API_KEY` | https://explore.openaq.org/ |
| AirNow | `AIRNOW_API_KEY` | https://docs.airnowapi.org/ |
| EPA AQS | `AQS_EMAIL` + `AQS_KEY` | https://aqs.epa.gov/aqsweb/documents/data_api.html |
| Copernicus ADS (CAMS) | ADS account + cdsapi | https://ads.atmosphere.copernicus.eu/ |

ECHO, NSIDC, NOAA GML/CtaG/Normals, USGS, WQP, NASA GIBS all require
**no key**.
