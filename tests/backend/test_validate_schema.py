"""Tests for backend/validate_schema.py version gating.

Regression (hostile-audit F6): a file whose meta.version differs from the
requested schema version — or is missing entirely — must fail (sys.exit(1)),
not merely warn and validate against the wrong contract.
"""
import json
import os
import sys

import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# validate_schema hard-exits at import time if jsonschema is absent, and jsonschema
# is deliberately not a test dependency (see tests/backend/test_schema_v1.py). Skip
# the module if it is missing, matching that convention.
try:
    import jsonschema  # noqa: F401
except ImportError:
    pytest.skip("jsonschema not installed", allow_module_level=True)

from backend import validate_schema


def _run_main(path, version, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["validate_schema.py", "--path", str(path), "--version", str(version)])
    validate_schema.main()


def test_version_mismatch_exits(tmp_path, monkeypatch):
    f = tmp_path / "films.json"
    f.write_text(json.dumps({"meta": {"version": 2}, "items": []}), encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        _run_main(f, 1, monkeypatch)
    assert exc.value.code == 1


def test_missing_version_exits(tmp_path, monkeypatch):
    f = tmp_path / "films.json"
    f.write_text(json.dumps({"meta": {}, "items": []}), encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        _run_main(f, 1, monkeypatch)
    assert exc.value.code == 1
