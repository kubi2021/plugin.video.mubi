# -*- coding: utf-8 -*-
"""Tests for scripts/healthcheck.py: status classification and the
activation-page drift canary."""

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "healthcheck.py"


def _load():
    spec = importlib.util.spec_from_file_location("healthcheck", _SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


healthcheck = _load()


def _response(status, url="https://example.com", headers=None):
    """A requests.Response stand-in. `url` is the final URL after redirects."""
    resp = MagicMock()
    resp.status_code = status
    resp.url = url
    resp.headers = headers or {}
    return resp


class TestCheck:
    @pytest.mark.parametrize("status", [200, 201, 301, 302, 399])
    def test_success_and_redirect_are_healthy(self, status):
        with patch.object(healthcheck.requests, "get", return_value=_response(status)):
            ok, detail = healthcheck.check("https://example.com")
        assert ok is True
        assert str(status) in detail

    @pytest.mark.parametrize("status", [400, 404, 410, 500, 503])
    def test_client_and_server_errors_fail(self, status):
        with patch.object(healthcheck.requests, "get", return_value=_response(status)):
            ok, detail = healthcheck.check("https://example.com")
        assert ok is False
        assert str(status) in detail

    def test_unreachable_host_fails_gracefully(self):
        with patch.object(
            healthcheck.requests,
            "get",
            side_effect=requests.ConnectionError("boom"),
        ):
            ok, detail = healthcheck.check("https://nope.invalid")
        assert ok is False
        assert "unreachable" in detail


class TestMain:
    def test_main_returns_nonzero_when_any_fail(self):
        with patch.object(healthcheck, "HEALTHCHECK_URLS", ["https://a", "https://b"]):
            with patch.object(
                healthcheck,
                "check",
                side_effect=[(True, "HTTP 200"), (False, "HTTP 404")],
            ):
                with patch.object(
                    healthcheck,
                    "check_activation_page",
                    return_value=(True, "HTTP 200 -> /en/tv"),
                ):
                    assert healthcheck.main() == 1

    def test_main_returns_zero_when_all_pass(self):
        with patch.object(healthcheck, "HEALTHCHECK_URLS", ["https://a"]):
            with patch.object(healthcheck, "check", return_value=(True, "HTTP 200")):
                with patch.object(
                    healthcheck,
                    "check_activation_page",
                    return_value=(True, "HTTP 200 -> /en/tv"),
                ):
                    assert healthcheck.main() == 0

    def test_main_fails_when_canary_drifts(self):
        with patch.object(healthcheck, "HEALTHCHECK_URLS", ["https://a"]):
            with patch.object(healthcheck, "check", return_value=(True, "HTTP 200")):
                with patch.object(
                    healthcheck,
                    "check_activation_page",
                    return_value=(False, "activation URL DRIFTED"),
                ):
                    assert healthcheck.main() == 1


class TestActivationPageCanary:
    """The canary follows MUBI_LOGIN_ACTIVATION_URL's redirect chain and judges
    where it *lands*, never a first-hop Location (hostile audit of PR 58, F1:
    mubi.com 301s /activate -> /tv/activate, which itself 404s)."""

    def _run(self, response, suffix="/tv"):
        with patch.object(healthcheck, "ACTIVATION_URL", "https://mubi.com/tv"):
            with patch.object(healthcheck, "ACTIVATION_EXPECTED_PATH_SUFFIX", suffix):
                with patch.object(healthcheck.requests, "get", **response) as get:
                    result = healthcheck.check_activation_page()
        return result, get

    def test_locale_prefixed_final_page_is_healthy(self):
        (ok, detail), _ = self._run({"return_value": _response(200, "https://mubi.com/en/tv")})
        assert ok is True
        assert "/en/tv" in detail

    def test_other_locale_prefix_is_not_drift(self):
        (ok, _), _ = self._run({"return_value": _response(200, "https://mubi.com/de/tv")})
        assert ok is True

    def test_trailing_slash_is_not_drift(self):
        (ok, _), _ = self._run({"return_value": _response(200, "https://mubi.com/en/tv/")})
        assert ok is True

    def test_drifted_final_path_fails_and_names_new_path(self):
        (ok, detail), _ = self._run(
            {"return_value": _response(200, "https://mubi.com/connect/device")}
        )
        assert ok is False
        assert "DRIFTED" in detail
        assert "/connect/device" in detail  # names the new path

    def test_canary_fails_when_followed_target_is_not_2xx(self):
        # Regression for F1: /activate -> 301 /tv/activate -> ... -> 404. A chain
        # that ends on an error page is unhealthy even if the path looks right.
        (ok, detail), _ = self._run(
            {"return_value": _response(404, "https://mubi.com/en/tv/tv/activate")}
        )
        assert ok is False
        assert "404" in detail

    def test_unreachable_fails_gracefully(self):
        (ok, detail), _ = self._run({"side_effect": requests.ConnectionError("boom")})
        assert ok is False
        assert "unreachable" in detail

    def test_canary_probes_the_url_the_user_is_shown(self):
        # The canary must check the login URL the plugin displays, not a probe
        # URL whose redirect happens to look authoritative.
        (ok, _), get = self._run({"return_value": _response(200, "https://mubi.com/en/tv")})
        assert get.call_args.args[0] == "https://mubi.com/tv"
        assert healthcheck.ACTIVATION_URL == healthcheck._constants.MUBI_LOGIN_ACTIVATION_URL
