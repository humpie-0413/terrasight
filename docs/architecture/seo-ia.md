# SEO Information Architecture (v2, Step 8)

> Frozen by Step 8 (2026-04-18). Any change to the funnel shape, noindex
> policy, or canonical-emission rule MUST update this doc first.
>
> Related: `docs/architecture/frontend-routing.md` (Step 6 route map) ·
> `docs/reports/report-page-ux.md` (Step 7 per-page contract) ·
> `docs/revenue/adsense-placement-policy.md` (ad slot policy).

---

## 1. The three-tier funnel

The public URL space maps to the CLAUDE.md 3-tier thesis:
**hook → depth → revenue**.

```
ENTRY (유입)                 RETENTION (체류)           MONETIZATION (수익)
┌─────────────────┐          ┌────────────────┐         ┌────────────────┐
│ /rankings/*     │ ──────→  │ /reports/{slug}│ ──────→ │ /reports/{slug}│
│ /guides/*       │          │ /globe         │         │ (ad slots ×3)  │
│  (noindex today)│          │ /atlas (Step 11)│        │                │
│ /reports        │          └────────────────┘         │ /rankings/*    │
│  (index)        │                                     │ (ad slots ×2)  │
└─────────────────┘                                     └────────────────┘
```

- **Entry surfaces** are discovery routes. Search engines land here
  via long-tail queries ("PM2.5 ranking U.S. metros", "Houston
  environmental report"). They deliberately link outward into the
  depth tier.
- **Retention surfaces** are the expert pages — reports, the globe,
  and (future) the atlas. These keep the user engaged, typically
  with internal cross-links back to rankings / reports / guides.
- **Monetization surfaces** overlap with retention — the ad slots
  live on the high-intent report and ranking pages, not on the home.

## 2. Route → bundle → crawlability map

| Route | Rendering | Indexable? | Sitemap? | Canonical emitted when `PUBLIC_SITE_URL` set? | Notes |
|---|---|---|---|---|---|
| `/` | Astro SSG | yes | yes | yes | Zero JS (Step 6). |
| `/globe` | Astro + React island | yes | yes | yes | CesiumJS lazy-loaded. |
| `/reports` | Astro SSG | yes | yes | yes | List of metros. |
| `/reports/{slug}` | Astro SSG | yes | yes | yes | Per-CBSA. JSON-LD Article + Breadcrumb + Dataset (conditional). |
| `/rankings` | Astro SSG | yes | yes | yes | 4 metric cards. |
| `/rankings/{metric}` | Astro SSG | yes | yes | yes | JSON-LD Breadcrumb always; Dataset only when ≥1 non-null row. |
| `/guides` | Astro SSG | yes | yes | yes | Index page is indexable — the stubs it links to are not. |
| `/guides/*` stubs | Astro SSG | **no** (`<meta name="robots" content="noindex, nofollow">`) | **excluded from sitemap** | **no** (not yet indexable) | Each stub also listed in `robots.txt` `Disallow` belt-and-suspenders. |
| `/atlas/*` | planned Step 11+ | TBD | TBD | TBD | Not yet built. |

### 2.1 Canonical rule (Rule 7)

**Canonical `<link rel="canonical">` emits only when
`PUBLIC_SITE_URL` is set at build time.** Dev and preview builds
deliberately skip the tag rather than shipping a placeholder URL
that would be wrong the moment the site deploys.

Check lives in `apps/web/src/lib/seo.ts::resolveSiteUrl()` (trims
trailing slash, returns `null` on empty / unset). `BaseLayout.astro`
consumes the return value; per-page pages (`/reports/{slug}`,
`/rankings/{metric}`) additionally inject their own canonical into
the `<slot name="head">` when they need it.

### 2.2 Noindex rule

A page is noindex **only if**:
- It is a Step 8 guide stub awaiting content, OR
- (future) the page represents stale / superseded data.

Today: all 4 guide stubs + the corresponding `Disallow` lines in
`robots.txt`. Remove the noindex meta + `Disallow` line + sitemap
filter exclusion together when a guide's content body ships.

## 3. Internal-link conventions

- Use `<InternalLink to="/...">` from
  `apps/web/src/components/InternalLink.astro` when crossing
  navigational sections (report ↔ atlas ↔ globe ↔ rankings ↔
  guides). It emits `data-link-type="internal"` and
  `data-target-section` analytics hooks.
- Plain `<a href="/...">` is fine for in-section links (e.g., a
  report linking a sibling citation / disclaimer guide).
- External links (citations, source pages) are **not** wrapped —
  they keep `target="_blank" rel="noopener noreferrer"` inline so
  they stay visually distinct and keep the referrer policy explicit.
- Canonical reverse-links:
  - Rankings card → `/reports/{slug}` (target-section = reports)
  - Report → `/rankings/{metric}` via `CityComparison.astro`
  - Report methodology disclaimer → `/guides/why-compliance-is-not-exposure`
  - Rankings methodology disclaimer → same guide
  - Every page → `/` via header brand + `/` footer brand

## 4. Sitemap + robots.txt

### Sitemap (`@astrojs/sitemap` v3.2.x, Astro-4-compatible)

- Wired in `apps/web/astro.config.mjs`. Astro's `site` option is
  populated from `process.env.PUBLIC_SITE_URL` — when unset, the
  sitemap integration warns and emits nothing (confirmed via
  `dist/sitemap-index.xml` absence on dev builds).
- Filter excludes every path under `/guides/` so the 4 stubs stay
  out of the sitemap until content ships.
- When `PUBLIC_SITE_URL` is set, `sitemap-index.xml` and
  `sitemap-0.xml` land in `dist/`. Verified: 11 URLs (home,
  globe, rankings index + 4 metrics, reports index + 3 cities).

### robots.txt (`apps/web/public/robots.txt`)

Static file in `public/`. Current content:

```
User-agent: *
Allow: /

Disallow: /guides/what-is-a-trust-tag
Disallow: /guides/how-to-read-a-report
Disallow: /guides/why-compliance-is-not-exposure
Disallow: /guides/finding-local-environmental-data
```

The `Sitemap:` line is **not** in the file today — its URL depends
on the deploy origin. Deploy wiring (Step 8 follow-up): CI prepends
`Sitemap: ${PUBLIC_SITE_URL}/sitemap-index.xml` to `dist/robots.txt`
when the env var is set, before uploading to Cloudflare Pages.

## 5. Content production backlog

Priority order once Step 9 ships:

1. **`/guides/why-compliance-is-not-exposure`** — referenced from
   every rankings page with `showComplianceDisclaimer=true` AND
   from every compliance-tagged report block. Highest internal
   PageRank ceiling.
2. **`/guides/what-is-a-trust-tag`** — referenced implicitly by
   every TrustBadge on every page. Second-highest ceiling.
3. **`/guides/how-to-read-a-report`** — onboarding for the reports
   tier. Medium priority.
4. **`/guides/finding-local-environmental-data`** — navigation hub.
   Lowest priority until the atlas (Tier 2) ships.

When a guide's body is written, the release checklist is:
1. Delete `<meta name="robots" content="noindex, nofollow">` from the
   stub page.
2. Remove the `Disallow:` line for that path from
   `public/robots.txt`.
3. Remove / tighten the filter in `astro.config.mjs` so the page
   appears in the sitemap.
4. Re-run the build and verify the URL lands in `sitemap-0.xml`.

## 6. Ad slot policy cross-ref

All monetization-related decisions are locked in
**`docs/revenue/adsense-placement-policy.md`**. Step 8 ships
reserved placeholders only — no AdSense tag is loaded at runtime.

## 7. Step 8 locked decisions

| Decision | Value |
|---|---|
| Canonical emission | `PUBLIC_SITE_URL` set → yes; unset → omit (never placeholder) |
| Guide stubs | `noindex, nofollow` + sitemap-excluded + `robots.txt` `Disallow` |
| Sitemap integration | `@astrojs/sitemap@^3.2.1` (Astro 4-compatible branch) |
| Sitemap filter | exclude `/guides/` until body content ships |
| Ad slot names (reports) | `report-hero`, `report-mid`, `report-footer` |
| Ad slot names (rankings) | `rankings-header`, `rankings-footer` |
| InternalLink analytics attrs | `data-link-type="internal"` + `data-target-section` (first path segment) |
| Twitter card | `summary_large_image` (via `lib/seo.ts::buildPageMeta`) |
| Default OG image | `/og/default.png` (file not created yet — reserved path) |

## 8. Step 9+ follow-ups

1. Author the 4 guide bodies per the backlog in §5 and clear the
   noindex gate.
2. Create the physical `/og/default.png` (1200×630, TerraSight
   brand). Step 8 only wires the path, not the file.
3. CI deploy wiring: prepend `Sitemap: ${PUBLIC_SITE_URL}/sitemap-index.xml`
   to `dist/robots.txt` when env var is set.
4. AdSense wiring (`packages/ads/*` TBD + consent gate) — covered
   by `docs/revenue/adsense-placement-policy.md` Step 9+.
5. Atlas SEO plan (Tier 2 — `/atlas/*`) — Step 11+ scope.
