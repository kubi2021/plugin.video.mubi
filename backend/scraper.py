import requests
import sys
import json
import time
import os
import gzip
import hashlib
from datetime import datetime
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MubiScraper:
    BASE_URL = 'https://api.mubi.com/v4'
    UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0'
    MIN_TOTAL_FILMS = 1000
    CRITICAL_COUNTRIES = ['US', 'GB', 'FR', 'DE', 'CH']
    MAX_MISSING_PERCENT = 5.0 # Max % of films allowed to have missing critical fields before failure

    def __init__(self):
        self.session = self._create_session()

    def _create_session(self):
        # ... (same as before) ...
        session = requests.Session()
        retries = Retry(
            total=5,
            backoff_factor=1,
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
        # ... (same as before) ...
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
                    logger.warning(f"Rate limited. Waiting {retry_after}s...")
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
                time.sleep(0.5) # Politeness delay

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
             # pct_missing_mubi_id check is implicit: if any missing mubi_id, it's a warning, but we might want to fail if MANY are missing
             # Users request: warning for single null mubi_id, but fail if widespread corruption?
             # Let's stick to the plan: Fail if >5% corrupt.
            
            if pct_missing_year > self.MAX_MISSING_PERCENT:
                validation_errors.append(f"Field Integrity: {pct_missing_year:.1f}% of films missing 'year' (max {self.MAX_MISSING_PERCENT}%)")
            
            # Critical fields (title/id) should probably have closer to 0 tolerance, but sticking to 5% for now or separate check
            if missing_title > 0:
                 pct_missing_title = (missing_title / total) * 100
                 if pct_missing_title > self.MAX_MISSING_PERCENT:
                     validation_errors.append(f"Field Integrity: {pct_missing_title:.1f}% of films missing 'title'")

        return validation_errors

    def run(self, output_path='films.json'):
        all_films = {} # id -> film_data
        film_countries = {} # id -> set(countries)
        errors = [] # Track errors per country

        for country in self.COUNTRIES:
            try:
                films = self.fetch_films_for_country(country)
                
                # Check for empty result if expected
                if not films:
                    logger.warning(f"No films found for {country}")
                    if country in self.CRITICAL_COUNTRIES:
                         msg = f"Critical country {country} returned 0 films."
                         logger.error(msg)
                         errors.append(msg)

                for film in films:
                    fid = film['id']
                    if fid not in all_films:
                        # Simplify film object to match schema
                        all_films[fid] = {
                            'mubi_id': fid,
                            'title': film.get('title'),
                            'original_title': film.get('original_title'),
                            'genres': film.get('genres'),
                            'countries': [], # Populated later
                            'year': film.get('year'),
                            'duration': film.get('duration'),
                            'directors': [d['name'] for d in film.get('directors', [])]
                        }
                        film_countries[fid] = set()
                    
                    film_countries[fid].add(country)
                
                logger.info(f"Finished {country}. Total unique films so far: {len(all_films)}")
            except Exception as e:
                logger.error(f"Failed to process {country}: {e}")
                errors.append(f"{country}: {str(e)}")
            
            time.sleep(2) # Delay between countries

        # Merge countries into film objects
        final_items = []
        for fid, film in all_films.items():
            film['countries'] = sorted(list(film_countries[fid]))
            final_items.append(film)

        # PANIC CHECK: If 0 films, this is a critical failure.
        if len(final_items) == 0:
            logger.error("CRITICAL: Scraper generated 0 films. Aborting.")
            sys.exit(1)

        # VALIDATE DATA
        data_errors = self.validate_data(final_items)
        if data_errors:
            logger.error(f"Data Validation Failed with {len(data_errors)} errors:")
            for err in data_errors:
                logger.error(f"  - {err}")
            errors.extend(data_errors)

        # Create output object
        output = {
            'meta': {
                'generated_at': datetime.utcnow().isoformat() + 'Z',
                'version': 1,
                'total_count': len(final_items),
            },
            'items': final_items
        }

        # Save to file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Successfully saved {len(final_items)} films to {output_path}")

        # NOTIFICATION ON ERRORS
        if errors:
            logger.error(f"Scraper finished with {len(errors)} errors:")
            for err in errors:
                logger.error(f"  - {err}")
            sys.exit(1)

if __name__ == "__main__":
    scraper = MubiScraper()
    scraper.run()
