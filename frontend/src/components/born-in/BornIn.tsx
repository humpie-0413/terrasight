/**
 * Born-in Interactive — birth year vs now comparison.
 * CO₂ / Global Temp Anomaly / Arctic Sea Ice.
 *
 * Record constraints (applied by backend):
 *   CO₂ before 1958  → clamped to 1958 (Mauna Loa record start)
 *   Sea ice before 1979 → clamped to 1979 (NSIDC record start)
 */
import { useState, KeyboardEvent } from 'react';

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? '/api';

// ─── Types ────────────────────────────────────────────────────────────────────

interface BornInPoint {
  date: string;
  value: number;
}

interface BornInIndicator {
  id: string;
  label: string;
  unit: string;
  record_start: number;
  birth_year_used: number;
  clamped: boolean;
  then: BornInPoint;
  now: BornInPoint;
  delta_abs: number;
  delta_pct: number | null;
  error?: string;
}

interface BornInResult {
  year: number;
  indicators: BornInIndicator[];
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function formatValue(id: string, val: number): string {
  if (id === 'co2') return val.toFixed(1);
  if (id === 'temp') return (val >= 0 ? '+' : '') + val.toFixed(2);
  return val.toFixed(2);
}

function deltaColor(id: string, delta: number): string {
  // For all three indicators, the "bad" direction is positive delta for co2/temp,
  // and negative delta for sea-ice.
  const bad = id === 'sea-ice' ? delta < 0 : delta > 0;
  return bad ? '#dc2626' : '#16a34a';
}

function deltaSign(delta: number): string {
  return delta >= 0 ? '+' : '';
}

// ─── IndicatorCard ────────────────────────────────────────────────────────────

function IndicatorCard({ ind, birthYear }: { ind: BornInIndicator; birthYear: number }) {
  if (ind.error) {
    return (
      <div style={cardStyle}>
        <div style={cardLabelStyle}>{ind.label}</div>
        <div style={{ color: '#ef4444', fontSize: '12px' }}>Unavailable: {ind.error}</div>
      </div>
    );
  }

  const clampNote =
    ind.clamped && ind.birth_year_used !== birthYear
      ? `Record starts ${ind.record_start} — using ${ind.birth_year_used}`
      : null;

  const dColor = deltaColor(ind.id, ind.delta_abs);

  return (
    <div style={cardStyle}>
      <div style={cardLabelStyle}>{ind.label}</div>

      <div style={rowStyle}>
        <div style={colStyle}>
          <div style={colHeadStyle}>In {ind.birth_year_used}</div>
          <div style={valueStyle}>{formatValue(ind.id, ind.then.value)}</div>
          <div style={unitStyle}>{ind.unit}</div>
        </div>
        <div style={arrowStyle}>→</div>
        <div style={colStyle}>
          <div style={colHeadStyle}>Now ({ind.now.date})</div>
          <div style={valueStyle}>{formatValue(ind.id, ind.now.value)}</div>
          <div style={unitStyle}>{ind.unit}</div>
        </div>
      </div>

      <div style={{ ...deltaStyle, color: dColor }}>
        {deltaSign(ind.delta_abs)}
        {formatValue(ind.id, ind.delta_abs)} {ind.unit}
        {ind.delta_pct !== null && (
          <span style={{ marginLeft: '4px', fontSize: '11px' }}>
            ({deltaSign(ind.delta_pct)}{ind.delta_pct}%)
          </span>
        )}
      </div>

      {clampNote && <div style={clampNoteStyle}>{clampNote}</div>}
    </div>
  );
}

// ─── BornIn ───────────────────────────────────────────────────────────────────

export default function BornIn() {
  const [inputYear, setInputYear] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<BornInResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const currentYear = new Date().getFullYear();

  async function handleCompare() {
    const y = parseInt(inputYear, 10);
    if (!y || y < 1850 || y > currentYear) {
      setError(`Enter a year between 1850 and ${currentYear}.`);
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetch(`${API_BASE}/trends/born-in?year=${y}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: BornInResult = await res.json();
      setResult(data);
    } catch (e) {
      setError(`Failed to load data: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter') handleCompare();
  }

  return (
    <section id="born-in" style={sectionStyle}>
      <div style={innerStyle}>
        <div style={labelStyle}>Born in…?</div>
        <h2 style={h2Style}>See how Earth changed in your lifetime</h2>
        <p style={bodyStyle}>
          Enter your birth year to compare CO₂ concentration, global
          temperature, and Arctic sea ice extent from then to now.
        </p>

        <div style={inputRowStyle}>
          <input
            type="number"
            placeholder="e.g. 1990"
            min={1850}
            max={currentYear}
            value={inputYear}
            onChange={(e) => setInputYear(e.target.value)}
            onKeyDown={handleKeyDown}
            style={inputStyle}
            aria-label="Birth year"
          />
          <button
            type="button"
            onClick={handleCompare}
            disabled={loading}
            style={loading ? { ...btnStyle, ...btnActiveStyle } : btnStyle}
          >
            {loading ? 'Loading…' : 'Compare →'}
          </button>
        </div>

        {error && <p style={errorStyle}>{error}</p>}

        {result && (
          <div style={cardsRowStyle}>
            {result.indicators.map((ind) => (
              <IndicatorCard key={ind.id} ind={ind} birthYear={result.year} />
            ))}
          </div>
        )}

        <p style={noteStyle}>
          Data records start: CO₂ 1958 · Temperature 1850 · Sea ice 1979
        </p>
      </div>
    </section>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const sectionStyle: React.CSSProperties = {
  padding: '40px 24px',
  borderTop: '1px solid rgba(51, 65, 85, 0.5)',
  background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.8) 0%, rgba(30, 41, 59, 0.6) 100%)',
};

const innerStyle: React.CSSProperties = {
  maxWidth: '680px',
  margin: '0 auto',
  textAlign: 'center',
};

const labelStyle: React.CSSProperties = {
  fontSize: '11px',
  textTransform: 'uppercase',
  letterSpacing: '0.1em',
  color: '#60a5fa',
  fontWeight: 600,
  marginBottom: '8px',
};

const h2Style: React.CSSProperties = {
  margin: '0 0 10px',
  fontSize: '22px',
  color: '#f1f5f9',
};

const bodyStyle: React.CSSProperties = {
  margin: '0 0 20px',
  fontSize: '14px',
  color: '#94a3b8',
  lineHeight: 1.6,
};

const inputRowStyle: React.CSSProperties = {
  display: 'flex',
  gap: '8px',
  justifyContent: 'center',
  alignItems: 'center',
  flexWrap: 'wrap',
};

const inputStyle: React.CSSProperties = {
  padding: '8px 12px',
  fontSize: '15px',
  border: '1px solid rgba(51, 65, 85, 0.5)',
  borderRadius: '6px',
  width: '120px',
  background: 'rgba(15, 23, 42, 0.8)',
  color: '#f1f5f9',
  fontFamily: 'system-ui, sans-serif',
  outline: 'none',
};

const btnStyle: React.CSSProperties = {
  padding: '8px 18px',
  fontSize: '14px',
  fontWeight: 600,
  background: '#0369a1',
  color: '#fff',
  border: 'none',
  borderRadius: '6px',
  cursor: 'pointer',
  fontFamily: 'system-ui, sans-serif',
};

const btnActiveStyle: React.CSSProperties = {
  background: '#0284c7',
  cursor: 'wait',
};

const errorStyle: React.CSSProperties = {
  marginTop: '10px',
  fontSize: '13px',
  color: '#dc2626',
};

const cardsRowStyle: React.CSSProperties = {
  display: 'flex',
  gap: '12px',
  marginTop: '24px',
  justifyContent: 'center',
  flexWrap: 'wrap',
  textAlign: 'left',
};

const cardStyle: React.CSSProperties = {
  background: 'rgba(15, 23, 42, 0.6)',
  border: '1px solid rgba(51, 65, 85, 0.5)',
  borderRadius: '8px',
  padding: '14px 16px',
  minWidth: '170px',
  flex: '1 1 170px',
  maxWidth: '220px',
  boxShadow: '0 1px 3px rgba(0,0,0,0.3)',
  backdropFilter: 'blur(8px)',
};

const cardLabelStyle: React.CSSProperties = {
  fontSize: '11px',
  fontWeight: 700,
  color: '#60a5fa',
  textTransform: 'uppercase',
  letterSpacing: '0.05em',
  marginBottom: '10px',
};

const rowStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '8px',
  marginBottom: '10px',
};

const colStyle: React.CSSProperties = {
  flex: 1,
};

const colHeadStyle: React.CSSProperties = {
  fontSize: '10px',
  color: '#64748b',
  marginBottom: '2px',
};

const valueStyle: React.CSSProperties = {
  fontSize: '18px',
  fontWeight: 700,
  color: '#f1f5f9',
  lineHeight: 1.1,
};

const unitStyle: React.CSSProperties = {
  fontSize: '10px',
  color: '#64748b',
  marginTop: '1px',
};

const arrowStyle: React.CSSProperties = {
  fontSize: '16px',
  color: '#94a3b8',
  flexShrink: 0,
};

const deltaStyle: React.CSSProperties = {
  fontSize: '13px',
  fontWeight: 700,
  padding: '4px 0',
  borderTop: '1px solid rgba(51, 65, 85, 0.5)',
};

const clampNoteStyle: React.CSSProperties = {
  marginTop: '6px',
  fontSize: '10px',
  color: '#64748b',
  fontStyle: 'italic',
};

const noteStyle: React.CSSProperties = {
  marginTop: '20px',
  fontSize: '12px',
  color: '#64748b',
};
