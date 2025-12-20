from __future__ import annotations

import re
import time
import logging
from typing import Callable, List, Optional, Any
from dataclasses import dataclass
import requests

# Configure logging
logger = logging.getLogger(__name__)

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
    # Rating data from provider
    vote_average: Optional[float] = None
    vote_count: Optional[int] = None

class TitleNormalizer:
    """Utilities for normalizing titles and generating spelling variants."""

    WORD_VARIATIONS = {
        # Spelling variations (British vs. American)
        "color": "colour",
        "colour": "color",
        "theater": "theatre",
        "theatre": "theater",
        "honor": "honour",
        "honour": "honor",
        "realize": "realise",
        "realise": "realize",
        "organize": "organise",
        "organise": "organize",
        "analyze": "analyse",
        "analyse": "analyze",
        "apologize": "apologise",
        "apologise": "apologize",
        "center": "centre",
        "centre": "center",
        "meter": "metre",
        "metre": "meter",
        "defense": "defence",
        "defence": "defense",
        "offense": "offence",
        "offence": "offense",
        "travelling": "traveling",
        "traveling": "travelling",
        "jewelry": "jewellery",
        "jewellery": "jewelry",
        "catalog": "catalogue",
        "catalogue": "catalog",
        "dialog": "dialogue",
        "dialogue": "dialog",
        "practice": "practise",
        "practise": "practice",
        "license": "licence",
        "licence": "license",
        "check": "cheque",
        "cheque": "check",
        # Regional terminology differences
        "elevator": "lift",
        "lift": "elevator",
        "truck": "lorry",
        "lorry": "truck",
        "apartment": "flat",
        "flat": "apartment",
        "cookie": "biscuit",
        "biscuit": "cookie",
        "soccer": "football",
        "football": "soccer",
        "fall": "autumn",
        "autumn": "fall",
        "diaper": "nappy",
        "nappy": "diaper",
        "flashlight": "torch",
        "torch": "flashlight",
        "garbage": "rubbish",
        "rubbish": "garbage",
        "sneakers": "trainers",
        "trainers": "sneakers",
        "vacation": "holiday",
        "holiday": "vacation",
        "hood": "bonnet",
        "bonnet": "hood",
        "trunk": "boot",
        "boot": "trunk",
        "mail": "post",
        "post": "mail",
        "zip code": "postcode",
        "postcode": "zip code",
    }

    def normalize_title(self, title: str) -> str:
        """Remove conjunctions like 'and'/'&' and collapse whitespace."""
        title = re.sub(r"\b(and|&)\b", "", title, flags=re.IGNORECASE)
        title = re.sub(r"\s+", " ", title).strip()
        return title

    def generate_alternative_spellings(self, title: str) -> List[str]:
        """Generate titles replacing known word variations."""
        alternatives: List[str] = []
        lower_title = title.lower()
        for word, replacement in self.WORD_VARIATIONS.items():
            if word in lower_title:
                # Use regex for case-insensitive replacement while preserving case of match
                pattern = re.compile(re.escape(word), re.IGNORECASE)
                
                def replace_case_match(match):
                    g = match.group()
                    if g.isupper():
                        return replacement.upper()
                    if g.istitle():
                        return replacement.capitalize()
                    return replacement

                new_title = pattern.sub(replace_case_match, title)
                
                # Verify we actually changed something and it's not effectively same
                if new_title.lower() != title.lower() and new_title not in alternatives:
                    alternatives.append(new_title)
        return alternatives

    def clean_title(self, title: str) -> str:
        """Remove common extra information that causes search failures."""
        # Patterns to remove
        patterns = [
            r"\(.*?Director'?s Cut.*?\)",
            r"\(.*?Redux.*?\)",
            r"\(.*?Restored.*?\)",
            r"\(.*?Remastered.*?\)",
            r"Director'?s Cut",
            r"Redux",
            r"\[MV\]",  # Music Video
        ]
        
        cleaned = title
        for pattern in patterns:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
            
        return re.sub(r"\s+", " ", cleaned).strip()

    def generate_title_variants(
        self,
        title: str,
        original_title: Optional[str] = None,
    ) -> List[str]:
        """Return list of titles to try in order (original, cleaned, normalized, alternatives)."""
        variants: List[str] = []

        normalized_title = title.strip()
        
        # 1. Original MUBI title
        variants.append(normalized_title)
        
        # 2. Original title (from metadata)
        if original_title and original_title.strip().lower() != normalized_title.lower():
            variants.append(original_title.strip())

        # 3. Cleaned title (suffixes removed)
        cleaned = self.clean_title(normalized_title)
        if cleaned and cleaned.lower() != normalized_title.lower():
            variants.append(cleaned)

        # 4. Normalized title (conjunctions removed)
        normalized = self.normalize_title(normalized_title)
        if normalized and normalized != normalized_title and normalized != cleaned:
            variants.append(normalized)

        # 5. Alternative spellings
        # Generate alternatives from the BEST candidate (usually the cleaned one)
        base_for_alternatives = cleaned if cleaned else normalized_title
        alternatives = self.generate_alternative_spellings(base_for_alternatives)
        for alt in alternatives:
            if alt not in variants:
                variants.append(alt)

        return variants


class RetryStrategy:
    """Utility for retrying API requests with exponential backoff."""

    def __init__(
        self,
        max_retries: int = 10,
        initial_backoff: float = 1.0,
        multiplier: float = 1.5,
    ) -> None:
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff
        self.multiplier = multiplier

    def execute(
        self,
        func: Callable[[], ExternalMetadataResult],
        title: str,
    ) -> ExternalMetadataResult:
        backoff = self.initial_backoff

        for attempt in range(self.max_retries):
            logger.debug(f"Attempt {attempt + 1}/{self.max_retries} for '{title}'")

            try:
                result = func()
                if result.success:
                    return result
                
                # If explicitly failed without exception (e.g. not found), we might still want to retry 
                # if the logic was purely connection based, but here we assume logic decided valid 'not found'.
                # However, for 429 logic below, it's inside exception block.
                # If logic returns result.success=False for "Not Found", verify if we should retry?
                # Usually "Not Found" is final. Rate limts raise HTTPError.
                if result.error_message == "Title not found (404)":
                     return result

                # If result is failure but not 404, loop might continue? 
                # Current implementation just returns result if not success??
                # Wait, original code:
                # if result.success: return result
                # return result (immediately returns failure)
                # So it only retries on Exception!
                return result

            except requests.exceptions.HTTPError as error:
                status_code = error.response.status_code if error.response else None
                if status_code in [401, 402, 429, 500, 502, 503, 504]: # Added 5xx for safer server error handling
                    retry_after = error.response.headers.get("Retry-After")
                    wait_time = backoff
                    
                    if retry_after:
                        try:
                            wait_time = float(retry_after) + 1  # Add small buffer
                            logger.debug(f"Server requested wait time: {wait_time}s")
                        except ValueError:
                            pass

                    logger.warning(f"HTTP {status_code} received for '{title}'. Retrying after {wait_time:.1f}s")
                    time.sleep(wait_time)
                    backoff *= self.multiplier
                    continue
                
                if status_code == 404:
                    logger.debug(f"Title '{title}' not found (404)")
                    return ExternalMetadataResult(
                        success=False,
                        error_message="Title not found (404)",
                    )
                
                logger.error(f"HTTP error {status_code}: {error}")
                return ExternalMetadataResult(
                    success=False,
                    error_message=f"HTTP {status_code}",
                )

            except Exception as error:
                logger.error(f"Request error for '{title}': {error}")
                return ExternalMetadataResult(
                    success=False,
                    error_message=str(error),
                )

        return ExternalMetadataResult(
            success=False,
            error_message=f"Max retries ({self.max_retries}) exhausted",
        )
