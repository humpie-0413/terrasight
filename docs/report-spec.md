# Local Environmental Reports — Block Specification

Spec for the 6-block Local Environmental Report, the revenue engine of
EarthPulse. URL pattern: `/reports/{cbsa-slug}`. Initial scope:
U.S.-first, 50-100 major metros.

## Defaults

- **Primary geographic unit:** Metro / CBSA
- **Climate block exception:** city (NOAA CtaG provides city time series)
- **Each block must show the unit it actually used** — CBSA bbox,
  reporting area, station, county, etc.

## Block 0 — Metro Header

- Official CBSA name
- Population (Census ACS) + year
- Climate zone (Köppen)
- Last-updated timestamp
- Four key-signal mini-cards:
  1. Current AQI (AirNow)
  2. Temperature anomaly (local, CtaG city series) — P1 placeholder
  3. EPA facilities count + violation count (ECHO)
  4. Streamflow sites reporting (USGS NRT)

## Block 1 — Air Quality

- **Current** → AirNow, reporting-area granularity, hourly, observed.
  Worst pollutant as headline (AQI + category + pollutant name).
- **Annual Trend** → EPA AirData / AQS, county or CBSA, annual,
  observed. PM2.5 and Ozone year series.
- **Context** → 2-3 sentence local interpretation. Manual or AI+review.
- ⚠️ Mandatory disclaimer: "AirNow reporting area ≠ CBSA boundary.
  Readings come from the monitor(s) closest to the sampled ZIP."

## Block 2 — Climate Change Locally

- NOAA CtaG city monthly time series (P1 pending — CtaG UI has no
  REST API; NOAAGlobalTemp city-level product integration deferred).
- U.S. Climate Normals 1991-2020 per-station baseline. 12 monthly
  rows (T-avg / T-max / T-min in °F, Precip in inches) + annual
  rollup.
- 30-year chart + precipitation chart + computed warming rate.
- Context: region-specific climate interpretation.

## Block 3 — Regulated Facilities & Compliance

- EPA ECHO (coords → CBSA bbox aggregation, live feed, regulatory).
- Summary cards: total facilities, currently in violation, formal
  actions (3 yr), penalties (3 yr, USD).
- Top facilities table ranked by current violation + enforcement
  activity.
- Facility map within the CBSA boundary.
- ⚠️ **Mandatory disclaimer**: "Regulatory compliance ≠ environmental
  exposure or health risk."

## Block 4 — Water Snapshot

- **Hydrology (NRT)** → USGS modernized OGC API, 15-min continuous.
  Label: "Near-real-time (15-minute interval)". Streamflow / stage.
- **Water Quality (discrete)** → WQP `/wqx3/` beta + USGS modernized
  discrete endpoints. Label: "Discrete samples — dates vary".
- ⚠️ Continuous vs discrete distinction **must be visible in the UI**.
- Backend constraint: never rely on WQP legacy `/data/` export —
  always hit `/wqx3/` beta + USGS modernized directly.

## Block 5 — Methodology & Data Limitations

- Geographic unit explainer (CBSA vs reporting area vs city vs
  station).
- Per-source table: cadence, trust tag, spatial scope, license.
- Known limitations bullets.
- Global disclaimer: "Educational / exploratory only. Not a
  substitute for an official environmental assessment."

## Block 6 — Related Content

- Rankings the metro appears in
- Educational guides
- Nearby metro reports (internal link graph for SEO + dwell time)

---

## AdSense placement rules

- Between Block 1-2, between Block 3-4, and inside / below Block 6.
- **Never inside a data block** — ads must be visually separated from
  tables and charts.
- Mobile: max 1 ad per block.
- Google policy: avoid scaled content abuse — people-first content.

## SEO content tracks (parallel to reports)

- **Fact rankings** — EPA violations (ECHO), PM2.5 (AirData / AQS),
  each with source + criteria exposed.
- **Educational guides** — "How to Read an AQI Report", "What Your
  Water Quality Samples Mean", etc.
- **Event explainers** — semi-automated triggers on wildfires,
  floods, pollution incidents.

---

## Block-level graceful degradation

Every block in the backend payload has a `status` field:

- `ok` — connector succeeded, `values` populated
- `error` — connector raised; `error` field carries the exception
- `not_configured` — API key missing; `message` carries registration
  instructions
- `pending` — known-incomplete feature (e.g. CtaG city series)

A single connector failure MUST NOT 5xx the whole report. The
frontend renders healthy blocks normally, degraded blocks as a small
notice, and pending blocks with a "coming soon" message — the layout
stays stable across all four states.
