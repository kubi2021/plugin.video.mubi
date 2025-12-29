import json
import os
import sys
import csv
import logging
from datetime import datetime

# Setup paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.tmdb_provider import TMDBProvider
from backend.omdb_provider import OMDBProvider
from thefuzz import fuzz

# Setup logging
logging.basicConfig(level=logging.WARNING, format='%(message)s') # WARNING to reduce noise from provider DEBUG
logger = logging.getLogger(__name__)

def evaluate_matching(input_path, output_csv):
    tmdb_key = os.environ.get('TMDB_API_KEY')
    if not tmdb_key:
        print("Error: TMDB_API_KEY not set.")
        sys.exit(1)
        
    # Get OMDB Keys
    omdb_keys = []
    env_keys = os.environ.get('OMDB_API_KEYS')
    if env_keys:
        omdb_keys.extend([k.strip() for k in env_keys.split(',') if k.strip()])
    single_key = os.environ.get('OMDB_API_KEY')
    if single_key and single_key not in omdb_keys:
        omdb_keys.append(single_key)
        
    if not omdb_keys:
        print("Warning: OMDB_API_KEYS not set. OMDB evaluation will be skipped.")
        omdb_provider = None
    else:
        omdb_provider = OMDBProvider(api_keys=omdb_keys)
        
    provider = TMDBProvider(api_key=tmdb_key)
    if not provider.test_connection():
        print("Error: Could not connect to TMDB.")
        sys.exit(1)

    print(f"Loading {input_path}...")
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Handle both list and dict wrapper
            if isinstance(data, list):
                all_items = data
            else:
                all_items = data.get('items', [])
    except FileNotFoundError:
        print(f"Error: {input_path} not found.")
        sys.exit(1)
    
    # Optimize with Multi-threading
    items = all_items
    print(f"Evaluating ALL {len(items)} films with 10 threads...")
    
    results = []
    
    # Track stats
    matched_count = 0
    omdb_attempted = 0
    omdb_found = 0
    
    import concurrent.futures

    def process_item(idx, film):
        mubi_id = film.get('mubi_id')
        title = film.get('title')
        year = film.get('year')
        
        mubi_directors = film.get('directors', [])
        mubi_rating = film.get('average_rating_out_of_ten')
        
        # Perform Match
        result = provider.get_imdb_id(
            title=title,
            original_title=film.get('original_title'),
            year=year,
            media_type='movie',
            mubi_directors=mubi_directors,
            mubi_runtime=film.get('duration'),
            mubi_genres=film.get('genres'),
            mubi_id=mubi_id
        )
        
        # OMDB Evaluation
        imdb_id = result.imdb_id if result.success else None
        omdb_success = "SKIPPED"
        omdb_error = ""
        omdb_ratings = {}
        omdb_res_success = False
        
        if imdb_id and omdb_provider:
             # Thread-safe? Request itself is thread-safe. OMDBProvider has a lock on key rotation.
            omdb_res = omdb_provider.get_details(imdb_id)
            if omdb_res.success:
                omdb_success = "YES"
                omdb_res_success = True
                # Parse extra ratings
                if hasattr(omdb_res, 'extra_ratings'):
                    for r in omdb_res.extra_ratings:
                        omdb_ratings[r['source']] = r['score_over_10']
            else:
                omdb_success = "NO"
                omdb_error = omdb_res.error_message
        
        # Risk Analysis
        risk_flags = []
        if result.success:
            if result.matched_year and year and abs(result.matched_year - year) > 1:
                risk_flags.append(f"YearDelta:{result.matched_year - year}")
            if fuzz.ratio(title, result.matched_title) < 80 and fuzz.ratio(film.get('original_title', ''), result.matched_original_title) < 80:
                risk_flags.append(f"TitleMismatch:{fuzz.ratio(title, result.matched_title)}")
            if result.match_score < 85:
                risk_flags.append("LowScore")

        film_data = {
            # Mubi Base Data
            "mubi_id": mubi_id,
            "mubi_title": title,
            "mubi_original_title": film.get('original_title'),
            "mubi_year": year,
            "mubi_directors": ", ".join(mubi_directors),
            "mubi_rating": mubi_rating,
            
            # TMDB Matched Data
            "tmdb_id": result.tmdb_id if result.success else "NO MATCH",
            "imdb_id": imdb_id if imdb_id else "",
            "tmdb_title": result.matched_title if result.success else "",
            "tmdb_original_title": result.matched_original_title if result.success else "",
            "tmdb_year": result.matched_year if result.success else "",
            "tmdb_directors": ", ".join(result.matched_directors) if result.success and result.matched_directors else "",
            "tmdb_vote_avg": result.vote_average if result.success else "",
            
            # Match Metrics
            "match_score": result.match_score if result.success else 0,
            "title_similarity": fuzz.ratio(title, result.matched_title) if result.success and result.matched_title else 0,
            
            # OMDB Data
            "omdb_success": omdb_success,
            "omdb_error": omdb_error,
            "omdb_imdb_rating": omdb_ratings.get('imdb', ''),
            "omdb_metacritic": omdb_ratings.get('metacritic', ''),
            "omdb_rotten_tomatoes": omdb_ratings.get('rotten_tomatoes', ''),
            
            # Heuristics
            "risk_flags": "; ".join(risk_flags)
        }
        
        return film_data, result.success, (imdb_id is not None and omdb_provider is not None), omdb_res_success

    # Sort of random order due to threads, but acceptable for evaluation
    
    # Prepare CSV
    fieldnames = [
        "mubi_id", "mubi_title", "mubi_original_title", "mubi_year", "mubi_directors", "mubi_rating",
        "tmdb_id", "imdb_id", "tmdb_title", "tmdb_original_title", "tmdb_year", "tmdb_directors", "tmdb_vote_avg",
        "match_score", "title_similarity",
        "omdb_success", "omdb_error", "omdb_imdb_rating", "omdb_metacritic", "omdb_rotten_tomatoes",
        "risk_flags"
    ]
    
    with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(process_item, i, film): i for i, film in enumerate(items)}
            
            count = 0
            for future in concurrent.futures.as_completed(futures):
                count += 1
                idx = futures[future]
                try:
                    f_data, is_match, tried_omdb, found_omdb = future.result()
                    
                    writer.writerow(f_data)
                    csvfile.flush() # Ensure written to disk
                    
                    if is_match: matched_count += 1
                    if tried_omdb: omdb_attempted += 1
                    if found_omdb: omdb_found += 1
                    
                    if count % 20 == 0:
                         print(f"Processed {count}/{len(items)}... Matches: {matched_count}, OMDB: {omdb_found}")

                except Exception as e:
                    print(f"Error processing item index {idx}: {e}")
    
    print(f"Report saved incrementally to {output_csv}")
    
    # Summary
    print(f"\n=== SUMMARY ===")
    print(f"Total Films: {len(results)}")
    print(f"TMDB Matches: {matched_count} ({100*matched_count/len(results):.1f}%)")
    if omdb_attempted > 0:
        print(f"OMDB Success Rate: {omdb_found}/{omdb_attempted} ({100*omdb_found/omdb_attempted:.1f}%)")
    else:
        print("OMDB: Not attempted (no keys or no IMDB IDs)")

if __name__ == "__main__":
    input_file = "films_clean.json"
    output_file = "evaluation_results.csv"
    evaluate_matching(input_file, output_file)
