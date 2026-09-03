"""CI gate: every sync workflow must register each OMDb key with ::add-mask:: first.

GitHub masks a secret only as its exact full string, and OMDB_API_KEYS is a
comma-separated list, so without this step a single key could appear verbatim in
a public run log. Text-based on purpose: the repo has no YAML dependency.
"""

import re
from pathlib import Path

import pytest

WORKFLOWS = Path(__file__).resolve().parents[2] / ".github" / "workflows"
SYNC_WORKFLOWS = sorted(WORKFLOWS.glob("mubi_*_sync.yml"))
STEP_RE = re.compile(r"^    - name: (.*)$", re.MULTILINE)


def _step_names(text):
    return STEP_RE.findall(text)


def test_sync_workflows_are_discovered():
    assert [p.name for p in SYNC_WORKFLOWS] == [
        "mubi_deep_sync.yml",
        "mubi_shallow_sync.yml",
        "mubi_test_sync.yml",
    ]


@pytest.mark.parametrize("path", SYNC_WORKFLOWS, ids=lambda p: p.name)
def test_first_step_masks_each_omdb_key(path):
    text = path.read_text()
    steps = _step_names(text)

    assert steps, f"{path.name}: no steps found"
    assert steps[0] == "Mask individual OMDb keys in logs", (
        f"{path.name}: the mask step must run first, found {steps[0]!r}"
    )
    mask_block = text.split("- name: Mask individual OMDb keys in logs", 1)[1].split("- name:", 1)[0]
    assert "OMDB_API_KEYS: ${{ secrets.OMDB_API_KEYS }}" in mask_block
    assert "IFS=','" in mask_block, "keys must be split on commas"
    assert '::add-mask::$key' in mask_block


@pytest.mark.parametrize("path", SYNC_WORKFLOWS, ids=lambda p: p.name)
def test_mask_step_precedes_every_use_of_the_omdb_secret(path):
    text = path.read_text()
    first_mask = text.index("- name: Mask individual OMDb keys in logs")
    uses = [m.start() for m in re.finditer(r"OMDB_API_KEYS: \$\{\{ secrets\.OMDB_API_KEYS \}\}", text)]

    assert len(uses) >= 2, f"{path.name}: expected the secret in the mask step and the enrich step"
    assert all(first_mask < u for u in uses[1:])
