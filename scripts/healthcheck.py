#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
External-endpoint healthcheck.

Requests every URL the plugin depends on (see
`repo/plugin_video_mubi/resources/lib/constants.py::HEALTHCHECK_URLS`) and fails
if any returns an unsuccessful HTTP status or is unreachable.

This exists because a third party retiring/moving a page it hosts (e.g. Mubi
retiring https://mubi.com/android -> 404, which silently broke plugin login) is
invisible to unit tests: the hardcoded string is still "correct", only the
remote server changed. Only a live request against the real URL catches it.

Run locally:   python scripts/healthcheck.py
Exit code 0 = all healthy, 1 = one or more failed.
"""

import importlib.util
import sys
from pathlib import Path
from urllib.parse import urlsplit

import requests

# Import the constants module directly by path so we don't pull in the Kodi
# addon package (which imports `xbmc` and friends unavailable in CI).
_CONSTANTS_PATH = (
    Path(__file__).resolve().parent.parent
    / "repo"
    / "plugin_video_mubi"
    / "resources"
    / "lib"
    / "constants.py"
)

_spec = importlib.util.spec_from_file_location("mubi_constants", _CONSTANTS_PATH)
_constants = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_constants)

HEALTHCHECK_URLS = _constants.HEALTHCHECK_URLS
ACTIVATION_URL = _constants.MUBI_LOGIN_ACTIVATION_URL
ACTIVATION_EXPECTED_PATH_SUFFIX = _constants.MUBI_ACTIVATION_EXPECTED_PATH_SUFFIX

# A real browser UA; some sites reject the default requests UA with a 403.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) "
    "Gecko/20100101 Firefox/125.0"
)
TIMEOUT = 20


def check(url):
    """Return (ok: bool, detail: str) for a single URL."""
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=TIMEOUT,
            allow_redirects=True,
        )
    except requests.RequestException as exc:
        return False, f"unreachable: {exc.__class__.__name__}: {exc}"

    # 2xx and 3xx are healthy; 4xx/5xx mean the page is gone or broken.
    if resp.status_code < 400:
        return True, f"HTTP {resp.status_code}"
    return False, f"HTTP {resp.status_code}"


def check_activation_page():
    """Drift canary for the device-activation URL.

    Follows `MUBI_LOGIN_ACTIVATION_URL`'s redirect chain -- the page the user is
    told to open -- and judges where it *lands*: the final status must be
    successful and the final path must end in `ACTIVATION_EXPECTED_PATH_SUFFIX`.
    Mubi prefixes a locale (/tv -> /en/tv), so only the suffix is compared; a
    move to e.g. /connect/device is reported by name.

    Deliberately not a first-hop Location check: mubi.com 301s /activate,
    /tv/activate and the retired /android alike to /tv/<path>, which then 404s.
    That is a legacy rewrite rule, not a pointer to the activation page, and a
    baseline built on it reports "healthy" for a dead target.

    Return (ok: bool, detail: str).
    """
    try:
        resp = requests.get(
            ACTIVATION_URL,
            headers={"User-Agent": USER_AGENT},
            timeout=TIMEOUT,
            allow_redirects=True,
        )
    except requests.RequestException as exc:
        return False, f"unreachable: {exc.__class__.__name__}: {exc}"

    final_path = urlsplit(resp.url).path
    if resp.status_code >= 400:
        return False, (
            f"activation page {ACTIVATION_URL} ends at {final_path!r} with "
            f"HTTP {resp.status_code} -- update MUBI_LOGIN_ACTIVATION_URL in constants.py"
        )
    if final_path.rstrip("/").endswith(ACTIVATION_EXPECTED_PATH_SUFFIX):
        return True, f"HTTP {resp.status_code} -> {final_path}"
    return False, (
        f"activation URL DRIFTED: {ACTIVATION_URL} now resolves to {final_path!r} "
        f"(expected a path ending in {ACTIVATION_EXPECTED_PATH_SUFFIX!r}) -- update "
        f"MUBI_LOGIN_ACTIVATION_URL / the suffix in constants.py"
    )


def main():
    print("Checking external endpoints the plugin depends on...\n")
    failures = []
    for url in HEALTHCHECK_URLS:
        ok, detail = check(url)
        symbol = "OK  " if ok else "FAIL"
        print(f"  [{symbol}] {url}  ({detail})")
        if not ok:
            failures.append((url, detail))

    # Drift canary (separate from the plain 200 checks above).
    ok, detail = check_activation_page()
    symbol = "OK  " if ok else "FAIL"
    print(f"  [{symbol}] activation-page canary  ({detail})")
    if not ok:
        failures.append((ACTIVATION_URL, detail))

    total = len(HEALTHCHECK_URLS) + 1
    print()
    if failures:
        print(f"{len(failures)} of {total} check(s) FAILED:")
        for url, detail in failures:
            print(f"  - {url}: {detail}")
        return 1

    print(f"All {total} checks healthy.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
