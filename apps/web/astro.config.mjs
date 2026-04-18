import { defineConfig } from 'astro/config';
import react from '@astrojs/react';
import sitemap from '@astrojs/sitemap';

// PUBLIC_SITE_URL is read at build time. When unset, we deliberately do
// NOT pass a `site` to Astro — which prevents sitemap emission. This
// matches the Rule 7 canonical policy: never hard-code a placeholder
// URL; callers must set PUBLIC_SITE_URL on the production build step.
const PUBLIC_SITE_URL = process.env.PUBLIC_SITE_URL?.trim();
if (!PUBLIC_SITE_URL) {
  // eslint-disable-next-line no-console
  console.warn(
    '[astro.config] PUBLIC_SITE_URL is not set — sitemap.xml will NOT be emitted ' +
      'and canonical links will be absent. Set PUBLIC_SITE_URL=https://... before production build.',
  );
}

export default defineConfig({
  // Astro only emits sitemap when `site` is defined. We skip it
  // intentionally when PUBLIC_SITE_URL is unset.
  site: PUBLIC_SITE_URL || undefined,
  integrations: [
    react(),
    sitemap({
      // Exclude guide stubs — they are `noindex, nofollow` until content
      // ships. The `page` argument is the full absolute URL the
      // integration built from `site` + pathname, e.g.
      // `https://example.com/guides/what-is-a-trust-tag/`.
      // See Step 8 SEO policy: `docs/architecture/seo-ia.md`.
      filter: (page) => !/\/guides\//.test(page),
    }),
  ],
  output: 'static',
  vite: {
    // Cesium is large (~5.5 MB) and uses browser-only globals (window,
    // document). We load it via `await import('cesium')` inside a
    // useEffect in GlobeApp.tsx, so it never needs to evaluate server-side.
    // Externalizing here keeps SSR from bundling it; the dynamic client
    // import pulls it in only after hydration.
    ssr: {
      external: ['cesium'],
    },
  },
});
