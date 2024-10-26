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
from resources.lib.metadata import Metadata
from resources.lib.film import Film
from resources.lib.library import Library
from resources.lib.playback import generate_drm_license_key




APP_VERSION_CODE = "6.06"
ACCEPT_LANGUAGE = "en-US"
CLIENT = "android"
CLIENT_APP = "mubi"
CLIENT_DEVICE_OS = "8.0"
USER_AGENT = "Mozilla/5.0 (Linux; Android 8.0.0; SM-G960F Build/R16NW) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.84 Mobile Safari/537.36"



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
        self.apiURL = 'https://api.mubi.com/v3/'
        self.UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0'
        self.session_manager = session_manager  # Use session manager for session-related data
        self.library = Library()  # Initialize the Library

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
            return cli_country
        else:
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
            'Client-Accept-Audio-Codecs': 'aac',
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

    def get_link_code(self):
        """
        Calls the Mubi API to generate a link code and an authentication token for the login process.

        :return: Dictionary with 'auth_token' and 'link_code'.
        :rtype: dict
        """
        response = self._make_api_call('GET', 'link_code', headers=self.hea_atv_gen())
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
        response = self._make_api_call('POST', 'authenticate', headers=self.hea_atv_gen(), json=data)

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
        response = self._make_api_call('DELETE', 'sessions', headers=self.hea_atv_auth())
        if response and response.status_code == 200:
            return True
        else:
            return False


    def get_film_groups(self):
        """
        Retrieves a list of all film groups (collections) from the MUBI API V3, handling pagination.
        Manually adds an additional entry for "Now Showing".

        :return: A list of all film group categories across all pages.
        :rtype: list
        """
        endpoint = 'browse/film_groups'
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




    def get_watch_list(self):
        """
        Retrieves and adds films to the library from the watchlist

        :return: Library instance with films.
        """
        try:
            # Retrieve films from the watchlist
            films_data = self.get_films_in_watchlist()

            # Process and add each film to the library
            category_name = "watchlist"
            for film_item in films_data:
                this_film = film_item.get('film')
                consumable = this_film.get('consumable')
                if consumable != None:
                    film = self.get_film_metadata(film_item, category_name)
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
        Retrieves films from the wishlist using the MUBI API V3.

        :return: result
        :rtype: json
        """
        endpoint = f'wishes'
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

        :param id: ID of the film group (category).
        :param category_name: Name of the category.
        :return: Library instance with films.
        """
        try:
            # Retrieve films from the film group with the given ID
            films_data = self.get_films_in_category_json(id)

            # Process and add each film to the library
            for film_item in films_data:
                film = self.get_film_metadata(film_item, category_name)
                if film:
                    self.library.add_film(film)

            xbmc.log(f"Fetched {len(self.library)} films for category '{category_name}'", xbmc.LOGINFO)
        except Exception as e:
            xbmc.log(f"Error fetching films for category '{category_name}': {e}", xbmc.LOGERROR)

        return self.library




    def get_films_in_category_json(self, category_id):
        """
        Retrieves films within a specific film group (collection) using the MUBI API V3.

        :param category_id: ID of the film group (category).
        :return: List of film group items (films).
        :rtype: list
        """
        all_film_items = []
        page = 1
        per_page = 20

        while True:
            endpoint = f'film_groups/{category_id}/film_group_items'
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




    def get_film_metadata(self, film_data: dict, category_name: str) -> Film:
        """
        Extracts and returns film metadata from the API data.

        :param film_data: Dictionary containing film data
        :param category_name: Name of the category
        :return: Film instance or None if not valid
        """
        try:
            film_info = film_data.get('film', {})
            if not film_info:
                return None

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
                category=category_name,
                metadata=metadata
            )
        except Exception as e:
            xbmc.log(f"Error parsing film metadata: {e}", xbmc.LOGERROR)
            return None






    def get_secure_stream_info(self, vid: str) -> dict:
        try:
            # Step 1: Attempt to check film viewing availability with parental lock
            viewing_url = f"{self.apiURL}films/{vid}/viewing"
            params = {'parental_lock_enabled': 'true'}  # Add as query parameter
            viewing_response = self._make_api_call("POST", full_url=viewing_url, headers=self.hea_atv_auth(), params=params)

            # If the parental lock check fails, log a warning but continue
            if not viewing_response or viewing_response.status_code != 200:
                xbmc.log(f"Parental lock check failed, ignoring. Error: {viewing_response.text if viewing_response else 'No response'}", xbmc.LOGWARNING)

            # Step 2: Handle Pre-roll (if any)
            preroll_url = f"{self.apiURL}prerolls/viewings"
            preroll_data = {'viewing_film_id': int(vid)}
            preroll_response = self._make_api_call("POST", full_url=preroll_url, headers=self.hea_atv_auth(), json=preroll_data)

            # Pre-roll is optional, so even if it fails, we can continue
            if preroll_response and preroll_response.status_code != 200:
                xbmc.log(f"Pre-roll processing failed: {preroll_response.text}", xbmc.LOGDEBUG)

            # Step 3: Fetch the secure video URL
            secure_url = f"https://api.mubi.com/v3/films/{vid}/viewing/secure_url"
            secure_response = self._make_api_call("GET", full_url=secure_url, headers=self.hea_atv_auth())

            # Ensure we keep the entire secure response data intact
            secure_data = secure_response.json() if secure_response and secure_response.status_code == 200 else None
            if not secure_data or "url" not in secure_data:
                message = secure_data.get('user_message', 'Unable to retrieve secure URL') if secure_data else 'Unknown error'
                xbmc.log(f"Error retrieving secure stream info: {message}", xbmc.LOGERROR)
                return {'error': message}

            # Step 4: Extract stream URL and DRM info (keep all URLs)
            stream_info = {
                'stream_url': secure_data['url'],  # The primary stream URL
                'urls': secure_data.get('urls', []),  # Additional URLs to select from
                'license_key': generate_drm_license_key(self.session_manager.token, self.session_manager.user_id)
            }

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
            # Log available streams
            xbmc.log(f"Selecting best stream from secure_data: {stream_info}", xbmc.LOGDEBUG)
            for stream in stream_info['urls']:
                xbmc.log(f"Available stream: {stream['src']} - Content Type: {stream['content_type']}", xbmc.LOGDEBUG)

            # Prefer MPEG-DASH over HLS
            for stream in stream_info['urls']:
                if stream['content_type'] == 'application/dash+xml':
                    xbmc.log(f"Selected DASH stream: {stream['src']}", xbmc.LOGDEBUG)
                    return stream['src']

            # If DASH not found, fall back to HLS
            for stream in stream_info['urls']:
                if stream['content_type'] == 'application/x-mpegURL':
                    xbmc.log(f"Selected HLS stream: {stream['src']}", xbmc.LOGDEBUG)
                    return stream['src']

            # No suitable stream found
            xbmc.log("No suitable stream found.", xbmc.LOGERROR)
            return None

        except Exception as e:
            xbmc.log(f"Error selecting best stream: {e}", xbmc.LOGERROR)
            return None
