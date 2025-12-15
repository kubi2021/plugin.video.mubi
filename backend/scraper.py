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
    MAX_WORKERS = 2 # Reduced to avoid 429s
    CRITICAL_COUNTRIES = ['US', 'GB', 'FR', 'DE']
    MAX_MISSING_PERCENT = 5.0 # Max % of films allowed to have missing critical fields before failure
    
    # Dynamically generate full country list
    COUNTRIES = [country.alpha_2 for country in pycountry.countries]

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
            for c in film.get('countries', []):
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

    def run(self, output_path='films.json', series_path='series.json', mode='deep', input_path=None):
        all_films = {} # id -> film_data
        all_series = {} # id -> series_data
        film_countries = {} # id -> set(countries)
        series_countries = {} # id -> set(countries)
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
                         film_countries[fid] = set(film.get('countries', []))
                    else:
                         film_countries[fid] = set()

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
                         series_countries[fid] = set(item.get('countries', []))
                    else:
                         series_countries[fid] = set()

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
                        
                        # Data Mapping
                        new_data = {
                            'mubi_id': fid,
                            'title': item.get('title'),
                            'original_title': item.get('original_title'),
                            'genres': item.get('genres'),
                            'year': item.get('year'),
                            'duration': item.get('duration'),
                            'directors': [d['name'] for d in item.get('directors', [])],
                            'popularity': item.get('popularity'),
                            'average_rating_out_of_ten': item.get('average_rating_out_of_ten'),
                            'short_synopsis': item.get('short_synopsis'),
                            'default_editorial': item.get('default_editorial'),
                            'episode': item.get('episode'),
                            'series': item.get('series')
                        }

                        # --- DISTINGUISH SERIES VS FILM ---
                        is_series = False
                        if item.get('episode') is not None or item.get('series') is not None:
                            is_series = True
                        
                        if is_series:
                            scraped_sids_this_run.add(fid)
                            target_dict = all_series
                            target_countries_dict = series_countries
                        else:
                            scraped_fids_this_run.add(fid)
                            target_dict = all_films
                            target_countries_dict = film_countries

                        # Update or Create
                        if fid in target_dict:
                            target_dict[fid].update(new_data)
                        else:
                            target_dict[fid] = new_data
                            target_dict[fid]['countries'] = [] 
                        
                        # Init country set
                        if fid not in target_countries_dict:
                            target_countries_dict[fid] = set()

                        # Add country
                        target_countries_dict[fid].add(country)
                    
                    logger.info(f"Finished {country}. Total films: {len(all_films)}, Total series: {len(all_series)}")
                    
                except Exception as e:
                    logger.error(f"Failed to process {country}: {e}")
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
            film['countries'] = sorted(list(film_countries.get(fid, set())))
            final_films.append(film)

        final_series = []
        for sid, item in all_series.items():
            item['countries'] = sorted(list(series_countries.get(sid, set())))
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
                'total_count': len(final_series),
                'mode': mode
            },
            'items': final_series
        }

        with open(series_path, 'w', encoding='utf-8') as f:
            json.dump(output_series, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Successfully saved {len(final_series)} series episodes to {series_path}")

        if errors:
            logger.error(f"Scraper finished with {len(errors)} errors.")
            sys.exit(1)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Mubi Catalog Scraper")
    parser.add_argument('--mode', choices=['deep', 'shallow'], default='deep', help="Deep (calibration) or Shallow (fast) sync")
    parser.add_argument('--output', default='films.json', help="Output films file path")
    parser.add_argument('--series-output', default='series.json', help="Output series file path")
    parser.add_argument('--input', default=None, help="Input file path (required for shallow mode)")
    
    args = parser.parse_args()
    
    scraper = MubiScraper()
    scraper.run(output_path=args.output, series_path=args.series_output, mode=args.mode, input_path=args.input)
