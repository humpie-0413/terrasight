# EarthPulse — Deployment Guide

## Architecture

```
Browser
  └── Cloudflare Pages (frontend SPA)
        └── VITE_API_BASE → Render (FastAPI backend)
                              └── external APIs (FIRMS, AirNow, OpenAQ, ...)
```

---

## Option Comparison

| | **A — Vercel + Render** | **B — CF Pages + Render ✅ recommended** | **C — CF Pages + Fly.io** |
|---|---|---|---|
| Frontend CDN | Vercel Edge Network | Cloudflare Edge (200+ PoPs) | Cloudflare Edge (200+ PoPs) |
| Frontend free tier | 100 GB bandwidth/mo | **Unlimited bandwidth** | **Unlimited bandwidth** |
| Backend free tier | Render sleeps 15 min | Render sleeps 15 min | **Fly.io always-on (shared CPU)** |
| Backend cold start | ~30 s | ~30 s | <5 s |
| Backend paid tier | Render $7/mo starter | Render $7/mo starter | Fly.io ~$2-5/mo (usage) |
| Config complexity | Low | Low | Medium (needs Dockerfile + fly CLI) |
| Best for | Quick start | **SEO portal (unlimited BW)** | Lowest cold-start cost |

**Recommendation: Option B.** Cloudflare Pages has no bandwidth cap — critical for an
SEO-driven portal where Local Report pages will attract long-tail search traffic. Render
free tier is fine for MVP; upgrade to Starter ($7/mo) once the site has regular traffic.

---

## Option B — Setup Steps

### 1. Deploy Backend (Render)

1. Push this repo to GitHub.
2. Go to [render.com](https://render.com) → New → Blueprint → connect repo.
   Render picks up `render.yaml` automatically.
3. In the Render dashboard → **Environment** → add secret env vars:
   ```
   AIRNOW_API_KEY=<your key>
   FIRMS_MAP_KEY=<your key>
   OPENAQ_API_KEY=<your key>
   ```
4. Note the deployed URL: `https://earthpulse-api.onrender.com`
5. Update `CORS_ORIGINS` in the Render env to include your CF Pages URL once you know it.

### 2. Deploy Frontend (Cloudflare Pages)

1. Go to [pages.cloudflare.com](https://pages.cloudflare.com) → Create project → connect GitHub.
2. Build settings:
   - **Framework preset:** None (manual)
   - **Root directory:** `frontend`
   - **Build command:** `npm run build`
   - **Build output directory:** `dist`
3. Add environment variable:
   ```
   VITE_API_BASE = https://earthpulse-api.onrender.com/api
   ```
4. Deploy. Your site will be at `https://earthpulse.pages.dev` (or custom domain).

### 3. Update CORS

After both are deployed, update the backend `CORS_ORIGINS` on Render:
```
CORS_ORIGINS=["https://earthpulse.pages.dev"]
```
Then trigger a redeploy on Render.

### 4. Custom Domain (optional)

- **Cloudflare Pages:** Pages dashboard → Custom domains → add your domain.
- **Render:** Dashboard → Settings → Custom Domains.
- Update `CORS_ORIGINS` on Render to include the custom domain.

---

## Local Development

```bash
# Terminal 1 — backend
cd /path/to/terrasight
cp .env.example .env        # fill in your API keys
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload

# Terminal 2 — frontend
cd frontend
npm install
npm run dev                 # proxy /api → localhost:8000 via vite.config.ts
```

---

## Environment Variables Reference

| Variable | Required | Used by | Notes |
|---|---|---|---|
| `DEBUG` | No | backend | default `false` |
| `CORS_ORIGINS` | Prod | backend | JSON array of allowed origins |
| `FIRMS_MAP_KEY` | P0 | fires globe layer | free instant registration |
| `AIRNOW_API_KEY` | P0 | Block 1 current AQI | free registration |
| `OPENAQ_API_KEY` | P0 | air monitors globe | free registration |
| `EPA_AQS_EMAIL` | P1 | annual PM2.5 trend | paired with key below |
| `EPA_AQS_KEY` | P1 | annual PM2.5 trend | 10 req/min limit |
| `CAMS_ADS_KEY` | P1 | smoke/AOD globe layer | manual approval |
| `VITE_API_BASE` | Prod | frontend | set to Render backend URL |

---

## Dockerfile Notes

The `Dockerfile` at repo root can be used for Render (blueprint auto-detects it),
Fly.io, Railway, or local container testing:

```bash
# Local container test
docker build -t earthpulse-api .
docker run -p 8000:8000 \
  -e AIRNOW_API_KEY=xxx \
  -e FIRMS_MAP_KEY=xxx \
  earthpulse-api
```

---

## Render Free Tier Workaround

The Render free tier spins down after 15 minutes of inactivity. The ranking page
already warns users that ECHO calls take 30–60 s. If cold-start latency becomes
a user-experience problem before you upgrade:

- Add an uptime ping (e.g., [UptimeRobot](https://uptimerobot.com) free plan pings
  `GET /health` every 5 minutes to keep the instance warm).
- Or upgrade to Render Starter ($7/mo) for always-on.
