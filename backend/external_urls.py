"""
Centralized external URLs used by the backend pipeline.

Mirror of the plugin's ``resources/lib/constants.py`` for the values both
sides share (Mubi web origin, TMDb/OMDb bases, IMDb title template). The two
modules stay independent so neither imports the other's package. This file is
deliberately NOT named ``constants.py``: the plugin module falls back to a bare
``import constants`` in some test harnesses and a same-named backend module on
sys.path would shadow it;
``tests/backend/test_backend_url_constants.py`` asserts the shared values agree, so
a change on one side that is not mirrored fails CI instead of drifting.
"""

# Mubi REST API v4 base used by the scraper.
MUBI_API_V4_URL = "https://api.mubi.com/v4"

# Mubi website origin, sent as Origin/Referer on scraper requests.
MUBI_WEB_URL = "https://mubi.com"

# External metadata providers (backend copies are canonical).
TMDB_API_URL = "https://api.themoviedb.org/3"
OMDB_API_URL = "https://www.omdbapi.com/"

# Public IMDb title page, used to build the imdb_url metadata field.
IMDB_TITLE_URL_TEMPLATE = "https://www.imdb.com/title/{imdb_id}/"
