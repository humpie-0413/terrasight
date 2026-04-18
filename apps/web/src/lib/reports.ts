/**
 * Pure TypeScript helpers for the /reports frontend.
 *
 * This module intentionally has zero Astro / React dependencies so it can
 * be imported from frontmatter (.astro), React islands, and build scripts
 * alike. All exported functions return plain JSON-serializable values.
 *
 * The canonical schema lives in `@terrasight/schemas`; consult `CoreBlockId`
 * / `OptionalBlockId` there for the frozen block-id vocabulary.
 */

import type {
  CityReport,
  ReportBlock,
  CoreBlockId,
  OptionalBlockId,
} from '@terrasight/schemas';

/**
 * The 8 frozen core report block ids, in the canonical report display
 * order. A `CityReport.blocks[]` array always contains exactly these 8
 * ids, optionally followed by 0-3 embeddable optional blocks.
 *
 * Frozen by docs/reports/report-block-policy.md and the Zod enum
 * `CoreBlockId` in `packages/schemas/src/index.ts`.
 */
export const CORE_BLOCK_IDS = [
  'air_quality',
  'climate_locally',
  'hazards_disasters',
  'water',
  'industrial_emissions',
  'site_cleanup',
  'population_exposure',
  'methodology',
] as const satisfies readonly CoreBlockId[];

/**
 * The 3 optional block ids that this renderer layer embeds inline in the
 * main report column. The other 2 optional ids (`city_comparison`,
 * `related_cities`) are rendered by purpose-built Agent 2 components and
 * must NOT be dispatched through `BlockRenderer`.
 *
 * Keep in sync with `components/reports/index.ts::EMBEDDABLE_OPTIONAL_BLOCK_IDS`.
 */
export const EMBEDDABLE_OPTIONAL_IDS = [
  'pfas_monitoring',
  'coastal_conditions',
  'disaster_history_detailed',
] as const satisfies readonly OptionalBlockId[];

type CoreId = (typeof CORE_BLOCK_IDS)[number];
type EmbeddableOptionalId = (typeof EMBEDDABLE_OPTIONAL_IDS)[number];

export interface PartitionedBlocks {
  /** 7 core blocks in their original `blocks[]` order, methodology excluded. */
  coreBlocks: ReportBlock[];
  /** Embeddable optional blocks that passed the availability gate. */
  embeddedOptionals: ReportBlock[];
  /** Methodology block — always present, always last in rendered output. */
  methodology: ReportBlock | null;
}

const CORE_ID_SET: ReadonlySet<string> = new Set(CORE_BLOCK_IDS);
const EMBEDDABLE_ID_SET: ReadonlySet<string> = new Set(EMBEDDABLE_OPTIONAL_IDS);

/**
 * Split `report.blocks[]` into the three rendering groups:
 *  - `coreBlocks`: the 7 non-methodology core blocks (original order preserved)
 *  - `embeddedOptionals`: the embeddable optionals whose availability map
 *     entry === 'included' (the Methodology column renders these inline)
 *  - `methodology`: the single methodology core block, to be rendered last
 *
 * Unknown block ids are silently dropped (schema enforces the closed set,
 * but we defend against future drift). `city_comparison` and
 * `related_cities` never appear in `blocks[]` by pipeline policy, but if
 * they do we drop them here too — the UI inserts their dedicated
 * components in layout-specific places.
 */
export function partitionBlocks(report: CityReport): PartitionedBlocks {
  const coreBlocks: ReportBlock[] = [];
  const embeddedOptionals: ReportBlock[] = [];
  let methodology: ReportBlock | null = null;

  for (const block of report.blocks) {
    if (block.id === 'methodology') {
      methodology = block;
      continue;
    }
    if (CORE_ID_SET.has(block.id)) {
      coreBlocks.push(block);
      continue;
    }
    if (EMBEDDABLE_ID_SET.has(block.id)) {
      const key = block.id as EmbeddableOptionalId;
      if (report.meta.optionalAvailability[key] === 'included') {
        embeddedOptionals.push(block);
      }
      continue;
    }
    // city_comparison / related_cities / future ids: drop — rendered elsewhere.
  }

  return { coreBlocks, embeddedOptionals, methodology };
}

/**
 * Build a JSON-LD `Article` description for the report. Returns a plain
 * object safe to `JSON.stringify` into a `<script type="application/ld+json">`.
 *
 * `siteUrl` is optional — when absent (env var unset), emitted URLs are
 * relative. This mirrors Rule 7 (canonical-only-when-PUBLIC_SITE_URL-set).
 */
export function buildJsonLdArticle(
  report: CityReport,
  siteUrl?: string | null,
): Record<string, unknown> {
  const pageUrl = siteUrl
    ? `${trimTrailingSlash(siteUrl)}/reports/${report.slug}`
    : `/reports/${report.slug}`;
  const name = `${report.city} — Environmental Report`;

  return {
    '@context': 'https://schema.org',
    '@type': 'Article',
    headline: report.summary.headline,
    name,
    author: {
      '@type': 'Organization',
      name: 'TerraSight',
    },
    publisher: {
      '@type': 'Organization',
      name: 'TerraSight',
    },
    datePublished: report.meta.build.generatedAt,
    dateModified: report.meta.updatedAt,
    mainEntityOfPage: {
      '@type': 'WebPage',
      '@id': pageUrl,
    },
    about: {
      '@type': 'Place',
      name: report.city,
      address: {
        '@type': 'PostalAddress',
        addressRegion: report.region,
        addressCountry: report.country,
      },
    },
  };
}

/**
 * Build a `BreadcrumbList`: Home → Reports → City.
 */
export function buildJsonLdBreadcrumb(
  report: CityReport,
  siteUrl?: string | null,
): Record<string, unknown> {
  const base = siteUrl ? trimTrailingSlash(siteUrl) : '';
  return {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: [
      {
        '@type': 'ListItem',
        position: 1,
        name: 'Home',
        item: `${base}/`,
      },
      {
        '@type': 'ListItem',
        position: 2,
        name: 'City Reports',
        item: `${base}/reports`,
      },
      {
        '@type': 'ListItem',
        position: 3,
        name: report.city,
        item: `${base}/reports/${report.slug}`,
      },
    ],
  };
}

/**
 * Build a `Dataset` schema summarising up to 3 `status === 'ok'` blocks
 * from the report. Returns `null` if no core or embedded block has
 * actual data — callers must skip emitting the script in that case
 * (never emit an empty Dataset, per the page spec).
 */
export function buildJsonLdDataset(
  report: CityReport,
  siteUrl?: string | null,
): Record<string, unknown> | null {
  const okBlocks = report.blocks.filter((b) => b.status === 'ok' && b.id !== 'methodology');
  if (okBlocks.length === 0) return null;

  const base = siteUrl ? trimTrailingSlash(siteUrl) : '';
  const pageUrl = `${base}/reports/${report.slug}`;
  const topMetrics = okBlocks.slice(0, 3).map((b) => b.title).join(', ');

  return {
    '@context': 'https://schema.org',
    '@type': 'Dataset',
    name: `${report.city} environmental indicators`,
    description: `Environmental indicators for ${report.city} (CBSA ${report.cbsaCode}) — ${topMetrics}.`,
    url: pageUrl,
    creator: {
      '@type': 'Organization',
      name: 'TerraSight',
    },
    spatialCoverage: {
      '@type': 'Place',
      name: report.city,
      geo: {
        '@type': 'GeoCoordinates',
        latitude: report.lat,
        longitude: report.lon,
      },
    },
    dateModified: report.meta.updatedAt,
    variableMeasured: okBlocks.slice(0, 3).map((b) => ({
      '@type': 'PropertyValue',
      name: b.title,
      description: truncate(b.body, 240),
    })),
  };
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function trimTrailingSlash(u: string): string {
  return u.endsWith('/') ? u.slice(0, -1) : u;
}

function truncate(s: string, n: number): string {
  if (s.length <= n) return s;
  return `${s.slice(0, n - 1).trimEnd()}…`;
}
