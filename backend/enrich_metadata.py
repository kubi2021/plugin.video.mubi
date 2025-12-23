import json
import os
import sys
import logging
import concurrent.futures
from datetime import datetime
from typing import Dict, Any, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Try to import dotenv for local development
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    logger.warning("python-dotenv library not found. .env file will be ignored. Install with: pip install python-dotenv")

# Ensure backend package can be imported if running directly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.tmdb_provider import TMDBProvider
from backend.omdb_provider import OMDBProvider

def enrich_metadata(films_path='films.json', content_type='movie'):
    # 1. Load Environment & Config
    api_key = os.environ.get('TMDB_API_KEY')
    if not api_key:
        logger.error("TMDB_API_KEY environment variable not set. Skipping metadata enrichment.")
        sys.exit(1)

    provider = TMDBProvider(api_key=api_key)
    if not provider.test_connection():
        logger.error("Failed to connect to TMDB API. Check your API key.")
    # Load OMDB keys from environment
    # Support single variable with comma-separated keys (OMDB_API_KEYS)
    # Also support legacy single key (OMDB_API_KEY) for backward compatibility
    omdb_keys = []
    
    env_keys = os.environ.get('OMDB_API_KEYS')
    if env_keys:
        omdb_keys.extend([k.strip() for k in env_keys.split(',') if k.strip()])
        
    # Fallback/Additional check for single key
    single_key = os.environ.get('OMDB_API_KEY')
    if single_key and single_key not in omdb_keys:
        omdb_keys.append(single_key)
            
    if not omdb_keys:
        # Fallback for local dev if needed, or raise warning
        logger.warning("No OMDB_API_KEYS found in environment. OMDB enrichment will be skipped or limited.")
        omdb_provider = None
    else:
        omdb_provider = OMDBProvider(api_keys=omdb_keys)

    # 2. Load Films
    if not os.path.exists(films_path):
        logger.error(f"Films file {films_path} not found.")
        sys.exit(1)

    try:
        with open(films_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            items = data.get('items', [])
    except Exception as e:
        logger.error(f"Failed to load JSON: {e}")
        sys.exit(1)

    # 3. Identify items needing enrichment
    items_to_process = []
    for i, film in enumerate(items):
        has_imdb = bool(film.get('imdb_id'))
        has_tmdb = bool(film.get('tmdb_id'))
        
        # Check if we need OMDB enrichment
        needs_omdb = False
        if has_imdb:
            ratings = film.get('ratings', [])
            has_imdb_rating = any(r.get('source') == 'imdb' for r in ratings)
            if not has_imdb_rating:
                needs_omdb = True

        if has_tmdb and not needs_omdb:
            continue
            
        if not has_tmdb or needs_omdb:
            items_to_process.append((i, film))

    total_films = len(items)
    to_process_count = len(items_to_process)
    logger.info(f"Loaded {total_films} films. Found {to_process_count} needing enrichment.")
    
    if to_process_count == 0:
        logger.info("No films need enrichment.")
        return

    updated_count = 0
    start_time = datetime.now()

    max_workers = 10
    logger.info(f"Starting enrichment with {max_workers} workers...")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        futures = {executor.submit(process_film, film, provider, omdb_provider, idx, total_films, content_type): idx for idx, film in items_to_process}
        
        completed_so_far = 0
        
        for future in concurrent.futures.as_completed(futures):
            completed_so_far += 1
            idx = futures[future]
            
            try:
                result = future.result()
                if result:
                    updated_count += 1
            except Exception as e:
                logger.error(f"Error processing film index {idx}: {e}")

    logger.info(f"Enrichment complete. Updated {updated_count} films.")
    
    # --- Global Stats Report ---
    stats = {
        "no_tmdb_id": 0,
        "no_tmdb_rating": 0,
        "no_imdb_rating": 0
    }
    
    for film in items:
        if not film.get("tmdb_id"):
            stats["no_tmdb_id"] += 1
            
        ratings = film.get("ratings", [])
        has_tmdb_rating = any(r.get("source") == "tmdb" for r in ratings)
        has_imdb_rating = any(r.get("source") == "imdb" for r in ratings)
        
        if not has_tmdb_rating:
            stats["no_tmdb_rating"] += 1
        if not has_imdb_rating:
            stats["no_imdb_rating"] += 1

    generate_report(stats, omdb_provider, total_films, updated_count)

    # 4. Save
    if updated_count > 0:
        data['items'] = items
        
        with open(films_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        duration = datetime.now() - start_time
        logger.info(f"Enrichment complete. Updated {updated_count} films in {duration}.")
    else:
        logger.info("Enrichment complete. No new metadata found.")

def generate_report(stats: Dict[str, int], omdb_provider: Optional[OMDBProvider], total: int, updated: int):
    """Log a comprehensive stats report."""
    if total == 0:
        return

    def pct(count, total):
        if total == 0: return "0 (0.0%)"
        return f"{count} ({count/total*100:.1f}%)"

    logger.info("=" * 60)
    logger.info(f"GLOBAL STATS REPORT ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
    logger.info("=" * 60)
    logger.info(f"Total Films:      {total}")
    logger.info(f"Updated this run: {updated}")
    logger.info("-" * 60)
    logger.info(f"NO TMDB ID Found:      {pct(stats['no_tmdb_id'], total)}")
    logger.info(f"NO TMDB Rating:        {pct(stats['no_tmdb_rating'], total)}")
    logger.info(f"NO IMDB Rating:        {pct(stats['no_imdb_rating'], total)}")
    logger.info("-" * 60)
    
    if omdb_provider:
        try:
            failed_keys = omdb_provider.get_failed_keys()
            if failed_keys:
                logger.warning(f"FAILED OMDB KEYS ({len(failed_keys)}):")
                for k in failed_keys:
                    masked = f"...{k[-4:]}" if len(k) > 4 else "***"
                    logger.warning(f"  - Key ending in {masked}")
            else:
                logger.info("OMDB Keys: All healthy (or none used).")
        except AttributeError:
             logger.info("OMDB Provider: Does not support key reporting.")
    else:
        logger.info("OMDB Provider: Disabled/Not initialized.")
        
    logger.info("=" * 60)

    # Validation
    # ...

def process_film(film: Dict[str, Any], provider: TMDBProvider, omdb_provider: Optional[OMDBProvider], idx: int, total: int, media_type: str = "movie") -> bool:
    """
    Process a single film to fetch external metadata.
    Returns True if updated, False otherwise.
    """
    title = film.get('title')
    original_title = film.get('original_title')
    year = film.get('year')
    directors = film.get('directors', [])
    duration = film.get('duration')
    genres = film.get('genres', [])
    
    mubi_id = film.get('mubi_id')
    
    logger.info(f"[{idx+1}/{total}] Fetching metadata for '{title}' ({year}) [MubiID:{mubi_id}]...")
    
    if not title:
        return False

    tmdb_id = film.get('tmdb_id')
    
    result = provider.get_imdb_id(
        title, 
        original_title=original_title, 
        year=year, 
        media_type=media_type, 
        tmdb_id=tmdb_id,
        mubi_directors=directors,
        mubi_runtime=duration,
        mubi_genres=genres,
        mubi_id=mubi_id
    )
    
    if result.success:
        if result.imdb_id:
            film['imdb_id'] = result.imdb_id
        if result.tmdb_id:
            film['tmdb_id'] = result.tmdb_id
        
        # Build ratings array
        ratings = []
        
        # Add Mubi rating (from existing fields)
        mubi_rating = film.get('average_rating_out_of_ten')
        mubi_voters = film.get('number_of_ratings')
        if mubi_rating is not None:
            ratings.append({
                "source": "mubi",
                "score_over_10": float(mubi_rating),
                "voters": int(mubi_voters) if mubi_voters else 0
            })
        
        # Add TMDB rating
        if result.vote_average is not None:
            ratings.append({
                "source": "tmdb",
                "score_over_10": result.vote_average,
                "voters": result.vote_count or 0
            })
        
        # 3. OMDB Enrichment
        # Only attempt if provider has valid keys
        imdb_id = film.get('imdb_id')
        if imdb_id and omdb_provider and omdb_provider.api_keys:
            omdb_result = omdb_provider.get_details(imdb_id)
            if omdb_result.success and hasattr(omdb_result, 'extra_ratings'):
                ratings.extend(omdb_result.extra_ratings)
                logger.info(f"Found match: OMDB for '{title}'")
        
        if ratings:
            film['ratings'] = ratings
        
        logger.info(f"Found match [MubiID:{mubi_id}]: IMDB={result.imdb_id}, TMDB={result.tmdb_id}")
        return True
    else:
        logger.warning(f"No match found for '{title}' ({year}) [MubiID:{mubi_id}]")
        return False
    


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Enrich Mubi Catalog with TMDB/IMDB IDs")
    parser.add_argument('--path', default='films.json', help="Path to films.json")
    parser.add_argument('--type', choices=['movie', 'series'], default='movie', help="Content type (movie or series)")
    
    args = parser.parse_args()
    enrich_metadata(args.path, args.type)
