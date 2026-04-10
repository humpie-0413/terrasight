/**
 * Born-in Interactive — P1 (viral feature).
 * P0 ships a placeholder UI only. Full data fetch + comparison is deferred.
 *
 * Spec (CLAUDE.md):
 *   Birth year → CO₂ / global temp / sea ice then vs now comparison.
 *   Data start-point auto-correction:
 *     CO₂ before 1958 → "1958 (record start)"
 *     Sea ice before 1979 → "1979 (record start)"
 */
export default function BornIn() {
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
            min={1900}
            max={new Date().getFullYear()}
            disabled
            style={inputStyle}
          />
          <button type="button" disabled style={btnStyle}>
            Compare →
          </button>
          <span style={comingSoonStyle}>Coming soon (P1)</span>
        </div>
        <p style={noteStyle}>
          Data records start: CO₂ 1958 · Temperature 1850 · Sea ice 1979
        </p>
      </div>
    </section>
  );
}

const sectionStyle: React.CSSProperties = {
  padding: '40px 24px',
  borderTop: '1px solid #e5e7eb',
  background: 'linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%)',
};
const innerStyle: React.CSSProperties = {
  maxWidth: '560px',
  margin: '0 auto',
  textAlign: 'center',
};
const labelStyle: React.CSSProperties = {
  fontSize: '11px',
  textTransform: 'uppercase',
  letterSpacing: '0.1em',
  color: '#0369a1',
  fontWeight: 600,
  marginBottom: '8px',
};
const h2Style: React.CSSProperties = {
  margin: '0 0 10px',
  fontSize: '22px',
  color: '#0c4a6e',
};
const bodyStyle: React.CSSProperties = {
  margin: '0 0 20px',
  fontSize: '14px',
  color: '#0369a1',
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
  border: '1px solid #bae6fd',
  borderRadius: '6px',
  width: '120px',
  background: '#f0f9ff',
  color: '#64748b',
  fontFamily: 'system-ui, sans-serif',
};
const btnStyle: React.CSSProperties = {
  padding: '8px 16px',
  fontSize: '14px',
  fontWeight: 600,
  background: '#e2e8f0',
  color: '#94a3b8',
  border: 'none',
  borderRadius: '6px',
  cursor: 'not-allowed',
  fontFamily: 'system-ui, sans-serif',
};
const comingSoonStyle: React.CSSProperties = {
  fontSize: '12px',
  color: '#0369a1',
  fontStyle: 'italic',
};
const noteStyle: React.CSSProperties = {
  marginTop: '14px',
  fontSize: '12px',
  color: '#0369a1',
  opacity: 0.75,
};
