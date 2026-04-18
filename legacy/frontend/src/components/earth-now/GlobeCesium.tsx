import {
  forwardRef,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
} from 'react';
import {
  Viewer,
  Ion,
  ImageryLayer,
  SingleTileImageryProvider,
  CustomDataSource,
  Entity,
  Color,
  Cartesian2,
  Cartesian3,
  Cartographic,
  ScreenSpaceEventHandler,
  ScreenSpaceEventType,
  defined,
  Rectangle,
  NearFarScalar,
  HeightReference,
  Math as CesiumMath,
} from 'cesium';
import 'cesium/Build/Cesium/Widgets/widgets.css';

import MetaLine from '../common/MetaLine';
import { TrustTag } from '../../utils/trustTags';
import { useApi } from '../../hooks/useApi';

const API_BASE = import.meta.env.VITE_API_BASE ?? '/api';
const CESIUM_TOKEN = import.meta.env.VITE_CESIUM_TOKEN ?? '';

// ─── Types ────────────────────────────────────────────────────────────────────

export type ActiveCategory =
  | 'air-quality' | 'temperature' | 'sst' | 'precipitation' | 'no2'
  | 'wildfires' | 'earthquakes' | 'co2-ghg'
  | 'ocean-crisis' | 'storms'
  | null;

export type ViewMode = 'globe' | 'map';

export interface GlobeHandle {
  flyTo: (lat: number, lng: number, altitude?: number) => void;
}

interface GlobeProps {
  activeCategory: ActiveCategory;
  onCategoryChange: (key: ActiveCategory) => void;
}

// ─── Data interfaces ──────────────────────────────────────────────────────────

interface FireHotspot {
  lat: number; lon: number; brightness: number; frp: number;
  confidence: string; acq_date: string; acq_time: string; daynight: string;
}
interface FiresResponse { count: number; configured: boolean; fires: FireHotspot[]; }

interface Earthquake { lat: number; lon: number; depth_km: number; magnitude: number; place: string; time_utc: string; event_url: string; tsunami: boolean; }
interface EarthquakeResponse { count: number; configured: boolean; status: string; earthquakes: Earthquake[]; }

interface OceanCurrentPoint { lat: number; lon: number; v: number; d: number; }
interface OceanCurrentsResponse { status: string; count: number; points: OceanCurrentPoint[]; }

// ─── Helpers ──────────────────────────────────────────────────────────────────

function getGibsDate(): string {
  const d = new Date();
  d.setDate(d.getDate() - 1);
  return d.toISOString().slice(0, 10);
}

/** Async helper: create SingleTileImageryProvider + add to viewer */
async function addSingleTileLayer(
  viewer: Viewer,
  url: string,
  alpha: number,
): Promise<ImageryLayer | null> {
  try {
    const provider = await SingleTileImageryProvider.fromUrl(url, {
      rectangle: Rectangle.fromDegrees(-180, -90, 180, 90),
    });
    const layer = new ImageryLayer(provider, { alpha });
    viewer.imageryLayers.add(layer);
    return layer;
  } catch {
    return null;
  }
}

// ─── Categories ───────────────────────────────────────────────────────────────

interface CategoryDef {
  key: string; icon: string; name: string; question: string;
  activeColor: string; tag: TrustTag; cadence: string;
  source: string; sourceUrl: string; activates: string[];
}

const CATEGORIES: CategoryDef[] = [
  {
    key: 'air-quality', icon: '🌬️', name: 'Air Quality',
    question: 'How is the air today?',
    activeColor: '#a855f7', tag: TrustTag.Derived, cadence: 'Hourly (CAMS model)',
    source: 'Open-Meteo / CAMS Global PM2.5', sourceUrl: 'https://open-meteo.com/en/docs/air-quality-api',
    activates: ['pm25-surface'],
  },
  {
    key: 'temperature', icon: '🌡️', name: 'Temperature',
    question: 'How warm is it globally?',
    activeColor: '#ef4444', tag: TrustTag.Derived, cadence: 'Hourly (GFS model)',
    source: 'Open-Meteo / GFS 2m Temperature', sourceUrl: 'https://open-meteo.com/en/docs',
    activates: ['temp-surface'],
  },
  {
    key: 'sst', icon: '🌊', name: 'Ocean',
    question: 'What\'s happening in the oceans?',
    activeColor: '#0ea5e9', tag: TrustTag.Observed, cadence: 'Daily',
    source: 'NASA GHRSST MUR + Ocean Currents', sourceUrl: 'https://podaac.jpl.nasa.gov/dataset/MUR-JPL-L4-GLOB-v4.1',
    activates: ['sst-surface', 'ocean-currents'],
  },
  {
    key: 'precipitation', icon: '🌧️', name: 'Precipitation',
    question: 'Where is it raining?',
    activeColor: '#3b82f6', tag: TrustTag.Derived, cadence: 'Hourly (GFS model)',
    source: 'Open-Meteo / GFS Precipitation', sourceUrl: 'https://open-meteo.com/en/docs',
    activates: ['precip-surface'],
  },
  {
    key: 'no2', icon: '🏭', name: 'NO₂ Pollution',
    question: 'Where is NO₂ concentrated?',
    activeColor: '#d97706', tag: TrustTag.Derived, cadence: 'Hourly (CAMS model)',
    source: 'Open-Meteo / CAMS Global NO₂', sourceUrl: 'https://open-meteo.com/en/docs/air-quality-api',
    activates: ['no2-surface'],
  },
  {
    key: 'wildfires', icon: '🔥', name: 'Wildfires',
    question: 'Where are fires burning?',
    activeColor: '#dc2626', tag: TrustTag.NearRealTime, cadence: 'NRT ~3h',
    source: 'NASA FIRMS', sourceUrl: 'https://firms.modaps.eosdis.nasa.gov/',
    activates: ['fires'],
  },
  {
    key: 'earthquakes', icon: '🌍', name: 'Earthquakes',
    question: 'Where did earthquakes hit?',
    activeColor: '#b91c1c', tag: TrustTag.Observed, cadence: 'NRT ~5 min',
    source: 'USGS', sourceUrl: 'https://earthquake.usgs.gov/',
    activates: ['earthquakes'],
  },
  {
    key: 'co2-ghg', icon: '💨', name: 'CO₂ & GHG',
    question: 'Where did OCO-2 measure CO₂ today?',
    activeColor: '#22c55e', tag: TrustTag.Observed, cadence: 'Daily (nadir swath ~3-5% coverage)',
    source: 'NASA OCO-2', sourceUrl: 'https://ocov2.jpl.nasa.gov/',
    activates: ['gibs-oco2'],
  },
];

const CATEGORY_LOOKUP = new Map(CATEGORIES.map((c) => [c.key, c]));

// ─── Color helpers ────────────────────────────────────────────────────────────

function fireColor(frp: number): Color {
  if (frp >= 500) return Color.fromCssColorString('#b41414').withAlpha(0.95);
  if (frp >= 200) return Color.fromCssColorString('#dc320a').withAlpha(0.9);
  if (frp >= 100) return Color.fromCssColorString('#f5640a').withAlpha(0.85);
  if (frp >= 50) return Color.fromCssColorString('#ffa014').withAlpha(0.8);
  if (frp >= 10) return Color.fromCssColorString('#ffc83c').withAlpha(0.75);
  return Color.fromCssColorString('#ffe678').withAlpha(0.65);
}

function earthquakeColor(mag: number): Color {
  if (mag < 5) return Color.fromCssColorString('#eab308').withAlpha(0.8);
  if (mag < 6) return Color.fromCssColorString('#f97316').withAlpha(0.85);
  if (mag < 7) return Color.fromCssColorString('#ef4444').withAlpha(0.9);
  return Color.fromCssColorString('#991b1b');
}

// ─── UI Components (LayerBar, Legend, Tooltip) ────────────────────────────────

function LayerBar({ activeCategory, onCategoryChange, viewMode, onViewModeChange }: {
  activeCategory: ActiveCategory; onCategoryChange: (k: ActiveCategory) => void;
  viewMode: ViewMode; onViewModeChange: (m: ViewMode) => void;
}) {
  return (
    <div style={layerBarStyle}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '3px', overflowX: 'auto', paddingBottom: 2 }}>
        <button type="button" onClick={() => onViewModeChange(viewMode === 'globe' ? 'map' : 'globe')}
          style={{ padding: '6px 10px', background: 'rgba(59,130,246,0.12)', border: '1px solid rgba(59,130,246,0.2)',
            borderRadius: '6px', color: '#94a3b8', fontSize: '12px', cursor: 'pointer', fontFamily: 'system-ui', flexShrink: 0 }}>
          {viewMode === 'globe' ? '3D' : '2D'}
        </button>
        <div style={{ width: 1, height: 20, background: 'rgba(51,65,85,0.4)', margin: '0 4px', flexShrink: 0 }} />
        {CATEGORIES.map((cat) => {
          const active = activeCategory === cat.key;
          return (
            <button key={cat.key} type="button"
              onClick={() => onCategoryChange(active ? null : cat.key as ActiveCategory)}
              style={{
                display: 'flex', alignItems: 'center', gap: '4px', padding: '5px 12px',
                fontSize: '11px', fontWeight: active ? 700 : 500, border: '1px solid',
                borderRadius: '16px', cursor: 'pointer', fontFamily: 'system-ui',
                whiteSpace: 'nowrap', flexShrink: 0,
                background: active ? cat.activeColor : 'rgba(30,41,59,0.5)',
                color: active ? '#fff' : '#94a3b8',
                borderColor: active ? cat.activeColor : 'rgba(51,65,85,0.4)',
                transition: 'all 0.2s',
                boxShadow: active ? `0 0 14px ${cat.activeColor}50` : 'none',
              }}>
              <span style={{ fontSize: '13px' }}>{cat.icon}</span>
              <span className="layer-pill-text">{cat.name}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

function Legend({ activeCategory }: { activeCategory: ActiveCategory }) {
  const legends: Record<string, { title: string; gradient: string; labels: string[]; note?: string }> = {
    wildfires: { title: 'Fire Radiative Power (MW)', gradient: 'linear-gradient(to right, rgb(255,230,120), rgb(255,160,20), rgb(220,50,10), rgb(180,20,20))', labels: ['0','50','200','500+'] },
    sst: { title: 'Ocean — SST 7-Day + Current Flow', gradient: 'linear-gradient(to right, rgb(49,54,149), rgb(116,173,209), rgb(253,174,97), rgb(215,48,39), rgb(165,0,38))', labels: ['-2°C','8','18','26','32°C'], note: 'SST cycles 7 days · Particles: currents · Click for temp' },
    'air-quality': { title: 'PM2.5 (µg/m³)', gradient: 'linear-gradient(to right, rgb(0,128,0), rgb(255,255,0), rgb(255,126,0), rgb(255,0,0), rgb(126,0,35))', labels: ['0','12','35','55','75+'] },
    temperature: { title: '2m Temperature (°C)', gradient: 'linear-gradient(to right, rgb(49,54,149), rgb(116,173,209), rgb(171,217,233), rgb(253,174,97), rgb(215,48,39), rgb(165,0,38))', labels: ['-40','-20','0','20','50'] },
    precipitation: { title: 'Precipitation (mm)', gradient: 'linear-gradient(to right, rgba(198,219,239,0.3), rgb(107,174,214), rgb(49,130,189), rgb(8,81,156))', labels: ['0','5','10','20+'] },
    no2: { title: 'NO₂ (µg/m³)', gradient: 'linear-gradient(to right, rgb(255,255,178), rgb(253,141,60), rgb(240,59,32), rgb(189,0,38))', labels: ['0','20','40','80+'] },
  };
  const cfg = activeCategory ? legends[activeCategory] : null;
  if (!cfg) {
    if (activeCategory === 'earthquakes') return (
      <div style={legendStyle}>
        <div style={legendTitleStyle}>Earthquake Magnitude</div>
        <div style={{ display: 'flex', gap: '8px' }}>
          {[{l:'M4',c:'#eab308',s:8},{l:'M5',c:'#f97316',s:10},{l:'M6',c:'#ef4444',s:13},{l:'M7+',c:'#991b1b',s:16}].map(e=>(
            <span key={e.l} style={{display:'inline-flex',alignItems:'center',gap:'3px'}}>
              <span style={{width:e.s,height:e.s,borderRadius:'50%',background:e.c,display:'inline-block'}}/>
              <span style={{fontSize:'10px',color:'#94a3b8'}}>{e.l}</span>
            </span>
          ))}
        </div>
      </div>
    );
    return null;
  }
  return (
    <div style={legendStyle}>
      <div style={legendTitleStyle}>{cfg.title}</div>
      <div style={{ background: cfg.gradient, height: 10, borderRadius: 3 }} />
      <div style={legendLabelsStyle}>{cfg.labels.map((l,i)=><span key={i}>{l}</span>)}</div>
      {cfg.note && <div style={{ marginTop: 4, fontSize: '9px', color: '#64748b' }}>{cfg.note}</div>}
    </div>
  );
}

interface TooltipInfo { x: number; y: number; html: string; pinned?: boolean; }

function Tooltip({ info, onClose }: { info: TooltipInfo | null; onClose: () => void }) {
  if (!info) return null;
  return (
    <div style={{
      position: 'absolute', left: info.x + 14, top: info.y - 14,
      pointerEvents: info.pinned ? 'auto' : 'none',
      background: 'rgba(12,18,32,0.94)', color: '#f1f5f9', padding: '10px 14px',
      border: '1px solid rgba(71,85,105,0.35)', borderRadius: '10px',
      fontSize: '12px', lineHeight: '1.5', fontFamily: 'system-ui',
      maxWidth: 300, zIndex: 25, backdropFilter: 'blur(14px)',
      boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
    }}>
      {info.pinned && <button type="button" onClick={onClose} style={{
        position:'absolute',top:4,right:6,background:'none',border:'none',
        color:'#64748b',cursor:'pointer',fontSize:'14px',padding:'2px'
      }}>✕</button>}
      <div dangerouslySetInnerHTML={{ __html: info.html }} />
    </div>
  );
}

// ─── Surface PNG map ──────────────────────────────────────────────────────────

const SURFACE_LAYERS: Record<string, { url: string; alpha: number }> = {
  'pm25-surface': { url: `${API_BASE}/globe/surface/pm25.png`, alpha: 0.8 },
  'temp-surface': { url: `${API_BASE}/globe/surface/temperature.png`, alpha: 0.8 },
  'precip-surface': { url: `${API_BASE}/globe/surface/precipitation.png`, alpha: 0.75 },
  'no2-surface': { url: `${API_BASE}/globe/surface/no2.png`, alpha: 0.8 },
};

// ─── Main Component ───────────────────────────────────────────────────────────

const GlobeCesium = forwardRef<GlobeHandle, GlobeProps>(function GlobeCesium(
  { activeCategory, onCategoryChange }, ref,
) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cesiumRef = useRef<HTMLDivElement>(null);
  const viewerRef = useRef<Viewer | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>('globe');
  const [tooltipInfo, setTooltipInfo] = useState<TooltipInfo | null>(null);
  const lastInteractionRef = useRef(0);

  // Layer refs
  const surfaceLayerRef = useRef<ImageryLayer | null>(null);
  const gibsLayerRef = useRef<ImageryLayer | null>(null);
  const pointDsRef = useRef<CustomDataSource | null>(null);
  const sstTimerRef = useRef<number>(0);
  const particleCanvasRef = useRef<HTMLCanvasElement>(null);

  // Data fetches
  const needsFires = activeCategory === 'wildfires';
  const needsQuakes = activeCategory === 'earthquakes';
  const needsCurrents = activeCategory === 'sst';
  const { data: firesData, loading: firesLoading } = useApi<FiresResponse>('/earth-now/fires', needsFires);
  const { data: quakeData, loading: quakesLoading } = useApi<EarthquakeResponse>('/hazards/earthquakes?min_magnitude=4&limit=500&days=7', needsQuakes);
  const { data: currentsData } = useApi<OceanCurrentsResponse>('/globe/surface/ocean-currents.json', needsCurrents);

  // ── Viewer init ──────────────────────────────────────────────────────────

  useEffect(() => {
    if (!cesiumRef.current || viewerRef.current) return;
    Ion.defaultAccessToken = CESIUM_TOKEN;

    const viewer = new Viewer(cesiumRef.current, {
      animation: false, timeline: false, homeButton: false, geocoder: false,
      navigationHelpButton: false, baseLayerPicker: false, fullscreenButton: false,
      vrButton: false, selectionIndicator: false, infoBox: false, sceneModePicker: false,
      creditContainer: document.createElement('div'),
    });

    viewer.scene.backgroundColor = Color.fromCssColorString('#020408');
    viewer.scene.globe.enableLighting = false;
    if (viewer.scene.skyAtmosphere) viewer.scene.skyAtmosphere.show = true;
    viewer.scene.fog.enabled = true;
    viewer.scene.fog.density = 0.0002;
    if (viewer.scene.skyBox) (viewer.scene.skyBox as unknown as { show: boolean }).show = false;
    if (viewer.scene.sun) viewer.scene.sun.show = false;
    if (viewer.scene.moon) viewer.scene.moon.show = false;
    viewer.scene.globe.atmosphereLightIntensity = 20.0;
    viewer.scene.globe.atmosphereRayleighCoefficient = new Cartesian3(5.5e-6, 13.0e-6, 28.4e-6);
    viewer.camera.setView({ destination: Cartesian3.fromDegrees(0, 20, 20000000) });

    // Hover
    const handler = new ScreenSpaceEventHandler(viewer.scene.canvas);
    handler.setInputAction((m: { endPosition: { x: number; y: number } }) => {
      lastInteractionRef.current = Date.now();
      const picked = viewer.scene.pick(new Cartesian2(m.endPosition.x, m.endPosition.y));
      if (defined(picked) && picked.id instanceof Entity && picked.id.properties) {
        const p = picked.id.properties;
        const t = p.type?.getValue() as string | undefined;
        let html = '';
        if (t === 'fire') html = `<b>Fire</b><br/>FRP: ${p.frp?.getValue()?.toFixed(1)} MW<br/>${p.lat?.getValue()?.toFixed(2)}°, ${p.lon?.getValue()?.toFixed(2)}°`;
        else if (t === 'earthquake') html = `<b>M${p.magnitude?.getValue()?.toFixed(1)}</b> — ${p.place?.getValue()}<br/>Depth: ${p.depth_km?.getValue()?.toFixed(1)} km`;
        if (html) setTooltipInfo(prev => prev?.pinned ? prev : { x: m.endPosition.x, y: m.endPosition.y, html });
        else setTooltipInfo(prev => prev?.pinned ? prev : null);
      } else setTooltipInfo(prev => prev?.pinned ? prev : null);
    }, ScreenSpaceEventType.MOUSE_MOVE);

    // Click for SST
    handler.setInputAction((c: { position: { x: number; y: number } }) => {
      lastInteractionRef.current = Date.now();
      const ray = viewer.camera.getPickRay(new Cartesian2(c.position.x, c.position.y));
      if (!ray) return;
      const cart = viewer.scene.globe.pick(ray, viewer.scene);
      if (!cart) { setTooltipInfo(null); return; }
      const carto = Cartographic.fromCartesian(cart);
      const lat = CesiumMath.toDegrees(carto.latitude);
      const lon = CesiumMath.toDegrees(carto.longitude);
      const coordStr = `${Math.abs(lat).toFixed(1)}°${lat>=0?'N':'S'}, ${Math.abs(lon).toFixed(1)}°${lon>=0?'E':'W'}`;
      // Show loading tooltip immediately
      setTooltipInfo({ x: c.position.x, y: c.position.y, html: `<b>${coordStr}</b><br/><span style="color:#64748b">Loading SST…</span>`, pinned: true });
      // Fetch real SST from backend OISST
      fetch(`${API_BASE}/globe/surface/sst-at-point?lat=${lat.toFixed(2)}&lon=${lon.toFixed(2)}`)
        .then(r => r.json())
        .then(data => {
          const html = data.sst_c != null
            ? `<b>${coordStr}</b><br/>SST: <b style="color:${data.sst_c>25?'#ef4444':data.sst_c>15?'#f97316':data.sst_c>5?'#3b82f6':'#6366f1'}">${data.sst_c}°C</b><br/><span style="color:#64748b;font-size:10px">NOAA OISST v2.1</span>`
            : `<b>${coordStr}</b><br/><span style="color:#64748b">Land or ice — no SST</span>`;
          setTooltipInfo({ x: c.position.x, y: c.position.y, html, pinned: true });
        })
        .catch(() => {
          setTooltipInfo({ x: c.position.x, y: c.position.y, html: `<b>${coordStr}</b><br/><span style="color:#64748b">SST unavailable</span>`, pinned: true });
        });
    }, ScreenSpaceEventType.LEFT_CLICK);

    handler.setInputAction(() => { lastInteractionRef.current = Date.now(); }, ScreenSpaceEventType.LEFT_DOWN);
    handler.setInputAction(() => { lastInteractionRef.current = Date.now(); }, ScreenSpaceEventType.WHEEL);
    viewerRef.current = viewer;
    return () => { handler.destroy(); viewer.destroy(); viewerRef.current = null; };
  }, []);

  useImperativeHandle(ref, () => ({
    flyTo: (lat, lng, alt = 1.8) => viewerRef.current?.camera.flyTo({ destination: Cartesian3.fromDegrees(lng, lat, alt * 6371000), duration: 1.5 }),
  }), []);

  // Auto-rotate
  useEffect(() => {
    if (viewMode !== 'globe') return;
    let id: number;
    const r = () => { if (viewerRef.current && Date.now() - lastInteractionRef.current > 8000) viewerRef.current.scene.camera.rotateRight(0.001); id = requestAnimationFrame(r); };
    id = requestAnimationFrame(r);
    return () => cancelAnimationFrame(id);
  }, [viewMode]);

  // View mode
  useEffect(() => { const v = viewerRef.current; if (!v) return; viewMode === 'globe' ? v.scene.morphTo3D(1) : v.scene.morphTo2D(1); }, [viewMode]);

  const activeLayers = useMemo(() => new Set(CATEGORIES.find(c => c.key === activeCategory)?.activates ?? []), [activeCategory]);

  // ── Layer management ─────────────────────────────────────────────────────

  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer) return;

    // Cleanup
    if (surfaceLayerRef.current) { viewer.imageryLayers.remove(surfaceLayerRef.current); surfaceLayerRef.current = null; }
    if (gibsLayerRef.current) { viewer.imageryLayers.remove(gibsLayerRef.current); gibsLayerRef.current = null; }
    if (pointDsRef.current) { viewer.dataSources.remove(pointDsRef.current); pointDsRef.current = null; }
    if (sstTimerRef.current) { clearInterval(sstTimerRef.current); sstTimerRef.current = 0; }

    // Self-rendered surfaces (PM2.5, Temp, Precip, NO₂)
    for (const [key, cfg] of Object.entries(SURFACE_LAYERS)) {
      if (activeLayers.has(key)) {
        (async () => {
          const layer = await addSingleTileLayer(viewer, cfg.url, cfg.alpha);
          if (layer) surfaceLayerRef.current = layer;
        })();
        break;
      }
    }

    // SST advection animation — SST data moves with ocean currents
    // Backend renders 8 frames of SST advected by flow field
    if (activeLayers.has('sst-surface')) {
      const NUM_FRAMES = 8;

      // Load first frame immediately
      (async () => {
        const layer = await addSingleTileLayer(viewer, `${API_BASE}/globe/surface/sst-advected/0.png`, 0.85);
        if (layer) surfaceLayerRef.current = layer;
      })();

      // Cycle through advection frames every 1.5 seconds
      let idx = 0;
      sstTimerRef.current = window.setInterval(() => {
        const v = viewerRef.current;
        if (!v) return;
        idx = (idx + 1) % NUM_FRAMES;
        (async () => {
          if (surfaceLayerRef.current) v.imageryLayers.remove(surfaceLayerRef.current);
          const layer = await addSingleTileLayer(v, `${API_BASE}/globe/surface/sst-advected/${idx}.png`, 0.85);
          if (layer) surfaceLayerRef.current = layer;
        })();
      }, 1500);
    }

    // GIBS CO₂
    if (activeLayers.has('gibs-oco2')) {
      const d = getGibsDate();
      const url = 'https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi' +
        '?SERVICE=WMS&REQUEST=GetMap&VERSION=1.1.1&LAYERS=OCO2_L2_CO2_Total_Column_Day' +
        `&TIME=${d}&BBOX=-180,-90,180,90&WIDTH=4096&HEIGHT=2048&SRS=EPSG:4326&FORMAT=image/png&TRANSPARENT=TRUE&STYLES=`;
      (async () => {
        const layer = await addSingleTileLayer(viewer, url, 0.6);
        if (layer) gibsLayerRef.current = layer;
      })();
    }

    // Fires
    if (activeLayers.has('fires') && firesData?.fires) {
      const ds = new CustomDataSource('fires');
      for (const f of firesData.fires) {
        ds.entities.add({
          position: Cartesian3.fromDegrees(f.lon, f.lat),
          point: { pixelSize: Math.max(3, Math.min(12, 3 + Math.log10(Math.max(f.frp, 1)) * 3)), color: fireColor(f.frp), outlineWidth: 0, heightReference: HeightReference.CLAMP_TO_GROUND, scaleByDistance: new NearFarScalar(1.5e6, 1, 1.5e7, 0.4) },
          properties: { type: 'fire', frp: f.frp, lat: f.lat, lon: f.lon, acq_date: f.acq_date, acq_time: f.acq_time },
        });
      }
      viewer.dataSources.add(ds);
      pointDsRef.current = ds;
    }

    // Earthquakes
    if (activeLayers.has('earthquakes') && quakeData?.earthquakes) {
      const ds = new CustomDataSource('quakes');
      for (const e of quakeData.earthquakes) {
        ds.entities.add({
          position: Cartesian3.fromDegrees(e.lon, e.lat),
          point: { pixelSize: Math.max(4, 4 + (e.magnitude - 4) * 4), color: earthquakeColor(e.magnitude), outlineColor: Color.WHITE.withAlpha(0.4), outlineWidth: 1, heightReference: HeightReference.CLAMP_TO_GROUND, scaleByDistance: new NearFarScalar(1.5e6, 1, 1.5e7, 0.4) },
          properties: { type: 'earthquake', magnitude: e.magnitude, place: e.place, depth_km: e.depth_km, time_utc: e.time_utc, tsunami: e.tsunami },
        });
      }
      viewer.dataSources.add(ds);
      pointDsRef.current = ds;
    }
  }, [activeLayers, firesData, quakeData]);

  // ── Particle animation (postRender) ──────────────────────────────────────

  useEffect(() => {
    const viewer = viewerRef.current;
    const canvas = particleCanvasRef.current;
    if (!viewer || !canvas || !activeLayers.has('ocean-currents')) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const container = containerRef.current;
    if (container) { canvas.width = container.clientWidth; canvas.height = container.clientHeight - 48; }

    // API data lookup
    const grid = new Map<string, OceanCurrentPoint>();
    if (currentsData?.points) for (const p of currentsData.points) grid.set(`${Math.round(p.lat/5)*5},${Math.round(p.lon/5)*5}`, p);

    function flow(lat: number, lon: number): [number, number] {
      const api = grid.get(`${Math.round(lat/5)*5},${Math.round(lon/5)*5}`);
      if (api && api.v > 0.05) { const r = api.d * Math.PI / 180; return [api.v * 0.2 * Math.sin(r), api.v * 0.2 * Math.cos(r)]; }
      const a = Math.abs(lat);
      if (lat < -45 && lat > -65) return [0.12, 0];
      if (a < 30) return [-0.06 * (1 - a/30), lat > 0 ? -0.008 : 0.008];
      if (a < 60) return [0.05 * Math.sin((a-30)/30*Math.PI), lat > 0 ? 0.008 : -0.008];
      return [-0.015, 0];
    }

    const N = 2500, MAX = 70, TL = 6;
    interface Pt { lon: number; lat: number; age: number; tr: {x:number;y:number}[]; }
    const pts: Pt[] = Array.from({length:N}, () => ({ lon: Math.random()*360-180, lat: Math.random()*140-70, age: Math.floor(Math.random()*MAX), tr:[] }));
    const cn = new Cartesian3(), pn = new Cartesian3();

    const v = viewer; // non-null capture
    function tick() {
      if (!ctx || !canvas || !v) return;
      const w = canvas.width, h = canvas.height;
      ctx.clearRect(0, 0, w, h);
      Cartesian3.normalize(v.camera.positionWC, cn);

      for (const p of pts) {
        const wc = Cartesian3.fromDegrees(p.lon, p.lat);
        Cartesian3.normalize(wc, pn);
        if (Cartesian3.dot(pn, cn) < 0.15 || p.age >= MAX) { p.lon=Math.random()*360-180; p.lat=Math.random()*140-70; p.age=0; p.tr=[]; continue; }

        const [du, dv] = flow(p.lat, p.lon);
        p.lon += du; p.lat += dv;
        if (p.lon > 180) p.lon -= 360; if (p.lon < -180) p.lon += 360;
        if (Math.abs(p.lat) > 70) { p.age = MAX; continue; }

        const sc = v.scene.cartesianToCanvasCoordinates(wc);
        if (!sc || sc.x<0 || sc.x>w || sc.y<0 || sc.y>h) { p.age=MAX; continue; }

        p.tr.push({x:sc.x, y:sc.y}); if (p.tr.length > TL) p.tr.shift();

        if (p.tr.length > 1) {
          const t = 1 - Math.abs(p.lat)/70;
          const cr = 60+t*195|0, cg = 120+t*80|0, cb = 210-t*170|0;
          for (let s = 1; s < p.tr.length; s++) {
            const a = (s/p.tr.length) * 0.55 * (1 - p.age/MAX);
            ctx.strokeStyle = `rgba(${cr},${cg},${cb},${a})`; ctx.lineWidth = 1.2;
            ctx.beginPath(); ctx.moveTo(p.tr[s-1].x, p.tr[s-1].y); ctx.lineTo(p.tr[s].x, p.tr[s].y); ctx.stroke();
          }
        }
        p.age++;
      }
    }

    v.scene.postRender.addEventListener(tick);
    return () => { v.scene.postRender.removeEventListener(tick); ctx.clearRect(0,0,canvas.width,canvas.height); };
  }, [activeLayers, currentsData]);

  // ── Render ───────────────────────────────────────────────────────────────

  const activeCatDef = activeCategory ? CATEGORY_LOOKUP.get(activeCategory) ?? null : null;
  const dataCount = useMemo(() => {
    if (activeCategory === 'wildfires') return firesData?.fires?.length ?? 0;
    if (activeCategory === 'earthquakes') return quakeData?.earthquakes?.length ?? 0;
    return 0;
  }, [activeCategory, firesData, quakeData]);
  const isLoading = (needsFires && firesLoading) || (needsQuakes && quakesLoading);

  return (
    <div ref={containerRef} style={containerStyle}>
      <div ref={cesiumRef} style={{ width: '100%', height: '100%', position: 'relative', zIndex: 1 }} />

      <canvas ref={particleCanvasRef} style={{
        position: 'absolute', top: 0, left: 0, right: 0, bottom: 48,
        zIndex: 2, pointerEvents: 'none',
        display: activeLayers.has('ocean-currents') ? 'block' : 'none',
      }} />

      <div style={{ position: 'absolute', inset: 0, zIndex: 3, pointerEvents: 'none', boxShadow: 'inset 0 0 120px 40px rgba(2,4,8,0.4)' }} />

      {isLoading && (
        <div style={{ position: 'absolute', inset: 0, zIndex: 5, display: 'flex', alignItems: 'center', justifyContent: 'center', pointerEvents: 'none' }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ width: 28, height: 28, borderRadius: '50%', border: '2px solid #1e293b', borderTopColor: activeCatDef?.activeColor ?? '#3b82f6', animation: 'spin 0.8s linear infinite', margin: '0 auto 8px' }} />
            <div style={{ color: '#64748b', fontSize: '11px', fontFamily: 'system-ui' }}>Loading {activeCatDef?.name ?? 'data'}…</div>
          </div>
        </div>
      )}

      <Tooltip info={tooltipInfo} onClose={() => setTooltipInfo(null)} />

      {activeCatDef && (
        <div style={{ position: 'absolute', top: 12, left: '50%', transform: 'translateX(-50%)', zIndex: 10,
          background: 'rgba(10,14,26,0.75)', backdropFilter: 'blur(12px)', border: '1px solid rgba(51,65,85,0.3)',
          borderRadius: '20px', padding: '5px 16px', fontSize: '12px', color: '#cbd5e1', fontFamily: 'system-ui',
          display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '14px' }}>{activeCatDef.icon}</span>
          <span style={{ fontWeight: 600 }}>{activeCatDef.name}</span>
          {dataCount > 0 && <span style={{ color: '#64748b', fontSize: '11px' }}>{dataCount.toLocaleString()}</span>}
          <span style={{ color: '#475569', fontSize: '10px' }}>{activeCatDef.question}</span>
        </div>
      )}

      {activeCatDef && (
        <div style={metaOverlayStyle}>
          <MetaLine cadence={activeCatDef.cadence} tag={activeCatDef.tag} source={activeCatDef.source} sourceUrl={activeCatDef.sourceUrl} />
        </div>
      )}

      <Legend activeCategory={activeCategory} />
      <LayerBar activeCategory={activeCategory} onCategoryChange={onCategoryChange} viewMode={viewMode} onViewModeChange={setViewMode} />
    </div>
  );
});

export default GlobeCesium;

// ─── Styles ───────────────────────────────────────────────────────────────────

const containerStyle: React.CSSProperties = { position: 'relative', width: '100%', height: '100%', background: '#020408', overflow: 'hidden' };
const metaOverlayStyle: React.CSSProperties = { position: 'absolute', top: 12, left: 12, zIndex: 10, background: 'rgba(10,14,26,0.5)', padding: '5px 10px', borderRadius: '6px', backdropFilter: 'blur(8px)', pointerEvents: 'none', border: '1px solid rgba(51,65,85,0.2)' };
const layerBarStyle: React.CSSProperties = { position: 'absolute', bottom: 0, left: 0, right: 0, zIndex: 15, background: 'rgba(10,14,26,0.85)', backdropFilter: 'blur(12px)', borderTop: '1px solid rgba(51,65,85,0.3)', padding: '8px 16px' };
const legendStyle: React.CSSProperties = { position: 'absolute', bottom: 60, left: 12, zIndex: 10, background: 'rgba(10,14,26,0.82)', backdropFilter: 'blur(8px)', border: '1px solid rgba(51,65,85,0.4)', borderRadius: '8px', padding: '8px 12px', minWidth: 160, maxWidth: 260 };
const legendTitleStyle: React.CSSProperties = { fontSize: '11px', fontWeight: 600, color: '#cbd5e1', marginBottom: 6, fontFamily: 'system-ui' };
const legendLabelsStyle: React.CSSProperties = { display: 'flex', justifyContent: 'space-between', fontSize: '9px', color: '#64748b', marginTop: 2, fontFamily: 'system-ui' };
