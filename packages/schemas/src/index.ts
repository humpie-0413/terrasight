import { z } from 'zod';

export const TrustTag = z.enum([
  'observed',
  'near-real-time',
  'forecast',
  'derived',
  'compliance',
]);
export type TrustTag = z.infer<typeof TrustTag>;

export const BlockStatus = z.enum(['ok', 'error', 'not_configured', 'pending']);
export type BlockStatus = z.infer<typeof BlockStatus>;

// SST point uses a narrower enum — `no_data` is the graceful response for
// a user click on land or ice cells (common, not an error). Keep in sync
// with `pipelines/contracts/__init__.py::SSTStatus`.
export const SSTStatus = z.enum(['ok', 'no_data', 'error']);
export type SSTStatus = z.infer<typeof SSTStatus>;

export const LayerManifest = z.object({
  id: z.string(),
  title: z.string(),
  category: z.enum(['imagery', 'event']),
  kind: z.enum(['continuous', 'event']),
  source: z.string(),
  trustTag: TrustTag,
  coverage: z.enum(['global', 'ocean-only', 'land-only', 'coastal']),
  cadence: z.enum(['daily', 'monthly', '3h', '5min', 'static']),
  enabled: z.boolean(),
  legend: z
    .object({
      unit: z.string(),
      min: z.number(),
      max: z.number(),
      colormap: z.string(),
    })
    .optional(),
  imagery: z
    .object({
      type: z.literal('wmts'),
      urlTemplate: z.string(),
      tileMatrixSet: z.string(),
      availableDates: z.string(),
    })
    .optional(),
  eventApi: z
    .object({
      path: z.string(),
      ttlSeconds: z.number(),
    })
    .optional(),
  caveats: z.array(z.string()),
});
export type LayerManifest = z.infer<typeof LayerManifest>;

export const EventPoint = z.object({
  id: z.string(),
  type: z.enum(['wildfire', 'earthquake', 'alert']),
  lat: z.number(),
  lon: z.number(),
  observedAt: z.string(),
  severity: z.union([z.number(), z.string()]).optional(),
  label: z.string(),
  properties: z.record(z.unknown()),
});
export type EventPoint = z.infer<typeof EventPoint>;

export const DatasetRegistryItem = z.object({
  slug: z.string(),
  title: z.string(),
  category: z.string(),
  summary: z.string(),
  sourceType: z.enum(['satellite', 'model', 'regulatory', 'inventory']),
  trustTag: TrustTag,
  geographicCoverage: z.string(),
  cadence: z.string(),
  resolution: z.string(),
  license: z.string(),
  sourceUrl: z.string(),
  caveats: z.array(z.string()),
  linkedLayers: z.array(z.string()),
  linkedReportBlocks: z.array(z.string()),
});
export type DatasetRegistryItem = z.infer<typeof DatasetRegistryItem>;

// ---------------------------------------------------------------------------
// Report schema (v2, Step 5)
// Locked by docs/reports/report-block-policy.md. 8 core blocks (always
// present) + 5 optional blocks (gate-based). See §1 for inclusion rules.
// ---------------------------------------------------------------------------

export const CoreBlockId = z.enum([
  'air_quality',
  'climate_locally',
  'hazards_disasters',
  'water',
  'industrial_emissions',
  'site_cleanup',
  'population_exposure',
  'methodology',
]);
export type CoreBlockId = z.infer<typeof CoreBlockId>;

export const OptionalBlockId = z.enum([
  'pfas_monitoring',
  'coastal_conditions',
  'disaster_history_detailed',
  'city_comparison',
  'related_cities',
]);
export type OptionalBlockId = z.infer<typeof OptionalBlockId>;

export const BlockId = z.union([CoreBlockId, OptionalBlockId]);
export type BlockId = z.infer<typeof BlockId>;

export const OptionalAvailability = z.enum(['included', 'absent', 'external']);
export type OptionalAvailability = z.infer<typeof OptionalAvailability>;

// One metric row inside a block (e.g., "PM2.5 annual mean: 10.4 µg/m³").
// Per-metric `trustTag` is optional — if omitted, the metric inherits
// the block-level trustTag.
export const ReportMetric = z.object({
  label: z.string(),
  value: z.union([z.string(), z.number(), z.null()]),
  unit: z.string().optional(),
  note: z.string().optional(),
  trustTag: TrustTag.optional(),
});
export type ReportMetric = z.infer<typeof ReportMetric>;

export const ReportCitation = z.object({
  label: z.string(),
  url: z.string(),
});
export type ReportCitation = z.infer<typeof ReportCitation>;

export const ReportBlock = z.object({
  id: BlockId,
  title: z.string(),
  status: BlockStatus,
  // Block-level tag = weakest-wins across all composited sources
  // (see report-block-policy.md §4).
  trustTag: TrustTag,
  body: z.string(),
  metrics: z.array(ReportMetric).default([]),
  citations: z.array(ReportCitation).default([]),
  // Populated when status != 'ok' — short human-readable explanation.
  error: z.string().optional(),
  // Mandatory disclaimers / caveats (ECHO compliance ≠ exposure, WQP
  // discrete samples, AirNow reporting-area ≠ CBSA, etc.).
  notes: z.array(z.string()).default([]),
  // Block-specific freeform payload (e.g., top-N tables, geo references).
  data: z.record(z.unknown()).optional(),
});
export type ReportBlock = z.infer<typeof ReportBlock>;

// One fixed-shape map keyed by the 5 optional block ids. A missing key
// is a schema error.
export const OptionalAvailabilityMap = z.object({
  pfas_monitoring: OptionalAvailability,
  coastal_conditions: OptionalAvailability,
  disaster_history_detailed: OptionalAvailability,
  city_comparison: OptionalAvailability,
  related_cities: OptionalAvailability,
});
export type OptionalAvailabilityMap = z.infer<typeof OptionalAvailabilityMap>;

export const CityReportMeta = z.object({
  updatedAt: z.string(),
  build: z.object({
    pipelineVersion: z.string(),
    generatedAt: z.string(),
  }),
  optionalAvailability: OptionalAvailabilityMap,
});
export type CityReportMeta = z.infer<typeof CityReportMeta>;

export const CityReport = z.object({
  slug: z.string(),
  cbsaCode: z.string(),
  city: z.string(),
  region: z.string(),
  country: z.literal('US'),
  coastal: z.boolean(),
  lat: z.number(),
  lon: z.number(),
  population: z.number().nullable().optional(),
  populationYear: z.string().nullable().optional(),
  climateZone: z.string().nullable().optional(),
  summary: z.object({
    headline: z.string(),
    bullets: z.array(z.string()),
  }),
  blocks: z.array(ReportBlock),
  meta: CityReportMeta,
});
export type CityReport = z.infer<typeof CityReport>;

// ---------------------------------------------------------------------------
// Report index (served at data/reports/index.json)
// ---------------------------------------------------------------------------

export const CityReportIndexStatus = z.enum(['ok', 'partial', 'error']);
export type CityReportIndexStatus = z.infer<typeof CityReportIndexStatus>;

export const CityReportIndexEntry = z.object({
  slug: z.string(),
  cbsaCode: z.string(),
  city: z.string(),
  region: z.string(),
  updatedAt: z.string(),
  status: CityReportIndexStatus,
  coreBlocksOk: z.number(),
  coreBlocksTotal: z.literal(8),
});
export type CityReportIndexEntry = z.infer<typeof CityReportIndexEntry>;

export const CityReportIndex = z.object({
  generatedAt: z.string(),
  pipelineVersion: z.string(),
  reports: z.array(CityReportIndexEntry),
});
export type CityReportIndex = z.infer<typeof CityReportIndex>;

// ---------------------------------------------------------------------------
// Rankings (served at data/rankings/*.json)
// One file per metric. Order of rows = ranking order.
// Direction indicates which end is "best" for ranking purposes.
// ---------------------------------------------------------------------------

export const RankingMetric = z.enum([
  'air_quality_pm25',
  'emissions_ghg_total',
  'water_violations_count',
  'disaster_declarations_10y',
]);
export type RankingMetric = z.infer<typeof RankingMetric>;

export const RankingRow = z.object({
  slug: z.string(),
  city: z.string(),
  region: z.string(),
  value: z.number().nullable(),
  unit: z.string(),
  rank: z.number().nullable(),
  trustTag: TrustTag,
});
export type RankingRow = z.infer<typeof RankingRow>;

export const Ranking = z.object({
  metric: RankingMetric,
  title: z.string(),
  direction: z.enum(['asc', 'desc']),
  unit: z.string(),
  generatedAt: z.string(),
  pipelineVersion: z.string(),
  n: z.number(),
  rows: z.array(RankingRow),
});
export type Ranking = z.infer<typeof Ranking>;

export const RankingsIndexEntry = z.object({
  metric: RankingMetric,
  title: z.string(),
  file: z.string(),
  nCbsa: z.number(),
  generatedAt: z.string(),
});
export type RankingsIndexEntry = z.infer<typeof RankingsIndexEntry>;

export const RankingsIndex = z.object({
  generatedAt: z.string(),
  pipelineVersion: z.string(),
  files: z.array(RankingsIndexEntry),
});
export type RankingsIndex = z.infer<typeof RankingsIndex>;
