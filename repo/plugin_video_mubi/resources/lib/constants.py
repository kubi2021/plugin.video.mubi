# -*- coding: utf-8 -*-

"""
Centralized external URLs and endpoints used by the plugin.

This module is intentionally dependency-free (no Kodi/`xbmc` imports) so it can
be imported both by the addon at runtime *and* by CI tooling such as the
endpoint healthcheck (`scripts/healthcheck.py`). Keeping every external URL in
one place means a third party moving/retiring a page (as Mubi did with the old
`https://mubi.com/android` login page) is caught in one auditable spot and can
be verified automatically.
"""

# --- Mubi ---------------------------------------------------------------

# Mubi REST API base.
MUBI_API_URL = "https://api.mubi.com/"

# Mubi website base. Used for Referer/Origin headers and client-country detection.
MUBI_WEB_URL = "https://mubi.com"

# Device / TV login activation page shown to the user during login.
# NOTE: Mubi retired the previous page (https://mubi.com/android -> 404); the
# device-code API response carries no URL, so this must be maintained here.
MUBI_LOGIN_ACTIVATION_URL = "https://mubi.com/tv"

# Widevine DRM license proxy used for playback.
DRM_LICENSE_URL = "https://lic.drmtoday.com/license-proxy-widevine/cenc/"


# --- Third-party services -------------------------------------------------

# IP geolocation services tried in order by Mubi.get_cli_country(). Each
# answers a bare GET with a 2-letter country code as plain text. Any one may
# vanish without notice (as https://mubi.com/android did), so the plugin falls
# through the list and the healthcheck watches the stable ones.
GEOIP_COUNTRY_URLS = [
    "https://get.geojs.io/v1/ip/country",
    "https://ifconfig.co/country-iso",
    "https://ipapi.co/country/",
    "https://ipinfo.io/country",
]

# External metadata providers (plugin-side legacy matcher; backend copy is canonical).
TMDB_API_URL = "https://api.themoviedb.org/3"
OMDB_API_URL = "https://www.omdbapi.com/"

# Public IMDb title page, used to build the imdb_url metadata field.
IMDB_TITLE_URL_TEMPLATE = "https://www.imdb.com/title/{imdb_id}/"


# --- Plugin's own hosted data -------------------------------------------

# Pre-computed, compressed catalog published on this repo's `database` branch.
CATALOG_FILMS_URL = (
    "https://github.com/kubi2021/plugin.video.mubi/raw/database/v1/films.json.gz"
)


# --- Healthcheck --------------------------------------------------------

# External URLs the plugin depends on that must return a successful (2xx/3xx)
# response. Checked on a schedule by scripts/healthcheck.py so that a retired or
# moved page is surfaced proactively instead of via a user bug report.
#
# The API base (MUBI_API_URL) is deliberately excluded: it returns 404 on a bare
# GET (there is no root endpoint), so it cannot be liveness-checked without an
# authenticated call. The DRM license endpoint is likewise excluded (it only
# responds to authenticated license POSTs).
#
# ipapi.co is excluded: it answers 403 to browser User-Agents and 200 to
# python-requests, i.e. it is bot-gated and would produce false alarms.
HEALTHCHECK_URLS = [
    MUBI_WEB_URL,
    MUBI_LOGIN_ACTIVATION_URL,
    CATALOG_FILMS_URL,
    "https://get.geojs.io/v1/ip/country",
    "https://ifconfig.co/country-iso",
    "https://ipinfo.io/country",
    TMDB_API_URL,  # bare GET -> 204
    OMDB_API_URL,  # bare GET -> 200 (JSON error body, no key needed)
]

# Activation-URL drift canary.
#
# `https://mubi.com/activate` is Mubi's server-side pointer to wherever device
# activation currently lives: it permanently (301) redirects to the real path.
# Today that first hop is `/tv/activate`. Watching *that Location header* is an
# authoritative early signal that Mubi moved the activation page (as it did when
# it retired /android): the redirect target changes before/independently of our
# hardcoded MUBI_LOGIN_ACTIVATION_URL breaking, and it names the new path.
#
# The healthcheck reads the first-hop Location (redirects OFF) and compares its
# path to the baseline below; a mismatch means "review the login URL". Only the
# path is compared, so Mubi returning an absolute vs relative Location is fine.
MUBI_ACTIVATION_PROBE_URL = "https://mubi.com/activate"
MUBI_ACTIVATION_EXPECTED_REDIRECT_PATH = "/tv/activate"
