# v2 QA / E2E / Regression — Step 10

**Date:** 2026-04-18
**Executor:** Claude (Opus, single-agent, `superpowers:executing-plans` + `ecc:e2e`)
**Scope:** v2 MVP critical paths (build matrix · worker endpoints · static-site invariants · broken links · status vocabulary).
**Verdict:** **SHIP-WITH-CAVEATS** — 0 P0, 1 P1 (broken footer guide links), 3 P2 (pre-existing / deferred).

---

## 1. Environment

| Item | Value |
|---|---|
| Shell | Git Bash (Windows 10 Pro 10.0.19045) |
| Node | v24.14.0 |
| pnpm | 9.6.0 |
| Python | 3.12.10 |
| Git SHA | `292035e711e2fa52015b71c5a52d59361cc9eb96` (working tree has uncommitted Step 6–9 work) |
| Wrangler | 3.114.17 (miniflare local) |
| Astro | 4.16.x |
| Cesium | 1.140 |

---

## 2. Build matrix

### 2.1 Web — `pnpm --filter web build`, `PUBLIC_SITE_URL` **unset**

- Pages: **16 built**, green in 14.42 s
  (/, /globe, /reports, /reports/{3 CBSAs}, /rankings, /rankings/{4 metrics}, /guides, /guides/{4 stubs})
- `[astro.config]` emits the documented warning: "PUBLIC_SITE_URL is not set — sitemap.xml will NOT be emitted and canonical links will be absent."
- `[@astrojs/sitemap] The Sitemap integration requires the 'site' astro.config option. Skipping.`
- `dist/sitemap-0.xml` **absent** ✓ (spec-correct)
- `dist/sitemap-index.xml` **absent** ✓
- `dist/robots.txt` **present** (779 B) ✓; contains no `Sitemap:` line ✓ (Step 8 note: CI deploy hook prepends it when env var is set).
- Home canonical absent ✓ (Rule 7).

### 2.2 Web — `PUBLIC_SITE_URL=https://terrasight.test pnpm build`

- Pages: **16 built**, green in 14.39 s (identical route set).
- `dist/sitemap-index.xml` present (single entry → `sitemap-0.xml`).
- `dist/sitemap-0.xml` contains **11 `<loc>` entries**:
  - `/`, `/globe/`, `/rankings/`, 4× `/rankings/{metric}/`, `/reports/`, 3× `/reports/{cbsa}/`
  - 0 `/guides/*` entries ✓ (per `filter: !\/guides\//` in `astro.config.mjs`)
- Report pages: `<link rel="canonical" href="https://terrasight.test/reports/{cbsa}">` emits ✓
- Rankings pages: canonical also emits per-metric ✓
- **Finding 2.2.a (P2) — Home page canonical not emitted.** `apps/web/src/pages/index.astro` calls `<Layout title=... description=... />` but never passes the `seo` prop, so `BaseLayout.astro` falls back to the "historical minimal OG + summary twitter" path and never emits `<link rel="canonical">`. This is inconsistent with `/reports/*` and `/rankings/*` which pass `seo`. Low-severity because the sitemap still lists the home URL, but home canonical is desirable for SEO. See §4.B2.

### 2.3 Web — `pnpm --filter web lint` (tsc --noEmit)

- Exit code **0**. Clean. No TypeScript errors.

### 2.4 Home zero-JS regression

```
grep -c '_astro/.*\.js' dist/index.html  →  0
```
✓ Rule 9 preserved; home emits pure HTML + one CSS link.

### 2.5 Home bundle size regression

| Asset (env-set build) | Raw | Gzipped |
|---|---|---|
| `dist/index.html` | 21,915 B | 4,816 B |
| `dist/_astro/index.*.css` (measured) | 13,385 B | 2,250 B |
| **Total** | **35,300 B** | **7,066 B** |

Budget: < 200 KB gzipped. Measured: **3.5 % of budget**. ✓ No regression vs `frontend-routing.md` §3 baseline (6.858 KB — drift is one CSS chunk-hash churn, not new code).

### 2.6 Guide stub `noindex` coverage

```
for f in dist/guides/*/index.html; do grep -l 'noindex' "$f"; done
```
| Stub | `<meta name="robots" content="noindex, nofollow">` |
|---|---|
| `what-is-a-trust-tag` | ✓ |
| `how-to-read-a-report` | ✓ |
| `why-compliance-is-not-exposure` | ✓ |
| `finding-local-environmental-data` | ✓ |

4/4 stubs noindex ✓.

### 2.7 Per-report structure scan

Sample file: `dist/reports/new-york-newark-jersey-city/index.html` (representative; all 3 CBSAs are symmetric per the composer).

| Artefact | Expected | Found |
|---|---|---|
| `id="block-air_quality"` … `id="block-methodology"` anchors | 8 | 8 ✓ |
| `data-ad-slot="report-hero"` | 1 | 1 ✓ |
| `data-ad-slot="report-mid"` | 1 | 1 ✓ |
| `data-ad-slot="report-footer"` | 1 | 1 ✓ |
| `city-comparison-external` element | 1 | 1 ✓ |
| `related-cities` sidebar | 1 | 1 ✓ |
| `rankings-snippet` sidebar (4 metric rows visible) | 1 | 1 ✓ |
| `<script type="application/ld+json">` with `"@type":"Article"` | ≥ 1 | 1 ✓ |
| `<script type="application/ld+json">` with `"@type":"BreadcrumbList"` | ≥ 1 | 1 ✓ |

(Note: raw `grep -c` counts **lines**; since Astro minifies to a single line, `grep -c 'data-ad-slot='` = 2, while `grep -oE` count = 3. Used `-oE` for truth.)

### 2.8 Per-rankings structure scan

All 4 slugs (`air-quality-pm25` · `emissions-ghg-total` · `water-violations-count` · `disaster-declarations-10y`):

| Artefact | Found |
|---|---|
| Ranked table OR "all pending" fallback | ✓ (current fixtures: all 3 rows null → "No metros have ranked values yet — every row is pending data") |
| `ranking-pending-list` with 3 pending metros | ✓ |
| `data-ad-slot="rankings-footer"` | ✓ |
| `"@type":"BreadcrumbList"` JSON-LD | ✓ |
| Methodology section (source + definition + cadence) | ✓ |
| `Compliance ≠ exposure` disclaimer on GHG + water only | ✓ |

### 2.9 Guide stub `/reports` + `/guides` back-links

All 4 stubs contain `href="/reports"` and `href="/guides"` ✓.

### 2.10 Broken-link scan (internal hrefs)

Extracted 32 unique internal targets from `dist/**/*.html`. 12 targets resolve to a missing `dist/<target>[/index.html]`:

| Target | Referenced from | Severity | Classification |
|---|---|---|---|
| `/atlas` | `BaseLayout.astro` site nav (10+ HTML pages) | **P2** | Expected — Atlas is Step 11 (`progress.md` Next Actions #3). Nav shipped ahead of target. |
| `/guides/methodology` | `SiteFooter.astro` L47 | **P1** | **BUG** — wrong slug. Actual page is `/guides/how-to-read-a-report`. |
| `/guides/trust-legend` | `SiteFooter.astro` L48 + L70 | **P1** | **BUG** — wrong slug. Actual page is `/guides/what-is-a-trust-tag`. |
| `/reports/atlanta-sandy-springs-alpharetta-ga` | NY report `peer_slugs` (`data/reports/new-york-newark-jersey-city.json`) | **P2** | Pipeline output — 3 samples built, 50 CBSAs planned. Peer sidebar lists slugs that won't exist until pipeline produces the full metro set. |
| `/reports/dallas-fort-worth-arlington` | NY + Houston `peer_slugs` | **P2** | Same pipeline-coverage story |
| `/reports/philadelphia-camden-wilmington` | NY `peer_slugs` | **P2** | " |
| `/reports/riverside-san-bernardino-ontario-ca` | LA `peer_slugs` | **P2** | " |
| `/reports/sacramento-roseville-folsom-ca` | LA `peer_slugs` | **P2** | " |
| `/reports/san-antonio-new-braunfels` | Houston `peer_slugs` | **P2** | " |
| `/reports/san-diego-chula-vista-carlsbad` | LA `peer_slugs` | **P2** | " |
| `/reports/san-francisco-oakland-berkeley-ca` | LA `peer_slugs` | **P2** | " |
| `/reports/san-jose-sunnyvale-santa-clara` | LA `peer_slugs` | **P2** | " |

**See §4 Bug list for remediation proposals.**

---

## 3. Worker (local dev)

### 3.1 Dev server boot

`pnpm --filter worker dev` → wrangler 3.114.17 → miniflare — boots clean on `http://127.0.0.1:8787` with bindings `CACHE_TTL_FIRES=600`, `CACHE_TTL_EARTHQUAKES=300`, `CACHE_TTL_SST_POINT=3600`. FIRMS_MAP_KEY intentionally unset to exercise Rule 5 degrade path.

Console warnings (non-fatal):
- wrangler.jsonc compatibility_date `2026-04-17` unsupported by installed runtime; falls back to `2025-07-18`. **Not a bug** — Step 3 pinned the compat date forward of the runtime revision, per Cloudflare recommended pattern.
- "Update available: wrangler@4.83.0" — cosmetic.

### 3.2 Endpoint probes

| Endpoint | HTTP | `status` | Body shape (excerpt) |
|---|---|---|---|
| `GET /health` | 200 | `ok` | `{"status":"ok","service":"terrasight-worker"}` |
| `GET /api/fires` (MAP_KEY unset) | 200 | `not_configured` | `{"status":"not_configured","source":"NASA FIRMS","source_url":"https://firms.modaps.eosdis.nasa.gov/api/area/","cadence":"NRT ~3h","tag":"near-real-time","count":0,"data":[],"notes":[],"message":"FIRMS_MAP_KEY not set"}` |
| `GET /api/earthquakes` | 200 | `ok` | `{"status":"ok","source":"USGS Earthquake","source_url":"...all_day.geojson","cadence":"5 min","tag":"observed","count":261,"data":[{"id":"aka2026hocqpy","type":"earthquake","lat":58.239,"lon":-155.061,"observedAt":"2026-04-17T19:56:48.959Z","severity":0.6,"label":"M0.6 — 82 km NNW of Karluk, Alaska","properties":{"depth_km":5,"url":"...","tsunami":0,"felt":null,"sig":6,"status":"automatic","severity_class":"micro","event_type":"earthquake"}}, …]}` |
| `GET /api/sst-point?lat=30&lon=-80` | 200 | `ok` | `{"status":"ok","source":"NOAA OISST v2.1","source_url":"https://coastwatch.pfeg.noaa.gov/erddap/griddap/ncdcOisst21NrtAgg","cadence":"daily","tag":"observed","lat":30,"lon":-80,"snappedLat":30.125,"snappedLon":-79.875,"sst_c":26.24,"observed_at":"2026-04-16T12:00:00Z","message":null}` |

All 4 endpoints respond with status values from the allowed enum (`ok` / `not_configured` / `pending` / `error`, plus the documented SST-only `no_data` narrowing). No 5xx, no blank bodies, no partial-failure UI hazards.

**Counter-check:** 26.24 °C in the Atlantic off northern Florida (30°N, 80°W) in mid-April is physically plausible (climatology +1–3 °C warm anomaly). Not a unit error.

---

## 4. Bug list (with remediation proposals)

### P1 — Broken guide links in `SiteFooter.astro`

**File:** `apps/web/src/components/SiteFooter.astro`
**Lines:** 47 (`/guides/methodology`), 48 and 70 (`/guides/trust-legend`).
**Reproduction:**
1. `PUBLIC_SITE_URL=https://terrasight.test pnpm --filter web build`
2. Open any `dist/guides/*/index.html` or `dist/reports/*/index.html` in a browser.
3. Scroll to footer → click "Methodology" or "Trust tag legend".
4. Dev preview / production deploy returns 404.

**Probable cause:** The footer links were authored against the Step 8 IA proposal (`/guides/methodology` + `/guides/trust-legend` as navigation hubs) but the actual stubs shipped in Step 8 were named differently: `how-to-read-a-report` + `what-is-a-trust-tag`. Nobody grep'd the footer against the actual emitted routes.

**Severity:** P1 (404 in production is visible; fix is one-line).

**Proposed fix (one-line each, safe to apply now):**
```
-  <a href="/guides/methodology">Methodology</a>
+  <a href="/guides/how-to-read-a-report">Methodology</a>

-  <a href="/guides/trust-legend">Trust tag legend</a>
+  <a href="/guides/what-is-a-trust-tag">Trust tag legend</a>

-  <a href="/guides/trust-legend" class="site-footer__legend-link">
+  <a href="/guides/what-is-a-trust-tag" class="site-footer__legend-link">
```
*Applied below in §6 (one-liner regression fix per Step 10 rule). See landmine entry in `docs/guardrails.md`.*

### P2 — Home page canonical not emitted

**File:** `apps/web/src/pages/index.astro`
**Line:** 42 (`<Layout title=... description=...>`).

Pass a `seo` prop:
```astro
<Layout
  title="TerraSight — Environmental Observatory"
  description="..."
  seo={{
    title: "TerraSight — Environmental Observatory",
    description: "...",
    path: "/",
  }}
>
```
This routes through `buildPageMeta()` which emits `<link rel="canonical">` only when `PUBLIC_SITE_URL` is set. Non-blocking; defer to the Step 9+ OG image follow-up so both are shipped together.

### P2 — Site nav `/atlas` link is a dead route

**File:** `apps/web/src/layouts/BaseLayout.astro`
**Line:** 154 (`<a href="/atlas">Atlas</a>`).

Atlas (Tier 2) is Step 11 per `progress.md` Next Actions. Two sensible fixes:

- **(preferred)** Gate the nav item behind a `if (import.meta.env.PUBLIC_ATLAS_READY)` build-time flag, default false. Flip when `/atlas/*` ships.
- Or remove the nav item for now and re-add in Step 11.

Non-blocking; users would land on a 404 today. Defer.

### P2 — Peer-metro links 404 for 8 of 11 peer slugs

**File:** pipeline — `data/reports/*.json` peer lists.
**Source of truth:** Step 5 composer at `pipelines/jobs/build_reports.py` resolves peer slugs from `data/cbsa_mapping.json` (50 CBSAs) regardless of which subset has a built report.

Two clean options:
- **(data-side)** At render time, filter `peer_slugs` against `reports-index.json` to drop slugs that don't have a built report yet. One-line change in `RelatedCities.astro`.
- **(pipeline-side)** In `build_reports.py`, post-filter `peer_slugs` to only include slugs the same run is producing. Safer but changes pipeline contract.

Non-blocking; affects sidebar UX only (dead links in the 3 sample reports). Defer to Step 11 alongside the full 50-CBSA expansion (at which point every peer link resolves anyway).

### Clean — status vocabulary drift (none found)

Grep of `apps/worker/src/**/*.ts` + `pipelines/transforms/*.py` for `status:` literals → only values found are:

- `ok` · `error` · `not_configured` · `pending` — BlockStatus enum (schema-frozen)
- `no_data` — SST-only, documented in `packages/schemas/src/index.ts` as `SSTStatus` narrowing + `docs/datasets/normalized-contracts.md`

No drift. ✓

### Clean — API path naming (none found)

Grep of `apps/web/src/**/*.{ts,tsx,astro}` for `/api/…`:

| Caller | Path |
|---|---|
| `apps/web/src/islands/GlobeApp.tsx` L402 | `/api/sst-point?lat=…&lon=…` |
| `apps/web/src/lib/layers.ts` L207 | `/api/fires` |
| `apps/web/src/lib/layers.ts` L218 | `/api/earthquakes` |

Worker mounts the exact same 3 routes in `apps/worker/src/index.ts` (L17–L19). No mismatch. ✓

---

## 5. Lighthouse (soft gate)

**Not run.** No Chrome or headless Chromium available on the QA host (`C:\Program Files\Google\Chrome\Application\chrome.exe` absent; `lighthouse` CLI not globally installed). Manual command for a future run:

```bash
# From apps/web, after `pnpm --filter web preview`:
npx lighthouse http://localhost:4321 \
  --only-categories=performance,accessibility,best-practices,seo \
  --output=json --output-path=./lighthouse-home.json
```

Expected: Perf ≥ 90 (home is pure HTML + 2.25 KB CSS, no JS), SEO ≥ 95 (all blocks have titles/descriptions; canonical only emits in env-set build — §4.B2 flags home canonical gap).

**Recommendation:** defer to deploy-readiness Step (per `progress.md` Next Actions #4), when the real deployed URL is also available for Field CWV vs Lab CWV comparison.

---

## 6. Actions taken in this QA pass

1. **Fixed P1 footer links** (`apps/web/src/components/SiteFooter.astro`, 3 href swaps). One-line regression fixes per Step 10 rule. Re-built; broken-link scan after fix drops to 9 targets (all now P2: `/atlas` nav + 8 peer-slug reports).
2. **Added 2 landmines to `docs/guardrails.md`** — "Step 10 / frontend landmines" subsection: (a) footer link / guide-slug drift, (b) peer_slugs-without-filter render.
3. **Appended Step 10 block to `progress.md`** per §7.1.
4. `CLAUDE.md` — **not touched**. No new architectural rule emerged that was not already documented.

---

## 7. Ship-readiness verdict

**Decision: SHIP-WITH-CAVEATS**

- **0 P0 blockers** (Step 9's `_redirects` P0 stayed fixed; no new blockers surfaced).
- **1 P1 fixed in this commit** (footer guide links). After fix the build is internally coherent — every remaining broken-link entry is either:
  - a deferred-but-documented route (`/atlas` = Step 11), or
  - a pipeline coverage gap (peer cities beyond the Step 5 sample 3).
- **3 P2 deferred**, each with a clear owner and follow-up step number:
  - Home canonical not emitted → fold into Step 9+ OG image follow-up.
  - Site nav `/atlas` → Step 11 Atlas Lite.
  - Peer-slug dead links → render-side filter in Step 11 (when full 50-CBSA expansion lands).
- **All v2 Non-Negotiable Rules (1–10) remain satisfied** as of the env-set build:
  - Rule 1 (no Render runtime): `_redirects` stays the commented-out v2 stub ✓
  - Rule 2 (no Open-Meteo): 0 matches in `apps/`, `packages/`, `pipelines/` ✓
  - Rule 3 (reports static): `getStaticPaths` in both `[...slug].astro` and `[metric].astro` ✓
  - Rule 4 (GIBS-first): `apps/web/src/lib/layers.ts` 5 imagery defs + 2 Worker events only ✓
  - Rule 5 (trust tags): 42 `trustTag` across 3 reports × 14 blocks ✓
  - Rule 6 (graceful status): endpoint probes returned only enum values ✓
  - Rule 7 (layer composition): `GlobeApp.tsx` enforces groupwise exclusivity ✓
  - Rule 8 (disclaimers): ECHO / WQP / AirNow injected via `block.notes[]` ✓
  - Rule 9 (no scores): schema has no `score` field ✓
  - Rule 10 (Worker is proxy/cache): only 3 thin routes in `apps/worker/src/routes/` ✓
- **Pipeline tests**: 60 pass in 0.54 s.
- **tsc --noEmit**: exit 0.
- **Home bundle**: 7.07 KB gzipped (3.5 % of 200 KB budget).
- **Worker endpoints**: 4/4 live, correctly statused.

### 7.1 progress.md append (see `progress.md`)

### 7.2 Recommended next actions
- Step 9+ (consent gate + AdSense runtime wiring) per `docs/revenue/adsense-placement-policy.md` §7.
- Deploy-readiness dry-run on Cloudflare Pages preview; re-run Lighthouse against the real preview URL.
- Author 4 guide bodies (compliance → trust tag → how to read → navigation hub) to clear the noindex gate.
- Step 11 (Atlas Lite 8 categories) — unblocks the nav `/atlas` P2.

---

## Appendix — verification commands replay

```bash
# Clean build, env unset
cd apps/web && rm -rf dist && pnpm build                   # 16 pages, no sitemap
grep -c '_astro/.*\.js' dist/index.html                    # 0
wc -c dist/index.html                                      # 21_915
gzip -c dist/index.html | wc -c                            # 4_816
gzip -c dist/_astro/index.*.css | wc -c                    # 2_250

# Clean build, env set
rm -rf dist && PUBLIC_SITE_URL=https://terrasight.test pnpm build  # 16 pages + sitemap
grep -oE '<loc>[^<]+</loc>' dist/sitemap-0.xml | wc -l     # 11

# Tsc
pnpm lint                                                  # exit 0

# Guide stubs
for f in dist/guides/*/index.html; do grep -l 'noindex' "$f"; done   # 4/4

# Reports invariants
grep -oE 'data-ad-slot="[^"]*"' dist/reports/new-york-newark-jersey-city/index.html | sort | uniq
# report-hero, report-mid, report-footer

# Pipeline tests
cd ../../pipelines && python -m pytest tests/              # 60 passed in 0.54s

# Worker
cd ../apps/worker && pnpm dev &      # miniflare 127.0.0.1:8787
curl -sS http://127.0.0.1:8787/health
curl -sS http://127.0.0.1:8787/api/fires
curl -sS http://127.0.0.1:8787/api/earthquakes
curl -sS 'http://127.0.0.1:8787/api/sst-point?lat=30&lon=-80'

# Broken-link scan (internal hrefs)
(for f in $(find dist -name '*.html'); do
   grep -oE 'href="/[^"#]*"' "$f" | sed 's/href="//; s/"$//'
 done) | sort -u | while read t; do
   c=${t%/}; [ -z "$c" ] && continue
   if [ -f "dist${c}/index.html" ] || [ -f "dist${c}" ] || [ -f "dist${c}.html" ]; then continue; fi
   echo "MISSING: $t"
 done
```
