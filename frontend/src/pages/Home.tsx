import { useRef, useState } from 'react';

import TrendsStrip from '../components/climate-trends/TrendsStrip';
import Globe, {
  type ContinuousLayer,
  type GlobeHandle,
} from '../components/earth-now/Globe';
import StoryPanel from '../components/earth-now/StoryPanel';
import BornIn from '../components/born-in/BornIn';
import AtlasGrid from '../components/atlas/AtlasGrid';

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
      <TrendsStrip />
      <section
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
    </main>
  );
}
