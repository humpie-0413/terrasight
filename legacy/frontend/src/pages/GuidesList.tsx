import { Link } from 'react-router-dom';

const GUIDES = [
  { slug: 'how-to-read-aqi', title: 'How to Read an AQI Report', icon: '📊' },
  { slug: 'understanding-epa-compliance', title: 'Understanding EPA Compliance', icon: '🏭' },
  { slug: 'water-quality-samples', title: 'Water Quality Samples Explained', icon: '💧' },
  { slug: 'climate-normals', title: 'Climate Normals Explained', icon: '🌡️' },
];

export default function GuidesList() {
  return (
    <main style={{ padding: '32px 24px', maxWidth: '800px', margin: '0 auto' }}>
      <h1 style={{ margin: '0 0 8px', fontSize: '24px', color: '#f1f5f9' }}>Environmental Guides</h1>
      <p style={{ margin: '0 0 24px', fontSize: '14px', color: '#94a3b8' }}>
        Learn how to read and interpret environmental data.
      </p>
      <div style={{ display: 'grid', gap: '12px' }}>
        {GUIDES.map(g => (
          <Link key={g.slug} to={`/guides/${g.slug}`}
            style={{
              display: 'flex', alignItems: 'center', gap: '12px',
              padding: '16px 20px', border: '1px solid rgba(51, 65, 85, 0.5)', borderRadius: '8px',
              background: 'rgba(15, 23, 42, 0.6)', backdropFilter: 'blur(8px)',
              textDecoration: 'none', color: '#f1f5f9',
              fontSize: '15px', fontWeight: 500,
            }}>
            <span style={{ fontSize: '20px' }}>{g.icon}</span>
            {g.title}
            <span style={{ marginLeft: 'auto', color: '#64748b', fontSize: '13px' }}>Read →</span>
          </Link>
        ))}
      </div>
    </main>
  );
}
