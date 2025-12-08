#!/usr/bin/env python3
"""
MUBI Country Catalogue Analyzer

Developer tool to query the MUBI API and build a country catalogue showing
which movies are available in which countries. Works both inside and outside Kodi.

What it does:
1. Queries the MUBI API for each country's film catalogue
2. Builds a map of film_id -> available countries (country-agnostic storage)
3. Generates a JSON catalogue file
4. Prints coverage analysis with optimal country sets for any user country

Usage (standalone - fetch and analyze):
    python -m tools.analyze_coverage [OPTIONS]

Usage (standalone - analyze existing data for different country):
    python -m tools.analyze_coverage --analyze-only --country US

    Options:
        --country, -c      Your country code for analysis (default: CH)
        --output, -o       Output path for JSON catalogue
        --no-json          Skip JSON generation, only print analysis
        --analyze-only, -a Analyze existing JSON without fetching (fast)
        --verbose, -v      Enable verbose logging

Usage (from Kodi):
    Can be imported and called directly when Kodi modules are available.
"""

import sys
import os

# Determine if we're running inside Kodi or standalone
try:
    import xbmc
    RUNNING_IN_KODI = True
except ImportError:
    RUNNING_IN_KODI = False
    # Inject Kodi stubs before importing plugin modules
    from tools.kodi_stubs import (
        XbmcStub, XbmcaddonStub, XbmcguiStub, XbmcpluginStub, XbmcvfsStub,
        InputstreamhelperStub
    )
    sys.modules['xbmc'] = XbmcStub('xbmc')
    sys.modules['xbmcaddon'] = XbmcaddonStub('xbmcaddon')
    sys.modules['xbmcgui'] = XbmcguiStub('xbmcgui')
    sys.modules['xbmcplugin'] = XbmcpluginStub('xbmcplugin')
    sys.modules['xbmcvfs'] = XbmcvfsStub('xbmcvfs')
    sys.modules['inputstreamhelper'] = InputstreamhelperStub('inputstreamhelper')


import json
from datetime import datetime
from pathlib import Path
from collections import defaultdict

# Now we can import from the plugin
from resources.lib.mubi import Mubi
from resources.lib.session_manager import SessionManager
from resources.lib.countries import COUNTRIES


# Output path for the generated JSON (relative to plugin root)
SCRIPT_DIR = Path(__file__).parent
PLUGIN_ROOT = SCRIPT_DIR.parent
OUTPUT_JSON_PATH = PLUGIN_ROOT / "resources" / "data" / "country_catalogue.json"


class StandaloneSessionManager:
    """Minimal session manager for standalone use (no authentication needed)."""

    def __init__(self, client_country='CH'):
        self.device_id = 'standalone-analyzer'
        self.client_country = client_country
        self.client_language = 'en'
        self.token = None
        self.is_logged_in = False
        self.user_id = None


def fetch_all_countries_catalogue(mubi: Mubi, countries: list, progress_callback=None) -> dict:
    """
    Fetch film catalogues for all specified countries.

    Returns:
        dict with structure:
        {
            'film_countries': {film_id: set(country_codes)},
            'country_films': {country_code: set(film_ids)},
            'total_films': int,
            'total_countries': int
        }
    """
    film_countries = defaultdict(set)  # film_id -> set of countries
    country_films = {}  # country_code -> set of film_ids

    total_countries = len(countries)

    for idx, country_code in enumerate(countries, 1):
        if progress_callback:
            if not progress_callback(idx, total_countries, country_code):
                break  # User cancelled

        print(f"[{idx}/{total_countries}] Fetching {country_code}...", end=' ', flush=True)

        try:
            film_ids, _, total_count, pages = mubi._fetch_films_for_country(
                country_code=country_code,
                playable_only=True,
                page_callback=None,
                global_film_ids=None
            )

            country_films[country_code] = film_ids
            for film_id in film_ids:
                film_countries[film_id].add(country_code)

            print(f"{len(film_ids)} films ({pages} pages)")

        except Exception as e:
            print(f"ERROR: {e}")
            country_films[country_code] = set()

    return {
        'film_countries': dict(film_countries),
        'country_films': country_films,
        'total_films': len(film_countries),
        'total_countries': len([c for c in country_films if country_films[c]])
    }


def calculate_greedy_coverage(country_films: dict, mandatory_first: list = None) -> list:
    """
    Greedy set-cover algorithm to find optimal country order.

    Args:
        country_films: {country_code: set(film_ids)}
        mandatory_first: List of countries that must be included first

    Returns:
        List of (country_code, new_films_count, cumulative_count, coverage_pct)
    """
    all_films = set()
    for films in country_films.values():
        all_films.update(films)

    total_films = len(all_films)
    if total_films == 0:
        return []

    covered = set()
    result = []
    remaining = set(country_films.keys())

    # Process mandatory countries first
    for country in (mandatory_first or []):
        if country in remaining:
            films = country_films.get(country, set())
            new_films = films - covered
            covered.update(new_films)
            remaining.remove(country)
            result.append((
                country,
                len(new_films),
                len(covered),
                len(covered) / total_films * 100
            ))

    # Greedy selection for remaining
    while remaining and len(covered) < total_films:
        best_country = None
        best_new = 0

        for country in remaining:
            films = country_films.get(country, set())
            new_count = len(films - covered)
            if new_count > best_new:
                best_new = new_count
                best_country = country

        if best_country is None or best_new == 0:
            break

        covered.update(country_films[best_country])
        remaining.remove(best_country)
        result.append((
            best_country,
            best_new,
            len(covered),
            len(covered) / total_films * 100
        ))

    return result


def calculate_country_stats(country_films: dict, film_countries: dict) -> dict:
    """Calculate statistics for each country."""
    stats = {}
    for country, films in country_films.items():
        exclusive = sum(1 for f in films if len(film_countries.get(f, set())) == 1)
        rare = sum(1 for f in films if len(film_countries.get(f, set())) <= 3)
        stats[country] = {
            'total': len(films),
            'exclusive': exclusive,
            'rare': rare
        }
    return stats


def generate_json_catalogue(catalogue: dict, output_path: Path) -> None:
    """Generate and save the JSON catalogue file.

    Stores film → countries mapping for flexibility.
    Analysis for any user country can be done on the fly from this data.
    """
    film_countries = catalogue['film_countries']

    # Build output structure: film_id → list of countries
    # This is more compact and country-agnostic
    output = {
        'generated': datetime.now().isoformat(),
        'total_films': catalogue['total_films'],
        'total_countries': catalogue['total_countries'],
        'films': {
            str(film_id): sorted(list(countries))
            for film_id, countries in film_countries.items()
        }
    }

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    size_kb = output_path.stat().st_size / 1024
    print(f"\n💾 Saved catalogue to: {output_path}")
    print(f"   File size: {size_kb:.1f} KB")


def load_json_catalogue(json_path: Path) -> dict:
    """Load a previously generated JSON catalogue and convert to internal format.

    This allows running analysis on any country without re-fetching.
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Rebuild internal format from film → countries mapping
    film_countries = {
        int(film_id): set(countries)
        for film_id, countries in data['films'].items()
    }

    # Rebuild country → films mapping
    country_films = defaultdict(set)
    for film_id, countries in film_countries.items():
        for country in countries:
            country_films[country].add(film_id)

    return {
        'film_countries': dict(film_countries),
        'country_films': dict(country_films),
        'total_films': data['total_films'],
        'total_countries': data['total_countries'],
        'generated': data.get('generated', 'unknown')
    }


def print_analysis(catalogue: dict, user_country: str = 'CH'):
    """Print comprehensive analysis."""
    country_films = catalogue['country_films']
    film_countries = catalogue['film_countries']
    total_films = catalogue['total_films']
    stats = calculate_country_stats(country_films, film_countries)

    print("\n" + "=" * 75)
    print("📊 CATALOGUE OVERVIEW")
    print("=" * 75)
    print(f"   Total unique movies: {total_films}")
    print(f"   Total countries with content: {catalogue['total_countries']}")

    # User's country stats
    user_country_upper = user_country.upper()
    user_films = country_films.get(user_country_upper, set())
    user_stats = stats.get(user_country_upper, {})

    print("\n" + "=" * 75)
    print(f"🇨🇭 YOUR COUNTRY: {user_country_upper}")
    print("=" * 75)
    if user_films:
        coverage = len(user_films) / total_films * 100 if total_films else 0
        print(f"   Movies available: {len(user_films)} ({coverage:.1f}% of catalogue)")
        print(f"   Exclusive movies: {user_stats.get('exclusive', 0)} (only in {user_country_upper})")
        print(f"   Rare movies: {user_stats.get('rare', 0)} (in ≤3 countries)")
    else:
        print(f"   No data for {user_country_upper}")

    # Greedy coverage with user's country first
    greedy = calculate_greedy_coverage(country_films, mandatory_first=[user_country_upper])

    # Speed oriented: Top 5
    print("\n" + "=" * 75)
    print(f"⚡ SPEED ORIENTED: Top 5 countries (including {user_country_upper})")
    print("=" * 75)
    print(f"\n{'Rank':<6}{'Country':<10}{'New Movies':<12}{'Cumulative':<12}{'Coverage':<10}")
    print("-" * 50)
    for i, (country, new_films, cumulative, pct) in enumerate(greedy[:5], 1):
        print(f"{i:<6}{country:<10}{new_films:<12}{cumulative:<12}{pct:.1f}%")

    # Completion oriented: 100% coverage
    full_coverage = [(c, n, cum, p) for c, n, cum, p in greedy if p >= 99.99]
    if full_coverage:
        countries_needed = len(full_coverage) if full_coverage[-1][3] >= 99.99 else len(greedy)
    else:
        countries_needed = len(greedy)

    print("\n" + "=" * 75)
    print(f"🏆 COMPLETION ORIENTED: Minimum countries for 100% (including {user_country_upper})")
    print("=" * 75)
    full_countries = [c for c, _, _, _ in greedy]
    print(f"\n   ✅ {len(full_countries)} countries needed for 100% coverage")
    print(f"   Total movies: {total_films}")
    print(f"\n   Countries: {full_countries[:20]}")
    if len(full_countries) > 20:
        print(f"   ... and {len(full_countries) - 20} more")

    # Coverage milestones
    print("\n" + "=" * 75)
    print(f"📈 COVERAGE MILESTONES (with {user_country_upper} as base)")
    print("=" * 75)
    print(f"\n{'Target':<10}{'Countries':<12}{'Movies':<12}{'Country List':<40}")
    print("-" * 75)

    milestones = [50, 75, 90, 95, 99, 100]
    for target in milestones:
        for i, (country, new_films, cumulative, pct) in enumerate(greedy):
            if pct >= target:
                countries_list = ', '.join([c for c, _, _, _ in greedy[:i+1]])
                if len(countries_list) > 38:
                    countries_list = countries_list[:35] + "..."
                print(f"{target}%{'':<6}{i+1:<12}{cumulative:<12}{countries_list}")
                break

    # Top 20 by total movies
    print("\n" + "=" * 75)
    print("🌍 TOP 20 COUNTRIES BY TOTAL MOVIES")
    print("=" * 75)
    sorted_by_total = sorted(stats.items(), key=lambda x: x[1]['total'], reverse=True)[:20]
    print(f"\n{'Rank':<6}{'Country':<10}{'Total':<10}{'Exclusive':<12}{'Rare (≤3)':<12}")
    print("-" * 50)
    for i, (country, s) in enumerate(sorted_by_total, 1):
        print(f"{i:<6}{country:<10}{s['total']:<10}{s['exclusive']:<12}{s['rare']:<12}")

    # Recommended core countries
    print("\n" + "=" * 75)
    print("📝 RECOMMENDED CORE_COUNTRIES")
    print("=" * 75)

    # Find 5, 10, 20 country sets
    for n in [5, 10, 20]:
        if len(greedy) >= n:
            countries = [c for c, _, _, _ in greedy[:n]]
            coverage = greedy[n-1][3]
            print(f"\n# {n} countries ({coverage:.1f}% coverage)")
            print(f"CORE_COUNTRIES_{n} = {countries}")

    print(f"\n# Complete: {len(greedy)} countries for 100%")
    print(f"CORE_COUNTRIES_FULL = {[c for c, _, _, _ in greedy]}")


def main():
    """Main entry point for standalone execution."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Analyze MUBI country coverage via API."
    )
    parser.add_argument(
        "--country", "-c",
        default="CH",
        help="Your country code for analysis (default: CH)"
    )
    parser.add_argument(
        "--output", "-o",
        default=str(OUTPUT_JSON_PATH),
        help=f"Output path for JSON catalogue (default: {OUTPUT_JSON_PATH})"
    )
    parser.add_argument(
        "--no-json",
        action="store_true",
        help="Skip JSON generation, only print analysis"
    )
    parser.add_argument(
        "--analyze-only", "-a",
        action="store_true",
        help="Only analyze existing JSON file (no API fetching)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    user_country = args.country.upper()

    # Analyze-only mode: load existing JSON and run analysis
    if args.analyze_only:
        json_path = Path(args.output)
        if not json_path.exists():
            print(f"\n❌ JSON file not found: {json_path}")
            print("   Run without --analyze-only to fetch data first.")
            sys.exit(1)

        print(f"\n📊 MUBI Country Coverage Analyzer (from cached data)")
        print(f"   Loading: {json_path}")
        catalogue = load_json_catalogue(json_path)
        print(f"   Generated: {catalogue.get('generated', 'unknown')}")
        print_analysis(catalogue, user_country=user_country)
        return

    # Set verbose mode for stubs
    if not RUNNING_IN_KODI:
        from tools.kodi_stubs import XbmcStub
        XbmcStub._verbose = args.verbose

    # Create standalone session manager
    session = StandaloneSessionManager(client_country=user_country)

    # Create Mubi instance
    mubi = Mubi(session)

    # Get list of all countries
    country_codes = list(COUNTRIES.keys())
    print(f"\n📊 MUBI Country Coverage Analyzer")
    print(f"   Your country: {user_country} ({COUNTRIES.get(user_country.lower(), 'Unknown')})")
    print(f"   Fetching catalogues for {len(country_codes)} countries...")
    print("   This will take several minutes.\n")

    # Fetch all catalogues
    catalogue = fetch_all_countries_catalogue(mubi, country_codes)

    if catalogue['total_films'] == 0:
        print("\n❌ No films found! Check API connectivity.")
        sys.exit(1)

    # Generate JSON
    if not args.no_json:
        generate_json_catalogue(catalogue, Path(args.output))

    # Print analysis
    print_analysis(catalogue, user_country=user_country)


if __name__ == "__main__":
    main()
