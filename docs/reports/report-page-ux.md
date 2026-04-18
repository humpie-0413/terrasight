# Report Page UX — `/reports/{slug}`

> **Status:** Step 7 delivered (2026-04-18). Routes live at
> `apps/web/src/pages/reports/[...slug].astro` and
> `apps/web/src/pages/reports/index.astro`.
> **Canonical data contract:** `packages/schemas/src/index.ts::CityReport`.

Read this file when you are about to edit anything under
`apps/web/src/pages/reports/**` or `apps/web/src/components/reports/**`.
It is the source of truth for block order, gating, ad placement,
JSON-LD emission, and canonical-URL policy. The companion files are
`report-block-policy.md` (block IDs, optional availability rules) and
`report-schema.md` (the Zod contract).

## 1. Route & data model

| Route | File | Behavior |
|---|---|---|
| `/reports` | `pages/reports/index.astro` | Listing page, paged off `data/reports-index.json` |
| `/reports/{slug}` | `pages/reports/[...slug].astro` | Per-CBSA page, built from `data/reports/{slug}.json` |

`getStaticPaths` iterates **the mirrored index**
(`apps/web/src/data/reports-index.json`) — not a filesystem glob.
Each slug's JSON is loaded via `import.meta.glob<CityReport>('../../data/reports/*.json', { eager: true, import: 'default' })` so TypeScript sees real types and Vite tree-shakes unreferenced slugs.

**Data-mirror rule:** `apps/web/src/data/reports/*.json` and
`apps/web/src/data/rankings/*.json` are copies of
`data/reports/*.json` and `data/rankings/*.json` (repo root). Astro/Vite
cannot reliably import JSON from outside `apps/web/`. A build-script
copy step is a Step 7 follow-up; today the mirror is manual — always
re-copy both directories when the pipeline regenerates them.

## 2. Block order & gating (Rule 5)

The report column renders blocks in this exact order:

```
1. air_quality          (core, always)
   ├─ AdSlot: report-mid (inserted immediately after)
2. climate_locally      (core, always)
3. hazards_disasters    (core, always)
4. water                (core, always)
5. industrial_emissions (core, always)
6. site_cleanup         (core, always)
7. population_exposure  (core, always)
8. coastal_conditions   (optional, embedded only when
                         meta.optionalAvailability['coastal_conditions']
                         === 'included')
9. pfas_monitoring      (optional, same gate)
10. disaster_history_detailed (optional, same gate)
11. CityComparison      (always renders — external link card, never
                         an embedded cross-report table)
12. methodology         (core, always LAST)
```

**Rules:**

- Core blocks (1-7, methodology) **always render**, even when
  `status !== 'ok'`. A `pending` / `not_configured` / `error` block
  renders `NoData` inside the body so the skeleton is always complete.
- Embedded optionals (8-10) render **only when `availability === 'included'`**.
  If `absent` / `external` / missing, the component is skipped — no
  empty card.
- `city_comparison` is **always external** (Step 5 policy).
  `CityComparison.astro` owns the hyphenated-slug rankings map and
  renders a static link card. Never embed a cross-report table here
  (2-pass aggregation is explicitly avoided).
- `related_cities` lives in the sidebar, not the main column.
  `RelatedCities.astro` is gated by `data.peer_slugs` (Step 5 actual
  emit shape) OR the schema-spec `data.peers` shape — both supported
  until the spike mismatch is reconciled.
- `methodology` is pulled out of the natural `blocks[]` order and
  appended last — always.

The splitting logic lives in
`apps/web/src/lib/reports.ts::partitionBlocks(report)`. Do not
re-implement it in the page — import it.

## 3. Ad slots

Three slots, all rendered through `AdSlot.astro`:

| Slot name | Position | Purpose |
|---|---|---|
| `report-hero` | Above main+sidebar grid, right below Summary | Top revenue unit |
| `report-mid` | Between `air_quality` and `climate_locally` | Mid-read unit |
| `report-footer` | Below the grid, above SiteFooter | Trailing unit |

**CLS rule:** `AdSlot` always emits `min-height` inline (default
`120px`). Never let an ad unit load without a reserved box. Step 8
wires the actual AdSense code; Step 7 ships a reserved placeholder.

Valid slot names live in `AdSlot.types.ts` as the exported
`AdSlotName` union — Astro cannot export types from `.astro`
directly. When adding a new slot name, edit both
`AdSlot.types.ts` and this table.

**Fragment trap (landmine):** Astro's `<>...</>` fragment shorthand
silently drops siblings when used inside `.map()`. The page uses
array-return `.map((block, i) => [<Primary/>, <Secondary/>])` for the
mid-slot injection. Do not replace with `<Fragment>` or shorthand —
you will lose the mid ad slot in the rendered HTML.

## 4. JSON-LD

The page emits up to 3 `<script type="application/ld+json">` blocks
into `<slot name="head">` in `BaseLayout.astro`:

1. `Article` — always. Authored by TerraSight, dateModified =
   `report.meta.updatedAt`.
2. `BreadcrumbList` — always. Home → Reports → {city}.
3. `Dataset` — **only when ≥1 non-methodology block has `status === 'ok'`**.
   `variableMeasured[]` contains up to 3 `PropertyValue` entries from
   those ok-status blocks. If every core block is pending (common
   for the current 3 seed reports), this script is not emitted —
   the schema forbids an empty Dataset.

All three builders live in `lib/reports.ts` as pure functions —
`buildJsonLdArticle`, `buildJsonLdBreadcrumb`, `buildJsonLdDataset`.
They accept a `siteUrl?: string | null`; when absent, URLs are
emitted as relative paths.

## 5. Canonical link (Rule 7)

`<link rel="canonical">` is emitted **only when `PUBLIC_SITE_URL`
is set at build time**. Dev / preview environments deliberately
skip the tag rather than hard-coding a placeholder URL that would
be wrong the moment the site deploys.

In CI: set `PUBLIC_SITE_URL=https://terrasight.example` on the
production build step. Nothing else downstream reads this env var;
only the canonical-emit check.

## 6. Sidebar

The right sidebar contains exactly two cards, in order:

1. `RelatedCities.astro` — peer CBSAs. Gated: renders nothing
   when `peer_slugs` / `peers` is missing or empty. Never a
   "no peers" empty-state card.
2. `RankingsSnippet.astro` — top-of-rankings teaser for the 4
   metrics. Glob-loads `data/rankings/*.json`; handles
   `value: null` / `rank: null` gracefully (pending label).

When you add a new sidebar card, put it AFTER these two — the ad
unit and city comparison stay in the main column.

## 7. Status → UI mapping (Rule 6)

| Block status | UI treatment |
|---|---|
| `ok` | Normal body + metrics table + citations + disclaimers |
| `pending` | `NoData` card, amber pill, body text + "data pending upstream migration" notice |
| `not_configured` | `NoData` card, gray pill, body text + "source not configured" notice |
| `error` | `NoData` card, red pill, `block.error` string passthrough |

`StatusPill.tsx` (shipped from `packages/ui`) owns the color
mapping. Never duplicate pill colors elsewhere; import the pill.

## 8. Files touched / shipped in Step 7

**Pages:**
- `apps/web/src/pages/reports/[...slug].astro` (NEW, ~370 lines)
- `apps/web/src/pages/reports/index.astro` (NEW)

**Shared helpers:**
- `apps/web/src/lib/reports.ts` (NEW) — `CORE_BLOCK_IDS`,
  `EMBEDDABLE_OPTIONAL_IDS`, `partitionBlocks`, 3 JSON-LD builders

**Components (`apps/web/src/components/reports/`):**
- `BlockRenderer.astro` — dispatcher
- `NoData.astro` — status-keyed notice
- `MetricsTable.astro` — shared 3-col metric table
- `AdSlot.astro` + `AdSlot.types.ts` — reserved-box ad placeholder
- `CityComparison.astro` — external rankings link card
- `RelatedCities.astro` — sidebar peer list (handles `peers` +
  `peer_slugs` drift)
- `RankingsSnippet.astro` — sidebar rankings teaser
- `blocks/AirQualityBlock.astro` (× 8 core bodies +
  × 3 embeddable optional bodies = 11 block body components)
- `index.ts` — barrel (default exports + `AdSlotName` type export +
  `EMBEDDABLE_OPTIONAL_BLOCK_IDS` re-export)

**UI primitive:**
- `packages/ui/src/StatusPill.tsx` (NEW) — ~18px pill, BlockStatus
  → color mapping

**Layout:**
- `apps/web/src/layouts/BaseLayout.astro` — added `<slot name="head" />`
  so per-page pages can inject JSON-LD + optional canonical

**Data fixtures:**
- `apps/web/src/data/reports/*.json` (× 3 mirrored CBSAs)
- `apps/web/src/data/rankings/*.json` (× 4 metrics + index)

## 9. Verification (2026-04-18)

Build is green:

```
6 page(s) built in 15.64s
  /index.html
  /globe/index.html
  /reports/index.html
  /reports/new-york-newark-jersey-city/index.html
  /reports/los-angeles-long-beach-anaheim/index.html
  /reports/houston-the-woodlands-sugar-land/index.html
```

`tsc --noEmit` passes. Rendered HTML contains, per CBSA report:

- 8 core block anchors (air_quality through methodology) ✓
- 1 embedded optional (coastal_conditions — `included` in
  fixture meta) ✓
- 3 ad slots (`data-ad-slot="report-hero"`, `…-mid`, `…-footer`) ✓
- CityComparison external link card ✓
- RelatedCities sidebar ✓
- RankingsSnippet sidebar ✓

## 10. Step 7 follow-ups (for Step 8+)

1. **Automate data mirror:** add a build hook that copies
   `data/reports/*.json` → `apps/web/src/data/reports/*.json`
   (same for `rankings/`).
2. **Resolve `peers` vs `peer_slugs` shape drift:** Step 5
   composer emits `peer_slugs: string[]`; schema spec has
   `peers: Array<{slug,city,region,reason?}>`. RelatedCities
   supports both — pick one and update both sides.
3. **AdSense wiring:** `AdSlot` is a reserved placeholder only;
   Step 8 wires the actual ad tag (lazy-loaded, with consent gate).
4. **Full rankings pages:** `/rankings/{metric}` targets are
   referenced by `CityComparison.astro`'s `SLUG_MAP` but do not yet
   exist. Step 8 builds them.
5. **Sitemap entry for every report + rankings page:** via
   `@astrojs/sitemap` in Step 8.
6. **Lighthouse pass:** `astro check` remains fragile on this repo
   (Cesium 50k-line `.d.ts` + Volar behavior); Step 10 runs
   Lighthouse against `pnpm --filter web preview`.
