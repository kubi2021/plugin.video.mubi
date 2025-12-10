from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import xbmc
import xbmcaddon
import xbmcvfs

from .base import ExternalMetadataResult


class MetadataCache:
    """Filesystem-based cache for external metadata lookups."""

    CACHE_VERSION = "1.0"
    DEFAULT_TTL_DAYS = 30

    def __init__(
        self,
        cache_file: Optional[Path] = None,
        ttl_days: int = DEFAULT_TTL_DAYS,
    ) -> None:
        self.ttl_days = ttl_days

        if cache_file:
            self.cache_file = cache_file
        else:
            addon = xbmcaddon.Addon()
            profile_path = Path(xbmcvfs.translatePath(addon.getAddonInfo("profile")))
            profile_path.mkdir(parents=True, exist_ok=True)
            self.cache_file = profile_path / "external_metadata_cache.json"

        self._cache_data = self._load_cache()

    def _load_cache(self) -> dict:
        if not self.cache_file.exists():
            return {"cache_version": self.CACHE_VERSION, "entries": {}}

        try:
            with open(self.cache_file, "r", encoding="utf-8") as handle:
                data = json.load(handle)

            if data.get("cache_version") != self.CACHE_VERSION:
                xbmc.log("Cache version mismatch, resetting cache", xbmc.LOGWARNING)
                return {"cache_version": self.CACHE_VERSION, "entries": {}}

            return data
        except Exception as error:
            xbmc.log(f"Failed to load external metadata cache: {error}", xbmc.LOGWARNING)
            return {"cache_version": self.CACHE_VERSION, "entries": {}}

    def _save_cache(self) -> None:
        try:
            with open(self.cache_file, "w", encoding="utf-8") as handle:
                json.dump(self._cache_data, handle, indent=2, ensure_ascii=False)
        except Exception as error:
            xbmc.log(f"Failed to save external metadata cache: {error}", xbmc.LOGERROR)

    def _make_cache_key(self, title: str, year: Optional[int], media_type: str) -> str:
        normalized = title.lower().strip()
        normalized = "".join(c if c.isalnum() or c.isspace() else "" for c in normalized)
        normalized = "_".join(normalized.split())
        year_str = str(year) if year else "unknown"
        return f"{normalized}_{year_str}_{media_type}"

    def get(self, title: str, year: Optional[int], media_type: str) -> Optional[ExternalMetadataResult]:
        cache_key = self._make_cache_key(title, year, media_type)
        entry = self._cache_data.get("entries", {}).get(cache_key)

        if not entry:
            return None

        try:
            expires_at = datetime.fromisoformat(entry["expires_at"].replace("Z", ""))
            if datetime.utcnow() > expires_at:
                xbmc.log(f"Cache entry expired for '{title}'", xbmc.LOGDEBUG)
                self._cache_data["entries"].pop(cache_key, None)
                self._save_cache()
                return None
        except Exception as error:
            xbmc.log(f"Failed to evaluate cache expiry: {error}", xbmc.LOGWARNING)
            return None

        xbmc.log(f"External metadata cache hit for '{title}'", xbmc.LOGDEBUG)
        return ExternalMetadataResult(
            imdb_id=entry.get("imdb_id"),
            imdb_url=entry.get("imdb_url"),
            tvdb_id=entry.get("tvdb_id"),
            source_provider=entry.get("source_provider", "cache"),
            success=entry.get("success", False),
            error_message=entry.get("error_message"),
        )

    def set(
        self,
        title: str,
        year: Optional[int],
        media_type: str,
        result: ExternalMetadataResult,
    ) -> None:
        cache_key = self._make_cache_key(title, year, media_type)
        now = datetime.utcnow()
        expires_at = now + timedelta(days=self.ttl_days)

        self._cache_data.setdefault("entries", {})[cache_key] = {
            "imdb_id": result.imdb_id,
            "imdb_url": result.imdb_url,
            "tvdb_id": result.tvdb_id,
            "source_provider": result.source_provider,
            "success": result.success,
            "error_message": result.error_message,
            "cached_at": now.isoformat() + "Z",
            "expires_at": expires_at.isoformat() + "Z",
        }

        self._save_cache()
        xbmc.log(f"Cached external metadata for '{title}'", xbmc.LOGDEBUG)

    def clear(self) -> None:
        self._cache_data["entries"] = {}
        self._save_cache()
        xbmc.log("External metadata cache cleared", xbmc.LOGINFO)

    def stats(self) -> dict:
        now = datetime.utcnow()
        total = len(self._cache_data.get("entries", {}))
        expired = sum(
            1
            for entry in self._cache_data.get("entries", {}).values()
            if entry.get("expires_at")
            and now > datetime.fromisoformat(entry["expires_at"].replace("Z", ""))
        )
        return {
            "cache_file": str(self.cache_file),
            "ttl_days": self.ttl_days,
            "total_entries": total,
            "expired_entries": expired,
        }
