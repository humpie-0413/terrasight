import TrendsStrip from '../components/climate-trends/TrendsStrip';
import Globe from '../components/earth-now/Globe';
import StoryPanel from '../components/earth-now/StoryPanel';
import BornIn from '../components/born-in/BornIn';
import AtlasGrid from '../components/atlas/AtlasGrid';

export default function Home() {
  return (
    <main>
      <TrendsStrip />
      <section style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '16px', padding: '16px 24px' }}>
        <Globe />
        <StoryPanel />
      </section>
      <BornIn />
      <AtlasGrid />
    </main>
  );
}
