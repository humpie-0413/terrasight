import { Hono } from 'hono';
import type { EventPoint, TrustTag } from '@terrasight/schemas';
import type { Env } from '../index';

/**
 * FIRMS wildfire event proxy.
 *
 * Contract: `docs/datasets/normalized-contracts.md` §2a (event-collection envelope).
 * Cache policy: §5 — 10 minutes (FIRMS NRT is ~3h anyway).
 *
 * Landmines mirrored from `pipelines/connectors/firms.py`:
 *   - FIRMS returns 400 (NOT 401/403) on a bad MAP_KEY. Body contains
 *     "Invalid MAP_KEY". We do NOT rethrow — degrade gracefully.
 *   - `acq_time` is HHMM with no colon and often not zero-padded
 *     ("930" → 09:30). Pad before composing ISO-8601.
 *   - FIRMS `confidence` for VIIRS is the string enum n|l|h — map to
 *     full words for the human label, keep raw in properties.
 *   - The world/1 feed is ~30k+ rows in fire season. Parser runs in one
 *     pass — no regex split/join fan-out.
 *   - Longitude should be -180..180 but clamp defensively.
 */

const FIRMS_BASE = 'https://firms.modaps.eosdis.nasa.gov/api/area/csv';
const FIRMS_SOURCE_DATASET = 'VIIRS_SNPP_NRT';
const FIRMS_AREA = 'world';
const FIRMS_SOURCE_LABEL = 'NASA FIRMS';
const FIRMS_SOURCE_URL = 'https://firms.modaps.eosdis.nasa.gov/api/area/';
const FIRMS_CADENCE = 'NRT ~3h';
const FIRMS_TAG: TrustTag = 'near-real-time';

type FiresEnvelope = {
  status: 'ok' | 'error' | 'not_configured' | 'pending';
  source: string;
  source_url: string;
  cadence: string;
  tag: TrustTag;
  count: number;
  data: EventPoint[];
  notes: string[];
  message?: string;
};

export const fires = new Hono<{ Bindings: Env }>();

fires.get('/', async (c) => {
  // 1. Not configured → graceful 200. `docs/datasets/normalized-contracts.md` §6.
  if (!c.env.FIRMS_MAP_KEY) {
    const body: FiresEnvelope = {
      status: 'not_configured',
      source: FIRMS_SOURCE_LABEL,
      source_url: FIRMS_SOURCE_URL,
      cadence: FIRMS_CADENCE,
      tag: FIRMS_TAG,
      count: 0,
      data: [],
      notes: [],
      message: 'FIRMS_MAP_KEY not set',
    };
    return c.json(body, 200);
  }

  // 2. Parse + clamp params.
  const daysParam = Number.parseInt(c.req.query('days') ?? '1', 10);
  const days = Number.isFinite(daysParam) ? Math.max(1, Math.min(10, daysParam)) : 1;
  // bbox is intentionally ignored for the MVP — we always pull the world feed.
  // Parsing it here keeps the cache key stable across clients that send it.

  // 3. Cache lookup.
  const cacheKey = new Request(
    `https://terrasight-cache.internal/fires?days=${days}`,
    { method: 'GET' },
  );
  const cache = caches.default;
  const cached = await cache.match(cacheKey);
  if (cached) {
    return cached;
  }

  const ttl = Number.parseInt(c.env.CACHE_TTL_FIRES ?? '600', 10);
  const upstreamUrl = `${FIRMS_BASE}/${c.env.FIRMS_MAP_KEY}/${FIRMS_SOURCE_DATASET}/${FIRMS_AREA}/${days}`;

  let upstream: Response;
  try {
    upstream = await fetch(upstreamUrl);
  } catch (err) {
    const body: FiresEnvelope = {
      status: 'error',
      source: FIRMS_SOURCE_LABEL,
      source_url: FIRMS_SOURCE_URL,
      cadence: FIRMS_CADENCE,
      tag: FIRMS_TAG,
      count: 0,
      data: [],
      notes: [`transport error: ${(err as Error).message ?? 'unknown'}`],
    };
    return c.json(body, 200);
  }

  // 4. FIRMS returns 400 on bad MAP_KEY — graceful degradation, not 502.
  if (upstream.status === 400) {
    const bodyText = await upstream.text();
    const note = bodyText.includes('Invalid MAP_KEY')
      ? 'Invalid MAP_KEY'
      : `upstream 400: ${bodyText.slice(0, 200)}`;
    const body: FiresEnvelope = {
      status: 'error',
      source: FIRMS_SOURCE_LABEL,
      source_url: FIRMS_SOURCE_URL,
      cadence: FIRMS_CADENCE,
      tag: FIRMS_TAG,
      count: 0,
      data: [],
      notes: [note],
    };
    return c.json(body, 200);
  }

  if (!upstream.ok) {
    const body: FiresEnvelope = {
      status: 'error',
      source: FIRMS_SOURCE_LABEL,
      source_url: FIRMS_SOURCE_URL,
      cadence: FIRMS_CADENCE,
      tag: FIRMS_TAG,
      count: 0,
      data: [],
      notes: [`upstream status ${upstream.status}`],
    };
    return c.json(body, 200);
  }

  const csvText = await upstream.text();
  const data = parseFirmsCsv(csvText);

  const body: FiresEnvelope = {
    status: 'ok',
    source: FIRMS_SOURCE_LABEL,
    source_url: FIRMS_SOURCE_URL,
    cadence: FIRMS_CADENCE,
    tag: FIRMS_TAG,
    count: data.length,
    data,
    notes: [],
  };

  const response = new Response(JSON.stringify(body), {
    status: 200,
    headers: {
      'content-type': 'application/json; charset=utf-8',
      'cache-control': `public, max-age=${ttl}`,
    },
  });

  c.executionCtx.waitUntil(cache.put(cacheKey, response.clone()));
  return response;
});

// ---------------------------------------------------------------------------
// CSV parsing — zero external deps. FIRMS CSV has no embedded commas or
// quoted fields (verified 2026-04-11 spike), so a naive split is safe.
// ---------------------------------------------------------------------------

const CONFIDENCE_MAP: Record<string, string> = {
  n: 'nominal',
  l: 'low',
  h: 'high',
};

function parseFirmsCsv(raw: string): EventPoint[] {
  if (!raw) return [];
  const lines = raw.split(/\r?\n/);
  if (lines.length < 2) return [];
  const header = lines[0]!.split(',').map((h) => h.trim());
  const idx = (name: string) => header.indexOf(name);
  const iLat = idx('latitude');
  const iLon = idx('longitude');
  const iBright = idx('bright_ti4');
  const iScan = idx('scan');
  const iTrack = idx('track');
  const iDate = idx('acq_date');
  const iTime = idx('acq_time');
  const iConf = idx('confidence');
  const iFrp = idx('frp');
  const iDN = idx('daynight');
  if (iLat < 0 || iLon < 0 || iDate < 0 || iTime < 0) {
    // Header doesn't look like FIRMS — treat as empty, not error.
    return [];
  }

  const out: EventPoint[] = [];
  for (let i = 1; i < lines.length; i++) {
    const line = lines[i];
    if (!line) continue;
    const parts = line.split(',');
    const latRaw = Number.parseFloat(parts[iLat] ?? '');
    const lonRaw = Number.parseFloat(parts[iLon] ?? '');
    if (!Number.isFinite(latRaw) || !Number.isFinite(lonRaw)) continue;
    const lat = clampLat(latRaw);
    const lon = clampLon(lonRaw);
    const frp = safeFloat(parts[iFrp]);
    const confidenceRaw = (parts[iConf] ?? '').trim();
    const confidenceWord = CONFIDENCE_MAP[confidenceRaw.toLowerCase()] ?? confidenceRaw ?? 'unknown';
    const acqDate = (parts[iDate] ?? '').trim();
    const acqTime = padTime((parts[iTime] ?? '').trim());
    const observedAt = `${acqDate}T${acqTime.slice(0, 2)}:${acqTime.slice(2, 4)}:00Z`;

    const ev: EventPoint = {
      id: stableId(lat, lon, acqDate, acqTime),
      type: 'wildfire',
      lat,
      lon,
      observedAt,
      severity: frp,
      label: `FRP ${frp.toFixed(1)} MW \u00b7 ${confidenceWord}`,
      properties: {
        brightness: safeFloat(parts[iBright]),
        daynight: (parts[iDN] ?? '').trim(),
        confidence_raw: confidenceRaw,
        scan: safeFloat(parts[iScan]),
        track: safeFloat(parts[iTrack]),
      },
    };
    out.push(ev);
  }
  return out;
}

function clampLat(v: number): number {
  return Math.max(-90, Math.min(90, v));
}

function clampLon(v: number): number {
  if (v >= -180 && v <= 180) return v;
  return ((v + 180) % 360 + 360) % 360 - 180;
}

function safeFloat(s: string | undefined): number {
  if (!s) return 0;
  const n = Number.parseFloat(s);
  return Number.isFinite(n) ? n : 0;
}

function padTime(hhmm: string): string {
  if (!hhmm) return '0000';
  return hhmm.padStart(4, '0');
}

/**
 * Stable 16-hex-char id derived from (lat,lon,acq_date,acq_time).
 * Matches the Python connector's hash so the same fire has the same id
 * whether normalized in batch or at the edge. Using FNV-1a 64-bit here
 * because Workers don't ship SubtleCrypto.sha1 for synchronous paths and
 * the only requirement is "stable per record".
 */
function stableId(lat: number, lon: number, acqDate: string, acqTime: string): string {
  const key = `${lat}|${lon}|${acqDate}|${acqTime}`;
  // FNV-1a 64-bit, split into two 32-bit halves for portability.
  let h1 = 0x811c9dc5;
  let h2 = 0x811c9dc5;
  for (let i = 0; i < key.length; i++) {
    const c = key.charCodeAt(i);
    h1 = Math.imul(h1 ^ (c & 0xff), 0x01000193);
    h2 = Math.imul(h2 ^ ((c >> 8) & 0xff), 0x01000193);
  }
  const hex1 = (h1 >>> 0).toString(16).padStart(8, '0');
  const hex2 = (h2 >>> 0).toString(16).padStart(8, '0');
  return `${hex1}${hex2}`;
}
