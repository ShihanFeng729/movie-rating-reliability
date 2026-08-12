"""Small, auditable TMDB client with caching and retry support."""

from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from hashlib import sha256
import json
from pathlib import Path
import ssl
import time
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from movie_rating_reliability.data_download import _default_ssl_context


API_BASE_URL = "https://api.themoviedb.org/3"
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

OpenUrl = Callable[..., Any]
Sleep = Callable[[float], None]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _retry_after_seconds(value: str | None, now: datetime) -> float | None:
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        try:
            return max(0.0, (parsedate_to_datetime(value) - now).total_seconds())
        except (TypeError, ValueError):
            return None


class TmdbClient:
    """Read public TMDB data using an application Bearer token."""

    def __init__(
        self,
        bearer_token: str,
        cache_dir: Path,
        *,
        cache_hours: float = 24,
        max_retries: int = 3,
        timeout: int = 30,
        opener: OpenUrl | None = None,
        sleeper: Sleep = time.sleep,
    ) -> None:
        if not bearer_token.strip():
            raise ValueError("TMDB bearer token cannot be empty.")
        if cache_hours < 0:
            raise ValueError("cache_hours cannot be negative.")
        if max_retries < 0:
            raise ValueError("max_retries cannot be negative.")

        self.bearer_token = bearer_token
        self.cache_dir = cache_dir
        self.cache_hours = cache_hours
        self.max_retries = max_retries
        self.timeout = timeout
        self.opener = opener or _verified_urlopen
        self.sleeper = sleeper

    def discover_movies(
        self,
        *,
        page: int = 1,
        language: str = "en-US",
        sort_by: str = "popularity.desc",
        minimum_votes: int = 0,
        refresh: bool = False,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Fetch one discover page and return its payload plus request metadata."""

        if not 1 <= page <= 500:
            raise ValueError("TMDB page must be between 1 and 500.")
        if minimum_votes < 0:
            raise ValueError("minimum_votes cannot be negative.")

        return self.get(
            "/discover/movie",
            {
                "include_adult": "false",
                "include_video": "false",
                "language": language,
                "page": page,
                "sort_by": sort_by,
                "vote_count.gte": minimum_votes,
            },
            refresh=refresh,
        )

    def movie_details(
        self,
        tmdb_id: int,
        *,
        language: str = "en-US",
        refresh: bool = False,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Fetch one movie by its stable TMDB identifier."""

        if tmdb_id <= 0:
            raise ValueError("TMDB movie ID must be positive.")
        return self.get(
            f"/movie/{tmdb_id}",
            {"language": language},
            refresh=refresh,
        )

    def get(
        self,
        endpoint: str,
        params: dict[str, object],
        *,
        refresh: bool = False,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """GET JSON from TMDB, using a recent cache entry when available."""

        query = urlencode(sorted((key, str(value)) for key, value in params.items()))
        url = f"{API_BASE_URL}{endpoint}?{query}"
        cache_path = self._cache_path(url)

        cached = self._read_cache(cache_path)
        if cached and not refresh and self._cache_is_fresh(cached):
            return cached["payload"], {
                "source": "cache",
                "url": url,
                "fetched_at_utc": cached["fetched_at_utc"],
                "cache_path": str(cache_path),
            }

        payload, fetched_at = self._request_json(url)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_record = {
            "url": url,
            "fetched_at_utc": fetched_at,
            "payload": payload,
        }
        cache_path.write_text(
            json.dumps(cache_record, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return payload, {
            "source": "api",
            "url": url,
            "fetched_at_utc": fetched_at,
            "cache_path": str(cache_path),
        }

    def _cache_path(self, url: str) -> Path:
        key = sha256(url.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{key}.json"

    def _read_cache(self, path: Path) -> dict[str, Any] | None:
        if not path.exists():
            return None
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
        required = {"fetched_at_utc", "payload", "url"}
        return record if required.issubset(record) else None

    def _cache_is_fresh(self, record: dict[str, Any]) -> bool:
        try:
            fetched_at = datetime.fromisoformat(record["fetched_at_utc"])
        except (TypeError, ValueError):
            return False
        age = utc_now() - fetched_at
        return age.total_seconds() <= self.cache_hours * 3600

    def _request_json(self, url: str) -> tuple[dict[str, Any], str]:
        request = Request(
            url,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self.bearer_token}",
                "User-Agent": "movie-rating-reliability/0.1 (research project)",
            },
        )

        for attempt in range(self.max_retries + 1):
            try:
                with self.opener(request, timeout=self.timeout) as response:
                    payload = json.load(response)
                if not isinstance(payload, dict):
                    raise ValueError("TMDB returned JSON that was not an object.")
                return payload, utc_now().isoformat()
            except HTTPError as error:
                if error.code not in RETRYABLE_STATUS_CODES:
                    raise
                if attempt == self.max_retries:
                    raise
                retry_after = _retry_after_seconds(
                    error.headers.get("Retry-After"),
                    utc_now(),
                )
                delay = retry_after if retry_after is not None else 2**attempt
                self.sleeper(delay)
            except URLError:
                if attempt == self.max_retries:
                    raise
                self.sleeper(2**attempt)

        raise RuntimeError("Unreachable retry state.")


def _verified_urlopen(request: Request, *, timeout: int) -> Any:
    """Open verified HTTPS with the macOS system CA bundle when necessary."""

    return urlopen(request, timeout=timeout, context=_default_ssl_context())
