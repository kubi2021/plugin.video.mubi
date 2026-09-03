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
    - When neither a start nor an end date is present, or a timestamp fails to
      parse, falls back to the legacy ``availability == 'live'`` status check.
    """
    if not details:
        return False

    if now is None:
        now = datetime.now(timezone.utc)

    available_at = details.get('available_at')
    ends_at = details.get('expires_at') or details.get('availability_ends_at')

    if available_at or ends_at:
        try:
            if available_at and now < _parse_aware(available_at):
                return False
            if ends_at and now > _parse_aware(ends_at):
                return False
            return True
        except (ValueError, OverflowError, TypeError) as e:
            xbmc.log(
                f"Error parsing availability dates ({e}); "
                f"falling back to status check",
                xbmc.LOGWARNING,
            )
            # Fall through to the legacy status check below.

    return details.get('availability') == 'live'
