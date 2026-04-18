"""Simple file-system PNG cache with TTL.

Stores rendered PNGs in /tmp/terrasight_cache/ with a timestamp suffix.
get() returns bytes if cache is fresh, None if stale/missing.
put() writes bytes and cleans stale entries for the same key.
"""
from __future__ import annotations

import time
from pathlib import Path

CACHE_DIR = Path("/tmp/terrasight_cache")


def _ensure_dir() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _cache_path(key: str) -> Path:
    """Sanitize key into a safe filename."""
    safe = key.replace("/", "_").replace(".", "_")
    return CACHE_DIR / f"{safe}.png"


def _meta_path(key: str) -> Path:
    safe = key.replace("/", "_").replace(".", "_")
    return CACHE_DIR / f"{safe}.meta"


def get(key: str, ttl_seconds: int = 21600) -> bytes | None:
    """Return cached PNG bytes if within TTL, else None."""
    _ensure_dir()
    cache_file = _cache_path(key)
    meta_file = _meta_path(key)
    if not cache_file.exists() or not meta_file.exists():
        return None
    try:
        written_at = float(meta_file.read_text().strip())
    except (ValueError, OSError):
        return None
    if time.time() - written_at > ttl_seconds:
        return None
    try:
        return cache_file.read_bytes()
    except OSError:
        return None


def put(key: str, data: bytes) -> None:
    """Write PNG bytes to cache with current timestamp."""
    _ensure_dir()
    _cache_path(key).write_bytes(data)
    _meta_path(key).write_text(str(time.time()))
