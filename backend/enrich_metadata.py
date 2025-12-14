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

    # 3. Identify items needing enrichment
    items_to_process = []
    for i, film in enumerate(items):
        has_imdb = bool(film.get('imdb_id'))
        has_tmdb = bool(film.get('tmdb_id'))
        
        if not (has_imdb and has_tmdb):
            items_to_process.append((i, film))

    total_films = len(items)
    to_process_count = len(items_to_process)
    logger.info(f"Loaded {total_films} films. Found {to_process_count} needing enrichment.")
    
    if to_process_count == 0:
        logger.info("No films need enrichment.")
        return

    updated_count = 0
    start_time = datetime.now()

    # Helper function for threaded execution
    def process_film(index, film_data):
        title = film_data.get('title')
        original_title = film_data.get('original_title')
        year = film_data.get('year')
        
        # Helper to avoid too much noise but still log
        # logger.debug(f"Fetching metadata for '{title}'...") # debug level to reduce noise in parallel
        
        result = provider.get_imdb_id(title, original_title=original_title, year=year)
        return index, result, title

    # Run in parallel
    # TMDB limits: generous, but let's be safe. 5-10 workers is usually fine.
    max_workers = 10 
    
    import concurrent.futures
    
    logger.info(f"Starting enrichment with {max_workers} workers...")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        futures = {executor.submit(process_film, idx, film): idx for idx, film in items_to_process}
        
        completed_so_far = 0
        
        for future in concurrent.futures.as_completed(futures):
            completed_so_far += 1
            idx, result, title = future.result()
            
            # Interactive progress log every 10 or so?
            if completed_so_far % 10 == 0 or completed_so_far == to_process_count:
                logger.info(f"Progress: {completed_so_far}/{to_process_count} ({completed_so_far/to_process_count*100:.1f}%)")

            if result.success:
                film = items[idx] # direct reference to mutable dict in list
                has_imdb = bool(film.get('imdb_id'))
                has_tmdb = bool(film.get('tmdb_id'))
                
                changes = False
                if result.imdb_id and not has_imdb:
                    film['imdb_id'] = result.imdb_id
                    changes = True
                if result.tmdb_id and not has_tmdb:
                    film['tmdb_id'] = result.tmdb_id
                    changes = True
                
                if changes:
                    updated_count += 1
                    logger.info(f"  [MATCH] '{title}' -> IMDB={result.imdb_id}, TMDB={result.tmdb_id}")
            else:
                 # Optional: log failures?
                 # logger.warning(f"  [FAIL] '{title}': {result.error_message}")
                 pass

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
