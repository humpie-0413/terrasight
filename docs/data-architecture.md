# TerraSight — Data Architecture

**Created:** 2026-04-15
**Purpose:** Definitive spec for every Globe surface layer — data source,
rendering approach, API endpoint, and current status.

---

## Globe Layer Classification

| Type | Rendering | Example |
|------|-----------|---------|
| **Surface** | Backend renders equirectangular PNG → 6 BitmapLayer strips | SST, PM2.5, Temperature |
| **Event** | Frontend ScatterplotLayer / PathLayer from JSON API | Wildfires, Earthquakes |
| **GIBS** | Frontend TileLayer from NASA GIBS WMS (pass-through) | CO₂ (OCO-2) |

---

## Surface Layers (Self-Rendered Pipeline)

Pipeline: Connector → `render_gridded_surface_png()` → full PNG → `_crop_strips()` → 6 strip PNGs → cache → `GET /strip/{layer}/{0-5}.png` → 6 × BitmapLayer

### Active Surface Layers

| Layer | Source | Auth | Domain | Resolution | Cadence | Colormap | vmin/vmax | Sigma | Cache | Status |
|-------|--------|------|--------|-----------|---------|----------|-----------|-------|-------|--------|
| SST | NOAA OISST v2.1 (CoastWatch ERDDAP) | None | Global ocean | 0.25° native, stride=4 → 1° | Daily (1-day lag) | RdYlBu_r | -2 / 32 °C | 2.0 | 6h | **Live** |
| PM2.5 | Open-Meteo AQ (CAMS Global) | None | Global | 0.4° native, 5° query grid | Hourly | RdYlGn_r | 0 / 75 µg/m³ | 15.0 | 6h | **Live** (rate-limit dependent) |
| Temperature | Open-Meteo Weather (GFS) | None | Global | 0.25° native, 5° query grid | Hourly | RdYlBu_r | -40 / 50 °C | 15.0 | 6h | **Live** (rate-limit dependent) |
| Precipitation | Open-Meteo Weather (GFS) | None | Global | 0.25° native, 5° query grid | Hourly | Blues | 0 / 20 mm | 15.0 | 6h | **Live** (rate-limit dependent) |
| NO₂ | Open-Meteo AQ (CAMS Global) | None | Global | 0.4° native, 5° query grid | Hourly | YlOrRd | 0 / 80 µg/m³ | 15.0 | 6h | **Live** (rate-limit dependent) |

### Planned Surface Layers (Future)

| Layer | Source | Auth | Notes |
|-------|--------|------|-------|
| Wind Speed | Open-Meteo Weather (GFS wind_speed_10m) | None | Same connector as Temperature |
| Soil Moisture | Open-Meteo Weather (soil_moisture_0_to_7cm) | None | Same connector |
| Ozone | Open-Meteo AQ (ozone) | None | Same connector as PM2.5 |
| Sea Level Anomaly | CMEMS (Copernicus Marine) | CMEMS account | Needs `copernicusmarine` package |
| AOD | Open-Meteo AQ (aerosol_optical_depth) | None | Replaces GIBS AOD |

---

## Event Layers (Point Data)

| Layer | Source | Auth | Endpoint | Format | Cadence | Status |
|-------|--------|------|----------|--------|---------|--------|
| Wildfires | NASA FIRMS | FIRMS_MAP_KEY | `/api/earth-now/fires` | JSON (top 5000 by FRP) | NRT ~3h | **Live** |
| Earthquakes | USGS FDSNWS | None | `/api/hazards/earthquakes` | JSON (M4+, 7 days) | NRT ~5 min | **Live** |

---

## GIBS Layers (Pass-through Tiles)

| Layer | GIBS Product | Cadence | Status |
|-------|-------------|---------|--------|
| CO₂ Column | OCO2_CO2_Column_Daily | Daily (3-5% coverage) | **Live** (sparse) |

---

## Removed / Deprecated Layers

| Layer | Reason | Replacement |
|-------|--------|-------------|
| Storms (IBTrACS) | Empty when no active cyclones → confusing UI | None (seasonal) |
| Floods (GIBS MODIS) | GIBS tiles unreliable, 3-day lag | None |
| Ocean Crisis (derived stress) | Redundant with SST surface | SST layer |
| PM2.5 MERRA-2 (GIBS) | 3-month stale, monthly | PM2.5 self-rendered (hourly) |
| AOD MODIS (GIBS) | Daily but GIBS-dependent | PM2.5 replaces use case |

---

## Backend Architecture

### Connectors

| File | Source | Type | Points/Call |
|------|--------|------|-------------|
| `oisst.py` | NOAA ERDDAP CSV | Gridded (0.25°) | ~43K at stride=4 |
| `open_meteo_aq.py` | Open-Meteo AQ REST JSON | Point-enumerated (5° grid) | ~2,664 via 3 POST batches |
| `open_meteo_weather.py` | Open-Meteo Weather REST JSON | Point-enumerated (5° grid) | ~2,664 via 3 POST batches |
| `firms.py` | NASA FIRMS CSV | Event points | ~5,000 (top FRP) |
| `ibtracs.py` | NOAA IBTrACS CSV | Event tracks | Variable |

### Rendering

| File | Function | Purpose |
|------|----------|---------|
| `surface_renderer.py` | `render_density_png()` | KDE for scattered data (fires) |
| `surface_renderer.py` | `render_gridded_surface_png()` | NaN-aware weighted smoothing for gridded data |
| `surface_cache.py` | `get()` / `put()` | File-system PNG cache with TTL |

### API Router

| Endpoint | Returns | Cache |
|----------|---------|-------|
| `GET /api/globe/surface/sst.png` | Full equirectangular PNG | 6h |
| `GET /api/globe/surface/pm25.png` | Full equirectangular PNG | 6h |
| `GET /api/globe/surface/temperature.png` | Full equirectangular PNG | 6h |
| `GET /api/globe/surface/precipitation.png` | Full equirectangular PNG | 6h |
| `GET /api/globe/surface/no2.png` | Full equirectangular PNG | 6h |
| `GET /api/globe/surface/strip/{layer}/{0-5}.png` | 30° latitude strip PNG | 6h |
| `GET /api/globe/surface/tile/{layer}?bbox` | Arbitrary crop (legacy) | 1h |

---

## Render Free Tier Constraints (512 MB RAM)

| Layer | Fetch Size | Peak Memory | Render Time |
|-------|-----------|-------------|-------------|
| SST (stride=4) | ~5 MB CSV | ~225 MB | ~2.5s |
| PM2.5 (5° grid) | ~0.5 MB JSON | ~216 MB | ~2s |
| Temperature | ~0.5 MB JSON | ~216 MB | ~2s |
| Precipitation | ~0.5 MB JSON | ~216 MB | ~2s |
| NO₂ | ~0.5 MB JSON | ~216 MB | ~2s |

All layers fit within 512 MB individually. **Never render two layers simultaneously** — sequential requests only.

---

## Open-Meteo Rate Limits

| Tier | Limit | Current Strategy |
|------|-------|-----------------|
| Free (non-commercial) | 10,000 calls/day, 5,000/hour | 3 calls per layer × 5 layers = 15 calls per refresh |
| Refresh cycle | 6-hour cache | ≤ 60 calls/day total |
| Retry | 3 attempts, backoff 5/10/20s | Graceful 502 on exhaustion |
| Batch delay | 4s between POST batches | Stays under per-minute limit |

---

## Frontend Architecture

| Category | Type | Layer Key | Data | Legend |
|----------|------|-----------|------|--------|
| Air Quality | Surface | `pm25-surface` | 6 strip BitmapLayers | AQI gradient (green→red→maroon) |
| Temperature | Surface | `temp-surface` | 6 strip BitmapLayers | Blue→red (-40 to 50°C) |
| Ocean Temp | Surface | `sst-surface` | 6 strip BitmapLayers | Blue→red (-2 to 32°C) |
| Precipitation | Surface | `precip-surface` | 6 strip BitmapLayers | Blues (0 to 20mm) |
| NO₂ Pollution | Surface | `no2-surface` | 6 strip BitmapLayers | Yellow→red (0 to 80 µg/m³) |
| Wildfires | Event | `fires` | ScatterplotLayer + density PNG | FRP gradient |
| Earthquakes | Event | `earthquakes` | ScatterplotLayer (glow + core) | Magnitude circles |
| CO₂ & GHG | GIBS | `gibs-oco2` | TileLayer (WMS) | OCO-2 column |
