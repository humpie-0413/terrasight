# AdSense Placement Policy (v2, Step 8)

> Frozen by Step 8 (2026-04-18). Defines the static ad slot map, the
> CLS-safe reserved-box rule, AdSense failure handling (Rule 5), and
> the consent / privacy deferral to Step 9+.
>
> Related: `docs/architecture/seo-ia.md` (overall IA + canonical rule) ·
> `docs/reports/report-page-ux.md` §3 (report page ad slot positions).

## 1. Fixed slot names + positions

The slot-name union is frozen at
`apps/web/src/components/reports/AdSlot.types.ts::AdSlotName`. Do
not rename an existing slot — Step 9+ ad-unit mappings are keyed
on these exact strings.

| Slot name | Page | Position | Min-height (inline) | Intent |
|---|---|---|---|---|
| `report-hero` | `/reports/{slug}` | Above main+sidebar grid, below summary lede | 120 px | Top revenue unit, first impression |
| `report-mid` | `/reports/{slug}` | Inside main column, immediately after `air_quality` block | 120 px | Mid-read unit — highest CTR location in the funnel |
| `report-footer` | `/reports/{slug}` | Below the grid, above SiteFooter | 120 px | Trailing unit |
| `rankings-header` | `/rankings` (index) | Below the page header, above the metric card list | 120 px | Rankings index entry revenue |
| `rankings-footer` | `/rankings/{metric}` | Below the methodology section | 120 px | Per-metric exit revenue |

**Per-page totals:** reports = 3 slots; rankings index = 1 slot;
per-metric rankings = 1 slot; home / globe / atlas / guides = 0
slots. These counts are policy, not advisory — adding a fourth
slot to reports requires doc + `AdSlotName` union + `AdSlot.astro`
update **together**.

## 2. Why these positions, and not others

- **Only high-intent pages carry ads.** The home is free of ads
  (zero-JS budget, Step 6) and so are the globe (interactive,
  Cesium-heavy) and guides (low-intent top of funnel). Ads live
  where the user is already deep in the funnel.
- **Above the fold + mid-read + below the fold.** The classic
  three-slot pattern on reports captures: (a) high-view scroll
  arrivals, (b) engaged readers who pass the first block, (c)
  users who scroll all the way through.
- **No in-content injection.** We do not insert ads between a
  metric table and its disclaimer, because the mandatory
  disclaimers (ECHO / WQP / AirNow) are a non-negotiable
  structural element (Rule 8). Breaking a metric-disclaimer pair
  across an ad would misrepresent the data.

## 3. CLS rule — every slot reserves height

The `AdSlot.astro` component emits `min-height:{minHeight}px`
inline on its root. Default `minHeight` is 120 px; do not
override without also updating the slot-name table above.

**Why inline style:** browser layout commits the reserved box
before the stylesheet finishes applying, so a bare-boxed slot
stays CLS-zero even when the CSS load is cold. External
stylesheets or `<style>` blocks do not give the same guarantee.

Empty vs. filled state:

```astro
<!-- Step 8 (Render now) -->
<aside data-ad-slot="report-mid" style="min-height:120px" ...>
  <span class="ad-slot__label">Advertisement</span>
</aside>

<!-- Step 9+ wiring (future) -->
<aside data-ad-slot="report-mid" style="min-height:120px" ...>
  <ins class="adsbygoogle" data-ad-client="ca-pub-..." ... />
  <!-- consent gate renders here -->
</aside>
```

In both states, the outer `<aside>` keeps its reserved box. An
AdSense fetch failure / consent refusal leaves the label text
visible — the layout stays intact.

## 4. AdSense failure handling (Rule 5)

Rule 5 (graceful degradation) applies to the ad unit just like
any other data surface:

| State | Behavior |
|---|---|
| AdSense JS loads, ad fills | Label + debug caption hidden; unit renders normally |
| AdSense JS loads, no fill | Label stays dimmed; box height preserved |
| AdSense JS blocked (uBlock / privacy extension) | Label + box stay; no DOM shift |
| `PUBLIC_ADSENSE_CLIENT` unset at build | Placeholder (Step 8 behavior today) |
| Step 9 consent gate refused | Same placeholder state; no cookies set |

**Never blank the page when the ad fails.** Step 6 + Step 7
already extended this contract to every data block; ads follow
the same discipline.

## 5. No in-content injection, no lazy pop-ins

- **No runtime DOM-injected ads.** All 5 Step 8 slots are present
  in the SSG-rendered HTML. No ad unit is inserted by JS after
  hydration.
- **No lazy "pop-in" units.** No modal overlays, sticky footers
  that creep above the native footer, or scroll-triggered
  interstitials. The visitor should never see an ad they did not
  scroll into view of naturally.
- **No auto-ads.** AdSense auto-ad placement (`enable_page_level_ads`)
  is explicitly disabled when the script wires up (Step 9+). We
  own the placements.

## 6. Labeling + accessibility

- `<aside role="complementary" aria-label="Advertisement">` on
  every slot — screen readers announce the region.
- Visible "ADVERTISEMENT" label (uppercase, letter-spaced) above
  the ad box, both in dev and production (the dev-only variant
  gets an additional dotted border + slot caption for
  orientation).
- No fake "news" / editorial framing around ads. AdSense policy
  explicitly forbids this, and so does our content policy.

## 7. Privacy / consent — Step 9 follow-up

Not wired in Step 8. Documented here so the consent design is
not reinvented:

1. **TCF v2 or local banner.** We'll default to a simple
   local-storage banner with "Accept / Reject" buttons (no TCF
   IAB iframe — heavier than the whole home bundle). Cloudflare
   Pages doesn't need the IAB framework for AdSense basic
   functionality.
2. **Personalized ads gated by consent.** Until the user clicks
   "Accept", we render `data-npa="1"` (non-personalized ads)
   across all slots. Clicking "Accept" swaps `npa` to 0 and
   reloads the ad slots.
3. **Region-aware default.** EU / UK / California visitors
   default to reject; others default to accept. IP geolocation
   happens at the edge (Cloudflare Workers), not the client.
4. **No third-party scripts before consent.** AdSense loader JS
   itself is deferred until consent resolves (pre-consent, the
   reserved boxes sit with label text only).

## 8. Developer checklist — adding a new slot

1. Extend the `AdSlotName` union in `AdSlot.types.ts`.
2. Add a row in §1 above.
3. Insert `<AdSlot slot="..." />` at the chosen position in the
   page.
4. Verify CLS: compare `min-height` in inline style on the new
   slot vs. §3.
5. Update the ad-unit ID mapping (Step 9+ code).

## 9. Locked decisions (Step 8)

- 5 slot names frozen: `report-hero`, `report-mid`, `report-footer`,
  `rankings-header`, `rankings-footer`.
- 120 px `min-height` default on every slot (inline style).
- `AdSlot.astro` is a reserved-box placeholder only — Step 8 does
  not load any third-party JS.
- No in-content, no pop-in, no auto-ads.
- Consent / privacy wiring deferred to Step 9+.
