import { Hono } from 'hono';
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

app.get('/health', (c) => c.json({ status: 'ok', service: 'terrasight-worker' }));

app.route('/api/fires', fires);
app.route('/api/earthquakes', earthquakes);
app.route('/api/sst-point', sstPoint);

app.notFound((c) => c.json({ status: 'error', message: 'Not found' }, 404));

export default app;
