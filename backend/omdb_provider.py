from __future__ import annotations

import logging
import itertools
import threading
from typing import Any, Dict, Optional, List, Union
import requests

from .metadata_utils import ExternalMetadataResult, RetryStrategy

# Configure logging
logger = logging.getLogger(__name__)

class OMDBProvider:
    """
    OMDB metadata provider.
    Used primarily for fetching ratings (IMDB, Metacritic, Rotten Tomatoes)
    using an existing IMDB ID.
    Supports API key rotation.
    """
    
    BASE_URL = "http://www.omdbapi.com/"
    
    def __init__(self, api_keys: Union[str, List[str]]) -> None:
        """
        Initialize OMDB provider with one or more API keys.
        api_keys: Single string key or list of string keys.
        """
        if isinstance(api_keys, str):
            self.api_keys = [api_keys]
        else:
            self.api_keys = [k for k in api_keys if k] # Filter empty strings
            
        if not self.api_keys:
            raise ValueError("At least one OMDB API key must be provided.")
            
        self._key_cycle = itertools.cycle(self.api_keys)
        self._bad_keys = set()
        self._lock = threading.Lock()
        
        self.retry_strategy = RetryStrategy(
            max_retries=3,
            initial_backoff=1.0,
            multiplier=1.5,
        )
        
    @property
    def provider_name(self) -> str:
        return "OMDB"
        
    def _get_next_key(self) -> str:
        with self._lock:
            # Try to find a non-bad key
            # We iterate at most len(api_keys) * 2 to prevent infinite loop if all bad
            for _ in range(len(self.api_keys) * 2):
                k = next(self._key_cycle)
                if k not in self._bad_keys:
                    return k
            # If all are bad, just return the last one (it will likely fail again, but we can't do magic)
            return k
            
    def _mark_key_bad(self, key: str):
        with self._lock:
            self._bad_keys.add(key)
    
    def get_details(self, imdb_id: str) -> ExternalMetadataResult:
        """
        Fetch details from OMDB using IMDB ID.
        Retries with valid keys if a 401 Invalid Key error occurs.
        """
        
        # We allow trying up to the number of keys we have + 1 (for good measure)
        # to ensure we cycle through all potential candidates if needed.
        max_attempts = len(self.api_keys) + 1
        
        last_error = None
        
        for attempt in range(max_attempts):
            current_key = self._get_next_key()
            
            params = {
                "apikey": current_key,
                "i": imdb_id,
                "plot": "short",
                "r": "json"
            }
            
            try:
                response = requests.get(self.BASE_URL, params=params, timeout=10)
                
                # Check directly for 401 (Invalid Key)
                if response.status_code == 401:
                    logger.warning(f"OMDB: Key ending in ...{current_key[-4:]} failed (401 Unauthorized). Marking as bad.")
                    self._mark_key_bad(current_key)
                    last_error = "401 Unauthorized (All keys invalid?)"
                    continue # Retry loop will get a new key
                
                response.raise_for_status()
                data = response.json()
                
                if data.get("Response") != "True":
                    error_msg = data.get("Error", "Unknown error")
                    # Some OMDB errors (like "Request limit reached!") might simpler be handled by rotation too?
                    # But "Movie not found" should NOT rotate.
                    if "limit" in error_msg.lower():
                        logger.warning(f"OMDB: Limit reached for key ending in ...{current_key[-4:]}. Removing from rotation.")
                        self._mark_key_bad(current_key)
                        continue
                        
                    return ExternalMetadataResult(
                        success=False, 
                        source_provider=self.provider_name,
                        error_message=error_msg
                    )
                 
                # Success - Parse Data
                return self._parse_response(data, imdb_id)

            except requests.RequestException as e:
                logger.warning(f"OMDB: Network error with key ...{current_key[-4:]}: {e}")
                last_error = str(e)
                # For network errors, we might want to just retry (maybe same key, maybe next).
                # Continuing loop rotates key, which is fine.
                continue
                
        # If we exit loop, we failed
        return ExternalMetadataResult(
            success=False,
            source_provider=self.provider_name,
            error_message=f"Exhausted all API keys. Last error: {last_error}"
        )

    def _parse_response(self, data: Dict[str, Any], imdb_id: str) -> ExternalMetadataResult:
        """Helper to parse valid OMDB JSON response."""
        ratings_data = [] 
        
        def parse_votes(v_str):
            try:
                return int(v_str.replace(",", ""))
            except (ValueError, AttributeError):
                return 0

        # 1. IMDB Rating
        if data.get("imdbRating") and data.get("imdbRating") != "N/A":
            try:
                score = float(data["imdbRating"])
                votes = parse_votes(data.get("imdbVotes", "0"))
                ratings_data.append({
                    "source": "imdb",
                    "score_over_10": score,
                    "voters": votes
                })
            except ValueError:
                pass
        
        # 2. Other Ratings
        for r in data.get("Ratings", []):
            source_name = r.get("Source")
            value = r.get("Value")
            
            if source_name == "Internet Movie Database":
                continue 
            
            elif source_name == "Rotten Tomatoes":
                try:
                    percentage = int(value.replace("%", ""))
                    score = percentage / 10.0
                    ratings_data.append({
                        "source": "rotten_tomatoes",
                        "score_over_10": score,
                        "voters": 0
                    })
                except ValueError:
                    pass
                    
            elif source_name == "Metacritic":
                try:
                    raw_score = int(value.split("/")[0])
                    score = raw_score / 10.0
                    ratings_data.append({
                        "source": "metacritic",
                        "score_over_10": score,
                        "voters": 0
                    })
                except (ValueError, IndexError):
                    pass

        result = ExternalMetadataResult(
            success=True,
            source_provider=self.provider_name,
            imdb_id=imdb_id
        )
        result.extra_ratings = ratings_data
        return result

    def test_connection(self) -> bool:
        """Test connection (using a known ID)."""
        res = self.get_details("tt0111161") # Shawshank Redemption
        return res.success

    def get_failed_keys(self) -> List[str]:
        """Return a list of keys that failed with 401."""
        with self._lock:
            return list(self._bad_keys)
