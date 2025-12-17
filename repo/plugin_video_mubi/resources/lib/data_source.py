# -*- coding: utf-8 -*-
import xbmc
import time
from typing import List, Dict, Any, Callable
from abc import ABC, abstractmethod

class FilmDataSource:
    """
    Interface for a film data source.
    Must return a list of raw film data dictionaries.
    """
    def get_films(self, *args, **kwargs) -> List[Dict[str, Any]]:
        raise NotImplementedError

class MubiApiDataSource(FilmDataSource):
    """
    Fetches film data directly from the Mubi API.
    Replicates the logic previously in mubi.py's get_all_films.
    """
    
    # Countries to sync catalogues from (ISO 3166-1 alpha-2 codes)
    SYNC_COUNTRIES = ['CH', 'DE', 'US', 'GB', 'FR', 'JP']

    def __init__(self, mubi_client):
        """
        :param mubi_client: Instance of the Mubi class to use for API calls
        """
        self.mubi = mubi_client

    def get_films(
        self, 
        playable_only: bool = True, 
        progress_callback=None, 
        countries: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieves all films from MUBI API by syncing across specified countries.
        
        :param playable_only: If True, only fetch currently playable films.
        :param progress_callback: Optional callback function to report progress.
        :param countries: List of ISO 3166-1 alpha-2 country codes to sync from.
        :return: List of raw film data dictionaries, merged and deduped.
        """
        # Default to client country or SYNC_COUNTRIES logic
        if countries is None:
            # We need to access settings via xbmcaddon, but to avoid circular imports or extra deps,
            # we can rely on mubi client if it had this info, but mubi client logic was:
            import xbmcaddon
            client_country = xbmcaddon.Addon().getSetting("client_country")
            if client_country:
                countries = [client_country.upper()]
                xbmc.log(f"Using client country from settings: {client_country}", xbmc.LOGINFO)
            else:
                countries = self.SYNC_COUNTRIES
                xbmc.log("No client country configured, using all SYNC_COUNTRIES", xbmc.LOGWARNING)

        # Statistics tracking
        country_stats = {}  # {country: {'total': n, 'unique_ids': set}}
        all_film_ids = set()  # All unique film IDs across all countries
        all_film_data = {}  # {film_id: film_data} - merged data from all countries
        film_country_map = {}  # {film_id: set of countries where available}
        total_pages_fetched = 0

        xbmc.log(f"=" * 60, xbmc.LOGINFO)
        xbmc.log(f"MULTI-COUNTRY CATALOGUE SYNC (DataSource)", xbmc.LOGINFO)
        xbmc.log(f"Countries to sync: {', '.join(countries)} ({len(countries)} total)", xbmc.LOGINFO)
        xbmc.log(f"=" * 60, xbmc.LOGINFO)

        # Fetch films from each country
        for country_idx, country in enumerate(countries, 1):
            xbmc.log("", xbmc.LOGINFO)
            xbmc.log(f"--- Country {country_idx}/{len(countries)}: {country} ---", xbmc.LOGINFO)

            # Track if user cancelled and running film count for this country
            user_cancelled = False
            running_new_films = [0]  # Use list to allow modification in closure

            # Create a page callback that updates progress after each page
            def create_page_callback(c_idx, c_code, c_total, base_count, new_count_ref):
                def page_callback(new_films_this_page):
                    nonlocal user_cancelled
                    new_count_ref[0] += new_films_this_page
                    if progress_callback and not user_cancelled:
                        try:
                            progress_callback(
                                current_films=base_count + new_count_ref[0],
                                total_films=0,
                                current_country=c_idx,
                                total_countries=c_total,
                                country_code=c_code
                            )
                        except Exception as e:
                            xbmc.log(f"Progress callback exception (user cancel): {e}", xbmc.LOGINFO)
                            user_cancelled = True
                            return False  # Signal to stop fetching
                    return True  # Continue
                return page_callback

            base_film_count = len(all_film_ids)
            page_cb = create_page_callback(
                country_idx, country, len(countries), base_film_count, running_new_films
            )

            # Initial progress update before fetching
            if progress_callback:
                try:
                    progress_callback(
                        current_films=len(all_film_ids),
                        total_films=0,
                        current_country=country_idx,
                        total_countries=len(countries),
                        country_code=country
                    )
                except Exception as e:
                    xbmc.log(f"Progress callback exception (user cancel): {e}", xbmc.LOGINFO)
                    return list(all_film_data.values())

            # Use the mubi client's internal helper to fetch pages
            # We assume mubi._fetch_films_for_country is still available or we move it here?
            # Ideally we move it here or make it public. 
            # For now, we will access it as protected member since Mubi class is passed in.
            film_ids, film_data, total_count, pages = self.mubi._fetch_films_for_country(
                country_code=country,
                playable_only=playable_only,
                page_callback=page_cb,
                global_film_ids=all_film_ids
            )

            # Check if user cancelled during fetch
            if user_cancelled:
                return list(all_film_data.values())

            # Track statistics
            country_stats[country] = {
                'total_reported': total_count,
                'unique_fetched': len(film_ids),
                'pages': pages,
                'film_ids': film_ids
            }
            total_pages_fetched += pages

            # Track which films are in which countries
            for film_id in film_ids:
                if film_id not in film_country_map:
                    film_country_map[film_id] = set()
                film_country_map[film_id].add(country)

            # Merge new films into all_film_data
            new_films_count = 0
            for film_id, data in film_data.items():
                if film_id not in all_film_data:
                    all_film_data[film_id] = data
                    all_film_ids.add(film_id)
                    new_films_count += 1
            
            xbmc.log(f"[{country}] Added {new_films_count} new unique films to merged catalogue", xbmc.LOGINFO)

        # Log comprehensive statistics
        self._log_stats(countries, total_pages_fetched, all_film_ids, country_stats, film_country_map)

        # Attach available countries to the raw data so the hydrator can use it
        output_list = []
        for film_id, data in all_film_data.items():
            # We inject the available countries into the raw data dictionary
            # This avoids changing the API structure but allows passing this info along
            data['__available_countries__'] = list(film_country_map.get(film_id, set()))
            output_list.append(data)
            
        return output_list

    def _log_stats(self, countries, total_pages_fetched, all_film_ids, country_stats, film_country_map):
        xbmc.log(f"", xbmc.LOGINFO)
        xbmc.log(f"=" * 60, xbmc.LOGINFO)
        xbmc.log(f"MULTI-COUNTRY SYNC STATISTICS", xbmc.LOGINFO)
        xbmc.log(f"=" * 60, xbmc.LOGINFO)
        xbmc.log(f"Countries synced: {len(countries)}", xbmc.LOGINFO)
        xbmc.log(f"Total pages fetched: {total_pages_fetched}", xbmc.LOGINFO)
        xbmc.log(f"Total unique films: {len(all_film_ids)}", xbmc.LOGINFO)
        xbmc.log(f"", xbmc.LOGINFO)

        # Per-country stats
        xbmc.log(f"--- Per-Country Breakdown ---", xbmc.LOGINFO)
        for country, stats in country_stats.items():
            xbmc.log(f"  {country}: {stats['unique_fetched']} films ({stats['pages']} pages)", xbmc.LOGINFO)

        # Films available in all countries vs country-specific
        films_in_all = set()
        films_country_exclusive = {}  # {country: set of exclusive film IDs}

        for film_id, available_countries in film_country_map.items():
            if len(available_countries) == len(countries):
                films_in_all.add(film_id)
            elif len(available_countries) == 1:
                country = list(available_countries)[0]
                if country not in films_country_exclusive:
                    films_country_exclusive[country] = set()
                films_country_exclusive[country].add(film_id)

        xbmc.log(f"", xbmc.LOGINFO)
        xbmc.log(f"--- Availability Analysis ---", xbmc.LOGINFO)
        xbmc.log(f"Films available in ALL {len(countries)} countries: {len(films_in_all)}", xbmc.LOGINFO)

        for country in countries:
            exclusive = films_country_exclusive.get(country, set())
            xbmc.log(f"Films EXCLUSIVE to {country}: {len(exclusive)}", xbmc.LOGINFO)

        xbmc.log(f"=" * 60, xbmc.LOGINFO)


class GithubDataSource(FilmDataSource):
    """
    Fetches film data from a pre-computed JSON file hosted on GitHub.
    URL: https://github.com/kubi2021/plugin.video.mubi/raw/database/v1/films.json.gz
    """

    GITHUB_URL = "https://github.com/kubi2021/plugin.video.mubi/raw/database/v1/films.json.gz"

    def get_films(self, *args, **kwargs) -> List[Dict[str, Any]]:
        """
        Downloads, decompresses, and parses films.json.gz from GitHub.
        """
        import requests
        from requests.adapters import HTTPAdapter
        from requests.packages.urllib3.util.retry import Retry
        import hashlib
        import gzip
        import json
        import io
        
        xbmc.log(f"Starting GitHub Sync from {self.GITHUB_URL}", xbmc.LOGINFO)
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session = requests.Session()
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        
        try:
            # 1. Download MD5 checksum
            md5_url = self.GITHUB_URL + ".md5"
            xbmc.log(f"Downloading MD5 checksum from {md5_url}", xbmc.LOGINFO)
            md5_response = session.get(md5_url, timeout=10)
            md5_response.raise_for_status()
            expected_md5 = md5_response.text.strip().split()[0] # Handle potentially "hash filename" format
            
            # 2. Download the file content
            xbmc.log(f"Downloading database from {self.GITHUB_URL}", xbmc.LOGINFO)
            response = session.get(self.GITHUB_URL, stream=True, timeout=30)
            response.raise_for_status()
            content = response.content

            # 3. Verify MD5
            calculated_md5 = hashlib.md5(content).hexdigest()
            if calculated_md5 != expected_md5:
                # Log detailed error for debugging
                xbmc.log(f"MD5 Mismatch! Expected: {expected_md5}, Calculated: {calculated_md5}", xbmc.LOGERROR)
                raise ValueError(f"MD5 verification failed. Integrity check failed for {self.GITHUB_URL}")
            
            xbmc.log("MD5 verification successful", xbmc.LOGINFO)

            # 4. Decompress and parse
            with gzip.GzipFile(fileobj=io.BytesIO(content)) as gz:
                data = json.load(gz)
                
            films_list = data.get("items", [])
            
            # Normalization: Map 'mubi_id' to 'id' if 'id' is missing
            # The plugin expects 'id'
            for film in films_list:
                if 'id' not in film and 'mubi_id' in film:
                    film['id'] = film['mubi_id']
                
                # Normalize 'directors' from list of strings to list of dicts
                # API returns [{'name': 'Director Name'}], GitHub JSON has ['Director Name']
                if 'directors' in film and isinstance(film['directors'], list):
                    if film['directors'] and isinstance(film['directors'][0], str):
                        film['directors'] = [{'name': d} for d in film['directors']]

            xbmc.log(f"Successfully downloaded and parsed {len(films_list)} films from GitHub", xbmc.LOGINFO)
            return films_list

        except requests.exceptions.RequestException as e:
            xbmc.log(f"Error downloading file from GitHub: {e}", xbmc.LOGERROR)
            raise
        except (gzip.BadGzipFile, json.JSONDecodeError) as e:
            xbmc.log(f"Error parsing GitHub data: {e}", xbmc.LOGERROR)
            raise
        except Exception as e:
            xbmc.log(f"Unexpected error in GithubDataSource: {e}", xbmc.LOGERROR)
            raise
        finally:
            session.close()

