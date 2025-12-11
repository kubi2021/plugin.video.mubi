from __future__ import annotations

import re
import time
from typing import Callable, List, Optional

import requests
import xbmc

from .base import ExternalMetadataResult


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
                # Use regex for case-insensitive replacement while preserving case of match if possible?
                # For simplicity, if we match 'Color', we want 'Colour'.
                # But 'Color' -> 'Colour', 'color' -> 'colour'.
                # Naive replacement:
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

    def generate_title_variants(
        self,
        title: str,
        original_title: Optional[str] = None,
    ) -> List[str]:
        """Return list of titles to try in order (original, normalized, alternatives)."""
        variants: List[str] = []

        normalized_title = title.strip()
        if original_title and original_title.strip().lower() != normalized_title.lower():
            variants.append(original_title.strip())

        normalized = self.normalize_title(normalized_title)
        if normalized:
            variants.append(normalized)

        variants.extend(self.generate_alternative_spellings(normalized))

        return variants


class RetryStrategy:
    """Utility for retrying OMDB requests with exponential backoff."""

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
            xbmc.log(
                f"Attempt {attempt + 1}/{self.max_retries} for '{title}'",
                xbmc.LOGDEBUG,
            )

            try:
                result = func()
                if result.success:
                    return result
                return result

            except requests.exceptions.HTTPError as error:
                status_code = error.response.status_code if error.response else None
                if status_code in [401, 402, 429]:
                    retry_after = error.response.headers.get("Retry-After")
                    wait_time = backoff
                    
                    if retry_after:
                        try:
                            wait_time = float(retry_after) + 1  # Add small buffer
                            xbmc.log(f"Server requested wait time: {wait_time}s", xbmc.LOGDEBUG)
                        except ValueError:
                            pass

                    xbmc.log(
                        f"HTTP {status_code} received for '{title}'. Retrying after {wait_time:.1f}s",
                        xbmc.LOGWARNING,
                    )
                    time.sleep(wait_time)
                    backoff *= self.multiplier
                    continue
                if status_code == 404:
                    xbmc.log(f"Title '{title}' not found (404)", xbmc.LOGDEBUG)
                    return ExternalMetadataResult(
                        success=False,
                        error_message="Title not found (404)",
                    )
                xbmc.log(f"HTTP error {status_code}: {error}", xbmc.LOGERROR)
                return ExternalMetadataResult(
                    success=False,
                    error_message=f"HTTP {status_code}",
                )

            except Exception as error:
                xbmc.log(f"Request error for '{title}': {error}", xbmc.LOGERROR)
                return ExternalMetadataResult(
                    success=False,
                    error_message=str(error),
                )

        return ExternalMetadataResult(
            success=False,
            error_message=f"Max retries ({self.max_retries}) exhausted",
        )
