/// <reference path="../.astro/types.d.ts" />

// Cesium 1.140 ships a ~50k-line `Source/Cesium.d.ts`. Even with
// `skipLibCheck: true`, `astro check` parses and resolves the whole
// file, which OOMs at 12 GB of heap. GlobeApp.tsx uses Cesium only
// through dynamic `await import('cesium')` with `any`-typed refs,
// so real types are not needed for the project check. The tsconfig
// `paths` map redirects editor resolution; this ambient declaration
// is the belt-and-suspenders override that `astro check` honors.
// Drop both when Cesium publishes a lighter type entry.
declare module 'cesium' {
  const cesium: any;
  export = cesium;
}
declare module 'cesium/Build/Cesium/Widgets/widgets.css' {
  const css: any;
  export default css;
}

// Permit .astro re-exports from .ts barrels (e.g., components/reports/index.ts).
// Astro itself generates per-file .d.ts shims inside .astro/ during dev/build,
// but those don't exist at plain `tsc --noEmit` time. This ambient declaration
// lets the type-check pass while Astro's own tooling still resolves the real
// component type when the consumer is an .astro frontmatter.
declare module '*.astro' {
  const Component: (props: Record<string, unknown>) => unknown;
  export default Component;
}
