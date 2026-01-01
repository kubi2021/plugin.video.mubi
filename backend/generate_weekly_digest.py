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


def main():
    print(f"Loading data from {INPUT_FILE}...")
    
    if not INPUT_FILE.exists():
        print(f"Error: {INPUT_FILE} not found.")
        sys.exit(1)
    
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
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
    
    # Generate Markdown
    md_lines = [
        "# 🎬 Mubi Weekly Digest",
        "",
        f"*Generated on: {now.strftime('%B %d, %Y')}*",
        "",
        "---",
        "",
        "## 📊 Global Stats",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total Movies in Catalog | **{total_movies:,}** |",
        f"| New Arrivals (Past 7 Days) | **{len(new_movies)}** |",
        "",
        "---",
        "",
        "## 🆕 New Arrivals",
        "",
    ]
    
    if not new_movies:
        md_lines.append("*No new movies found in the past 7 days.*")
    else:
        md_lines.append(f"*Sorted by Bayesian rating (highest first)*")
        md_lines.append("")
    
    for i, film in enumerate(new_movies, 1):
        title = film.get('title', 'Unknown Title')
        year = film.get('year', '')
        duration = film.get('duration', 0)
        genres = film.get('genres', [])
        directors = film.get('directors', [])
        countries = film.get('historic_countries', [])
        synopsis = film.get('short_synopsis', '')
        trailer_url = film.get('trailer_url')
        
        # Get image URL from stills
        stills = film.get('stills', {})
        image_url = stills.get('medium') or film.get('still_url')
        
        # Format genres
        genre_str = ", ".join(genres) if genres else "N/A"
        country_str = ", ".join(countries) if countries else ""
        
        # Build movie entry
        md_lines.append(f"### {i}. {title} ({year})")
        md_lines.append("")
        
        if image_url:
            md_lines.append(f"![{title}]({image_url})")
            md_lines.append("")
        
        md_lines.append(f"**{format_rating_line(film)}**")
        md_lines.append("")
        md_lines.append(f"🎭 **Genre:** {genre_str} | ⏱️ **Duration:** {duration} min" + (f" | 🌍 **From:** {country_str}" if country_str else ""))
        md_lines.append("")
        
        if directors:
            director_str = ", ".join(directors)
            md_lines.append(f"🎬 **Director:** {director_str}")
            md_lines.append("")
        
        if synopsis:
            md_lines.append(f"> {synopsis}")
            md_lines.append("")
        
        if trailer_url:
            md_lines.append(f"🎥 [Watch Trailer]({trailer_url})")
            md_lines.append("")
        
        md_lines.append("---")
        md_lines.append("")
    
    # Write markdown output
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    output_content = "\n".join(md_lines)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(output_content)
    
    # Write JSON output for React Email template
    json_output_file = OUTPUT_FILE.parent / 'weekly_digest.json'
    json_data = {
        "generatedAt": now.strftime('%B %d, %Y'),
        "totalMovies": total_movies,
        "newArrivals": [
            {
                "title": film.get('title', 'Unknown'),
                "year": film.get('year', 0),
                "bayesian": get_bayesian_score(film) or None,
                "bayesianVoters": get_rating_voters(film, 'bayesian'),
                "mubi": film.get('average_rating_out_of_ten'),
                "mubiVoters": film.get('number_of_ratings'),
                "imdb": get_rating_value(film, 'imdb'),
                "imdbVoters": get_rating_voters(film, 'imdb'),
                "tmdb": get_rating_value(film, 'tmdb'),
                "tmdbVoters": get_rating_voters(film, 'tmdb'),
                "genres": film.get('genres', []),
                "duration": film.get('duration', 0),
                "countries": film.get('historic_countries', []),
                "directors": film.get('directors', []),
                "synopsis": film.get('short_synopsis', ''),
                "imageUrl": (film.get('stills', {}) or {}).get('medium') or film.get('still_url'),
                "trailerUrl": film.get('trailer_url'),
            }
            for film in new_movies
        ]
    }
    
    with open(json_output_file, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Report generated: {OUTPUT_FILE}")
    print(f"   JSON output: {json_output_file}")
    print(f"   Total new movies: {len(new_movies)}")
    
    # Preview first few titles
    if new_movies:
        print("\nTop 5 by Bayesian rating:")
        for film in new_movies[:5]:
            title = film.get('title', 'Unknown')
            score = get_bayesian_score(film)
            print(f"  - {title}: {score:.1f}")


if __name__ == "__main__":
    main()

