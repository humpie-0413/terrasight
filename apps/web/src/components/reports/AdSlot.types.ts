/**
 * AdSlot name enum — valid slot identifiers for the `<AdSlot />` placeholder.
 *
 * Kept in a sibling `.ts` file because Astro (.astro) components cannot
 * cleanly re-export TypeScript types through the barrel. This file is the
 * canonical source; both the AdSlot component and `index.ts` import it.
 *
 * Step 8 wires real AdSense and will extend / freeze this list — never
 * rename an existing slot without updating the Step 8 ad-unit mapping.
 */
export type AdSlotName =
  | 'report-hero'
  | 'report-mid'
  | 'report-footer'
  | 'rankings-header'
  | 'rankings-footer';
