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
  UrlTemplateImageryProvider,
  CustomDataSource,
  Entity,
  Color,
  Cartesian2,
  Cartesian3,
  ScreenSpaceEventHandler,
  ScreenSpaceEventType,
  defined,
  Rectangle,
  GeographicTilingScheme,
  NearFarScalar,
  HeightReference,
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
    key: 'sst', icon: '🌊', name: 'Ocean Temp',
    question: 'How warm are the oceans?',
    activeColor: '#f97316', tag: TrustTag.Observed, cadence: 'Daily (1-day lag)',
    source: 'NOAA OISST v2.1', sourceUrl: 'https://coastwatch.pfeg.noaa.gov/erddap/griddap/ncdcOisst21NrtAgg.html',
    activates: ['sst-surface'],
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
      <div style={legendTitleStyle}>Sea Surface Temperature (°C)</div>
      <div style={{ background: 'linear-gradient(to right, rgb(49,54,149), rgb(116,173,209), rgb(253,174,97), rgb(215,48,39), rgb(165,0,38))', height: 10, borderRadius: 3 }} />
      <div style={legendLabelsStyle}><span>-2</span><span>8</span><span>18</span><span>26</span><span>32</span></div>
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

interface TooltipInfo { x: number; y: number; html: string; }

function Tooltip({ info }: { info: TooltipInfo | null }) {
  if (!info) return null;
  return (
    <div style={{
      position: 'absolute', left: info.x + 14, top: info.y - 14, pointerEvents: 'none',
      background: 'rgba(12,18,32,0.94)', color: '#f1f5f9', padding: '10px 14px',
      border: '1px solid rgba(71,85,105,0.35)', borderRadius: '10px',
      fontSize: '12px', lineHeight: '1.5', fontFamily: 'system-ui, sans-serif',
      maxWidth: 300, zIndex: 25, backdropFilter: 'blur(14px)',
      boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
    }} dangerouslySetInnerHTML={{ __html: info.html }} />
  );
}

// ─── Surface PNG layer map ────────────────────────────────────────────────────

const SURFACE_LAYERS: Record<string, { url: string; alpha: number }> = {
  'sst-surface': { url: `${API_BASE}/globe/surface/sst.png`, alpha: 0.85 },
  'pm25-surface': { url: `${API_BASE}/globe/surface/pm25.png`, alpha: 0.8 },
  'temp-surface': { url: `${API_BASE}/globe/surface/temperature.png`, alpha: 0.8 },
  'precip-surface': { url: `${API_BASE}/globe/surface/precipitation.png`, alpha: 0.75 },
  'no2-surface': { url: `${API_BASE}/globe/surface/no2.png`, alpha: 0.8 },
};

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
  const gibsLayerRef = useRef<ImageryLayer | null>(null);
  const pointDataSourceRef = useRef<CustomDataSource | null>(null);

  // ── Lazy data fetches ────────────────────────────────────────────────────

  const needsFires = activeCategory === 'wildfires';
  const needsQuakes = activeCategory === 'earthquakes';

  const { data: firesData, loading: firesLoading } = useApi<FiresResponse>(
    '/earth-now/fires', needsFires,
  );
  const { data: earthquakeData, loading: quakesLoading } = useApi<EarthquakeResponse>(
    '/hazards/earthquakes?min_magnitude=4&limit=500&days=7', needsQuakes,
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
          setTooltipInfo({ x: movement.endPosition.x, y: movement.endPosition.y, html });
        } else {
          setTooltipInfo(null);
        }
      } else {
        setTooltipInfo(null);
      }
    }, ScreenSpaceEventType.MOUSE_MOVE);

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

    // 1. Remove previous surface overlay
    if (surfaceLayerRef.current) {
      viewer.imageryLayers.remove(surfaceLayerRef.current);
      surfaceLayerRef.current = null;
    }

    // 2. Remove previous GIBS overlay
    if (gibsLayerRef.current) {
      viewer.imageryLayers.remove(gibsLayerRef.current);
      gibsLayerRef.current = null;
    }

    // 3. Remove previous point data
    if (pointDataSourceRef.current) {
      viewer.dataSources.remove(pointDataSourceRef.current);
      pointDataSourceRef.current = null;
    }

    // 4. Add surface PNG overlay (SST, PM2.5, Temperature, etc.)
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
        break; // Only one surface at a time
      }
    }

    // 5. Add GIBS CO₂ overlay
    if (activeLayers.has('gibs-oco2')) {
      try {
        const date = getGibsDate();
        const provider = new UrlTemplateImageryProvider({
          url: `https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/OCO2_L2_CO2_Total_Column_Day/default/${date}/2km/{z}/{reverseY}/{x}.png`,
          tilingScheme: new GeographicTilingScheme(),
          maximumLevel: 5,
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

      {/* Vignette overlay */}
      <div style={{ position: 'absolute', inset: 0, zIndex: 2, pointerEvents: 'none', boxShadow: 'inset 0 0 120px 40px rgba(2,4,8,0.4)' }} />

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

      <Tooltip info={tooltipInfo} />

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
