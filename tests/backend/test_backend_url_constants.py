"""Tests for backend.external_urls: shape, tripwire, and agreement with the plugin."""

import importlib.util
import re
import tokenize
from pathlib import Path

import pytest

from backend import external_urls as constants

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
PLUGIN_CONSTANTS = REPO_ROOT / "repo" / "plugin_video_mubi" / "resources" / "lib" / "constants.py"


def _load_plugin_constants():
    # By path, like scripts/healthcheck.py: avoids importing the Kodi package.
    spec = importlib.util.spec_from_file_location("plugin_constants_for_test", PLUGIN_CONSTANTS)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestBackendUrlConstants:
    def test_all_urls_are_https(self):
        for name in ("MUBI_API_V4_URL", "MUBI_WEB_URL", "TMDB_API_URL", "OMDB_API_URL", "IMDB_TITLE_URL_TEMPLATE"):
            assert getattr(constants, name).startswith("https://"), f"{name} must be https"

    @pytest.mark.parametrize("name", ["MUBI_WEB_URL", "TMDB_API_URL", "OMDB_API_URL", "IMDB_TITLE_URL_TEMPLATE"])
    def test_shared_values_agree_with_plugin_constants(self, name):
        plugin = _load_plugin_constants()
        assert getattr(constants, name) == getattr(plugin, name), (
            f"{name} differs between backend/external_urls.py and the plugin constants; change both or neither"
        )

    def test_scraper_and_providers_use_constants(self):
        from backend.omdb_provider import OMDBProvider
        from backend.scraper import MubiScraper
        from backend.tmdb_provider import TMDBProvider

        assert MubiScraper.BASE_URL == constants.MUBI_API_V4_URL
        assert OMDBProvider.BASE_URL == constants.OMDB_API_URL
        assert TMDBProvider.BASE_URL == constants.TMDB_API_URL


class TestNoUrlLiteralsOutsideConstants:
    """Tripwire: no http(s) literal in backend/*.py outside constants.py."""

    URL_RE = re.compile(r"https?://[A-Za-z0-9]")  # a bare scheme (session.mount) is not a URL
    STRING_TOKEN_TYPES = {tokenize.STRING} | (
        {tokenize.FSTRING_MIDDLE} if hasattr(tokenize, "FSTRING_MIDDLE") else set()
    )

    def _url_literals(self, path):
        with tokenize.open(path) as handle:
            for tok in tokenize.generate_tokens(handle.readline):
                if tok.type in self.STRING_TOKEN_TYPES and self.URL_RE.search(tok.string):
                    yield f"{path.relative_to(BACKEND_ROOT)}:{tok.start[0]}: {tok.string.strip()[:80]}"

    def test_no_external_url_literals_outside_constants(self):
        offenders = []
        for path in sorted(BACKEND_ROOT.glob("*.py")):
            if path.name == "external_urls.py":
                continue
            offenders.extend(self._url_literals(path))
        assert offenders == [], (
            "External URL literals outside backend/external_urls.py "
            "(move them there and import the name):\n  " + "\n  ".join(offenders)
        )
