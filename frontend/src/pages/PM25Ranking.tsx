import { Link } from 'react-router-dom';
import { useApi } from '../hooks/useApi';

interface PM25Row {
  slug: string;
  name: string;
  state: string | null;
  pm25_aqi: number | null;
  pm25_category: string | null;
  reporting_area: string | null;
  observed_at: string | null;
  status: string;
  error?: string;
}

interface PM25RankingResponse {
  slug: string;
  title: string;
  criterion?: string;
  note?: string;
  retrieved_date?: string;
  source?: string;
  source_url?: string;
  status?: string;
  message?: string;
  rows: PM25Row[];
}

function aqiColors(category: string | null): { bg: string; text: string } {
  switch (category) {
    case 'Good': return { bg: '#00e400', text: '#064e3b' };
    case 'Moderate': return { bg: '#ffff00', text: '#713f12' };
    case 'Unhealthy for Sensitive Groups': return { bg: '#ff7e00', text: '#fff' };
    case 'Unhealthy': return { bg: '#ff0000', text: '#fff' };
    case 'Very Unhealthy': return { bg: '#8f3f97', text: '#fff' };
    case 'Hazardous': return { bg: '#7e0023', text: '#fff' };
    default: return { bg: '#e2e8f0', text: '#374151' };
  }
}

export default function PM25Ranking() {
  const { data, loading, error } = useApi<PM25RankingResponse>('/rankings/pm25');

  return (
    <main style={pageStyle}>
      <div style={breadcrumbStyle}>
        <Link to="/" style={breadcrumbLinkStyle}>Home</Link>
        <span style={sep}>›</span>
        <span>Rankings</span>
        <span style={sep}>›</span>
        <span>PM2.5 Levels</span>
      </div>

      <h1 style={h1Style}>U.S. Metros by Current PM2.5 Levels</h1>
      <p style={subtitleStyle}>
        Real-time PM2.5 air quality index from AirNow monitoring stations, sorted highest
        to lowest. PM2.5 (fine particulate matter ≤ 2.5 µm) is the pollutant most strongly
        linked to cardiovascular and respiratory health effects.
      </p>

      {loading && (
        <div style={loadingStyle}>
          <p>Loading AirNow PM2.5 data for all metros…</p>
        </div>
      )}

      {error && (
        <div style={errorBoxStyle}>
          <strong>Failed to load ranking:</strong> {error.message}
        </div>
      )}

      {data?.status === 'not_configured' && (
        <div style={warnBoxStyle}>
          <strong>AirNow API key not configured.</strong>
          <p style={{ margin: '8px 0 0', fontSize: '13px' }}>{data.message}</p>
        </div>
      )}

      {data && data.status !== 'not_configured' && (
        <>
          {data.note && (
            <div style={noteBoxStyle}>
              <strong>Note:</strong> {data.note}
            </div>
          )}

          <table style={tableStyle}>
            <thead>
              <tr>
                <th style={thStyle}>#</th>
                <th style={{ ...thStyle, textAlign: 'left' }}>Metro</th>
                <th style={thStyle}>PM2.5 AQI</th>
                <th style={thStyle}>Category</th>
                <th style={{ ...thStyle, textAlign: 'left' }}>Reporting Area</th>
                <th style={thStyle}>Report</th>
              </tr>
            </thead>
            <tbody>
              {data.rows.map((row, i) => {
                const colors = aqiColors(row.pm25_category);
                return (
                  <tr key={row.slug} style={i % 2 === 0 ? rowEven : rowOdd}>
                    <td style={tdCenter}>{row.status === 'ok' ? i + 1 : '—'}</td>
                    <td style={tdName}>
                      <span style={metroNameStyle}>{row.name}</span>
                      {row.state && <span style={stateStyle}>{row.state}</span>}
                    </td>
                    <td style={tdCenter}>
                      {row.pm25_aqi != null
                        ? <strong>{row.pm25_aqi}</strong>
                        : <span style={naStyle}>—</span>}
                    </td>
                    <td style={tdCenter}>
                      {row.pm25_category ? (
                        <span style={{
                          display: 'inline-block',
                          padding: '2px 8px',
                          borderRadius: '4px',
                          background: colors.bg,
                          color: colors.text,
                          fontSize: '12px',
                          fontWeight: 600,
                          whiteSpace: 'nowrap',
                        }}>
                          {row.pm25_category}
                        </span>
                      ) : <span style={naStyle}>—</span>}
                    </td>
                    <td style={tdLeft}>
                      {row.reporting_area ?? <span style={naStyle}>—</span>}
                    </td>
                    <td style={tdCenter}>
                      <Link to={`/reports/${row.slug}`} style={reportLinkStyle}>View →</Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>

          {data.retrieved_date && (
            <div style={footerStyle}>
              <p style={sourceLineStyle}>
                Source:{' '}
                {data.source_url ? (
                  <a href={data.source_url} target="_blank" rel="noopener noreferrer" style={extLinkStyle}>
                    {data.source}
                  </a>
                ) : data.source}
                {' · '}real-time observational data{' · '}
                Retrieved {data.retrieved_date}
              </p>
              <p style={disclaimerStyle}>
                PM2.5 values reflect the most recent hourly AirNow observation for each
                metro's representative ZIP code. Reporting area boundaries ≠ CBSA
                boundaries. For official air quality advisories, visit{' '}
                <a href="https://www.airnow.gov" target="_blank" rel="noopener noreferrer" style={extLinkStyle}>
                  airnow.gov
                </a>.
              </p>
            </div>
          )}
        </>
      )}
    </main>
  );
}

const pageStyle: React.CSSProperties = { maxWidth: '960px', margin: '0 auto', padding: '24px' };
const breadcrumbStyle: React.CSSProperties = { display: 'flex', gap: '6px', alignItems: 'center', fontSize: '13px', color: '#64748b', marginBottom: '20px' };
const breadcrumbLinkStyle: React.CSSProperties = { color: '#2563eb', textDecoration: 'none' };
const sep: React.CSSProperties = { color: '#94a3b8' };
const h1Style: React.CSSProperties = { margin: '0 0 8px', fontSize: '26px', color: '#0f172a' };
const subtitleStyle: React.CSSProperties = { margin: '0 0 20px', fontSize: '14px', color: '#475569', lineHeight: 1.6 };
const loadingStyle: React.CSSProperties = { padding: '24px', background: '#f8fafc', borderRadius: '8px', color: '#64748b', fontSize: '14px' };
const errorBoxStyle: React.CSSProperties = { padding: '16px', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: '8px', color: '#b91c1c', fontSize: '14px' };
const warnBoxStyle: React.CSSProperties = { padding: '16px', background: '#fffbeb', border: '1px solid #fde68a', borderRadius: '8px', color: '#92400e', fontSize: '14px' };
const noteBoxStyle: React.CSSProperties = { padding: '12px 16px', background: '#fffbeb', border: '1px solid #fde68a', borderRadius: '6px', fontSize: '13px', color: '#92400e', marginBottom: '20px' };
const tableStyle: React.CSSProperties = { width: '100%', borderCollapse: 'collapse', fontSize: '14px' };
const thStyle: React.CSSProperties = { padding: '10px 12px', background: '#f1f5f9', borderBottom: '2px solid #e2e8f0', fontWeight: 600, color: '#374151', textAlign: 'center', whiteSpace: 'nowrap' };
const rowEven: React.CSSProperties = { background: '#fff' };
const rowOdd: React.CSSProperties = { background: '#f8fafc' };
const tdCenter: React.CSSProperties = { padding: '10px 12px', textAlign: 'center', borderBottom: '1px solid #e2e8f0', color: '#374151' };
const tdLeft: React.CSSProperties = { padding: '10px 12px', borderBottom: '1px solid #e2e8f0', color: '#374151', fontSize: '13px' };
const tdName: React.CSSProperties = { padding: '10px 12px', borderBottom: '1px solid #e2e8f0' };
const metroNameStyle: React.CSSProperties = { fontWeight: 500, color: '#0f172a', display: 'block' };
const stateStyle: React.CSSProperties = { fontSize: '12px', color: '#64748b' };
const naStyle: React.CSSProperties = { color: '#94a3b8', fontSize: '12px' };
const reportLinkStyle: React.CSSProperties = { color: '#2563eb', textDecoration: 'none', fontSize: '13px', fontWeight: 500 };
const footerStyle: React.CSSProperties = { marginTop: '24px', paddingTop: '16px', borderTop: '1px solid #e5e7eb' };
const sourceLineStyle: React.CSSProperties = { margin: '0 0 8px', fontSize: '12px', color: '#64748b' };
const extLinkStyle: React.CSSProperties = { color: '#2563eb' };
const disclaimerStyle: React.CSSProperties = { margin: 0, fontSize: '12px', color: '#94a3b8', fontStyle: 'italic' };
