#!/usr/bin/env python3
"""Generate a weekly digest of new Mubi films as a Markdown file."""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

# Configuration
INPUT_FILE = Path('/Users/kubi/Downloads/films.json')
REPO_ROOT = Path(__file__).parent.parent
OUTPUT_FILE = REPO_ROOT / 'tmp' / 'weekly_digest.md'
DAYS_LOOKBACK = 7


def get_bayesian_score(film: dict) -> float:
    """Extract Bayesian score from ratings array."""
    for rating in film.get('ratings', []):
        if rating.get('source') == 'bayesian':
            return rating.get('score_over_10', 0) or 0
    return 0


def get_rating_value(film: dict, source: str) -> Optional[float]:
    """Extract specific rating value from ratings array."""
    for rating in film.get('ratings', []):
        if rating.get('source') == source:
            return rating.get('score_over_10')
    return None


def get_rating_voters(film: dict, source: str) -> Optional[int]:
    """Extract voter count for a specific rating source."""
    for rating in film.get('ratings', []):
        if rating.get('source') == source:
            return rating.get('voters')
    return None


def get_earliest_availability(film: dict) -> Optional[datetime]:
    """
    Get the earliest available_at date across all countries for a film.
    Returns None if no valid dates found.
    """
    available_countries = film.get('available_countries', {})
    if not available_countries:
        return None
    
    earliest_date = None
    
    for country_code, country_data in available_countries.items():
        avail_str = country_data.get('available_at')
        if not avail_str:
            continue
        
        try:
            # Parse ISO format date, handle Z suffix
            if avail_str.endswith('Z'):
                avail_str = avail_str[:-1] + '+00:00'
            avail_dt = datetime.fromisoformat(avail_str)
            
            if earliest_date is None or avail_dt < earliest_date:
                earliest_date = avail_dt
        except ValueError:
            continue
    
    return earliest_date


def get_latest_expiration(film: dict) -> Optional[datetime]:
    """
    Get the latest expires_at date across all countries for a film.
    Returns None if no keys or valid dates found.
    """
    available_countries = film.get('available_countries', {})
    if not available_countries:
        return None
    
    latest_date = None
    
    for country_code, country_data in available_countries.items():
        expires_str = country_data.get('expires_at')
        if not expires_str:
            continue
        
        try:
            # Parse ISO format date, handle Z suffix
            if expires_str.endswith('Z'):
                expires_str = expires_str[:-1] + '+00:00'
            expires_dt = datetime.fromisoformat(expires_str)
            
            if latest_date is None or expires_dt > latest_date:
                latest_date = expires_dt
        except ValueError:
            continue
    
    return latest_date


def format_rating_line(film: dict) -> str:
    """Format the ratings line for a film."""
    parts = []
    
    bayesian = get_bayesian_score(film)
    if bayesian:
        parts.append(f"⭐ **{bayesian:.1f}** (Bayesian)")
    
    mubi = film.get('average_rating_out_of_ten')
    if mubi:
        parts.append(f"Mubi: {mubi:.1f}")
    
    imdb = get_rating_value(film, 'imdb')
    if imdb:
        parts.append(f"IMDb: {imdb:.1f}")
    
    tmdb = get_rating_value(film, 'tmdb')
    if tmdb:
        parts.append(f"TMDB: {tmdb:.1f}")
    
    return " | ".join(parts) if parts else "No ratings available"


def generate_digest(input_file: Path, output_file: Path) -> None:
    """Main logic to generate the digest."""
    print(f"Loading data from {input_file}...")
    
    if not input_file.exists():
        print(f"Error: {input_file} not found.")
        sys.exit(1)
    
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    items = data.get('items', [])
    total_movies = len(items)
    print(f"Total items loaded: {total_movies}")
    
    # Get current time and calculate cutoff
    now = datetime.now(timezone.utc)
    cutoff_date = now - timedelta(days=DAYS_LOOKBACK)
    
    print(f"Current time (UTC): {now.isoformat()}")
    print(f"Cutoff date: {cutoff_date.isoformat()}")
    print(f"Filtering movies with earliest availability >= {cutoff_date.date()}...")
    
    # Find new movies
    new_movies = []
    
    for film in items:
        earliest_date = get_earliest_availability(film)
        if earliest_date and earliest_date >= cutoff_date:
            film['_earliest_availability'] = earliest_date  # Store for debugging
            new_movies.append(film)
    
    print(f"Found {len(new_movies)} new movies in the past {DAYS_LOOKBACK} days.")
    
    # Sort by Bayesian rating (descending)
    new_movies.sort(key=get_bayesian_score, reverse=True)
    
    # Prepare JSON data structure
    json_movies = []
    
    # Prepare Markdown content
    md_lines = [
        "# Mubi Weekly Digest",
        "",
        f"Generated on: {now.strftime('%Y-%m-%d')}",
        "",
        "## Global Stats",
        f"- **Total Movies**: {total_movies}",
        f"- **New Arrivals (Past 7 Days)**: {len(new_movies)}",
        "",
        "## New Arrivals",
        ""
    ]
    
    if not new_movies:
        md_lines.append("No new movies found in the past 7 days.")
    
    for i, film in enumerate(new_movies, 1):
        title = film.get('title', 'Unknown Title')
        year = film.get('year')
        duration = film.get('duration')
        genres = film.get('genres', [])
        synopsis = film.get('short_synopsis', '')
        trailer_url = film.get('trailer_url')
        historic_countries = film.get('historic_countries', [])
        directors = film.get('directors', [])
        
        # Determine image URL
        stills = film.get('stills') or {}
        image_url = stills.get('medium') or film.get('still_url')
        
        # Ratings
        bayesian = get_bayesian_score(film)
        mubi = film.get('average_rating_out_of_ten')
        imdb = get_rating_value(film, 'imdb')
        tmdb = get_rating_value(film, 'tmdb')
        
        # Expiration
        latest_expires = get_latest_expiration(film)
        available_until = latest_expires.isoformat() if latest_expires else None
        
        # Build JSON entry
        json_movies.append({
            "id": film.get('mubi_id'),
            "imdbId": film.get('imdb_id'),
            "tmdbId": film.get('tmdb_id'),
            "title": title,
            "year": year,
            "bayesian": bayesian or None,
            "bayesianVoters": get_rating_voters(film, 'bayesian'),
            "mubi": mubi,
            "mubiVoters": film.get('number_of_ratings'),
            "imdb": imdb,
            "imdbVoters": get_rating_voters(film, 'imdb'),
            "tmdb": tmdb,
            "tmdbVoters": get_rating_voters(film, 'tmdb'),
            "genres": genres,
            "duration": duration,
            "countries": historic_countries,
            "directors": directors,
            "synopsis": synopsis,
            "imageUrl": image_url,
            "trailerUrl": trailer_url,
            "availableUntil": available_until
        })
        
        # Markdown formatting
        rating_str_parts = []
        if bayesian: rating_str_parts.append(f"Bayesian: **{bayesian:.1f}**")
        if mubi: rating_str_parts.append(f"Mubi: {mubi}")
        if imdb: rating_str_parts.append(f"IMDb: {imdb}")
        if tmdb: rating_str_parts.append(f"TMDB: {tmdb}")
        
        rating_line = " | ".join(rating_str_parts) if rating_str_parts else "No ratings available"
        genres_str = ", ".join(genres)
        
        md_lines.append(f"### {i}. {title} ({year})")
        
        if image_url:
            md_lines.append(f"\n![{title}]({image_url})")
            
        md_lines.append(f"\n**{rating_line}**")
        md_lines.append(f"\n**Genre**: {genres_str} | **Duration**: {duration} min")
        if available_until:
             md_lines.append(f" | **Available until**: {latest_expires.strftime('%Y-%m-%d')}")
        
        if synopsis:
             md_lines.append(f"\n> {synopsis}")
             
        if trailer_url:
            md_lines.append(f"\n[Watch Trailer]({trailer_url})")
            
        md_lines.append("\n---")

    # Write Markdown
    print(f"Writing Markdown to {output_file}...")
    # Ensure tmp dir exists
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md_lines))
        
    # Write JSON
    json_output_file = output_file.with_suffix('.json')
    print(f"Writing JSON to {json_output_file}...")
    
    json_data = {
        "generatedAt": now.isoformat(),
        "totalMovies": total_movies,
        "newArrivals": json_movies
    }
    
    # Ensure tmp dir exists
    json_output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(json_output_file, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    
    print("Done.")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate weekly digest.")
    parser.add_argument("--input", type=Path, default=INPUT_FILE, help="Path to input films.json")
    parser.add_argument("--output", type=Path, default=OUTPUT_FILE, help="Path to output Markdown/JSON file")
    
    args = parser.parse_args()
    
    generate_digest(args.input, args.output)


if __name__ == "__main__":
    main()
