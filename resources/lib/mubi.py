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

# try:
#     from simplecache import SimpleCache
# except:
#     from simplecachedummy import SimpleCache

APP_VERSION_CODE = '6.06'
ACCEPT_LANGUAGE = 'en-US'
CLIENT = 'android'
CLIENT_APP = 'mubi'
CLIENT_DEVICE_OS = '8.0'
USER_AGENT = 'Mozilla/5.0 (Linux; Android 8.0.0; SM-G960F Build/R16NW) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.84 Mobile Safari/537.36'

# All of the packet exchanges for the Android API were sniffed using the Packet Capture App
Film = namedtuple(
    'Film',
    ['title', 'mubi_id', 'artwork', 'web_url','metadata']
)

Metadata = namedtuple(
    'Metadata',
    ['title', 'director', 'year', 'duration', 'country', 'plot', 'plotoutline',
     'genre', 'originaltitle', 'rating', 'votes', 'castandrole', 'tagline', 'dateadded' ,'trailer', 'image']
)



class Mubi(object):
    _URL_MUBI = "https://mubi.com"
    _mubi_urls = {
        "login": urljoin(_URL_MUBI, "api/v2/sessions"),
        "startup": urljoin(_URL_MUBI, "api/v2/app_startup"),
        "films": urljoin(_URL_MUBI, "/api/v2/film_programmings"),
        # "film": urljoin(_URL_MUBI, "services/android/films/%s"),
        "set_watching": urljoin(_URL_MUBI, "api/v2/films/%s/playback_languages"),
        # "set_watching": urljoin(_URL_MUBI, "api/v1/films/%s/viewing/watching"),
        # "set_reel": urljoin(_URL_MUBI, "api/v1/films/%s/viewing/set_reel"),
        "set_reel": urljoin(_URL_MUBI, "api/v2/films/%s/viewing"),
        # "get_url": urljoin(_URL_MUBI, "api/v1/films/%s/reels/%s/secure_url")
        "get_url": urljoin(_URL_MUBI, "api/v2/films/%s/reels/%s/secure_url")
    }

    def __init__(self, username, password):
        self._username = username
        self._password = password
        self._cache_id = "plugin.video.mubi.filminfo.%s"
        # self._simplecache = SimpleCache()
        # Need a 20 digit id, hash username to make it predictable
        self._udid = int(hashlib.sha1(username.encode('utf-8')).hexdigest(), 32) % (10 ** 20)
        self._token = None
        self._userid = None
        self._country = None
        # The new mubi API (under the route /api/v1/[...] rather than /services/android) asks for these header fields:
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
        # When playing in external browser, no need to login
        # self.login()

    def login(self):
        payload = {
            'email': self._username,
            'password': self._password
        }
        xbmc.log("Logging in with username: %s and udid: %s" % (self._username, self._udid), 2)

        r = self._session.post(self._mubi_urls["login"], data=payload)
        result = (''.join(r.text)).encode('utf-8')

        if r.status_code == 200:
            self._token = json.loads(result)['token']
            self._userid = json.loads(result)['user']['id']
            self._session.headers.update({'authorization': "Bearer %s" % self._token})
            xbmc.log("Login Successful with token=%s and userid=%s" % (self._token, self._userid), 2)
            xbmc.log("Headers=%s" % self._session.headers, 2)
            xbmc.executebuiltin('Notification(%s, %s, %d, %s)'%("Mubi","Login Successful", 5000, '/script.hellow.world.png'))

        else:
            xbmc.log("Login Failed with result: %s" % result, 4)
            xbmc.executebuiltin('Notification(%s, %s, %d, %s)'%("Mubi","Login Failed: %s" % result, 5000, '/script.hellow.world.png'))

        # self.app_startup()
        # return r.status_code

    def app_startup(self):
        payload = {
            'udid': self._udid,
            'token': self._token,
            'client': 'android',
            'client_version': APP_VERSION_CODE
        }

        r = self._session.post(self._mubi_urls['startup'] + "?client=android", data=payload)

        print("fetching country: " + self._mubi_urls['startup'] + "?client=android")
        result = (''.join(r.text)).encode('utf-8')

        if r.status_code == 200:
            self._country = json.loads(result)['country']
            xbmc.log("Successfully got country as %s" % self._country, 2)
        else:
            xbmc.log("Failed to get country: %s" % result, 4)

        self.now_showing()
        return

    # def get_film_page(self, film_id):
    #     cached = self._simplecache.get(self._cache_id % film_id)
    #     if cached:
    #         return json.loads(cached)
    #
    #     args = "?country=%s" % self._country
    #     r = self._session.get((self._mubi_urls['film'] % str(film_id)) + args)
    #     print("getting film page " + self._mubi_urls['film'] % str(film_id) + args)
    #
    #     if r.status_code != 200:
    #         # xbmc.log("Invalid status code %s getting film info for %s" % (r.status_code, film_id), 4)
    #         print("Invalid status code %s getting film info for %s" % (r.status_code, film_id))
    #
    #     self._simplecache.set(self._cache_id % film_id, r.text, expiration=datetime.timedelta(days=32))
    #     return json.loads(r.text)

    def get_film_metadata(self, film_overview):
        film_id = film_overview['film']['id']
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

        web_url = film_overview['film']['web_url']

        # Get detailed look at film to get cast info
        # film_page = self.get_film_page(film_id)
        # cast = [(m['name'], m['credits']) for m in film_page['cast']]

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
            tagline=film_overview['our_take'],
            dateadded = film_overview['available_at'],
            trailer=film_overview['film']['trailer_url'],
            image = film_overview['film']['still_url']
        )
        return Film(film_overview['film']['title'], film_id, film_overview['film']['stills']['standard'], web_url, metadata)

    def get_now_showing_json(self):
        # Get list of available films
        args = "?accept-language=%s&client=%s&client-version=%s&client-device-identifier=%s&client-app=%s&client-device-os=%s" % (ACCEPT_LANGUAGE, CLIENT,APP_VERSION_CODE, self._udid, CLIENT_APP, CLIENT_DEVICE_OS)
        r = self._session.get(self._mubi_urls['films'] + args)
        if r.status_code != 200:
            xbmc.log("Invalid status code "+ str(r.status_code) + " getting list of films", 4)
            xbmc.log(self._mubi_urls['films'] + args, 4)
        return r.text

    def now_showing(self):
        films = [self.get_film_metadata(film) for film in json.loads(self.get_now_showing_json())]
        for f in films:
                print(f)
        return [f for f in films if f]

    # def set_reel(self, film_id, reel_id):
    #     # this calls tells the api that the user wants to select a reel other than the default reel (i.e.
    #     # they want to see another dub)
    #     payload = {'reel_id': reel_id}
    #     r = self._session.put((self._mubi_urls['set_reel'] % str(film_id)), data=payload)
    #     result = (''.join(r.text)).encode('utf-8')
    #     xbmc.log("Set reel response: %s" % result, 2)
    #     return r.status_code == 200
    #
    def set_watching(self, film_id):
        # this call tells the api that the user wants to watch a certain movie and returns the default reel id
        # payload = {'last_time_code': 0}
        # r = self._session.put((self._mubi_urls['set_watching'] % str(film_id)), data=payload)
        r = self._session.get((self._mubi_urls['set_watching'] % str(film_id)))
        result = (''.join(r.text)).encode('utf-8')
        if r.status_code == 200:
            return json.loads(result)["reels"][0]["id"]
        else:
            xbmc.log("Request was: %s" % r.url, 4)
            xbmc.log("Failed to obtain the reel id with result: %s" % result, 4)
        return -1
    #
    # def get_default_reel_id_is_drm(self, film_id):
    #     reel_id = [(f['reels'][0]['id'], f['reels'][0]['drm'])
    #                for f in json.loads(self.get_now_showing_json()) if str(f['id']) == str(film_id)]
    #     if len(reel_id) == 1:
    #         return reel_id[0]
    #     elif reel_id:
    #         xbmc.log("Multiple default_reel's returned for film %s: %s" % (film_id, ', '.join(reel_id)), 3)
    #         return reel_id[0]
    #     else:
    #         xbmc.log("Could not find default reel id for film %s" % film_id, 4)
    #         return None
    #
    # # function to obtain the film id from the web version of MUBI (not the API)
    # def get_film_id_by_web_url(self, mubi_url):
    #     import re, html
    #     r = self._session.get(
    #         mubi_url,
    #         headers = {
    #             'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.123 Safari/537.36'
    #         }
    #     )
    #     result = (''.join(r.text)).encode('utf-8')
    #     m = re.search('"film_id":([0-9]+)', result)
    #     film_id = m.group(1)
    #     reels = []
    #     # try:
    #     #     m = re.search('data-available-reels=\'([^\']+)\'', result)
    #     #     reels = json.loads(html.unescape(m.group(1)))
    #     # except: pass
    #     xbmc.log("Got film id: %s" % film_id, 3)
    #     return {"film_id": film_id, "reels": reels}
    #
    def get_play_url(self, film_id, reel_id = -1):
        # reels probably refer to different streams of the same movie (usually when the movie is available in two dub versions)
        # it is necessary to tell the API that one wants to watch a film before requesting the movie URL from the API, otherwise
        # the URL will not be delivered.
        # this can be done by either calling
        #     [1] api/v1/{film_id}/viewing/set_reel, or
        #     [2] api/v1/{film_id}/viewing/watching
        # the old behavior of the addon was calling [1], as the reel id could be known from loading the film list.
        # however, with the new feature of playing a movie by entering the MUBI web url, the reel id is not always known (i.e.
        # if the film is taken from the library, rather than from the "now showing" section).
        # by calling [2], the default reel id for a film (which is usually the original dub version of the movie) is returned.

        # <old>
        # (reel_id, is_drm) = self.get_default_reel_id_is_drm(film_id)

        # set the current reel before playing the movie (if the reel was never set, the movie URL will not be delivered)
        payload = {'reel_id': reel_id, 'sidecar_subtitle_language_code': 'eng'}
        r = self._session.post((self._mubi_urls['set_reel'] % str(film_id)), data=payload)
        result = (''.join(r.text)).encode('utf-8')
        xbmc.log("Set reel response: %s" % result, 2)
        # </old>

        # new: get the default reel id by calling api/v1/{film_id}/viewing/watching
        # if reel_id > 0:
        #     self.set_reel(film_id, reel_id)

        reel_id = self.set_watching(film_id)
        # is_drm = True  # let's just assume, that is_drm is always true

        # get the movie URL
        args = "?download=false" # "?country=%s&download=false" % (self._country)
        xbmc.log("Headers are: %s" % self._session.headers, 4)
        r = self._session.get((self._mubi_urls['get_url'] % (str(film_id), str(reel_id))) + args)
        result = (''.join(r.text)).encode('utf-8')
        if r.status_code != 200:
            xbmc.log("Could not get secure URL for film %s with reel_id=%s" % (film_id, reel_id), 4)
            xbmc.log("Request was: %s" % r.url, 4)
            xbmc.log("Request was: %s" % r.headers, 4)
            xbmc.log("Request was: %s" % r.cookies, 4)

        xbmc.log("Request was: %s" % r.url, 4)
        xbmc.log("Response was: (%s) %s" % (r.status_code, result), 2)
        # url = json.loads(result)["urls"][0]['src']
        url = json.loads(result)["url"]
        drm_asset_id = json.loads(result)["drm"]["asset_id"]

        # return the video info
        item_result = {
            'url': url,
            'is_mpd': "mpd" in url,
            'token': self._token,
            'userId': self._userid,
            'drm_asset_id' : drm_asset_id,
            # 'drm_header': base64.b64encode('{"userId":' + str(self._userid) + ',"sessionId":"' + self._token + '","merchant":"mubi"}') if is_drm else None
            'drm_header': base64.b64encode(('{"userId":' + str(self._userid) + ',"sessionId":"' + self._token + '","merchant":"mubi"}').encode())
            # 'drm_header': base64.b64encode(bytes('{"userId":' + str(self._userid) + ',"sessionId":"' + self._token + '","merchant":"mubi"}')) if is_drm else None
            # 'drm_header': None
        }
        # item_result = {
        #     'url': url,
        #     'is_mpd': "mpd" in url,
        #     'drm_header': None
        # }
        # xbmc.log("Got video info as: '%s'" % json.dumps(item_result), 2)
        return item_result
