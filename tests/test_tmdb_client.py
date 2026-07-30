from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
import json
from pathlib import Path
import sys
import tempfile
import unittest
from urllib.error import HTTPError, URLError


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from movie_rating_reliability.tmdb_client import TmdbClient  # noqa: E402


class JsonResponse(BytesIO):
    def __enter__(self) -> "JsonResponse":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


class TmdbClientTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.cache_dir = Path(self.temporary_directory.name)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_authorization_header_and_cache_reuse(self) -> None:
        calls = []

        def opener(request: object, timeout: int) -> JsonResponse:
            calls.append((request, timeout))
            return JsonResponse(
                json.dumps({"page": 1, "results": [{"id": 42}]}).encode()
            )

        client = TmdbClient("secret-token", self.cache_dir, opener=opener)
        first, first_metadata = client.discover_movies(page=1)
        second, second_metadata = client.discover_movies(page=1)

        self.assertEqual(first, second)
        self.assertEqual(len(calls), 1)
        self.assertEqual(
            calls[0][0].get_header("Authorization"),
            "Bearer secret-token",
        )
        self.assertEqual(first_metadata["source"], "api")
        self.assertEqual(second_metadata["source"], "cache")
        cache_text = next(self.cache_dir.glob("*.json")).read_text()
        self.assertNotIn("secret-token", cache_text)

    def test_retry_after_is_respected_for_429(self) -> None:
        attempts = 0
        delays = []

        def opener(request: object, timeout: int) -> JsonResponse:
            nonlocal attempts
            del request, timeout
            attempts += 1
            if attempts == 1:
                raise HTTPError(
                    "https://api.test",
                    429,
                    "Too Many Requests",
                    {"Retry-After": "2"},
                    None,
                )
            return JsonResponse(b'{"page": 1, "results": []}')

        client = TmdbClient(
            "token",
            self.cache_dir,
            opener=opener,
            sleeper=delays.append,
        )
        client.discover_movies()

        self.assertEqual(attempts, 2)
        self.assertEqual(delays, [2.0])

    def test_non_retryable_error_is_raised_immediately(self) -> None:
        attempts = 0

        def opener(request: object, timeout: int) -> JsonResponse:
            nonlocal attempts
            del request, timeout
            attempts += 1
            raise HTTPError(
                "https://api.test",
                401,
                "Unauthorized",
                {},
                None,
            )

        client = TmdbClient("token", self.cache_dir, opener=opener)
        with self.assertRaises(HTTPError):
            client.discover_movies()
        self.assertEqual(attempts, 1)

    def test_temporary_network_error_is_retried(self) -> None:
        attempts = 0
        delays = []

        def opener(request: object, timeout: int) -> JsonResponse:
            nonlocal attempts
            del request, timeout
            attempts += 1
            if attempts == 1:
                raise URLError("temporary connection problem")
            return JsonResponse(b'{"page": 1, "results": []}')

        client = TmdbClient(
            "token",
            self.cache_dir,
            opener=opener,
            sleeper=delays.append,
        )
        client.discover_movies()

        self.assertEqual(attempts, 2)
        self.assertEqual(delays, [1])

    def test_page_range_is_validated(self) -> None:
        client = TmdbClient("token", self.cache_dir)
        with self.assertRaises(ValueError):
            client.discover_movies(page=501)
