import requests
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
    COUNTRIES = ['CH', 'DE', 'US', 'GB', 'FR', 'JP', 'TR', 'IN', 'CA', 'AU', 'BR', 'MX']

    def __init__(self):
        self.session = self._create_session()

    def _create_session(self):
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
                # Retry logic is handled by session, but if we fail here, we might want to panic or just skip
                break
        
        return films_data

    def run(self, output_path='films.json'):
        all_films = {} # id -> film_data
        film_countries = {} # id -> set(countries)

        for country in self.COUNTRIES:
            films = self.fetch_films_for_country(country)
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
                        # 'tmdb_id': film.get('tmdb_id'), # Removed per user request
                        # 'imdb_id': film.get('imdb_id'), # Removed per user request
                        # 'image': film.get('stills', {}).get('medium'), # Removed per user request 
                        'year': film.get('year'),
                        'duration': film.get('duration'),
                        'directors': [d['name'] for d in film.get('directors', [])]
                    }
                    film_countries[fid] = set()
                
                film_countries[fid].add(country)
            
            logger.info(f"Finished {country}. Total unique films so far: {len(all_films)}")
            time.sleep(2) # Delay between countries

        # Merge countries into film objects
        final_items = []
        for fid, film in all_films.items():
            film['countries'] = sorted(list(film_countries[fid]))
            final_items.append(film)

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

if __name__ == "__main__":
    scraper = MubiScraper()
    scraper.run()
