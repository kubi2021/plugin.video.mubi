from __future__ import annotations

from typing import Any, Dict, Optional
import xbmc
import xbmcaddon

from .base import BaseMetadataProvider
from .omdb_provider import OMDBProvider
from .tmdb_provider import TMDBProvider






class MetadataProviderFactory:
    """
    Factory for creating metadata provider instances.
    
    Implements automatic provider selection based on API key availability:
    - TMDB preferred when available
    - Falls back to OMDB if only OMDB key available
    - Returns None if no keys configured
    """
    
    @staticmethod
    def _get_api_keys() -> tuple[str, str]:
        """Retrieve API keys from addon settings."""
        try:
            addon = xbmcaddon.Addon()
            omdb_key = addon.getSetting("omdbapiKey")
            tmdb_key = addon.getSetting("tmdb_api_key")
            return omdb_key.strip(), tmdb_key.strip()
        except Exception as e:
            xbmc.log(f"Error retrieving API keys: {e}", xbmc.LOGERROR)
            return "", ""

    @staticmethod
    def validate_configuration() -> bool:
        """
        Check if at least one provider is configured.
        
        :return: True if a provider is ready, False otherwise.
        """
        omdb_key, tmdb_key = MetadataProviderFactory._get_api_keys()
        return bool(omdb_key or tmdb_key)

    @staticmethod
    def open_settings():
        """Open the addon settings dialog."""
        xbmcaddon.Addon().openSettings()

    @staticmethod
    def get_provider() -> Optional[BaseMetadataProvider]:
        """
        Automatically select and instantiate the best available provider.
        
        Selection priority:
        1. TMDB (if TMDB API key available) - preferred provider
        2. OMDB (if OMDB API key available) - fallback provider
        3. None (if no keys available) - graceful degradation
        
        :return: Provider instance or None
        """
        omdb_key, tmdb_key = MetadataProviderFactory._get_api_keys()
        
        # Priority 1: TMDB (preferred when available)
        if tmdb_key:
            xbmc.log(
                "External metadata: Using TMDB provider",
                xbmc.LOGINFO
            )
            return TMDBProvider(api_key=tmdb_key)
        
        # Priority 3: OMDB (fallback for existing users)
        if omdb_key:
            xbmc.log(
                "External metadata: Using OMDB provider",
                xbmc.LOGINFO
            )
            return OMDBProvider(api_key=omdb_key)
        
        # Priority 4: No provider available
        xbmc.log(
            "External metadata: No provider available - no API keys configured",
            xbmc.LOGWARNING
        )
        return None
    



