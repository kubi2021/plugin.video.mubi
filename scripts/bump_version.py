#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Bump the plugin version and set the release news in `addon.xml`.

This exists because the release workflow used to edit `addon.xml` with `sed`
(a greedy `s|<news>.*</news>|...|` plus a hand-rolled XML escape table over
user-supplied release notes). In v27 that produced nested `<news>` tags, and
the same construction re-breaks on any note containing `sed` metacharacters
(`|`, `&`, `\\`) or a second `<news>` block. Parsing with a real XML parser is
the only robust fix (see DEVELOPMENT_PRINCIPLES.md P8).

The version is an integer; this reads the current value, increments it by one,
and writes both the `version` attribute and the `<news>` text back in a single
parser pass -- no `sed`, no manual escaping.

Run:  python3 scripts/bump_version.py --notes "Bug fixes and improvements"
Prints the new version integer to stdout (for the workflow to capture).
"""

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

_ADDON_XML = (
    Path(__file__).resolve().parent.parent
    / "repo"
    / "plugin_video_mubi"
    / "addon.xml"
)


def _read_declaration(path: Path) -> str:
    """Return the original `<?xml ...?>` declaration line verbatim.

    ElementTree drops the declaration on serialisation (and would rewrite it
    without `standalone="yes"`), so we preserve the first line as-is.
    """
    with path.open("r", encoding="utf-8") as handle:
        first_line = handle.readline().strip()
    if not first_line.startswith("<?xml"):
        raise ValueError(
            "Expected an XML declaration on line 1 of {}".format(path)
        )
    return first_line


def bump(notes, path=_ADDON_XML):
    """Increment the addon version and set the news text.

    Returns the new version integer. Raises ValueError if the current version
    attribute is missing or not an integer, or if there is no `<news>` element.
    """
    path = Path(path)
    declaration = _read_declaration(path)

    tree = ET.parse(str(path))
    root = tree.getroot()

    current = root.get("version")
    if current is None or not current.isdigit():
        raise ValueError(
            "addon version must be a non-negative integer, got {!r}".format(
                current
            )
        )
    new_version = int(current) + 1

    news = root.find("./extension/metadata/news")
    if news is None:
        news = root.find(".//news")
    if news is None:
        raise ValueError("No <news> element found in {}".format(path))

    root.set("version", str(new_version))
    # Assigning to .text; ElementTree escapes &, <, > on serialisation and
    # leaves quotes/apostrophes as valid text content.
    news.text = "v{} - {}".format(new_version, notes)

    body = ET.tostring(root, encoding="unicode")
    # ElementTree renders empty elements as `<import ... />`; the hand-authored
    # file uses `<import .../>` with no space. Normalise so each release diff is
    # only the two intended lines. Safe here: `>` is escaped to `&gt;` in text,
    # and no attribute value contains the literal sequence " />".
    body = body.replace(" />", "/>")
    path.write_text(declaration + "\n" + body + "\n", encoding="utf-8")

    return new_version


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--notes",
        required=True,
        help="Release notes to place in the <news> element.",
    )
    parser.add_argument(
        "--path",
        default=str(_ADDON_XML),
        help="Path to addon.xml (defaults to the plugin's addon.xml).",
    )
    args = parser.parse_args(argv)

    new_version = bump(args.notes, args.path)
    # stdout carries only the version so the workflow can capture it cleanly.
    print(new_version)
    return 0


if __name__ == "__main__":
    sys.exit(main())
