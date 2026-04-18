# v2 Reviewer Verification — Step 9

**Date:** 2026-04-18
**Reviewer:** Claude (Opus, single-agent, `verification-before-completion`)
**Scope:** Step 3 through Step 8 deliverables against `CLAUDE.md` Non-Negotiable Rules + `docs/architecture/architecture-v2.md` §9 + `docs/architecture/data-source-policy.md` + `docs/datasets/*`.
**Verdict:** PASS with one blocker (P0) + two P2 follow-ups. See §5.

---

## 1. Must / must-not checklist

### MUST (v2 invariants)

| # | Rule | Where verified |
|---|---|---|
| M1 | Every dataset / map layer / report block carries a `trustTag` | schemas `ReportBlock.trustTag`, `LayerManifest.trustTag`, `DatasetRegistryItem.trustTag`; fixtures verified (42 `trustTag` across 3 reports × 14 blocks) |
| M2 | Every block / endpoint exposes a structured `status` (`ok` / `error` / `not_configured` / `pending`) | `schemas.BlockStatus` z.enum; Worker routes + backend/main.py + all composer branches return `status` |
| M3 | Every report is statically generated at build time (`getStaticPaths`) | `apps/web/src/pages/reports/[...slug].astro`, `apps/web/src/pages/rankings/[metric].astro` |
| M4 | Mandatory disclaimers present (ECHO / WQP / AirNow) | rendered via `block.notes[]`; 21 files reference compliance-≠-exposure; composer-injected per block-id |
| M5 | Graceful degradation on every Worker + Render endpoint | FIRMS bad key → `not_configured`; USGS/OISST HTTP error → `status: 'error'`; OISST null cell → `no_data` |
| M6 | Canonical `<link rel="canonical">` only when `PUBLIC_SITE_URL` is set | `apps/web/src/lib/seo.ts::resolveSiteUrl()` returns `null` when unset; BaseLayout skips the tag; verified via dev build (no canonical) + `PUBLIC_SITE_URL=https://terrasight.example` build (11 sitemap URLs) |
| M7 | Guide stubs triple-noindex (meta + sitemap filter + robots Disallow) | all 4 stub HTMLs contain `noindex`; `sitemap-0.xml` contains zero `/guides/` entries; `robots.txt` has 4 `Disallow:` lines |
| M8 | 5 ad slots frozen (report-hero/mid/footer + rankings-header/footer) | `AdSlot.types.ts::AdSlotName` union exactly 5 strings; 3 slots per report page rendered in HTML |
| M9 | Home route ships zero JS | `grep -c "_astro/.*\.js" dist/index.html` → 0; no Cesium refs on `dist/index.html` |
| M10 | Layer composition rule (1 continuous + 1 event max) | `GlobeApp.tsx` LayerControls group / exclusivity — already verified in Step 6 acceptance |

### MUST-NOT (v2 prohibitions)

| # | Rule | Check result |
|---|---|---|
| N1 | No Render runtime dependency in v2 code paths (apps/, packages/, pipelines/) | ⚠ `apps/web/public/_redirects` still proxies `/api/* → terrasight-api-o959.onrender.com`. See §3.1 — **P0 blocker**. |
| N2 | No Open-Meteo in production MVP | `grep open-meteo \| open_meteo` returns only `docs/` references + quarantined `legacy/backend-connectors/open_meteo_*.py`. Zero matches in `apps/web`, `apps/worker`, `packages/`, `pipelines/`. |
| N3 | No request-time raster / PNG rendering | `grep renderSurface \| raster \| numpy` in `apps/` returns zero files. `backend/main.py` maintenance stub ships only 4 passthroughs — no raster endpoints. `legacy/backend-api/globe_surface.py` is quarantined. |
| N4 | No Cesium on `/` (home zero-JS budget) | Confirmed — 0 references in `dist/index.html`. |
| N5 | Never use `VIIRS_SNPP_DayNightBand_ENCC` | All 12 matches are warning comments / docs / tests; `apps/web/src/lib/layers.ts` line 172 explicitly warns against it and uses `VIIRS_SNPP_DayNightBand` (non-ENCC) |
| N6 | No composite environmental "score" | Verified — schema has no `score` field; fixtures carry per-metric rows only |
| N7 | No runtime DOM-injected / lazy / pop-in ad slots | `AdSlot.astro` renders static server-side with inline `min-height`; no `client:*` directive; 3 slots present in emitted HTML |

---

## 2. Variation-by-variation scan evidence

### 2.1 Trust-tag coverage (M1)

```
grep -r "trustTag" data/reports/ | wc  → 42  (3 reports × 14 blocks = 42 ✓)
packages/schemas/src/index.ts L3-10: TrustTag enum = {observed, near-real-time, forecast, derived, compliance}
packages/schemas/src/index.ts L138-156: ReportBlock.trustTag required (no .optional())
packages/schemas/src/index.ts L240-248: RankingRow.trustTag required
packages/schemas/src/index.ts L21-54: LayerManifest.trustTag required
```

### 2.2 Graceful status (M2 / M5)

```
packages/schemas/src/index.ts L12: BlockStatus = {ok, error, not_configured, pending}
packages/schemas/src/index.ts L18: SSTStatus = {ok, no_data, error}  ← SST narrows: land/ice = no_data
apps/worker/src/routes/fires.ts L13: "FIRMS returns 400 on bad key — degrade gracefully"
apps/worker/src/routes/sst-point.ts + CLAUDE.md lines 166-167: land-masked cell → no_data not error
backend/main.py L65-71: FIRMS_MAP_KEY unset → status:'not_configured'
backend/main.py L112-113, L123-125, L173-175: every HTTP exception → status:'error'
```

### 2.3 Static generation (M3)

```
apps/web/src/pages/reports/[...slug].astro  → getStaticPaths from reports-index.json
apps/web/src/pages/rankings/[metric].astro  → getStaticPaths inline 4 hyphenated slugs
Build output: 16 pages pre-rendered (/, /globe, /reports, 3 CBSAs, /rankings, 4 metrics, /guides, 4 stubs).
```

### 2.4 Home zero-JS (M9)

```
grep -c "_astro/.*\.js" dist/index.html → 0
dist/index.html has ZERO <script type="module"> references; Astro SSG only.
/globe loads GlobeApp.js + Cesium.js via dynamic import — not on home.
```

### 2.5 Canonical gating (M6)

```
apps/web/src/lib/seo.ts::resolveSiteUrl() — returns null when PUBLIC_SITE_URL unset
PUBLIC_SITE_URL unset build: dist/sitemap*.xml absent; dist/reports/*/index.html has no <link rel="canonical">
PUBLIC_SITE_URL=https://terrasight.example build: dist/sitemap-0.xml has 11 <loc> entries; canonicals emit
```

### 2.6 Guide stub triple-protection (M7)

```
dist/guides/what-is-a-trust-tag/index.html         → noindex ✓
dist/guides/how-to-read-a-report/index.html        → noindex ✓
dist/guides/why-compliance-is-not-exposure/index.html → noindex ✓
dist/guides/finding-local-environmental-data/index.html → noindex ✓
dist/sitemap-0.xml: zero /guides/ URLs                 ✓
dist/robots.txt: 4 Disallow: lines                     ✓
```

### 2.7 No Open-Meteo leak (N2)

```
grep "open-meteo\|open_meteo" in apps/, packages/, pipelines/ → 0 matches.
Matches only in: docs/*.md (reference doc), legacy/backend-connectors/ (quarantined).
```

### 2.8 No raster rendering in v2 paths (N3)

```
grep "renderSurface\|numpy\|raster" in apps/ → no files.
backend/main.py is 4-endpoint maintenance stub (health + fires + quakes + sst-point); no PNG / raster.
```

### 2.9 Schema ↔ fixture conformance (pipelines/tests)

```
pytest pipelines/tests/ → 60 passed in 0.53s
  test_report_contract.py (14 tests) — core-block invariants, gate correctness, weakest-wins, composer roundtrip
  test_erddap_sst_contract.py (14 tests)
  test_gibs_contract.py (18 tests) — manifest conformance, _ENCC detection, date formats
  test_firms_contract.py (5 tests)
  test_usgs_contract.py (7 tests)
  test_smoke.py (2 tests)
```

### 2.10 Ad-slot layout sanity (M8)

```
dist/reports/new-york-newark-jersey-city/index.html: 3 data-ad-slot occurrences (hero + mid + footer) ✓
AdSlot.astro inline style="min-height:${minHeight}px" (CLS-safe)
AdSlot.types.ts exactly 5 frozen names matching docs/revenue/adsense-placement-policy.md §1
```

---

## 3. Findings

### 3.1 BLOCKER (P0) — `_redirects` points to dead Render runtime

**File:** `apps/web/public/_redirects`

**Current:**
```
/api/* https://terrasight-api-o959.onrender.com/:splat 200
```

**Issue:** This is a v1 Cloudflare-Pages rewrite that sends all `/api/*` traffic to the legacy Render deployment — violating v2 rule N1 ("Worker is proxy/cache only. No Render runtime dependency"). The Worker already implements the same 3 endpoints (`/api/fires`, `/api/earthquakes`, `/api/sst-point`) at `apps/worker/src/index.ts`. The redirect must target the Worker's deploy URL (or be removed when the Worker is deployed to the same origin / on a dedicated subdomain).

**Risk:** At the moment a real `PUBLIC_SITE_URL` ships, Globe fetches will flow to Render and either:
- succeed via the 4-endpoint maintenance stub (only fires/quakes/sst-point work, so most probably OK today), OR
- fail cold-start-slow (Render free tier 30s wake time), OR
- hit a stale response contract if Render and Worker drift.

**Fix options (choose per deployment story):**
- **(a) Same-origin Worker (recommended):** Deploy the Worker to the same Cloudflare zone as the Pages site; delete the `_redirects` rewrite entirely. Pages will serve `/api/*` via the Worker route binding.
- **(b) Dedicated subdomain Worker:** Set `PUBLIC_WORKER_BASE_URL=https://api.terrasight.example` at Pages build; delete the `_redirects` line. Globe `fetch()` already reads `PUBLIC_WORKER_BASE_URL` (see `apps/web/src/islands/GlobeApp.tsx` L49-51).
- **(c) Keep Render maintenance until Worker deploys:** Update the rewrite target to match the Worker's production URL; leave as a drop-in swap.

**Recommended action NOW (in this review commit):** Replace the `_redirects` line with a comment that documents the intent so no one accidentally re-adds the Render target:

```
# /api/* is served by the Cloudflare Worker at apps/worker/ (v2). The
# Worker is bound either same-origin at the Pages zone or on a dedicated
# subdomain exposed via PUBLIC_WORKER_BASE_URL. See
# docs/architecture/architecture-v2.md §7 and frontend-routing.md.
# Do not re-add a /api/* → terrasight-api-o959.onrender.com rewrite —
# v2 forbids Render runtime dependency (Rule N1).
```

Applied in this commit. See §6.

### 3.2 P2 — `data/` rankings/reports JSON duplication

**Files:** `data/reports/*.json` + `data/rankings/*.json` (repo root) mirrored to `apps/web/src/data/*.json` (workspace).

**Issue:** Astro/Vite cannot reliably `import.meta.glob` across the workspace root, so report + ranking JSONs live twice. Currently manual — already logged as Step 8 follow-up in progress.md + `docs/guardrails.md` Step 7 frontend landmines.

**Risk:** Stale mirror → visitor sees yesterday's ranking while pipeline already shipped today's.

**Fix:** Add a `pnpm --filter web predev` / `prebuild` hook that runs `cp -r data/reports apps/web/src/data/reports && cp -r data/rankings apps/web/src/data/rankings`, or use a Vite plugin alias. Deferred (not a release blocker; pipelines currently produce null-value scaffolds).

### 3.3 P2 — `/og/default.png` path reserved, file absent

**File (referenced):** `apps/web/src/lib/seo.ts` default OG image path.

**Issue:** `buildPageMeta()` emits `<meta property="og:image" content="/og/default.png">` but no such file exists in `apps/web/public/`. Social scrapers will 404 on the OG image.

**Fix:** Create a 1200×630 TerraSight-brand image and drop in `apps/web/public/og/default.png`. Documented as Step 9+ follow-up in `docs/architecture/seo-ia.md` §8.

### 3.4 Clean (no action) — `VIIRS_SNPP_DayNightBand_ENCC` mentions

All 12 matches are intentional warnings:
- `apps/web/src/lib/layers.ts` L9-10, L172 — comment warnings
- `pipelines/connectors/gibs.py` + `pipelines/tests/test_gibs_contract.py` — negative-case assertion the connector rejects it
- `data/fixtures/gibs/VIIRS_SNPP_DayNightBand_ENCC.json` — the frozen fixture documenting the 2023-07-07 landmine
- `docs/*` — architecture notes

Actual layer usage resolves to the non-ENCC `VIIRS_SNPP_DayNightBand` id. PASS.

---

## 4. Cross-reference: rule → artifact

| Non-Negotiable Rule (CLAUDE.md) | Primary enforcement point |
|---|---|
| Rule 1 — No Render runtime rasterization | `backend/main.py` stub only; `_redirects` being fixed (§3.1); `apps/` has zero raster endpoints |
| Rule 2 — No Open-Meteo in production MVP | No matches in any v2 path (apps/, packages/, pipelines/) |
| Rule 3 — Reports statically generated | `getStaticPaths` in `[...slug].astro` + `[metric].astro` |
| Rule 4 — GIBS-first for Globe | `apps/web/src/lib/layers.ts` — 5 GIBS WMTS defs + 2 Worker-proxy events only |
| Rule 5 — Trust tags required | zod enum required on all schemas; 42 block-level tags in fixtures |
| Rule 6 — Graceful status | Worker + Render stub + composer all exit via `status` branches |
| Rule 7 — Layer composition ≤ 1 continuous + 1 event | `GlobeApp.tsx` LayerControls group enforcement (Step 6 acceptance) |
| Rule 8 — Mandatory disclaimers | `block.notes[]` injected by composer for air_quality (ECHO + AirNow) + water (WQP); rankings methodology carries same |
| Rule 9 — No composite scores | Schema has no "score" field; every metric is a standalone row |
| Rule 10 — Worker is proxy/cache only | `apps/worker/src/index.ts` — 3 routes, thin passthrough + cache, zero heavy computation |

---

## 5. Verdict

**Overall: PASS with 1 P0 blocker fixed in this commit + 2 P2 deferred.**

| Severity | Count | Status |
|---|---|---|
| P0 (blocker) | 1 | §3.1 fixed in this commit |
| P1 (must-fix pre-prod) | 0 | — |
| P2 (follow-up, non-blocking) | 2 | §3.2 + §3.3 deferred, tracked in progress.md Next Actions |
| Clean | all other rules | — |

**Release-blocking items (progress.md):**
- **None after §3.1 is committed.** The `_redirects` rewrite being swapped away from Render is the only release blocker surfaced by this review.

**Next-phase risks (non-blocking but document in Step 9+):**
- OG image file missing (§3.3)
- Data-mirror manual copy will drift (§3.2)
- Cesium 1.37 MB bundle still large (pre-existing, tracked in Step 6 follow-ups)

---

## 6. Actions taken in this review commit

1. Fixed `apps/web/public/_redirects` per §3.1 — removed Render rewrite, added v2 intent comment.
2. Created this file `docs/review/review-checklist.md`.
3. Updated `progress.md` Last Completed with Step 9 outcome + Next Actions.

No schema / component / data changes — this is a policy-enforcement review only.

---

## 7. Appendix — verification commands replay

```bash
# Type check
cd apps/web && pnpm tsc --noEmit                  # exit 0

# Build (both modes)
cd apps/web && pnpm build                          # 16 pages, no sitemap
cd apps/web && PUBLIC_SITE_URL=https://terrasight.example pnpm build  # 16 pages + 11-URL sitemap

# Pipeline tests
cd pipelines && python -m pytest tests/ -x         # 60 passed

# Rule scans
grep -r "open-meteo\|open_meteo" apps/ packages/ pipelines/   # 0 matches
grep -r "onrender\|render.com"   apps/web/public/_redirects   # FIXED (0 matches after commit)
grep -c "_astro/.*\.js" dist/index.html                       # 0
grep -l "noindex" dist/guides/*/index.html                    # 4/4
grep "<loc>.*/guides/" dist/sitemap-0.xml                     # empty
```
