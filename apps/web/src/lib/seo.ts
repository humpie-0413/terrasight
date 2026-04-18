/**
 * Pure TypeScript SEO / meta helpers.
 *
 * Returns plain data (`PageMeta`) that `BaseLayout.astro` merges into the
 * existing per-page `<head>` slot. Zero Astro / React dependencies — this
 * module is usable from frontmatter (.astro), React islands, and build
 * scripts alike.
 *
 * ## Canonical rule (Rule 7)
 *
 * A canonical URL is emitted **only** when `PUBLIC_SITE_URL` is set at
 * build time (read from `import.meta.env.PUBLIC_SITE_URL`). Dev / preview
 * environments deliberately skip the tag rather than hard-coding a
 * placeholder that would be wrong the moment the site deploys.
 *
 * ## Twitter card
 *
 * We emit `summary_large_image` (assumes every page has a usable OG image
 * at 1200×630). Default OG image path is `/og/default.png` — the file
 * itself lives under `apps/web/public/og/` (not created here; referenced
 * only).
 */
export interface PageSeoInput {
  /** Page `<title>` content. Usually `"<Page> — TerraSight"`. */
  title: string;
  /** Meta description (≤ 160 chars ideally). */
  description: string;
  /**
   * Path (e.g., `/rankings/air-quality-pm25`). Always an absolute path,
   * leading slash, no trailing slash. Used for canonical + OG URL.
   */
  path: string;
  /** Optional OG / Twitter image URL. Defaults to `/og/default.png`. */
  image?: string;
  /** OpenGraph `og:type`. Defaults to `website`. */
  type?: 'website' | 'article';
}

export interface MetaTag {
  property?: string;
  name?: string;
  content: string;
}

export interface PageMeta {
  title: string;
  description: string;
  /**
   * Absolute canonical URL. Only non-null when `PUBLIC_SITE_URL` was set
   * at build time. Never a placeholder.
   */
  canonicalUrl: string | null;
  ogTags: MetaTag[];
  twitterTags: MetaTag[];
}

const DEFAULT_OG_IMAGE = '/og/default.png';

/**
 * Resolve the site URL from `import.meta.env.PUBLIC_SITE_URL`, trimmed
 * of any trailing slash. Returns `null` when unset — callers must treat
 * `null` as "do not emit canonical / absolute OG URL".
 *
 * Exported so the sitemap helper + `BaseLayout` can share one source of
 * truth for the env-var lookup.
 */
export function resolveSiteUrl(): string | null {
  // `import.meta.env.PUBLIC_SITE_URL` is typed as `string | undefined`
  // by Astro/Vite. Cast to the same shape for compatibility with both
  // .astro and .ts consumers.
  const raw = (import.meta as unknown as { env?: Record<string, string | undefined> })
    .env?.PUBLIC_SITE_URL;
  if (!raw || typeof raw !== 'string') return null;
  const trimmed = raw.trim();
  if (trimmed.length === 0) return null;
  return trimmed.replace(/\/$/, '');
}

/**
 * Build the per-page meta bundle consumed by `BaseLayout.astro`.
 *
 * When `PUBLIC_SITE_URL` is not set, `canonicalUrl` is `null` and the
 * OG `og:url` tag is emitted as a relative path. This matches the
 * Step 7 policy: never hard-code a placeholder absolute URL.
 */
export function buildPageMeta(input: PageSeoInput): PageMeta {
  const {
    title,
    description,
    path,
    image = DEFAULT_OG_IMAGE,
    type = 'website',
  } = input;

  const site = resolveSiteUrl();
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;

  const canonicalUrl = site ? `${site}${normalizedPath}` : null;
  const ogUrl = canonicalUrl ?? normalizedPath;
  const ogImage = image.startsWith('http') || !site
    ? image
    : `${site}${image.startsWith('/') ? image : `/${image}`}`;

  const ogTags: MetaTag[] = [
    { property: 'og:type', content: type },
    { property: 'og:title', content: title },
    { property: 'og:description', content: description },
    { property: 'og:url', content: ogUrl },
    { property: 'og:image', content: ogImage },
    { property: 'og:site_name', content: 'TerraSight' },
  ];

  const twitterTags: MetaTag[] = [
    { name: 'twitter:card', content: 'summary_large_image' },
    { name: 'twitter:title', content: title },
    { name: 'twitter:description', content: description },
    { name: 'twitter:image', content: ogImage },
  ];

  return {
    title,
    description,
    canonicalUrl,
    ogTags,
    twitterTags,
  };
}

/**
 * Public SEO input alias for `.astro` page props.
 *
 * `.astro` files can import this type (they read types through the
 * sibling .ts file pattern, same as `AdSlot.types.ts`).
 */
export type PageSeo = PageSeoInput;
