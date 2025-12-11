from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class ExternalMetadataResult:
    """Result returned by an external metadata provider."""

    imdb_id: Optional[str] = None
    imdb_url: Optional[str] = None
    tmdb_id: Optional[str] = None
    tvdb_id: Optional[str] = None
    source_provider: str = ""
    success: bool = False
    error_message: Optional[str] = None


class BaseMetadataProvider(ABC):
    """Abstract base class for external metadata providers."""

    def __init__(self, api_key: str, config: Optional[Dict[str, Any]] = None) -> None:
        self.api_key = api_key
        self.config = config or {}

    @abstractmethod
    def get_imdb_id(
        self,
        title: str,
        original_title: Optional[str] = None,
        year: Optional[int] = None,
        media_type: str = "movie",
    ) -> ExternalMetadataResult:
        """Fetch IMDB id for a given title."""
        ...

    @abstractmethod
    def test_connection(self) -> bool:
        """Test whether the provider is reachable."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the human-readable name of the provider."""
        ...
