from __future__ import annotations

import logging
from typing import Any, Dict, Optional
import requests
import unicodedata

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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
        
        # Initialize Session with Retry logic
        self.session = requests.Session()
        retries = Retry(
            total=self.config.get("max_retries", 3),
            backoff_factor=self.config.get("backoff_factor", 1.0),
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount('https://', adapter)
        self.session.mount('http://', adapter)
        
        self.title_normalizer = TitleNormalizer()
        # RetryStrategy class unused for session-based approach, but keeping for compatibility if other methods use it
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
        Implementation of the Tri-Vector Verification Protocol (Sequential).
        Executes search strategies in order of precision.
        """
        log_prefix = f"[MubiID:{mubi_id}] " if mubi_id else ""
        media_type = mubi_data.get("media_type", "movie")
        
        # --- Strategy A: Original Title (High Precision) ---
        if mubi_data.get("original_title"):
            logger.debug(f"{log_prefix}Strategy A: Original Title '{mubi_data['original_title']}'")
            candidates = self._search_api(mubi_data["original_title"], media_type)
            if candidates:
                best_match, confidence = self._verify_candidates(mubi_data, candidates, media_type)
                if best_match and confidence >= 80:
                    logger.info(f"{log_prefix}MATCH FOUND (Strategy A): TMDB ID {best_match['id']} (Score: {confidence})")
                    return self._build_result(best_match, confidence, mubi_data, media_type)

        # --- Strategy B: English Title + Year (High Precision filter) ---
        # Filters out generic titles from wrong eras immediately
        if mubi_data.get("title") and mubi_data.get("year"):
            logger.debug(f"{log_prefix}Strategy B: Title '{mubi_data['title']}' + Year {mubi_data['year']}")
            # Note: _search_api with year uses strict filtering
            candidates = self._search_api(mubi_data["title"], media_type, year=mubi_data["year"])
            if candidates:
                best_match, confidence = self._verify_candidates(mubi_data, candidates, media_type)
                if best_match and confidence >= 80:
                    logger.info(f"{log_prefix}MATCH FOUND (Strategy B): TMDB ID {best_match['id']} (Score: {confidence})")
                    return self._build_result(best_match, confidence, mubi_data, media_type)

        # --- Strategy C: English Title (Wide Net) ---
        # Only needed if A failed and B failed (e.g. year mismatch > 1 year)
        # Avoid running if Title == Original Title (covered by A)
        english_title = mubi_data.get("title")
        original_title = mubi_data.get("original_title")
        should_run_wide = True
        if original_title and english_title and original_title.lower() == english_title.lower():
             should_run_wide = False
             
        if should_run_wide and english_title:
            logger.debug(f"{log_prefix}Strategy C: Title '{english_title}' (Wide)")
            # No year filter here
            candidates = self._search_api(english_title, media_type)
            if candidates:
                best_match, confidence = self._verify_candidates(mubi_data, candidates, media_type)
                if best_match and confidence >= 80:
                    logger.info(f"{log_prefix}MATCH FOUND (Strategy C): TMDB ID {best_match['id']} (Score: {confidence})")
                    return self._build_result(best_match, confidence, mubi_data, media_type)
                    
        # --- Strategy F: Split Search (Title : Subtitle) ---
        # Handles "Title: Subtitle" or "Title - Subtitle"
        # Search for the core title part with year
        separators = [":", " - ", " – ", "(", "["]
        candidates_queries = set()
        for t in [mubi_data.get("title"), mubi_data.get("original_title")]:
            if not t: continue
            for sep in separators:
                if sep in t:
                    part = t.split(sep)[0].strip()
                    if len(part) > 2: # Avoid tiny fragments
                        candidates_queries.add(part)
        
        if candidates_queries:
            logger.debug(f"{log_prefix}Strategy F: Split Title Search {candidates_queries}")
            for q in candidates_queries:
                # Try with Year (Precision)
                # Note: We prioritize precision here. If we searched wide, it might match random things.
                # But since we verify, it's safer.
                results = self._search_api(q, media_type, year=mubi_data.get("year"))
                if results:
                    best_match, confidence = self._verify_candidates(mubi_data, results, media_type)
                    if best_match and confidence >= 80:
                        logger.info(f"{log_prefix}MATCH FOUND (Strategy F - Split): TMDB ID {best_match['id']} (Score: {confidence})")
                        return self._build_result(best_match, confidence, mubi_data, media_type)

        # --- Strategy D: Fallback Neighbor Years ---
        if mubi_data.get("year"):
            logger.debug(f"{log_prefix}Strategy D: Fallback Neighbor Years")
            base_year = mubi_data["year"]
            # B covered base_year. Try neighbors.
            fallback_years = [base_year + 1, base_year - 1]
            query = mubi_data.get("original_title") or mubi_data.get("title")
            
            fallback_candidates = []
            for fy in fallback_years:
                results = self._search_api(query, media_type, year=fy)
                fallback_candidates.extend(results)
                
            if fallback_candidates:
                 best_match, confidence = self._verify_candidates(mubi_data, fallback_candidates, media_type)
                 if best_match and confidence >= 80:
                    logger.info(f"{log_prefix}MATCH FOUND (Strategy D): TMDB ID {best_match['id']} (Score: {confidence})")
                    return self._build_result(best_match, confidence, mubi_data, media_type)

        # --- Strategy E: Cross-Media Fallback (TV Check) ---
        # If movie search failed completely, check if it's actually a TV show (Miniseries/TV Movie)
        if media_type == "movie":
             logger.debug(f"{log_prefix}Strategy E: Cross-Media Fallback (TV Check)")
             q = mubi_data.get("original_title") or mubi_data.get("title")
             # Try simple search without year first to allow flexibility (miniseries often span years)
             tv_results = self._search_api(q, media_type="tv")
             
             if tv_results:
                 best_tv, tv_score = self._verify_candidates(mubi_data, tv_results, tmdb_media_type="tv")
                 if best_tv and tv_score >= 80:
                     logger.info(f"{log_prefix}MATCH FOUND (Strategy E - TV Fallback): TMDB ID {best_tv['id']} (Score: {tv_score})")
                     return self._build_result(best_tv, tv_score, mubi_data, media_type="tv")

        logger.info(f"{log_prefix}No match met threshold after all strategies.")
        return ExternalMetadataResult(
            success=False,
            source_provider=self.provider_name,
            error_message="No match met confidence threshold"
        )

    def _build_result(self, best_match: dict, confidence: int, mubi_data: dict, media_type: str) -> ExternalMetadataResult:
        """Helper to construct ExternalMetadataResult."""
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
            matched_title=best_match.get("title") or best_match.get("name"),
            matched_original_title=best_match.get("original_title") or best_match.get("original_name"),
            matched_year=self._extract_year(best_match.get("release_date") if media_type == "movie" else best_match.get("first_air_date")),
            matched_directors=tmdb_directors,
            match_score=confidence,
            match_details={
                "year_delta": abs(int(best_match.get("release_date", "0000").split("-")[0]) - mubi_data["year"]) if mubi_data.get("year") and best_match.get("release_date") else None,
                "strategy": "sequential"
            }
        )

    def _verify_candidates(self, mubi_data: dict, candidates: list, tmdb_media_type: str) -> tuple[Optional[dict], int]:
        """Helper to run deep verification on a list of candidates."""
        best_match = None
        highest_confidence = 0
        
        target_year = mubi_data.get("year")
        
        for item in candidates:
            # Phase II: Temporal Pre-Filtering
            if target_year:
                cand_year = self._extract_year(item.get("release_date") if tmdb_media_type == "movie" else item.get("first_air_date"))
                if cand_year:
                    year_delta = abs(cand_year - target_year)
                    # Allow up to 3 years delta, UNLESS title is an exact match (handle Remasters/Re-releases)
                    is_exact_title = (item.get("title", "").lower().strip() == mubi_data.get("title", "").lower().strip())
                    
                    if year_delta > 3 and not is_exact_title:
                         continue

             # Fetch full details
            details = self._get_details_with_credits(item["id"], media_type=tmdb_media_type)
            if not details: continue
            
            tmdb_year = self._extract_year(item.get("release_date") if tmdb_media_type == "movie" else item.get("first_air_date"))
            confidence_score = self._calculate_final_score(mubi_data, details, tmdb_year)
            
            if confidence_score > highest_confidence:
                highest_confidence = confidence_score
                best_match = details
                
        return best_match, highest_confidence

    def _calculate_final_score(self, mubi_data: dict, tmdb_details: dict, tmdb_year: Optional[int]) -> int:
        """Calculate the confidence score based on the Tri-Vector weights."""
        score = 0
        
        if not self.fuzz:
            logger.warning("Fuzzy matching disabled (thefuzz missing). Cannot verify director/title.")
            if mubi_data.get("year") and tmdb_year and mubi_data["year"] == tmdb_year:
                return 10
            return 0

        # 1. Director Match (+50)
        mubi_directors = [d.lower() for d in mubi_data.get("directors", [])]
        tmdb_crew = tmdb_details.get("credits", {}).get("crew", [])
        tmdb_directors = [p["name"].lower() for p in tmdb_crew if p.get("job") == "Director"]
        
        # 2. Title Match (+30)
        mubi_title = mubi_data.get("title", "")
        mubi_ot = mubi_data.get("original_title", "")
        
        tmdb_title = tmdb_details.get("title") or tmdb_details.get("name") or ""
        tmdb_ot = tmdb_details.get("original_title") or tmdb_details.get("original_name") or ""
        
        tmdb_titles = {tmdb_title, tmdb_ot}
        
        alts_data = tmdb_details.get("alternative_titles", {})
        alternatives = alts_data.get("titles", []) + alts_data.get("results", [])
        
        for alt in alternatives:
            if alt.get("title"):
                tmdb_titles.add(alt["title"])
        
        max_title_score = 0
        
        mubi_title_norm = self._normalize_string(mubi_title)
        mubi_ot_norm = self._normalize_string(mubi_ot)
        
        for t_tmdb in tmdb_titles:
            s1 = self.fuzz.token_set_ratio(mubi_title, t_tmdb)
            s2 = self.fuzz.token_set_ratio(mubi_ot, t_tmdb)
            
            t_tmdb_norm = self._normalize_string(t_tmdb)
            s3 = self.fuzz.token_set_ratio(mubi_title_norm, t_tmdb_norm)
            s4 = self.fuzz.token_set_ratio(mubi_ot_norm, t_tmdb_norm)
            
            max_title_score = max(max_title_score, s1, s2, s3, s4)
        
        # Director Matching
        director_match = False
        if mubi_directors and tmdb_directors:
            mubi_directors_norm = [self._normalize_string(d) for d in mubi_data.get("directors", [])]
            tmdb_directors_norm = [self._normalize_string(p["name"]) for p in tmdb_crew if p.get("job") == "Director"]
            
            for md in mubi_directors_norm:
                for td in tmdb_directors_norm:
                    if self.fuzz.WRatio(md, td) >= 85:
                        director_match = True
                        break
                if director_match: break
            
            if not director_match:
                for md in mubi_directors_norm:
                    parts = md.split()
                    if len(parts) > 1:
                        md_reversed = f"{parts[-1]} {' '.join(parts[:-1])}"
                        for td in tmdb_directors_norm:
                             if self.fuzz.WRatio(md_reversed, td) >= 85:
                                director_match = True
                                break
                             
                             stopwords = {"brothers", "bros", "sisters", "the", "and", "&"}
                             md_tokens = {t for t in set(md.split()) if t not in stopwords}
                             td_tokens = {t for t in set(td.split()) if t not in stopwords}
                             
                             if not md_tokens or not td_tokens:
                                 md_tokens = set(md.split())
                                 td_tokens = set(td.split())
                             
                             common = len(md_tokens & td_tokens)
                             total = min(len(md_tokens), len(td_tokens))
                             threshold = 0.5 if max_title_score > 80 else 0.51
                             matched_tokens = md_tokens & td_tokens
                             valid_overlap = any(len(t) > 3 for t in matched_tokens)
                             
                             if total > 0 and (common / total) >= threshold and valid_overlap:
                                 director_match = True
                                 break
                                      
                    if director_match: break

            if not director_match and max_title_score > 90:
                for md in mubi_directors_norm:
                    for td in tmdb_directors_norm:
                        md_last = md.split()[-1] if md.strip() else ""
                        td_last = td.split()[-1] if td.strip() else ""
                        if md_last and td_last and md_last == td_last and len(md_last) > 2:
                            director_match = True
                            break
                    if director_match: break

        if director_match:
            score += 50
        elif mubi_directors and tmdb_directors:
            score -= 20
            
        if max_title_score > 90:
            score += 30
            
        # 3. Year Exact Match (+10)
        if mubi_data.get("year") and tmdb_year:
            year_delta = abs(mubi_data["year"] - tmdb_year)
            if year_delta == 0:
                score += 10
            elif year_delta == 1:
                score += 5
        
        # 4. Runtime Match (+10)
        mubi_dur = mubi_data.get("duration")
        tmdb_dur = tmdb_details.get("runtime")
        if mubi_dur and tmdb_dur:
            diff = abs(mubi_dur - tmdb_dur)
            if diff <= 10:
                score += 10
            elif diff > 40:
                if director_match and max_title_score > 90:
                    score -= 10 
                else:
                    score -= 30
                
        return score

    def _search_api(self, query: str, media_type: str, year: Optional[int] = None, include_adult: bool = True) -> list:
        """Internal wrapper for search API to handle year filtering."""
        # Sanitize query: TMDB search fails with underscores (e.g. "Hoax_canular")
        sanitized_query = query.replace("_", " ")
        
        endpoint = "search/movie" if media_type == "movie" else "search/tv"
        params = {
            "api_key": self.api_key,
            "query": sanitized_query,
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
            resp = self.session.get(url, params=params, timeout=10)
            resp.raise_for_status()
            return resp.json().get("results", [])
        except Exception as e:
            logger.error(f"Search API error: {e}")
            return []

    def _get_details_with_credits(self, tmdb_id: int, media_type: str) -> dict:
        """Fetch details with append_to_response=credits,external_ids."""
        url = f"{self.BASE_URL}/{media_type}/{tmdb_id}"
        params = {
            "api_key": self.api_key,
            "append_to_response": "credits,external_ids,alternative_titles"
        }
        try:
            response = self.session.get(url, params=params, timeout=10)
            if response.ok:
                return response.json()
        except Exception as e:
            logger.warning(f"Failed to fetch details for {tmdb_id}: {e}")
        return {}

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

    def _normalize_string(self, s: Optional[str]) -> str:
        """Normalize string to ASCII, removing accents and lowering case. Replaces hyphens with spaces."""
        if not s:
            return ""
        s = unicodedata.normalize('NFD', s)
        # Keep alphanumeric, but replace hyphen with space to split tokens
        return "".join(c if c.isalnum() else ' ' for c in s if unicodedata.category(c) != 'Mn').lower()
