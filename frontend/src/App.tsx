import { lazy, Suspense } from 'react';
import { Routes, Route } from 'react-router-dom';
import Header from './components/header/Header';
import Home from './pages/Home';

// Lazy-load all non-home routes so they split into separate async chunks.
// This keeps the main bundle focused on the Home page (globe hero + trends)
// while atlas, reports, rankings, and guides load on demand.
const LocalReport = lazy(() => import('./pages/LocalReport'));
const Atlas = lazy(() => import('./pages/Atlas'));
const AtlasCategory = lazy(() => import('./pages/AtlasCategory'));
const Ranking = lazy(() => import('./pages/Ranking'));
const PM25Ranking = lazy(() => import('./pages/PM25Ranking'));
const Guide = lazy(() => import('./pages/Guide'));

const fallbackStyle: React.CSSProperties = {
  padding: 40,
  textAlign: 'center',
  color: '#64748b',
  fontSize: '15px',
};

export default function App() {
  return (
    <>
      <Header />
      <Suspense fallback={<div style={fallbackStyle}>Loading…</div>}>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/reports/:cbsaSlug" element={<LocalReport />} />
          <Route path="/atlas" element={<Atlas />} />
          <Route path="/atlas/:categorySlug" element={<AtlasCategory />} />
          <Route path="/rankings/pm25" element={<PM25Ranking />} />
          <Route path="/rankings/:rankingSlug" element={<Ranking />} />
          <Route path="/guides/:guideSlug" element={<Guide />} />
        </Routes>
      </Suspense>
    </>
  );
}
