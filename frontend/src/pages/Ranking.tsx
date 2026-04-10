import { Link } from 'react-router-dom';
import { useApi } from '../hooks/useApi';

interface RankingRow {
  slug: string;
  name: string;
  state: string | null;
  sampled_facilities: number | null;
  in_violation: number | null;
  violation_rate_pct: number | null;
  status: string;
  error?: string;
}

interface RankingResponse {
  slug: string;
  title: string;
  criterion: string;
  note: string;
  retrieved_date: string;
  source: string;
  source_url: string;
  tag: string;
  rows: RankingRow[];
}

export default function Ranking() {
  const { data, loading, error } = useApi<RankingResponse>('/rankings/epa-violations');

  return (
    <main style={pageStyle}>
      <div style={breadcrumbStyle}>
        <Link to="/" style={breadcrumbLinkStyle}>Home</Link>
        <span style={sep}>›</span>
        <span>Rankings</span>
      </div>

      <h1 style={h1Style}>U.S. Metros with Most EPA Violations (2025)</h1>
      <p style={subtitleStyle}>
        Facilities currently in violation of Clean Air Act or Clean Water Act per EPA ECHO
        regulatory compliance data. Sorted by violation count.
      </p>

      {loading && (
        <div style={loadingStyle}>
          <p>Loading ECHO data for all metros — this may take 30–60 seconds…</p>
        </div>
      )}

      {error && (
        <div style={errorBoxStyle}>
          <strong>Failed to load ranking:</strong> {error.message}
        </div>
      )}

      {data && (
        <>
          <div style={noteBoxStyle}>
            <strong>Note:</strong> {data.note}
          </div>

          <table style={tableStyle}>
            <thead>
              <tr>
                <th style={thStyle}>#</th>
                <th style={{ ...thStyle, textAlign: 'left' }}>Metro</th>
                <th style={thStyle}>Sampled</th>
                <th style={thStyle}>In Violation</th>
                <th style={thStyle}>Rate</th>
                <th style={thStyle}>Report</th>
              </tr>
            </thead>
            <tbody>
              {data.rows.map((row, i) => (
                <tr key={row.slug} style={i % 2 === 0 ? rowEven : rowOdd}>
                  <td style={tdCenter}>
                    {row.status === 'ok' ? i + 1 : '—'}
                  </td>
                  <td style={tdName}>
                    <span style={metroNameStyle}>{row.name}</span>
                    {row.state && <span style={stateStyle}>{row.state}</span>}
                  </td>
                  <td style={tdCenter}>
                    {row.sampled_facilities != null
                      ? row.sampled_facilities.toLocaleString()
                      : <span style={naStyle}>error</span>}
                  </td>
                  <td style={tdCenter}>
                    {row.in_violation != null ? (
                      <strong style={
                        (row.in_violation ?? 0) > 10 ? violHighStyle : violLowStyle
                      }>
                        {row.in_violation}
                      </strong>
                    ) : <span style={naStyle}>—</span>}
                  </td>
                  <td style={tdCenter}>
                    {row.violation_rate_pct != null
                      ? `${row.violation_rate_pct}%`
                      : '—'}
                  </td>
                  <td style={tdCenter}>
                    <Link to={`/reports/${row.slug}`} style={reportLinkStyle}>
                      View →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div style={footerStyle}>
            <p style={sourceLineStyle}>
              Source:{' '}
              <a href={data.source_url} target="_blank" rel="noopener noreferrer" style={extLinkStyle}>
                {data.source}
              </a>
              {' · '}regulatory compliance data{' · '}
              Retrieved {data.retrieved_date}
            </p>
            <p style={disclaimerStyle}>
              Regulatory compliance ≠ environmental exposure or health risk.
              Violation counts reflect a sample of up to 500 active facilities per metro bounding box —
              not a complete census. Educational use only.
            </p>
          </div>
        </>
      )}
    </main>
  );
}

const pageStyle: React.CSSProperties = {
  maxWidth: '960px',
  margin: '0 auto',
  padding: '24px',
};
const breadcrumbStyle: React.CSSProperties = {
  display: 'flex',
  gap: '6px',
  alignItems: 'center',
  fontSize: '13px',
  color: '#64748b',
  marginBottom: '20px',
};
const breadcrumbLinkStyle: React.CSSProperties = {
  color: '#2563eb',
  textDecoration: 'none',
};
const sep: React.CSSProperties = { color: '#94a3b8' };
const h1Style: React.CSSProperties = {
  margin: '0 0 8px',
  fontSize: '26px',
  color: '#0f172a',
};
const subtitleStyle: React.CSSProperties = {
  margin: '0 0 20px',
  fontSize: '14px',
  color: '#475569',
  lineHeight: 1.6,
};
const loadingStyle: React.CSSProperties = {
  padding: '24px',
  background: '#f8fafc',
  borderRadius: '8px',
  color: '#64748b',
  fontSize: '14px',
};
const errorBoxStyle: React.CSSProperties = {
  padding: '16px',
  background: '#fef2f2',
  border: '1px solid #fecaca',
  borderRadius: '8px',
  color: '#b91c1c',
  fontSize: '14px',
};
const noteBoxStyle: React.CSSProperties = {
  padding: '12px 16px',
  background: '#fffbeb',
  border: '1px solid #fde68a',
  borderRadius: '6px',
  fontSize: '13px',
  color: '#92400e',
  marginBottom: '20px',
};
const tableStyle: React.CSSProperties = {
  width: '100%',
  borderCollapse: 'collapse',
  fontSize: '14px',
};
const thStyle: React.CSSProperties = {
  padding: '10px 12px',
  background: '#f1f5f9',
  borderBottom: '2px solid #e2e8f0',
  fontWeight: 600,
  color: '#374151',
  textAlign: 'center',
  whiteSpace: 'nowrap',
};
const rowEven: React.CSSProperties = { background: '#fff' };
const rowOdd: React.CSSProperties = { background: '#f8fafc' };
const tdCenter: React.CSSProperties = {
  padding: '10px 12px',
  textAlign: 'center',
  borderBottom: '1px solid #e2e8f0',
  color: '#374151',
};
const tdName: React.CSSProperties = {
  padding: '10px 12px',
  borderBottom: '1px solid #e2e8f0',
};
const metroNameStyle: React.CSSProperties = {
  fontWeight: 500,
  color: '#0f172a',
  display: 'block',
};
const stateStyle: React.CSSProperties = {
  fontSize: '12px',
  color: '#64748b',
};
const violHighStyle: React.CSSProperties = { color: '#b91c1c' };
const violLowStyle: React.CSSProperties = { color: '#0f172a' };
const naStyle: React.CSSProperties = { color: '#94a3b8', fontSize: '12px' };
const reportLinkStyle: React.CSSProperties = {
  color: '#2563eb',
  textDecoration: 'none',
  fontSize: '13px',
  fontWeight: 500,
};
const footerStyle: React.CSSProperties = {
  marginTop: '24px',
  paddingTop: '16px',
  borderTop: '1px solid #e5e7eb',
};
const sourceLineStyle: React.CSSProperties = {
  margin: '0 0 8px',
  fontSize: '12px',
  color: '#64748b',
};
const extLinkStyle: React.CSSProperties = { color: '#2563eb' };
const disclaimerStyle: React.CSSProperties = {
  margin: 0,
  fontSize: '12px',
  color: '#94a3b8',
  fontStyle: 'italic',
};
