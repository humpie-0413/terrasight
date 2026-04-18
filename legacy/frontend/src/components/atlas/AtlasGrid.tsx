import { Link } from 'react-router-dom';
import catalog from '../../data/atlas_catalog.json';

/**
 * Environmental Data Atlas — 8-category grid on the home page.
 * Full detail at /atlas; each card links to /atlas/:slug.
 */
export default function AtlasGrid() {
  return (
    <section style={sectionStyle}>
      <div style={headerRow}>
        <h2 style={h2Style}>Environmental Data Atlas</h2>
        <Link to="/atlas" style={allLinkStyle}>View all →</Link>
      </div>
      <div style={gridStyle}>
        {catalog.categories.map((cat) => {
          const liveCount = cat.datasets.filter((d) => d.status === 'live').length;
          return (
            <Link key={cat.slug} to={`/atlas/${cat.slug}`} style={cardStyle}>
              <span style={iconStyle}>{cat.icon}</span>
              <h3 style={cardTitleStyle}>{cat.title}</h3>
              <div style={cardFooter}>
                <span style={countStyle}>{cat.datasets.length} datasets</span>
                {liveCount > 0 && (
                  <span style={liveStyle}>{liveCount} live</span>
                )}
              </div>
            </Link>
          );
        })}
      </div>
    </section>
  );
}

const sectionStyle: React.CSSProperties = {
  padding: '32px 24px',
  borderTop: '1px solid #e5e7eb',
};
const headerRow: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'baseline',
  marginBottom: '20px',
};
const h2Style: React.CSSProperties = {
  margin: 0,
  fontSize: '22px',
  color: '#0f172a',
};
const allLinkStyle: React.CSSProperties = {
  fontSize: '14px',
  color: '#2563eb',
  textDecoration: 'none',
  fontWeight: 500,
};
const gridStyle: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
  gap: '14px',
};
const cardStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  padding: '16px',
  border: '1px solid #e5e7eb',
  borderRadius: '8px',
  textDecoration: 'none',
  color: 'inherit',
  background: '#fff',
  gap: '8px',
};
const iconStyle: React.CSSProperties = {
  fontSize: '24px',
  lineHeight: 1,
};
const cardTitleStyle: React.CSSProperties = {
  margin: 0,
  fontSize: '14px',
  fontWeight: 600,
  color: '#0f172a',
  lineHeight: 1.4,
};
const cardFooter: React.CSSProperties = {
  display: 'flex',
  gap: '8px',
  alignItems: 'center',
  marginTop: 'auto',
};
const countStyle: React.CSSProperties = {
  fontSize: '11px',
  color: '#94a3b8',
};
const liveStyle: React.CSSProperties = {
  fontSize: '11px',
  color: '#16a34a',
  fontWeight: 600,
  padding: '1px 6px',
  background: '#f0fdf4',
  borderRadius: '999px',
};
