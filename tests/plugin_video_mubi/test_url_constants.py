# -*- coding: utf-8 -*-
"""Tests for the centralized external-URL constants (resources.lib.constants)."""

from resources.lib import constants


class TestUrlConstants:
    def test_all_urls_are_https(self):
        for name in (
            "MUBI_API_URL",
            "MUBI_WEB_URL",
            "MUBI_LOGIN_ACTIVATION_URL",
            "DRM_LICENSE_URL",
            "CATALOG_FILMS_URL",
        ):
            value = getattr(constants, name)
            assert value.startswith("https://"), f"{name} must be https"

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

    def test_activation_drift_canary_baselines_present(self):
        assert constants.MUBI_ACTIVATION_PROBE_URL.startswith("https://")
        # The expected redirect target is compared as a path, so it must be one.
        assert constants.MUBI_ACTIVATION_EXPECTED_REDIRECT_PATH.startswith("/")
