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


def _response(status):
    resp = MagicMock()
    resp.status_code = status
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
                assert healthcheck.main() == 1

    def test_main_returns_zero_when_all_pass(self):
        with patch.object(healthcheck, "HEALTHCHECK_URLS", ["https://a"]):
            with patch.object(healthcheck, "check", return_value=(True, "HTTP 200")):
                assert healthcheck.main() == 0
