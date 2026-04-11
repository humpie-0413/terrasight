import MetaLine from '../common/MetaLine';
import { TrustTag } from '../../utils/trustTags';
import { useApi } from '../../hooks/useApi';

/**
 * Climate Trends strip — 3 cards: CO2, Global Temp Anomaly, Arctic Sea Ice.
 * CLAUDE.md Block 1층 "Climate Trends (느린 변화 카드 3개)".
 *
 * One request to GET /api/trends fans out to all three connectors on the
 * backend in parallel, so a single useApi call drives the whole strip.
 */

interface TrendPoint {
  date: string;
  value: number;
}

interface TrendIndicator {
  id: 'co2' | 'temp' | 'sea-ice' | 'ch4' | 'sea-level';
  label: string;
  unit: string;
  source: string;
  source_url: string;
  cadence: string;
  tag: string;
  record_start: string;
  latest: { date: string; value: number; window?: string } | null;
  series: TrendPoint[];
  baseline?: string;
  error?: string;
}

interface TrendsResponse {
  indicators: TrendIndicator[];
}

const ORDER: Array<TrendIndicator['id']> = ['co2', 'temp', 'sea-ice', 'ch4', 'sea-level'];

export default function TrendsStrip() {
  const { data, loading, error } = useApi<TrendsResponse>('/trends');

  // Keep deterministic CO₂ → Temp → Sea Ice order regardless of backend ordering.
  const byId = new Map<TrendIndicator['id'], TrendIndicator>(
    data?.indicators.map((i) => [i.id, i]) ?? [],
  );

  return (
    <section id="climate-trends" style={sectionStyle}>
      {ORDER.map((id) => (
        <TrendCard
          key={id}
          id={id}
          indicator={byId.get(id)}
          loading={loading}
          error={error}
        />
      ))}
    </section>
  );
}

function TrendCard({
  id,
  indicator,
  loading,
  error,
}: {
  id: TrendIndicator['id'];
  indicator: TrendIndicator | undefined;
  loading: boolean;
  error: Error | null;
}) {
  const meta = STATIC_META[id];

  return (
    <article style={cardStyle}>
      <MetaLine
        cadence={meta.cadence}
        tag={meta.tag}
        source={meta.source}
        sourceUrl={meta.sourceUrl}
      />
      <h3 style={titleStyle}>{meta.title}</h3>

      {loading && <p style={loadingStyle}>Loading…</p>}
      {!loading && error && <p style={errorStyle}>Unable to load data.</p>}
      {!loading && indicator?.error && (
        <p style={errorStyle}>Unable to load data.</p>
      )}
      {!loading && indicator && !indicator.error && indicator.latest && (
        <>
          <p style={valueStyle}>
            {formatValue(indicator.latest.value, id)}{' '}
            <span style={unitStyle}>{indicator.unit}</span>
          </p>
          <p style={asOfStyle}>
            as of {indicator.latest.date}
            {indicator.latest.window ? ` · ${indicator.latest.window}` : ''}
            {indicator.baseline ? ` · baseline ${indicator.baseline}` : ''}
          </p>
          <Sparkline points={indicator.series} strokeColor={meta.sparkColor} />
        </>
      )}
    </article>
  );
}

function formatValue(value: number, id: TrendIndicator['id']): string {
  if (id === 'temp') {
    const sign = value >= 0 ? '+' : '';
    return `${sign}${value.toFixed(2)}`;
  }
  if (id === 'sea-level') {
    const sign = value >= 0 ? '+' : '';
    return `${sign}${value.toFixed(1)}`;
  }
  if (id === 'ch4') return value.toFixed(1);
  return value.toFixed(2);
}

/**
 * Tiny inline SVG sparkline — no chart library yet, keeps bundle lean.
 * Expects a series of { date, value } sorted ascending.
 */
function Sparkline({
  points,
  strokeColor,
}: {
  points: TrendPoint[];
  strokeColor: string;
}) {
  if (points.length < 2) return null;

  const width = 220;
  const height = 48;
  const padding = 4;

  const values = points.map((p) => p.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;

  const stepX = (width - padding * 2) / (points.length - 1);
  const coords = points.map((p, i) => {
    const x = padding + i * stepX;
    const y = padding + (1 - (p.value - min) / range) * (height - padding * 2);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  const path = `M ${coords.join(' L ')}`;

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label="12-month sparkline"
      style={{ display: 'block', marginTop: '8px' }}
    >
      <path
        d={path}
        fill="none"
        stroke={strokeColor}
        strokeWidth={1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/**
 * Static per-card metadata. The backend ships the same strings, but rendering
 * them from a local table lets the MetaLine paint even during the initial
 * loading state so the trust signalling is visible from the first frame.
 */
const STATIC_META: Record<
  TrendIndicator['id'],
  {
    title: string;
    cadence: string;
    tag: TrustTag;
    source: string;
    sourceUrl: string;
    sparkColor: string;
  }
> = {
  co2: {
    title: 'CO₂',
    cadence: 'Monthly',
    tag: TrustTag.Observed,
    source: 'NOAA GML Mauna Loa',
    sourceUrl: 'https://gml.noaa.gov/ccgg/trends/',
    sparkColor: '#0f766e',
  },
  temp: {
    title: 'Global Temp Anomaly',
    cadence: 'Monthly (preliminary)',
    tag: TrustTag.NearRealTime,
    source: 'NOAA Global Temperature',
    sourceUrl:
      'https://www.ncei.noaa.gov/products/land-based-station/noaa-global-temp',
    sparkColor: '#b91c1c',
  },
  'sea-ice': {
    title: 'Arctic Sea Ice',
    cadence: 'Daily (5-day running mean)',
    tag: TrustTag.Observed,
    source: 'NSIDC Sea Ice Index',
    sourceUrl: 'https://nsidc.org/data/seaice_index',
    sparkColor: '#1d4ed8',
  },
  ch4: {
    title: 'CH₄ (Methane)',
    cadence: 'Monthly',
    tag: TrustTag.Observed,
    source: 'NOAA GML Global CH₄',
    sourceUrl: 'https://gml.noaa.gov/ccgg/trends/ch4/',
    sparkColor: '#d97706',
  },
  'sea-level': {
    title: 'Sea Level Rise',
    cadence: '~10-day',
    tag: TrustTag.Observed,
    source: 'NOAA NESDIS GMSL',
    sourceUrl: 'https://www.star.nesdis.noaa.gov/socd/lsa/SeaLevelRise/',
    sparkColor: '#2563eb',
  },
};

const sectionStyle: React.CSSProperties = {
  display: 'flex',
  gap: '14px',
  padding: '16px 24px',
  overflowX: 'auto',
  scrollSnapType: 'x mandatory',
  WebkitOverflowScrolling: 'touch',
};

const cardStyle: React.CSSProperties = {
  padding: '16px',
  border: '1px solid #e5e7eb',
  borderRadius: '8px',
  background: '#fff',
  minWidth: '200px',
  flexShrink: 0,
  scrollSnapAlign: 'start',
};

const titleStyle: React.CSSProperties = {
  margin: '8px 0 4px',
  fontSize: '14px',
  color: '#334155',
  fontWeight: 600,
};

const valueStyle: React.CSSProperties = {
  margin: 0,
  fontSize: '28px',
  fontWeight: 700,
  color: '#0f172a',
  lineHeight: 1.1,
};

const unitStyle: React.CSSProperties = {
  fontSize: '14px',
  fontWeight: 500,
  color: '#64748b',
};

const asOfStyle: React.CSSProperties = {
  margin: '2px 0 0',
  fontSize: '11px',
  color: '#94a3b8',
};

const loadingStyle: React.CSSProperties = {
  margin: '8px 0 0',
  fontSize: '13px',
  color: '#94a3b8',
};

const errorStyle: React.CSSProperties = {
  margin: '8px 0 0',
  fontSize: '13px',
  color: '#dc2626',
};
