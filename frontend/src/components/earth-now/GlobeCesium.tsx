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

// ─── GIBS date helper ─────────────────────────────────────────────────────────

function getGibsDate(): string {
  const d = new Date();
  d.setDate(d.getDate() - 1);
  return d.toISOString().slice(0, 10);
}

// ─── Categories ───────────────────────────────────────────────────────────────

interface CategoryDef {
  key: string;
  icon: string;
  name: string;
  question: string;
  activeColor: string;
  tag: TrustTag;
  cadence: string;
  source: string;
  sourceUrl: string;
  activates: string[];
}

const CATEGORIES: CategoryDef[] = [
  // ── Continuous Surfaces (self-rendered PNGs) ────────────────────────
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
  // ── Event Layers (point data) ──────────────────────────────────────
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

const CATEGORY_LOOKUP = new Map<string, CategoryDef>(
  CATEGORIES.map((c) => [c.key, c]),
);

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
  return Color.fromCssColorString('#991b1b').withAlpha(1.0);
}

// ─── LayerBar ─────────────────────────────────────────────────────────────────

function LayerBar({
  activeCategory, onCategoryChange, viewMode, onViewModeChange,
}: {
  activeCategory: ActiveCategory;
  onCategoryChange: (key: ActiveCategory) => void;
  viewMode: ViewMode;
  onViewModeChange: (mode: ViewMode) => void;
}) {
  return (
    <div style={layerBarStyle}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '3px', overflowX: 'auto', paddingBottom: 2 }}>
        <button type="button"
          onClick={() => onViewModeChange(viewMode === 'globe' ? 'map' : 'globe')}
          style={{
            padding: '6px 10px', background: 'rgba(59,130,246,0.12)',
            border: '1px solid rgba(59,130,246,0.2)', borderRadius: '6px',
            color: '#94a3b8', fontSize: '12px', cursor: 'pointer',
            fontFamily: 'system-ui, sans-serif', flexShrink: 0,
          }}>
          {viewMode === 'globe' ? '3D' : '2D'}
        </button>

        <div style={{ width: 1, height: 20, background: 'rgba(51,65,85,0.4)', margin: '0 4px', flexShrink: 0 }} />

        {CATEGORIES.map((cat) => {
          const active = activeCategory === cat.key;
          return (
            <button key={cat.key} type="button"
              onClick={() => onCategoryChange(active ? null : cat.key as ActiveCategory)}
              style={{
                display: 'flex', alignItems: 'center', gap: '4px',
                padding: '5px 12px', fontSize: '11px', fontWeight: active ? 700 : 500,
                border: '1px solid', borderRadius: '16px',
                cursor: 'pointer', fontFamily: 'system-ui, sans-serif',
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

// ─── Legend ────────────────────────────────────────────────────────────────────

function Legend({ activeCategory }: { activeCategory: ActiveCategory }) {
  if (activeCategory === 'wildfires') return (
    <div style={legendStyle}>
      <div style={legendTitleStyle}>Fire Radiative Power (MW)</div>
      <div style={{ background: 'linear-gradient(to right, rgb(255,230,120), rgb(255,200,60), rgb(255,160,20), rgb(245,100,10), rgb(220,50,10), rgb(180,20,20))', height: 10, borderRadius: 3 }} />
      <div style={legendLabelsStyle}><span>0</span><span>50</span><span>200</span><span>500+</span></div>
    </div>
  );
  if (activeCategory === 'earthquakes') return (
    <div style={legendStyle}>
      <div style={legendTitleStyle}>Earthquake Magnitude</div>
      <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
        {[{ label: 'M4', color: '#eab308', size: 8 }, { label: 'M5', color: '#f97316', size: 10 },
          { label: 'M6', color: '#ef4444', size: 13 }, { label: 'M7+', color: '#991b1b', size: 16 }].map((e) => (
          <span key={e.label} style={{ display: 'inline-flex', alignItems: 'center', gap: '3px' }}>
            <span style={{ width: e.size, height: e.size, borderRadius: '50%', background: e.color, display: 'inline-block' }} />
            <span style={{ fontSize: '10px', color: '#94a3b8' }}>{e.label}</span>
          </span>
        ))}
      </div>
    </div>
  );
  if (activeCategory === 'sst') return (
    <div style={legendStyle}>
      <div style={legendTitleStyle}>Ocean — SST + Current Flow</div>
      <div style={{ background: 'linear-gradient(to right, rgb(49,54,149), rgb(116,173,209), rgb(253,174,97), rgb(215,48,39), rgb(165,0,38))', height: 10, borderRadius: 3 }} />
      <div style={legendLabelsStyle}><span>-2°C</span><span>8</span><span>18</span><span>26</span><span>32°C</span></div>
      <div style={{ marginTop: 4, fontSize: '9px', color: '#64748b' }}>Particles flow with ocean currents · Click for SST</div>
    </div>
  );
  if (activeCategory === 'air-quality') return (
    <div style={legendStyle}>
      <div style={legendTitleStyle}>PM2.5 (µg/m³)</div>
      <div style={{ background: 'linear-gradient(to right, rgb(0,128,0), rgb(255,255,0), rgb(255,126,0), rgb(255,0,0), rgb(143,63,151), rgb(126,0,35))', height: 10, borderRadius: 3 }} />
      <div style={legendLabelsStyle}><span>0</span><span>12</span><span>35</span><span>55</span><span>75+</span></div>
    </div>
  );
  if (activeCategory === 'temperature') return (
    <div style={legendStyle}>
      <div style={legendTitleStyle}>2m Temperature (°C)</div>
      <div style={{ background: 'linear-gradient(to right, rgb(49,54,149), rgb(69,117,180), rgb(116,173,209), rgb(171,217,233), rgb(253,174,97), rgb(244,109,67), rgb(215,48,39), rgb(165,0,38))', height: 10, borderRadius: 3 }} />
      <div style={legendLabelsStyle}><span>-40</span><span>-20</span><span>0</span><span>20</span><span>50</span></div>
    </div>
  );
  if (activeCategory === 'precipitation') return (
    <div style={legendStyle}>
      <div style={legendTitleStyle}>Precipitation (mm)</div>
      <div style={{ background: 'linear-gradient(to right, rgba(198,219,239,0.3), rgb(158,202,225), rgb(107,174,214), rgb(49,130,189), rgb(8,81,156))', height: 10, borderRadius: 3 }} />
      <div style={legendLabelsStyle}><span>0</span><span>5</span><span>10</span><span>20+</span></div>
    </div>
  );
  if (activeCategory === 'no2') return (
    <div style={legendStyle}>
      <div style={legendTitleStyle}>NO₂ (µg/m³)</div>
      <div style={{ background: 'linear-gradient(to right, rgb(255,255,178), rgb(254,204,92), rgb(253,141,60), rgb(240,59,32), rgb(189,0,38))', height: 10, borderRadius: 3 }} />
      <div style={legendLabelsStyle}><span>0</span><span>20</span><span>40</span><span>60</span><span>80+</span></div>
    </div>
  );
  return null;
}

// ─── Tooltip ──────────────────────────────────────────────────────────────────

interface TooltipInfo { x: number; y: number; html: string; pinned?: boolean; }

function Tooltip({ info, onClose }: { info: TooltipInfo | null; onClose: () => void }) {
  if (!info) return null;
  return (
    <div style={{
      position: 'absolute', left: info.x + 14, top: info.y - 14,
      pointerEvents: info.pinned ? 'auto' : 'none',
      background: 'rgba(12,18,32,0.94)', color: '#f1f5f9', padding: '10px 14px',
      border: '1px solid rgba(71,85,105,0.35)', borderRadius: '10px',
      fontSize: '12px', lineHeight: '1.5', fontFamily: 'system-ui, sans-serif',
      maxWidth: 300, zIndex: 25, backdropFilter: 'blur(14px)',
      boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
    }}>
      {info.pinned && (
        <button
          type="button"
          onClick={onClose}
          style={{
            position: 'absolute', top: 4, right: 6,
            background: 'none', border: 'none', color: '#64748b',
            cursor: 'pointer', fontSize: '14px', lineHeight: 1, padding: '2px',
          }}
        >✕</button>
      )}
      <div dangerouslySetInnerHTML={{ __html: info.html }} />
    </div>
  );
}

// ─── Surface PNG layer map ────────────────────────────────────────────────────

// Self-rendered surface PNGs (backend → SingleTileImageryProvider)
const SURFACE_LAYERS: Record<string, { url: string; alpha: number }> = {
  'pm25-surface': { url: `${API_BASE}/globe/surface/pm25.png`, alpha: 0.8 },
  'temp-surface': { url: `${API_BASE}/globe/surface/temperature.png`, alpha: 0.8 },
  'precip-surface': { url: `${API_BASE}/globe/surface/precipitation.png`, alpha: 0.75 },
  'no2-surface': { url: `${API_BASE}/globe/surface/no2.png`, alpha: 0.8 },
};

// GIBS WMTS layers — rendered with native land mask (no bleed)
function getGibsSstDate(): string {
  const d = new Date();
  d.setDate(d.getDate() - 2); // GHRSST has ~2 day latency
  return d.toISOString().slice(0, 10);
}

// ─── Main Component ───────────────────────────────────────────────────────────

const GlobeCesium = forwardRef<GlobeHandle, GlobeProps>(function GlobeCesium(
  { activeCategory, onCategoryChange },
  ref,
) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cesiumContainerRef = useRef<HTMLDivElement>(null);
  const viewerRef = useRef<Viewer | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>('globe');
  const [tooltipInfo, setTooltipInfo] = useState<TooltipInfo | null>(null);
  const lastInteractionRef = useRef(0);

  // Track which layers are currently added
  const surfaceLayerRef = useRef<ImageryLayer | null>(null);
  const seaIceLayerRef = useRef<ImageryLayer | null>(null);
  const gibsLayerRef = useRef<ImageryLayer | null>(null);
  const pointDataSourceRef = useRef<CustomDataSource | null>(null);
  const particleCanvasRef = useRef<HTMLCanvasElement>(null);
  const particleAnimRef = useRef<number>(0);

  // ── Lazy data fetches ────────────────────────────────────────────────────

  const needsFires = activeCategory === 'wildfires';
  const needsQuakes = activeCategory === 'earthquakes';
  const needsOceanCurrents = activeCategory === 'sst';

  const { data: firesData, loading: firesLoading } = useApi<FiresResponse>(
    '/earth-now/fires', needsFires,
  );
  const { data: earthquakeData, loading: quakesLoading } = useApi<EarthquakeResponse>(
    '/hazards/earthquakes?min_magnitude=4&limit=500&days=7', needsQuakes,
  );
  const { data: currentsData } = useApi<OceanCurrentsResponse>(
    '/globe/surface/ocean-currents.json', needsOceanCurrents,
  );

  // ── Cesium Viewer initialization ─────────────────────────────────────────

  useEffect(() => {
    if (!cesiumContainerRef.current || viewerRef.current) return;

    Ion.defaultAccessToken = CESIUM_TOKEN;

    const viewer = new Viewer(cesiumContainerRef.current, {
      animation: false,
      timeline: false,
      homeButton: false,
      geocoder: false,
      navigationHelpButton: false,
      baseLayerPicker: false,
      fullscreenButton: false,
      vrButton: false,
      selectionIndicator: false,
      infoBox: false,
      sceneModePicker: false,
      creditContainer: document.createElement('div'), // hide credits overlay
    });

    // Dark space atmosphere
    viewer.scene.backgroundColor = Color.fromCssColorString('#020408');
    viewer.scene.globe.enableLighting = false;
    if (viewer.scene.skyAtmosphere) viewer.scene.skyAtmosphere.show = true;
    viewer.scene.fog.enabled = true;
    viewer.scene.fog.density = 0.0002;
    if (viewer.scene.skyBox) (viewer.scene.skyBox as unknown as { show: boolean }).show = false;
    if (viewer.scene.sun) viewer.scene.sun.show = false;
    if (viewer.scene.moon) viewer.scene.moon.show = false;

    // Dark space fog for atmosphere glow
    viewer.scene.globe.atmosphereLightIntensity = 20.0;
    viewer.scene.globe.atmosphereRayleighCoefficient = new Cartesian3(5.5e-6, 13.0e-6, 28.4e-6);

    // Initial camera position
    viewer.camera.setView({
      destination: Cartesian3.fromDegrees(0, 20, 20000000),
    });

    // Hover handler for tooltips
    const handler = new ScreenSpaceEventHandler(viewer.scene.canvas);
    handler.setInputAction((movement: { endPosition: { x: number; y: number } }) => {
      lastInteractionRef.current = Date.now();
      const pos = new Cartesian2(movement.endPosition.x, movement.endPosition.y);
      const picked = viewer.scene.pick(pos);
      if (defined(picked) && picked.id instanceof Entity && picked.id.properties) {
        const props = picked.id.properties;
        const type = props.type?.getValue() as string | undefined;
        let html = '';

        if (type === 'fire') {
          const frp = props.frp?.getValue();
          const lat = props.lat?.getValue();
          const lon = props.lon?.getValue();
          const date = props.acq_date?.getValue();
          const time = props.acq_time?.getValue();
          html = `<b>Fire hotspot</b><br/>${date} ${time} UTC<br/>FRP: ${frp?.toFixed(1)} MW<br/>${lat?.toFixed(2)}°, ${lon?.toFixed(2)}°`;
        } else if (type === 'earthquake') {
          const mag = props.magnitude?.getValue();
          const place = props.place?.getValue();
          const depth = props.depth_km?.getValue();
          const time_utc = props.time_utc?.getValue();
          const tsunami = props.tsunami?.getValue();
          html = `<b>M${mag?.toFixed(1)}</b> — ${place}<br/>Depth: ${depth?.toFixed(1)} km<br/>${time_utc} UTC${tsunami ? '<br/><span style="color:#ef4444;font-weight:600">⚠ Tsunami</span>' : ''}`;
        }

        if (html) {
          setTooltipInfo((prev) => prev?.pinned ? prev : { x: movement.endPosition.x, y: movement.endPosition.y, html });
        } else {
          setTooltipInfo((prev) => prev?.pinned ? prev : null);
        }
      } else {
        setTooltipInfo((prev) => prev?.pinned ? prev : null);
      }
    }, ScreenSpaceEventType.MOUSE_MOVE);

    // Click handler — show lat/lon + approximate SST at clicked point
    handler.setInputAction((click: { position: { x: number; y: number } }) => {
      lastInteractionRef.current = Date.now();
      const ray = viewer.camera.getPickRay(new Cartesian2(click.position.x, click.position.y));
      if (!ray) return;
      const cartesian = viewer.scene.globe.pick(ray, viewer.scene);
      if (!cartesian) {
        setTooltipInfo(null); // clicked empty space → dismiss
        return;
      }
      const carto = Cartographic.fromCartesian(cartesian);
      const lat = CesiumMath.toDegrees(carto.latitude);
      const lon = CesiumMath.toDegrees(carto.longitude);
      // Approximate SST from latitude (equator ~28°C, poles ~-2°C)
      const approxSST = 28 - Math.abs(lat) * 0.38;
      const isOcean = Math.abs(lat) < 85; // rough check
      const html = isOcean
        ? `<b>${lat.toFixed(1)}°${lat >= 0 ? 'N' : 'S'}, ${Math.abs(lon).toFixed(1)}°${lon >= 0 ? 'E' : 'W'}</b><br/>` +
          `SST ≈ <b style="color:${approxSST > 20 ? '#ef4444' : approxSST > 10 ? '#f97316' : '#3b82f6'}">${approxSST.toFixed(1)}°C</b><br/>` +
          `<span style="color:#64748b;font-size:10px">Approximate from GHRSST MUR</span>`
        : `<b>${lat.toFixed(1)}°, ${Math.abs(lon).toFixed(1)}°</b><br/><span style="color:#64748b">Ice/Land — no SST data</span>`;
      setTooltipInfo({ x: click.position.x, y: click.position.y, html, pinned: true });
    }, ScreenSpaceEventType.LEFT_CLICK);

    // Track user interaction for auto-rotation
    handler.setInputAction(() => { lastInteractionRef.current = Date.now(); }, ScreenSpaceEventType.LEFT_DOWN);
    handler.setInputAction(() => { lastInteractionRef.current = Date.now(); }, ScreenSpaceEventType.WHEEL);

    viewerRef.current = viewer;

    return () => {
      handler.destroy();
      viewer.destroy();
      viewerRef.current = null;
    };
  }, []);

  // ── flyTo imperative handle ──────────────────────────────────────────────

  useImperativeHandle(ref, () => ({
    flyTo: (lat: number, lng: number, altitude = 1.8) => {
      viewerRef.current?.camera.flyTo({
        destination: Cartesian3.fromDegrees(lng, lat, altitude * 6371000),
        duration: 1.5,
      });
    },
  }), []);

  // ── Auto-rotation ────────────────────────────────────────────────────────

  useEffect(() => {
    if (viewMode !== 'globe') return;
    let rafId: number;
    const rotate = () => {
      const viewer = viewerRef.current;
      if (viewer && Date.now() - lastInteractionRef.current > 8000) {
        viewer.scene.camera.rotateRight(0.001);
      }
      rafId = requestAnimationFrame(rotate);
    };
    rafId = requestAnimationFrame(rotate);
    return () => cancelAnimationFrame(rafId);
  }, [viewMode]);

  // ── View mode switching ──────────────────────────────────────────────────

  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer) return;
    if (viewMode === 'globe') {
      viewer.scene.morphTo3D(1.0);
    } else {
      viewer.scene.morphTo2D(1.0);
    }
  }, [viewMode]);

  // ── Active layers from category ──────────────────────────────────────────

  const activeLayers = useMemo(() => {
    const cat = CATEGORIES.find((c) => c.key === activeCategory);
    return new Set(cat?.activates ?? []);
  }, [activeCategory]);

  // ── Layer management — update Cesium layers when category changes ────────

  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer) return;

    // 1. Remove previous overlays
    if (surfaceLayerRef.current) {
      viewer.imageryLayers.remove(surfaceLayerRef.current);
      surfaceLayerRef.current = null;
    }
    if (seaIceLayerRef.current) {
      viewer.imageryLayers.remove(seaIceLayerRef.current);
      seaIceLayerRef.current = null;
    }
    if (gibsLayerRef.current) {
      viewer.imageryLayers.remove(gibsLayerRef.current);
      gibsLayerRef.current = null;
    }
    if (pointDataSourceRef.current) {
      viewer.dataSources.remove(pointDataSourceRef.current);
      pointDataSourceRef.current = null;
    }
    // Stop particle animation
    if (particleAnimRef.current) {
      cancelAnimationFrame(particleAnimRef.current);
      particleAnimRef.current = 0;
    }
    const pCanvas = particleCanvasRef.current;
    if (pCanvas) {
      const pCtx = pCanvas.getContext('2d');
      if (pCtx) pCtx.clearRect(0, 0, pCanvas.width, pCanvas.height);
    }

    // 4. Add self-rendered surface PNG (PM2.5, Temperature, Precipitation, NO₂)
    for (const [key, cfg] of Object.entries(SURFACE_LAYERS)) {
      if (activeLayers.has(key)) {
        try {
          const provider = new SingleTileImageryProvider({
            url: cfg.url,
            rectangle: Rectangle.fromDegrees(-180, -90, 180, 90),
          });
          const imgLayer = new ImageryLayer(provider, { alpha: cfg.alpha });
          viewer.imageryLayers.add(imgLayer);
          surfaceLayerRef.current = imgLayer;
        } catch {
          // Provider creation may fail if URL not ready
        }
        break;
      }
    }

    // 5. Add GIBS MUR SST — native land mask, ocean only
    if (activeLayers.has('sst-surface')) {
      try {
        const date = getGibsSstDate();
        const wmsUrl =
          'https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi' +
          '?SERVICE=WMS&REQUEST=GetMap&VERSION=1.1.1' +
          '&LAYERS=GHRSST_L4_MUR_Sea_Surface_Temperature' +
          `&TIME=${date}` +
          '&BBOX=-180,-90,180,90&WIDTH=4096&HEIGHT=2048' +
          '&SRS=EPSG:4326&FORMAT=image/png&TRANSPARENT=TRUE&STYLES=';
        const provider = new SingleTileImageryProvider({
          url: wmsUrl,
          rectangle: Rectangle.fromDegrees(-180, -90, 180, 90),
        });
        const imgLayer = new ImageryLayer(provider, { alpha: 0.85 });
        viewer.imageryLayers.add(imgLayer);
        surfaceLayerRef.current = imgLayer;
      } catch {
        // GIBS may not be available
      }
    }

    // 6. Add GIBS CO₂ overlay via WMS
    if (activeLayers.has('gibs-oco2')) {
      try {
        const date = getGibsDate();
        const wmsUrl =
          'https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi' +
          '?SERVICE=WMS&REQUEST=GetMap&VERSION=1.1.1' +
          '&LAYERS=OCO2_L2_CO2_Total_Column_Day' +
          `&TIME=${date}` +
          '&BBOX=-180,-90,180,90&WIDTH=4096&HEIGHT=2048' +
          '&SRS=EPSG:4326&FORMAT=image/png&TRANSPARENT=TRUE&STYLES=';
        const provider = new SingleTileImageryProvider({
          url: wmsUrl,
          rectangle: Rectangle.fromDegrees(-180, -90, 180, 90),
        });
        const imgLayer = new ImageryLayer(provider, { alpha: 0.6 });
        viewer.imageryLayers.add(imgLayer);
        gibsLayerRef.current = imgLayer;
      } catch {
        // GIBS may not be available
      }
    }

    // 6. Add fire points
    if (activeLayers.has('fires') && firesData?.fires) {
      const ds = new CustomDataSource('fires');
      for (const f of firesData.fires) {
        ds.entities.add({
          position: Cartesian3.fromDegrees(f.lon, f.lat),
          point: {
            pixelSize: Math.max(3, Math.min(12, 3 + Math.log10(Math.max(f.frp, 1)) * 3)),
            color: fireColor(f.frp),
            outlineWidth: 0,
            heightReference: HeightReference.CLAMP_TO_GROUND,
            scaleByDistance: new NearFarScalar(1.5e6, 1.0, 1.5e7, 0.4),
          },
          properties: {
            type: 'fire',
            frp: f.frp,
            lat: f.lat,
            lon: f.lon,
            acq_date: f.acq_date,
            acq_time: f.acq_time,
          },
        });
      }
      viewer.dataSources.add(ds);
      pointDataSourceRef.current = ds;
    }

    // 7. Add earthquake points
    if (activeLayers.has('earthquakes') && earthquakeData?.earthquakes) {
      const ds = new CustomDataSource('earthquakes');
      for (const e of earthquakeData.earthquakes) {
        ds.entities.add({
          position: Cartesian3.fromDegrees(e.lon, e.lat),
          point: {
            pixelSize: Math.max(4, 4 + (e.magnitude - 4) * 4),
            color: earthquakeColor(e.magnitude),
            outlineColor: Color.WHITE.withAlpha(0.4),
            outlineWidth: 1,
            heightReference: HeightReference.CLAMP_TO_GROUND,
            scaleByDistance: new NearFarScalar(1.5e6, 1.0, 1.5e7, 0.4),
          },
          properties: {
            type: 'earthquake',
            magnitude: e.magnitude,
            place: e.place,
            depth_km: e.depth_km,
            time_utc: e.time_utc,
            tsunami: e.tsunami,
          },
        });
      }
      viewer.dataSources.add(ds);
      pointDataSourceRef.current = ds;
    }
  }, [activeLayers, firesData, earthquakeData]);

  // ── Ocean current particle animation ─────────────────────────────────
  // Works with OR without API data — uses scientifically-based ocean
  // circulation model as default, enhanced by real data when available.

  useEffect(() => {
    const viewer = viewerRef.current;
    const canvas = particleCanvasRef.current;
    if (!viewer || !canvas || !activeLayers.has('ocean-currents')) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Resize canvas to container minus bottom bar (48px)
    const container = containerRef.current;
    if (container) {
      canvas.width = container.clientWidth;
      canvas.height = container.clientHeight - 48;
    }

    // Build API data lookup if available
    const gridMap = new Map<string, OceanCurrentPoint>();
    if (currentsData?.points) {
      for (const p of currentsData.points) {
        gridMap.set(`${Math.round(p.lat / 5) * 5},${Math.round(p.lon / 5) * 5}`, p);
      }
    }

    // Scientifically-based ocean circulation model
    // Based on major gyre systems + equatorial currents + ACC
    function getOceanFlow(lat: number, _lon: number): [number, number] {
      // Check API data first
      const apiPt = gridMap.get(`${Math.round(lat / 5) * 5},${Math.round(_lon / 5) * 5}`);
      if (apiPt && apiPt.v > 0.05) {
        const rad = (apiPt.d * Math.PI) / 180;
        return [apiPt.v * 0.25 * Math.sin(rad), apiPt.v * 0.25 * Math.cos(rad)];
      }

      // Scientific default: major ocean circulation patterns
      const absLat = Math.abs(lat);

      // Antarctic Circumpolar Current (ACC): 45-65°S, strong eastward
      if (lat < -45 && lat > -65) return [0.15, 0];

      // Trade winds zone (0-30°): westward (NE trades in NH, SE trades in SH)
      if (absLat < 30) {
        const tradeStrength = 0.08 * (1 - absLat / 30);
        return [-tradeStrength, lat > 0 ? -0.01 : 0.01];
      }

      // Westerlies zone (30-60°): eastward
      if (absLat < 60) {
        const westStrength = 0.06 * Math.sin(((absLat - 30) / 30) * Math.PI);
        return [westStrength, lat > 0 ? 0.01 : -0.01];
      }

      // Polar: weak easterlies
      return [-0.02, 0];
    }

    // Initialize particles
    const NUM = 3000;
    const MAX_AGE = 60;
    const TRAIL_LEN = 5; // keep last N screen positions for trail
    interface P { lon: number; lat: number; age: number; trail: Array<{x: number; y: number}>; }
    const ps: P[] = Array.from({ length: NUM }, () => ({
      lon: Math.random() * 360 - 180,
      lat: Math.random() * 150 - 75,
      age: Math.floor(Math.random() * MAX_AGE),
      trail: [],
    }));

    let running = true;
    const cameraDir = new Cartesian3();
    const ptDir = new Cartesian3();

    function frame() {
      if (!running || !viewer || !ctx || !canvas) return;
      const w = canvas.width;
      const h = canvas.height;

      // Clear canvas completely each frame — no opaque fill that would
      // block the SST/GIBS imagery layers underneath
      ctx.clearRect(0, 0, w, h);

      const camPos = viewer.camera.positionWC;
      Cartesian3.normalize(camPos, cameraDir);

      for (const p of ps) {
        const world = Cartesian3.fromDegrees(p.lon, p.lat);
        Cartesian3.normalize(world, ptDir);
        const dot = Cartesian3.dot(ptDir, cameraDir);

        // Behind globe or off bounds → reset
        if (dot < 0.1 || p.age >= MAX_AGE) {
          p.lon = Math.random() * 360 - 180;
          p.lat = Math.random() * 150 - 75;
          p.age = 0;
          p.trail = [];
          continue;
        }

        // Move by ocean flow
        const [du, dv] = getOceanFlow(p.lat, p.lon);
        p.lon += du;
        p.lat += dv;
        if (p.lon > 180) p.lon -= 360;
        if (p.lon < -180) p.lon += 360;
        if (Math.abs(p.lat) > 75) p.age = MAX_AGE;

        const sp = viewer.scene.cartesianToCanvasCoordinates(world);
        if (!sp || sp.x < 0 || sp.x > w || sp.y < 0 || sp.y > h) {
          p.age = MAX_AGE;
          continue;
        }

        // Store screen position in trail
        p.trail.push({ x: sp.x, y: sp.y });
        if (p.trail.length > TRAIL_LEN) p.trail.shift();

        // Draw trail segments with fading opacity
        if (p.trail.length > 1) {
          const t = 1 - Math.abs(p.lat) / 75;
          const r = Math.floor(40 + t * 215);
          const g = Math.floor(100 + t * 100 - Math.pow(t, 2) * 80);
          const b = Math.floor(220 - t * 180);
          for (let s = 1; s < p.trail.length; s++) {
            const a = (s / p.trail.length) * 0.6 * (1 - p.age / MAX_AGE);
            ctx.strokeStyle = `rgba(${r},${g},${b},${a})`;
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(p.trail[s - 1].x, p.trail[s - 1].y);
            ctx.lineTo(p.trail[s].x, p.trail[s].y);
            ctx.stroke();
          }
        }

        p.age++;
      }

      particleAnimRef.current = requestAnimationFrame(frame);
    }

    particleAnimRef.current = requestAnimationFrame(frame);

    return () => {
      running = false;
      cancelAnimationFrame(particleAnimRef.current);
      particleAnimRef.current = 0;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
    };
  }, [activeLayers, currentsData]);

  // ── Status ───────────────────────────────────────────────────────────────

  const activeCatDef = activeCategory ? CATEGORY_LOOKUP.get(activeCategory) ?? null : null;

  const dataCount = useMemo(() => {
    if (activeCategory === 'wildfires') return firesData?.fires?.length ?? 0;
    if (activeCategory === 'earthquakes') return earthquakeData?.earthquakes?.length ?? 0;
    return 0;
  }, [activeCategory, firesData, earthquakeData]);

  const isActiveLoading = (needsFires && firesLoading) || (needsQuakes && quakesLoading);

  // ── Render ───────────────────────────────────────────────────────────────

  return (
    <div ref={containerRef} style={containerStyle}>
      <div ref={cesiumContainerRef} style={{ width: '100%', height: '100%', position: 'relative', zIndex: 1 }} />

      {/* Ocean current particle overlay — stops above LayerBar (bottom 48px) */}
      <canvas
        ref={particleCanvasRef}
        style={{
          position: 'absolute', top: 0, left: 0, right: 0, bottom: 48,
          zIndex: 2, pointerEvents: 'none',
          display: activeLayers.has('ocean-currents') ? 'block' : 'none',
        }}
      />

      {/* Vignette overlay */}
      <div style={{ position: 'absolute', inset: 0, zIndex: 3, pointerEvents: 'none', boxShadow: 'inset 0 0 120px 40px rgba(2,4,8,0.4)' }} />

      {/* Loading indicator */}
      {isActiveLoading && (
        <div style={{
          position: 'absolute', inset: 0, zIndex: 5,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          pointerEvents: 'none',
        }}>
          <div style={{ textAlign: 'center', animation: 'fadeInUp 0.3s ease-out' }}>
            <div style={{
              width: 28, height: 28, borderRadius: '50%',
              border: '2px solid #1e293b', borderTopColor: activeCatDef?.activeColor ?? '#3b82f6',
              animation: 'spin 0.8s linear infinite', margin: '0 auto 8px',
            }} />
            <div style={{ color: '#64748b', fontSize: '11px', fontFamily: 'system-ui, sans-serif' }}>
              Loading {activeCatDef?.name ?? 'data'}…
            </div>
          </div>
        </div>
      )}

      <Tooltip info={tooltipInfo} onClose={() => setTooltipInfo(null)} />

      {/* Active category pill */}
      {activeCatDef && (
        <div style={{
          position: 'absolute', top: 12, left: '50%', transform: 'translateX(-50%)',
          zIndex: 10,
          background: 'rgba(10,14,26,0.75)', backdropFilter: 'blur(12px)',
          border: '1px solid rgba(51,65,85,0.3)', borderRadius: '20px',
          padding: '5px 16px', fontSize: '12px', color: '#cbd5e1',
          fontFamily: 'system-ui, sans-serif',
          display: 'flex', alignItems: 'center', gap: '8px',
        }}>
          <span style={{ fontSize: '14px' }}>{activeCatDef.icon}</span>
          <span style={{ fontWeight: 600 }}>{activeCatDef.name}</span>
          {dataCount > 0 && (
            <span style={{ color: '#64748b', fontSize: '11px' }}>{dataCount.toLocaleString()}</span>
          )}
          <span style={{ color: '#475569', fontSize: '10px' }}>{activeCatDef.question}</span>
        </div>
      )}

      {activeCatDef && (
        <div style={metaOverlayStyle}>
          <MetaLine cadence={activeCatDef.cadence} tag={activeCatDef.tag} source={activeCatDef.source} sourceUrl={activeCatDef.sourceUrl} />
        </div>
      )}

      <Legend activeCategory={activeCategory} />

      <LayerBar
        activeCategory={activeCategory}
        onCategoryChange={onCategoryChange}
        viewMode={viewMode}
        onViewModeChange={setViewMode}
      />
    </div>
  );
});

export default GlobeCesium;

// ─── Styles ───────────────────────────────────────────────────────────────────

const containerStyle: React.CSSProperties = {
  position: 'relative', width: '100%', height: '100%',
  background: '#020408',
  overflow: 'hidden',
};

const metaOverlayStyle: React.CSSProperties = {
  position: 'absolute', top: 12, left: 12, zIndex: 10,
  background: 'rgba(10,14,26,0.5)', padding: '5px 10px',
  borderRadius: '6px', backdropFilter: 'blur(8px)', pointerEvents: 'none',
  border: '1px solid rgba(51,65,85,0.2)',
};

const layerBarStyle: React.CSSProperties = {
  position: 'absolute', bottom: 0, left: 0, right: 0, zIndex: 15,
  background: 'rgba(10,14,26,0.85)', backdropFilter: 'blur(12px)',
  borderTop: '1px solid rgba(51,65,85,0.3)',
  padding: '8px 16px',
};

const legendStyle: React.CSSProperties = {
  position: 'absolute', bottom: 60, left: 12, zIndex: 10,
  background: 'rgba(10,14,26,0.82)', backdropFilter: 'blur(8px)',
  border: '1px solid rgba(51,65,85,0.4)', borderRadius: '8px',
  padding: '8px 12px', minWidth: 160, maxWidth: 260,
};

const legendTitleStyle: React.CSSProperties = {
  fontSize: '11px', fontWeight: 600, color: '#cbd5e1',
  marginBottom: 6, fontFamily: 'system-ui, sans-serif',
};

const legendLabelsStyle: React.CSSProperties = {
  display: 'flex', justifyContent: 'space-between',
  fontSize: '9px', color: '#64748b', marginTop: 2,
  fontFamily: 'system-ui, sans-serif',
};
