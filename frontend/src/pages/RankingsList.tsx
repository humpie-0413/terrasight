import { Link } from 'react-router-dom';

const RANKINGS = [
  { slug: 'epa-violations', title: 'EPA Facility Violations', icon: '🏭' },
  { slug: 'pm25', title: 'PM2.5 Air Quality Levels', icon: '💨' },
  { slug: 'tri-releases', title: 'TRI Toxics Releases', icon: '♻️' },
  { slug: 'ghg-emissions', title: 'Facility GHG Emissions', icon: '🏭' },
  { slug: 'superfund', title: 'Superfund NPL Sites', icon: '🚨' },
  { slug: 'drinking-water-violations', title: 'Drinking Water Violations', icon: '💧' },
];

export default function RankingsList() {
  return (
    <main style={{ padding: '32px 24px', maxWidth: '800px', margin: '0 auto' }}>
      <h1 style={{ margin: '0 0 8px', fontSize: '24px', color: '#f1f5f9' }}>Environmental Rankings</h1>
      <p style={{ margin: '0 0 24px', fontSize: '14px', color: '#94a3b8' }}>
        50 U.S. metros ranked by environmental metrics.
      </p>
      <div style={{ display: 'grid', gap: '12px' }}>
        {RANKINGS.map(r => (
          <Link key={r.slug} to={`/rankings/${r.slug}`}
            style={{
              display: 'flex', alignItems: 'center', gap: '12px',
              padding: '16px 20px', border: '1px solid rgba(51, 65, 85, 0.5)', borderRadius: '8px',
              background: 'rgba(15, 23, 42, 0.6)', backdropFilter: 'blur(8px)',
              textDecoration: 'none', color: '#f1f5f9',
              fontSize: '15px', fontWeight: 500,
            }}>
            <span style={{ fontSize: '20px' }}>{r.icon}</span>
            {r.title}
            <span style={{ marginLeft: 'auto', color: '#64748b', fontSize: '13px' }}>50 metros →</span>
          </Link>
        ))}
      </div>
    </main>
  );
}
