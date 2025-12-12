from __future__ import annotations

from typing import Any, Dict, Optional

import requests
import xbmc

from .base import BaseMetadataProvider, ExternalMetadataResult
from .title_utils import TitleNormalizer, RetryStrategy


class TMDBProvider(BaseMetadataProvider):
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
        super().__init__(api_key, config)
        
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
        
        Returns ExternalMetadataResult with:
        - imdb_id: IMDB identifier (e.g., "tt0133093")
        - tmdb_id: TMDB identifier (e.g., "603")
        - source_provider: "TMDB"
        """


        # Generate search candidates (Original Title, Title, Variants)
        search_candidates = self.title_normalizer.generate_title_variants(title, original_title)
        
        # Ensure simple title and original title are at the top of the list if not already
        if title not in search_candidates:
             search_candidates.insert(0, title)
        if original_title and original_title != title and original_title not in search_candidates:
             search_candidates.insert(1, original_title)

        tmdb_id = None
        
        for candidate in search_candidates:
            # 1. Try strict search with year
            tmdb_id = self._search_movie(candidate, year)
            if tmdb_id:
                break
                
            # 2. If year provided, try searching WITHOUT year (fuzzy match)
            # This handles cases where MUBI year is off by ±1 year
            if year:
                xbmc.log(f"TMDB: Trying fuzzy year search for '{candidate}'", xbmc.LOGDEBUG)
                tmdb_id = self._search_movie(candidate, year=None, target_year=year)
                if tmdb_id:
                    break
        
        if not tmdb_id:
            result = ExternalMetadataResult(
                success=False,
                source_provider=self.provider_name,
                error_message="No match found"
            )
            return result
            
        # Get details to find IMDB ID
        result = self._get_movie_details(tmdb_id)
        

            
        return result

    def _search_movie(self, title: str, year: Optional[int], target_year: Optional[int] = None) -> Optional[int]:
        """
        Search for a movie.
        
        :param title: Title to search for
        :param year: Strict year filter for API
        :param target_year: Use for fuzzy matching when year is None (±1 year tolerance)
        """
        params = {
            "api_key": self.api_key,
            "query": title,
            "include_adult": "false",
            "page": 1
        }
        if year:
            params["year"] = str(year)
            
        def do_search() -> ExternalMetadataResult:
            response = requests.get(f"{self.BASE_URL}/search/movie", params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            results = data.get("results", [])
            
            if not results:
                return ExternalMetadataResult(
                    success=False,
                    source_provider=self.provider_name,
                    error_message="No match found"
                )
                
            # If target_year is provided (fuzzy search), find best match
            if target_year and not year:
                for movie in results:
                    release_date = movie.get("release_date", "")
                    if release_date:
                        try:
                            # Parse year from "YYYY-MM-DD"
                            movie_year = int(release_date.split("-")[0])
                            # Check tolerance ±2 year
                            if abs(movie_year - target_year) <= 2:
                                return ExternalMetadataResult(
                                    success=True,
                                    tmdb_id=str(movie["id"]),
                                    source_provider=self.provider_name
                                )
                        except (ValueError, IndexError):
                            continue
                
                # If no match found within tolerance
                return ExternalMetadataResult(
                    success=False,
                    source_provider=self.provider_name,
                    error_message=f"No match found within 2 years of {target_year}"
                )
                
            # Return the ID of the first result (default strict behavior)
            return ExternalMetadataResult(
                success=True,
                tmdb_id=str(results[0]["id"]),
                source_provider=self.provider_name
            )

        try:
            # retry_strategy expects a function that returns ExternalMetadataResult
            result = self.retry_strategy.execute(do_search, title)
            
            if result.success and result.tmdb_id:
                return int(result.tmdb_id)
            return None
            
        except Exception as e:
            xbmc.log(f"TMDB: Search failed for '{title}': {e}", xbmc.LOGWARNING)
            return None

    def _get_movie_details(self, tmdb_id: int) -> ExternalMetadataResult:
        """Get movie details including external IDs."""
        try:
            # We need the external_ids, which can be fetched with append_to_response
            # or via a separate endpoint. append_to_response is efficient.
            url = f"{self.BASE_URL}/movie/{tmdb_id}"
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
                "success": True
            }
            
            if imdb_id:
                result_data["imdb_id"] = imdb_id
                result_data["imdb_url"] = f"https://www.imdb.com/title/{imdb_id}/"
                
            return ExternalMetadataResult(**result_data)
            
        except Exception as e:
            xbmc.log(f"TMDB: Failed to get details for ID {tmdb_id}: {e}", xbmc.LOGERROR)
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
