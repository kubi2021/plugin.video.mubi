# -*- coding: utf-8 -*-
"""Tests for scripts/healthcheck.py status classification."""

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


def _response(status, headers=None):
    resp = MagicMock()
    resp.status_code = status
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

    def test_main_returns_nonzero_when_any_fail(self):
        with patch.object(healthcheck, "HEALTHCHECK_URLS", ["https://a", "https://b"]):
            with patch.object(
                healthcheck,
                "check",
                side_effect=[(True, "HTTP 200"), (False, "HTTP 404")],
            ):
                with patch.object(
                    healthcheck,
                    "check_activation_redirect",
                    return_value=(True, "HTTP 301 -> /tv/activate"),
                ):
                    assert healthcheck.main() == 1

    def test_main_returns_zero_when_all_pass(self):
        with patch.object(healthcheck, "HEALTHCHECK_URLS", ["https://a"]):
            with patch.object(healthcheck, "check", return_value=(True, "HTTP 200")):
                with patch.object(
                    healthcheck,
                    "check_activation_redirect",
                    return_value=(True, "HTTP 301 -> /tv/activate"),
                ):
                    assert healthcheck.main() == 0


class TestActivationRedirectCanary:
    def test_matching_relative_location_is_healthy(self):
        with patch.object(
            healthcheck,
            "ACTIVATION_EXPECTED_REDIRECT_PATH",
            "/tv/activate",
        ):
            with patch.object(
                healthcheck.requests,
                "get",
                return_value=_response(301, {"Location": "/tv/activate"}),
            ):
                ok, detail = healthcheck.check_activation_redirect()
        assert ok is True
        assert "/tv/activate" in detail

    def test_absolute_location_compares_by_path(self):
        with patch.object(
            healthcheck, "ACTIVATION_EXPECTED_REDIRECT_PATH", "/tv/activate"
        ):
            with patch.object(
                healthcheck.requests,
                "get",
                return_value=_response(
                    301, {"Location": "https://mubi.com/tv/activate"}
                ),
            ):
                ok, _ = healthcheck.check_activation_redirect()
        assert ok is True

    def test_drifted_location_fails_and_names_new_path(self):
        with patch.object(
            healthcheck, "ACTIVATION_EXPECTED_REDIRECT_PATH", "/tv/activate"
        ):
            with patch.object(
                healthcheck.requests,
                "get",
                return_value=_response(301, {"Location": "/connect/device"}),
            ):
                ok, detail = healthcheck.check_activation_redirect()
        assert ok is False
        assert "DRIFTED" in detail
        assert "/connect/device" in detail  # names the new path

    def test_non_redirect_status_fails(self):
        with patch.object(
            healthcheck.requests, "get", return_value=_response(200, {})
        ):
            ok, detail = healthcheck.check_activation_redirect()
        assert ok is False
        assert "200" in detail

    def test_unreachable_fails_gracefully(self):
        with patch.object(
            healthcheck.requests,
            "get",
            side_effect=requests.ConnectionError("boom"),
        ):
            ok, detail = healthcheck.check_activation_redirect()
        assert ok is False
        assert "unreachable" in detail

    def test_main_fails_when_canary_drifts(self):
        with patch.object(healthcheck, "HEALTHCHECK_URLS", ["https://a"]):
            with patch.object(healthcheck, "check", return_value=(True, "HTTP 200")):
                with patch.object(
                    healthcheck,
                    "check_activation_redirect",
                    return_value=(False, "activation URL DRIFTED"),
                ):
                    assert healthcheck.main() == 1
