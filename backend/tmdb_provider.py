from __future__ import annotations

import logging
from typing import Any, Dict, Optional
import requests

from .metadata_utils import ExternalMetadataResult, TitleNormalizer, RetryStrategy

# Configure logging
logger = logging.getLogger(__name__)

class TMDBProvider:
    """
    TMDB metadata provider.
    
    Advantages over OMDB:
    - Returns both IMDB ID and TMDB ID
    - Multiple search results for better matching
    - Better support for international titles
    - Free API with higher rate limits
    """
    
    BASE_URL = "https://api.themoviedb.org/3"
    
    def __init__(self, api_key: str, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize TMDB provider with API key."""
        self.api_key = api_key
        self.config = config or {}
        
        self.title_normalizer = TitleNormalizer()
        self.retry_strategy = RetryStrategy(
            max_retries=self.config.get("max_retries", 3),
            initial_backoff=self.config.get("backoff_factor", 1.0),
            multiplier=self.config.get("backoff_multiplier", 1.5),
        )
        
    @property
    def provider_name(self) -> str:
        return "TMDB"
    
    def get_imdb_id(
        self,
        title: str,
        original_title: Optional[str] = None,
        year: Optional[int] = None,
        media_type: str = "movie"
    ) -> ExternalMetadataResult:
        """
        Fetch IMDB ID and TMDB ID from TMDB.
        Tries Movie search first, then TV search.
        """

        # Generate search candidates
        search_candidates = self.title_normalizer.generate_title_variants(title, original_title)
        
        # Ensure simple title and original title are at the top
        if title not in search_candidates:
             search_candidates.insert(0, title)
        if original_title and original_title != title and original_title not in search_candidates:
             search_candidates.insert(1, original_title)

        # ... (candidates generation)

        search_order = []
        if media_type == "movie":
            search_order = ["movie", "tv"]
        elif media_type == "tv" or media_type == "series":
            search_order = ["tv", "movie"]
        else:
            search_order = ["movie", "tv"] # Default

        for m_type in search_order:
            for candidate in search_candidates:
                # A. Strict search
                if m_type == "movie":
                    tmdb_id = self._search_movie(candidate, year)
                    if tmdb_id: return self._get_movie_details(tmdb_id)
                else:
                    tmdb_id = self._search_tv(candidate, year)
                    if tmdb_id: return self._get_tv_details(tmdb_id)
                
                # B. Fuzzy year search (if year provided)
                if year:
                    if m_type == "movie":
                        tmdb_id = self._search_movie(candidate, year=None, target_year=year)
                        if tmdb_id: return self._get_movie_details(tmdb_id)
                    else:
                        tmdb_id = self._search_tv(candidate, year=None, target_year=year)
                        if tmdb_id: return self._get_tv_details(tmdb_id)
        
        return ExternalMetadataResult(
            success=False,
            source_provider=self.provider_name,
            error_message="No match found in Movie or TV results"
        )

    def _search_movie(self, title: str, year: Optional[int], target_year: Optional[int] = None) -> Optional[int]:
        """Search for a movie."""
        return self._search_generic("movie", title, year, target_year)

    def _search_tv(self, title: str, year: Optional[int], target_year: Optional[int] = None) -> Optional[int]:
        """Search for a TV show."""
        return self._search_generic("tv", title, year, target_year)

    def _search_generic(self, media_type: str, title: str, year: Optional[int], target_year: Optional[int] = None) -> Optional[int]:
        """
        Generic search for movie or tv.
        media_type: 'movie' or 'tv'
        """
        endpoint = f"search/{media_type}"
        params = {
            "api_key": self.api_key,
            "query": title,
            "include_adult": "false",
            "page": 1
        }
        
        # TMDB API params differ slightly
        if year:
            if media_type == "movie":
                params["year"] = str(year) # release_year for movies (or just year)
            else:
                params["first_air_date_year"] = str(year) # first_air_date_year for TV
            
        def do_search() -> ExternalMetadataResult:
            response = requests.get(f"{self.BASE_URL}/{endpoint}", params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            results = data.get("results", [])
            
            if not results:
                return ExternalMetadataResult(success=False, source_provider=self.provider_name)
                
            # If target_year is provided (fuzzy search), find best match
            if target_year and not year:
                for item in results:
                    # Get date string (release_date for movie, first_air_date for tv)
                    date_str = item.get("release_date") if media_type == "movie" else item.get("first_air_date")
                    
                    if date_str:
                        try:
                            item_year = int(date_str.split("-")[0])
                            if abs(item_year - target_year) <= 2:
                                return ExternalMetadataResult(
                                    success=True,
                                    tmdb_id=str(item["id"]),
                                    source_provider=self.provider_name
                                )
                        except (ValueError, IndexError):
                            continue
                
                return ExternalMetadataResult(success=False, source_provider=self.provider_name)
                
            # Default: First result
            return ExternalMetadataResult(
                success=True,
                tmdb_id=str(results[0]["id"]),
                source_provider=self.provider_name
            )

        try:
            result = self.retry_strategy.execute(do_search, title)
            if result.success and result.tmdb_id:
                return int(result.tmdb_id)
            return None
        except Exception as e:
            logger.warning(f"TMDB: {media_type.upper()} search failed for '{title}': {e}")
            return None

    def _get_movie_details(self, tmdb_id: int) -> ExternalMetadataResult:
        return self._get_details_generic(tmdb_id, "movie")

    def _get_tv_details(self, tmdb_id: int) -> ExternalMetadataResult:
        return self._get_details_generic(tmdb_id, "tv")

    def _get_details_generic(self, tmdb_id: int, media_type: str) -> ExternalMetadataResult:
        """Get details for movie or tv."""
        try:
            url = f"{self.BASE_URL}/{media_type}/{tmdb_id}"
            params = {
                "api_key": self.api_key,
                "append_to_response": "external_ids"
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            external_ids = data.get("external_ids", {})
            imdb_id = external_ids.get("imdb_id")
            
            result_data = {
                "tmdb_id": str(tmdb_id),
                "source_provider": self.provider_name,
                "success": True,
                # "media_type": media_type # TODO: Add if supported in Result
            }
            
            if imdb_id:
                result_data["imdb_id"] = imdb_id
                result_data["imdb_url"] = f"https://www.imdb.com/title/{imdb_id}/"
            
            # Extract rating data (TMDB uses 0-10 scale)
            if data.get("vote_average"):
                result_data["vote_average"] = float(data["vote_average"])
            if data.get("vote_count"):
                result_data["vote_count"] = int(data["vote_count"])
                
            return ExternalMetadataResult(**result_data)
            
        except Exception as e:
            logger.error(f"TMDB: Failed to get {media_type} details for ID {tmdb_id}: {e}")
            return ExternalMetadataResult(
                success=False,
                source_provider=self.provider_name,
                error_message=str(e)
            )

    def test_connection(self) -> bool:
        """Test whether the provider is reachable."""
        try:
            response = requests.get(
                f"{self.BASE_URL}/configuration",
                params={"api_key": self.api_key},
                timeout=10
            )
            return response.status_code == 200
        except Exception:
            return False
