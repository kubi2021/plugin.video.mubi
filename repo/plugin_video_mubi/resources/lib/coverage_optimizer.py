"""
Coverage Optimizer - Greedy Set Cover Algorithm for MUBI Catalogue

Uses a pre-computed country catalogue JSON to determine the minimum set of
countries needed to achieve 100% film coverage, starting with the user's country.

This allows worldwide sync to fetch from ~23 countries instead of 248,
dramatically reducing API calls and sync time.
"""

import json
import os
from collections import defaultdict
from typing import Dict, List, Optional

try:
    import xbmc
    import xbmcaddon
    RUNNING_IN_KODI = True
except ImportError:
    RUNNING_IN_KODI = False


def _get_catalogue_path() -> str:
    """Get the path to the country catalogue JSON file."""
    if RUNNING_IN_KODI:
        addon_path = xbmcaddon.Addon().getAddonInfo('path')
        return os.path.join(addon_path, 'resources', 'data', 'country_catalogue.json')
    else:
        # For testing or standalone use
        current_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(current_dir, '..', 'data', 'country_catalogue.json')


def load_country_catalogue() -> Optional[Dict]:
    """
    Load the pre-computed country catalogue from JSON.

    Returns:
        dict with 'films' mapping film_id -> list of country codes,
        or None if file not found or invalid.
    """
    catalogue_path = _get_catalogue_path()

    if not os.path.exists(catalogue_path):
        if RUNNING_IN_KODI:
            xbmc.log(f"Country catalogue not found: {catalogue_path}", xbmc.LOGWARNING)
        return None

    try:
        with open(catalogue_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if 'films' not in data:
            if RUNNING_IN_KODI:
                xbmc.log("Invalid country catalogue format: missing 'films' key", xbmc.LOGERROR)
            return None

        return data

    except (json.JSONDecodeError, IOError) as e:
        if RUNNING_IN_KODI:
            xbmc.log(f"Error loading country catalogue: {e}", xbmc.LOGERROR)
        return None


def get_optimal_countries(user_country: str) -> List[str]:
    """
    Use the greedy set cover algorithm to find the minimum set of countries
    needed for 100% catalogue coverage, starting with the user's country.

    Args:
        user_country: ISO 3166-1 alpha-2 country code (e.g., 'CH', 'US')

    Returns:
        List of country codes in optimal order (user's country first),
        or empty list if catalogue not available.
    """
    catalogue = load_country_catalogue()
    if not catalogue:
        return []

    user_country_lower = user_country.lower()

    # Build country -> films mapping from film -> countries
    country_films = defaultdict(set)
    all_films = set()

    for film_id, countries in catalogue['films'].items():
        film_id_int = int(film_id)
        all_films.add(film_id_int)
        for country in countries:
            country_films[country].add(film_id_int)

    if not all_films:
        return []

    # Import COUNTRIES for VPN tier lookup
    try:
        from .countries import COUNTRIES
    except ImportError:
        from countries import COUNTRIES

    # Greedy set cover algorithm
    covered = set()
    selected = []
    remaining = dict(country_films)

    # Always start with user's country
    if user_country_lower in remaining:
        covered.update(remaining[user_country_lower])
        selected.append(user_country_lower.upper())
        del remaining[user_country_lower]

    # Greedily select countries that cover the most uncovered films
    # Tiebreaker: prefer countries with lower VPN tier (better infrastructure)
    while covered != all_films and remaining:
        def country_score(c):
            new_films_count = len(remaining[c] - covered)
            # VPN tier: 1=best, 4=worst. Use negative for descending sort on coverage
            vpn_tier = COUNTRIES.get(c, {}).get('vpn_tier', 4)
            # Return tuple: (new_films DESC, vpn_tier ASC)
            return (-new_films_count, vpn_tier)
        
        best = min(remaining.keys(), key=country_score)
        new_films = remaining[best] - covered

        if not new_films:
            break  # No more films to cover

        covered.update(new_films)
        selected.append(best.upper())
        del remaining[best]

    if RUNNING_IN_KODI:
        xbmc.log(
            f"Coverage optimizer: {len(selected)} countries needed for 100% coverage "
            f"(starting with {user_country.upper()})",
            xbmc.LOGINFO
        )

    return selected


def get_coverage_stats(user_country: str) -> dict:
    """
    Get statistics about coverage optimization.

    Returns:
        dict with 'total_films', 'total_countries_available', 'optimal_countries',
        'user_country_films' (films available in user's country)
    """
    catalogue = load_country_catalogue()
    if not catalogue:
        return {}

    user_country_lower = user_country.lower()

    # Build mappings
    country_films = defaultdict(set)
    all_films = set()

    for film_id, countries in catalogue['films'].items():
        film_id_int = int(film_id)
        all_films.add(film_id_int)
        for country in countries:
            country_films[country].add(film_id_int)

    optimal = get_optimal_countries(user_country)

    return {
        'total_films': len(all_films),
        'total_countries_available': len(country_films),
        'optimal_countries': optimal,
        'optimal_country_count': len(optimal),
        'user_country_films': len(country_films.get(user_country_lower, set())),
    }

