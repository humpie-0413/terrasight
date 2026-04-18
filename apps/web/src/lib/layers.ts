// -----------------------------------------------------------------------------
// Globe layer manifest (Step 6 Task 1).
//
// Mirrors `docs/datasets/gibs-approved-layers.md` — this file is the TypeScript
// source of truth for the Globe island. Any edits here MUST be reflected in
// that doc (and vice versa).
//
// Landmines to remember:
//   • NEVER use `VIIRS_SNPP_DayNightBand_ENCC` (frozen 2023-07-07). Use the
//     non-ENCC id `VIIRS_SNPP_DayNightBand`.
//   • UI label for BlueMarble is "Natural Earth" (NOT "Blue Marble" — brand).
//   • AOD UI label is "Aerosol Proxy (AOD)" (NOT "PM2.5").
//   • Date format for GIBS is `YYYY-MM-DD`. `T00:00:00Z` ISO → HTTP 400.
//   • BlueMarble path uses the literal segment `default/default/...` (no date).
// -----------------------------------------------------------------------------

import type { TrustTag } from '@terrasight/schemas';

export interface ImageryLayerDef {
  id: string;
  title: string; // UI label
  source: string; // human-readable source
  sourceUrl: string;
  trustTag: TrustTag;
  cadence: 'daily' | 'monthly' | 'static';
  coverage: 'global' | 'ocean-only';
  urlTemplate: string; // GIBS REST template with {Time}, {TileMatrix}, {TileRow}, {TileCol}
  tileMatrixSet: string;
  ext: 'jpg' | 'png';
  dateMode: 'static' | 'daily'; // static → 'default' literal; daily → YYYY-MM-DD
  legend?: { unit: string; min: number; max: number; colormap: string };
  clickPolicy: 'none' | 'sst-point' | 'info-only';
  caveat: string; // one-line caveat (for Legend)
  caveats: string[]; // full caveat list
  isBase: boolean; // true for BlueMarble only
}

export interface EventLayerDef {
  id: 'fires' | 'earthquakes';
  title: string;
  source: string;
  sourceUrl: string;
  trustTag: TrustTag;
  cadence: string;
  apiPath: string; // '/api/fires' or '/api/earthquakes'
  refreshSeconds: number; // how often to refetch
  caveat: string;
}

export const IMAGERY_LAYERS: ImageryLayerDef[] = [
  // -------------------------------------------------------------------------
  // BlueMarble — base layer, always on. Static monthly composite, no date.
  // UI label MUST be "Natural Earth" (Blue Marble is a brand name).
  // -------------------------------------------------------------------------
  {
    id: 'BlueMarble_ShadedRelief_Bathymetry',
    title: 'Natural Earth',
    source: 'NASA GIBS / Blue Marble',
    sourceUrl: 'https://gibs.earthdata.nasa.gov/',
    trustTag: 'observed',
    cadence: 'monthly',
    coverage: 'global',
    urlTemplate:
      'https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/BlueMarble_ShadedRelief_Bathymetry/default/default/500m/{TileMatrix}/{TileRow}/{TileCol}.jpg',
    tileMatrixSet: '500m',
    ext: 'jpg',
    dateMode: 'static',
    clickPolicy: 'none',
    caveat: 'Monthly composite — not real-time.',
    caveats: [
      'Monthly composite — not real-time.',
      'UI label is "Natural Earth"; do not use "Blue Marble" (brand).',
    ],
    isBase: true,
  },
  // -------------------------------------------------------------------------
  // Sea Surface Temperature — GHRSST L4 MUR (NASA JPL). Click handler uses
  // NOAA OISST v2.1 via /api/sst-point (Worker). Ocean-only coverage.
  // -------------------------------------------------------------------------
  {
    id: 'GHRSST_L4_MUR_Sea_Surface_Temperature',
    title: 'Sea Surface Temperature',
    source: 'NASA JPL MUR GHRSST L4 via GIBS',
    sourceUrl: 'https://gibs.earthdata.nasa.gov/',
    trustTag: 'near-real-time',
    cadence: 'daily',
    coverage: 'ocean-only',
    urlTemplate:
      'https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/GHRSST_L4_MUR_Sea_Surface_Temperature/default/{Time}/1km/{TileMatrix}/{TileRow}/{TileCol}.png',
    tileMatrixSet: '1km',
    ext: 'png',
    dateMode: 'daily',
    legend: {
      unit: '\u00B0C',
      min: -2,
      max: 35,
      colormap: 'GHRSST_L4_MUR_Sea_Surface_Temperature',
    },
    clickPolicy: 'sst-point',
    caveat: '1-day latency (NRT). Polar regions interpolated.',
    caveats: [
      '1-day latency (NRT).',
      'Polar regions interpolated.',
      'Click value is OISST (NOAA) via Worker — not GIBS tile RGB.',
    ],
    isBase: false,
  },
  // -------------------------------------------------------------------------
  // Aerosol Optical Depth — MODIS Terra. UI label MUST be "Aerosol Proxy
  // (AOD)". Never label or interpret as PM2.5 (column-integrated quantity).
  // -------------------------------------------------------------------------
  {
    id: 'MODIS_Terra_Aerosol',
    title: 'Aerosol Proxy (AOD)',
    source: 'MODIS Terra — NASA GSFC via GIBS',
    sourceUrl: 'https://gibs.earthdata.nasa.gov/',
    trustTag: 'near-real-time',
    cadence: 'daily',
    coverage: 'global',
    urlTemplate:
      'https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/MODIS_Terra_Aerosol/default/{Time}/2km/{TileMatrix}/{TileRow}/{TileCol}.png',
    tileMatrixSet: '2km',
    ext: 'png',
    dateMode: 'daily',
    legend: {
      unit: 'AOD (unitless)',
      min: 0,
      max: 1,
      colormap: 'MODIS_Terra_Aerosol',
    },
    clickPolicy: 'info-only',
    caveat: 'Column-integrated aerosol optical depth — not PM2.5.',
    caveats: [
      'AOD = column-integrated aerosol optical depth (total atmospheric column).',
      'Do NOT interpret as PM2.5 or air-quality index.',
      'Land + ocean combined product.',
    ],
    isBase: false,
  },
  // -------------------------------------------------------------------------
  // Cloud Fraction Day — MODIS Aqua.
  // -------------------------------------------------------------------------
  {
    id: 'MODIS_Aqua_Cloud_Fraction_Day',
    title: 'Cloud Fraction (Day)',
    source: 'MODIS Aqua — NASA GSFC via GIBS',
    sourceUrl: 'https://gibs.earthdata.nasa.gov/',
    trustTag: 'near-real-time',
    cadence: 'daily',
    coverage: 'global',
    urlTemplate:
      'https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/MODIS_Aqua_Cloud_Fraction_Day/default/{Time}/2km/{TileMatrix}/{TileRow}/{TileCol}.png',
    tileMatrixSet: '2km',
    ext: 'png',
    dateMode: 'daily',
    legend: {
      unit: 'fraction (0\u20131)',
      min: 0,
      max: 1,
      colormap: 'MODIS_Aqua_Cloud_Fraction_Day',
    },
    clickPolicy: 'info-only',
    caveat: 'Day-only pass — no nighttime coverage.',
    caveats: [
      'Day-only pass (Aqua afternoon orbit).',
      'Nighttime coverage: none.',
    ],
    isBase: false,
  },
  // -------------------------------------------------------------------------
  // Night Lights — VIIRS Suomi NPP Day/Night Band (NON-ENCC).
  // IMPORTANT: do NOT use `VIIRS_SNPP_DayNightBand_ENCC` (frozen 2023-07-07).
  // No numeric legend — Legend will gracefully degrade to "no scale".
  // -------------------------------------------------------------------------
  {
    id: 'VIIRS_SNPP_DayNightBand',
    title: 'Night Lights',
    source: 'VIIRS Suomi NPP Day/Night Band via GIBS',
    sourceUrl: 'https://gibs.earthdata.nasa.gov/',
    trustTag: 'near-real-time',
    cadence: 'daily',
    coverage: 'global',
    urlTemplate:
      'https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/VIIRS_SNPP_DayNightBand/default/{Time}/1km/{TileMatrix}/{TileRow}/{TileCol}.png',
    tileMatrixSet: '1km',
    ext: 'png',
    dateMode: 'daily',
    clickPolicy: 'info-only',
    caveat: 'Human activity proxy — not a direct electricity measurement.',
    caveats: [
      'Labeled as "human activity proxy" — not direct electricity consumption.',
      'Raw radiance — no atmospheric correction.',
      'Glare over ocean/ice cells can mimic human activity.',
    ],
    isBase: false,
  },
];

export const EVENT_LAYERS: EventLayerDef[] = [
  {
    id: 'fires',
    title: 'Wildfires (VIIRS FIRMS)',
    source: 'NASA FIRMS',
    sourceUrl: 'https://firms.modaps.eosdis.nasa.gov/',
    trustTag: 'near-real-time',
    cadence: 'NRT ~3h',
    apiPath: '/api/fires',
    refreshSeconds: 600, // 10 min — matches Worker cache TTL
    caveat: '~3h NRT latency. Global feed, filtered client-side.',
  },
  {
    id: 'earthquakes',
    title: 'Earthquakes (USGS)',
    source: 'USGS Earthquake Feed',
    sourceUrl: 'https://earthquake.usgs.gov/',
    trustTag: 'observed',
    cadence: '~5 min',
    apiPath: '/api/earthquakes',
    refreshSeconds: 300, // 5 min
    caveat: 'Analyst-pending events (mag=null) filtered.',
  },
];

// -----------------------------------------------------------------------------
// Helpers
// -----------------------------------------------------------------------------

/**
 * Returns the yesterday UTC date string in YYYY-MM-DD format.
 *
 * GIBS daily tiles may not be published yet for today's UTC date (NRT latency
 * ~1 day). Using yesterday avoids tile-missing-404s on fresh UTC-midnight
 * builds — conservative default for Step 6.
 */
export function yesterdayISO(): string {
  const now = new Date();
  const y = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate() - 1));
  const yyyy = y.getUTCFullYear();
  const mm = String(y.getUTCMonth() + 1).padStart(2, '0');
  const dd = String(y.getUTCDate()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd}`;
}

/**
 * Returns the date string to substitute for {Time} in a GIBS tile URL template:
 * - `static` dateMode → literal `default` (BlueMarble and other static layers)
 * - `daily` dateMode → YYYY-MM-DD (yesterday UTC)
 */
export function gibsDateStr(def: ImageryLayerDef): string {
  return def.dateMode === 'static' ? 'default' : yesterdayISO();
}
