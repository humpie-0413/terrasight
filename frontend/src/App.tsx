import { lazy, Suspense } from 'react';
import { Routes, Route } from 'react-router-dom';
import Header from './components/header/Header';
import Home from './pages/Home';

// Lazy-load all non-home routes so they split into separate async chunks.
const EarthNow = lazy(() => import('./pages/EarthNow'));
const Trends = lazy(() => import('./pages/Trends'));
const Reports = lazy(() => import('./pages/Reports'));
const LocalReport = lazy(() => import('./pages/LocalReport'));
const Atlas = lazy(() => import('./pages/Atlas'));
const AtlasCategory = lazy(() => import('./pages/AtlasCategory'));
const RankingsList = lazy(() => import('./pages/RankingsList'));
const Ranking = lazy(() => import('./pages/Ranking'));
const PM25Ranking = lazy(() => import('./pages/PM25Ranking'));
const GuidesList = lazy(() => import('./pages/GuidesList'));
const Guide = lazy(() => import('./pages/Guide'));

const fallbackStyle: React.CSSProperties = {
  padding: 40,
  textAlign: 'center',
  color: '#94a3b8',
  fontSize: '15px',
};

export default function App() {
  return (
    <>
      <Header />
      <Suspense fallback={<div style={fallbackStyle}>Loading…</div>}>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/earth-now" element={<EarthNow />} />
          <Route path="/trends" element={<Trends />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/reports/:cbsaSlug" element={<LocalReport />} />
          <Route path="/atlas" element={<Atlas />} />
          <Route path="/atlas/:categorySlug" element={<AtlasCategory />} />
          <Route path="/rankings" element={<RankingsList />} />
          <Route path="/rankings/pm25" element={<PM25Ranking />} />
          <Route path="/rankings/:rankingSlug" element={<Ranking />} />
          <Route path="/guides" element={<GuidesList />} />
          <Route path="/guides/:guideSlug" element={<Guide />} />
        </Routes>
      </Suspense>
    </>
  );
}
