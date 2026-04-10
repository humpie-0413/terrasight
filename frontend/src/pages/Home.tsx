import { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import TrendsStrip from '../components/climate-trends/TrendsStrip';
import Globe, {
  type ContinuousLayer,
  type GlobeHandle,
} from '../components/earth-now/Globe';
import StoryPanel from '../components/earth-now/StoryPanel';
import BornIn from '../components/born-in/BornIn';
import AtlasGrid from '../components/atlas/AtlasGrid';
import { useApi } from '../hooks/useApi';

/**
 * Home page assembly — Climate Trends strip, Earth Now hero (Globe + Story),
 * then the rest of the page.
 *
 * Globe layer state lives here (lifted out of Globe.tsx) so the Story Panel's
 * "Explore on Globe" button can command both the active layer AND the camera
 * position via a forwardRef handle on Globe.
 */
export default function Home() {
  const [firesOn, setFiresOn] = useState(true);
  const [continuousLayer, setContinuousLayer] =
    useState<ContinuousLayer>(null);
  const globeRef = useRef<GlobeHandle>(null);

  const handleExploreOnGlobe = (
    layerOn: string,
    camera: { lat: number; lng: number; altitude: number },
  ) => {
    if (layerOn === 'firms') setFiresOn(true);
    if (layerOn === 'oisst') setContinuousLayer('ocean-heat');
    if (layerOn === 'openaq') setContinuousLayer('air-monitors');
    globeRef.current?.flyTo(camera.lat, camera.lng, camera.altitude);
  };

  return (
    <main>
      <div id="climate-trends">
        <TrendsStrip />
      </div>
      <section
        id="earth-now"
        style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(0, 2fr) minmax(280px, 1fr)',
          gap: '16px',
          padding: '16px 24px',
        }}
      >
        <Globe
          ref={globeRef}
          firesOn={firesOn}
          onToggleFires={setFiresOn}
          continuousLayer={continuousLayer}
          onSetContinuousLayer={setContinuousLayer}
        />
        <StoryPanel onExploreOnGlobe={handleExploreOnGlobe} />
      </section>
      <BornIn />
      <AtlasGrid />
      <div id="local-reports">
        <LocalReportsSection />
      </div>
    </main>
  );
}

// ── Local Reports section ─────────────────────────────────────────────────

interface MetroSummary {
  slug: string;
  name: string;
  state: string | null;
  population: number | null;
  population_year: string | null;
  climate_zone: string | null;
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
      const res = await fetch(`/api/reports/search?q=${encodeURIComponent(q)}`);
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

      {/* Metro cards */}
      <div style={gridStyle}>
        {loading && <p style={{ color: '#64748b', fontSize: '14px' }}>Loading metros…</p>}
        {metros?.map((metro) => (
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
  borderTop: '1px solid #e5e7eb',
};
const h2Style: React.CSSProperties = {
  margin: '0 0 6px',
  fontSize: '22px',
  color: '#0f172a',
};
const subtitleStyle: React.CSSProperties = {
  margin: '0 0 20px',
  fontSize: '14px',
  color: '#475569',
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
  border: '1px solid #e2e8f0',
  borderRadius: '8px',
  background: '#fff',
  textDecoration: 'none',
  color: 'inherit',
  boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
  transition: 'border-color 0.15s',
};
const cardNameStyle: React.CSSProperties = {
  fontWeight: 600,
  fontSize: '15px',
  color: '#0f172a',
  marginBottom: '4px',
};
const cardMetaStyle: React.CSSProperties = {
  fontSize: '13px',
  color: '#475569',
  marginBottom: '2px',
};
const cardClimateStyle: React.CSSProperties = {
  fontSize: '12px',
  color: '#64748b',
  marginBottom: '10px',
};
const cardLinkStyle: React.CSSProperties = {
  fontSize: '13px',
  color: '#2563eb',
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
  border: '1px solid #cbd5e1',
  borderRadius: '6px',
  width: '220px',
  fontFamily: 'system-ui, sans-serif',
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
  color: '#b91c1c',
};
