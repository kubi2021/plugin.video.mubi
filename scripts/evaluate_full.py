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
from thefuzz import fuzz

# Setup logging
logging.basicConfig(level=logging.WARNING, format='%(message)s') # WARNING to reduce noise from provider DEBUG
logger = logging.getLogger(__name__)

def evaluate_matching(input_path, output_csv):
    api_key = os.environ.get('TMDB_API_KEY')
    if not api_key:
        print("Error: TMDB_API_KEY not set.")
        sys.exit(1)
        
    provider = TMDBProvider(api_key=api_key)
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
    
    items = all_items
    print(f"Evaluating ALL {len(items)} films...")
    
    results = []
    
    # Track stats
    matched_count = 0
    
    for i, film in enumerate(items):
        mubi_id = film.get('mubi_id')
        title = film.get('title')
        year = film.get('year')
        
        # Log progress every 10 items
        if i % 10 == 0:
            print(f"Processing {i+1}/{len(items)}: {title} ({year}) [MubiID: {mubi_id}] - Matches so far: {matched_count}")
            
        mubi_directors = film.get('directors', [])
        mubi_rating = film.get('average_rating_out_of_ten')
        
        # Perform Match
        # Note: We rely on TMDBProvider's robust logging for debug details
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
        
        if result.success:
            matched_count += 1
        
        # Risk Analysis for Manual Review
        risk_flags = []
        if result.success:
            if result.matched_year and year and abs(result.matched_year - year) > 1:
                risk_flags.append(f"YearDelta:{result.matched_year - year}")
            if fuzz.ratio(title, result.matched_title) < 80 and fuzz.ratio(film.get('original_title', ''), result.matched_original_title) < 80:
                risk_flags.append(f"TitleMismatch:{fuzz.ratio(title, result.matched_title)}")
            if result.match_score < 85:
                risk_flags.append("LowScore")
            # Check director mismatch if directors exist
            if mubi_directors and result.matched_directors:
                # Simple check: is any mubi director part of tmdb directors?
                # We can reuse the provider's normalization logic or just fuzzy search
                # For summary, just checking exact substring might be enough or assume provider did its job
                # But we want to flag "Relaxed Overlap" cases
                pass
                
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
            "tmdb_title": result.matched_title if result.success else "",
            "tmdb_original_title": result.matched_original_title if result.success else "",
            "tmdb_year": result.matched_year if result.success else "",
            "tmdb_directors": ", ".join(result.matched_directors) if result.success and result.matched_directors else "",
            "tmdb_rating": result.vote_average if result.success else "",
            
            # Metrics
            "match_score": result.match_score if result.success else 0,
            "title_similarity": fuzz.ratio(title, result.matched_title) if result.success and result.matched_title else 0,
            "year_delta": (result.matched_year - year) if result.success and result.matched_year and year else "",
            "tmdb_votes": result.vote_count if result.success else "",
            "error_msg": result.error_message if not result.success else "",
            
            # Heuristics
            "risk_flags": "; ".join(risk_flags)
        }
        results.append(film_data)
        
    # Generate CSV
    print("Generating CSV report...")
    if not results:
        print("No results to save.")
        return

    keys = list(results[0].keys())
    
    with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=keys)
        writer.writeheader()
        writer.writerows(results)
            
    print(f"Report saved to {output_csv}")
    
    # Summary
    print(f"\n=== SUMMARY ===")
    print(f"Total: {len(results)}")
    print(f"Matched: {matched_count} ({100*matched_count/len(results):.1f}%)")
    print(f"No Match: {len(results) - matched_count}")

if __name__ == "__main__":
    input_file = "films_clean.json"
    output_file = "evaluation_results.csv" # Standardizing output name
    evaluate_matching(input_file, output_file)
