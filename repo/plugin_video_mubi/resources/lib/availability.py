"""Shared availability-window logic.

Single source of truth for deciding whether a film is currently available in a
given country, from that country's availability ``details`` dict. Used by
``film.py``, ``data_source.py`` and ``navigation_handler.py`` so every
availability path in the plugin agrees on the same inputs (issue #52).

Timestamps are parsed into timezone-aware datetimes and compared as instants,
never as strings: lexical comparison of ISO-8601 strings only happens to work
when every value shares an identical format and offset suffix, and silently
mis-orders otherwise (e.g. ``...T07:53:51+02:00`` vs ``...T06:53:51Z``).
"""

from datetime import datetime, timezone
from typing import Optional

import dateutil.parser
import xbmc


def _parse_aware(timestamp: str) -> datetime:
    """Parse an ISO-8601 timestamp into a timezone-aware datetime.

    Naive timestamps are assumed to be UTC, mirroring ``data_source.py``.
    """
    parsed = dateutil.parser.isoparse(timestamp)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def is_country_available(details: dict, now: Optional[datetime] = None) -> bool:
    """Return ``True`` if the film is currently available in this country.

    :param details: Availability details for one country, e.g.
        ``{'available_at': ..., 'expires_at': ..., 'availability': 'live'}``.
    :param now: Aware UTC datetime to test against; defaults to the current time.
        Callers filtering many films should pass a shared ``now`` so every film
        is judged against the same instant.
    :return: ``True`` when ``now`` falls inside the availability window.

    Window rules:
    - ``available_at`` is the start; the end is ``expires_at`` when present, else
      ``availability_ends_at`` (Mubi emits both field names across endpoints).
    - A film is available on its dates only when it has a start date that is in
      the past and (if an end date is present) has not yet passed. A window with
      an end date but *no* start date is not treated as available on its dates —
      a missing start means "not started yet".
    - An end date already in the past means expired, even if ``availability`` is
      still ``'live'``.
    - When there is no usable start date (absent window, no start field, or a
      timestamp fails to parse) and the film has not expired, falls back to the
      legacy ``availability == 'live'`` status check.
    """
    if not details:
        return False

    if now is None:
        now = datetime.now(timezone.utc)

    available_at = details.get("available_at")
    ends_at = details.get("expires_at") or details.get("availability_ends_at")

    if available_at or ends_at:
        try:
            if ends_at and now > _parse_aware(ends_at):
                return False  # Expired — overrides the status check below.
            if available_at:
                if now < _parse_aware(available_at):
                    return False  # Start date is in the future: not yet available.
                return True  # Valid start in the past and not expired.
            # End date present (or future) but no start date: a missing start is
            # not enough to be "available" — fall through to the status check.
        except (ValueError, OverflowError, TypeError) as e:
            xbmc.log(
                f"Error parsing availability dates ({e}); falling back to status check",
                xbmc.LOGWARNING,
            )
            # Fall through to the legacy status check below.

    return details.get("availability") == "live"
