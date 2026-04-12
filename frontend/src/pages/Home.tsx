import { Link } from 'react-router-dom';

export default function Home() {
  return (
    <main>
      {/* Hero section */}
      <section style={{
        background: 'linear-gradient(135deg, #0c1445 0%, #1a237e 50%, #0d47a1 100%)',
        color: '#fff', padding: '60px 24px', textAlign: 'center',
      }}>
        <h1 style={{ margin: '0 0 12px', fontSize: '32px', fontWeight: 700 }}>TerraSight</h1>
        <p style={{ margin: '0 0 24px', fontSize: '16px', color: '#94a3b8', maxWidth: '600px', marginLeft: 'auto', marginRight: 'auto' }}>
          Live climate signals, environmental data atlas, and U.S. metro-level environmental reports.
        </p>
        <div style={{ display: 'flex', gap: '12px', justifyContent: 'center', flexWrap: 'wrap' }}>
          <Link to="/earth-now" style={heroBtnStyle}>Explore Earth Now</Link>
          <Link to="/trends" style={{ ...heroBtnStyle, background: 'rgba(255,255,255,0.15)' }}>Climate Trends</Link>
          <Link to="/reports" style={{ ...heroBtnStyle, background: 'rgba(255,255,255,0.15)' }}>Local Reports</Link>
        </div>
      </section>

      {/* Section cards grid */}
      <section style={{ padding: '32px 24px', maxWidth: '1000px', margin: '0 auto' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '20px' }}>
          <SectionCard to="/earth-now" icon="🌍" title="Earth Now"
            desc="Real-time satellite fire detection, ocean heat, air quality monitors, tropical storms, and earthquakes on an interactive 3D globe." />
          <SectionCard to="/trends" icon="📈" title="Climate Trends"
            desc="Six key climate indicators with historical sparklines: CO₂, temperature, sea ice, methane, sea level, and drought." />
          <SectionCard to="/atlas" icon="📚" title="Environmental Atlas"
            desc="23 live datasets across 8 categories — air, water, hydrology, coast, soil, waste, emissions, and hazards." />
          <SectionCard to="/reports" icon="📍" title="Local Reports"
            desc="14-block environmental profiles for 50 U.S. metros: air quality, facilities, PFAS, drinking water, hazards, and more." />
          <SectionCard to="/rankings" icon="📊" title="Rankings"
            desc="Compare 50 metros by EPA violations, PM2.5, toxic releases, GHG emissions, Superfund sites, and drinking water." />
          <SectionCard to="/guides" icon="📖" title="Guides"
            desc="Learn how to read AQI reports, EPA compliance data, water quality samples, and climate normals." />
        </div>
      </section>
    </main>
  );
}

function SectionCard({ to, icon, title, desc }: { to: string; icon: string; title: string; desc: string }) {
  return (
    <Link to={to} style={{
      display: 'block', padding: '20px', border: '1px solid #e2e8f0', borderRadius: '12px',
      background: '#fff', textDecoration: 'none', color: 'inherit',
      boxShadow: '0 1px 3px rgba(0,0,0,0.06)', transition: 'box-shadow 0.15s',
    }}>
      <div style={{ fontSize: '28px', marginBottom: '8px' }}>{icon}</div>
      <h2 style={{ margin: '0 0 6px', fontSize: '18px', color: '#0f172a' }}>{title}</h2>
      <p style={{ margin: 0, fontSize: '13px', color: '#475569', lineHeight: 1.5 }}>{desc}</p>
    </Link>
  );
}

const heroBtnStyle: React.CSSProperties = {
  display: 'inline-block', padding: '12px 24px', background: '#2563eb',
  color: '#fff', borderRadius: '8px', textDecoration: 'none',
  fontSize: '15px', fontWeight: 600,
};
