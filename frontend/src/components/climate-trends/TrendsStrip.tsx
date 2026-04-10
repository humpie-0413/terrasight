import MetaLine from '../common/MetaLine';
import { TrustTag } from '../../utils/trustTags';
import { useApi } from '../../hooks/useApi';

/**
 * Climate Trends strip — 3 cards: CO2, Global Temp Anomaly, Arctic Sea Ice.
 * CLAUDE.md Block 1층 "Climate Trends (느린 변화 카드 3개)"
 *
 * CO₂ card is wired to real data from /api/trends/co2 (NOAA GML Mauna Loa).
 * Temp and Sea Ice cards remain placeholders until their connectors land.
 */

interface TrendPoint {
  date: string;
  value: number;
}

interface Co2Response {
  id: 'co2';
  source: string;
  source_url: string;
  cadence: string;
  tag: string;
  record_start: string;
  unit: string;
  latest: { date: string; value: number } | null;
  series: TrendPoint[];
}

export default function TrendsStrip() {
  const co2 = useApi<Co2Response>('/trends/co2');

  return (
    <section id="climate-trends" style={sectionStyle}>
      <article style={cardStyle}>
        <MetaLine
          cadence="Monthly"
          tag={TrustTag.Observed}
          source="NOAA GML Mauna Loa"
          sourceUrl="https://gml.noaa.gov/ccgg/trends/"
        />
        <h3 style={titleStyle}>CO₂</h3>
        {co2.loading && <p style={loadingStyle}>Loading…</p>}
        {co2.error && <p style={errorStyle}>Unable to load CO₂ data.</p>}
        {co2.data?.latest && (
          <>
            <p style={valueStyle}>
              {co2.data.latest.value.toFixed(2)}{' '}
              <span style={unitStyle}>ppm</span>
            </p>
            <p style={asOfStyle}>as of {co2.data.latest.date}</p>
            <Sparkline points={co2.data.series} />
          </>
        )}
      </article>

      <article style={cardStyle}>
        <MetaLine
          cadence="Monthly (preliminary)"
          tag={TrustTag.NearRealTime}
          source="NOAA Climate at a Glance"
          sourceUrl="https://www.ncei.noaa.gov/access/monitoring/climate-at-a-glance/"
        />
        <h3 style={titleStyle}>Global Temp Anomaly</h3>
        <p style={placeholderStyle}>— °C</p>
        {/* TODO: sparkline since 1880 */}
      </article>

      <article style={cardStyle}>
        <MetaLine
          cadence="Daily (5-day running mean)"
          tag={TrustTag.Observed}
          source="NSIDC Sea Ice Index"
          sourceUrl="https://nsidc.org/data/seaice_index"
        />
        <h3 style={titleStyle}>Arctic Sea Ice</h3>
        <p style={placeholderStyle}>— million km²</p>
        {/* TODO: sparkline since 1979 */}
      </article>
    </section>
  );
}

/**
 * Tiny inline SVG sparkline — no chart library yet, keeps bundle lean.
 * Expects a series of { date, value } sorted ascending.
 */
function Sparkline({ points }: { points: TrendPoint[] }) {
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
      aria-label="CO₂ 12-month sparkline"
      style={{ display: 'block', marginTop: '8px' }}
    >
      <path
        d={path}
        fill="none"
        stroke="#0f766e"
        strokeWidth={1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

const sectionStyle: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(3, 1fr)',
  gap: '16px',
  padding: '16px 24px',
};

const cardStyle: React.CSSProperties = {
  padding: '16px',
  border: '1px solid #e5e7eb',
  borderRadius: '8px',
  background: '#fff',
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

const placeholderStyle: React.CSSProperties = {
  margin: '8px 0 0',
  fontSize: '20px',
  color: '#cbd5e1',
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
