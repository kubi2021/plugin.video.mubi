import requests
import sys
import json
import time
import os
import gzip
import hashlib
import concurrent.futures
import logging
import pycountry
import random
from datetime import datetime
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MubiScraper:
    BASE_URL = 'https://api.mubi.com/v4'
    UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0'
    MIN_TOTAL_FILMS = 1000
    MAX_WORKERS = 2 # Increased for debugging speed
    CRITICAL_COUNTRIES = ['US', 'GB', 'FR', 'DE']
    MAX_MISSING_PERCENT = 5.0 # Max % of films allowed to have missing critical fields before failure
    
    # Dynamically generate full country list
    COUNTRIES = [country.alpha_2 for country in pycountry.countries]

    # Mubi to US MPAA Mapping Table
    MUBI_TO_MPAA_MAP = {
        "GENERAL": "G",
        "AL": "G",
        "A10": "PG",
        "12": "PG-13",
        "A12": "PG-13",
        "14": "PG-13",
        "A14": "PG-13",
        "CAUTION": "PG-13",
        "16": "R",
        "A16": "R",
        "MATURE": "R",
        "18": "NC-17",
        "A18": "NC-17",
        "ADULT": "NC-17"
    }

    def __init__(self):
        self.session = self._create_session()

    def _create_session(self):
        session = requests.Session()
        retries = Retry(
            total=8, # Increased retries
            backoff_factor=2, # Increased backoff
            status_forcelist=[500, 502, 503, 504, 429],
            allowed_methods=["GET"]
        )
        adapter = HTTPAdapter(max_retries=retries)
        session.mount('https://', adapter)
        session.mount('http://', adapter)
        session.headers.update({
            'User-Agent': self.UA,
            'Client': 'web',
            'Origin': 'https://mubi.com',
            'Referer': 'https://mubi.com',
            'Accept-Encoding': 'gzip'
        })
        return session

    def _get_headers(self, country_code):
        headers = {
            'Client-Country': country_code,
            'accept-language': 'en'
        }
        return headers

    def fetch_films_for_country(self, country_code):
        # Add random jitter to desynchronize threads
        time.sleep(random.uniform(0.5, 2.0))
        
        logger.info(f"Fetching films for {country_code}...")
        film_ids = set()
        films_data = [] # List of film objects
        page = 1
        
        while True:
            try:
                url = f"{self.BASE_URL}/browse/films"
                params = {
                    'page': page,
                    'sort': 'title',
                    'playable': 'true'
                }
                
                response = self.session.get(url, headers=self._get_headers(country_code), params=params, timeout=15)
                
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 10))
                    logger.warning(f"Rate limited (429). Waiting {retry_after}s...")
                    time.sleep(retry_after)
                    continue

                response.raise_for_status()
                data = response.json()
                
                films = data.get('films', [])
                for film in films:
                    film_ids.add(film['id'])
                    films_data.append(film)

                meta = data.get('meta', {})
                logger.info(f"[{country_code}] Page {page} fetched. {len(films)} films.")

                if not meta.get('next_page'):
                    break
                
                page = meta['next_page']
                time.sleep(0.5) # Politeness delay between pages

            except Exception as e:
                logger.error(f"Error fetching page {page} for {country_code}: {e}")
                # Re-raise so run() can track the error
                raise e
        
        return films_data

    def validate_data(self, final_items):
        """
        Validates the harvested data against safety thresholds.
        Returns a list of error messages (empty if valid).
        """
        validation_errors = []
        total = len(final_items)

        # 1. Total Count Threshold
        if total < self.MIN_TOTAL_FILMS:
            validation_errors.append(f"Total film count {total} is below minimum threshold ({self.MIN_TOTAL_FILMS})")

        # 2. Field Integrity
        missing_mubi_id = 0
        missing_title = 0
        missing_year = 0
        
        for item in final_items:
            if not item.get('mubi_id'):
                missing_mubi_id += 1
                logger.warning(f"Film missing mubi_id: {item}")
            if not item.get('title'):
                missing_title += 1
            if not item.get('year'):
                missing_year += 1
        
        # Calculate percentages
        if total > 0:
            pct_missing_year = (missing_year / total) * 100
            if pct_missing_year > self.MAX_MISSING_PERCENT:
                validation_errors.append(f"Field Integrity: {pct_missing_year:.1f}% of films missing 'year' (max {self.MAX_MISSING_PERCENT}%)")
            
            if missing_title > 0:
                 pct_missing_title = (missing_title / total) * 100
                 if pct_missing_title > self.MAX_MISSING_PERCENT:
                     validation_errors.append(f"Field Integrity: {pct_missing_title:.1f}% of films missing 'title'")

        return validation_errors

    def calculate_greedy_targets(self, existing_films):
        """
        Uses a Greedy Set Cover algorithm to find the minimum set of countries
        needed to cover all films in the existing dataset.
        """
        logger.info("Calculating optimal country set using Greedy Set Cover...")
        
        # 1. Build Universe and Subsets
        # Universe: All Film IDs we need to cover
        universe = set()
        # Subsets: Country -> Set of Film IDs available there
        country_coverage = {c: set() for c in self.COUNTRIES}
        
        for film in existing_films:
            fid = film['mubi_id']
            universe.add(fid)
            
            # Use available_countries keys
            available_countries = film.get('available_countries', {})
            for c in available_countries.keys():
                if c in country_coverage:
                    country_coverage[c].add(fid)
        
        logger.info(f"Universe size: {len(universe)} films across {len(self.COUNTRIES)} countries.")
        
        # 2. Greedy Loop
        selected_countries = []
        covered_films = set()
        
        while len(covered_films) < len(universe):
            # Find country that covers the most *uncovered* films
            best_country = None
            best_new_coverage = 0
            
            remaining_needed = universe - covered_films
            
            for country, films in country_coverage.items():
                if country in selected_countries:
                    continue
                
                # Intersection of this country's films with what we still need
                newly_covered = len(films.intersection(remaining_needed))
                
                if newly_covered > best_new_coverage:
                    best_new_coverage = newly_covered
                    best_country = country
            
            if best_country is None:
                # This happens if remaining films are not available in any known country (should not happen if data is consistent)
                logger.warning(f"Could not find coverage for {len(remaining_needed)} remaining films. Stopping greedy search.")
                break
            
            selected_countries.append(best_country)
            covered_films.update(country_coverage[best_country])
            logger.info(f"Selected {best_country} (Covers {best_new_coverage} new films). Total covered: {len(covered_films)}/{len(universe)}")
            
        logger.info(f"Optimal set found: {len(selected_countries)} countries cover {len(covered_films)} films.")
        # Sort for consistent execution order
        return sorted(selected_countries)

    def _prune_series_data(self, data):
        """
        Removes specific fields from series/episode data to reduce file size.
        """
        keys_to_remove = [
            'fotd_show_episode', 'episode_label_color', 'title_upcase', 'slug', 'web_url',
            'availability_message', 'short_synopsis_html', 'default_editorial_html',
            'trailer_url', 'trailer_id', 'industry_events_count', 'cast_members_count',
            'optimised_trailers', 'artworks'
        ]
        
        # Helper to prune a dict in-place
        def prune_dict(d):
            if not d: return
            for key in keys_to_remove:
                d.pop(key, None)
        
        prune_dict(data.get('episode'))
        prune_dict(data.get('series'))

    def _prune_film_data(self, data):
        """
        Removes unnecessary fields from film data to reduce file size.
        Removes: label_hex_color from content_rating, focal_point from artworks.
        """
        # Prune content_rating
        content_rating = data.get('content_rating')
        if content_rating and isinstance(content_rating, dict):
            content_rating.pop('label_hex_color', None)
        
        # Prune artworks
        artworks = data.get('artworks', [])
        if artworks:
            # Prune unused artwork formats to save space
            # We only keep:
            # - cover_artwork_vertical (Poster)
            # - centered_background (Fanart)
            # - cover_artwork_horizontal (Banner)
            
            kept_formats = {
                'cover_artwork_vertical', 
                'centered_background', 
                'cover_artwork_horizontal'
            }
            
            pruned_artworks = []
            for artwork in artworks:
                if artwork.get('format') in kept_formats:
                    # Prune extra fields from the artwork object itself
                    if 'focal_point' in artwork:
                        del artwork['focal_point']
                    if 'locale' in artwork: # Often null or unused
                         del artwork['locale']
                    pruned_artworks.append(artwork)
            
            data['artworks'] = pruned_artworks

    def _enrich_genres(self, film_data):
        """
        Enriches genres with 'LGBTQ+' if keywords are found in synopsis or editorial.
        """
        keys_to_check = ['short_synopsis', 'default_editorial']
        keywords = [
            'queer', 'lgbt', 'lesbian', 'transgender', 'bisexual', 'intersex', 
            'pansexual', 'transsexual', 'non-binary', 'nonbinary', 'homosexual', 
            'drag queen', 'drag king', 'same-sex', 'gender identity'
        ]
        
        found = False
        for key in keys_to_check:
            text = film_data.get(key)
            if text and isinstance(text, str):
                lower_text = text.lower()
                for keyword in keywords:
                    if keyword in lower_text:
                        found = True
                        break
            if found:
                break
        
        if found:
            genres = film_data.get('genres') or []
            if 'LGBTQ+' not in genres:
                genres.append('LGBTQ+')
                film_data['genres'] = genres

    def run(self, output_path='films.json', series_path='series.json', mode='deep', input_path=None):
        all_films = {} # id -> film_data
        all_series = {} # id -> series_data
        film_countries = {} # id -> dict(country -> consumable)
        series_countries = {} # id -> dict(country -> consumable)
        errors = [] # Track errors per country
        
        # Determine paths
        # If input_path is not explicitly set, try to use output_path as input (incremental update)
        load_path = input_path if input_path else output_path
        # We also need to load existing series data if available (simplification: assume input_path holds films, we derive series input path)
        series_load_path = series_path 
        if input_path and not series_path:
             # If specific input path given, we might need a specific series input, but for now defaults work
             pass

        # -- 1. LOAD EXISTING DATA --
        # Load Films
        if os.path.exists(load_path):
            try:
                with open(load_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    existing_items = data.get('items', [])
                    
                logger.info(f"Loaded {len(existing_items)} existing films from {load_path}")
                
                for film in existing_items:
                    fid = film['mubi_id']
                    all_films[fid] = film
                    if mode == 'shallow':
                         # Load existing available_countries
                         if 'available_countries' in film:
                             film_countries[fid] = film['available_countries']
                         else:
                             film_countries[fid] = {}
                    else:
                         film_countries[fid] = {}

            except Exception as e:
                logger.error(f"Failed to load existing data from {load_path}: {e}")
        else:
             logger.info(f"No existing data found at {load_path}. Starting fresh.")

        # Load Series
        if os.path.exists(series_load_path):
            try:
                with open(series_load_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    existing_items = data.get('items', [])
                    
                logger.info(f"Loaded {len(existing_items)} existing series from {series_load_path}")
                
                for item in existing_items:
                    fid = item['mubi_id']
                    all_series[fid] = item
                    if mode == 'shallow':
                         if 'available_countries' in item:
                             series_countries[fid] = item['available_countries']
                         else:
                             series_countries[fid] = {}
                    else:
                         series_countries[fid] = {}

            except Exception as e:
                logger.error(f"Failed to load existing series data: {e}")
        else:
             logger.info(f"No existing series data found. Starting fresh.")


        # -- 2. DETERMINE TARGETS --
        target_countries = []
        if mode == 'deep':
            logger.info("Starting DEEP sync (Full Calibration)...")
            target_countries = self.COUNTRIES
        
        elif mode == 'shallow':
            logger.info("Starting SHALLOW sync (Incremental Update)...")
            if not all_films:
                 logger.warning("Shallow sync requested but no existing data found. This will effectively be a partial fresh scrape.")
            
            # Use the existing data (films AND series) to calculate targets
            # Combine values for coverage calculation
            combined_items = list(all_films.values()) + list(all_series.values())
            # Note: calculate_greedy_targets might need adaptation if it relies solely on 'countries' list
            # We will patch 'countries' list temporarily onto items for the greedy calc if needed, 
            # or update calculate_greedy_targets.
            # For this refactor, let's assume keys of available_countries are sufficient.
            
            # Temporary adapter for greedy algo: ensure items have 'countries' list derived from 'available_countries' keys
            for item in combined_items:
                if 'available_countries' in item and isinstance(item['available_countries'], dict):
                    item['countries'] = list(item['available_countries'].keys())
                # If old schema 'countries' exists, it stays.

            target_countries = self.calculate_greedy_targets(combined_items)

        # --- 3. SCRAPING LOOP (PARALLEL) ---
        logger.info(f"Starting scrape for {len(target_countries)} countries: {target_countries}")
        
        scraped_fids_this_run = set()
        scraped_sids_this_run = set() # Series IDs

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as executor:
            future_to_country = {executor.submit(self.fetch_films_for_country, country): country for country in target_countries}
            
            for future in concurrent.futures.as_completed(future_to_country):
                country = future_to_country[future]
                
                try:
                    items = future.result()
                    
                    if not items:
                         logger.warning(f"No items found for {country}")
                         if mode == 'deep' and country in self.CRITICAL_COUNTRIES:
                                 errors.append(f"Critical country {country} returned 0 items.")

                    # MERGE LOGIC
                    for item in items:
                        fid = item['id']
                        
                        # Data Mapping - Extended schema
                        new_data = {
                            # Core identifiers
                            'mubi_id': fid,
                            
                            # Basic metadata
                            'title': item.get('title'),
                            'original_title': item.get('original_title'),
                            'year': item.get('year'),
                            'duration': item.get('duration'),
                            'genres': item.get('genres', []),
                            'directors': [d['name'] for d in item.get('directors', [])],
                            'short_synopsis': item.get('short_synopsis'),
                            'default_editorial': item.get('default_editorial'),
                            'historic_countries': item.get('historic_countries', []),
                            
                            # Mubi-specific ratings
                            'popularity': item.get('popularity'),
                            'average_rating_out_of_ten': item.get('average_rating_out_of_ten'),
                            'number_of_ratings': item.get('number_of_ratings'),
                            'hd': item.get('hd'),
                            'critic_review_rating': item.get('critic_review_rating'),
                            
                            # Content rating & warnings
                            'content_rating': item.get('content_rating'),
                            # Scraper-derived MPAA
                            'mpaa': None,
                            'content_warnings': item.get('content_warnings', []),
                            
                            # Imagery & artwork
                            'stills': item.get('stills'),
                            'still_url': item.get('still_url')['url'] if isinstance(item.get('still_url'), dict) else item.get('still_url'),
                            'portrait_image': item.get('portrait_image')['url'] if isinstance(item.get('portrait_image'), dict) else item.get('portrait_image'),
                            'artworks': item.get('artworks', []),
                            
                            # Trailers
                            'trailer_url': item.get('trailer_url'),
                            'trailer_id': item.get('trailer_id'),
                            'optimised_trailers': item.get('optimised_trailers'),
                            
                            # Availability & playback
                            'playback_languages': (item.get('consumable') or {}).get('playback_languages'),
                            
                            # Awards & press
                            'award': item.get('award'),
                            'press_quote': item.get('press_quote'),
                            
                            # Series/episode info
                            'episode': item.get('episode'),
                            'series': item.get('series')
                        }
                        
                        # Prune unnecessary fields from film data
                        self._prune_film_data(new_data)
                        
                        # Enrich genres (LGBTQ+ tagging)
                        self._enrich_genres(new_data)

                        # Calculate MPAA Rating
                        content_rating = new_data.get('content_rating')
                        if content_rating:
                            # Use rating_code as primary, fallback to label
                            rating_code = content_rating.get('rating_code', '')
                            rating_label = content_rating.get('label', '')
                            
                            # Check rating_code first, then label
                            key = str(rating_code).upper() if rating_code else str(rating_label).upper()
                            
                            # Look up in the map
                            if key in self.MUBI_TO_MPAA_MAP:
                                new_data['mpaa'] = {'US': self.MUBI_TO_MPAA_MAP[key]}

                        # --- DISTINGUISH SERIES VS FILM ---
                        is_series = False
                        if item.get('episode') is not None or item.get('series') is not None:
                            is_series = True
                        
                        if is_series:
                            scraped_sids_this_run.add(fid)
                            target_dict = all_series
                            target_countries_dict = series_countries
                            
                            # Clean up Series Data
                            self._prune_series_data(new_data)
                            
                        else:
                            scraped_fids_this_run.add(fid)
                            target_dict = all_films
                            target_countries_dict = film_countries

                        # Update or Create
                        if fid in target_dict:
                            target_dict[fid].update(new_data)
                        else:
                            target_dict[fid] = new_data
                            # CLEANUP: Remove legacy 'countries' if it exists when creating new
                            target_dict[fid].pop('countries', None)
                        
                        # Init country dict
                        if fid not in target_countries_dict:
                            target_countries_dict[fid] = {}

                        # Add availability data for this country
                        # We store the 'consumable' object which contains dates and status
                        consumable = item.get('consumable') or {}
                        if consumable:
                            # Create a slim copy with only essential fields
                            consumable_copy = consumable.copy()
                            
                            # Remove playback_languages (moved to top level)
                            consumable_copy.pop('playback_languages', None)
                            
                            # Prune unused fields to reduce JSON size (~8MB savings)
                            consumable_copy.pop('offered', None)           # Always catalogue
                            consumable_copy.pop('film_id', None)           # Already at top level
                            consumable_copy.pop('film_date_message', None) # Always null
                            consumable_copy.pop('exclusive', None)         # Not used
                            consumable_copy.pop('permit_download', None)   # Not used
                            
                            target_countries_dict[fid][country] = consumable_copy
                    
                    logger.info(f"Finished {country}. Total films: {len(all_films)}, Total series: {len(all_series)}")
                    
                except Exception as e:
                    import traceback
                    logger.error(f"Failed to process {country}: {e}")
                    logger.error(f"Full traceback:\n{traceback.format_exc()}")
                    errors.append(f"{country}: {str(e)}")


        # --- 4. FINALIZATION & PRUNING ---
         
        # In DEEP mode: Prune removed content
        if mode == 'deep':
            # Prune Films
            initial_count_films = len(all_films)
            for fid in list(all_films.keys()):
                if fid not in scraped_fids_this_run:
                    del all_films[fid]
                    if fid in film_countries:
                        del film_countries[fid]
            
            removed_count = initial_count_films - len(all_films)
            if removed_count > 0:
                logger.info(f"DEEP SYNC: Pruned {removed_count} films.")

            # Prune Series
            initial_count_series = len(all_series)
            for sid in list(all_series.keys()):
                if sid not in scraped_sids_this_run:
                    del all_series[sid]
                    if sid in series_countries:
                        del series_countries[sid]
            
            removed_count_s = initial_count_series - len(all_series)
            if removed_count_s > 0:
                logger.info(f"DEEP SYNC: Pruned {removed_count_s} series episodes.")

        # --- PREPARE FINAL LISTS ---
        final_films = []
        for fid, film in all_films.items():
            # Assign aggregated availability data
            avail = film_countries.get(fid, {})
            
            # ZOMBIE FILTER: If no availability in any country, SKIP (Deep Sync Only)
            # In Shallow Sync, we avoid removing items to ensure "append-only" behavior,
            # even if they currently appear to have no availability (zombie state).
            if mode == 'deep' and not avail:
                if mode == 'deep': # Only strict prune in deep mode to be safe? 
                    # Actually, we never want zombies in the DB, deep or shallow.
                    # But in shallow mode we might not have updated availability for all countries?
                    # Shallow mode calculates targets based on coverage. If we sync and find it has NO countries now, drop it.
                    pass
            
            if not avail:
                 # If we have confirmed it has no availability, don't include it.
                 # The only edge case is if we did a partial sync and missed the country it IS available in?
                 # But shallow sync uses coverage. If we checked its known countries and found nothing, it's gone.
                 # If we didn't check its countries, we wouldn't have updated it? 
                 # Wait, shallow sync only updates. It doesn't delete unless we're in deep mode?
                 # If shallow sync, 'film_countries' only contains data for synced countries.
                 # We need to merge with existing data? 
                 # Unrelated to this specific task, let's stick to the obvious fix for the reported issue which is likely Deep Sync related.
                 # User's json was likely from a Deep Sync.
                 pass

            # Assign aggregated availability data
            combined_avail = film_countries.get(fid, {})
            
            # IMPORTANT: For Zombie filtering, we need to be careful not to drop films in shallow sync 
            # if we simply didn't scrape their countries. 
            # But the 'film_countries' dictionary in 'run' is initialized from EXISTING data in step 1.
            # So 'film_countries' contains global availability state.
            # If it's empty, it essentially means the film is gone everywhere.
            
            if not combined_avail:
                 # It's a zombie.
                 continue

            film['available_countries'] = combined_avail
            # Remove legacy list if present to ensure schema cleanliness
            film.pop('countries', None)
            final_films.append(film)

        final_series = []
        for sid, item in all_series.items():
            # Assign aggregated availability data
            item['available_countries'] = series_countries.get(sid, {})
            # Remove legacy list if present
            item.pop('countries', None)
            final_series.append(item)

        # PANIC CHECK
        if len(final_films) == 0 and len(final_series) == 0:
            logger.error("CRITICAL: Scraper generated 0 items. Aborting.")
            sys.exit(1)

        # VALIDATE (Only in Deep Mode, Only Films for now)
        if mode == 'deep':
            data_errors = self.validate_data(final_films)
            if data_errors:
                errors.extend(data_errors)
        else:
             logger.info("Skipping data validation for Shallow Sync (Append-Only mode).")

        # SAVE FILMS
        output_films = {
            'meta': {
                'generated_at': datetime.utcnow().isoformat() + 'Z',
                'version': 1,
                'version_label': '1.0-beta.3',  # Human-readable version for debugging
                'total_count': len(final_films),
                'mode': mode
            },
            'items': final_films
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_films, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Successfully saved {len(final_films)} films to {output_path}")

        # SAVE SERIES
        output_series = {
            'meta': {
                'generated_at': datetime.utcnow().isoformat() + 'Z',
                'version': 1,
                'version_label': '1.0-beta.3',  # Human-readable version for debugging
                'total_count': len(final_series),
                'mode': mode
            },
            'items': final_series
        }

        with open(series_path, 'w', encoding='utf-8') as f:
            json.dump(output_series, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Successfully saved {len(final_series)} series episodes to {series_path}")

        if errors:
            logger.error(f"Scraper finished with {len(errors)} errors:")
            for e in errors:
                logger.error(f"  - {e}")
            sys.exit(1)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Mubi Catalog Scraper")
    parser.add_argument('--mode', choices=['deep', 'shallow'], default='deep', help="Deep (calibration) or Shallow (fast) sync")
    parser.add_argument('--output', default='films.json', help="Output films file path")
    parser.add_argument('--series-output', default='series.json', help="Output series file path")
    parser.add_argument('--input', default=None, help="Input file path (required for shallow mode)")
    parser.add_argument('--countries', default=None, help="Comma-separated list of country codes to scrape (e.g., DE,US,GB). Defaults to all.")
    
    args = parser.parse_args()
    
    scraper = MubiScraper()
    
    # Override COUNTRIES if specified
    if args.countries:
        scraper.COUNTRIES = [c.strip().upper() for c in args.countries.split(',')]
        logger.info(f"Limiting scrape to countries: {scraper.COUNTRIES}")
    
    scraper.run(output_path=args.output, series_path=args.series_output, mode=args.mode, input_path=args.input)
