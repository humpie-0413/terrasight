// Barrel export for report block rendering components.
//
// Consumers (Agent 1's [...slug].astro page, future `/reports/index.astro`)
// should import from this module. Astro components re-exported here remain
// usable in .astro frontmatter since Astro/Vite resolve the .astro extension.
//
// Note: the 3 ids below are the ONLY optional blocks this renderer layer
// embeds inline. `city_comparison` and `related_cities` are rendered by
// Agent 2 components — do NOT attempt to dispatch them through BlockRenderer.
export const EMBEDDABLE_OPTIONAL_BLOCK_IDS = [
  'pfas_monitoring',
  'coastal_conditions',
  'disaster_history_detailed',
] as const;

export { default as BlockRenderer } from './BlockRenderer.astro';
export { default as NoData } from './NoData.astro';
export { default as AirQualityBlock } from './blocks/AirQualityBlock.astro';
export { default as ClimateLocallyBlock } from './blocks/ClimateLocallyBlock.astro';
export { default as HazardsDisastersBlock } from './blocks/HazardsDisastersBlock.astro';
export { default as WaterBlock } from './blocks/WaterBlock.astro';
export { default as IndustrialEmissionsBlock } from './blocks/IndustrialEmissionsBlock.astro';
export { default as SiteCleanupBlock } from './blocks/SiteCleanupBlock.astro';
export { default as PopulationExposureBlock } from './blocks/PopulationExposureBlock.astro';
export { default as MethodologyBlock } from './blocks/MethodologyBlock.astro';
export { default as PfasMonitoringBlock } from './blocks/PfasMonitoringBlock.astro';
export { default as CoastalConditionsBlock } from './blocks/CoastalConditionsBlock.astro';
export { default as DisasterHistoryDetailedBlock } from './blocks/DisasterHistoryDetailedBlock.astro';

// Agent 2 — sidebar / adjunct components for the Report page.
export { default as RelatedCities } from './RelatedCities.astro';
export { default as CityComparison } from './CityComparison.astro';
export { default as RankingsSnippet } from './RankingsSnippet.astro';
export { default as AdSlot } from './AdSlot.astro';
export type { AdSlotName } from './AdSlot.types';
