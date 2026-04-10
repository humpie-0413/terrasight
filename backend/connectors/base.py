"""Abstract base class for external data source connectors.

Every connector normalizes data into a dict with:
- values
- metadata (cadence, trust tag, source, source URL, spatial scope, license)

Connectors MUST attach a trust tag from the 5-level vocabulary:
observed / near-real-time / forecast / derived / estimated.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal

TrustTag = Literal["observed", "near-real-time", "forecast", "derived", "estimated"]


@dataclass
class ConnectorResult:
    values: Any
    source: str
    source_url: str
    cadence: str
    tag: TrustTag
    spatial_scope: str
    license: str
    notes: list[str] = field(default_factory=list)


class BaseConnector(ABC):
    """Base connector: fetch → normalize → cache."""

    name: str
    source: str
    source_url: str
    cadence: str
    tag: TrustTag

    @abstractmethod
    async def fetch(self, **params: Any) -> Any:
        """Call the external API."""

    @abstractmethod
    def normalize(self, raw: Any) -> ConnectorResult:
        """Transform raw payload into a ConnectorResult."""

    async def cache(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Write to Redis cache (implemented by subclasses / helpers)."""
        # TODO: wire up Redis client
        _ = (key, value, ttl)

    async def run(self, **params: Any) -> ConnectorResult:
        raw = await self.fetch(**params)
        return self.normalize(raw)
