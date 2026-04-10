# EarthPulse — Project Context (V5, slim)

> A visual-first environmental engineering portal for English-speaking
> audiences: live climate signals on the front, an environmental data
> atlas inside, and U.S. Local Environmental Reports for revenue.

## One-line identity

Climate visualization hooks the visitor → environmental data atlas
keeps them around → metro-level environmental reports drive AdSense
and SEO long-tail traffic.

- **Language:** English-first
- **Audience:** environmental engineering students / practitioners +
  climate-curious general public + U.S. regional environmental search
- **Positioning:** portal × observatory × atlas — not a catalog, not a
  pretty globe. A three-tier funnel: *make them see → make them dig →
  make them search*.
- **Revenue model:** AdSense (primary) + educational / tool upsells
  (secondary). The SEO long tail from Local Reports is the core
  traffic engine.

## Three-tier structure

### Tier 1 — Earth Now + Climate Trends (hook)

- **Climate Trends strip** — 3 cards: CO₂ (NOAA GML Mauna Loa),
  Global Temp Anomaly (NOAAGlobalTemp CDR), Arctic Sea Ice (NSIDC).
  Each card shows cadence · trust badge · source **above** the value.
- **Earth Now globe** — base imagery (NASA GIBS BlueMarble) +
  layers: Fires (FIRMS, default ON), Ocean Heat (OISST), Smoke
  (CAMS, disabled — ADS account needed), Air Monitors (OpenAQ).
  Layer composition rule: 1 continuous field + 1 event overlay at
  most.
- **Story Panel** (preset-driven editorial) + **Born-in Interactive**
  (P1 viral).

### Tier 2 — Environmental Data Atlas (depth)

Eight categories reflecting environmental engineering curricula:

1. Air & Atmosphere
2. Water Quality, Drinking Water & Wastewater
3. Hydrology & Floods
4. Coast & Ocean
5. Soil, Land & Site Condition
6. Waste & Materials
7. Emissions, Energy & Facilities
8. Climate, Hazards & Exposure

Every dataset must display trust tag, source, cadence, spatial scope,
license, and known limitations.

### Tier 3 — Local Environmental Reports (revenue engine)

- `/reports/{cbsa-slug}` — U.S. CBSA-level, 50-100 metros initially.
- 6 blocks: Metro Header → Air Quality → Climate Locally →
  Facilities → Water → Methodology → Related. Full spec in
  **`docs/report-spec.md`**.
- Mandatory disclaimers: ECHO ("compliance ≠ exposure"), WQP
  ("discrete samples — dates vary"), AirNow ("reporting area ≠
  CBSA").

## Tech stack

- **Frontend:** React + Vite + TypeScript. `react-globe.gl` for the
  Earth Now hero (chosen over Cesium for bundle size).
- **Backend:** FastAPI (Python), one connector class per data source
  in `backend/connectors/`.
- **Maps (Local Reports):** Mapbox or Leaflet (TBD)
- **DB / cache:** PostgreSQL + Redis (scheduler TBD)

## Differentiation (vs incumbents)

| Incumbent | Their strength | Our wedge |
|---|---|---|
| earth.nullschool | Beautiful atmospheric viz | No water / soil / facilities / compliance |
| NASA Worldview | 1,200+ layers | Expert tool — no education or local reports |
| Resource Watch | 300+ datasets, policy framing | Policy-maker audience, not eng-curriculum |
| Windy.com | Mass UX, weather | No environmental coverage |
| EPA / USGS / NOAA portals | Per-domain depth | Fully siloed — no cross-domain story |

Our three-way bet: environmental-engineering taxonomy × explicit
trust tagging × regulatory-to-observational crosslinks wrapped in a
hook → depth → revenue funnel.

---

## Operating rules (for Claude / anyone driving this repo)

1. **Do not re-read files already in conversation context.** If a
   file was just read, referenced, or edited, do not `Read` it
   again — assume the previous content is current unless a tool
   modified it in the meantime.
2. **Batch independent tool calls in parallel.** File reads, globs,
   and curl probes with no data dependency between them MUST go in
   a single message with multiple tool calls.
3. **Delegate wide work to sub-agents.** Any task that would load
   dozens of files or probe many endpoints (exploring a subsystem,
   implementing 2+ independent connectors, research sweeps) should
   be dispatched to an `Explore` or `general-purpose` agent with
   explicit scope — not done inline.
4. **Write down landmines as you find them.** Every URL quirk,
   schema rename, or parameter gotcha goes into the connector's
   docstring *and* `docs/guardrails.md`'s landmine table before the
   task is marked done.
5. **Graceful degradation is mandatory.** Connector failures /
   missing API keys / pending features must never 5xx or blank the
   UI. Every block / endpoint returns a structured `status` field
   (`ok` / `error` / `not_configured` / `pending`).

## When to read which doc

| If you're … | Read |
|---|---|
| Adding a new data source or hitting an endpoint quirk | `docs/connectors.md` |
| Touching a Local Reports block | `docs/report-spec.md` |
| About to mark something "done" | `docs/guardrails.md` (verification checklist) |
| Catching up on what has been built | `progress.md` |
| Curious which endpoints were spike-verified and how | `docs/api-spike-results.md` |

**Do not paste the contents of these docs back into CLAUDE.md.** They
exist to keep this file small so it can always be in-context.
