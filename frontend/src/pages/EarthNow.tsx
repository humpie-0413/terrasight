import { lazy, Suspense, useRef, useState } from 'react';
import type { GlobeHandle } from '../components/earth-now/Globe';
import StoryPanel from '../components/earth-now/StoryPanel';

const Globe = lazy(() => import('../components/earth-now/Globe'));

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
    <main style={{ padding: '16px 24px' }}>
      <h1 style={{ margin: '0 0 16px', fontSize: '24px', color: '#0f172a' }}>Earth Now</h1>
      <section style={{
        display: 'grid',
        gridTemplateColumns: 'minmax(0, 2fr) minmax(280px, 1fr)',
        gap: '16px',
      }}>
        <Suspense fallback={
          <div style={{
            width: '100%',
            aspectRatio: '16/9',
            background: 'linear-gradient(135deg, #0c1445 0%, #1a237e 50%, #0d47a1 100%)',
            borderRadius: '12px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#94a3b8',
            fontSize: '15px',
          }}>
            Loading Earth Now…
          </div>
        }>
          <Globe
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
