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
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Target IDs from user (previous no-match cases)
TARGET_IDS = {
    170676, 237636, 400379, 392, 434001, 377417, 336255, 363013, 93415, 132330,
    132501, 133955, 133953, 133812, 200149, 156533, 294106, 290069, 107884, 430902,
    162511, 374529, 234651, 23078, 350898, 402206, 25673, 104, 362266, 16152,
    383, 229011, 179876, 151958, 2572, 182499, 276385, 87410, 177652, 217139,
    23699, 104590, 120970, 200178, 456912, 456913, 301059, 164520, 126797, 3570,
    3052, 222916, 234624, 241060, 24075, 25706, 103075, 23805, 42129, 30335,
    30337, 30339, 30348, 21500, 22606, 1035, 843, 91713, 401237, 2710,
    83246, 113557, 149852, 2024, 46380, 27543, 224, 1031, 1175, 269463,
    290112, 104721, 435039, 205618, 3099
}

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
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        all_items = data.get('items', [])
    
    # Filter to target IDs only
    items = [film for film in all_items if film.get('mubi_id') in TARGET_IDS]
    print(f"Evaluating {len(items)} films (filtered from {len(all_items)})...")
    
    results = []
    
    for i, film in enumerate(items):
        mubi_id = film.get('mubi_id')
        title = film.get('title')
        year = film.get('year')
        
        # Log progress
        print(f"Processing {i+1}/{len(items)}: {title} ({year}) [MubiID: {mubi_id}]")
            
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
    matched = sum(1 for r in results if r["tmdb_id"] != "NO MATCH")
    print(f"\n=== SUMMARY ===")
    print(f"Total: {len(results)}")
    print(f"Matched: {matched} ({100*matched/len(results):.1f}%)")
    print(f"No Match: {len(results) - matched}")

if __name__ == "__main__":
    input_file = "films_clean.json"
    output_file = "evaluation_targeted.csv"
    evaluate_matching(input_file, output_file)
