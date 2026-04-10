import { Link } from 'react-router-dom';
import catalog from '../data/atlas_catalog.json';
import TrustBadge from '../components/common/TrustBadge';
import type { TrustTag } from '../utils/trustTags';

/**
 * /atlas — Environmental Data Atlas main page.
 * Shows all 8 category cards with icon, dataset count, and trust-tag summary.
 */
export default function Atlas() {
  return (
    <main style={pageStyle}>
      <header style={headerStyle}>
        <h1 style={h1Style}>Environmental Data Atlas</h1>
        <p style={subtitleStyle}>
          Eight categories of environmental engineering data — each dataset
          labeled with cadence, trust tag, and source.
        </p>
      </header>

      <div style={gridStyle}>
        {catalog.categories.map((cat) => {
          const liveSets = cat.datasets.filter((d) => d.status === 'live');
          const tags = [...new Set(cat.datasets.map((d) => d.trust_tag))] as TrustTag[];
          return (
            <Link key={cat.slug} to={`/atlas/${cat.slug}`} style={cardStyle}>
              <div style={iconStyle}>{cat.icon}</div>
              <h2 style={cardTitleStyle}>{cat.title}</h2>
              <p style={descStyle}>{cat.description}</p>
              <div style={footerStyle}>
                <span style={countStyle}>
                  {cat.datasets.length} datasets
                  {liveSets.length > 0 && (
                    <span style={liveStyle}> · {liveSets.length} live</span>
                  )}
                </span>
                <div style={tagsStyle}>
                  {tags.slice(0, 2).map((t) => (
                    <TrustBadge key={t} tag={t} />
                  ))}
                </div>
              </div>
            </Link>
          );
        })}
      </div>

      <footer style={footerNoteStyle}>
        <p>
          All datasets display cadence, trust tag (observed · NRT · forecast ·
          derived · estimated), spatial scope, and license. P0 = live, P1/P2 = planned.
        </p>
      </footer>
    </main>
  );
}

const pageStyle: React.CSSProperties = {
  maxWidth: '1100px',
  margin: '0 auto',
  padding: '32px 24px',
};
const headerStyle: React.CSSProperties = {
  marginBottom: '32px',
};
const h1Style: React.CSSProperties = {
  margin: '0 0 8px',
  fontSize: '28px',
  color: '#0f172a',
};
const subtitleStyle: React.CSSProperties = {
  margin: 0,
  fontSize: '15px',
  color: '#475569',
  maxWidth: '640px',
};
const gridStyle: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
  gap: '20px',
};
const cardStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  padding: '20px',
  border: '1px solid #e2e8f0',
  borderRadius: '10px',
  background: '#fff',
  textDecoration: 'none',
  color: 'inherit',
  boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
  transition: 'border-color 0.15s, box-shadow 0.15s',
};
const iconStyle: React.CSSProperties = {
  fontSize: '28px',
  marginBottom: '10px',
  lineHeight: 1,
};
const cardTitleStyle: React.CSSProperties = {
  margin: '0 0 8px',
  fontSize: '16px',
  fontWeight: 600,
  color: '#0f172a',
};
const descStyle: React.CSSProperties = {
  margin: '0 0 16px',
  fontSize: '13px',
  color: '#475569',
  lineHeight: 1.55,
  flexGrow: 1,
};
const footerStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  flexWrap: 'wrap',
  gap: '6px',
};
const countStyle: React.CSSProperties = {
  fontSize: '12px',
  color: '#64748b',
  fontWeight: 500,
};
const liveStyle: React.CSSProperties = {
  color: '#16a34a',
  fontWeight: 600,
};
const tagsStyle: React.CSSProperties = {
  display: 'flex',
  gap: '4px',
};
const footerNoteStyle: React.CSSProperties = {
  marginTop: '40px',
  padding: '16px',
  borderTop: '1px solid #e5e7eb',
  fontSize: '13px',
  color: '#64748b',
};
