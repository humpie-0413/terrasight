/**
 * NOAA OISST point-query proxy route — `/api/sst-point`.
 *
 * Envelope: scalar-point (see `docs/datasets/normalized-contracts.md` §2b).
 * Cache TTL: `CACHE_TTL_SST_POINT` (default 3600s; daily cadence upstream).
 *
 * Step-2 landmines enforced here:
 * (a) ERDDAP longitude is 0-360 — we wrap on the way out and UNWRAP the
 *     snapped `longitude` column on the way back so the browser always
 *     sees -180..180 (contract §3).
 * (b) `zlev=(0.0)` is mandatory — the griddap var signature is
 *     `sst[time][zlev][lat][lon]`. Omitting `[(0.0)]` yields a 400.
 * (c) Land / ice cells return JSON `null` in `rows[0]`'s sst column.
 *     We map to `status: 'no_data'` (NOT `error`) per §2b so the UI
 *     renders "Location is land or ice" instead of an error toast.
 * (d) `ncdcOisst21NrtAgg` is the NRT aggregate (~1-day lag). Final
 *     aggregate is `ncdcOisst21Agg` (~14-day lag, not used on Globe).
 */

import { Hono } from 'hono';
import type { Env } from '../index';

const ERDDAP_BASE =
  'https://coastwatch.pfeg.noaa.gov/erddap/griddap/ncdcOisst21NrtAgg';

const SOURCE_LABEL = 'NOAA OISST v2.1';
const CADENCE_LABEL = 'daily';
const TRUST_TAG = 'observed' as const;

// ERDDAP 0.25° grid extent (user-side lon in -180..180).
const LAT_MIN = -89.875;
const LAT_MAX = 89.875;
const LON_MIN = -179.875;
const LON_MAX = 179.875;

type OkEnvelope = {
  status: 'ok';
  source: string;
  source_url: string;
  cadence: string;
  tag: typeof TRUST_TAG;
  lat: number;
  lon: number;
  snappedLat: number;
  snappedLon: number;
  sst_c: number;
  observed_at: string;
  message: null;
};

type NoDataEnvelope = {
  status: 'no_data';
  source: string;
  source_url: string;
  cadence: string;
  tag: typeof TRUST_TAG;
  lat: number;
  lon: number;
  snappedLat: number | null;
  snappedLon: number | null;
  sst_c: null;
  observed_at: string | null;
  message: string;
};

type ErrorEnvelope = {
  status: 'error';
  source: string;
  source_url: string;
  cadence: string;
  tag: typeof TRUST_TAG;
  lat: number | null;
  lon: number | null;
  sst_c: null;
  message: string;
};

type SstEnvelope = OkEnvelope | NoDataEnvelope | ErrorEnvelope;

type ErddapResponse = {
  table: {
    columnNames: string[];
    columnTypes?: string[];
    columnUnits?: string[];
    rows: Array<Array<string | number | null>>;
  };
};

function wrapLon(lon: number): number {
  return lon < 0 ? lon + 360 : lon;
}

function unwrapLon(lon360: number): number {
  return lon360 > 180 ? lon360 - 360 : lon360;
}

function buildErddapUrl(lat: number, lon: number): string {
  const lon360 = wrapLon(lon);
  // `sst[last][(0.0)][(lat)][(lon360)]` — ERDDAP snap-to-nearest-centre
  // uses parentheses around the decimal value.
  return `${ERDDAP_BASE}.json?sst[last][(0.0)][(${lat})][(${lon360})]`;
}

export const sstPoint = new Hono<{ Bindings: Env }>();

sstPoint.get('/', async (c) => {
  const latStr = c.req.query('lat');
  const lonStr = c.req.query('lon');
  if (!latStr || !lonStr) {
    return c.json(
      {
        status: 'error',
        source: SOURCE_LABEL,
        source_url: ERDDAP_BASE,
        cadence: CADENCE_LABEL,
        tag: TRUST_TAG,
        lat: null,
        lon: null,
        sst_c: null,
        message: 'lat and lon query params are required',
      } satisfies ErrorEnvelope,
      400,
    );
  }

  const lat = Number(latStr);
  const lon = Number(lonStr);
  if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
    return c.json(
      {
        status: 'error',
        source: SOURCE_LABEL,
        source_url: ERDDAP_BASE,
        cadence: CADENCE_LABEL,
        tag: TRUST_TAG,
        lat: null,
        lon: null,
        sst_c: null,
        message: 'lat and lon must be finite numbers',
      } satisfies ErrorEnvelope,
      400,
    );
  }

  if (lat < LAT_MIN || lat > LAT_MAX || lon < LON_MIN || lon > LON_MAX) {
    return c.json(
      {
        status: 'error',
        source: SOURCE_LABEL,
        source_url: ERDDAP_BASE,
        cadence: CADENCE_LABEL,
        tag: TRUST_TAG,
        lat,
        lon,
        sst_c: null,
        message: 'lat/lon out of range',
      } satisfies ErrorEnvelope,
      400,
    );
  }

  // Cache lookup. Use a stable, normalized key rounded to ~110 m (3 dp).
  // We wrap the key in an HTTPS URL string so Cloudflare's Cache API is
  // happy with its Request-keyed contract.
  const cacheKeyUrl = new URL(c.req.url);
  cacheKeyUrl.pathname = '/api/sst-point';
  cacheKeyUrl.search = `?key=sst:${lat.toFixed(3)}:${lon.toFixed(3)}`;
  const cacheKey = new Request(cacheKeyUrl.toString(), { method: 'GET' });
  const cache = caches.default;

  const cached = await cache.match(cacheKey);
  if (cached) {
    return new Response(cached.body, {
      status: cached.status,
      headers: cached.headers,
    });
  }

  const url = buildErddapUrl(lat, lon);
  let upstream: Response;
  try {
    upstream = await fetch(url, {
      headers: { Accept: 'application/json' },
      cf: {
        cacheTtl: Number(c.env.CACHE_TTL_SST_POINT) || 3600,
        cacheEverything: true,
      },
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    const body: ErrorEnvelope = {
      status: 'error',
      source: SOURCE_LABEL,
      source_url: ERDDAP_BASE,
      cadence: CADENCE_LABEL,
      tag: TRUST_TAG,
      lat,
      lon,
      sst_c: null,
      message: `ERDDAP fetch failed: ${message}`,
    };
    return c.json(body, 200); // graceful — never 5xx from Worker.
  }

  if (!upstream.ok) {
    const body: ErrorEnvelope = {
      status: 'error',
      source: SOURCE_LABEL,
      source_url: ERDDAP_BASE,
      cadence: CADENCE_LABEL,
      tag: TRUST_TAG,
      lat,
      lon,
      sst_c: null,
      message: `ERDDAP HTTP ${upstream.status}`,
    };
    return c.json(body, 200);
  }

  let parsed: ErddapResponse;
  try {
    parsed = (await upstream.json()) as ErddapResponse;
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    const body: ErrorEnvelope = {
      status: 'error',
      source: SOURCE_LABEL,
      source_url: ERDDAP_BASE,
      cadence: CADENCE_LABEL,
      tag: TRUST_TAG,
      lat,
      lon,
      sst_c: null,
      message: `ERDDAP parse failed: ${message}`,
    };
    return c.json(body, 200);
  }

  const rows = parsed?.table?.rows;
  const columnNames = parsed?.table?.columnNames;
  if (!Array.isArray(rows) || !Array.isArray(columnNames) || rows.length === 0) {
    const body: NoDataEnvelope = {
      status: 'no_data',
      source: SOURCE_LABEL,
      source_url: ERDDAP_BASE,
      cadence: CADENCE_LABEL,
      tag: TRUST_TAG,
      lat,
      lon,
      snappedLat: null,
      snappedLon: null,
      sst_c: null,
      observed_at: null,
      message: 'ERDDAP returned no rows for this location.',
    };
    return c.json(body, 200);
  }

  const colIdx: Record<string, number> = {};
  columnNames.forEach((name, i) => {
    colIdx[name] = i;
  });
  const row = rows[0];
  const sstCell = row?.[colIdx['sst']];
  const timeCell = row?.[colIdx['time']];
  const snappedLatCell = row?.[colIdx['latitude']];
  const snappedLonCell = row?.[colIdx['longitude']];

  // Landmine (c) — JSON null means land / ice.
  if (sstCell === null || sstCell === undefined) {
    const body: NoDataEnvelope = {
      status: 'no_data',
      source: SOURCE_LABEL,
      source_url: ERDDAP_BASE,
      cadence: CADENCE_LABEL,
      tag: TRUST_TAG,
      lat,
      lon,
      snappedLat: typeof snappedLatCell === 'number' ? snappedLatCell : null,
      snappedLon:
        typeof snappedLonCell === 'number' ? unwrapLon(snappedLonCell) : null,
      sst_c: null,
      observed_at: typeof timeCell === 'string' ? timeCell : null,
      message: 'Location is land or ice.',
    };
    return c.json(body, 200);
  }

  const sst_c = typeof sstCell === 'number' ? sstCell : Number(sstCell);
  const snappedLat =
    typeof snappedLatCell === 'number' ? snappedLatCell : Number(snappedLatCell);
  const snappedLon360 =
    typeof snappedLonCell === 'number' ? snappedLonCell : Number(snappedLonCell);
  if (!Number.isFinite(sst_c) || !Number.isFinite(snappedLat) || !Number.isFinite(snappedLon360)) {
    const body: ErrorEnvelope = {
      status: 'error',
      source: SOURCE_LABEL,
      source_url: ERDDAP_BASE,
      cadence: CADENCE_LABEL,
      tag: TRUST_TAG,
      lat,
      lon,
      sst_c: null,
      message: 'ERDDAP returned non-numeric cells.',
    };
    return c.json(body, 200);
  }

  const body: OkEnvelope = {
    status: 'ok',
    source: SOURCE_LABEL,
    source_url: ERDDAP_BASE,
    cadence: CADENCE_LABEL,
    tag: TRUST_TAG,
    lat,
    lon,
    snappedLat,
    snappedLon: unwrapLon(snappedLon360),
    sst_c,
    observed_at: typeof timeCell === 'string' ? timeCell : String(timeCell),
    message: null,
  };

  const ttl = Number(c.env.CACHE_TTL_SST_POINT) || 3600;
  const response = new Response(JSON.stringify(body satisfies SstEnvelope), {
    status: 200,
    headers: {
      'content-type': 'application/json; charset=UTF-8',
      'cache-control': `public, max-age=${ttl}`,
    },
  });
  // Only cache `ok` responses — errors and no_data could be transient.
  c.executionCtx.waitUntil(cache.put(cacheKey, response.clone()));
  return response;
});
