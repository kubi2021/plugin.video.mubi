# -*- coding: utf-8 -*-
"""Tests for scripts/bump_version.py.

Regression for issue #48: the release workflow edited addon.xml with a greedy
`sed` over user-supplied release notes, which produced nested <news> tags (v27)
and re-breaks on sed/XML metacharacters. These tests feed adversarial notes and
assert the file stays valid XML with correct values.
"""

import importlib.util
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "bump_version.py"


def _load():
    spec = importlib.util.spec_from_file_location("bump_version", _SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bump_version = _load()


ADDON_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<addon id="plugin.video.mubi" name="MUBI" version="29" provider-name="kubi2021">\n'
    "  <extension point=\"xbmc.addon.metadata\">\n"
    "    <news>v29 - Old notes</news>\n"
    "  </extension>\n"
    "</addon>\n"
)


@pytest.fixture
def addon_file(tmp_path):
    path = tmp_path / "addon.xml"
    path.write_text(ADDON_XML, encoding="utf-8")
    return path


def _reparse(path):
    return ET.parse(str(path)).getroot()


def test_increments_version_and_sets_news(addon_file):
    new_version = bump_version.bump("Bug fixes and improvements", addon_file)

    assert new_version == 30
    root = _reparse(addon_file)
    assert root.get("version") == "30"
    assert root.find(".//news").text == "v30 - Bug fixes and improvements"


def test_apostrophe_does_not_corrupt_xml(addon_file):
    # The v27 failure class: an apostrophe in the notes.
    bump_version.bump("Fix Alice's watchlist", addon_file)

    root = _reparse(addon_file)  # raises if the file is not well-formed
    assert root.find(".//news").text == "v30 - Fix Alice's watchlist"


@pytest.mark.parametrize(
    "notes",
    [
        "amp & ampersand",
        'double "quotes" here',
        "angle <brackets> here",
        "sed pipe | delimiter",
        "sed backslash \\1 and replacement & chars",
        "everything ' \" & < > | \\ at once",
        "</news><news>injected second block",
    ],
)
def test_adversarial_notes_stay_valid_xml(addon_file, notes):
    bump_version.bump(notes, addon_file)

    # 1. Still well-formed XML.
    root = _reparse(addon_file)
    # 2. Exactly one <news> element (no nesting / no injected second block).
    news_elements = root.findall(".//news")
    assert len(news_elements) == 1
    # 3. The notes round-trip byte-for-byte through parse -> serialise -> parse.
    assert news_elements[0].text == "v30 - {}".format(notes)


def test_declaration_and_standalone_preserved(addon_file):
    bump_version.bump("keep the prolog", addon_file)

    first_line = addon_file.read_text(encoding="utf-8").splitlines()[0]
    assert first_line == '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'


def test_diff_is_only_the_two_intended_lines(tmp_path):
    """Bumping must not reformat unrelated lines (self-closing tags etc.)."""
    path = tmp_path / "addon.xml"
    original = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<addon id="plugin.video.mubi" name="MUBI" version="29" provider-name="kubi2021">\n'
        "  <requires>\n"
        '    <import addon="xbmc.python" version="3.0.1"/>\n'
        "  </requires>\n"
        '  <extension point="xbmc.addon.metadata">\n'
        "    <news>v29 - Old notes</news>\n"
        "  </extension>\n"
        "</addon>\n"
    )
    path.write_text(original, encoding="utf-8")

    bump_version.bump("New notes", path)

    original_lines = original.splitlines()
    new_lines = path.read_text(encoding="utf-8").splitlines()
    changed = [
        i for i, (a, b) in enumerate(zip(original_lines, new_lines)) if a != b
    ]
    assert len(original_lines) == len(new_lines)
    # Only the <addon ... version> line and the <news> line changed.
    assert changed == [1, 6]
    # Self-closing tag keeps the hand-authored `/>` (no space), not ET's ` />`.
    assert '    <import addon="xbmc.python" version="3.0.1"/>' in new_lines


def test_non_integer_version_rejected(tmp_path):
    path = tmp_path / "addon.xml"
    path.write_text(
        ADDON_XML.replace('version="29"', 'version="1.2.3"'), encoding="utf-8"
    )

    with pytest.raises(ValueError):
        bump_version.bump("notes", path)


def test_missing_news_element_rejected(tmp_path):
    path = tmp_path / "addon.xml"
    path.write_text(
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<addon id="plugin.video.mubi" name="MUBI" version="29">\n'
        "</addon>\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        bump_version.bump("notes", path)


def test_real_addon_xml_round_trips():
    """The script must handle the real repo addon.xml, not just the fixture."""
    real = (
        Path(__file__).resolve().parent.parent
        / "repo"
        / "plugin_video_mubi"
        / "addon.xml"
    )
    original = real.read_text(encoding="utf-8")
    try:
        current = int(ET.parse(str(real)).getroot().get("version"))
        new_version = bump_version.bump("adversarial ' \" & < > | test", real)
        assert new_version == current + 1
        root = ET.parse(str(real)).getroot()  # raises if malformed
        assert root.find(".//news").text == "v{} - adversarial ' \" & < > | test".format(
            new_version
        )
    finally:
        real.write_text(original, encoding="utf-8")
