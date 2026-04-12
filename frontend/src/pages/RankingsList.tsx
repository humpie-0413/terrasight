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
      <h1 style={{ margin: '0 0 8px', fontSize: '24px', color: '#0f172a' }}>Environmental Rankings</h1>
      <p style={{ margin: '0 0 24px', fontSize: '14px', color: '#475569' }}>
        50 U.S. metros ranked by environmental metrics.
      </p>
      <div style={{ display: 'grid', gap: '12px' }}>
        {RANKINGS.map(r => (
          <Link key={r.slug} to={`/rankings/${r.slug}`}
            style={{
              display: 'flex', alignItems: 'center', gap: '12px',
              padding: '16px 20px', border: '1px solid #e2e8f0', borderRadius: '8px',
              background: '#fff', textDecoration: 'none', color: '#0f172a',
              fontSize: '15px', fontWeight: 500,
            }}>
            <span style={{ fontSize: '20px' }}>{r.icon}</span>
            {r.title}
            <span style={{ marginLeft: 'auto', color: '#94a3b8', fontSize: '13px' }}>50 metros →</span>
          </Link>
        ))}
      </div>
    </main>
  );
}
