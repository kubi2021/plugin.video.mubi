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
CATALOG_FILMS_URL = "https://github.com/kubi2021/plugin.video.mubi/raw/database/v1/films.json.gz"


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
# Two of the four GEOIP_COUNTRY_URLS are deliberately NOT healthchecked because
# they are bot-gated and would fire false alarms while still being fine for real
# (residential) plugin users:
#   - ipapi.co answers 403 to browser User-Agents and 200 to python-requests.
#   - ifconfig.co is Cloudflare-fronted and 403s datacenter IPs (the GitHub
#     Actions runner) while returning 200 for residential IPs. Observed live:
#     issue #62, run 33742252948 -> HTTP 403 from the runner, 200 from a laptop.
# geojs.io and ipinfo.io answer a bare GET with a country code from any IP, so
# they stand in for the fallback chain's liveness.
HEALTHCHECK_URLS = [
    MUBI_WEB_URL,
    MUBI_LOGIN_ACTIVATION_URL,
    CATALOG_FILMS_URL,
    "https://get.geojs.io/v1/ip/country",
    "https://ipinfo.io/country",
    TMDB_API_URL,  # bare GET -> 204
    OMDB_API_URL,  # bare GET -> 200 (JSON error body, no key needed)
]

# Activation-URL drift canary.
#
# scripts/healthcheck.py follows MUBI_LOGIN_ACTIVATION_URL's redirect chain (the
# page the user is told to open) and requires that it lands on a successful
# status with a final path ending in the suffix below. Mubi prefixes a locale
# (/tv -> /en/tv), so only the suffix is compared: a different locale on the CI
# runner is not drift, while a move to e.g. /connect/device is, and the failure
# message names the new path.
#
# Do NOT baseline on a first-hop Location header: mubi.com 301s /activate,
# /tv/activate and the retired /android alike to /tv/<path>, and those then
# 404. That is a legacy rewrite rule, not a pointer to the activation page.
MUBI_ACTIVATION_EXPECTED_PATH_SUFFIX = "/tv"
