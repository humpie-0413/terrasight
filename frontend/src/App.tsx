import { lazy, Suspense } from 'react';
import { Routes, Route } from 'react-router-dom';
import Header from './components/header/Header';
import Home from './pages/Home';
import Atlas from './pages/Atlas';
import AtlasCategory from './pages/AtlasCategory';
import Ranking from './pages/Ranking';
import PM25Ranking from './pages/PM25Ranking';
import Guide from './pages/Guide';

// Lazy-load LocalReport: it owns ~45 KB of report-page JSX (10 blocks +
// the new Phase E.3 toxic releases / site cleanup / facility GHG /
// drinking water sections) that nothing else on the site needs. Splitting
// it into its own async chunk keeps the main bundle under the 600 KB
// gzipped guardrail without sacrificing the Home globe hero on first paint.
const LocalReport = lazy(() => import('./pages/LocalReport'));

const reportFallbackStyle: React.CSSProperties = {
  padding: 40,
  textAlign: 'center',
};

export default function App() {
  return (
    <>
      <Header />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route
          path="/reports/:cbsaSlug"
          element={
            <Suspense
              fallback={<div style={reportFallbackStyle}>Loading report…</div>}
            >
              <LocalReport />
            </Suspense>
          }
        />
        <Route path="/atlas" element={<Atlas />} />
        <Route path="/atlas/:categorySlug" element={<AtlasCategory />} />
        <Route path="/rankings/pm25" element={<PM25Ranking />} />
        <Route path="/rankings/:rankingSlug" element={<Ranking />} />
        <Route path="/guides/:guideSlug" element={<Guide />} />
      </Routes>
    </>
  );
}
