import { lazy, Suspense, useRef, useState } from 'react';
import type { GlobeHandle } from '../components/earth-now/GlobeDeck';
import StoryPanel from '../components/earth-now/StoryPanel';

const GlobeDeck = lazy(() => import('../components/earth-now/GlobeDeck'));

type ActiveEvent = 'fires' | 'storms' | 'monitors' | 'earthquakes' | null;
type ActiveContinuous =
  | 'ocean-heat' | 'coral' | 'cmems-sla'
  | 'gibs-aod' | 'gibs-pm25' | 'gibs-oco2' | 'gibs-flood'
  | null;

export default function EarthNow() {
  const [activeEvent, setActiveEvent] = useState<ActiveEvent>('fires');
  const [activeContinuous, setActiveContinuous] = useState<ActiveContinuous>(null);
  const globeRef = useRef<GlobeHandle>(null);

  const handleExploreOnGlobe = (
    layerOn: string,
    camera: { lat: number; lng: number; altitude: number },
  ) => {
    if (layerOn === 'firms') setActiveEvent('fires');
    if (layerOn === 'oisst') setActiveContinuous('ocean-heat');
    if (layerOn === 'openaq') setActiveEvent('monitors');
    globeRef.current?.flyTo(camera.lat, camera.lng, camera.altitude);
  };

  return (
    <main style={{ padding: '0 24px 24px' }}>
      <h1 style={{ margin: '16px 0', fontSize: '24px', color: '#f1f5f9', fontWeight: 700 }}>Earth Now</h1>
      <section style={{
        display: 'grid',
        gridTemplateColumns: 'minmax(0, 2.5fr) minmax(260px, 1fr)',
        gap: '16px',
      }}>
        <Suspense fallback={
          <div style={{
            width: '100%', height: '640px',
            background: 'radial-gradient(ellipse at center, #0a0e27 0%, #040610 100%)',
            borderRadius: '12px',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: '#94a3b8', fontSize: '15px',
          }}>
            Loading Earth Now…
          </div>
        }>
          <GlobeDeck
            ref={globeRef}
            activeEvent={activeEvent}
            activeContinuous={activeContinuous}
            onLayerChange={(type, key) => {
              if (type === 'event') setActiveEvent(key as ActiveEvent);
              else setActiveContinuous(key as ActiveContinuous);
            }}
          />
        </Suspense>
        <StoryPanel onExploreOnGlobe={handleExploreOnGlobe} />
      </section>
    </main>
  );
}
