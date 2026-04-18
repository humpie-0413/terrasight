// -----------------------------------------------------------------------------
// GlobeApp — CesiumJS-powered Earth Now island (Step 6 Task 1).
//
// Responsibilities:
//   1. Mount a Cesium Viewer with BlueMarble base layer (always on).
//   2. Let the user toggle ONE imagery layer (SST / AOD / Clouds / NightLights)
//      at a time — enforces the "1 continuous imagery active" rule.
//   3. Let the user toggle ONE event layer (fires / earthquakes) at a time —
//      enforces the "1 event active" rule.
//   4. Handle globe clicks:
//      - SST imagery active + ocean → call /api/sst-point, show value popup.
//      - Event point picked → show event popup (severity, observedAt, source).
//      - AOD / Clouds / NightLights active → show info-only caveat card.
//   5. Render the Legend overlay from @terrasight/ui.
//   6. Mobile viewport (<768px) → render GlobeMobileFallback instead.
//
// Cesium integration notes:
//   - We avoid full Cesium static-asset copy for Step 6 (deploy concern).
//     All UI widgets that require /Assets/ (baseLayerPicker, geocoder, etc.)
//     are disabled to sidestep asset-base-URL requirements at dev time.
//   - requestRenderMode: true + maximumRenderTimeChange: Infinity → CPU idle.
//   - We do NOT use Ion assets → Ion.defaultAccessToken = '' (empty string).
//
// Worker base URL:
//   PUBLIC_WORKER_BASE_URL env var (see .env.example). Defaults to '' which
//   means same-origin (production). In `astro dev`, set to http://localhost:8787
//   so the Worker (wrangler dev) is reachable cross-origin.
// -----------------------------------------------------------------------------

import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import type { EventPoint } from '@terrasight/schemas';
import {
  Legend,
  GlobeMobileFallback,
  TrustBadge,
  type LayerSummary,
  type EventLayerSummary,
} from '@terrasight/ui';
import {
  IMAGERY_LAYERS,
  EVENT_LAYERS,
  gibsDateStr,
  type ImageryLayerDef,
  type EventLayerDef,
} from '../lib/layers';

const MOBILE_BREAKPOINT = 768;

// Same-origin by default; override with PUBLIC_WORKER_BASE_URL during dev.
const WORKER_BASE: string =
  (import.meta.env.PUBLIC_WORKER_BASE_URL as string | undefined) ?? '';

// -----------------------------------------------------------------------------
// Mobile detection hook — SSR-safe (guards `window`).
// -----------------------------------------------------------------------------

function useIsMobile(): boolean {
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const check = () => setIsMobile(window.innerWidth < MOBILE_BREAKPOINT);
    check();
    window.addEventListener('resize', check);
    return () => window.removeEventListener('resize', check);
  }, []);

  return isMobile;
}

// -----------------------------------------------------------------------------
// Popup state — discriminated union keyed on `kind`.
// -----------------------------------------------------------------------------

type PopupState =
  | { kind: 'none' }
  | { kind: 'sst'; lat: number; lon: number; loading: true }
  | {
      kind: 'sst';
      lat: number;
      lon: number;
      loading: false;
      sst_c: number | null;
      message?: string;
      observed_at?: string;
    }
  | { kind: 'event'; point: EventPoint; layerTitle: string; sourceUrl: string }
  | { kind: 'info-only'; layerTitle: string; caveats: string[] };

// -----------------------------------------------------------------------------
// Main component
// -----------------------------------------------------------------------------

export default function GlobeApp() {
  const isMobile = useIsMobile();

  // Cesium viewer + imagery/event refs. `any` type to avoid pulling Cesium
  // type symbols into the top-level SSR analysis pass.
  const containerRef = useRef<HTMLDivElement>(null);
  const viewerRef = useRef<any>(null);
  const imageryLayerRef = useRef<any>(null);
  const eventDataSourceRef = useRef<any>(null);
  // Track mount state; Cesium dynamic import completes after unmount in dev.
  const mountedRef = useRef(true);

  const [activeImageryId, setActiveImageryId] = useState<string | null>(null);
  const [activeEventId, setActiveEventId] = useState<
    'fires' | 'earthquakes' | null
  >(null);
  const [eventCount, setEventCount] = useState<number | null>(null);
  const [popup, setPopup] = useState<PopupState>({ kind: 'none' });
  // Cesium-ready flag — imagery/event effects wait on this.
  const [cesiumReady, setCesiumReady] = useState(false);

  // ---------------------------------------------------------------------------
  // 1. Initialize Cesium Viewer (desktop only). Dynamic import avoids SSR.
  // ---------------------------------------------------------------------------

  useEffect(() => {
    if (isMobile) return;
    if (typeof window === 'undefined') return;
    if (!containerRef.current) return;

    mountedRef.current = true;
    let cancelled = false;

    (async () => {
      const cesium = await import('cesium');
      // Side-effect CSS (widgets). Some build pipelines inline it; in dev it
      // may emit a missing-asset warning but won't block the globe rendering.
      try {
        await import('cesium/Build/Cesium/Widgets/widgets.css' as string);
      } catch {
        /* noop — widgets.css is cosmetic; skip if unresolvable */
      }
      if (cancelled || !containerRef.current) return;

      // We don't use Ion assets; silence the default-token warning.
      cesium.Ion.defaultAccessToken = '';

      const viewer = new cesium.Viewer(containerRef.current, {
        // Disable all widgets that require /Assets/ to avoid deploy-time
        // asset-base-URL issues. Step 6 goal: working 3D globe + toggles.
        geocoder: false,
        baseLayerPicker: false,
        fullscreenButton: false,
        vrButton: false,
        sceneModePicker: false,
        navigationHelpButton: false,
        homeButton: false,
        animation: false,
        timeline: false,
        infoBox: false,
        selectionIndicator: false,
        // Idle CPU tuning.
        requestRenderMode: true,
        maximumRenderTimeChange: Infinity,
      });

      // Remove any default imagery provider added by Cesium (we supply our own).
      viewer.imageryLayers.removeAll();

      // Add BlueMarble base layer (always on).
      const baseDef = IMAGERY_LAYERS.find((l) => l.isBase)!;
      const baseProvider = new cesium.WebMapTileServiceImageryProvider({
        url: baseDef.urlTemplate,
        layer: baseDef.id,
        style: 'default',
        format: `image/${baseDef.ext === 'jpg' ? 'jpeg' : 'png'}`,
        tileMatrixSetID: baseDef.tileMatrixSet,
        maximumLevel: 8,
      });
      viewer.imageryLayers.addImageryProvider(baseProvider);

      // Install left-click screen-space handler.
      const handler = viewer.screenSpaceEventHandler;
      handler.setInputAction((evt: { position: any }) => {
        handleLeftClick(viewer, cesium, evt.position);
      }, cesium.ScreenSpaceEventType.LEFT_CLICK);

      viewerRef.current = viewer;
      if (!cancelled) setCesiumReady(true);
    })();

    return () => {
      cancelled = true;
      mountedRef.current = false;
      const v = viewerRef.current;
      if (v && !v.isDestroyed()) {
        try {
          v.destroy();
        } catch {
          /* noop — Cesium occasionally throws on double-destroy in HMR */
        }
      }
      viewerRef.current = null;
      imageryLayerRef.current = null;
      eventDataSourceRef.current = null;
    };
    // Only re-run if isMobile flips; clicks route via refs so no need to depend
    // on activeImageryId / activeEventId here.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isMobile]);

  // ---------------------------------------------------------------------------
  // 2. Active imagery effect — remove previous toggleable layer, add new one.
  // ---------------------------------------------------------------------------

  useEffect(() => {
    if (isMobile || !cesiumReady) return;
    const viewer = viewerRef.current;
    if (!viewer) return;

    let cancelled = false;

    (async () => {
      const cesium = await import('cesium');
      if (cancelled) return;

      // Remove prior toggleable imagery layer (base is index 0; not touched).
      if (imageryLayerRef.current) {
        viewer.imageryLayers.remove(imageryLayerRef.current, true);
        imageryLayerRef.current = null;
      }

      if (!activeImageryId) return;

      const def = IMAGERY_LAYERS.find((l) => l.id === activeImageryId);
      if (!def || def.isBase) return;

      const dateStr = gibsDateStr(def);
      const url = def.urlTemplate.replace('{Time}', dateStr);

      const provider = new cesium.WebMapTileServiceImageryProvider({
        url,
        layer: def.id,
        style: 'default',
        format: `image/${def.ext === 'jpg' ? 'jpeg' : 'png'}`,
        tileMatrixSetID: def.tileMatrixSet,
        maximumLevel: 8,
      });
      const layer = viewer.imageryLayers.addImageryProvider(provider);
      imageryLayerRef.current = layer;
    })();

    return () => {
      cancelled = true;
    };
  }, [activeImageryId, isMobile, cesiumReady]);

  // ---------------------------------------------------------------------------
  // 3. Active event effect — fetch Worker endpoint + add Cesium points.
  // ---------------------------------------------------------------------------

  useEffect(() => {
    if (isMobile || !cesiumReady) return;
    const viewer = viewerRef.current;
    if (!viewer) return;

    let cancelled = false;
    let refreshTimer: ReturnType<typeof setInterval> | null = null;

    (async () => {
      const cesium = await import('cesium');
      if (cancelled) return;

      // Remove previous event data source.
      if (eventDataSourceRef.current) {
        viewer.dataSources.remove(eventDataSourceRef.current, true);
        eventDataSourceRef.current = null;
      }
      setEventCount(null);

      if (!activeEventId) return;

      const maybeDef = EVENT_LAYERS.find((l) => l.id === activeEventId);
      if (!maybeDef) return;
      // Bind into a const so the inner `load()` closure sees a narrowed
      // (non-undefined) reference; TS otherwise widens through closures.
      const def: EventLayerDef = maybeDef;

      // Earthquake clutter control: default to period=day & minMagnitude=3.0
      const query =
        def.id === 'earthquakes' ? '?period=day&minMagnitude=3.0' : '';
      const url = `${WORKER_BASE}${def.apiPath}${query}`;

      const ds = new cesium.CustomDataSource(def.id);
      viewer.dataSources.add(ds);
      eventDataSourceRef.current = ds;

      async function load() {
        try {
          const res = await fetch(url);
          if (!res.ok) {
            // Worker may return 500 or the endpoint may be unreachable in dev
            // — fail gracefully: just leave the event layer empty.
            setEventCount(0);
            return;
          }
          const payload = (await res.json()) as {
            status?: string;
            count?: number;
            data?: EventPoint[];
          };
          if (cancelled || eventDataSourceRef.current !== ds) return;
          const data = Array.isArray(payload.data) ? payload.data : [];

          ds.entities.removeAll();
          for (const pt of data) {
            if (
              typeof pt.lat !== 'number' ||
              typeof pt.lon !== 'number' ||
              !isFinite(pt.lat) ||
              !isFinite(pt.lon)
            ) {
              continue;
            }
            ds.entities.add({
              id: `${def.id}:${pt.id}`,
              position: cesium.Cartesian3.fromDegrees(pt.lon, pt.lat),
              point: {
                pixelSize: pointSizeFor(def.id, pt),
                color: pointColorFor(def.id, cesium),
                outlineColor: cesium.Color.WHITE.withAlpha(0.6),
                outlineWidth: 1,
                heightReference: cesium.HeightReference.CLAMP_TO_GROUND,
              },
              properties: {
                kind: 'event',
                layerId: def.id,
                eventPoint: pt,
              },
            });
          }
          setEventCount(payload.count ?? data.length);
          viewer.scene.requestRender();
        } catch {
          if (cancelled) return;
          setEventCount(0);
        }
      }

      await load();
      refreshTimer = setInterval(load, def.refreshSeconds * 1000);
    })();

    return () => {
      cancelled = true;
      if (refreshTimer) clearInterval(refreshTimer);
    };
  }, [activeEventId, isMobile, cesiumReady]);

  // ---------------------------------------------------------------------------
  // 4. Click handler — routes to SST / event / info-only popup.
  //
  // Declared as a closure so the imagery/event effects can set refs that this
  // function reads at click time (no stale-closure issues).
  // ---------------------------------------------------------------------------

  function handleLeftClick(viewer: any, cesium: any, screenPos: any) {
    if (!viewer || viewer.isDestroyed()) return;

    // 1) Did the click hit an event entity?
    const picked = viewer.scene.pick(screenPos);
    if (picked && picked.id && picked.id.properties) {
      const kindProp = picked.id.properties.kind?.getValue?.();
      if (kindProp === 'event') {
        const layerId = picked.id.properties.layerId?.getValue?.();
        const pt: EventPoint | undefined =
          picked.id.properties.eventPoint?.getValue?.();
        const def = EVENT_LAYERS.find((l) => l.id === layerId);
        if (pt && def) {
          setPopup({
            kind: 'event',
            point: pt,
            layerTitle: def.title,
            sourceUrl: def.sourceUrl,
          });
          return;
        }
      }
    }

    // 2) Convert screen position → globe lat/lon.
    const ray = viewer.camera.getPickRay(screenPos);
    if (!ray) return;
    const world = viewer.scene.globe.pick(ray, viewer.scene);
    if (!world) return;
    const carto = cesium.Cartographic.fromCartesian(world);
    const lat = cesium.Math.toDegrees(carto.latitude);
    const lon = cesium.Math.toDegrees(carto.longitude);

    // 3) Route by active imagery layer. Read via ref so the closure (captured
    //    at Viewer-init time) sees the current value, not the stale initial.
    const currentImagery = currentImageryDefRef.current;

    if (currentImagery?.clickPolicy === 'sst-point') {
      setPopup({ kind: 'sst', lat, lon, loading: true });
      (async () => {
        try {
          const res = await fetch(
            `${WORKER_BASE}/api/sst-point?lat=${lat.toFixed(4)}&lon=${lon.toFixed(4)}`,
          );
          const j = (await res.json()) as {
            status?: string;
            sst_c?: number;
            message?: string;
            observed_at?: string;
          };
          if (!mountedRef.current) return;
          if (j.status === 'ok' && typeof j.sst_c === 'number') {
            setPopup({
              kind: 'sst',
              lat,
              lon,
              loading: false,
              sst_c: j.sst_c,
              observed_at: j.observed_at,
            });
          } else {
            setPopup({
              kind: 'sst',
              lat,
              lon,
              loading: false,
              sst_c: null,
              message: j.message ?? 'No SST data at this location.',
            });
          }
        } catch {
          if (!mountedRef.current) return;
          setPopup({
            kind: 'sst',
            lat,
            lon,
            loading: false,
            sst_c: null,
            message: 'Failed to fetch SST value (Worker unreachable?).',
          });
        }
      })();
      return;
    }

    if (currentImagery?.clickPolicy === 'info-only') {
      setPopup({
        kind: 'info-only',
        layerTitle: currentImagery.title,
        caveats: currentImagery.caveats,
      });
      return;
    }

    // Base-only or 'none' policy → nothing to show.
  }

  // Refs to read `activeImageryId` inside the click closure without stale
  // values (the closure captures at Viewer-init time).
  const activeImageryIdRef = useRef<string | null>(activeImageryId);
  const currentImageryDefRef = useRef<ImageryLayerDef | null>(null);
  useEffect(() => {
    activeImageryIdRef.current = activeImageryId;
    currentImageryDefRef.current =
      IMAGERY_LAYERS.find((l) => l.id === activeImageryId) ?? null;
  }, [activeImageryId]);

  // ---------------------------------------------------------------------------
  // 5. Derive Legend props.
  // ---------------------------------------------------------------------------

  const activeImageryDef = useMemo(
    () => IMAGERY_LAYERS.find((l) => l.id === activeImageryId) ?? null,
    [activeImageryId],
  );
  const activeEventDef = useMemo(
    () => EVENT_LAYERS.find((l) => l.id === activeEventId) ?? null,
    [activeEventId],
  );

  const imagerySummary: LayerSummary | null = activeImageryDef
    ? {
        id: activeImageryDef.id,
        title: activeImageryDef.title,
        source: activeImageryDef.source,
        sourceUrl: activeImageryDef.sourceUrl,
        trustTag: activeImageryDef.trustTag,
        cadence: activeImageryDef.cadence,
        scale: activeImageryDef.legend,
        caveat: activeImageryDef.caveat,
      }
    : null;

  const eventSummary: EventLayerSummary | null = activeEventDef
    ? {
        id: activeEventDef.id,
        title: activeEventDef.title,
        source: activeEventDef.source,
        sourceUrl: activeEventDef.sourceUrl,
        trustTag: activeEventDef.trustTag,
        cadence: activeEventDef.cadence,
        count: eventCount ?? undefined,
        caveat: activeEventDef.caveat,
      }
    : null;

  // ---------------------------------------------------------------------------
  // 6. Render — mobile fallback OR full globe.
  // ---------------------------------------------------------------------------

  if (isMobile) return <GlobeMobileFallback />;

  return (
    <div
      style={{
        position: 'relative',
        width: '100%',
        height: '100vh',
        background: '#000',
        overflow: 'hidden',
        fontFamily: 'system-ui, sans-serif',
      }}
    >
      <div ref={containerRef} style={{ width: '100%', height: '100%' }} />

      <LayerControls
        imageryLayers={IMAGERY_LAYERS.filter((l) => !l.isBase)}
        eventLayers={EVENT_LAYERS}
        activeImageryId={activeImageryId}
        activeEventId={activeEventId}
        onToggleImagery={(id) =>
          setActiveImageryId((curr) => (curr === id ? null : id))
        }
        onToggleEvent={(id) =>
          setActiveEventId((curr) => (curr === id ? null : id))
        }
      />

      <Legend activeImagery={imagerySummary} activeEvent={eventSummary} />

      {popup.kind !== 'none' && (
        <PopupCard state={popup} onClose={() => setPopup({ kind: 'none' })} />
      )}
    </div>
  );
}

// -----------------------------------------------------------------------------
// LayerControls — top-right toggle panel. Local component; not exported.
// -----------------------------------------------------------------------------

interface LayerControlsProps {
  imageryLayers: ImageryLayerDef[];
  eventLayers: EventLayerDef[];
  activeImageryId: string | null;
  activeEventId: 'fires' | 'earthquakes' | null;
  onToggleImagery: (id: string) => void;
  onToggleEvent: (id: 'fires' | 'earthquakes') => void;
}

function LayerControls({
  imageryLayers,
  eventLayers,
  activeImageryId,
  activeEventId,
  onToggleImagery,
  onToggleEvent,
}: LayerControlsProps) {
  return (
    <div
      style={{
        position: 'absolute',
        top: '16px',
        right: '16px',
        zIndex: 10,
        width: '240px',
        background: 'rgba(15, 23, 42, 0.85)',
        color: '#e2e8f0',
        padding: '12px 14px',
        borderRadius: '8px',
        border: '1px solid rgba(148, 163, 184, 0.15)',
        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.25)',
        fontSize: '12px',
      }}
    >
      <SectionHeader>Imagery</SectionHeader>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
        {imageryLayers.map((l) => (
          <ToggleButton
            key={l.id}
            label={l.title}
            active={activeImageryId === l.id}
            onClick={() => onToggleImagery(l.id)}
          />
        ))}
      </div>

      <div
        style={{
          borderTop: '1px solid rgba(148, 163, 184, 0.2)',
          margin: '12px 0 10px',
        }}
      />

      <SectionHeader>Events</SectionHeader>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
        {eventLayers.map((l) => (
          <ToggleButton
            key={l.id}
            label={l.title}
            active={activeEventId === l.id}
            onClick={() => onToggleEvent(l.id)}
          />
        ))}
      </div>
    </div>
  );
}

function SectionHeader({ children }: { children: ReactNode }) {
  return (
    <div
      style={{
        fontSize: '10px',
        textTransform: 'uppercase',
        letterSpacing: '0.08em',
        color: '#94a3b8',
        fontWeight: 600,
        marginBottom: '8px',
      }}
    >
      {children}
    </div>
  );
}

interface ToggleButtonProps {
  label: string;
  active: boolean;
  onClick: () => void;
}

function ToggleButton({ label, active, onClick }: ToggleButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        width: '100%',
        padding: '6px 10px',
        borderRadius: '6px',
        border: active
          ? '1px solid rgba(34, 197, 94, 0.6)'
          : '1px solid rgba(148, 163, 184, 0.25)',
        background: active ? 'rgba(34, 197, 94, 0.12)' : 'rgba(30, 41, 59, 0.6)',
        color: active ? '#86efac' : '#e2e8f0',
        fontSize: '12px',
        fontFamily: 'inherit',
        cursor: 'pointer',
        textAlign: 'left',
      }}
    >
      <span>{label}</span>
      <span
        style={{
          fontSize: '10px',
          color: active ? '#22c55e' : '#64748b',
        }}
      >
        {active ? 'ON' : 'off'}
      </span>
    </button>
  );
}

// -----------------------------------------------------------------------------
// PopupCard — Fixed top-center overlay for click results.
// -----------------------------------------------------------------------------

interface PopupCardProps {
  state: Exclude<PopupState, { kind: 'none' }>;
  onClose: () => void;
}

function PopupCard({ state, onClose }: PopupCardProps) {
  return (
    <div
      style={{
        position: 'absolute',
        top: '16px',
        left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 11,
        width: 'min(420px, calc(100% - 32px))',
        background: 'rgba(15, 23, 42, 0.95)',
        color: '#e2e8f0',
        padding: '14px 40px 14px 18px',
        borderRadius: '8px',
        border: '1px solid rgba(148, 163, 184, 0.2)',
        boxShadow: '0 8px 24px rgba(0, 0, 0, 0.4)',
        fontSize: '13px',
        lineHeight: 1.5,
      }}
    >
      <button
        type="button"
        onClick={onClose}
        aria-label="Close"
        style={{
          position: 'absolute',
          top: '8px',
          right: '10px',
          width: '24px',
          height: '24px',
          borderRadius: '4px',
          border: 'none',
          background: 'transparent',
          color: '#94a3b8',
          fontSize: '16px',
          cursor: 'pointer',
          lineHeight: 1,
        }}
      >
        {'\u00D7'}
      </button>
      <PopupBody state={state} />
    </div>
  );
}

function PopupBody({ state }: { state: Exclude<PopupState, { kind: 'none' }> }) {
  if (state.kind === 'sst') {
    return (
      <div>
        <div style={{ fontSize: '11px', color: '#94a3b8', marginBottom: '4px' }}>
          Sea Surface Temperature
        </div>
        {state.loading ? (
          <div>{'Fetching SST\u2026'}</div>
        ) : state.sst_c !== null ? (
          <>
            <div style={{ fontSize: '20px', fontWeight: 700, color: '#f1f5f9' }}>
              {state.sst_c.toFixed(1)} {'\u00B0C'}
            </div>
            <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '4px' }}>
              ({state.lat.toFixed(3)}, {state.lon.toFixed(3)})
              {state.observed_at ? ` \u00B7 ${state.observed_at}` : ''}
            </div>
            <div style={{ marginTop: '8px' }}>
              <TrustBadge tag="observed" />
              <span
                style={{
                  fontSize: '11px',
                  color: '#94a3b8',
                  marginLeft: '6px',
                }}
              >
                NOAA OISST v2.1
              </span>
            </div>
          </>
        ) : (
          <div style={{ color: '#cbd5e1' }}>
            {state.message ?? 'No data at this location.'}
          </div>
        )}
      </div>
    );
  }

  if (state.kind === 'event') {
    const p = state.point;
    const observedAt = formatObservedAt(p.observedAt);
    return (
      <div>
        <div style={{ fontSize: '11px', color: '#94a3b8', marginBottom: '4px' }}>
          {state.layerTitle}
        </div>
        <div style={{ fontSize: '14px', fontWeight: 700, color: '#f1f5f9' }}>
          {p.label}
        </div>
        <div
          style={{
            fontSize: '11px',
            color: '#94a3b8',
            marginTop: '4px',
            display: 'flex',
            gap: '6px',
            flexWrap: 'wrap',
          }}
        >
          <span>({p.lat.toFixed(3)}, {p.lon.toFixed(3)})</span>
          <span>{'\u00B7'}</span>
          <span>{observedAt}</span>
          {typeof p.severity !== 'undefined' && (
            <>
              <span>{'\u00B7'}</span>
              <span>severity {p.severity}</span>
            </>
          )}
        </div>
        <div style={{ marginTop: '8px' }}>
          <a
            href={state.sourceUrl}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              fontSize: '11px',
              color: '#60a5fa',
              textDecoration: 'underline',
            }}
          >
            Source
          </a>
        </div>
      </div>
    );
  }

  // info-only
  return (
    <div>
      <div style={{ fontSize: '11px', color: '#94a3b8', marginBottom: '4px' }}>
        {state.layerTitle}
      </div>
      <div style={{ fontSize: '13px', color: '#f1f5f9', marginBottom: '8px' }}>
        Click values are not available for this layer.
      </div>
      <ul
        style={{
          margin: 0,
          paddingLeft: '18px',
          fontSize: '12px',
          color: '#cbd5e1',
        }}
      >
        {state.caveats.map((c, i) => (
          <li key={i} style={{ marginBottom: '4px' }}>
            {c}
          </li>
        ))}
      </ul>
    </div>
  );
}

function formatObservedAt(iso: string): string {
  try {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return iso;
    return d.toISOString().replace('T', ' ').slice(0, 16) + 'Z';
  } catch {
    return iso;
  }
}

// -----------------------------------------------------------------------------
// Event-point styling — size/color as a function of layer + severity.
// -----------------------------------------------------------------------------

function pointSizeFor(layerId: string, pt: EventPoint): number {
  if (layerId === 'earthquakes') {
    const mag =
      typeof pt.severity === 'number'
        ? pt.severity
        : typeof pt.severity === 'string'
          ? parseFloat(pt.severity) || 3
          : 3;
    // Mag 3 → 6px; mag 7 → 14px.
    return Math.max(4, Math.min(16, 6 + (mag - 3) * 2));
  }
  // Fires — fixed small size; FRP varies enormously and would dominate.
  return 4;
}

function pointColorFor(layerId: string, cesium: any): any {
  if (layerId === 'earthquakes') {
    return cesium.Color.fromCssColorString('#a855f7').withAlpha(0.85);
  }
  return cesium.Color.fromCssColorString('#ef4444').withAlpha(0.9);
}
