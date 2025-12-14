import json
import os
import sys
import logging
from datetime import datetime

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

def enrich_metadata(films_path='films.json'):
    # 1. Load Environment & Config
    api_key = os.environ.get('TMDB_API_KEY')
    if not api_key:
        logger.error("TMDB_API_KEY environment variable not set. Skipping metadata enrichment.")
        sys.exit(1)

    provider = TMDBProvider(api_key=api_key)
    if not provider.test_connection():
        logger.error("Failed to connect to TMDB API. Check your API key.")
        sys.exit(1)

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

    logger.info(f"Loaded {len(items)} films. Starting enrichment...")

    updated_count = 0
    start_time = datetime.now()

    # 3. Iterate and Enrich
    for i, film in enumerate(items):
        title = film.get('title')
        original_title = film.get('original_title')
        year = film.get('year')
        mubi_id = film.get('mubi_id')

        # Check if we already have the IDs
        has_imdb = bool(film.get('imdb_id'))
        has_tmdb = bool(film.get('tmdb_id'))

        if has_imdb and has_tmdb:
            continue

        logger.info(f"[{i+1}/{len(items)}] Fetching metadata for '{title}' ({year})...")
        
        result = provider.get_imdb_id(title, original_title=original_title, year=year)
        
        if result.success:
            changes = False
            if result.imdb_id and not has_imdb:
                film['imdb_id'] = result.imdb_id
                changes = True
            if result.tmdb_id and not has_tmdb:
                film['tmdb_id'] = result.tmdb_id
                changes = True
            
            if changes:
                updated_count += 1
                logger.info(f"  -> Found IDs: IMDB={result.imdb_id}, TMDB={result.tmdb_id}")
            else:
                 logger.info("  -> Data found matches existing or incomplete.")
        else:
            logger.warning(f"  -> No match found: {result.error_message}")

    # 4. Save
    if updated_count > 0:
        data['items'] = items
        # Update meta timestamp if desired, or just save
        # data['meta']['generated_at'] = ... (Maybe we keep scraper's timestamp?)
        
        with open(films_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        duration = datetime.now() - start_time
        logger.info(f"Enrichment complete. Updated {updated_count} films in {duration}.")
    else:
        logger.info("Enrichment complete. No new metadata found.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Enrich Mubi Catalog with TMDB/IMDB IDs")
    parser.add_argument('--path', default='films.json', help="Path to films.json")
    
    args = parser.parse_args()
    enrich_metadata(args.path)
