# TerraSight Frontend Routing (v2)

**Version:** v2.step6.0
**Last updated:** 2026-04-18
**Owner:** `apps/web/`

This document freezes the home↔Globe role split, bundle-size budget, mobile
fallback rules, and the Worker base URL contract for the v2 Astro frontend.

---

## 1. Route map

| Route | Rendering | Bundles shipped | Purpose |
|---|---|---|---|
| `/` (home) | **Astro SSG** — pure HTML | CSS only (no JS) | SEO landing: Hero + Climate Trends strip + Featured Reports + Link Cards + Footer. All values (trend numbers, report titles, CTAs) present in view-source. |
| `/globe` | Astro shell + **React island** | `client.js` (Astro runtime) + `GlobeApp.js` + lazy `Cesium.js` | CesiumJS 1.140 globe with 4 GIBS imagery layers + 2 Worker event layers (fires, earthquakes). Dynamic `await import('cesium')` inside `useEffect` so Cesium never evaluates server-side or on `/`. |
| `/reports/{cbsa-slug}` | Astro SSG (Step 7) | CSS only (planned) | U.S. metro environmental reports. Not in Step 6 scope — covered by pipeline output in `data/reports/*.json`. |
| `/atlas/*` | Astro SSG (Step 8) | CSS only (planned) | Environmental data atlas (8 categories). Not in Step 6 scope. |

### Route isolation rules

1. **Home must never reference Cesium.** `grep -c "cesium" dist/index.html` == `0`. Enforced by (a) no import of `GlobeApp` from `index.astro`, (b) `ssr.external: ['cesium']` in `astro.config.mjs` (see §4).
2. **Globe island is opt-in only.** Loaded via `<GlobeApp client:visible />` in `/globe.astro`. `client:visible` defers hydration until the island enters viewport.
3. **No `client:load` anywhere.** All interactive islands use `client:visible` or `client:idle` to keep Time-to-Interactive low.

---

## 2. Home ↔ Globe role split

### Home (`/`) — hook + funnel

**Purpose:** make the visitor see live climate signals + top metro reports in
the first paint, then send them to Globe (depth) or Reports (revenue) via
clear CTAs.

**Composition (in order):**
1. `HeroSection` — tagline, two CTAs ("Open the Globe" → `/globe`, "Find your metro" → `/reports`).
2. `ClimateTrendsStrip` — 3 cards (CO₂ / Temp anomaly / Arctic sea ice). Each card: Trust badge + source + cadence **above** the value. Values from `src/data/climate-trends.json` (build-time fixture, refreshed by pipeline in Step 7).
3. `FeaturedReports` — top 5 city reports from `src/data/reports-index.json`.
4. `LinkCards` — static links to Atlas / Methodology / Data sources.
5. `SiteFooter` — generatedAt timestamp, license, GitHub link.

**Constraints:**
- Zero `client:*` directives on home components.
- TrustBadge renders as static HTML (alias of existing `TrustBadge` as `TrustTag` in `packages/ui/src/index.ts`).
- No `<script>` tags referencing `_astro/*.js` in the emitted HTML.

### Globe (`/globe`) — depth

**Purpose:** expose all 6 MVP layers with toggles, legend, event popups, and
SST click values. This is the expert / curious-user funnel to Atlas + Reports.

**Island:** `apps/web/src/islands/GlobeApp.tsx` (~884 lines).

**Layers (6 MVP + 1 base):**

| ID | Kind | Source | Trust tag | Cadence | Notes |
|---|---|---|---|---|---|
| `BlueMarble_NextGeneration` | imagery (base, always on) | NASA GIBS | observed | monthly | "Natural Earth" UI label; not counted in 6 MVP layers |
| `GHRSST_L4_MUR_Sea_Surface_Temperature` | imagery (togglable) | NASA GIBS | observed | daily | Clickable ocean cells → `/api/sst-point` |
| `MODIS_Combined_Value_Added_AOD` | imagery (togglable) | NASA GIBS | observed | daily | UI label: "Aerosol Proxy (AOD)" — never "PM2.5" |
| `MODIS_Terra_Aerosol_Cloud_Fraction` | imagery (togglable) | NASA GIBS | observed | daily | Cloud fraction 0–1 |
| `VIIRS_SNPP_DayNightBand` | imagery (togglable) | NASA GIBS | observed | daily | **NEVER use `_ENCC`** (frozen 2023-07-07) |
| `fires` | event overlay (togglable) | FIRMS via Worker | near-real-time | 10 min | Red points, fixed 4 px |
| `earthquakes` | event overlay (togglable) | USGS via Worker | near-real-time | 5 min | Purple points, mag-scaled 3→6px / 7→14px |

**Layer composition rule (enforced at island level):**
- ≤ 1 continuous imagery layer active at a time (base + one overlay).
- ≤ 1 event layer active at a time.
- Controls live in top-right `LayerControls` panel; Legend (bottom-left) reflects current state.

**Widgets disabled** (sidesteps missing `/Assets/` base URL):
- `baseLayerPicker`, `geocoder`, `homeButton`, `sceneModePicker`, `navigationHelpButton`, `animation`, `timeline`, `fullscreenButton`, `infoBox`, `selectionIndicator`.

**Auth:** `Cesium.Ion.defaultAccessToken = ''` — we do not use Ion.

---

## 3. Bundle size budget & measurements

Measured from `pnpm --filter web build` output on 2026-04-18:

| Asset | Raw | Gzipped | Budget | Status |
|---|---|---|---|---|
| `dist/index.html` (home) | 18,864 B | 4,157 B | < 200 KB gzipped | ✅ |
| `dist/_astro/index.css` | 13,385 B | 2,701 B | — | — |
| **Home total (HTML + CSS)** | **32,249 B** | **6,858 B** | < 200 KB gzipped | ✅ 3.4% of budget |
| `dist/globe/index.html` | 11,005 B | — | — | — |
| `dist/_astro/GlobeApp.js` | 21,678 B | 7,500 B | — | — |
| `dist/_astro/globe.css` | 24,404 B | 5,516 B | — | — |
| `dist/_astro/client.js` (Astro hydration) | 135,601 B | ~44 KB | — | — |
| `dist/_astro/Cesium.js` | 5,559,029 B | 1,369,090 B | — | Loaded **lazy** on `/globe` only |

**Home renders with zero JS.** The emitted `index.html` references exactly
one asset: `_astro/index.CAiTjVyu.css`. No `<script>` tags. This is the
enforcement for "index route < 200 KB gzipped".

**Globe Cesium chunk is 1.37 MB gzipped.** Not blocking for Step 6 (expected
given CesiumJS full build). Optimization candidates (Step 7+): CDN hosting,
scene-module tree-shaking, custom Cesium build stripping unused primitives.

---

## 4. Build config: Cesium + SSR

### `apps/web/astro.config.mjs`

```js
vite: {
  ssr: {
    external: ['cesium'],  // NOT noExternal — critical
  },
},
```

**Why `external` and not `noExternal`:** Cesium 1.140 uses browser-only
globals (`window`, `document`) at module-eval time. `noExternal` bundles it
into the SSG worker and evaluates it during static generation, which wipes
`renderers.mjs` mid-build and fails. `external` keeps Cesium out of SSR
entirely; we load it at runtime via dynamic `import('cesium')` inside a
`useEffect`, which only fires post-hydration on the client.

### `apps/web/tsconfig.json`

```json
"paths": {
  "cesium": ["src/cesium-shim/index.d.ts"],
  "cesium/Build/Cesium/Widgets/widgets.css": ["src/cesium-shim/index.d.ts"]
}
```

Plus an ambient backstop in `apps/web/src/env.d.ts`:

```ts
declare module 'cesium' { const cesium: any; export = cesium; }
declare module 'cesium/Build/Cesium/Widgets/widgets.css' { const css: any; export default css; }
```

**Why the shim:** Cesium 1.140's `Source/Cesium.d.ts` is ~50,000 lines.
`skipLibCheck: true` skips type-checking of the file but does not skip
parsing/resolution when anything in the project imports `cesium`. The
shim remaps the module specifier to an `any` declaration; GlobeApp.tsx
accesses Cesium through a dynamic-import'd `any`-typed ref, so real
types are not needed for the project check.

Drop the shim + `declare module` when Cesium publishes a lighter type entry.

### Type-check uses `tsc --noEmit`, not `astro check`

`pnpm --filter web lint` runs `tsc --noEmit`.

**Why not `astro check`:** `@astrojs/check` uses Volar under the hood.
Volar performs a whole-project crawl that **ignores `tsconfig` `paths`
and ambient `declare module` overrides when following npm package types**,
so it walks Cesium's 50k-line `.d.ts` via the package's `types` field and
OOMs — measured failure at 12 GB heap (2026-04-18). Paths + ambient
declarations are honored by `tsc` directly, which exits clean at the
default 4 GB heap.

Trade-off: `.astro` frontmatter scripts are not type-checked by `tsc` (it
doesn't recognize `.astro` as a TS extension). They are validated at
build time by the Vite/Rollup pipeline in `astro build`, so real type
errors still fail the build. `tsc --noEmit` covers every `.ts` / `.tsx`
file (islands, UI, schemas), which is where logic lives.

Clearing condition: when Cesium ships a lighter `.d.ts` (tracked upstream),
switch back to `astro check` and delete the shim.

### Cesium static assets (deploy-time — not yet wired)

CesiumJS expects to fetch `/Assets/*`, `/Widgets/*`, `/Workers/*`,
`/ThirdParty/*` at runtime. Step 6 ships with these widgets disabled, so
the missing `/Assets/` base URL does not break the globe. **Before Step 7
production deploy:**

1. Copy `node_modules/cesium/Build/Cesium/*` → `apps/web/public/cesium/`.
2. Set `window.CESIUM_BASE_URL = '/cesium/'` before any `Viewer` construction.

---

## 5. Worker base URL contract

Globe event layers fetch from the Cloudflare Worker. Base URL resolves from
an env var at build time:

```ts
const WORKER_BASE = import.meta.env.PUBLIC_WORKER_BASE_URL ?? '';
fetch(`${WORKER_BASE}/api/fires`);
fetch(`${WORKER_BASE}/api/earthquakes`);
fetch(`${WORKER_BASE}/api/sst-point?lat=...&lon=...`);
```

| Environment | `PUBLIC_WORKER_BASE_URL` | Reason |
|---|---|---|
| Local dev | `http://localhost:8787` | Wrangler dev server on separate port |
| Preview / CI | worker preview URL (e.g. `https://preview-xxx.workers.dev`) | Set per-deploy in CI |
| Production | `''` (empty string) | Same-origin — Worker is mounted under the same hostname as Pages via Cloudflare routes |

**Documented in** `apps/web/.env.example`. The `PUBLIC_` prefix is required
by Astro/Vite for the value to reach client-side code.

**Graceful status (CLAUDE.md Rule 5):** if Worker fetch fails, GlobeApp must
not blank the UI. Event layers render a dimmed legend row with
`status="error"` and keep the imagery base rendering.

---

## 6. Mobile fallback

Viewport `< 768px` → render `GlobeMobileFallback` (from `packages/ui`)
instead of `GlobeApp`.

- SSR-safe: `useIsMobile()` reads `window.innerWidth` only inside
  `useEffect` (guarded against undefined `window`).
- Fallback panel has 3 CTAs: Home (`/`), Reports (`/reports`), Atlas (`/atlas`).
- No Cesium chunk is fetched on mobile — the dynamic `import('cesium')`
  lives inside the desktop-branch `useEffect` and is only reached when
  `isMobile === false`.

---

## 7. Acceptance criteria (Step 6) — verification

| Criterion | Verified how | Result |
|---|---|---|
| SEO-friendly home HTML (view-source shows all values) | `grep 424.5 dist/index.html` (CO₂ card); manual view-source check | ✅ |
| Zero Cesium on home | `grep -c cesium dist/index.html` == `0` | ✅ |
| Zero JS on home | `grep "_astro/.*\\.js" dist/index.html` == empty | ✅ |
| 6 MVP layers stable on `/globe` | Manifest cross-check vs `docs/datasets/gibs-approved-layers.md` — all 5 imagery IDs match; `_ENCC` banned; 2 event routes mounted on Worker | ✅ |
| Event popup + Legend | Present in `GlobeApp.tsx` (PopupCard + `Legend` from `packages/ui`) | ✅ |
| Index route < 200 KB gzipped | Measured 6,858 B (3.4% of budget) | ✅ |
| Mobile fallback works | `useIsMobile()` + `GlobeMobileFallback` wired in GlobeApp | ✅ |
| TrustTag 5-enum frozen | Existing `TrustBadge` aliased as `TrustTag` in `packages/ui/src/index.ts` | ✅ |

---

## 8. Known gaps / follow-ups (Step 7+)

1. **Duplicate data dir:** `apps/web/src/data/reports-index.json` is a hand-copy of `data/reports/index.json` (pipeline output). Astro/Vite does not reliably import across workspace roots. Step 7 must script this mirror as part of `pnpm build`.
2. **Cesium asset copy missing** (§4). Required before production deploy — currently masked by disabled widgets.
3. **Cesium 1.37 MB gzipped bundle** — candidate for CDN-host or custom build (Step 7 performance pass).
4. **`astro check` is blocked by Cesium's 50k-line `.d.ts`** — even 12 GB heap OOMs because Volar ignores `tsconfig paths` + ambient `declare module` when walking package types. Current lint uses `tsc --noEmit` (passes at default heap, honors paths). Restore `astro check` when Cesium upstream ships a lighter type entry.
5. **GIBS tile failure handling** — Rule 5 graceful status: Globe currently falls back to "Natural Earth" base if a toggled imagery layer 404s, but the Legend does not yet surface `status="error"` distinctly. Tracked for Step 7 polish.
