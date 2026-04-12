import { Link } from 'react-router-dom';

export default function Home() {
  return (
    <main>
      {/* Hero section */}
      <section style={{
        background: 'linear-gradient(135deg, #0a0e27 0%, #0f1b3d 40%, #0c1445 70%, #0a0e27 100%)',
        color: '#fff', padding: '80px 24px 60px', textAlign: 'center',
        position: 'relative', overflow: 'hidden',
      }}>
        <div style={{
          position: 'absolute', inset: 0,
          background: 'radial-gradient(ellipse at 50% 0%, rgba(59,130,246,0.08) 0%, transparent 60%)',
          pointerEvents: 'none',
        }} />
        <h1 style={{ margin: '0 0 12px', fontSize: '36px', fontWeight: 800, letterSpacing: '-0.02em', position: 'relative' }}>
          TerraSight
        </h1>
        <p style={{ margin: '0 0 28px', fontSize: '16px', color: '#94a3b8', maxWidth: '560px', marginLeft: 'auto', marginRight: 'auto', lineHeight: 1.6, position: 'relative' }}>
          Live climate signals, environmental data atlas, and U.S. metro-level environmental reports — all with transparent sourcing.
        </p>
        <div style={{ display: 'flex', gap: '12px', justifyContent: 'center', flexWrap: 'wrap', position: 'relative' }}>
          <Link to="/earth-now" style={heroBtnPrimary}>Explore Earth Now</Link>
          <Link to="/trends" style={heroBtnSecondary}>Climate Trends</Link>
          <Link to="/reports" style={heroBtnSecondary}>Local Reports</Link>
        </div>
      </section>

      {/* Section cards grid */}
      <section style={{ padding: '40px 24px', maxWidth: '1000px', margin: '0 auto' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '20px' }}>
          <SectionCard to="/earth-now" icon="\uD83C\uDF0D" title="Earth Now"
            desc="Real-time satellite fire detection, ocean heat, air quality monitors, tropical storms, and earthquakes on an interactive 3D globe." />
          <SectionCard to="/trends" icon="\uD83D\uDCC8" title="Climate Trends"
            desc="Six key climate indicators with historical sparklines: CO\u2082, temperature, sea ice, methane, sea level, and drought." />
          <SectionCard to="/atlas" icon="\uD83D\uDCDA" title="Environmental Atlas"
            desc="23 live datasets across 8 categories — air, water, hydrology, coast, soil, waste, emissions, and hazards." />
          <SectionCard to="/reports" icon="\uD83D\uDCCD" title="Local Reports"
            desc="14-block environmental profiles for 50 U.S. metros: air quality, facilities, PFAS, drinking water, hazards, and more." />
          <SectionCard to="/rankings" icon="\uD83D\uDCCA" title="Rankings"
            desc="Compare 50 metros by EPA violations, PM2.5, toxic releases, GHG emissions, Superfund sites, and drinking water." />
          <SectionCard to="/guides" icon="\uD83D\uDCD6" title="Guides"
            desc="Learn how to read AQI reports, EPA compliance data, water quality samples, and climate normals." />
        </div>
      </section>
    </main>
  );
}

function SectionCard({ to, icon, title, desc }: { to: string; icon: string; title: string; desc: string }) {
  return (
    <Link to={to} style={cardStyle}>
      <div style={{ fontSize: '28px', marginBottom: '8px' }}>{icon}</div>
      <h2 style={{ margin: '0 0 6px', fontSize: '18px', color: '#f1f5f9', fontWeight: 600 }}>{title}</h2>
      <p style={{ margin: 0, fontSize: '13px', color: '#94a3b8', lineHeight: 1.5 }}>{desc}</p>
    </Link>
  );
}

const heroBtnPrimary: React.CSSProperties = {
  display: 'inline-block', padding: '12px 28px', background: '#2563eb',
  color: '#fff', borderRadius: '8px', textDecoration: 'none',
  fontSize: '15px', fontWeight: 600, boxShadow: '0 0 20px rgba(37,99,235,0.3)',
  transition: 'transform 0.15s, box-shadow 0.15s',
};
const heroBtnSecondary: React.CSSProperties = {
  display: 'inline-block', padding: '12px 24px',
  background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.15)',
  color: '#e2e8f0', borderRadius: '8px', textDecoration: 'none',
  fontSize: '15px', fontWeight: 600, backdropFilter: 'blur(4px)',
};
const cardStyle: React.CSSProperties = {
  display: 'block', padding: '22px', borderRadius: '12px',
  background: 'rgba(15, 23, 42, 0.6)', border: '1px solid rgba(51, 65, 85, 0.5)',
  textDecoration: 'none', color: 'inherit',
  backdropFilter: 'blur(8px)',
  boxShadow: '0 4px 16px rgba(0,0,0,0.2)',
  transition: 'border-color 0.2s, box-shadow 0.2s, transform 0.2s',
};
