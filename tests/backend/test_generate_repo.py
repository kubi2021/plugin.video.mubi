"""Tests for backend/generate_repo.py.

Regression (hostile-audit F5): a missing input file must fail loudly
(sys.exit(1)), not return 0 and let a stale artifact deploy.
"""
import gzip
import hashlib
import json
import os
import sys

import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.generate_repo import generate_repo


def test_generate_repo_exits_on_missing_input(tmp_path):
    missing = tmp_path / "does_not_exist.json"
    with pytest.raises(SystemExit) as exc:
        generate_repo(str(missing))
    assert exc.value.code == 1


def test_generate_repo_writes_gz_and_matching_md5(tmp_path):
    src = tmp_path / "films.json"
    src.write_text(json.dumps({"items": [{"mubi_id": 1}]}), encoding="utf-8")

    generate_repo(str(src))

    gz = tmp_path / "films.json.gz"
    md5 = tmp_path / "films.json.gz.md5"
    assert gz.exists() and md5.exists()

    # The .gz decompresses back to the source, and the .md5 matches the .gz bytes.
    assert json.loads(gzip.decompress(gz.read_bytes())) == {"items": [{"mubi_id": 1}]}
    assert md5.read_text().strip() == hashlib.md5(gz.read_bytes()).hexdigest()
