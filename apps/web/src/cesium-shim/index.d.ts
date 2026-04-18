// -----------------------------------------------------------------------------
// Cesium module type shim (path-redirect target).
//
// tsconfig `paths` maps `cesium` → this file. Cesium 1.140's 50k-line
// Source/Cesium.d.ts causes `astro check` to OOM (the file is parsed/resolved
// even with `skipLibCheck: true`). GlobeApp.tsx accesses Cesium through a
// dynamic import with `any`-typed refs, so no real types are needed for the
// project check.
//
// Drop this when Cesium publishes a lighter type entry or we copy static
// assets and want editor type help.
// -----------------------------------------------------------------------------

declare const cesium: any;
export = cesium;
