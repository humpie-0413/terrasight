import { Routes, Route } from 'react-router-dom';
import Header from './components/header/Header';
import Home from './pages/Home';
import LocalReport from './pages/LocalReport';
import Atlas from './pages/Atlas';
import AtlasCategory from './pages/AtlasCategory';
import Ranking from './pages/Ranking';
import PM25Ranking from './pages/PM25Ranking';
import Guide from './pages/Guide';

export default function App() {
  return (
    <>
      <Header />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/reports/:cbsaSlug" element={<LocalReport />} />
        <Route path="/atlas" element={<Atlas />} />
        <Route path="/atlas/:categorySlug" element={<AtlasCategory />} />
        <Route path="/rankings/pm25" element={<PM25Ranking />} />
        <Route path="/rankings/:rankingSlug" element={<Ranking />} />
        <Route path="/guides/:guideSlug" element={<Guide />} />
      </Routes>
    </>
  );
}
