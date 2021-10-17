# -*- coding: utf-8 -*-
import datetime
import dateutil.parser
import requests
import json
import hashlib
import base64
from collections import namedtuple
import xbmc
from urllib.parse import urljoin


APP_VERSION_CODE = '6.06'
ACCEPT_LANGUAGE = 'en-US'
CLIENT = 'android'
CLIENT_APP = 'mubi'
CLIENT_DEVICE_OS = '8.0'
USER_AGENT = 'Mozilla/5.0 (Linux; Android 8.0.0; SM-G960F Build/R16NW) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.84 Mobile Safari/537.36'


Film = namedtuple(
    'Film',
    ['title', 'mubi_id', 'artwork', 'web_url', 'category','metadata']
)

Metadata = namedtuple(
    'Metadata',
    ['title', 'director', 'year', 'duration', 'country', 'plot', 'plotoutline',
     'genre', 'originaltitle', 'rating', 'votes', 'castandrole', 'dateadded' ,'trailer', 'image']
)

class Mubi(object):
    _URL_MUBI = "https://mubi.com"
    _mubi_urls = {
        "login": urljoin(_URL_MUBI, "api/v2/sessions"),
        "startup": urljoin(_URL_MUBI, "api/v2/app_startup"),
        "films": urljoin(_URL_MUBI, "/api/v2/film_programmings"),
        "film_groups": urljoin(_URL_MUBI, "/api/v2/layout"),
        "films_in_group": urljoin(_URL_MUBI, "/api/v2/film_groups/%s/film_group_items"),
        "set_watching": urljoin(_URL_MUBI, "api/v2/films/%s/playback_languages"),
        "set_reel": urljoin(_URL_MUBI, "api/v2/films/%s/viewing"),
        "get_url": urljoin(_URL_MUBI, "api/v2/films/%s/reels/%s/secure_url")
    }

    def __init__(self, username, password):
        self._username = username
        self._password = password
        self._cache_id = "plugin.video.mubi.filminfo.%s"
        # Need a 20 digit id, hash username to make it predictable
        self._udid = int(hashlib.sha1(username.encode('utf-8')).hexdigest(), 32) % (10 ** 20)
        self._token = None
        self._userid = None
        self._country = None
        self._session = requests.Session()
        self._session.headers.update({
            'accept-language': ACCEPT_LANGUAGE,
            'client': CLIENT,
            'client-version': APP_VERSION_CODE,
            'client-app': CLIENT_APP,
            'client-device-os': CLIENT_DEVICE_OS,
            'user-agent': USER_AGENT,
            'if-none-match': 'W/"505d0033184d7877a3b351d8c94b6211"',
            'accept': 'application/json, text/plain, */*',
            'client-device-identifier': str(self._udid)
        })

    def get_film_list(self, type, id, category_name):
        """
        Mubi has 2 categories of films:
        - Filmprogramming: the movie of the day, available for 30 days
        - Film Group: each film group call returns multiple categories, such as Top 1000, or Mubi releases, for example.

        This function query the list of films and then query the metadata for each film.
        Ultimately, it returns a nametupl of films.
        """


        if type=="FilmProgramming":
             films = [self.get_film_metadata(film, category_name) for film in (self.get_now_showing_json())]
        elif type=="FilmGroup":
             films = [self.get_film_metadata(film, category_name) for film in (self.get_films_in_category_json(id))]

        return [f for f in films if f]

    def get_now_showing_json(self):
        """
        Calls the API and get the list of the 30 films of the day.

        """
        # Get list of available films
        args = "?accept-language=%s&client=%s&client-version=%s&client-device-identifier=%s&client-app=%s&client-device-os=%s" % (ACCEPT_LANGUAGE, CLIENT,APP_VERSION_CODE, self._udid, CLIENT_APP, CLIENT_DEVICE_OS)
        r = self._session.get(self._mubi_urls['films'] + args)
        if r.status_code != 200:
            xbmc.log("Invalid status code for films of the day: "+ str(r.status_code) + " getting list of films", 4)
            xbmc.log(self._mubi_urls['films'] + args, 4)
        return r.json()


    def get_film_groups(self):
        """
        Query film groups. Each call to film groups returns one or many film category, such as Top 1000, or Mubi releases, for example.

        It will return a list of category.

        """

        args = "?filter_tvod=true"
        r = self._session.get(self._mubi_urls['film_groups'] + args)
        if r.status_code != 200:
            xbmc.log("Invalid status code "+ str(r.status_code) + " getting list of categories", 4)
            xbmc.log(self._mubi_urls['categories'] + args, 4)

        film_groups = (''.join(r.text)).encode('utf-8')

        categories = []
        for group in json.loads(film_groups):
            if group["type"] == "FilmGroup":
                r = self._session.get(urljoin(self._URL_MUBI, group["resource"]))

                film_group = json.loads((''.join(r.text)).encode('utf-8'))
                if film_group:
                    for item in film_group:
                        category = {
                            "title": item["full_title"],
                            "id": item["id"],
                            "description": item["description"],
                            "image": item["image"],
                            "type": group["type"]
                        }
                        xbmc.log("Ressource %s " % group["resource"], 1)
                        xbmc.log("Group title %s " % item["full_title"], 1)
                        categories.append(category)
            elif group["type"] == "FilmProgramming":
                category = {
                    "title": "Film of the day",
                    "id": '-1',
                    "description": "Movie of the day, for the past 30 days",
                    "image": "",
                    "type": group["type"]
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
        args = "?page="+ str(page_num) + "&per_page="+ str(per_page) +"&filter_tvod=true"
        response = self._session.get(self._mubi_urls['films_in_group'] % str(category) + args)
        data = response.json()

        # Store the first page of results
        total_results = total_results + data["film_group_items"]

        # While data['next'] isn't empty, let's download the next page, too
        for page_num in range(1, data['meta']['total_pages']):

            args = "?page="+ str(page_num) + "&per_page="+ str(per_page) +"&filter_tvod=true"
            response = self._session.get(self._mubi_urls['films_in_group'] % str(category) + args)
            data = response.json()
            # Store the current page of results
            total_results = total_results + data["film_group_items"]

        return total_results


    def get_film_metadata(self, film_overview, category_name):
        """
        For each film, this function will query the API to get the metadata.

        """
        film_id = film_overview['film']['id']

        available_at = str(datetime.date.today())
        if "available_at" in film_overview:
            available_at = dateutil.parser.parse(film_overview['available_at'])
            expires_at = dateutil.parser.parse(film_overview['expires_at'])

            # Check film is valid, has not expired and is not preview
            now = datetime.datetime.now(available_at.tzinfo)
            if available_at > now:
                xbmc.log("Film %s is not yet available" % film_id, 2)
                return None
            elif expires_at < now:
                xbmc.log("Film %s has expired" % film_id, 2)
                return None
            available_at = str(available_at)

        web_url = film_overview['film']['web_url']

        # Build film metadata object
        metadata = Metadata(
            title=film_overview['film']['title'],
            director=film_overview['film']['directors'],
            year=film_overview['film']['year'],
            duration=film_overview['film']['duration'] * 60,  # This is in seconds
            country=film_overview['film']['historic_countries'],
            plot=film_overview['film']['default_editorial'],
            plotoutline = film_overview['film']['short_synopsis'],
            genre=', '.join(film_overview['film']['genres']),
            originaltitle=film_overview['film']['original_title'],
            rating=film_overview['film']['average_rating_out_of_ten'],
            votes=film_overview['film']['number_of_ratings'],
            castandrole="",
            dateadded = available_at,
            trailer=film_overview['film']['trailer_url'],
            image = film_overview['film']['still_url']
        )
        return Film(film_overview['film']['title'], film_id, film_overview['film']['stills']['standard'], web_url, category_name, metadata)




###### DRM SECTION #######

# The functions below will be needed in order to loads
# the films within Kodi, with DRMs

# def login(self):
#     payload = {
#         'email': self._username,
#         'password': self._password
#     }
#     xbmc.log("Logging in with username: %s and udid: %s" % (self._username, self._udid), 2)
#
#     r = self._session.post(self._mubi_urls["login"], data=payload)
#     result = (''.join(r.text)).encode('utf-8')
#
#     if r.status_code == 200:
#         self._token = json.loads(result)['token']
#         self._userid = json.loads(result)['user']['id']
#         self._session.headers.update({'authorization': "Bearer %s" % self._token})
#         xbmc.log("Login Successful with token=%s and userid=%s" % (self._token, self._userid), 2)
#         xbmc.log("Headers=%s" % self._session.headers, 2)
#         xbmc.executebuiltin('Notification(%s, %s, %d, %s)'%("Mubi","Login Successful", 5000, '/script.hellow.world.png'))
#
#     else:
#         xbmc.log("Login Failed with result: %s" % result, 4)
#         xbmc.executebuiltin('Notification(%s, %s, %d, %s)'%("Mubi","Login Failed: %s" % result, 5000, '/script.hellow.world.png'))
#
#     return r.status_code
#
# def app_startup(self):
#     payload = {
#         'udid': self._udid,
#         'token': self._token,
#         'client': 'android',
#         'client_version': APP_VERSION_CODE
#     }
#
#     r = self._session.post(self._mubi_urls['startup'] + "?client=android", data=payload)
#
#     print("fetching country: " + self._mubi_urls['startup'] + "?client=android")
#     result = (''.join(r.text)).encode('utf-8')
#
#     if r.status_code == 200:
#         self._country = json.loads(result)['country']
#         xbmc.log("Successfully got country as %s" % self._country, 2)
#     else:
#         xbmc.log("Failed to get country: %s" % result, 4)
#
#     self.now_showing()
#     return



    # def get_play_url(self, film_id, reel_id = -1):
    #     # reels probably refer to different streams of the same movie (usually when the movie is available in two dub versions)
    #     # it is necessary to tell the API that one wants to watch a film before requesting the movie URL from the API, otherwise
    #     # the URL will not be delivered.
    #     # this can be done by either calling
    #     #     [1] api/v1/{film_id}/viewing/set_reel, or
    #     #     [2] api/v1/{film_id}/viewing/watching
    #     # the old behavior of the addon was calling [1], as the reel id could be known from loading the film list.
    #     # however, with the new feature of playing a movie by entering the MUBI web url, the reel id is not always known (i.e.
    #     # if the film is taken from the library, rather than from the "now showing" section).
    #     # by calling [2], the default reel id for a film (which is usually the original dub version of the movie) is returned.
    #
    #     # set the current reel before playing the movie (if the reel was never set, the movie URL will not be delivered)
    #     payload = {'reel_id': reel_id, 'sidecar_subtitle_language_code': 'eng'}
    #     r = self._session.post((self._mubi_urls['set_reel'] % str(film_id)), data=payload)
    #     result = (''.join(r.text)).encode('utf-8')
    #     xbmc.log("Set reel response: %s" % result, 2)
    #
    #     reel_id = self.set_watching(film_id)
    #
    #     # get the movie URL
    #     args = "?download=false"
    #     xbmc.log("Headers are: %s" % self._session.headers, 4)
    #     r = self._session.get((self._mubi_urls['get_url'] % (str(film_id), str(reel_id))) + args)
    #     result = (''.join(r.text)).encode('utf-8')
    #     if r.status_code != 200:
    #         xbmc.log("Could not get secure URL for film %s with reel_id=%s" % (film_id, reel_id), 4)
    #         xbmc.log("Request was: %s" % r.url, 4)
    #         xbmc.log("Request was: %s" % r.headers, 4)
    #         xbmc.log("Request was: %s" % r.cookies, 4)
    #
    #     xbmc.log("Request was: %s" % r.url, 4)
    #     xbmc.log("Response was: (%s) %s" % (r.status_code, result), 2)
    #     url = json.loads(result)["url"]
    #     drm_asset_id = json.loads(result)["drm"]["asset_id"]
    #
    #     # return the video info
    #     item_result = {
    #         'url': url,
    #         'is_mpd': "mpd" in url,
    #         'token': self._token,
    #         'userId': self._userid,
    #         'drm_asset_id' : drm_asset_id,
    #         'drm_header': base64.b64encode(('{"userId":' + str(self._userid) + ',"sessionId":"' + self._token + '","merchant":"mubi"}').encode())
    #     }
    #
    #     return item_result

    # def set_watching(self, film_id):
    #     # this call tells the api that the user wants to watch a certain movie and returns the default reel id
    #
    #     r = self._session.get((self._mubi_urls['set_watching'] % str(film_id)))
    #     result = (''.join(r.text)).encode('utf-8')
    #     if r.status_code == 200:
    #         return json.loads(result)["reels"][0]["id"]
    #     else:
    #         xbmc.log("Request was: %s" % r.url, 4)
    #         xbmc.log("Failed to obtain the reel id with result: %s" % result, 4)
    #     return -1
