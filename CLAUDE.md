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
- **Earth Now globe (v2 MVP — 6 layers)** — base imagery (GIBS
  BlueMarble) + 4 GIBS imagery (SST, AOD, Clouds, Night Lights) +
  2 Worker-proxied events (FIRMS wildfires, USGS earthquakes).
  **Approved list and URLs:** `docs/datasets/gibs-approved-layers.md`.
  **Never use `VIIRS_SNPP_DayNightBand_ENCC`** (frozen 2023-07-07).
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

> **v1 (current) — migrating to v2.** v2 target stack is defined in
> `docs/architecture/architecture-v2.md`. Code paths below reflect v1
> until Step 3 (monorepo migration) runs.

- **Frontend (v1):** React + Vite + TypeScript. CesiumJS for the
  Earth Now globe.
- **Frontend (v2 target):** Astro + React island + TypeScript.
- **Backend (v1):** FastAPI (Python), connectors in `backend/connectors/`.
- **Backend (v2 target):** Cloudflare Workers (Hono) — proxy/cache only.
  Heavy work moves to GitHub Actions batch (`pipelines/`).
- **Storage (v2 target):** Cloudflare R2.
- **DB / cache (deferred):** PostgreSQL + Redis (scheduler TBD).

## Non-Negotiable Rules (v2)

Full spec: **`docs/architecture/architecture-v2.md`** ·
**`mvp-scope-v2.md`** · **`data-source-policy.md`**.

1. **No Render runtime rasterization.** No request-time numpy/scipy PNG.
2. **No Open-Meteo in production MVP.** Reference-only.
3. **Reports are statically generated.** Build-time `report.json` only.
4. **GIBS-first for global Globe layers.**
5. **Trust tags required** on every dataset / report block / map layer.
6. **Graceful status** — every block/endpoint returns `ok` / `error` /
   `not_configured` / `pending`.
7. **Layer composition:** 1 continuous + 1 event overlay at most.
8. **Mandatory disclaimers** (ECHO / WQP / AirNow) — non-removable.
9. **No composite environmental scores.** Transparent indicators only.
10. **Worker is proxy/cache only.** No raster rendering, no Report
    assembly at request time.

## Current Phase

**v2 Architecture Reset** — see `progress.md` for status and
`docs/terrasight-v2-step-prompts.md` for the step-by-step plan.

## 2026-04-17 Architecture Decisions
- Render backend will remain in maintenance mode temporarily, serving only /fires, /quakes, /sst-point, /health.
- Heavy raster rendering and Open-Meteo-dependent surface endpoints are frozen and scheduled for removal.
- Frontend migration strategy is Astro shell + React islands, not a full Astro rewrite of the interactive globe.
- Legacy policy is move-first, delete-after-parity.
- Root cleanup policy: delete *.bak and Screenshot* immediately; move compute_bbox*.py to legacy/scripts-experimental unless proven reusable in pipelines.

## 2026-04-18 Architecture Decisions (Step 6 — Home / Globe frontend)
- Home (`/`) is pure Astro SSG with **zero JS emitted** (TrustBadge rendered server-side). Measured 6.9 KB gzipped total — well under the 200 KB budget.
- Globe (`/globe`) is a React island loaded via `client:visible`; CesiumJS 1.140 enters only through dynamic `await import('cesium')` inside `useEffect` — never evaluated server-side, never shipped to `/`.
- `astro.config.mjs` uses `ssr.external: ['cesium']` (NOT `noExternal` — `noExternal` wipes `renderers.mjs` mid-SSG build).
- Cesium `any`-type shim at `apps/web/src/cesium-shim/index.d.ts` + tsconfig `paths` + ambient `declare module 'cesium'` in `apps/web/src/env.d.ts` — all three together sidestep the 50k-line `Cesium.d.ts` resolution OOM. Drop when Cesium ships a lighter type entry.
- **Lint uses `tsc --noEmit`, not `astro check`.** `@astrojs/check` (Volar) ignores tsconfig `paths` + ambient `declare module` when walking npm package types and OOMs on Cesium.d.ts even at 12 GB heap. `tsc` honors paths and exits clean at default 4 GB. Trade-off: `.astro` frontmatter scripts aren't type-checked by `tsc`, but Vite/Rollup catches real errors during `astro build`.
- Worker base URL for Globe event fetches resolves from `PUBLIC_WORKER_BASE_URL` env var (dev `http://localhost:8787`, prod `''` same-origin).
- Mobile fallback < 768px renders `packages/ui/GlobeMobileFallback` — no Cesium chunk fetched.
- Cesium widgets disabled (baseLayerPicker / geocoder / homeButton / animation / timeline / etc.) to sidestep missing `/Assets/` base URL. Copying Cesium static assets to `apps/web/public/cesium/` + setting `window.CESIUM_BASE_URL` is a pre-prod-deploy requirement (Step 7).
- BlueMarble UI label is "Natural Earth" (brand). AOD UI label is "Aerosol Proxy (AOD)" — never "PM2.5".
- `TrustBadge` remains the canonical component; `packages/ui/src/index.ts` exports `TrustBadge as TrustTag` alias instead of renaming.

## 2026-04-18 Architecture Decisions (Step 8 — SEO / monetization)
- **`apps/web/src/lib/seo.ts`** is the single source of truth for canonical/OG/Twitter tag construction. `BaseLayout.astro` accepts an optional `seo` prop and falls back to legacy tags when unset, so Step 6 pages keep working without migration. Full spec: `docs/architecture/seo-ia.md`.
- **Canonical link emits ONLY when `PUBLIC_SITE_URL` is set** at build time (`resolveSiteUrl()` in `lib/seo.ts` returns `null` when unset). Same gate controls `@astrojs/sitemap` emission (Astro's `site` option is populated from the env var; without it, sitemap integration warns + skips). Never hard-code a placeholder URL.
- **Guide stubs are `<meta name="robots" content="noindex, nofollow">`** until content bodies ship. Three-layer defense: per-page meta tag, sitemap filter excludes `/guides/*`, `public/robots.txt` has `Disallow:` lines. Unblocking a guide requires removing all three together.
- **`@astrojs/sitemap@^3.2.1`** (NOT `^3.7.x`) — newer releases assume Astro 5's `astro:routes:resolved` hook; on Astro 4.16 they crash with `_routes is undefined`. Downgraded 3.7.2 → 3.2.1 during Step 8. Revisit when Astro 5 migration happens.
- **Ad slot naming is frozen:** 3 on reports (`report-hero` / `report-mid` / `report-footer`) + 2 on rankings (`rankings-header` / `rankings-footer`). Union lives in `AdSlot.types.ts`. No runtime/lazy injection — Step 8 ships reserved boxes only (120 px `min-height` inline for CLS). AdSense JS + consent gate deferred to Step 9+. Spec: `docs/revenue/adsense-placement-policy.md`.
- **Astro `getStaticPaths` LANDMINE:** runs in an isolated scope and cannot access top-level frontmatter constants — the 4-slug map in `/rankings/[metric].astro` has to be redeclared inline inside `getStaticPaths`. If you hit `... is not defined` at the beginning of dynamic-route generation, this is almost certainly the cause.
- **Rankings URL ↔ file-slug translation** mirrors the authoritative `CityComparison.astro::SLUG_MAP`: `air-quality-pm25` ↔ `air_quality_pm25` etc. Keep both maps in sync; adding a 5th metric touches `CityComparison.astro` + `/rankings/index.astro` + `/rankings/[metric].astro`.
- **InternalLink component** (`src/components/InternalLink.astro`) wraps cross-section links with `data-link-type="internal"` + inferred `data-target-section`. Analytics-only; no JS loaded.

## 2026-04-18 Architecture Decisions (Step 7 — Reports frontend)
- `/reports/{slug}` is Astro SSG. `getStaticPaths` iterates `src/data/reports-index.json` (not a filesystem glob); each slug's JSON loads via typed `import.meta.glob<CityReport>(..., { eager: true, import: 'default' })`.
- **Data mirror (required):** `data/reports/*.json` and `data/rankings/*.json` (repo root) must be mirrored to `apps/web/src/data/*.json`. Astro/Vite does not reliably import JSON from outside `apps/web/`. Automation is a Step 8 follow-up; today copy manually whenever the pipeline regenerates.
- Block order: `coreBlocks` iterate in natural order with AdSlot injected **immediately after `air_quality`**, then embedded optionals (only `availability === 'included'`), then `CityComparison`, then `methodology` LAST. `partitionBlocks()` in `lib/reports.ts` is the single source of truth — pages never hardcode block ids.
- **Fragment trap:** Astro's `<>...</>` shorthand silently drops sibling children inside `.map()`. Use array-return `.map((b,i) => [<A/>, condition ? <B/> : null])` when injecting mid-loop elements. Documented in `docs/reports/report-page-ux.md` §3.
- **Canonical link (Rule 7):** `<link rel="canonical">` emits only when `PUBLIC_SITE_URL` is set. Dev/preview skip it — never hard-code a placeholder URL.
- **Optional-block gate (Rule 5):** core blocks always render (`NoData` shell if `status !== 'ok'`); embeddable optionals gated by `report.meta.optionalAvailability[id] === 'included'`. `city_comparison` is always `external` (external-link card). `related_cities` lives in sidebar, not main column.
- **Astro type-export workaround:** `.astro` files cannot export TypeScript types through a barrel. When a component needs a named type union (e.g., `AdSlotName`), put it in a sibling `*.types.ts` file and import from there. Example: `AdSlot.astro` + `AdSlot.types.ts`.
- **Sidebar shape drift:** Step 5 composer emits `data.peer_slugs: string[]` while the schema spec has `data.peers: Array<{slug,city,region,reason?}>`. `RelatedCities.astro` handles both shapes until Step 5 reconciles to one.
- **AdSlot is a reserved-box placeholder only.** Always renders `min-height` inline for CLS safety. Real AdSense wiring happens in Step 8.
- `<link rel="canonical">` + JSON-LD scripts inject via a named `<slot name="head" />` in `BaseLayout.astro`.
- 3 ad slots per report page: `report-hero` (above grid), `report-mid` (after air_quality block), `report-footer` (below grid). Slot name union frozen in `AdSlot.types.ts`.

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
6. **Always update `progress.md` when work finishes.** Record
   completed items, changed numbers, next actions, and blockers.
   This step is not optional — never skip it.
7. **No changes until you're 95% sure.** If you are not ~95%
   confident in the plan or the diagnosis, do not start editing.
   Ask clarifying questions until you reach that bar.

## When to read which doc

| If you're … | Read |
|---|---|
| Planning a v2 task | `docs/architecture/architecture-v2.md` · `mvp-scope-v2.md` · `data-source-policy.md` |
| Touching the Astro home or Globe island (route / bundle / Cesium config) | `docs/architecture/frontend-routing.md` |
| Adding a Globe imagery layer | `docs/datasets/gibs-approved-layers.md` (single source of truth) |
| Deciding runtime vs batch for a new source | `docs/datasets/runtime-vs-batch-sources.md` |
| Verifying a source's 7-axis profile | `docs/datasets/source-spike-matrix.md` |
| Adding a new data source or hitting an endpoint quirk | `docs/connectors.md` · `docs/guardrails.md` (landmines) |
| Touching the `/reports/{slug}` page (block order / ads / JSON-LD / canonical) | `docs/reports/report-page-ux.md` |
| Adding / moving an ad slot or changing a canonical / noindex policy | `docs/architecture/seo-ia.md` · `docs/revenue/adsense-placement-policy.md` |
| Touching a Local Reports block | `docs/reports/report-block-policy.md` · `docs/reports/report-schema.md` · `docs/report-spec.md` (v1 reference) |
| About to mark something "done" | `docs/guardrails.md` (verification checklist) |
| Catching up on what has been built | `progress.md` |
| Curious which endpoints were spike-verified and how | `docs/api-spike-results.md` (v1) · `docs/datasets/source-spike-matrix.md` (v2) |

**Do not paste the contents of these docs back into CLAUDE.md.** They
exist to keep this file small so it can always be in-context.
