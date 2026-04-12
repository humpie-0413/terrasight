import { Link, useParams } from 'react-router-dom';
import { useApi } from '../hooks/useApi';

interface RankingRow {
  slug: string;
  name: string;
  state: string | null;
  status: string;
  error?: string;
  // Loose metric fields — each ranking endpoint returns a different shape
  // (sampled_facilities, in_violation, violation_rate_pct, facility_count,
  // total_co2e_tonnes, site_count, npl_final_count, system_count,
  // violation_count, …). Resolved per-slug via RANKING_COLUMNS below.
  [metric: string]: unknown;
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

type ColumnSpec = {
  key: string;
  header: string;
  render: (row: RankingRow) => React.ReactNode;
};

// Per-slug column metadata. Common columns (#, Metro, Report) are rendered
// by the table itself; these are the metric columns that vary per ranking.
const RANKING_COLUMNS: Record<string, ColumnSpec[]> = {
  'epa-violations': [
    {
      key: 'sampled_facilities',
      header: 'Sampled',
      render: (r) => {
        const v = r.sampled_facilities;
        return typeof v === 'number' ? v.toLocaleString() : <span style={naStyle}>error</span>;
      },
    },
    {
      key: 'in_violation',
      header: 'In Violation',
      render: (r) => {
        const v = r.in_violation;
        if (typeof v !== 'number') return <span style={naStyle}>—</span>;
        return (
          <strong style={v > 10 ? violHighStyle : violLowStyle}>{v}</strong>
        );
      },
    },
    {
      key: 'violation_rate_pct',
      header: 'Rate',
      render: (r) => {
        const v = r.violation_rate_pct;
        return typeof v === 'number' ? `${v}%` : '—';
      },
    },
  ],
  'tri-releases': [
    {
      key: 'facility_count',
      header: 'TRI Facilities',
      render: (r) => {
        const v = r.facility_count;
        return typeof v === 'number' ? v.toLocaleString() : <span style={naStyle}>—</span>;
      },
    },
  ],
  'ghg-emissions': [
    {
      key: 'facility_count',
      header: 'Facilities',
      render: (r) => {
        const v = r.facility_count;
        return typeof v === 'number' ? v.toLocaleString() : <span style={naStyle}>—</span>;
      },
    },
    {
      key: 'total_co2e_tonnes',
      header: 'Total tCO₂e',
      render: (r) => {
        const v = r.total_co2e_tonnes;
        return typeof v === 'number'
          ? v.toLocaleString(undefined, { maximumFractionDigits: 0 })
          : <span style={naStyle}>—</span>;
      },
    },
  ],
  superfund: [
    {
      key: 'site_count',
      header: 'Sites',
      render: (r) => {
        const v = r.site_count;
        return typeof v === 'number' ? v.toLocaleString() : <span style={naStyle}>—</span>;
      },
    },
    {
      key: 'npl_final_count',
      header: 'NPL Final',
      render: (r) => {
        const v = r.npl_final_count;
        return typeof v === 'number' ? v.toLocaleString() : <span style={naStyle}>—</span>;
      },
    },
  ],
  'drinking-water-violations': [
    {
      key: 'system_count',
      header: 'Systems',
      render: (r) => {
        const v = r.system_count;
        return typeof v === 'number' ? v.toLocaleString() : <span style={naStyle}>—</span>;
      },
    },
    {
      key: 'violation_count',
      header: 'Violations',
      render: (r) => {
        const v = r.violation_count;
        return typeof v === 'number' ? v.toLocaleString() : <span style={naStyle}>—</span>;
      },
    },
    {
      key: 'violation_rate_pct',
      header: 'Rate',
      render: (r) => {
        const v = r.violation_rate_pct;
        return typeof v === 'number' ? `${v.toFixed(1)}%` : '—';
      },
    },
  ],
};

export default function Ranking() {
  const { rankingSlug } = useParams<{ rankingSlug: string }>();
  const slug = rankingSlug ?? 'epa-violations';
  const { data, loading, error } = useApi<RankingResponse>(`/rankings/${slug}`);

  // Fall back to epa-violations columns if slug is unknown.
  const columns = RANKING_COLUMNS[slug] ?? RANKING_COLUMNS['epa-violations'];

  return (
    <main style={pageStyle}>
      <div style={breadcrumbStyle}>
        <Link to="/" style={breadcrumbLinkStyle}>Home</Link>
        <span style={sep}>›</span>
        <span>Rankings</span>
      </div>

      <h1 style={h1Style}>{data?.title ?? 'Loading…'}</h1>
      {data && (
        <p style={subtitleStyle}>{data.criterion}</p>
      )}

      {loading && (
        <div style={loadingStyle}>
          <p>Loading data for all metros — this may take 30–60 seconds…</p>
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
                {columns.map((col) => (
                  <th key={col.key} style={thStyle}>{col.header}</th>
                ))}
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
                  {columns.map((col) => (
                    <td key={col.key} style={tdCenter}>
                      {col.render(row)}
                    </td>
                  ))}
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
              {' · '}{data.tag}{' · '}
              Retrieved {data.retrieved_date}
            </p>
            <p style={disclaimerStyle}>
              Regulatory and reporting data reflect a sample of facilities per metro bounding box —
              not a complete census. Compliance ≠ environmental exposure or health risk.
              Educational use only.
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
  color: '#60a5fa',
  textDecoration: 'none',
};
const sep: React.CSSProperties = { color: '#64748b' };
const h1Style: React.CSSProperties = {
  margin: '0 0 8px',
  fontSize: '26px',
  color: '#f1f5f9',
};
const subtitleStyle: React.CSSProperties = {
  margin: '0 0 20px',
  fontSize: '14px',
  color: '#94a3b8',
  lineHeight: 1.6,
};
const loadingStyle: React.CSSProperties = {
  padding: '24px',
  background: 'rgba(15, 23, 42, 0.6)',
  borderRadius: '8px',
  color: '#94a3b8',
  fontSize: '14px',
};
const errorBoxStyle: React.CSSProperties = {
  padding: '16px',
  background: 'rgba(127, 29, 29, 0.3)',
  border: '1px solid rgba(248, 113, 113, 0.4)',
  borderRadius: '8px',
  color: '#f87171',
  fontSize: '14px',
};
const noteBoxStyle: React.CSSProperties = {
  padding: '12px 16px',
  background: 'rgba(120, 53, 15, 0.25)',
  border: '1px solid rgba(251, 191, 36, 0.4)',
  borderRadius: '6px',
  fontSize: '13px',
  color: '#fbbf24',
  marginBottom: '20px',
};
const tableStyle: React.CSSProperties = {
  width: '100%',
  borderCollapse: 'collapse',
  fontSize: '14px',
};
const thStyle: React.CSSProperties = {
  padding: '10px 12px',
  background: 'rgba(15, 23, 42, 0.8)',
  borderBottom: '2px solid rgba(51, 65, 85, 0.5)',
  fontWeight: 600,
  color: '#cbd5e1',
  textAlign: 'center',
  whiteSpace: 'nowrap',
};
const rowEven: React.CSSProperties = { background: 'rgba(15, 23, 42, 0.3)' };
const rowOdd: React.CSSProperties = { background: 'rgba(15, 23, 42, 0.5)' };
const tdCenter: React.CSSProperties = {
  padding: '10px 12px',
  textAlign: 'center',
  borderBottom: '1px solid rgba(51, 65, 85, 0.5)',
  color: '#e2e8f0',
};
const tdName: React.CSSProperties = {
  padding: '10px 12px',
  borderBottom: '1px solid rgba(51, 65, 85, 0.5)',
};
const metroNameStyle: React.CSSProperties = {
  fontWeight: 500,
  color: '#f1f5f9',
  display: 'block',
};
const stateStyle: React.CSSProperties = {
  fontSize: '12px',
  color: '#64748b',
};
const violHighStyle: React.CSSProperties = { color: '#f87171' };
const violLowStyle: React.CSSProperties = { color: '#e2e8f0' };
const naStyle: React.CSSProperties = { color: '#64748b', fontSize: '12px' };
const reportLinkStyle: React.CSSProperties = {
  color: '#60a5fa',
  textDecoration: 'none',
  fontSize: '13px',
  fontWeight: 500,
};
const footerStyle: React.CSSProperties = {
  marginTop: '24px',
  paddingTop: '16px',
  borderTop: '1px solid rgba(51, 65, 85, 0.5)',
};
const sourceLineStyle: React.CSSProperties = {
  margin: '0 0 8px',
  fontSize: '12px',
  color: '#64748b',
};
const extLinkStyle: React.CSSProperties = { color: '#60a5fa' };
const disclaimerStyle: React.CSSProperties = {
  margin: 0,
  fontSize: '12px',
  color: '#64748b',
  fontStyle: 'italic',
};
