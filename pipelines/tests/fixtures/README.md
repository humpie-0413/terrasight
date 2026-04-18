# pipelines/tests/fixtures

One directory per connector. Every fixture JSON file MUST be:

1. **Trimmed** — no more than ~15 sample records per file. We want
   representative shapes, not a full snapshot of the source's data.
2. **Offline-playable** — contract tests load these via `json.loads()`
   and feed them to `connector.normalize(raw)`. No network calls in the
   test path.
3. **Stamped** — every fixture JSON has a top-level
   `{ "_recorded_at": "YYYY-MM-DD", "_source_url": "...", "_notes": "..." }`
   block so future readers can reproduce the capture.
4. **Include failure cases** — land-cell nulls, empty feeds, 400s.
   Contract tests assert graceful `status: error | not_configured`.

## Layout

```
pipelines/tests/fixtures/
├── gibs/                   # HEAD-probe metadata per layer manifest
│   ├── blue_marble.json
│   ├── sst.json
│   ├── aod.json
│   ├── clouds.json
│   └── night_lights.json
├── firms/
│   ├── sample-normalized.json      # 10 fires, normalized EventPoint[]
│   ├── empty-feed.json             # zero-row CSV edge case
│   └── auth-error.json             # simulated 400 from bad MAP_KEY
├── usgs/
│   ├── earthquakes-all-day.json    # ~15 trimmed features
│   └── empty-feed.json
└── erddap_sst/
    ├── point-ocean.json            # successful point result
    ├── point-land-null.json        # JSON null = land/ice cell
    └── point-error.json            # ERDDAP 500 simulation
```

## Capture recipe

```python
# From a repo-rooted `uv run python`:
import asyncio, json, httpx
async def capture():
    async with httpx.AsyncClient() as c:
        r = await c.get("https://.../...")
        return r.text if r.headers["content-type"].startswith("text") else r.json()
data = asyncio.run(capture())
# Trim to ~15 records here, then save with the stamp block above.
```

Never commit fixtures >500 KB. For large rasters, commit a metadata-only
stub (dimensions, content-type, first-byte sample).
