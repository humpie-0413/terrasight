import { lazy, Suspense, useRef, useState } from 'react';
import type { ActiveCategory, GlobeHandle } from '../components/earth-now/GlobeDeck';
import StoryPanel from '../components/earth-now/StoryPanel';

const GlobeDeck = lazy(() => import('../components/earth-now/GlobeDeck'));

export default function EarthNow() {
  const [activeCategory, setActiveCategory] = useState<ActiveCategory>('air-quality');
  const globeRef = useRef<GlobeHandle>(null);
  const [storyOpen, setStoryOpen] = useState(false);

  const handleExploreOnGlobe = (
    layerOn: string,
    camera: { lat: number; lng: number; altitude: number },
  ) => {
    if (layerOn === 'firms') setActiveCategory('wildfires');
    if (layerOn === 'oisst') setActiveCategory('ocean-crisis');
    if (layerOn === 'openaq') setActiveCategory('air-quality');
    globeRef.current?.flyTo(camera.lat, camera.lng, camera.altitude);
  };

  return (
    <main style={{
      position: 'relative',
      height: '100vh',
      overflow: 'hidden',
      background: '#020408',
    }}>
      <Suspense fallback={
        <div style={{
          width: '100%', height: '100%',
          background: 'radial-gradient(ellipse at center, #0a0e27 0%, #020408 100%)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: '#475569', fontSize: '13px', fontFamily: 'system-ui, sans-serif',
        }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{
              width: 36, height: 36, borderRadius: '50%',
              border: '2px solid #1e293b', borderTopColor: '#3b82f6',
              animation: 'spin 0.8s linear infinite',
              margin: '0 auto 12px',
            }} />
            Initializing Earth Now…
          </div>
        </div>
      }>
        <GlobeDeck
          ref={globeRef}
          activeCategory={activeCategory}
          onCategoryChange={setActiveCategory}
        />
      </Suspense>

      {/* Floating Story Panel */}
      <div className="globe-story-panel" style={{
        position: 'absolute',
        bottom: 64,
        right: 16,
        zIndex: 20,
        width: 300,
      }}>
        <button
          type="button"
          onClick={() => setStoryOpen(!storyOpen)}
          style={{
            display: 'flex', alignItems: 'center', gap: 8, width: '100%',
            background: 'rgba(10,14,26,0.85)', backdropFilter: 'blur(12px)',
            border: '1px solid rgba(51,65,85,0.4)',
            borderRadius: storyOpen ? '8px 8px 0 0' : '8px',
            color: '#cbd5e1', fontSize: 12, fontWeight: 600,
            padding: '8px 14px', cursor: 'pointer',
            fontFamily: 'system-ui, sans-serif', textAlign: 'left',
          }}
        >
          <span>Climate Story</span>
          <span style={{ marginLeft: 'auto', fontSize: 10, color: '#475569' }}>
            {storyOpen ? '▼' : '▲'}
          </span>
        </button>
        {storyOpen && (
          <div style={{
            background: 'rgba(10,14,26,0.92)',
            backdropFilter: 'blur(12px)',
            border: '1px solid rgba(51,65,85,0.4)',
            borderTop: 'none',
            borderRadius: '0 0 8px 8px',
            maxHeight: '50vh',
            overflowY: 'auto',
          }}>
            <StoryPanel onExploreOnGlobe={handleExploreOnGlobe} />
          </div>
        )}
      </div>
    </main>
  );
}
