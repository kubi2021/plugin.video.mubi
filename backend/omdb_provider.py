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
            return next(self._key_cycle)
    
    def get_details(self, imdb_id: str) -> ExternalMetadataResult:
        """
        Fetch details from OMDB using IMDB ID.
        """
        current_key = self._get_next_key()
        
        params = {
            "apikey": current_key,
            "i": imdb_id,
            "plot": "short", # We only need ratings, shorten payload
            "r": "json"
        }
        
        def do_request() -> ExternalMetadataResult:
            response = requests.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("Response") != "True":
                error_msg = data.get("Error", "Unknown error")
                return ExternalMetadataResult(
                    success=False, 
                    source_provider=self.provider_name,
                    error_message=error_msg
                )
             
            # Extract Ratings
            ratings_data = [] # List of dicts {source, score, voters}
            
            # Helper to parse votes string "139,037" -> 139037
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
            
            # 2. Other Ratings (RT, Metacritic)
            for r in data.get("Ratings", []):
                source_name = r.get("Source")
                value = r.get("Value")
                
                if source_name == "Internet Movie Database":
                    continue # Already handled via top-level fields which are more reliable (votes)
                
                elif source_name == "Rotten Tomatoes":
                    # Format: "73%"
                    try:
                        percentage = int(value.replace("%", ""))
                        score = percentage / 10.0 # Scale to 10
                        ratings_data.append({
                            "source": "rotten_tomatoes",
                            "score_over_10": score,
                            "voters": 0 # RT doesn't provide voter count in this API
                        })
                    except ValueError:
                        pass
                        
                elif source_name == "Metacritic":
                    # Format: "64/100"
                    try:
                        raw_score = int(value.split("/")[0])
                        score = raw_score / 10.0 # Scale to 10
                        ratings_data.append({
                            "source": "metacritic",
                            "score_over_10": score,
                            "voters": 0 # Metascore doesn't provide voter count
                        })
                    except (ValueError, IndexError):
                        pass

            # We reuse ExternalMetadataResult but attach our ratings list
            # Since ExternalMetadataResult is a dataclass, we can't easily attach arbitrary fields 
            # unless it supports it. Let's check metadata_utils.py or just return a dict/custom object?
            # Looking at tmdb_provider, it returns ExternalMetadataResult.
            # I should inspect metadata_utils.py to see if I can add a 'ratings' field or if I should just return the result
            # and let the caller handle it.
            # For now, I will store these in a dynamic attribute or modify ExternalMetadataResult later.
            # actually, let's just make this method return the list of ratings directly or a dict.
            # The interface implies returning ExternalMetadataResult.
            
            result = ExternalMetadataResult(
                success=True,
                source_provider=self.provider_name,
                imdb_id=imdb_id
            )
            # Monkey-patch info for now, clearer than modifying the class just for this if not needed elsewhere
            result.extra_ratings = ratings_data
            return result

        try:
            return self.retry_strategy.execute(do_request, imdb_id)
        except Exception as e:
            logger.error(f"OMDB: Request failed for {imdb_id}: {e}")
            return ExternalMetadataResult(
                success=False,
                source_provider=self.provider_name,
                error_message=str(e)
            )

    def test_connection(self) -> bool:
        """Test connection (using a known ID)."""
        res = self.get_details("tt0111161") # Shawshank Redemption
        return res.success
