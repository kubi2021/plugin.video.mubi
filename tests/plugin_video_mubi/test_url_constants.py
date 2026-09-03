# -*- coding: utf-8 -*-
"""Tests for the centralized external-URL constants (resources.lib.constants)."""

import re
import tokenize
from pathlib import Path

from resources.lib import constants


class TestUrlConstants:
    def test_all_urls_are_https(self):
        for name in (
            "MUBI_API_URL",
            "MUBI_WEB_URL",
            "MUBI_LOGIN_ACTIVATION_URL",
            "DRM_LICENSE_URL",
            "CATALOG_FILMS_URL",
            "TMDB_API_URL",
            "OMDB_API_URL",
            "IMDB_TITLE_URL_TEMPLATE",
        ):
            value = getattr(constants, name)
            assert value.startswith("https://"), f"{name} must be https"
        for value in constants.GEOIP_COUNTRY_URLS + constants.HEALTHCHECK_URLS:
            assert value.startswith("https://"), f"{value} must be https"

    def test_geoip_services_are_wired_into_country_detection(self):
        from resources.lib import mubi

        assert mubi.GEOIP_COUNTRY_URLS is constants.GEOIP_COUNTRY_URLS
        assert len(constants.GEOIP_COUNTRY_URLS) >= 2, "need a fallback chain"

    def test_metadata_providers_use_constants(self):
        from resources.lib.external_metadata import omdb_provider, tmdb_provider

        assert omdb_provider.OMDBProvider.API_URL == constants.OMDB_API_URL
        assert tmdb_provider.TMDBProvider.BASE_URL == constants.TMDB_API_URL

    def test_login_activation_url_is_current(self):
        # Guard the fix for the retired mubi.com/android page.
        assert constants.MUBI_LOGIN_ACTIVATION_URL == "https://mubi.com/tv"
        assert "android" not in constants.MUBI_LOGIN_ACTIVATION_URL

    def test_healthcheck_urls_cover_user_facing_endpoints(self):
        assert constants.MUBI_WEB_URL in constants.HEALTHCHECK_URLS
        assert constants.MUBI_LOGIN_ACTIVATION_URL in constants.HEALTHCHECK_URLS
        assert constants.CATALOG_FILMS_URL in constants.HEALTHCHECK_URLS

    def test_healthcheck_excludes_bare_api_base(self):
        # api.mubi.com/ returns 404 on a bare GET, so it must not be strict-checked.
        assert constants.MUBI_API_URL not in constants.HEALTHCHECK_URLS

    def test_data_source_uses_catalog_constant(self):
        from resources.lib import data_source

        assert data_source.GithubDataSource.GITHUB_URL == constants.CATALOG_FILMS_URL

    def test_activation_canary_suffix_matches_the_login_url(self):
        # scripts/healthcheck.py follows MUBI_LOGIN_ACTIVATION_URL's redirects and
        # requires the final path to end in this suffix, so the suffix must be a
        # path fragment and the login URL itself must satisfy it.
        from urllib.parse import urlsplit

        suffix = constants.MUBI_ACTIVATION_EXPECTED_PATH_SUFFIX
        assert suffix.startswith("/")
        login_path = urlsplit(constants.MUBI_LOGIN_ACTIVATION_URL).path.rstrip("/")
        assert login_path.endswith(suffix)


class TestNoUrlLiteralsOutsideConstants:
    """Tripwire for the CLAUDE.md rule "External URLs only in constants.py".

    Tokenises every plugin source file (comments are skipped, docstrings are
    not) and fails on any string literal carrying an http(s) URL outside
    constants.py. Loopback is the only allowed exception.
    """

    PLUGIN_ROOT = Path(__file__).resolve().parents[2] / "repo" / "plugin_video_mubi"
    URL_RE = re.compile(r"https?://[A-Za-z0-9]")  # scheme alone (session.mount) is not a URL
    ALLOWED_HOST_RE = re.compile(r"https?://127\.0\.0\.1")
    # py3.12+ splits f-strings into FSTRING_* tokens; 3.8-3.11 emit one STRING.
    STRING_TOKEN_TYPES = {tokenize.STRING} | (
        {tokenize.FSTRING_MIDDLE} if hasattr(tokenize, "FSTRING_MIDDLE") else set()
    )

    def _url_literals(self, path):
        with tokenize.open(path) as handle:
            for tok in tokenize.generate_tokens(handle.readline):
                if tok.type in self.STRING_TOKEN_TYPES and self.URL_RE.search(tok.string):
                    if not self.ALLOWED_HOST_RE.search(tok.string):
                        yield f"{path.relative_to(self.PLUGIN_ROOT)}:{tok.start[0]}: {tok.string.strip()[:80]}"

    def test_no_external_url_literals_outside_constants(self):
        offenders = []
        for path in sorted(self.PLUGIN_ROOT.rglob("*.py")):
            if path.name == "constants.py":
                continue
            offenders.extend(self._url_literals(path))

        assert offenders == [], (
            "External URL literals outside constants.py "
            "(move them there and import the name):\n  " + "\n  ".join(offenders)
        )
