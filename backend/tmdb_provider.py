from __future__ import annotations

import logging
from typing import Any, Dict, Optional
import requests

from .metadata_utils import ExternalMetadataResult, TitleNormalizer, RetryStrategy

# Configure logging
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
        
        # Determine genres dynamically to avoid hardcoding IDs
        self.movie_genres = self._fetch_genres("movie")
        self.tv_genres = self._fetch_genres("tv")
        
        # Import fuzz for matching
        try:
            from thefuzz import fuzz
            self.fuzz = fuzz
        except ImportError:
            logger.warning("thefuzz not installed. Falling back to exact matching.")
            self.fuzz = None

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
        mubi_runtime: Optional[int] = None,
        mubi_genres: Optional[list] = None,
        mubi_id: Optional[int] = None
    ) -> ExternalMetadataResult:
        """
        Fetch IMDB ID and TMDB ID from TMDB using Tri-Vector Verification Protocol.
        """
        
        # Note: We ignore the provided tmdb_id as per new requirements to always verify
        
        mubi_data = {
            "title": title,
            "original_title": original_title,
            "year": year,
            "directors": mubi_directors or [],
            "duration": mubi_runtime,
            "media_type": media_type
        }
        
        return self._find_match_three_phase(mubi_data, mubi_id)

    def _find_match_three_phase(self, mubi_data: dict, mubi_id: Optional[int] = None) -> ExternalMetadataResult:
        """
        Implementation of the Tri-Vector Verification Protocol.
        Phase I: Candidate Retrieval (Search)
        Phase II: Verification Funnel (Logic)
        """

        
        log_prefix = f"[MubiID:{mubi_id}] " if mubi_id else ""
        media_type = mubi_data.get("media_type", "movie")
        
        # --- Phase I: Candidate Retrieval ---
        candidates = []
        
        # Strategy A: Search Original Title (High Precision)
        if mubi_data.get("original_title"):
            logger.debug(f"{log_prefix}Searching by Original Title: {mubi_data['original_title']}")
            candidates = self._search_api(mubi_data["original_title"], media_type)
            
        # Strategy B: Search Title (High Recall) - if A failed or returned nothing
        if not candidates and mubi_data.get("title") != mubi_data.get("original_title"):
            logger.debug(f"{log_prefix}Searching by Title: {mubi_data['title']}")
            candidates = self._search_api(mubi_data["title"], media_type)
            
        if not candidates:
             return ExternalMetadataResult(
                success=False,
                source_provider=self.provider_name,
                error_message="No candidates found"
            )

        # --- Phase II: Verification Funnel ---
        scored_candidates = []
        
        for candidate in candidates:
             # 1. Temporal Filtering
             tmdb_date = candidate.get("release_date") if media_type == "movie" else candidate.get("first_air_date")
             tmdb_year = self._extract_year(tmdb_date)
             
             if not tmdb_year or not mubi_data.get("year"):
                 # If dates are missing, be permissive but penalize later? 
                 pass
             elif tmdb_year and mubi_data.get("year"):
                 # If both exist, enforce window.
                 delta = abs(tmdb_year - mubi_data["year"])
                 # Allow +/- 2 years generally, +/- 3 for obscure (we don't know popularity yet easily, defaulting to 3 for safety)
                 if delta > 3:
                     continue
             
             # 2. Title Relevance Pre-Sort (Optimization)
             # We need to pick top candidates for deep verification
             # Use max of title or original title match
             title_score = 0
             if self.fuzz:
                 s1 = self.fuzz.token_set_ratio(mubi_data["title"], candidate.get("title", ""))
                 s2 = self.fuzz.token_set_ratio(mubi_data.get("original_title", ""), candidate.get("original_title", "")) if media_type == "movie" else 0
                 title_score = max(s1, s2)
             else:
                 title_score = 100 if mubi_data["title"] == candidate.get("title") else 0
                 
             scored_candidates.append({
                 "candidate": candidate,
                 "pre_score": title_score,
                 "tmdb_year": tmdb_year
             })
             
        # Sort by pre-score and take top 3
        scored_candidates.sort(key=lambda x: x["pre_score"], reverse=True)
        top_candidates = scored_candidates[:3]
        
        best_match = None
        highest_confidence = 0
        
        for item in top_candidates:
            candidate = item["candidate"]
            tmdb_id = candidate["id"]
            
            # Deep Verification: Fetch Details + Credits
            details = self._get_details_with_credits(tmdb_id, media_type)
            if not details:
                continue
                
            confidence_score = self._calculate_final_score(mubi_data, details, item["tmdb_year"])
            
            logger.debug(f"{log_prefix}Candidate {tmdb_id} ('{candidate.get('title')}'): Score={confidence_score}")
            
            if confidence_score > highest_confidence:
                highest_confidence = confidence_score
                best_match = details

        # --- Fallback Strategy ---
        if highest_confidence < 80 and mubi_data.get("year"):
            # If confidence is low, try specific year searches (year, year+1, year-1)
            # This handles cases like "About Love" where generic search fails
            logger.debug(f"{log_prefix}Low confidence ({highest_confidence}). Attempting fallback year searches...")
            base_year = mubi_data["year"]
            fallback_years = [base_year, base_year + 1, base_year - 1]
            fallback_candidates = []
            
            seen_ids = {c["id"] for c in candidates}
            
            for fy in fallback_years:
                q = mubi_data.get("original_title") or mubi_data.get("title")
                results = self._search_api(q, media_type, year=fy, include_adult=True)
                for r in results:
                    if r["id"] not in seen_ids:
                        fallback_candidates.append(r)
                        seen_ids.add(r["id"])
                        
            if fallback_candidates:
                # Re-run verification on new candidates
                # Filter first (temporal filter +/- 3 years)
                valid_fallback = []
                for item in fallback_candidates:
                    tmdb_date = item.get("release_date") if media_type == "movie" else item.get("first_air_date")
                    t_year = self._extract_year(tmdb_date)
                    if t_year and abs(t_year - base_year) <= 3:
                        valid_fallback.append(item)
                        
                if valid_fallback:
                    fb_best, fb_score = self._verify_candidates(mubi_data, valid_fallback, tmdb_media_type="movie" if media_type == "movie" else "tv")
                    if fb_score > highest_confidence:
                        logger.info(f"{log_prefix}Fallback search improved score from {highest_confidence} to {fb_score}")
                        best_match = fb_best
                        highest_confidence = fb_score

        # --- Decision ---
        # "If not certain, then do not match anything" -> Threshold 80
        if highest_confidence >= 80 and best_match:
            logger.info(f"{log_prefix}MATCH FOUND: TMDB ID {best_match['id']} (Score: {highest_confidence})")
            
            # Format result
            external_ids = best_match.get("external_ids", {})
            tmdb_crew = best_match.get("credits", {}).get("crew", [])
            tmdb_directors = [p["name"] for p in tmdb_crew if p.get("job") == "Director"]
            
            return ExternalMetadataResult(
                success=True,
                tmdb_id=str(best_match["id"]),
                imdb_id=external_ids.get("imdb_id"),
                imdb_url=f"https://www.imdb.com/title/{external_ids.get('imdb_id')}/" if external_ids.get("imdb_id") else None,
                source_provider=self.provider_name,
                vote_average=best_match.get("vote_average"),
                vote_count=best_match.get("vote_count"),
                # Verification Data
                matched_title=best_match.get("title"),
                matched_original_title=best_match.get("original_title"),
                matched_year=self._extract_year(best_match.get("release_date") if media_type == "movie" else best_match.get("first_air_date")),
                matched_directors=tmdb_directors,
                match_score=highest_confidence,
                match_details={
                    "year_delta": abs(int(best_match.get("release_date", "").split("-")[0]) - mubi_data["year"]) if mubi_data.get("year") and best_match.get("release_date") else None,
                    # We could add more details here if needed by the evaluator script
                }
            )
        else:
            logger.info(f"{log_prefix}No match met threshold (Best: {highest_confidence}). Returning None.")
            return ExternalMetadataResult(
                success=False,
                source_provider=self.provider_name,
                error_message="No match met confidence threshold"
            )



    def _get_details_with_credits(self, tmdb_id: int, media_type: str) -> dict:
        """Fetch details with append_to_response=credits,external_ids."""
        url = f"{self.BASE_URL}/{media_type}/{tmdb_id}"
        params = {
            "api_key": self.api_key,
            "append_to_response": "credits,external_ids"
        }
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.ok:
                return response.json()
        except Exception as e:
            logger.warning(f"Failed to fetch details for {tmdb_id}: {e}")
        return {}
        
    def _verify_candidates(self, mubi_data: dict, candidates: list, tmdb_media_type: str) -> tuple[Optional[dict], int]:
        """Helper to run deep verification on a list of candidates."""
        best_match = None
        highest_confidence = 0
        
        # Limit to top 5 purely by relevance to save API calls? 
        # Or should we trust the caller has filtered?
        # Caller (search phase) filters 20 results. 
        # But for fallback, we might have many. Let's process all provided.
        
        for item in candidates:
             # Fetch full details
            details = self._get_details_with_credits(item["id"], media_type=tmdb_media_type) # Changed from _get_details
            if not details: continue
            
            tmdb_year = self._extract_year(item.get("release_date") if tmdb_media_type == "movie" else item.get("first_air_date"))
            confidence_score = self._calculate_final_score(mubi_data, details, tmdb_year)
            
            # logger.debug(f"Candidate {item['id']} ('{item.get('title')}'): Score={confidence_score}")
            
            if confidence_score > highest_confidence:
                highest_confidence = confidence_score
                best_match = details
                
        return best_match, highest_confidence

    def _search_api(self, query: str, media_type: str, year: Optional[int] = None, include_adult: bool = True) -> list:
        """Internal wrapper for search API to handle year filtering."""
        endpoint = "search/movie" if media_type == "movie" else "search/tv"
        params = {
            "api_key": self.api_key,
            "query": query,
            "include_adult": str(include_adult).lower(),
            "language": "en-US",
            "page": 1
        }
        if year:
             params["year"] = year # strict primary release year filter for movies
             # For TV it is first_air_date_year
             if media_type != "movie":
                 del params["year"]
                 params["first_air_date_year"] = year

        url = f"{self.BASE_URL}/{endpoint}"
        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            return resp.json().get("results", [])
        except Exception as e:
            logger.error(f"Search API error: {e}")
            return []

    def _calculate_final_score(self, mubi_data: dict, tmdb_details: dict, tmdb_year: Optional[int]) -> int:
        """Calculate the confidence score based on the Tri-Vector weights."""
        score = 0
        
        # Guard: If fuzzy matching is not available, we can't reliably score directors or titles
        # Return 0 or handle gracefully? For now, assume 0 for fuzzy parts.
        if not self.fuzz:
            logger.warning("Fuzzy matching disabled (thefuzz missing). Cannot verify director/title.")
            # We can still do year matches
            if mubi_data.get("year") and tmdb_year and mubi_data["year"] == tmdb_year:
                return 10
            return 0

        # 1. Director Match (+50) - The "Fingerprint"
        mubi_directors = [d.lower() for d in mubi_data.get("directors", [])]
        tmdb_crew = tmdb_details.get("credits", {}).get("crew", [])
        tmdb_directors = [p["name"].lower() for p in tmdb_crew if p.get("job") == "Director"]
        
        director_match = False
        if mubi_directors and tmdb_directors:
            for md in mubi_directors:
                for td in tmdb_directors:
                    if self.fuzz.WRatio(md, td) > 85:
                        director_match = True
                        break
                if director_match: break
        
        if director_match:
            score += 50
        elif mubi_directors and tmdb_directors:
            score -= 20
            
        # 2. Title Match (+30)
        t_score = self.fuzz.token_set_ratio(mubi_data["title"], tmdb_details.get("title", ""))
        ot_score = self.fuzz.token_set_ratio(mubi_data.get("original_title", ""), tmdb_details.get("original_title", ""))
        max_title_score = max(t_score, ot_score)
        
        if max_title_score > 90:
            score += 30
            
        # 3. Year Exact Match (+10)
        if mubi_data.get("year") and tmdb_year:
            if mubi_data["year"] == tmdb_year:
                score += 10
        
        # 4. Runtime Match (+10)
        mubi_dur = mubi_data.get("duration")
        tmdb_dur = tmdb_details.get("runtime")
        if mubi_dur and tmdb_dur:
            diff = abs(mubi_dur - tmdb_dur)
            if diff <= 10:
                score += 10
            elif diff > 40:
                score -= 30
                
        return score

    def _extract_year(self, date_str: Optional[str]) -> Optional[int]:
        if not date_str: return None
        try:
            return int(date_str.split("-")[0])
        except (ValueError, IndexError):
            return None

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
            
    def _fetch_genres(self, media_type: str) -> Dict[int, str]:
        """
        Fetch genre mapping from TMDB API to avoid hardcoded IDs.
        Returns: Dict {id: name}
        """
        try:
            url = f"{self.BASE_URL}/genre/{media_type}/list"
            params = {"api_key": self.api_key}
            response = requests.get(url, params=params, timeout=10)
            if response.ok:
                data = response.json()
                return {g["id"]: g["name"].lower() for g in data.get("genres", [])}
        except Exception as e:
            logger.warning(f"Failed to fetch {media_type} genres: {e}")
        return {}

