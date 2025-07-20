# -*- coding: utf-8 -*-

# This code defines a Python class `Mubi` that interacts with the Mubi API 
# to retrieve information about films available on the Mubi streaming platform.
# It includes functionality for user login, retrieving lists of films 
# (either daily film programming or film groups), and fetching metadata for individual films.
# The class uses HTTP requests to communicate with the API, processes the responses, 
# and organizes the film data into named tuples for easy access.


import datetime
import dateutil.parser
import requests
import json
import hashlib
import base64
from collections import namedtuple
import xbmc
import re
import random
from urllib.parse import urljoin
from urllib.parse import urlencode
import time
import threading
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from .metadata import Metadata
from .film import Film
from .library import Library
from .playback import generate_drm_license_key


class Mubi:

    # Class-level variables for rate limiting
    _lock = threading.Lock()
    _last_call_time = 0
    _calls_made = 0
    _call_history = []

    def __init__(self, session_manager):
        """
        Initialize the Mubi class with the session manager.

        :param session_manager: Instance of SessionManager to handle session data
        :type session_manager: SessionManager
        """
        self.apiURL = 'https://api.mubi.com/'
        self.UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0'
        self.session_manager = session_manager  # Use session manager for session-related data
        self.library = Library()  # Initialize the Library

    def _sanitize_headers_for_logging(self, headers):
        """
        Sanitize headers for safe logging by masking sensitive information.

        :param headers: Dictionary of headers to sanitize
        :return: Dictionary with sensitive headers masked
        """
        if not headers:
            return headers

        # List of sensitive header patterns (case-insensitive)
        sensitive_patterns = [
            'authorization', 'api-key', 'api_key', 'x-api-key', 'auth-token', 'x-auth-token',
            'cookie', 'set-cookie', 'csrf-token', 'x-csrf-token', 'access-token', 'x-access-token',
            'token', 'bearer', 'basic', 'digest'
        ]

        sanitized = {}
        for key, value in headers.items():
            key_lower = key.lower()
            is_sensitive = any(pattern in key_lower for pattern in sensitive_patterns)
            if is_sensitive:
                sanitized[key] = '***REDACTED***'
            else:
                sanitized[key] = value

        return sanitized

    def _sanitize_params_for_logging(self, params):
        """
        Sanitize URL parameters for safe logging by masking sensitive information.

        :param params: Dictionary of parameters to sanitize
        :return: Dictionary with sensitive parameters masked
        """
        if not params:
            return params

        # List of sensitive parameter names (case-insensitive)
        sensitive_params = {
            'api_key', 'token', 'password', 'secret', 'auth', 'authorization',
            'access_token', 'refresh_token', 'session_id', 'csrf_token'
        }

        sanitized = {}
        for key, value in params.items():
            if key.lower() in sensitive_params:
                sanitized[key] = '***REDACTED***'
            else:
                sanitized[key] = value

        return sanitized

    def _sanitize_json_for_logging(self, json_data):
        """
        Sanitize JSON data for safe logging by masking sensitive information.

        :param json_data: Dictionary of JSON data to sanitize
        :return: Dictionary with sensitive fields masked
        """
        if not json_data:
            return json_data

        # List of sensitive field names (case-insensitive)
        sensitive_fields = {
            'password', 'api_key', 'token', 'secret', 'auth', 'authorization',
            'access_token', 'refresh_token', 'session_id', 'csrf_token'
        }

        sanitized = {}
        for key, value in json_data.items():
            if key.lower() in sensitive_fields:
                sanitized[key] = '***REDACTED***'
            else:
                sanitized[key] = value

        return sanitized

    def _make_api_call(self, method, endpoint=None, full_url=None, headers=None, params=None, data=None, json=None):
        url = full_url if full_url else f"{self.apiURL}{endpoint}"

        # Ensure headers are not None and set Accept-Encoding to gzip
        if headers is None:
            headers = {}
        headers.setdefault('Accept-Encoding', 'gzip')

        # Log API call details
        xbmc.log(f"Making API call: {method} {url}", xbmc.LOGDEBUG)
        xbmc.log(f"Headers: {headers}", xbmc.LOGDEBUG)
        
        # Log parameters if they exist
        if params:
            xbmc.log(f"Parameters: {params}", xbmc.LOGDEBUG)
        
        # Log JSON body if it exists
        if json:
            xbmc.log(f"JSON: {json}", xbmc.LOGDEBUG)

        # Rate limiting: Max 60 calls per minute
        with self._lock:
            current_time = time.time()
            self._call_history = [t for t in self._call_history if current_time - t < 60]
            if len(self._call_history) >= 60:
                wait_time = 60 - (current_time - self._call_history[0])
                xbmc.log(f"Rate limit reached. Sleeping for {wait_time:.2f} seconds.", xbmc.LOGINFO)
                time.sleep(wait_time)
                self._call_history = [t for t in self._call_history if current_time - t < 60]

            self._call_history.append(time.time())

        # Set up retries with exponential backoff for transient errors
        session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET", "POST", "DELETE", "PUT", "PATCH"]
        )
        adapter = HTTPAdapter(max_retries=retries)
        session.mount('https://', adapter)
        session.mount('http://', adapter)

        try:
            # Log the final request details (including params)
            xbmc.log(f"Sending request: {method} {url} with params: {params}", xbmc.LOGDEBUG)

            response = session.request(
                method,
                url,
                headers=headers,
                params=params,  # Pass query parameters explicitly here
                data=data,
                json=json,
                timeout=10  # Set a reasonable timeout
            )

            # Log the response status
            xbmc.log(f"Response status code: {response.status_code}", xbmc.LOGDEBUG)

            # Raise an HTTPError for bad responses (4xx and 5xx)
            response.raise_for_status()

            # Log full response content safely
            response_content = response.text
            # xbmc.log(f"Full response content: {response_content}", xbmc.LOGDEBUG)

            return response

        except requests.exceptions.HTTPError as http_err:
            xbmc.log(f"HTTP error occurred: {http_err}", xbmc.LOGERROR)
            if response is not None:
                xbmc.log(f"Response Headers: {response.headers}", xbmc.LOGERROR)
                xbmc.log(f"Response Content: {response.text}", xbmc.LOGERROR)
            return None

        except requests.exceptions.RequestException as req_err:
            xbmc.log(f"Request exception occurred: {req_err}", xbmc.LOGERROR)
            return None

        except Exception as err:
            xbmc.log(f"An unexpected error occurred: {err}", xbmc.LOGERROR)
            return None

        finally:
            session.close()
            xbmc.log("Session closed after API call.", xbmc.LOGDEBUG)




    def get_cli_country(self):
        """
        Retrieves the client's country from Mubi's website.

        :return: Client country code.
        :rtype: str
        """
        headers = {'User-Agent': self.UA}
        response = self._make_api_call('GET', full_url='https://mubi.com/', headers=headers)
        if response:
            resp_text = response.text
            country = re.findall(r'"Client-Country":"([^"]+?)"', resp_text)
            cli_country = country[0] if country else 'PL'
            xbmc.log(f"Client country detected: {cli_country}", xbmc.LOGINFO)
            return cli_country
        else:
            xbmc.log("Failed to detect client country, defaulting to: PL", xbmc.LOGINFO)
            return 'PL'

    def get_cli_language(self):
        """
        Retrieves the client's preferred language from Mubi's website.

        :return: Client preferred language code (e.g., 'en' for English).
        :rtype: str
        """
        headers = {'User-Agent': self.UA}
        response = self._make_api_call('GET', full_url='https://mubi.com/', headers=headers)
        if response:
            resp_text = response.text
            language = re.findall(r'"Accept-Language":"([^"]+?)"', resp_text)
            accept_language = language[0] if language else 'en'
            return accept_language
        else:
            return 'en'

    def hea_atv_gen(self):
        """
        Generates headers required for API requests without authorization in a web-based context.

        :return: Headers dictionary.
        :rtype: dict
        """
        base_url = 'https://mubi.com'  # This is used for the Referer and Origin headers

        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0',
            'Authorization': f'Bearer {self.session_manager.token}',  # Authorization token from session
            'Anonymous_user_id': self.session_manager.device_id,  # Use session manager for device ID
            'Client': 'web',
            'Client-Accept-Audio-Codecs': 'aac,eac3,ac3,dts',  # Added Enhanced AC-3 and other surround sound codecs
            'Client-Accept-Video-Codecs': 'h265,vp9,h264',  # Include support for video codecs
            'Client-Country': self.session_manager.client_country,  # Client country from session
            'accept-language' : self.session_manager.client_language,
            'Referer': base_url,  # Add Referer for web-based requests
            'Origin': base_url,  # Add Origin for web-based requests
            'Accept-Encoding': 'gzip',
            'accept': 'application/json'
        }


    def hea_atv_auth(self):
        """
        Generates headers required for API requests with authorization.

        :return: Headers dictionary with Authorization token.
        :rtype: dict
        """
        headers = self.hea_atv_gen()
        token = self.session_manager.token  # Use session manager
        if not token:
            xbmc.log("No token found", xbmc.LOGERROR)
        headers['Authorization'] = f'Bearer {token}'
        return headers

    def hea_gen(self):
        """
        Generates web headers required for API requests with authorization (similar to heaGen() in inspiration code).
        This is used for endpoints that expect web client headers rather than Android TV headers.

        :return: Headers dictionary with web client headers and Authorization token.
        :rtype: dict
        """
        base_url = 'https://mubi.com'
        token = self.session_manager.token
        if not token:
            xbmc.log("No token found for web headers", xbmc.LOGERROR)

        return {
            'Referer': base_url,
            'Origin': base_url,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0',
            'Authorization': f'Bearer {token}',
            'Anonymous_user_id': self.session_manager.device_id,
            'Client': 'web',
            'Client-Accept-Audio-Codecs': 'eac3,aac',
            'Client-Accept-Video-Codecs': 'h265,vp9,h264',
            'Client-Country': self.session_manager.client_country,
            'accept-language': self.get_cli_language()
        }

    def get_link_code(self):
        """
        Calls the Mubi API to generate a link code and an authentication token for the login process.

        :return: Dictionary with 'auth_token' and 'link_code'.
        :rtype: dict
        """
        response = self._make_api_call('GET', 'v4/link_code', headers=self.hea_atv_gen())
        if response:
            return response.json()
        else:
            return None

    def authenticate(self, auth_token):
        """
        Authenticates the user with the provided auth_token.

        :param auth_token: Authentication token from get_link_code().
        :type auth_token: str
        :return: Authentication response data if successful, None otherwise.
        :rtype: dict or None
        """
        data = {'auth_token': auth_token}
        response = self._make_api_call(
            'POST', 'v4/authenticate', headers=self.hea_atv_gen(), json=data
        )

        if response:
            response_data = response.json()

            # Check if token and user data are present in the response
            if 'token' in response_data and 'user' in response_data:
                token = response_data['token']
                user_id = response_data['user']['id']  # Extract user_id from the response

                # Set the token and user_id in the session
                self.session_manager.set_logged_in(token, str(user_id))  # Store both token and user_id

                xbmc.log("User authenticated successfully", xbmc.LOGDEBUG)
                return response_data  # Return the full response data
            else:
                xbmc.log(f"Authentication failed: {response_data.get('message', 'No error message provided')}", xbmc.LOGERROR)
        else:
            xbmc.log("Authentication failed: No response from server", xbmc.LOGERROR)

        return None  # Return None if authentication failed



    def log_out(self):
        """
        Logs the user out by invalidating the session.

        :return: True if logout was successful, False otherwise.
        :rtype: bool
        """
        response = self._make_api_call('DELETE', 'v4/sessions', headers=self.hea_atv_auth())
        if response and response.status_code == 200:
            return True
        else:
            return False


    def get_film_groups(self):
        """
        Retrieves a list of all film groups (collections) from the MUBI API V4, handling pagination.
        Manually adds an additional entry for "Now Showing".

        :return: A list of all film group categories across all pages.
        :rtype: list
        """
        endpoint = 'v4/browse/film_groups'
        headers = self.hea_atv_gen()  # Use headers without authorization
        categories = []
        page = 1  # Start from the first page

        while True:
            params = {'page': page}
            response = self._make_api_call('GET', endpoint=endpoint, headers=headers, params=params)

            if response:
                data = response.json()
                film_groups = data.get('film_groups', [])
                meta = data.get('meta', {})

                for group in film_groups:
                    image_data = group.get('image', '')
                    if isinstance(image_data, dict):
                        image_url = image_data.get('medium', '')
                    elif isinstance(image_data, str):
                        image_url = image_data
                    else:
                        image_url = ''

                    category = {
                        'title': group.get('full_title', ''),
                        'id': group.get('id', ''),
                        'description': group.get('description', ''),
                        'image': image_url,
                    }
                    categories.append(category)

                # Check if there's a next page
                next_page = meta.get('next_page')
                if next_page:
                    page = next_page
                else:
                    break  # No more pages to fetch
            else:
                xbmc.log(f"Failed to retrieve film groups on page {page}", xbmc.LOGERROR)
                break  # Exit the loop on failure

        xbmc.log("Manually added 'Now Showing' category", xbmc.LOGDEBUG)

        return categories


    def get_all_films(self, playable_only=True):
        """
        Retrieves all films directly from the MUBI API V4 /browse/films endpoint, handling pagination.
        This is more efficient than fetching films category by category.

        :param playable_only: If True, only fetch currently playable films. If False, fetch entire catalog.
        :return: Library instance with all films.
        :rtype: Library
        """
        try:
            endpoint = 'v4/browse/films'
            headers = self.hea_gen()  # Use web headers for best results
            all_films_library = Library()
            page = 1
            total_films_fetched = 0
            total_series_skipped = 0
            total_pages_fetched = 0

            xbmc.log(f"Starting to fetch all films from {endpoint} using sort=title (filtering out series)", xbmc.LOGINFO)

            while True:
                # Use sort=title to get the full catalog
                params = {
                    'page': page,
                    'sort': 'title',  # Sort parameter is required to get full catalog
                }

                if playable_only:
                    params['playable'] = 'true'
                    xbmc.log(f"Fetching page {page} with playable filter and sort=title", xbmc.LOGINFO)
                else:
                    xbmc.log(f"Fetching page {page} without playable filter, sort=title", xbmc.LOGDEBUG)

                xbmc.log(f"Fetching page {page} with params: {params}", xbmc.LOGDEBUG)
                response = self._make_api_call('GET', endpoint=endpoint, headers=headers, params=params)

                if response:
                    # Check response status
                    xbmc.log(f"Page {page}: Response status code: {response.status_code}", xbmc.LOGDEBUG)

                    try:
                        data = response.json()
                    except Exception as e:
                        xbmc.log(f"Page {page}: Failed to parse JSON response: {e}", xbmc.LOGERROR)
                        break

                    films = data.get('films', [])
                    meta = data.get('meta', {})
                    total_pages_fetched += 1

                    # Log the complete API response for the first few pages to understand structure
                    if total_pages_fetched <= 2:  # Only log first 2 pages to avoid spam
                        xbmc.log(f"DEBUG - Page {page} COMPLETE API RESPONSE: {data}", xbmc.LOGDEBUG)

                    # Detailed logging for debugging pagination
                    xbmc.log(f"Page {page}: Received {len(films)} films", xbmc.LOGINFO)
                    xbmc.log(f"Page {page}: Complete meta object: {meta}", xbmc.LOGINFO)
                    xbmc.log(f"Page {page}: Complete response keys: {list(data.keys())}", xbmc.LOGINFO)

                    # Check if there are any other pagination-related fields
                    for key, value in data.items():
                        if 'page' in key.lower() or 'total' in key.lower() or 'count' in key.lower():
                            xbmc.log(f"Page {page}: Found pagination field {key}: {value}", xbmc.LOGINFO)

                    # Check if there are any error messages in the response
                    if 'error' in data or 'message' in data:
                        xbmc.log(f"Page {page}: API returned error: {data}", xbmc.LOGERROR)

                    # Process each film and add debug logging
                    for idx, film_data in enumerate(films):
                        # Debug log: Show the complete film response structure for documentation
                        if total_films_fetched < 5:  # Log first 5 films for comprehensive documentation
                            xbmc.log(f"=== FILM {total_films_fetched + 1} COMPLETE RESPONSE ===", xbmc.LOGDEBUG)
                            xbmc.log(f"Film ID: {film_data.get('id', 'N/A')}", xbmc.LOGDEBUG)
                            xbmc.log(f"Film Title: {film_data.get('title', 'N/A')}", xbmc.LOGDEBUG)
                            xbmc.log(f"Complete Film Object: {film_data}", xbmc.LOGDEBUG)
                            xbmc.log(f"=== END FILM {total_films_fetched + 1} ===", xbmc.LOGDEBUG)

                            # Also log the top-level keys for structure analysis
                            film_keys = list(film_data.keys()) if isinstance(film_data, dict) else []
                            xbmc.log(f"Film {total_films_fetched + 1} top-level keys: {film_keys}", xbmc.LOGDEBUG)

                            # Log specific nested objects that might be important
                            if 'consumable' in film_data:
                                xbmc.log(f"Film {total_films_fetched + 1} consumable object: {film_data['consumable']}", xbmc.LOGDEBUG)
                            if 'directors' in film_data:
                                xbmc.log(f"Film {total_films_fetched + 1} directors: {film_data['directors']}", xbmc.LOGDEBUG)
                            if 'genres' in film_data:
                                xbmc.log(f"Film {total_films_fetched + 1} genres: {film_data['genres']}", xbmc.LOGDEBUG)
                            if 'cast' in film_data:
                                xbmc.log(f"Film {total_films_fetched + 1} cast: {film_data['cast']}", xbmc.LOGDEBUG)
                            if 'countries' in film_data or 'historic_countries' in film_data:
                                countries = film_data.get('countries', film_data.get('historic_countries', []))
                                xbmc.log(f"Film {total_films_fetched + 1} countries: {countries}", xbmc.LOGDEBUG)

                        # Create a wrapper structure similar to category-based approach
                        # The direct films endpoint returns films directly, not wrapped in 'film' key
                        film_wrapper = {'film': film_data}

                        # Use "All Films" as the primary category since we don't have collection info
                        # The direct API doesn't provide collection/category information
                        category_name = "All Films"

                        film = self.get_film_metadata(film_wrapper)
                        if film:
                            # Debug: Log what fields we're using vs what's available
                            if total_films_fetched < 3:
                                used_fields = ['id', 'title', 'original_title', 'year', 'duration', 'short_synopsis',
                                             'directors', 'genres', 'historic_countries', 'average_rating',
                                             'number_of_ratings', 'still_url', 'trailer_url', 'web_url', 'consumable']
                                available_fields = list(film_data.keys())
                                unused_fields = [field for field in available_fields if field not in used_fields]
                                xbmc.log(f"Film {total_films_fetched + 1} - Fields we use: {used_fields}", xbmc.LOGDEBUG)
                                xbmc.log(f"Film {total_films_fetched + 1} - Available but unused fields: {unused_fields}", xbmc.LOGDEBUG)

                            all_films_library.add_film(film)
                            total_films_fetched += 1

                    # Check if there's a next page
                    next_page = meta.get('next_page')
                    xbmc.log(f"Page {page} processed. Next page: {next_page}. Total films so far: {total_films_fetched}", xbmc.LOGINFO)

                    if next_page:
                        page = next_page
                    else:
                        xbmc.log(f"No more pages. Finished fetching all films.", xbmc.LOGINFO)
                        break  # No more pages to fetch
                else:
                    xbmc.log(f"Failed to retrieve films on page {page}", xbmc.LOGERROR)
                    break  # Exit the loop on failure

                # Safety check to prevent infinite loops
                if total_pages_fetched > 100:  # Reasonable upper limit
                    xbmc.log(f"Safety limit reached: fetched {total_pages_fetched} pages. Stopping.", xbmc.LOGWARNING)
                    break

            xbmc.log(f"Successfully fetched {total_films_fetched} films from {total_pages_fetched} pages using direct API approach", xbmc.LOGINFO)
            return all_films_library

        except Exception as e:
            xbmc.log(f"Error retrieving all films directly: {e}", xbmc.LOGERROR)
            return Library()  # Return empty library on error


    def get_watch_list(self):
        """
        Retrieves and adds films to the library from the watchlist

        :return: Library instance with films.
        """
        try:
            # Retrieve films from the watchlist
            films_data = self.get_films_in_watchlist()

            # Process and add each film to the library
            for film_item in films_data:
                this_film = film_item.get('film')
                consumable = this_film.get('consumable')
                if consumable != None:
                    film = self.get_film_metadata(film_item)
                    if film:
                        self.library.add_film(film)

            xbmc.log(f"Fetched {len(self.library)} available films from the watchlist", xbmc.LOGINFO)
        except Exception as e:
            xbmc.log(f"Error retrieving films from the watchlist: {e}", xbmc.LOGERROR)

        return self.library




    def get_films_in_watchlist(self):
        """
        Retrieves films from the watchlist using the MUBI API V3.

        :return: List of film group items (films).
        :rtype: list
        """
        # The wishlist API does not seem to support paging, so we call it two times:
        # First time with per_page=0, which will just return the total_count
        # Second time, with per_page=<total_count>, to ensure we retrieve all items
        response = self._call_wishlist_api(0)
        data = response.json()
        meta = data.get('meta')
        total_count = meta.get('total_count')
        
        all_film_items = []
        response = self._call_wishlist_api(total_count)
        data = response.json()
        wishes = data.get('wishes', [])
        all_film_items.extend(wishes)

        return all_film_items




    def _call_wishlist_api(self, per_page: int):
        """
        Retrieves films from the wishlist using the MUBI API V4.

        :return: result
        :rtype: json
        """
        endpoint = 'v4/wishes'
        headers = self.hea_atv_auth()
        params = {
            'user_id': self.session_manager.user_id,
            'per_page': per_page
        }

        response = self._make_api_call('GET', endpoint=endpoint, headers=headers, params=params)
        if not response:
            xbmc.log(f"Failed to retrieve films from your watchlist", xbmc.LOGERROR)
        return response



    def get_film_list(self, id: int, category_name: str):
        """
        Retrieves and adds films to the library based on the category id.
        Note: category_name is kept for compatibility but no longer used for tagging.

        :param id: ID of the film group (category).
        :param category_name: Name of the category (for logging only).
        :return: Library instance with films.
        """
        try:
            # Retrieve films from the film group with the given ID
            films_data = self.get_films_in_category_json(id)

            # Process and add each film to the library
            for film_item in films_data:
                film = self.get_film_metadata(film_item)
                if film:
                    self.library.add_film(film)

            xbmc.log(f"Fetched {len(self.library)} films for category '{category_name}'", xbmc.LOGINFO)
        except Exception as e:
            xbmc.log(f"Error fetching films for category '{category_name}': {e}", xbmc.LOGERROR)

        return self.library




    def get_films_in_category_json(self, category_id):
        """
        Retrieves films within a specific film group (collection) using the MUBI API V4.

        :param category_id: ID of the film group (category).
        :return: List of film group items (films).
        :rtype: list
        """
        all_film_items = []
        page = 1
        per_page = 20

        while True:
            endpoint = f'v4/film_groups/{category_id}/film_group_items'
            headers = self.hea_atv_auth()
            params = {
                'page': page,
                'per_page': per_page,
                'include_upcoming': 'true'  # Include upcoming films if needed
            }

            response = self._make_api_call('GET', endpoint=endpoint, headers=headers, params=params)
            if response:
                data = response.json()
                film_group_items = data.get('film_group_items', [])
                all_film_items.extend(film_group_items)

                meta = data.get('meta', {})
                next_page = meta.get('next_page')
                if next_page:
                    page = next_page
                else:
                    break
            else:
                xbmc.log(f"Failed to retrieve film group items for category {category_id}", xbmc.LOGERROR)
                break

        return all_film_items




    def get_film_metadata(self, film_data: dict) -> Film:
        """
        Extracts and returns film metadata from the API data.
        Filters out series content to only process actual films.

        :param film_data: Dictionary containing film data
        :return: Film instance or None if not valid or is a series
        """
        try:
            film_info = film_data.get('film', {})
            if not film_info:
                return None

            # Check if this is a series (like inspiration code does)
            is_series = False
            if 'series' in film_info:
                if film_info['series'] is not None:
                    is_series = True
                    xbmc.log(f"Skipping series content: {film_info.get('title', 'Unknown')}", xbmc.LOGDEBUG)
                    return None  # Skip series content for film sync

            available_at = film_info.get('consumable', {}).get('available_at')
            expires_at = film_info.get('consumable', {}).get('expires_at')
            if available_at and expires_at:
                available_at_dt = dateutil.parser.parse(available_at)
                expires_at_dt = dateutil.parser.parse(expires_at)
                now = datetime.datetime.now(tz=available_at_dt.tzinfo)
                if available_at_dt > now or expires_at_dt < now:
                    return None

            metadata = Metadata(
                title=film_info.get('title', ''),
                director=[d['name'] for d in film_info.get('directors', [])],
                year=film_info.get('year', ''),
                duration=film_info.get('duration', 0),
                country=film_info.get('historic_countries', []),
                plot=film_info.get('short_synopsis', ''),
                plotoutline=film_info.get('short_synopsis', ''),
                genre=film_info.get('genres', []),
                originaltitle=film_info.get('original_title', ''),
                rating=film_info.get('average_rating', 0),
                votes=film_info.get('number_of_ratings', 0),
                dateadded=datetime.date.today().strftime('%Y-%m-%d'),
                trailer=film_info.get('trailer_url', ''),
                image=film_info.get('still_url', '')
            )

            return Film(
                mubi_id=film_info.get('id'),
                title=film_info.get('title', ''),
                artwork=film_info.get('still_url', ''),
                web_url=film_info.get('web_url', ''),
                metadata=metadata
            )
        except Exception as e:
            xbmc.log(f"Error parsing film metadata: {e}", xbmc.LOGERROR)
            return None






    def get_secure_stream_info(self, vid: str) -> dict:
        try:
            # Step 1: Attempt to check film viewing availability with parental lock
            viewing_url = f"{self.apiURL}v4/films/{vid}/viewing"
            params = {'parental_lock_enabled': 'true'}  # Add as query parameter
            viewing_response = self._make_api_call("POST", full_url=viewing_url, headers=self.hea_atv_auth(), params=params)

            # If the parental lock check fails, log a warning but continue
            if not viewing_response or viewing_response.status_code != 200:
                xbmc.log(f"Parental lock check failed, ignoring. Error: {viewing_response.text if viewing_response else 'No response'}", xbmc.LOGWARNING)

            # Step 2: Handle Pre-roll (if any)
            preroll_url = f"{self.apiURL}v4/prerolls/viewings"
            preroll_data = {'viewing_film_id': int(vid)}
            preroll_response = self._make_api_call("POST", full_url=preroll_url, headers=self.hea_atv_auth(), json=preroll_data)

            # Pre-roll is optional, so even if it fails, we can continue
            if preroll_response and preroll_response.status_code != 200:
                xbmc.log(f"Pre-roll processing failed: {preroll_response.text}", xbmc.LOGDEBUG)

            # Step 3: Fetch the secure video URL
            secure_url = f"{self.apiURL}v4/films/{vid}/viewing/secure_url"
            secure_response = self._make_api_call("GET", full_url=secure_url, headers=self.hea_atv_auth())

            # Ensure we keep the entire secure response data intact
            secure_data = secure_response.json() if secure_response and secure_response.status_code == 200 else None
            if not secure_data or "url" not in secure_data:
                message = secure_data.get('user_message', 'Unable to retrieve secure URL') if secure_data else 'Unknown error'
                xbmc.log(f"Error retrieving secure stream info: {message}", xbmc.LOGERROR)
                return {'error': message}

            # Log the complete raw response from Mubi for audio analysis
            xbmc.log(f"=== RAW MUBI SECURE URL RESPONSE ===", xbmc.LOGINFO)
            xbmc.log(f"Complete secure_data from Mubi API: {secure_data}", xbmc.LOGINFO)
            xbmc.log(f"=== END RAW RESPONSE ===", xbmc.LOGINFO)

            # Step 4: Extract stream URL and DRM info (keep all URLs and any additional metadata)
            stream_info = {
                'stream_url': secure_data['url'],  # The primary stream URL
                'urls': secure_data.get('urls', []),  # Additional URLs to select from
                'license_key': generate_drm_license_key(self.session_manager.token, self.session_manager.user_id)
            }

            # Preserve any additional metadata that might contain audio information
            for key, value in secure_data.items():
                if key not in ['url', 'urls']:
                    stream_info[key] = value

            return stream_info

        except Exception as e:
            xbmc.log(f"Error retrieving secure stream info: {e}", xbmc.LOGERROR)
            return {'error': 'An unexpected error occurred while retrieving stream info'}


    def select_best_stream(self, stream_info):
        """
        Selects the best stream URL from the available options.

        :param stream_info: Dictionary containing stream URLs and types
        :return: Best stream URL or None
        """
        try:
            # Log the complete stream info for debugging
            xbmc.log(f"=== MUBI STREAM ANALYSIS ===", xbmc.LOGINFO)
            xbmc.log(f"Complete stream_info received: {stream_info}", xbmc.LOGINFO)

            # Log available streams with detailed information
            xbmc.log(f"Number of available streams: {len(stream_info.get('urls', []))}", xbmc.LOGINFO)

            for i, stream in enumerate(stream_info.get('urls', [])):
                xbmc.log(f"Stream {i+1}:", xbmc.LOGINFO)
                xbmc.log(f"  - URL: {stream.get('src', 'N/A')}", xbmc.LOGINFO)
                xbmc.log(f"  - Content Type: {stream.get('content_type', 'N/A')}", xbmc.LOGINFO)

                # Log all available keys in the stream object
                for key, value in stream.items():
                    if key not in ['src', 'content_type']:
                        xbmc.log(f"  - {key}: {value}", xbmc.LOGINFO)

            # Also log any additional metadata that might contain audio info
            for key, value in stream_info.items():
                if key not in ['urls', 'stream_url', 'license_key']:
                    xbmc.log(f"Additional stream metadata - {key}: {value}", xbmc.LOGINFO)

            xbmc.log(f"=== END STREAM ANALYSIS ===", xbmc.LOGINFO)

            # Prefer MPEG-DASH over HLS
            for stream in stream_info['urls']:
                if stream['content_type'] == 'application/dash+xml':
                    xbmc.log(f"Selected DASH stream: {stream['src']}", xbmc.LOGINFO)
                    return stream['src']

            # If DASH not found, fall back to HLS
            for stream in stream_info['urls']:
                if stream['content_type'] == 'application/x-mpegURL':
                    xbmc.log(f"Selected HLS stream: {stream['src']}", xbmc.LOGINFO)
                    return stream['src']

            # No suitable stream found
            xbmc.log("No suitable stream found.", xbmc.LOGERROR)
            return None

        except Exception as e:
            xbmc.log(f"Error selecting best stream: {e}", xbmc.LOGERROR)
            return None
