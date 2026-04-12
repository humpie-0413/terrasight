import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useApi } from '../hooks/useApi';

interface MetroSummary {
  slug: string;
  name: string;
  state: string | null;
  population: number | null;
  population_year: string | null;
  climate_zone: string | null;
}

export default function Reports() {
  return (
    <main>
      <LocalReportsSection />
    </main>
  );
}

function LocalReportsSection() {
  const navigate = useNavigate();
  const { data: metros, loading } = useApi<MetroSummary[]>('/reports/');
  const [zip, setZip] = useState('');
  const [searchMsg, setSearchMsg] = useState('');

  const handleSearch = async () => {
    const q = zip.trim();
    if (!q) return;
    setSearchMsg('');
    try {
      const base = import.meta.env.VITE_API_BASE ?? '/api';
      const res = await fetch(`${base}/reports/search?q=${encodeURIComponent(q)}`);
      const data = await res.json();
      if (data.slug) {
        navigate(`/reports/${data.slug}`);
      } else {
        setSearchMsg(data.message ?? 'No metro found.');
      }
    } catch {
      setSearchMsg('Search failed — please try again.');
    }
  };

  return (
    <section style={sectionStyle}>
      <h2 style={h2Style}>Local Environmental Reports</h2>
      <p style={subtitleStyle}>
        Metro-level air quality, climate, water, and facility data — U.S. metros.
      </p>

      {/* Metro cards — top 4 + "View all" */}
      <div style={gridStyle}>
        {loading && <p style={{ color: '#64748b', fontSize: '14px' }}>Loading metros…</p>}
        {metros?.slice(0, 4).map((metro) => (
          <a
            key={metro.slug}
            href={`/reports/${metro.slug}`}
            style={cardStyle}
          >
            <div style={cardNameStyle}>{metro.name}</div>
            <div style={cardMetaStyle}>
              {metro.state}
              {metro.population
                ? ` · Pop. ${(metro.population / 1_000_000).toFixed(1)}M`
                : ''}
            </div>
            {metro.climate_zone && (
              <div style={cardClimateStyle}>{metro.climate_zone}</div>
            )}
            <div style={cardLinkStyle}>View Report →</div>
          </a>
        ))}
      </div>

      {/* View all link */}
      {metros && metros.length > 4 && (
        <div style={{ marginBottom: '20px' }}>
          <a href="/reports" style={viewAllStyle}>
            View all {metros.length} metros →
          </a>
        </div>
      )}

      {/* Rankings + Guides quick links */}
      <div style={linksRowStyle}>
        <a href="/rankings/epa-violations" style={quickLinkStyle}>
          📊 EPA Violations Ranking
        </a>
        <a href="/rankings/pm25" style={quickLinkStyle}>
          💨 PM2.5 Levels Ranking
        </a>
        <a href="/rankings/tri-releases" style={quickLinkStyle}>
          ♻️ TRI Toxics Releases Ranking
        </a>
        <a href="/rankings/ghg-emissions" style={quickLinkStyle}>
          🏭 Facility GHG Emissions Ranking
        </a>
        <a href="/rankings/superfund" style={quickLinkStyle}>
          🚨 Superfund Sites Ranking
        </a>
        <a href="/rankings/drinking-water-violations" style={quickLinkStyle}>
          💧 Drinking Water Violations Ranking
        </a>
        <a href="/guides/how-to-read-aqi" style={quickLinkStyle}>
          📖 How to Read an AQI Report
        </a>
        <a href="/guides/understanding-epa-compliance" style={quickLinkStyle}>
          🏭 Understanding EPA Compliance
        </a>
        <a href="/guides/water-quality-samples" style={quickLinkStyle}>
          💧 Water Quality Samples
        </a>
        <a href="/guides/climate-normals" style={quickLinkStyle}>
          🌡️ Climate Normals Explained
        </a>
      </div>

      {/* ZIP / city search */}
      <div style={searchRowStyle}>
        <input
          type="text"
          value={zip}
          onChange={(e) => { setZip(e.target.value); setSearchMsg(''); }}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          placeholder="ZIP code or city name…"
          style={inputStyle}
        />
        <button type="button" onClick={handleSearch} style={btnStyle}>
          Search
        </button>
        {searchMsg && <span style={msgStyle}>{searchMsg}</span>}
      </div>
    </section>
  );
}

const sectionStyle: React.CSSProperties = {
  padding: '32px 24px',
  borderTop: '1px solid rgba(51, 65, 85, 0.5)',
};
const h2Style: React.CSSProperties = {
  margin: '0 0 6px',
  fontSize: '22px',
  color: '#f1f5f9',
};
const subtitleStyle: React.CSSProperties = {
  margin: '0 0 20px',
  fontSize: '14px',
  color: '#94a3b8',
};
const gridStyle: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))',
  gap: '16px',
  marginBottom: '24px',
};
const cardStyle: React.CSSProperties = {
  display: 'block',
  padding: '16px 18px',
  border: '1px solid rgba(51, 65, 85, 0.5)',
  borderRadius: '8px',
  background: 'rgba(15, 23, 42, 0.6)',
  backdropFilter: 'blur(8px)',
  textDecoration: 'none',
  color: 'inherit',
  boxShadow: '0 1px 3px rgba(0,0,0,0.3)',
  transition: 'border-color 0.15s',
};
const cardNameStyle: React.CSSProperties = {
  fontWeight: 600,
  fontSize: '15px',
  color: '#f1f5f9',
  marginBottom: '4px',
};
const cardMetaStyle: React.CSSProperties = {
  fontSize: '13px',
  color: '#94a3b8',
  marginBottom: '2px',
};
const cardClimateStyle: React.CSSProperties = {
  fontSize: '12px',
  color: '#64748b',
  marginBottom: '10px',
};
const cardLinkStyle: React.CSSProperties = {
  fontSize: '13px',
  color: '#60a5fa',
  fontWeight: 500,
};
const viewAllStyle: React.CSSProperties = {
  fontSize: '14px',
  color: '#60a5fa',
  textDecoration: 'none',
  fontWeight: 500,
};
const linksRowStyle: React.CSSProperties = {
  display: 'flex',
  gap: '12px',
  flexWrap: 'wrap',
  marginBottom: '20px',
};
const quickLinkStyle: React.CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: '6px',
  padding: '8px 14px',
  background: 'rgba(15, 23, 42, 0.6)',
  border: '1px solid rgba(51, 65, 85, 0.5)',
  borderRadius: '6px',
  fontSize: '13px',
  color: '#e2e8f0',
  textDecoration: 'none',
  fontWeight: 500,
};
const searchRowStyle: React.CSSProperties = {
  display: 'flex',
  gap: '8px',
  alignItems: 'center',
  flexWrap: 'wrap',
};
const inputStyle: React.CSSProperties = {
  padding: '8px 12px',
  fontSize: '14px',
  border: '1px solid rgba(51, 65, 85, 0.5)',
  borderRadius: '6px',
  width: '220px',
  fontFamily: 'system-ui, sans-serif',
  background: 'rgba(15, 23, 42, 0.8)',
  color: '#f1f5f9',
};
const btnStyle: React.CSSProperties = {
  padding: '8px 16px',
  fontSize: '14px',
  fontWeight: 600,
  background: '#1d4ed8',
  color: '#fff',
  border: 'none',
  borderRadius: '6px',
  cursor: 'pointer',
  fontFamily: 'system-ui, sans-serif',
};
const msgStyle: React.CSSProperties = {
  fontSize: '13px',
  color: '#f87171',
};
