from __future__ import annotations

from typing import Any, Dict, Optional

from .base import BaseMetadataProvider
from .omdb_provider import OMDBProvider


class ProviderType:
    OMDB = "omdb"
    TVMDB = "tvmdb"


class MetadataProviderFactory:
    """Factory for creating metadata provider instances."""

    @staticmethod
    def create_provider(
        provider_type: str,
        api_key: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> BaseMetadataProvider:
        if provider_type == ProviderType.OMDB:
            return OMDBProvider(api_key, config)
        if provider_type == ProviderType.TVMDB:
            raise NotImplementedError("TVMDB provider is not implemented yet")
        raise ValueError(f"Unknown provider type: {provider_type}")

    @staticmethod
    def get_default_provider(api_key: str) -> BaseMetadataProvider:
        return MetadataProviderFactory.create_provider(
            ProviderType.OMDB,
            api_key,
        )
