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
        media_type: str = "movie",
        tmdb_id: Optional[int] = None,
        mubi_directors: Optional[list] = None,
        mubi_runtime: Optional[int] = None
    ) -> ExternalMetadataResult:
        """
        Fetch IMDB ID and TMDB ID from TMDB.
        Tries Movie search first, then TV search.
        If tmdb_id is provided, skips search and fetches details directly.
        
        Args:
            mubi_directors: List of director names from Mubi for disambiguation.
            mubi_runtime: Runtime in minutes from Mubi for disambiguation.
        """
        
        # Optimization: Use existing TMDB ID if provided
        if tmdb_id:
            try:
                tid = int(tmdb_id)
                if media_type == "movie":
                    return self._get_movie_details(tid)
                else:
                    return self._get_tv_details(tid)
            except (ValueError, TypeError):
                logger.warning(f"Invalid TMDB ID provided: {tmdb_id}. Falling back to search.")


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
                # A. Strict search (with disambiguation signals)
                if m_type == "movie":
                    found_id = self._search_movie(candidate, year, 
                                                   mubi_directors=mubi_directors, 
                                                   mubi_runtime=mubi_runtime)
                    if found_id: return self._get_movie_details(found_id)
                else:
                    found_id = self._search_tv(candidate, year,
                                                mubi_directors=mubi_directors,
                                                mubi_runtime=mubi_runtime)
                    if found_id: return self._get_tv_details(found_id)
                
                # B. Fuzzy year search (if year provided)
                if year:
                    if m_type == "movie":
                        found_id = self._search_movie(candidate, year=None, target_year=year,
                                                       mubi_directors=mubi_directors,
                                                       mubi_runtime=mubi_runtime)
                        if found_id: return self._get_movie_details(found_id)
                    else:
                        found_id = self._search_tv(candidate, year=None, target_year=year,
                                                    mubi_directors=mubi_directors,
                                                    mubi_runtime=mubi_runtime)
                        if found_id: return self._get_tv_details(found_id)
        
        return ExternalMetadataResult(
            success=False,
            source_provider=self.provider_name,
            error_message="No match found in Movie or TV results"
        )


    def _search_movie(self, title: str, year: Optional[int], target_year: Optional[int] = None,
                      mubi_directors: Optional[list] = None, mubi_runtime: Optional[int] = None) -> Optional[int]:
        """Search for a movie."""
        return self._search_generic("movie", title, year, target_year, mubi_directors, mubi_runtime)

    def _search_tv(self, title: str, year: Optional[int], target_year: Optional[int] = None,
                   mubi_directors: Optional[list] = None, mubi_runtime: Optional[int] = None) -> Optional[int]:
        """Search for a TV show."""
        return self._search_generic("tv", title, year, target_year, mubi_directors, mubi_runtime)

    def _search_generic(self, media_type: str, title: str, year: Optional[int], target_year: Optional[int] = None,
                        mubi_directors: Optional[list] = None, mubi_runtime: Optional[int] = None) -> Optional[int]:
        """
        Generic search for movie or tv.
        media_type: 'movie' or 'tv'
        
        When multiple results are returned, uses scoring to disambiguate:
        - Director match: +10 points
        - Runtime match (±3 min): +5 points
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
            
            # Single result: no ambiguity
            if len(results) == 1:
                return ExternalMetadataResult(
                    success=True,
                    tmdb_id=str(results[0]["id"]),
                    source_provider=self.provider_name
                )
            
            # Multiple results: apply scoring if disambiguation signals available
            if mubi_directors or mubi_runtime:
                scored_results = []
                for item in results:
                    score = 0
                    tmdb_id = item["id"]
                    
                    # A. Director match (+10 pts)
                    if mubi_directors:
                        credits = self._get_credits(tmdb_id, media_type)
                        tmdb_directors = [c.get("name", "").lower() for c in credits.get("crew", []) 
                                          if c.get("job") == "Director"]
                        mubi_directors_lower = [d.lower() for d in mubi_directors]
                        if any(d in tmdb_directors for d in mubi_directors_lower):
                            score += 10
                            logger.debug(f"Director match for TMDB {tmdb_id}: +10")
                    
                    # B. Runtime match (+5 pts)
                    if mubi_runtime:
                        tmdb_runtime = item.get("runtime")  # May not be in search results
                        if tmdb_runtime is None:
                            details = self._get_details_light(tmdb_id, media_type)
                            tmdb_runtime = details.get("runtime")
                        if tmdb_runtime and abs(tmdb_runtime - mubi_runtime) <= 3:
                            score += 5
                            logger.debug(f"Runtime match for TMDB {tmdb_id} ({tmdb_runtime}min): +5")
                    
                    scored_results.append((score, item))
                
                # Sort by score descending
                scored_results.sort(key=lambda x: -x[0])
                best_score, best_item = scored_results[0]
                
                if best_score >= 10:
                    logger.info(f"Disambiguated '{title}' by director match -> TMDB ID {best_item['id']}")
                elif best_score >= 5:
                    logger.info(f"Disambiguated '{title}' by runtime match -> TMDB ID {best_item['id']}")
                elif best_score > 0:
                    logger.info(f"Partial disambiguation for '{title}' (score={best_score}) -> TMDB ID {best_item['id']}")
                else:
                    logger.warning(f"'{title}': {len(results)} candidates, no strong signal. Using first result.")
                
                return ExternalMetadataResult(
                    success=True,
                    tmdb_id=str(best_item["id"]),
                    source_provider=self.provider_name
                )
            
            # If target_year is provided (fuzzy search without disambiguation signals), find year match
            if target_year and not year:
                for item in results:
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
                
            # Default: First result (no disambiguation signals provided)
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


    def _get_credits(self, tmdb_id: int, media_type: str) -> dict:
        """Fetch credits (cast/crew) for a movie or TV show."""
        endpoint = f"{media_type}/{tmdb_id}/credits"
        try:
            response = requests.get(
                f"{self.BASE_URL}/{endpoint}",
                params={"api_key": self.api_key},
                timeout=10
            )
            if response.ok:
                return response.json()
        except Exception as e:
            logger.debug(f"Failed to fetch credits for {media_type}/{tmdb_id}: {e}")
        return {"crew": [], "cast": []}

    def _get_details_light(self, tmdb_id: int, media_type: str) -> dict:
        """Fetch lightweight details (runtime, etc.) for a movie or TV show."""
        endpoint = f"{media_type}/{tmdb_id}"
        try:
            response = requests.get(
                f"{self.BASE_URL}/{endpoint}",
                params={"api_key": self.api_key},
                timeout=10
            )
            if response.ok:
                return response.json()
        except Exception as e:
            logger.debug(f"Failed to fetch details for {media_type}/{tmdb_id}: {e}")
        return {}

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

