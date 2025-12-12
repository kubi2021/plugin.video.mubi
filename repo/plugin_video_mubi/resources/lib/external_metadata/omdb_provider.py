from __future__ import annotations

from typing import Any, Dict, Optional

import requests
import xbmc

from .base import BaseMetadataProvider, ExternalMetadataResult
from .title_utils import TitleNormalizer, RetryStrategy


class OMDBProvider(BaseMetadataProvider):
    """OMDB-based metadata provider with caching."""

    API_URL = "http://www.omdbapi.com/"

    def __init__(self, api_key: str, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(api_key, config)

        self.title_normalizer = TitleNormalizer()
        self.retry_strategy = RetryStrategy(
            max_retries=self.config.get("max_retries", 10),
            initial_backoff=self.config.get("backoff_factor", 1.0),
            multiplier=self.config.get("backoff_multiplier", 1.5),
        )



    @property
    def provider_name(self) -> str:
        return "OMDB"

    def get_imdb_id(
        self,
        title: str,
        original_title: Optional[str] = None,
        year: Optional[int] = None,
        media_type: str = "movie",
    ) -> ExternalMetadataResult:


        variants = self.title_normalizer.generate_title_variants(title, original_title)
        for variant in variants:
            result = self._request_with_retry(variant, year, media_type)
            if result.success:

                return result

        xbmc.log(
            f"OMDB: Failed to find IMDB ID for '{title}'",
            xbmc.LOGWARNING,
        )

        result = ExternalMetadataResult(
            success=False,
            source_provider=self.provider_name,
            error_message="No match found",
        )



        return result

    def _request_with_retry(
        self,
        title: str,
        year: Optional[int],
        media_type: str,
    ) -> ExternalMetadataResult:
        params: Dict[str, Any] = {
            "apikey": self.api_key,
            "t": title,
            "type": media_type,
        }
        if year:
            params["y"] = str(year)

        return self.retry_strategy.execute(
            func=lambda: self._make_request(params),
            title=title,
        )

    def _make_request(self, params: Dict[str, str]) -> ExternalMetadataResult:
        try:
            response = requests.get(self.API_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get("imdbID"):
                imdb_id = data["imdbID"]
                imdb_url = f"https://www.imdb.com/title/{imdb_id}/"
                xbmc.log(
                    f"OMDB: Found IMDB ID {imdb_id} for '{params.get('t')}'",
                    xbmc.LOGINFO,
                )
                return ExternalMetadataResult(
                    imdb_id=imdb_id,
                    imdb_url=imdb_url,
                    source_provider=self.provider_name,
                    success=True,
                )

            return ExternalMetadataResult(
                success=False,
                source_provider=self.provider_name,
                error_message="No IMDB ID returned",
            )
        except requests.exceptions.HTTPError:
            raise
        except Exception as error:  # pragma: no cover - fallback for unexpected errors
            xbmc.log(f"OMDB: Request error: {error}", xbmc.LOGERROR)
            return ExternalMetadataResult(
                success=False,
                source_provider=self.provider_name,
                error_message=str(error),
            )

    def test_connection(self) -> bool:
        try:
            response = requests.get(
                self.API_URL,
                params={"apikey": self.api_key, "t": "test", "type": "movie"},
                timeout=10,
            )
            return response.status_code == 200
        except Exception:  # pragma: no cover
            xbmc.log("OMDB: Connection test failed", xbmc.LOGERROR)
            return False
