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



APP_VERSION_CODE = "6.06"
ACCEPT_LANGUAGE = "en-US"
CLIENT = "android"
CLIENT_APP = "mubi"
CLIENT_DEVICE_OS = "8.0"
USER_AGENT = "Mozilla/5.0 (Linux; Android 8.0.0; SM-G960F Build/R16NW) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.84 Mobile Safari/537.36"


Film = namedtuple(
    "Film", ["title", "mubi_id", "artwork", "web_url", "category", "metadata"]
)

Metadata = namedtuple(
    "Metadata",
    [
        "title",
        "director",
        "year",
        "duration",
        "country",
        "plot",
        "plotoutline",
        "genre",
        "originaltitle",
        "rating",
        "votes",
        "castandrole",
        "dateadded",
        "trailer",
        "image",
    ],
)

class Mubi:
    def __init__(self, session_manager):
        """
        Initialize the Mubi class with the session manager.

        :param session_manager: Instance of SessionManager to handle session data
        :type session_manager: SessionManager
        """
        self.apiURL = 'https://api.mubi.com/v3/'
        self.UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0'
        self.session_manager = session_manager  # Use session manager for session-related data

    def _make_api_call(self, method, endpoint=None, full_url=None, headers=None, params=None, data=None, json=None):
        """
        Generic method to make API calls.

        :param method: HTTP method ('GET', 'POST', 'DELETE', etc.)
        :param endpoint: API endpoint to call (appended to self.apiURL unless full_url is provided)
        :param full_url: (Optional) Full URL to use instead of appending endpoint to self.apiURL
        :param headers: (Optional) Dictionary of HTTP Headers to send with the request
        :param params: (Optional) Dictionary of URL parameters to append to the URL
        :param data: (Optional) Dictionary, bytes, or file-like object to send in the body of the request
        :param json: (Optional) A JSON serializable Python object to send in the body of the request
        :return: Response object
        """
        url = full_url if full_url else f"{self.apiURL}{endpoint}"
        try:
            response = requests.request(method, url, headers=headers, params=params, data=data, json=json)
            response.raise_for_status()
            return response
        except requests.HTTPError as http_err:
            xbmc.log(f"HTTP error occurred: {http_err}", xbmc.LOGERROR)
            return None
        except Exception as err:
            xbmc.log(f"An error occurred: {err}", xbmc.LOGERROR)
            return None

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

    def hea_atv_gen(self):
        """
        Generates headers required for API requests without authorization.

        :return: Headers dictionary.
        :rtype: dict
        """
        return {
            'User-Agent': 'MUBI-Android-TV/31.1',  # Updated User-Agent
            'accept-encoding': 'gzip',
            'accept': 'application/json',
            'client': 'android_tv',
            'client-version': '31.1',  # Updated client-version
            'client-device-identifier': self.session_manager.device_id,  # Use session manager
            'client-app': 'mubi',
            'client-device-brand': 'unknown',
            'client-device-model': 'sdk_google_atv_x86',
            'client-device-os': '8.0.0',
            'client-accept-audio-codecs': 'AAC',
            'client-country': self.session_manager.client_country  # Use session manager
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
        :return: Response JSON from the authenticate API call.
        :rtype: dict
        """
        data = {'auth_token': auth_token}
        response = self._make_api_call('POST', 'authenticate', headers=self.hea_atv_gen(), json=data)
        if response:
            return response.json()
        else:
            return None

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
        Retrieves a list of film groups (collections) from the MUBI API V3.

        :return: A list of film group categories.
        :rtype: list
        """
        endpoint = 'browse/film_groups'
        headers = self.hea_atv_gen()  # Use headers without authorization
        params = {'page': 1}

        response = self._make_api_call('GET', endpoint=endpoint, headers=headers, params=params)

        if response:
            data = response.json()
            film_groups = data.get('film_groups', [])
            categories = []
            for group in film_groups:
                xbmc.log(f"group content: {json.dumps(group, indent=2)}", xbmc.LOGDEBUG)
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
                    'type': group.get('type', ''),
                }
                categories.append(category)
            return categories
        else:
            xbmc.log("Failed to retrieve film groups", xbmc.LOGERROR)
            return []


        

class MubiOLD(object):

    _URL_MUBI = "https://api.mubi.com/v3/"
    _mubi_urls = {
        "login_code": urljoin(_URL_MUBI, "link_code"),
        "authenticate": urljoin(_URL_MUBI, "authenticate"),
        "logout": urljoin(_URL_MUBI, "sessions")
    }

    # _URL_MUBI = "https://mubi.com"
    # _mubi_urls = {
    #     "login": urljoin(_URL_MUBI, "api/v2/sessions"),
    #     "startup": urljoin(_URL_MUBI, "api/v2/app_startup"),
    #     "films": urljoin(_URL_MUBI, "/api/v2/film_programmings"),
    #     "film_groups": urljoin(_URL_MUBI, "/api/v2/layout"),
    #     "films_in_group": urljoin(_URL_MUBI, "/api/v2/film_groups/%s/film_group_items"),
    #     "get_url": urljoin(_URL_MUBI, "api/v2/films/%s/reels/%s/secure_url"),
    # }

    ## once we introduce the mubi login, remove the "random"
    # def __init__(self, username, password):
    def __init__(self, username="random", password="random"):

        self._username = username
        self._password = password
        self._cache_id = "plugin.video.mubi.filminfo.%s"
        # Need a 20 digit id, hash username to make it predictable
        self._udid = int(hashlib.sha1(username.encode("utf-8")).hexdigest(), 32) % (
            10 ** 20
        )
        self._token = None
        self._userid = None
        self._country = None
        self._session = requests.Session()
        self._session.headers.update(
            {
                "accept-language": ACCEPT_LANGUAGE,
                "client": CLIENT,
                "client-version": APP_VERSION_CODE,
                "client-app": CLIENT_APP,
                "client-device-os": CLIENT_DEVICE_OS,
                "user-agent": USER_AGENT,
                "if-none-match": 'W/"505d0033184d7877a3b351d8c94b6211"',
                "accept": "application/json, text/plain, */*",
                "client-device-identifier": str(self._udid),
            }
        )

    def get_film_list(self, type, id, category_name):
        """
        Mubi has 2 categories of films:
        - Filmprogramming: the movie of the day, available for 30 days
        - Film Group: each film group call returns multiple categories, such as Top 1000, or Mubi releases, for example.

        This function query the list of films and then query the metadata for each film.
        Ultimately, it returns a nametupl of films.
        """

        if type == "FilmProgramming":
            films = [
                self.get_film_metadata(film, category_name)
                for film in (self.get_now_showing_json())
            ]
        elif type == "FilmGroup":
            films = [
                self.get_film_metadata(film, category_name)
                for film in (self.get_films_in_category_json(id))
            ]

        return [f for f in films if f]

    def get_now_showing_json(self):
        """
        Calls the API and get the list of the 30 films of the day.

        """
        # Get list of available films
        args = (
            "?accept-language=%s&client=%s&client-version=%s&client-device-identifier=%s&client-app=%s&client-device-os=%s"
            % (
                ACCEPT_LANGUAGE,
                CLIENT,
                APP_VERSION_CODE,
                self._udid,
                CLIENT_APP,
                CLIENT_DEVICE_OS,
            )
        )
        r = self._session.get(self._mubi_urls["films"] + args)
        if r.status_code != 200:
            xbmc.log(
                "Invalid status code for films of the day: "
                + str(r.status_code)
                + " getting list of films",
                4,
            )
            xbmc.log(self._mubi_urls["films"] + args, 4)
        return r.json()

    def get_film_groups(self):
        """
        Query film groups. Each call to film groups returns one or many film category, such as Top 1000, or Mubi releases, for example.

        It will return a list of category.

        """

        args = "?filter_tvod=true"
        r = self._session.get(self._mubi_urls["film_groups"] + args)
        if r.status_code != 200:
            xbmc.log(
                "Invalid status code "
                + str(r.status_code)
                + " getting list of categories",
                4,
            )
            xbmc.log(self._mubi_urls["categories"] + args, 4)

        film_groups = ("".join(r.text)).encode("utf-8")

        categories = []
        for group in json.loads(film_groups):
            if group["type"] == "FilmGroup":
                r = self._session.get(urljoin(self._URL_MUBI, group["resource"]))

                film_group = json.loads(("".join(r.text)).encode("utf-8"))
                if film_group:
                    for item in film_group:
                        category = {
                            "title": item["full_title"],
                            "id": item["id"],
                            "description": item["description"],
                            "image": item["image"],
                            "type": group["type"],
                        }
                        xbmc.log("Ressource %s " % group["resource"], 1)
                        xbmc.log("Group title %s " % item["full_title"], 1)
                        categories.append(category)
            elif group["type"] == "FilmProgramming":
                category = {
                    "title": "Film of the day",
                    "id": "-1",
                    "description": "Movie of the day, for the past 30 days",
                    "image": "",
                    "type": group["type"],
                }
                categories.append(category)

        return categories

    def get_films_in_category_json(self, category):
        """
        Each category (such as Mubi top 1000) contains a list of films.
        This function queries the API and gets all the films in the category.

        """

        total_results = []

        # Grab the search results
        page_num = 1
        per_page = 20
        args = (
            "?page="
            + str(page_num)
            + "&per_page="
            + str(per_page)
            + "&filter_tvod=true"
        )
        response = self._session.get(
            self._mubi_urls["films_in_group"] % str(category) + args
        )
        data = response.json()

        # Store the first page of results
        total_results = total_results + data["film_group_items"]

        # While data['next'] isn't empty, let's download the next page, too
        for page_num in range(1, data["meta"]["total_pages"]):

            args = (
                "?page="
                + str(page_num)
                + "&per_page="
                + str(per_page)
                + "&filter_tvod=true"
            )
            response = self._session.get(
                self._mubi_urls["films_in_group"] % str(category) + args
            )
            data = response.json()
            # Store the current page of results
            total_results = total_results + data["film_group_items"]

        return total_results

    def get_film_metadata(self, film_overview, category_name):
        """
        For each film, this function will query the API to get the metadata.

        """
        film_id = film_overview["film"]["id"]

        available_at = str(datetime.date.today())
        if "available_at" in film_overview:
            available_at = dateutil.parser.parse(film_overview["available_at"])
            expires_at = dateutil.parser.parse(film_overview["expires_at"])

            # Check film is valid, has not expired and is not preview
            now = datetime.datetime.now(available_at.tzinfo)
            if available_at > now:
                xbmc.log("Film %s is not yet available" % film_id, 2)
                return None
            elif expires_at < now:
                xbmc.log("Film %s has expired" % film_id, 2)
                return None
            available_at = str(available_at)

        web_url = film_overview["film"]["web_url"]

        # Build film metadata object
        metadata = Metadata(
            title=film_overview["film"]["title"],
            director=film_overview["film"]["directors"],
            year=film_overview["film"]["year"],
            duration=film_overview["film"]["duration"],
            country=film_overview["film"]["historic_countries"],
            plot=film_overview["film"]["default_editorial"],
            plotoutline=film_overview["film"]["short_synopsis"],
            genre=film_overview["film"]["genres"],
            originaltitle=film_overview["film"]["original_title"],
            rating=film_overview["film"]["average_rating_out_of_ten"],
            votes=film_overview["film"]["number_of_ratings"],
            castandrole="",
            dateadded=available_at,
            trailer=film_overview["film"]["trailer_url"],
            image=film_overview["film"]["still_url"],
        )
        return Film(
            film_overview["film"]["title"],
            film_id,
            film_overview["film"]["stills"]["standard"],
            web_url,
            category_name,
            metadata,
        )
