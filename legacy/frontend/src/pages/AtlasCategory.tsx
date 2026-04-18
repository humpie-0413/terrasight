import { Link, useParams } from 'react-router-dom';
import catalog from '../data/atlas_catalog.json';
import TrustBadge from '../components/common/TrustBadge';
import MetaLine from '../components/common/MetaLine';
import type { TrustTag } from '../utils/trustTags';

/**
 * /atlas/:categorySlug — Dataset listing for one Atlas category.
 * Static data from atlas_catalog.json — no backend call needed.
 */
export default function AtlasCategory() {
  const { categorySlug } = useParams<{ categorySlug: string }>();
  const category = catalog.categories.find((c) => c.slug === categorySlug);

  if (!category) {
    return (
      <main style={pageStyle}>
        <h1 style={h1Style}>Category not found</h1>
        <p>No Atlas category matches "{categorySlug}".</p>
        <Link to="/atlas" style={backLink}>← Back to Atlas</Link>
      </main>
    );
  }

  return (
    <main style={pageStyle}>
      <nav style={breadcrumbStyle}>
        <Link to="/atlas" style={backLink}>Atlas</Link>
        <span style={{ color: '#94a3b8', margin: '0 6px' }}>›</span>
        <span style={{ color: '#f1f5f9' }}>{category.title}</span>
      </nav>

      <header style={headerStyle}>
        <span style={iconStyle}>{category.icon}</span>
        <h1 style={h1Style}>{category.title}</h1>
        <p style={subtitleStyle}>{category.description}</p>
      </header>

      <div style={datasetList}>
        {category.datasets.map((ds) => (
          <article key={ds.id} style={dsCardStyle}>
            {/* MetaLine: cadence · trust tag · source — before the name */}
            <MetaLine
              cadence={ds.update_frequency}
              tag={ds.trust_tag as TrustTag}
              source={ds.source}
            />
            <div style={dsHeaderRow}>
              <h2 style={dsTitleStyle}>{ds.name}</h2>
              <span style={ds.status === 'live' ? livePillStyle : plannedPillStyle}>
                {ds.status === 'live' ? 'Live P0' : 'Planned'}
              </span>
            </div>
            <p style={dsDescStyle}>{ds.description}</p>
            <div style={dsMetaGrid}>
              <MetaItem label="Spatial coverage" value={ds.spatial_coverage} />
              <MetaItem label="License" value={ds.license} />
            </div>
            <div style={dsFooter}>
              <TrustBadge tag={ds.trust_tag as TrustTag} />
              <a
                href={ds.url}
                target="_blank"
                rel="noopener noreferrer"
                style={externalLink}
              >
                View source →
              </a>
            </div>
          </article>
        ))}
      </div>

      <div style={{ marginTop: '32px' }}>
        <Link to="/atlas" style={backLink}>← Back to Atlas</Link>
      </div>
    </main>
  );
}

function MetaItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span style={metaLabelStyle}>{label}:</span>{' '}
      <span style={metaValueStyle}>{value}</span>
    </div>
  );
}

const pageStyle: React.CSSProperties = {
  maxWidth: '900px',
  margin: '0 auto',
  padding: '32px 24px',
};
const breadcrumbStyle: React.CSSProperties = {
  fontSize: '13px',
  marginBottom: '20px',
  display: 'flex',
  alignItems: 'center',
};
const backLink: React.CSSProperties = {
  color: '#60a5fa',
  textDecoration: 'none',
  fontSize: '14px',
};
const headerStyle: React.CSSProperties = {
  marginBottom: '28px',
};
const iconStyle: React.CSSProperties = {
  fontSize: '36px',
  display: 'block',
  marginBottom: '8px',
};
const h1Style: React.CSSProperties = {
  margin: '0 0 8px',
  fontSize: '26px',
  color: '#f1f5f9',
};
const subtitleStyle: React.CSSProperties = {
  margin: 0,
  fontSize: '14px',
  color: '#94a3b8',
  maxWidth: '640px',
  lineHeight: 1.6,
};
const datasetList: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: '20px',
};
const dsCardStyle: React.CSSProperties = {
  padding: '20px 22px',
  border: '1px solid rgba(51, 65, 85, 0.5)',
  borderRadius: '10px',
  background: 'rgba(15, 23, 42, 0.6)',
  backdropFilter: 'blur(8px)',
  boxShadow: '0 4px 16px rgba(0,0,0,0.2)',
};
const dsHeaderRow: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'flex-start',
  gap: '12px',
  marginBottom: '8px',
};
const dsTitleStyle: React.CSSProperties = {
  margin: 0,
  fontSize: '16px',
  fontWeight: 600,
  color: '#f1f5f9',
};
const livePillStyle: React.CSSProperties = {
  fontSize: '11px',
  fontWeight: 600,
  padding: '2px 8px',
  borderRadius: '999px',
  background: 'rgba(22, 163, 74, 0.15)',
  color: '#4ade80',
  whiteSpace: 'nowrap',
  flexShrink: 0,
};
const plannedPillStyle: React.CSSProperties = {
  fontSize: '11px',
  fontWeight: 600,
  padding: '2px 8px',
  borderRadius: '999px',
  background: 'rgba(100, 116, 139, 0.15)',
  color: '#94a3b8',
  whiteSpace: 'nowrap',
  flexShrink: 0,
};
const dsDescStyle: React.CSSProperties = {
  margin: '0 0 12px',
  fontSize: '13px',
  color: '#94a3b8',
  lineHeight: 1.6,
};
const dsMetaGrid: React.CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: '6px 20px',
  marginBottom: '14px',
};
const metaLabelStyle: React.CSSProperties = {
  fontSize: '12px',
  color: '#64748b',
  fontWeight: 500,
};
const metaValueStyle: React.CSSProperties = {
  fontSize: '12px',
  color: '#94a3b8',
};
const dsFooter: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
};
const externalLink: React.CSSProperties = {
  fontSize: '13px',
  color: '#60a5fa',
  textDecoration: 'none',
  fontWeight: 500,
};
