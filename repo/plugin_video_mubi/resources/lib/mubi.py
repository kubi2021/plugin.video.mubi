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
import xbmcgui
import re
import random
from urllib.parse import urljoin
from urllib.parse import urlencode
import time
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from typing import Optional, Tuple
from .metadata import Metadata
from .film import Film
from .library import Library
from .playback import generate_drm_license_key


class Mubi:

    # Country code to full name mapping for user-friendly messages
    COUNTRY_NAMES = {
        'CH': 'Switzerland',
        'DE': 'Germany',
        'US': 'the United States',
        'GB': 'the United Kingdom',
        'FR': 'France',
        'JP': 'Japan',
    }

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

        # Set up retries with exponential backoff for transient errors
        # Note: 429 (Too Many Requests) is handled separately below with Retry-After
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

        # Retry loop for rate limiting (429 responses)
        # Use longer waits to respect MUBI's rate limits (especially for bulk operations)
        max_rate_limit_retries = 5
        base_wait_time = 10  # Start with 10 seconds for rate limit backoff

        for attempt in range(max_rate_limit_retries + 1):
            try:
                response = session.request(
                    method,
                    url,
                    headers=headers,
                    params=params,
                    data=data,
                    json=json,
                    timeout=10
                )

                # Handle rate limiting (429 Too Many Requests)
                if response.status_code == 429:
                    if attempt < max_rate_limit_retries:
                        # Check for Retry-After header (can be seconds or HTTP date)
                        retry_after = response.headers.get('Retry-After')
                        if retry_after:
                            try:
                                wait_time = int(retry_after)
                            except ValueError:
                                # Might be an HTTP date, use base exponential backoff
                                wait_time = base_wait_time * (2 ** attempt)
                        else:
                            # No Retry-After header, use exponential backoff
                            # 10s, 20s, 40s, 80s, 160s = up to 5+ minutes total
                            wait_time = base_wait_time * (2 ** attempt)

                        xbmc.log(
                            f"Rate limited (429). Waiting {wait_time}s before retry "
                            f"(attempt {attempt + 1}/{max_rate_limit_retries})",
                            xbmc.LOGWARNING
                        )
                        time.sleep(wait_time)
                        continue
                    else:
                        xbmc.log("Rate limit retries exhausted", xbmc.LOGERROR)
                        response.raise_for_status()

                # Check for invalid token before raising HTTPError
                if response.status_code in [401, 422]:
                    self._check_and_handle_invalid_token(response)

                # Raise an HTTPError for bad responses (4xx and 5xx)
                response.raise_for_status()

                session.close()
                return response

            except requests.exceptions.HTTPError as http_err:
                xbmc.log(f"HTTP error occurred: {http_err}", xbmc.LOGERROR)
                if response is not None:
                    xbmc.log(f"Response Headers: {response.headers}", xbmc.LOGERROR)
                    xbmc.log(f"Response Content: {response.text}", xbmc.LOGERROR)
                session.close()
                return None

            except requests.exceptions.RequestException as req_err:
                xbmc.log(f"Request exception occurred: {req_err}", xbmc.LOGERROR)
                session.close()
                return None

            except Exception as err:
                xbmc.log(f"An unexpected error occurred: {err}", xbmc.LOGERROR)
                session.close()
                return None

        # If we exhausted all retries without returning, close session and return None
        session.close()
        xbmc.log("All retry attempts exhausted.", xbmc.LOGERROR)
        return None

    def _check_and_handle_invalid_token(self, response):
        """
        Check if the API response indicates an invalid or expired token.
        If so, automatically log out the user and show a notification.

        :param response: HTTP response object
        """
        try:
            # Try to parse the response as JSON
            response_data = response.json()

            # Check for invalid token indicators
            # MUBI API returns code 8 for "Invalid login token"
            if response_data.get('code') == 8 or \
               'invalid' in response_data.get('message', '').lower() and 'token' in response_data.get('message', '').lower() or \
               'expired' in response_data.get('user_message', '').lower():

                xbmc.log("Invalid or expired token detected. Logging out user.", xbmc.LOGWARNING)

                # Log out the user
                self.session_manager.set_logged_out()

                # Show user-friendly notification
                try:
                    dialog = xbmcgui.Dialog()
                    user_message = response_data.get('user_message', 'Your session has expired. Please sign in again.')
                    dialog.notification(
                        "MUBI - Session Expired",
                        user_message,
                        xbmcgui.NOTIFICATION_WARNING,
                        5000  # 5 second notification
                    )

                    # Refresh the container to show the login option
                    xbmc.executebuiltin('Container.Refresh')
                except Exception as notification_error:
                    xbmc.log(f"Failed to show session expired notification: {notification_error}", xbmc.LOGWARNING)

        except Exception as e:
            # If we can't parse the response, just log and continue
            xbmc.log(f"Could not check for invalid token: {e}", xbmc.LOGDEBUG)

    def _safe_json_parse(self, response, operation_name="API operation"):
        """
        Safely parse JSON response with user-friendly error handling.

        Level 2 Bug Fix: Handles malformed JSON responses gracefully with user notifications.

        :param response: HTTP response object
        :param operation_name: Name of the operation for user-friendly error messages
        :return: Parsed JSON data or None if parsing fails
        """
        if not response:
            return None

        try:
            return response.json()
        except json.JSONDecodeError as e:
            # Log technical details for debugging
            xbmc.log(f"JSON parsing error in {operation_name}: {e}", xbmc.LOGERROR)
            xbmc.log(f"Response content: {response.text[:500]}...", xbmc.LOGERROR)
            xbmc.log(f"Response headers: {response.headers}", xbmc.LOGERROR)

            # Show user-friendly notification
            try:
                dialog = xbmcgui.Dialog()
                dialog.notification(
                    "MUBI",
                    "Having trouble reaching MUBI service. Please try again later.",
                    xbmcgui.NOTIFICATION_WARNING,
                    5000  # 5 second notification
                )
            except Exception as notification_error:
                # Fallback if notification fails
                xbmc.log(f"Failed to show notification: {notification_error}", xbmc.LOGWARNING)

            return None
        except Exception as e:
            # Handle any other unexpected errors
            xbmc.log(f"Unexpected error parsing response in {operation_name}: {e}", xbmc.LOGERROR)

            # Show generic error notification
            try:
                dialog = xbmcgui.Dialog()
                dialog.notification(
                    "MUBI",
                    "Service temporarily unavailable. Please try again later.",
                    xbmcgui.NOTIFICATION_ERROR,
                    5000
                )
            except Exception:
                pass  # Silent fallback

            return None




    def get_cli_country(self):
        """
        Retrieves the client's country based on current IP using IP geolocation.

        This method uses a third-party IP geolocation service to detect the user's
        current location purely based on IP address. This is essential for VPN users
        who may change their country without restarting Kodi.

        Falls back to MUBI's website detection if the geolocation service fails.

        :return: Client country code (uppercase, e.g., 'US', 'CH', 'AF').
        :rtype: str
        """
        import requests as fresh_requests

        # Try multiple IP geolocation services for reliability
        geo_services = [
            ('https://ipapi.co/country/', 'text'),  # Returns just country code like "US"
            ('https://ipinfo.io/country', 'text'),  # Returns just country code like "US"
        ]

        for service_url, response_type in geo_services:
            try:
                xbmc.log(f"Detecting country via IP geolocation: {service_url}", xbmc.LOGDEBUG)
                response = fresh_requests.get(
                    service_url,
                    headers={'User-Agent': self.UA},
                    timeout=5
                )

                if response and response.status_code == 200:
                    country_code = response.text.strip().upper()
                    # Validate it looks like a country code (2 letters)
                    if len(country_code) == 2 and country_code.isalpha():
                        xbmc.log(f"Client country detected from IP geolocation: {country_code}", xbmc.LOGINFO)
                        return country_code

            except Exception as e:
                xbmc.log(f"IP geolocation service {service_url} failed: {e}", xbmc.LOGDEBUG)
                continue

        # Fallback: Try MUBI's website (less reliable for VPN users)
        xbmc.log("IP geolocation failed, falling back to MUBI website detection", xbmc.LOGWARNING)
        try:
            headers = {
                'User-Agent': self.UA,
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0',
            }

            fresh_session = fresh_requests.Session()
            fresh_session.cookies.clear()
            response = fresh_session.get('https://mubi.com/', headers=headers, timeout=10)

            if response and response.status_code == 200:
                country = re.findall(r'"Client-Country":"([^"]+?)"', response.text)
                cli_country = country[0] if country else 'PL'
                xbmc.log(f"Client country detected from MUBI: {cli_country}", xbmc.LOGINFO)
                return cli_country
        except Exception as e:
            xbmc.log(f"MUBI fallback detection failed: {e}", xbmc.LOGERROR)

        xbmc.log("All country detection methods failed, defaulting to: PL", xbmc.LOGWARNING)
        return 'PL'

    def get_cli_language(self):
        """
        Returns the client's preferred language for API requests.
        Uses cached value if available, otherwise returns default 'en'.

        Note: Previously this method fetched language from mubi.com on every call,
        but that caused issues with rate limiting/CAPTCHA during catalogue sync.
        Now uses a simple default since the API accepts 'en' for all requests.

        :return: Client preferred language code (e.g., 'en' for English).
        :rtype: str
        """
        # Use cached value from session manager if available
        if hasattr(self.session_manager, 'client_language') and self.session_manager.client_language:
            return self.session_manager.client_language
        # Default to English - works well with MUBI's international API
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


    def hea_atv_auth(self, country: str = None):
        """
        Generates headers required for API requests with authorization.

        :param country: Optional country code to override Client-Country header.
        :return: Headers dictionary with Authorization token.
        :rtype: dict
        """
        headers = self.hea_atv_gen()
        token = self.session_manager.token  # Use session manager
        if not token:
            xbmc.log("No token found", xbmc.LOGERROR)
        headers['Authorization'] = f'Bearer {token}'
        # Override country if specified (for multi-country playback)
        if country:
            headers['Client-Country'] = country
            xbmc.log(f"Using override country for API: {country}", xbmc.LOGINFO)
        return headers

    # Common browser User-Agents for rotation to avoid fingerprinting
    COMMON_USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) Gecko/20100101 Firefox/131.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 14.7; rv:131.0) Gecko/20100101 Firefox/131.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0',
    ]

    # Countries to sync catalogues from (ISO 3166-1 alpha-2 codes)
    # Different countries have different film availability on MUBI
    SYNC_COUNTRIES = ['CH', 'DE', 'US', 'GB', 'FR', 'JP']

    def _get_random_user_agent(self):
        """
        Returns a random User-Agent from the pool of common browser UAs.
        Used to reduce fingerprinting on anonymous requests.

        :return: Random User-Agent string.
        :rtype: str
        """
        return random.choice(self.COMMON_USER_AGENTS)

    def hea_gen_anonymous(self, country_code: Optional[str] = None):
        """
        Generates anonymous web headers for API requests that don't require authentication.
        Used for browsing the catalogue without sending user credentials.
        Uses a random User-Agent on each call to reduce fingerprinting.

        :param country_code: Optional country code to override the session's client_country.
                            Used for multi-country catalogue sync.
        :return: Headers dictionary without Authorization token.
        :rtype: dict
        """
        base_url = 'https://mubi.com'
        # Use provided country_code or fall back to session's client_country
        client_country = country_code if country_code else self.session_manager.client_country

        return {
            'Referer': base_url,
            'Origin': base_url,
            'User-Agent': self._get_random_user_agent(),
            'Client': 'web',
            'Client-Accept-Video-Codecs': 'h265,vp9,h264',
            'Client-Country': client_country,
            'accept-language': self.get_cli_language()
        }

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
        return self._safe_json_parse(response, "authentication link code generation")

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

        response_data = self._safe_json_parse(response, "user authentication")

        if response_data:
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
    def _fetch_films_for_country(
        self, country_code: str, playable_only: bool = True, page_callback=None,
        global_film_ids: set = None
    ) -> Tuple[set, dict, int, int]:
        """
        Fetches all films for a specific country from the MUBI API.

        :param country_code: ISO 3166-1 alpha-2 country code (e.g., 'CH', 'DE', 'US')
        :param playable_only: If True, only fetch currently playable films.
        :param page_callback: Optional callback called after each page with (globally_new_films).
                              Returns False if cancelled.
        :param global_film_ids: Set of film IDs already discovered from previous countries.
                                Used to count truly new films for progress display.
        :return: Tuple of (film_ids set, film_data dict {id: film_data}, total_count, pages_fetched)
        """
        endpoint = 'v4/browse/films'
        film_ids = set()
        film_data_map = {}  # {film_id: film_data}
        page = 1
        pages_fetched = 0
        total_count = 0

        # For counting truly new films (not seen in any previous country)
        known_global_ids = global_film_ids or set()

        xbmc.log(f"[{country_code}] Starting to fetch films", xbmc.LOGINFO)

        while True:
            # Generate headers with specific country
            headers = self.hea_gen_anonymous(country_code=country_code)

            params = {
                'page': page,
                'sort': 'title',
            }
            if playable_only:
                params['playable'] = 'true'

            response = self._make_api_call('GET', endpoint=endpoint, headers=headers, params=params)

            if not response:
                xbmc.log(f"[{country_code}] Failed to retrieve page {page}", xbmc.LOGERROR)
                break

            data = self._safe_json_parse(response, f"[{country_code}] films page {page}")
            if not data:
                break

            films = data.get('films', [])
            meta = data.get('meta', {})
            pages_fetched += 1

            # Get total count from first page
            if page == 1:
                total_count = meta.get('total_count', 0)
                total_pages = meta.get('total_pages', 0)
                xbmc.log(f"[{country_code}] API reports {total_count} films across {total_pages} pages", xbmc.LOGINFO)

            # Process films
            globally_new_films = 0  # Films not seen in ANY country yet
            for film_entry in films:
                film_id = film_entry.get('id')
                if film_id and film_id not in film_ids:
                    film_ids.add(film_id)
                    film_data_map[film_id] = film_entry
                    # Count as globally new only if not seen in previous countries
                    if film_id not in known_global_ids:
                        globally_new_films += 1

            # Call page callback with globally new films count (throttled to every 5 pages)
            if page_callback and pages_fetched % 5 == 0:
                should_continue = page_callback(globally_new_films)
                if should_continue is False:
                    xbmc.log(f"[{country_code}] Cancelled by user", xbmc.LOGINFO)
                    break

            # Check for next page
            next_page = meta.get('next_page')
            if next_page:
                page = next_page
                # Small delay between pages to avoid rate limiting
                time.sleep(0.3)
            else:
                break

            # Safety limit
            if pages_fetched > 100:
                xbmc.log(
                    f"[{country_code}] Safety limit reached at {pages_fetched} pages",
                    xbmc.LOGWARNING
                )
                break

        xbmc.log(f"[{country_code}] Completed: {len(film_ids)} unique films from {pages_fetched} pages", xbmc.LOGINFO)
        return film_ids, film_data_map, total_count, pages_fetched

    def process_film_data(self, film_data: dict) -> Optional[Film]:
        """
        Hydrates raw film data into a Film object.
        Replaces previous loop logic.
        """
        # The data source injects keys into the raw dict.
        # But here 'film_data' is just the dict from the API (plus __available_countries__)
        
        fid = film_data.get('id')
        
        # Check if country availability was injected by DataSource
        available_countries = film_data.get('__available_countries__', [])
        
        # We need to wrap it because get_film_metadata expects {'film': ...} structure
        # This is a legacy artifact of the Mubi API V3/V4 structure where sometimes it sends wrapper
        film_wrapper = {'film': film_data}
        
        return self.get_film_metadata(film_wrapper, available_countries=list(available_countries))

    def get_all_films(self, playable_only=True, progress_callback=None, countries=None):
        """
        Retrieves all films from MUBI API by syncing across specified countries.
        Uses the new pipeline: DataSource -> Filter -> Hydrate -> Library.

        :param playable_only: If True, only fetch currently playable films.
        :param progress_callback: Optional callback function to report progress.
        :param countries: List of ISO 3166-1 alpha-2 country codes to sync from.
        :return: Library instance with all films.
        """
        from .data_source import MubiApiDataSource
        from .filters import FilmFilter

        # 1. Fetch (DataSource)
        data_source = MubiApiDataSource(self)
        # progress_callback is handled inside data source for the fetching phase
        raw_films = data_source.get_films(playable_only, progress_callback, countries)
        
        xbmc.log(f"Pipeline: Fetched {len(raw_films)} raw films.", xbmc.LOGINFO)

        # 2. Filter (FilmFilter)
        film_filter = FilmFilter()
        filtered_films = film_filter.filter_films(raw_films)
        
        xbmc.log(f"Pipeline: Filtering retained {len(filtered_films)} films.", xbmc.LOGINFO)

        # 3. Hydrate & 4. Add to Library
        all_films_library = Library()
        
        if progress_callback:
             try:
                 progress_callback(
                     current_films=len(raw_films), # Total known
                     total_films=len(filtered_films), # Films to process
                     current_country=len(self.SYNC_COUNTRIES), # Done
                     total_countries=len(self.SYNC_COUNTRIES),
                     country_code='PROCESSING'
                 )
             except Exception:
                 pass
        
        xbmc.log(f"Processing {len(filtered_films)} films into library...", xbmc.LOGINFO)
        total_films_added = 0
        
        for film_data in filtered_films:
            film = self.process_film_data(film_data)
            if film:
                all_films_library.add_film(film)
                total_films_added += 1

        xbmc.log(f"Successfully added {total_films_added} films to library", xbmc.LOGINFO)
        return all_films_library


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
        data = self._safe_json_parse(response, "watchlist count retrieval")

        if not data:
            return []  # Return empty list for graceful degradation

        meta = data.get('meta')
        total_count = meta.get('total_count') if meta else 0

        if total_count == 0:
            return []

        all_film_items = []
        response = self._call_wishlist_api(total_count)
        data = self._safe_json_parse(response, "watchlist films retrieval")

        if data:
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













    def get_film_metadata(self, film_data: dict, available_countries: list = None) -> Film:
        """
        Extracts and returns film metadata from the API data.
        Filters out series content to only process actual films.

        :param film_data: Dictionary containing film data
        :param available_countries: List of country codes where this film is available
        :return: Film instance or None if not valid or is a series
        """
        try:
            film_info = film_data.get('film', {})
            if not film_info:
                return None

            # Check if this is a series (like inspiration code does)
            if 'series' in film_info and film_info['series'] is not None:
                return None  # Skip series content for film sync

            available_at = film_info.get('consumable', {}).get('available_at')
            expires_at = film_info.get('consumable', {}).get('expires_at')
            if available_at and expires_at:
                available_at_dt = dateutil.parser.parse(available_at)
                expires_at_dt = dateutil.parser.parse(expires_at)
                now = datetime.datetime.now(tz=available_at_dt.tzinfo)
                if available_at_dt > now or expires_at_dt < now:
                    return None

            # Enhanced plot descriptions: Use default_editorial if available, fallback to short_synopsis
            default_editorial = film_info.get('default_editorial', '')
            short_synopsis = film_info.get('short_synopsis', '')

            if default_editorial:
                enhanced_plot = default_editorial
            else:
                enhanced_plot = short_synopsis

            short_outline = short_synopsis  # Keep short synopsis for outline

            # Extract content rating for age ratings
            content_rating_info = film_info.get('content_rating', {})
            mpaa_rating = ''
            if content_rating_info:
                # Use rating_code as primary, fallback to label, include description if available
                rating_code = content_rating_info.get('rating_code', '')
                rating_label = content_rating_info.get('label', '')
                rating_description = content_rating_info.get('description', '')

                if rating_code:
                    mpaa_rating = rating_code
                    if rating_description:
                        mpaa_rating += f" - {rating_description}"
                elif rating_label:
                    mpaa_rating = rating_label.upper()
                    if rating_description:
                        mpaa_rating += f" - {rating_description}"

            # Enhanced rating precision: Use 10-point scale if available, fallback to 5-point
            rating_10_point = film_info.get('average_rating_out_of_ten', 0)
            rating_5_point = film_info.get('average_rating', 0)

            if rating_10_point:
                final_rating = rating_10_point
            else:
                # Fallback to 5-point and convert to 10-point scale
                final_rating = rating_5_point * 2 if rating_5_point else 0

            # Extract all artwork URLs
            artwork_urls = self._get_all_artwork_urls(film_info)

            # Extract playback language information
            audio_languages, subtitle_languages, media_features = self._get_playback_languages(film_info)

            metadata = Metadata(
                title=film_info.get('title', ''),
                director=[d['name'] for d in film_info.get('directors', [])],
                year=film_info.get('year', ''),
                duration=film_info.get('duration', 0),
                country=film_info.get('historic_countries', []),
                plot=enhanced_plot,  # Use enhanced editorial content
                plotoutline=short_outline,  # Keep short synopsis for outline
                genre=film_info.get('genres', []),
                originaltitle=film_info.get('original_title', ''),
                rating=final_rating,  # Use enhanced 10-point rating
                votes=film_info.get('number_of_ratings', 0),
                dateadded=datetime.date.today().strftime('%Y-%m-%d'),
                trailer=self._get_best_trailer_url(film_info),
                image=self._get_best_thumbnail_url(film_info),
                mpaa=mpaa_rating,  # Add content rating
                artwork_urls=artwork_urls,  # Add all artwork URLs
                audio_languages=audio_languages,  # Available audio languages
                subtitle_languages=subtitle_languages,  # Available subtitle languages
                media_features=media_features  # Media features (4K, stereo, 5.1, etc.)
            )

            return Film(
                mubi_id=film_info.get('id'),
                title=film_info.get('title', ''),
                artwork=self._get_best_thumbnail_url(film_info),
                web_url=film_info.get('web_url', ''),
                metadata=metadata,
                available_countries=available_countries or []
            )
        except Exception as e:
            xbmc.log(f"Error parsing film metadata: {e}", xbmc.LOGERROR)
            return None

    def _get_best_thumbnail_url(self, film_info: dict) -> str:
        """
        Get the best available thumbnail URL, preferring retina quality.

        :param film_info: Dictionary containing film data
        :return: Best available thumbnail URL
        """
        try:
            # Check for enhanced stills with retina quality
            stills = film_info.get('stills', {})
            if isinstance(stills, dict):
                # Prefer retina quality for higher resolution
                retina_url = stills.get('retina', '')
                if retina_url:
                    return retina_url

                # Fallback to standard quality
                standard_url = stills.get('standard', '')
                if standard_url:
                    return standard_url

            # Final fallback to still_url
            return film_info.get('still_url', '')

        except Exception as e:
            xbmc.log(f"Error getting thumbnail URL: {e}", xbmc.LOGERROR)
            return film_info.get('still_url', '')  # Safe fallback

    def _get_all_artwork_urls(self, film_info: dict) -> dict:
        """
        Extract all available artwork URLs from MUBI film data.
        Supports: thumb (landscape), poster (portrait), fanart (background), clearlogo (title treatment).

        Priority sources:
        - thumb: stills.retina > stills.standard > still_url
        - poster: artworks[cover_artwork_vertical] > portrait_image
        - fanart: artworks[centered_background]
        - clearlogo: title_treatment_url

        :param film_info: Dictionary containing film data
        :return: Dictionary mapping artwork types to URLs
        """
        artwork_urls = {}

        try:
            # Handle None or invalid input gracefully
            if not film_info or not isinstance(film_info, dict):
                return {}

            # Thumbnail/Landscape images from stills
            stills = film_info.get('stills', {})
            if isinstance(stills, dict):
                # Use retina quality for thumb (landscape)
                if stills.get('retina'):
                    artwork_urls['thumb'] = stills['retina']
                elif stills.get('standard'):
                    artwork_urls['thumb'] = stills['standard']

            # Fallback to still_url if no stills available
            if 'thumb' not in artwork_urls:
                still_url = film_info.get('still_url')
                if still_url:
                    artwork_urls['thumb'] = still_url

            # Extract artwork from artworks[] array - better quality poster and fanart
            artworks = film_info.get('artworks', [])
            if isinstance(artworks, list):
                for artwork in artworks:
                    if not isinstance(artwork, dict):
                        continue

                    artwork_format = artwork.get('format', '')
                    image_url = artwork.get('image_url', '')

                    if not image_url:
                        continue

                    # Poster from cover_artwork_vertical (vertical/portrait format)
                    if artwork_format == 'cover_artwork_vertical' and 'poster' not in artwork_urls:
                        artwork_urls['poster'] = image_url

                    # Fanart from centered_background (large background image)
                    elif artwork_format == 'centered_background' and 'fanart' not in artwork_urls:
                        artwork_urls['fanart'] = image_url

            # Fallback: Portrait image for poster if not found in artworks[]
            if 'poster' not in artwork_urls:
                portrait_image = film_info.get('portrait_image')
                if portrait_image:
                    artwork_urls['poster'] = portrait_image

            # Title treatment for clear logo
            title_treatment = film_info.get('title_treatment_url')
            if title_treatment:
                artwork_urls['clearlogo'] = title_treatment

            return artwork_urls

        except Exception as e:
            xbmc.log(f"Error extracting artwork URLs: {e}", xbmc.LOGERROR)
            # Safe fallback - handle None film_info gracefully
            if film_info and isinstance(film_info, dict):
                still_url = film_info.get('still_url', '')
                return {'thumb': still_url} if still_url else {}
            else:
                return {}

    def _get_best_trailer_url(self, film_info: dict) -> str:
        """
        Get the highest quality trailer URL available from optimised trailers.

        :param film_info: Dictionary containing film data
        :return: Best available trailer URL
        """
        try:
            # Check for optimised trailers with multiple qualities
            optimised_trailers = film_info.get('optimised_trailers', [])
            if isinstance(optimised_trailers, list) and optimised_trailers:
                # Prefer highest quality available: 1080p > 720p > 240p
                for quality in ['1080p', '720p', '240p']:
                    for trailer in optimised_trailers:
                        if isinstance(trailer, dict) and trailer.get('profile') == quality:
                            trailer_url = trailer.get('url', '')
                            if trailer_url:
                                return trailer_url

            # Fallback to original trailer_url
            return film_info.get('trailer_url', '')

        except Exception as e:
            xbmc.log(f"Error getting trailer URL: {e}", xbmc.LOGERROR)
            return film_info.get('trailer_url', '')  # Safe fallback

    def _get_playback_languages(self, film_info: dict) -> tuple:
        """
        Extract playback language information from MUBI film data.

        :param film_info: Dictionary containing film data
        :return: Tuple of (audio_languages, subtitle_languages, media_features)
        """
        try:
            # Get consumable information which contains playback_languages
            consumable = film_info.get('consumable', {})
            if not isinstance(consumable, dict):
                return [], [], []

            playback_languages = consumable.get('playback_languages', {})
            if not isinstance(playback_languages, dict):
                return [], [], []

            # Extract language and feature information
            audio_languages = playback_languages.get('audio_options', [])
            subtitle_languages = playback_languages.get('subtitle_options', [])
            media_features = playback_languages.get('media_features', [])

            # Also check for extended_audio_options if available
            extended_audio = playback_languages.get('extended_audio_options', [])
            if extended_audio and isinstance(extended_audio, list):
                # Merge with audio_options, avoiding duplicates
                all_audio = list(set(audio_languages + extended_audio))
                audio_languages = all_audio

            # Ensure all are lists
            audio_languages = audio_languages if isinstance(audio_languages, list) else []
            subtitle_languages = subtitle_languages if isinstance(subtitle_languages, list) else []
            media_features = media_features if isinstance(media_features, list) else []

            return audio_languages, subtitle_languages, media_features

        except Exception as e:
            xbmc.log(f"Error extracting playback languages: {e}", xbmc.LOGERROR)
            return [], [], []






    def get_secure_stream_info(self, vid: str, film_country: Optional[str] = None) -> dict:
        """
        Get secure stream information for a film.

        :param vid: Film ID
        :param film_country: Country where the film is available (for error messages only,
                             not used in API headers - we always use user's actual country)
        :return: Dictionary with stream info or error
        """
        try:
            # Log the playback attempt
            user_country = self.session_manager.client_country
            xbmc.log(f"Getting stream info for film {vid}", xbmc.LOGINFO)
            xbmc.log(f"User country: {user_country}, Film available in: {film_country}", xbmc.LOGINFO)

            # Always use user's actual country for API headers (geo-restriction is IP-based)
            headers = self.hea_atv_auth()

            # Step 1: Attempt to check film viewing availability with parental lock
            # Make a direct request to check for geo-restriction errors
            viewing_url = f"{self.apiURL}v4/films/{vid}/viewing"
            params = {'parental_lock_enabled': 'true'}

            try:
                response = requests.post(viewing_url, headers=headers, params=params, timeout=10)
                xbmc.log(f"Viewing availability response: {response.status_code}", xbmc.LOGDEBUG)

                # Check for geo-restriction error (422 with "Film not authorized")
                if response.status_code == 422:
                    try:
                        error_data = response.json()
                        if error_data.get('code') == 50 or 'not authorized' in error_data.get('message', '').lower():
                            xbmc.log(f"Geo-restriction detected: {error_data}", xbmc.LOGWARNING)
                            # Include the film's available country in the error message
                            if film_country:
                                country_name = self.COUNTRY_NAMES.get(film_country, film_country)
                                error_msg = f"Film not available in your country. Use a VPN to {country_name} to watch it."
                            else:
                                error_msg = "Film not available in your country. Use a VPN to watch it."
                            return {'error': error_msg}
                    except (ValueError, KeyError):
                        pass  # Not a JSON response or missing fields

                # For other non-200 responses, log and continue (some may be recoverable)
                if response.status_code != 200:
                    xbmc.log(f"Viewing availability check returned {response.status_code}: {response.text}", xbmc.LOGWARNING)

            except requests.exceptions.RequestException as e:
                xbmc.log(f"Error checking viewing availability: {e}", xbmc.LOGWARNING)

            # Step 2: Handle Pre-roll (if any)
            preroll_url = f"{self.apiURL}v4/prerolls/viewings"
            preroll_data = {'viewing_film_id': int(vid)}
            preroll_response = self._make_api_call("POST", full_url=preroll_url, headers=headers, json=preroll_data)

            # Pre-roll is optional, so even if it fails, we can continue
            if preroll_response and preroll_response.status_code != 200:
                xbmc.log(f"Pre-roll processing failed: {preroll_response.text}", xbmc.LOGDEBUG)

            # Step 3: Fetch the secure video URL
            secure_url = f"{self.apiURL}v4/films/{vid}/viewing/secure_url"
            secure_response = self._make_api_call("GET", full_url=secure_url, headers=headers)

            # Ensure we keep the entire secure response data intact
            if secure_response and secure_response.status_code == 200:
                secure_data = self._safe_json_parse(secure_response, "secure stream URL retrieval")
            else:
                secure_data = None

            if not secure_data or "url" not in secure_data:
                if secure_data:
                    message = secure_data.get('user_message', 'Unable to retrieve secure URL')
                else:
                    message = 'Service temporarily unavailable'
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
            return {'error': 'Service temporarily unavailable while retrieving stream info'}


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
