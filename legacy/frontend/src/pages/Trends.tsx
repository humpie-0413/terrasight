import { lazy, Suspense } from 'react';
import TrendsStrip from '../components/climate-trends/TrendsStrip';

const BornIn = lazy(() => import('../components/born-in/BornIn'));

export default function Trends() {
  return (
    <main style={{ padding: '16px 24px' }}>
      <h1 style={{ margin: '0 0 16px', fontSize: '24px', color: '#f1f5f9' }}>Climate Trends</h1>
      <TrendsStrip />
      <Suspense fallback={null}>
        <BornIn />
      </Suspense>
    </main>
  );
}
