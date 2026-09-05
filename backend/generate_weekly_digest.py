#!/usr/bin/env python3
"""Generate a weekly digest of new Mubi films as a Markdown file."""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

# Configuration
REPO_ROOT = Path(__file__).parent.parent
INPUT_FILE = REPO_ROOT / "films.json"
OUTPUT_FILE = REPO_ROOT / "tmp" / "weekly_digest.md"
DAYS_LOOKBACK = 7


def get_bayesian_score(film: dict) -> float:
    """Extract Bayesian score from ratings array."""
    for rating in film.get("ratings", []):
        if rating.get("source") == "bayesian":
            return rating.get("score_over_10", 0) or 0
    return 0


def get_rating_value(film: dict, source: str) -> Optional[float]:
    """Extract specific rating value from ratings array."""
    for rating in film.get("ratings", []):
        if rating.get("source") == source:
            return rating.get("score_over_10")
    return None


def get_rating_voters(film: dict, source: str) -> Optional[int]:
    """Extract voter count for a specific rating source."""
    for rating in film.get("ratings", []):
        if rating.get("source") == source:
            return rating.get("voters")
    return None


def _parse_iso_utc(value) -> Optional[datetime]:
    """Parse an ISO 8601 string to an aware UTC datetime, or None.

    The single canonical normalise for every timestamp the digest compares:
    handle the Z suffix, and force a tz-less (naive) timestamp to UTC so it can
    be compared against the aware cutoff without raising TypeError. Anything that
    is not a non-empty string, or does not parse, returns None and never raises
    (an int/dict/None value would otherwise blow up the whole digest on
    ``.endswith``). The scraper's ``_earliest_started_availability`` mirrors this
    normalise — keep the two identical (CLAUDE.md lesson).
    """
    if not value or not isinstance(value, str):
        return None
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        dt = datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def get_earliest_availability(film: dict) -> Optional[datetime]:
    """
    Get the earliest available_at date across all countries for a film.
    Returns None if no valid dates found.
    """
    available_countries = film.get("available_countries", {})
    if not available_countries:
        return None

    earliest_date = None

    for country_code, country_data in available_countries.items():
        avail_dt = _parse_iso_utc((country_data or {}).get("available_at"))
        if avail_dt is None:
            continue
        if earliest_date is None or avail_dt < earliest_date:
            earliest_date = avail_dt

    return earliest_date


def get_first_available(film: dict) -> Optional[datetime]:
    """
    Parse the frozen first_available_at timestamp (when the film first became
    playable). This is the digest's inclusion signal: it is immutable, so
    country rotation cannot re-qualify a film, and it is null while a film is
    only upcoming, so upcoming titles are not featured before they go live.
    Returns None for null/absent/unparseable values.
    """
    return _parse_iso_utc(film.get("first_available_at"))


def get_latest_expiration(film: dict) -> Optional[datetime]:
    """
    Get the latest expires_at date across all countries for a film.
    Returns None if no keys or valid dates found.
    """
    available_countries = film.get("available_countries", {})
    if not available_countries:
        return None

    latest_date = None

    for country_code, country_data in available_countries.items():
        expires_dt = _parse_iso_utc((country_data or {}).get("expires_at"))
        if expires_dt is None:
            continue
        if latest_date is None or expires_dt > latest_date:
            latest_date = expires_dt

    return latest_date


def generate_digest(
    input_file: Path,
    output_file: Path,
    now_override: Optional[datetime] = None,
) -> None:
    """Main logic to generate the digest."""
    print(f"Loading data from {input_file}...")

    if not input_file.exists():
        print(f"Error: {input_file} not found.")
        sys.exit(1)

    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    items = data.get("items", [])
    total_movies = len(items)
    print(f"Total items loaded: {total_movies}")

    # Get current time and calculate cutoff
    now = now_override or datetime.now(timezone.utc)
    cutoff_date = now - timedelta(days=DAYS_LOOKBACK)

    print(f"Current time (UTC): {now.isoformat()}")
    print(f"Cutoff date: {cutoff_date.isoformat()}")
    print(f"Filtering movies that became available since {cutoff_date.date()}...")

    # Find new movies: became playable within the lookback window.
    # first_available_at is frozen the first time the film is observed as
    # actually playable, so:
    #  - a film qualifies for exactly one digest (no country-rotation churn),
    #  - upcoming films (null until they go live) are not featured early,
    #  - a film that fully left the catalogue and later returns is re-created
    #    and re-stamped, so it is featured again when it comes back.
    new_movies = []

    for film in items:
        first_available = get_first_available(film)
        if first_available is None or first_available < cutoff_date:
            continue
        film["_first_available"] = first_available  # Store for debugging
        new_movies.append(film)

    print(f"Found {len(new_movies)} movies that became available in the past {DAYS_LOOKBACK} days.")

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
        "",
    ]

    if not new_movies:
        md_lines.append("No new movies found in the past 7 days.")

    for i, film in enumerate(new_movies, 1):
        title = film.get("title", "Unknown Title")
        year = film.get("year")
        duration = film.get("duration")
        genres = film.get("genres", [])
        synopsis = film.get("short_synopsis", "")
        trailer_url = film.get("trailer_url")
        historic_countries = film.get("historic_countries", [])
        directors = film.get("directors", [])

        # Determine image URL
        stills = film.get("stills") or {}
        image_url = stills.get("medium") or film.get("still_url")

        # Ratings
        bayesian = get_bayesian_score(film)
        mubi = film.get("average_rating_out_of_ten")
        imdb = get_rating_value(film, "imdb")
        tmdb = get_rating_value(film, "tmdb")

        # Expiration
        latest_expires = get_latest_expiration(film)
        available_until = latest_expires.isoformat() if latest_expires else None

        # Build JSON entry
        json_movies.append(
            {
                "id": film.get("mubi_id"),
                "imdbId": film.get("imdb_id"),
                "tmdbId": film.get("tmdb_id"),
                "title": title,
                "year": year,
                "bayesian": bayesian or None,
                "bayesianVoters": get_rating_voters(film, "bayesian"),
                "mubi": mubi,
                "mubiVoters": film.get("number_of_ratings"),
                "imdb": imdb,
                "imdbVoters": get_rating_voters(film, "imdb"),
                "tmdb": tmdb,
                "tmdbVoters": get_rating_voters(film, "tmdb"),
                "genres": genres,
                "duration": duration,
                "countries": historic_countries,
                "directors": directors,
                "synopsis": synopsis,
                "imageUrl": image_url,
                "trailerUrl": trailer_url,
                "availableUntil": available_until,
            }
        )

        # Markdown formatting
        rating_str_parts = []
        if bayesian:
            rating_str_parts.append(f"Bayesian: **{bayesian:.1f}**")
        if mubi:
            rating_str_parts.append(f"Mubi: {mubi}")
        if imdb:
            rating_str_parts.append(f"IMDb: {imdb}")
        if tmdb:
            rating_str_parts.append(f"TMDB: {tmdb}")

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
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    # Write JSON
    json_output_file = output_file.with_suffix(".json")
    print(f"Writing JSON to {json_output_file}...")

    json_data = {"generatedAt": now.isoformat(), "totalMovies": total_movies, "newArrivals": json_movies}

    # Ensure tmp dir exists
    json_output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(json_output_file, "w", encoding="utf-8") as f:
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
