"""NASA GIBS (Global Imagery Browse Services) WMTS layer manifest.

v2 scope: this module is a *pure manifest generator*. It emits
validated :class:`LayerManifest` entries describing the five
browser-direct imagery layers that the v2 Globe island loads from
the NASA GIBS REST WMTS endpoint. No network calls, no FastAPI, no
Hono — the Worker never proxies GIBS imagery (see
``docs/architecture/architecture-v2.md`` §7).

Reference docs
--------------
- ``docs/datasets/gibs-approved-layers.md`` — single source of truth
  for layer IDs, titles, URL templates, and caveats.
- ``docs/datasets/normalized-contracts.md`` §4 — LayerManifest freeze.
- ``pipelines/contracts/__init__.py`` — pydantic mirror of the zod
  schema in ``packages/schemas/src/index.ts``.

Landmines (from Step 2 live spike — all verified 2026-04-17)
------------------------------------------------------------
1. ``VIIRS_SNPP_DayNightBand_ENCC`` frozen 2023-07-07 — current-date
   requests return HTTP 400. Why it matters: substituting the ENCC
   variant for recent dates silently breaks Night Lights in prod.
2. ``TileMatrixSet`` varies per layer (500m / 1km / 2km) — cannot
   hardcode one value. Why it matters: using 2km for SST (which is
   1km) yields HTTP 400 and an empty globe.
3. Date token format is ``YYYY-MM-DD`` only — ``T00:00:00Z`` or any
   ISO datetime returns HTTP 400. Why it matters: naive
   ``date.isoformat()`` output is fine, but ``datetime.isoformat()``
   is NOT and will silently break.
4. CesiumJS 1.140 ``WebMapTileServiceImageryProvider.fromUrl()`` is
   async and must be awaited. Why it matters: the sync constructor
   still works without GetCapabilities, so prefer
   ``new WebMapTileServiceImageryProvider({ urlTemplate, ... })`` to
   keep init synchronous and avoid ``Promise<ImageryProvider>`` leaks.

Public API
----------
- ``GIBS_MANIFESTS``: frozen list of 5 LayerManifest instances.
- ``get_manifest(layer_id)``: lookup by ``LayerManifest.id``. Raises
  :class:`KeyError` for unknown or *explicitly banned* ids (ENCC).
- ``all_manifests()``: returns a new list copy of GIBS_MANIFESTS.
"""

from pipelines.contracts import LayerImagery, LayerLegend, LayerManifest

# REST WMTS template pattern (Cesium-compatible). Note: {Time} and
# {TileMatrixSet} are layer-specific — never hardcode the former, and
# let Cesium substitute the latter via `tileMatrixSetID`.
_WMTS_REST_BASE = "https://gibs.earthdata.nasa.gov/wmts/epsg4326/best"

# Layer IDs we MUST refuse to serve even if the caller asks nicely.
# Currently: the ENCC "enhanced near-constant contrast" Day/Night
# Band variant, frozen at 2023-07-07 (see landmine #1).
_BANNED_LAYER_IDS: frozenset[str] = frozenset(
    {"VIIRS_SNPP_DayNightBand_ENCC"}
)


def _wmts_url(layer_id: str, date_token: str, tms: str, ext: str) -> str:
    """Assemble the GIBS REST WMTS URL template for CesiumJS.

    ``date_token`` is the literal to embed in the date slot. For static
    layers pass ``"default"``. For daily layers pass ``"{Time}"`` so
    the browser-side provider can substitute the current date.
    """
    return (
        f"{_WMTS_REST_BASE}/{layer_id}/default/{date_token}/"
        f"{tms}/{{TileMatrix}}/{{TileRow}}/{{TileCol}}.{ext}"
    )


# ---------------------------------------------------------------------------
# 5 approved manifests (verified against docs/datasets/gibs-approved-layers.md)
# ---------------------------------------------------------------------------

_BLUE_MARBLE = LayerManifest(
    id="BlueMarble_ShadedRelief_Bathymetry",
    title="Natural Earth",
    category="imagery",
    kind="continuous",
    source="NASA GIBS / Blue Marble",
    trustTag="observed",
    coverage="global",
    cadence="monthly",
    enabled=True,
    imagery=LayerImagery(
        type="wmts",
        urlTemplate=_wmts_url(
            "BlueMarble_ShadedRelief_Bathymetry",
            "default",
            "500m",
            "jpg",
        ),
        tileMatrixSet="500m",
        availableDates="static",
    ),
    eventApi=None,
    legend=None,
    caveats=[
        "Monthly composite — not real-time.",
        "UI label must read 'Natural Earth', not 'Blue Marble' "
        "(avoid brand confusion with the NASA Blue Marble Navigator).",
    ],
)


_SST = LayerManifest(
    id="GHRSST_L4_MUR_Sea_Surface_Temperature",
    title="Sea Surface Temperature (SST)",
    category="imagery",
    kind="continuous",
    source="NASA JPL MUR GHRSST L4 via GIBS",
    trustTag="near-real-time",
    coverage="ocean-only",
    cadence="daily",
    enabled=True,
    imagery=LayerImagery(
        type="wmts",
        urlTemplate=_wmts_url(
            "GHRSST_L4_MUR_Sea_Surface_Temperature",
            "{Time}",
            "1km",
            "png",
        ),
        tileMatrixSet="1km",
        availableDates="2002-06-01/present (daily)",
    ),
    eventApi=None,
    legend=LayerLegend(
        unit="\u00b0C",
        min=-2.0,
        max=32.0,
        colormap="thermal",
    ),
    caveats=[
        "1-day latency (NRT).",
        "Polar regions are interpolated.",
        "Click values come from Worker /api/sst-point (OISST) — do NOT "
        "reverse-engineer the GIBS tile RGB to obtain temperatures.",
    ],
)


_AOD = LayerManifest(
    id="MODIS_Terra_Aerosol",
    title="Aerosol Proxy (AOD)",
    category="imagery",
    kind="continuous",
    source="MODIS Terra — NASA GSFC via GIBS",
    trustTag="near-real-time",
    coverage="global",
    cadence="daily",
    enabled=True,
    imagery=LayerImagery(
        type="wmts",
        urlTemplate=_wmts_url(
            "MODIS_Terra_Aerosol",
            "{Time}",
            "2km",
            "png",
        ),
        tileMatrixSet="2km",
        availableDates="2000-02-24/present (daily)",
    ),
    eventApi=None,
    legend=None,
    caveats=[
        "AOD = column-integrated aerosol optical depth (unitless).",
        "Do NOT label as PM2.5, particulate matter, or air-quality index.",
        "Combined land + ocean product.",
        "Click behaviour: descriptive card only — no value readout.",
    ],
)


_CLOUDS = LayerManifest(
    id="MODIS_Aqua_Cloud_Fraction_Day",
    title="Cloud Fraction (Day)",
    category="imagery",
    kind="continuous",
    source="MODIS Aqua — NASA GSFC via GIBS",
    trustTag="near-real-time",
    coverage="global",
    cadence="daily",
    enabled=True,
    imagery=LayerImagery(
        type="wmts",
        urlTemplate=_wmts_url(
            "MODIS_Aqua_Cloud_Fraction_Day",
            "{Time}",
            "2km",
            "png",
        ),
        tileMatrixSet="2km",
        availableDates="2002-07-04/present (daily)",
    ),
    eventApi=None,
    legend=None,
    caveats=[
        "Day-pass only — night hemisphere blank.",
        "Click behaviour: descriptive card only — no value readout.",
    ],
)


_NIGHT_LIGHTS = LayerManifest(
    id="VIIRS_SNPP_DayNightBand",
    title="Night Lights",
    category="imagery",
    kind="continuous",
    source="VIIRS Suomi NPP Day/Night Band via GIBS",
    trustTag="near-real-time",
    coverage="global",
    cadence="daily",
    enabled=True,
    imagery=LayerImagery(
        type="wmts",
        urlTemplate=_wmts_url(
            "VIIRS_SNPP_DayNightBand",
            "{Time}",
            "1km",
            "png",
        ),
        tileMatrixSet="1km",
        availableDates="2012-01-19/present (daily)",
    ),
    eventApi=None,
    legend=None,
    caveats=[
        "Label as 'human activity proxy' — not a direct electricity "
        "consumption measurement.",
        "Raw radiance, no atmospheric correction; ocean/ice glare is "
        "expected.",
        "`VIIRS_SNPP_DayNightBand_ENCC` variant frozen 2023-07-07; do "
        "not substitute — current-date requests return HTTP 400.",
    ],
)


GIBS_MANIFESTS: list[LayerManifest] = [
    _BLUE_MARBLE,
    _SST,
    _AOD,
    _CLOUDS,
    _NIGHT_LIGHTS,
]


def get_manifest(layer_id: str) -> LayerManifest:
    """Return the :class:`LayerManifest` whose ``id`` matches ``layer_id``.

    Raises :class:`KeyError` when no manifest matches, or when the
    caller asks for a layer that is explicitly banned (e.g. the
    VIIRS ENCC variant — see landmine #1).
    """
    if layer_id in _BANNED_LAYER_IDS:
        raise KeyError(
            f"Layer {layer_id!r} is banned (frozen variant — see "
            f"gibs-approved-layers.md). Use VIIRS_SNPP_DayNightBand "
            f"instead."
        )
    for manifest in GIBS_MANIFESTS:
        if manifest.id == layer_id:
            return manifest
    raise KeyError(
        f"Layer {layer_id!r} is not in GIBS_MANIFESTS. Approved ids: "
        f"{sorted(m.id for m in GIBS_MANIFESTS)}"
    )


def all_manifests() -> list[LayerManifest]:
    """Return a *new* list copy of the approved manifests."""
    return list(GIBS_MANIFESTS)


__all__ = [
    "GIBS_MANIFESTS",
    "get_manifest",
    "all_manifests",
]
