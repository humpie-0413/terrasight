/**
 * USGS earthquake summary-feed proxy route.
 *
 * Upstream:  https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_<period>.geojson
 * Cache key: `earthquakes:period=<p>:minMag=<m>`
 * TTL:       `env.CACHE_TTL_EARTHQUAKES` seconds (default 300)
 *
 * Landmines enforced in the normalizer (mirror of `pipelines/connectors/usgs.py`):
 *   1. `properties.time` is ms since epoch, not seconds.
 *   2. `geometry.coordinates` is `[lon, lat, depth_km]`.
 *   3. Features with `mag: null` are filtered out.
 *   4. Non-`earthquake` seismic events (quarry blast, rockburst, ...) are
 *      kept under `type: "earthquake"` per the frozen EventPoint contract
 *      but their original USGS `type` is preserved as `properties.event_type`.
 */
import { Hono } from 'hono';
import type { EventPoint, TrustTag } from '@terrasight/schemas';
import type { Env } from '../index';

export const earthquakes = new Hono<{ Bindings: Env }>();

const VALID_PERIODS = ['day', 'hour', 'week', 'month'] as const;
type Period = (typeof VALID_PERIODS)[number];

type EnvelopeStatus = 'ok' | 'error' | 'not_configured' | 'pending';

interface EventCollectionEnvelope {
  status: EnvelopeStatus;
  source: string;
  source_url: string;
  cadence: string;
  tag: TrustTag;
  count: number;
  data: EventPoint[];
  notes: string[];
}

interface UsgsFeature {
  id?: string;
  properties?: {
    mag?: number | null;
    place?: string | null;
    time?: number | null;
    url?: string | null;
    tsunami?: number | null;
    felt?: number | null;
    sig?: number | null;
    status?: string | null;
    type?: string | null;
  } | null;
  geometry?: {
    coordinates?: [number, number, number] | number[] | null;
  } | null;
}

interface UsgsFeatureCollection {
  type?: string;
  features?: UsgsFeature[] | null;
}

function classifySeverity(mag: number): string {
  if (mag >= 6.0) return 'major';
  if (mag >= 4.5) return 'moderate';
  if (mag >= 2.5) return 'light';
  return 'micro';
}

function truncateLabel(text: string, limit = 80): string {
  if (text.length <= limit) return text;
  return text.slice(0, Math.max(0, limit - 1)).trimEnd() + '\u2026';
}

function parsePeriod(raw: string | undefined): Period {
  if (raw && (VALID_PERIODS as readonly string[]).includes(raw)) {
    return raw as Period;
  }
  return 'day';
}

function parseMinMagnitude(raw: string | undefined): number {
  if (!raw) return 0;
  const n = Number.parseFloat(raw);
  return Number.isFinite(n) ? n : 0;
}

function feedUrl(period: Period): string {
  return `https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_${period}.geojson`;
}

function normalize(
  raw: UsgsFeatureCollection,
  minMagnitude: number,
): { data: EventPoint[]; filteredNullMag: number } {
  const features = raw.features ?? [];
  const out: EventPoint[] = [];
  let filteredNullMag = 0;

  for (const feat of features) {
    const props = feat?.properties ?? null;
    const coords = feat?.geometry?.coordinates ?? null;

    const magRaw = props?.mag;
    if (magRaw === null || magRaw === undefined) {
      // Landmine #3: analyst-pending events — filter.
      filteredNullMag++;
      continue;
    }
    const mag = typeof magRaw === 'number' ? magRaw : Number.parseFloat(String(magRaw));
    if (!Number.isFinite(mag)) {
      filteredNullMag++;
      continue;
    }

    // Worker-level minimum magnitude filter (in addition to the null filter).
    if (mag < minMagnitude) continue;

    if (!Array.isArray(coords) || coords.length < 2) continue;
    // Landmine #2: coordinates are [lon, lat, depth_km].
    const lon = Number(coords[0]);
    const lat = Number(coords[1]);
    const depthKm = coords.length > 2 ? Number(coords[2]) : 0;
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) continue;

    const timeMs = props?.time;
    if (timeMs === null || timeMs === undefined) continue;
    // Landmine #1: `time` is ms since epoch, not seconds.
    const observedDate = new Date(Number(timeMs));
    if (Number.isNaN(observedDate.getTime())) continue;
    const observedAt = observedDate.toISOString();

    const featureId = feat?.id;
    if (!featureId) continue;

    const place = (props?.place ?? '').toString().trim();
    const label = truncateLabel(place ? `M${mag.toFixed(1)} \u2014 ${place}` : `M${mag.toFixed(1)}`);

    // Landmine #4: preserve USGS event_type separately.
    const eventType = (props?.type ?? 'earthquake').toString();

    const point: EventPoint = {
      id: String(featureId),
      type: 'earthquake',
      lat,
      lon,
      observedAt,
      severity: mag,
      label,
      properties: {
        depth_km: Number.isFinite(depthKm) ? depthKm : 0,
        url: (props?.url ?? '').toString(),
        tsunami: Number(props?.tsunami ?? 0) || 0,
        felt: props?.felt ?? null,
        sig: props?.sig ?? null,
        status: (props?.status ?? '').toString(),
        severity_class: classifySeverity(mag),
        event_type: eventType,
      },
    };
    out.push(point);
  }

  return { data: out, filteredNullMag };
}

earthquakes.get('/', async (c) => {
  const period = parsePeriod(c.req.query('period'));
  const minMagnitude = parseMinMagnitude(c.req.query('minMagnitude'));
  const upstreamUrl = feedUrl(period);

  const ttl = Number.parseInt(c.env.CACHE_TTL_EARTHQUAKES ?? '300', 10) || 300;
  const cache = caches.default;

  // Cache key per normalized-contracts §5 policy.
  const cacheKeyUrl = new URL(c.req.url);
  cacheKeyUrl.search = `period=${period}&minMag=${minMagnitude}`;
  const cacheKey = new Request(cacheKeyUrl.toString(), { method: 'GET' });

  const cached = await cache.match(cacheKey);
  if (cached) {
    return cached;
  }

  const commonMeta = {
    source: 'USGS Earthquake',
    source_url: upstreamUrl,
    cadence: '5 min',
    tag: 'observed' as TrustTag,
  };

  let upstreamRes: Response;
  try {
    upstreamRes = await fetch(upstreamUrl, {
      headers: { Accept: 'application/geo+json, application/json' },
    });
  } catch (err) {
    const errEnvelope: EventCollectionEnvelope = {
      status: 'error',
      ...commonMeta,
      count: 0,
      data: [],
      notes: [`Upstream fetch failed: ${(err as Error).message ?? 'unknown'}`],
    };
    return c.json(errEnvelope);
  }

  if (!upstreamRes.ok) {
    const errEnvelope: EventCollectionEnvelope = {
      status: 'error',
      ...commonMeta,
      count: 0,
      data: [],
      notes: [`Upstream returned HTTP ${upstreamRes.status}`],
    };
    return c.json(errEnvelope);
  }

  let raw: UsgsFeatureCollection;
  try {
    raw = (await upstreamRes.json()) as UsgsFeatureCollection;
  } catch (err) {
    const errEnvelope: EventCollectionEnvelope = {
      status: 'error',
      ...commonMeta,
      count: 0,
      data: [],
      notes: [`Upstream JSON parse failed: ${(err as Error).message ?? 'unknown'}`],
    };
    return c.json(errEnvelope);
  }

  const { data, filteredNullMag } = normalize(raw, minMagnitude);

  const notes: string[] = [];
  if (filteredNullMag > 0) {
    notes.push(
      `Filtered ${filteredNullMag} analyst-pending feature(s) with mag=null.`,
    );
  }

  const envelope: EventCollectionEnvelope = {
    status: 'ok',
    ...commonMeta,
    count: data.length,
    data,
    notes,
  };

  const response = c.json(envelope);
  response.headers.set('Cache-Control', `public, max-age=${ttl}`);

  c.executionCtx.waitUntil(cache.put(cacheKey, response.clone()));
  return response;
});
