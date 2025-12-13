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

    def detect_clusters(self, final_items, fuzzy_threshold=0.98):
        """
        Analyzes the full dataset to find countries with identical or highly similar catalogues.
        Uses a fuzzy matching approach (Jaccard similarity >= threshold OR subset relationship).
        Returns a dictionary representing the clusters.
        """
        logger.info(f"Analyzing data for clusters (Fuzzy Threshold: {fuzzy_threshold})...")
        country_films = {} # country_code -> set of film IDs

        # 1. Build country -> film_ids map
        for film in final_items:
            fid = film['mubi_id']
            for country in film['countries']:
                if country not in country_films:
                    country_films[country] = set()
                country_films[country].add(fid)

        # 2. Sort potential leaders by catalogue size (descending)
        sorted_countries = sorted(country_films.keys(), key=lambda c: len(country_films[c]), reverse=True)
        
        assigned = set()
        clusters = []
        
        for leader in sorted_countries:
            if leader in assigned:
                continue
                
            cluster_members = [leader]
            leader_set = country_films[leader]
            assigned.add(leader)
            
            # Greedy search for members
            for candidate in sorted_countries:
                if candidate in assigned:
                    continue
                
                candidate_set = country_films[candidate]
                
                # Check similarity
                intersection = len(leader_set & candidate_set)
                union = len(leader_set | candidate_set)
                jaccard = intersection / union if union > 0 else 0
                
                is_subset = candidate_set.issubset(leader_set)
                
                if jaccard >= fuzzy_threshold or is_subset:
                     cluster_members.append(candidate)
                     assigned.add(candidate)
            
            cluster = {
                "leader": leader,
                "members": sorted(cluster_members),
                "count": len(leader_set),
                "hash": hashlib.md5(",".join(map(str, sorted(list(leader_set)))).encode('utf-8')).hexdigest()
            }
            clusters.append(cluster)
        
        # Sort clusters by member count (descending)
        clusters.sort(key=lambda x: len(x['members']), reverse=True)
        
        logger.info(f"Detected {len(clusters)} unique clusters across {len(country_films)} countries.")
        return clusters

    def run(self, output_path='films.json', mode='deep', clusters_path='clusters.json'):
        all_films = {} # id -> film_data
        film_countries = {} # id -> set(countries)
        errors = [] # Track errors per country
        
        target_countries = []
        cluster_map = {} # leader -> list of members (only for shallow mode)

        if mode == 'deep':
            logger.info("Starting DEEP sync (Calibration Mode)...")
            target_countries = self.COUNTRIES
        elif mode == 'shallow':
            logger.info("Starting SHALLOW sync (Fast Mode)...")
            if not os.path.exists(clusters_path):
                logger.error(f"Clusters file {clusters_path} not found. Cannot run shallow sync.")
                sys.exit(1)
            
            with open(clusters_path, 'r') as f:
                clusters = json.load(f)
            
            for c in clusters:
                target_countries.append(c['leader'])
                cluster_map[c['leader']] = c['members']
            
            logger.info(f"Loaded {len(clusters)} clusters. Will scrape {len(target_countries)} leaders.")

        # --- SCRAPING LOOP (PARALLEL) ---
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as executor:
            # Map countries to futures
            future_to_country = {executor.submit(self.fetch_films_for_country, country): country for country in target_countries}
            
            for future in concurrent.futures.as_completed(future_to_country):
                country = future_to_country[future]
                
                try:
                    films = future.result()
                    
                    # Check for empty result if expected
                    if not films:
                        logger.warning(f"No films found for {country}")
                        if country in self.CRITICAL_COUNTRIES:
                                msg = f"Critical country {country} returned 0 films."
                                logger.error(msg)
                                errors.append(msg)

                    # Determine which countries get credit for these films
                    countries_to_assign = [country]
                    if mode == 'shallow' and country in cluster_map:
                        countries_to_assign = cluster_map[country]

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
                        
                        # Assign to ALL members of the cluster
                        for member in countries_to_assign:
                            film_countries[fid].add(member)
                    
                    logger.info(f"Finished {country} (Cluster size: {len(countries_to_assign)}). Unique films: {len(all_films)}")
                    
                except Exception as e:
                    logger.error(f"Failed to process {country}: {e}")
                    errors.append(f"{country}: {str(e)}")

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

        # CLUSTER CALIBRATION (Deep Mode Only)
        if mode == 'deep' and not errors:
            clusters = self.detect_clusters(final_items)
            with open(clusters_path, 'w', encoding='utf-8') as f:
                json.dump(clusters, f, indent=2)
            logger.info(f"Saved cluster map to {clusters_path}")

        # Create output object
        output = {
            'meta': {
                'generated_at': datetime.utcnow().isoformat() + 'Z',
                'version': 1,
                'total_count': len(final_items),
                'mode': mode
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
    import argparse
    parser = argparse.ArgumentParser(description="Mubi Catalog Scraper")
    parser.add_argument('--mode', choices=['deep', 'shallow'], default='deep', help="Deep (calibration) or Shallow (fast) sync")
    parser.add_argument('--output', default='films.json', help="Output file path")
    parser.add_argument('--clusters', default='clusters.json', help="Clusters map file path")
    
    args = parser.parse_args()
    
    scraper = MubiScraper()
    scraper.run(output_path=args.output, mode=args.mode, clusters_path=args.clusters)
