# TerraSight — Live Data Snapshot

**Collected:** 2026-04-12 ~17:00 UTC
**Source:** Local API (FastAPI TestClient against latest `master` code)
**Purpose:** Document every piece of data visible on the live website

---

## 1. Climate Trends Strip (6 cards)

| Card | Latest Value | Date | Source | Cadence | Trust Tag |
|------|-------------|------|--------|---------|-----------|
| CO₂ | **429.35 ppm** | 2026-02 | NOAA GML Mauna Loa | monthly | observed |
| Global Temp Anomaly | **+0.64 °C** | 2026-03 | NOAAGlobalTemp v6.1 | monthly (preliminary) | near-real-time |
| Arctic Sea Ice | **13.878 M km²** | 2026-04-11 | NSIDC Sea Ice Index | daily (5-day mean) | observed |
| CH₄ (Methane) | **1,945.85 ppb** | 2025-11 | NOAA GML Global CH₄ | monthly | observed |
| Sea Level Rise | *(data unavailable)* | — | NOAA NESDIS GMSL | ~10-day | observed |
| US Drought | **94.3% area >= D1** | 2026-04-07 | US Drought Monitor | weekly (Thu) | observed |

### Drought Detail (CONUS, 2026-04-07)

| Category | % Area |
|----------|--------|
| No Drought | 20.92% |
| D0 Abnormally Dry | 79.08% |
| D1 Moderate | 60.05% |
| D2 Severe | 36.35% |
| D3 Extreme | 14.47% |
| D4 Exceptional | 2.02% |

---

## 2. Earth Now Globe Layers

### Fires (NASA FIRMS VIIRS)
- **24,569** hotspots detected globally in last 24h
- Top hotspot: lat=21.28, lon=102.53 (SE Asia), FRP=658.91 MW, brightness=367 K

### Sea Surface Temperature (NOAA OISST)
- **1,684** ocean grid points (5° spacing)
- Range: **-1.8 °C** to **+30.59 °C**, mean **14.5 °C**

### Air Monitors (OpenAQ v3 PM2.5)
- **1,000** stations (limit=1000, ~25,000 available globally)
- Sample: Monitor #2622686 (lat=35.22): PM2.5 = 12.0 µg/m³

### Tropical Storms (IBTrACS)
- **3** active storms:
  - INDUSA (South Indian) — wind 0 kt
  - MAILA (South Pacific) — SSHS Cat 3
  - VAIANU (South Pacific) — wind 0 kt

### Coral Bleaching (NOAA CRW)
- **8,996** grid points with DHW/BAA/SST data

### Earthquakes (USGS, last 7 days, M4+)
- **5** earthquakes returned (limit=5):
  1. **M5.2** — 187 km WSW of Sinabang, Indonesia, depth 10 km (2026-04-12 02:40 UTC)
  2. **M5.0** — Pagan region, Northern Mariana Islands, depth 226 km (2026-04-12 01:09 UTC)
  3. **M4.6** — 49 km ENE of Bhadarwah, India, depth 10 km (2026-04-11 22:52 UTC)
  4. **M4.3** — 31 km SW of Kastri, Greece, depth 10 km (2026-04-12 11:06 UTC)
  5. **M4.1** — 48 km WSW of San Antonio, Chile, depth 30 km (2026-04-12 09:12 UTC)

### Sea Level Anomaly (CMEMS)
- Status: **pending** (Copernicus Marine migration in progress)

---

## 3. NWS Active Weather Alerts

**177 active alerts** across the U.S. (2026-04-12)

| # | Severity | Event | Area | Sender |
|---|----------|-------|------|--------|
| 1 | Moderate | Special Weather Statement | Edwards; Kinney (TX) | NWS Austin/San Antonio TX |
| 2 | Moderate | Gale Warning | Kiska to Attu Pacific Side (AK) | NWS Anchorage AK |
| 3 | Moderate | Gale Warning | Bering Sea Offshore (AK) | NWS Anchorage AK |
| 4 | Minor | Small Craft Advisory | Castle Cape to Cape Tolstoi (AK) | NWS Anchorage AK |
| 5 | Moderate | Gale Warning | Bering Sea West of 180 | NWS Anchorage AK |

---

## 4. NOAA CO-OPS Tides (Houston-Galveston area)

**8 stations** in Houston CBSA bbox. Sample 3:

| Station | ID | Water Level (ft MLLW) | Water Temp (°F) | Last Reading |
|---------|----|-----------------------|-----------------|--------------|
| Morgans Point, Barbours Cut | 8770613 | 1.795 | 75.2 | 2026-04-12 11:36 UTC |
| Manchester | 8770777 | 2.005 | 75.2 | 2026-04-12 11:36 UTC |
| Rollover Pass | 8770971 | 1.775 | 74.7 | 2026-04-12 11:36 UTC |

---

## 5. OpenFEMA Disaster Declarations (Texas, last 3 years)

| Date | Type | Incident | Title | County |
|------|------|----------|-------|--------|
| 2026-03-15 | FM (Fire Mgmt) | Fire | CORNER POCKET FIRE | Donley |
| 2026-02-18 | FM (Fire Mgmt) | Fire | 8 BALL FIRE | Donley |
| 2026-02-18 | FM (Fire Mgmt) | Fire | 8 BALL FIRE | Armstrong |
| 2025-07-06 | DR (Major Disaster) | Flood | SEVERE STORMS, STRAIGHT-LINE WINDS, AND FLOODING | Hamilton |
| 2025-07-06 | DR (Major Disaster) | Flood | SEVERE STORMS, STRAIGHT-LINE WINDS, AND FLOODING | Concho |

---

## 6. Local Report — Houston-The Woodlands-Sugar Land

### Metro Header
- **CBSA Code:** 26420
- **Population:** 7,340,000 (2022)
- **Climate Zone:** Humid subtropical (Cfa)
- **Core County:** Harris County (FIPS 48201)
- **Key Signal Cards:** 6

### Block 1: Air Quality (AirNow)
- **AQI:** 52 (Moderate)
- **Primary Pollutant:** PM2.5
- **Reporting Area:** Houston-Galveston-Brazoria
- **Observed:** 2026-04-12 05:00 CST
- **Readings:** 3 pollutant readings

### Block 2: Climate Locally (NOAA Climate Normals)
- Status: **ok**
- Station: Houston Hobby AP (USW00012918)

### Block 13: Active Weather Alerts (NWS)
- **1 active alert** for Houston area
- Status: **ok**

### Block 3: Facilities (EPA ECHO)
- **Sampled Facilities:** 500
- **In Violation:** 17 (3.4%)
- **CAA Facilities:** 1,206
- **CWA Facilities:** 15,998
- **Top Violations:** 10 listed

### Block 7: Toxic Releases (TRI + RCRA)
- **TRI Facilities:** 100
- **Top Facilities:** 5 listed
- **RCRA Hazardous Waste Generators:** 50 handlers (integrated sub-section)

### Block 11: PFAS Monitoring
- **Monitored Systems:** 1
- **Unique Contaminants:** 30
- **Most Frequent:** PFHxS
- **Total Samples:** 100
- **Top Detections:** 10 listed

### Block 8: Site Cleanup
- **Superfund NPL Sites:** 23
- **Brownfields Sites:** 100

### Block 9: Facility GHG (GHGRP)
- **Facilities:** 100
- **Total CO₂e:** 4,157,781.4 tonnes (2023)
- **Top Facilities:** 5 listed

### Block 10: Drinking Water (SDWIS)
- **Water Systems:** 200
- **Total Violations:** 3,486
- **Systems with Violations:** 183
- **Violation Rate:** 91.5%
- **Population Affected:** 10,135

### Block 4: Water Snapshot (USGS + WQP)
- Status: **ok**

### Block 14: Coastal Conditions (CO-OPS)
- **Tide Stations:** 8 (Houston is a coastal metro)
- Status: **ok**

### Block 12: Hazards & Disasters
- **Federal Disasters (5 yr):** 50
- **Most Common Type:** Flood
- **Largest Quake (30d):** None in Houston bbox
- **Recent Disasters:** 10 listed
- **Recent Earthquakes:** 0 in bbox

### Block 5: Methodology
- Status: **ok**

### Block 6: Related
- Status: **pending** (not yet implemented)

---

## 7. SEO Rankings (6 pages, 50 metros each)

### EPA Facility Violations
| Rank | Metro | State | Sampled | In Violation | Rate |
|------|-------|-------|---------|-------------|------|
| 1 | Seattle-Tacoma-Bellevue | WA | 200 | 53 | 26.5% |
| 2 | Buffalo-Cheektowaga | NY | 300 | 24 | 8.0% |
| 3 | New Orleans-Metairie | LA | 100 | 24 | 24.0% |

### PM2.5 Levels (AirNow real-time)
| Rank | Metro | State | AQI | Category | Area |
|------|-------|-------|-----|----------|------|
| 1 | Birmingham-Hoover | AL | 91 | Moderate | Birmingham |
| 2 | Louisville/Jefferson County | KY | 83 | Moderate | Louisville |
| 3 | Kansas City | MO | 78 | Moderate | Kansas City |

### TRI Facility Count — 50 metros, sorted by state TRI facility count
### GHG Emissions (GHGRP) — 50 metros, sorted by state tCO₂e
### Superfund NPL Sites — 50 metros, sorted by site count in bbox
### Drinking Water Violations (SDWIS) — 50 metros, sorted by violation count

---

## 8. Born-in Interactive (year=1990 example)

| Indicator | Then (1990) | Now (latest) | Delta |
|-----------|------------|-------------|-------|
| CO₂ | 354.45 ppm | 429.35 ppm | +74.9 ppm (+21.1%) |
| Global Temp | -0.19 °C | +0.64 °C | +0.83 °C |
| Arctic Sea Ice | 6.14 M km² | 4.75 M km² | -1.39 M km² (-22.6%) |

---

## 9. Story Panel
- **Preset:** 2026 Wildfire Season
- **Body:** "NASA FIRMS is tracking active fire hotspots across western North America..."
- **Globe Hint:** Layer=FIRMS, Camera: lat=40, lng=-120, alt=1.6

---

## 10. Atlas Categories (8)

| # | Category | Live Datasets |
|---|----------|--------------|
| 1 | Air & Atmosphere | AirNow, AQS, OpenAQ, CAMS (planned) |
| 2 | Water Quality, Drinking Water & Wastewater | WQP, SDWIS, PFAS |
| 3 | Hydrology & Floods | USGS Water, USDM, NOAA RFC (planned) |
| 4 | Coast & Ocean | OISST, CO-OPS, NDBC (planned) |
| 5 | Soil, Land & Site Condition | Superfund, Brownfields, SoilGrids (planned), NLCD (planned) |
| 6 | Waste & Materials | TRI, RCRA |
| 7 | Emissions, Energy & Facilities | ECHO, Climate TRACE (planned), GHGRP, eGRID (planned) |
| 8 | Climate, Hazards & Exposure | FIRMS, NOAA GML, NOAAGlobalTemp, NSIDC, USGS Earthquake, NWS Alerts, OpenFEMA, FEMA NRI (planned) |

**Total live datasets:** 23

---

## 11. Direct API Endpoints (releases, sites)

### Releases (state=TX)
| Endpoint | Count | Status |
|----------|-------|--------|
| `/api/releases/tri` | 3+ | ok |
| `/api/releases/ghgrp` | 3+ | ok |
| `/api/releases/rcra` | 3+ | ok |

### Sites (Houston bbox)
| Endpoint | Count | Status |
|----------|-------|--------|
| `/api/sites/superfund` | 3+ | ok |
| `/api/sites/brownfields` | 3+ | ok |
| `/api/sites/pfas` | 3+ | ok |

---

## 12. System Health Summary

| Surface | Endpoints | Status |
|---------|-----------|--------|
| Trends | 6/6 indicators | 5 live, 1 unavailable (sea level intermittent) |
| Globe | 7 layer data sources | 6 live, 1 pending (CMEMS SLA) |
| Local Reports | 14 blocks | 13 ok, 1 pending (related) |
| Rankings | 6 pages × 50 metros | All ok |
| Hazards | 3 endpoints | All ok |
| Coast | 1 endpoint | ok (17 coastal metros) |
| Disasters | 1 endpoint | ok |
| Releases | 3 endpoints | All ok |
| Sites | 3 endpoints | All ok |
| Atlas | 8 categories, 23 live | All ok |
| Born-in | 3 indicators | All ok |
| Story | 1 preset | ok |

**Total API routes:** 43
**Total connectors:** 40 (34 active + 4 pending/disabled + 2 stubs)
**Bundle:** Main 62.96 KB + Globe vendor 519.83 KB (lazy) + 8 route chunks
