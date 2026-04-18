import { Hono } from 'hono';
import { cors } from 'hono/cors';
import { fires } from './routes/fires';
import { earthquakes } from './routes/earthquakes';
import { sstPoint } from './routes/sst-point';

export interface Env {
  FIRMS_MAP_KEY?: string;
  CACHE_TTL_FIRES: string;
  CACHE_TTL_EARTHQUAKES: string;
  CACHE_TTL_SST_POINT: string;
}

const app = new Hono<{ Bindings: Env }>();

// CORS — Pages (prod + preview aliases) and local dev origins. These are
// read-only proxies of public NASA/USGS/NOAA data so we don't need credentials.
// Without this, browser fetches from terrasight.pages.dev to
// terrasight-worker.*.workers.dev are blocked and /api/* calls fail silently.
app.use(
  '/api/*',
  cors({
    origin: (origin) => {
      if (!origin) return origin;
      if (/^https:\/\/([a-z0-9-]+\.)?terrasight\.pages\.dev$/.test(origin)) return origin;
      if (/^https?:\/\/localhost(:\d+)?$/.test(origin)) return origin;
      if (/^https?:\/\/127\.0\.0\.1(:\d+)?$/.test(origin)) return origin;
      return null;
    },
    allowMethods: ['GET', 'OPTIONS'],
    maxAge: 600,
  }),
);

app.get('/health', (c) => c.json({ status: 'ok', service: 'terrasight-worker' }));

app.route('/api/fires', fires);
app.route('/api/earthquakes', earthquakes);
app.route('/api/sst-point', sstPoint);

app.notFound((c) => c.json({ status: 'error', message: 'Not found' }, 404));

export default app;
