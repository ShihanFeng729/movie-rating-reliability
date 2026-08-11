from __future__ import annotations

from io import BytesIO
from pathlib import Path
import sys
import tempfile
import unittest
from urllib.error import URLError


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from movie_rating_reliability.data_download import (  # noqa: E402
    _default_ssl_context,
    DatasetFile,
    download_datasets,
    download_file,
    selected_sources,
)


class ClosingBytesIO(BytesIO):
    def __enter__(self) -> "ClosingBytesIO":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


class DataDownloadTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temporary_directory.name)
        self.source = DatasetFile(
            dataset="example",
            filename="ratings.csv",
            url="https://example.test/ratings.csv",
            note="Test fixture.",
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    @staticmethod
    def fake_opener(url: str, timeout: int) -> ClosingBytesIO:
        del url, timeout
        return ClosingBytesIO(b"movie_id,rating\n1,4.5\n")

    def test_download_file_writes_content_and_metadata(self) -> None:
        record = download_file(
            self.source,
            self.data_dir,
            opener=self.fake_opener,
        )

        path = self.data_dir / "example" / "ratings.csv"
        self.assertEqual(path.read_bytes(), b"movie_id,rating\n1,4.5\n")
        self.assertEqual(record["status"], "downloaded")
        self.assertEqual(record["size_bytes"], path.stat().st_size)
        self.assertEqual(len(str(record["sha256"])), 64)

    def test_existing_file_is_not_downloaded_again(self) -> None:
        destination = self.data_dir / "example" / "ratings.csv"
        destination.parent.mkdir(parents=True)
        destination.write_bytes(b"keep me")

        def failing_opener(url: str, timeout: int) -> ClosingBytesIO:
            del url, timeout
            raise AssertionError("The downloader should have skipped this file.")

        record = download_file(
            self.source,
            self.data_dir,
            opener=failing_opener,
        )

        self.assertEqual(record["status"], "existing")
        self.assertEqual(destination.read_bytes(), b"keep me")

    def test_temporary_network_error_is_retried(self) -> None:
        calls = 0
        delays: list[float] = []

        def flaky_opener(url: str, timeout: int) -> ClosingBytesIO:
            nonlocal calls
            del url, timeout
            calls += 1
            if calls < 3:
                raise URLError("temporary disconnect")
            return ClosingBytesIO(b"recovered")

        record = download_file(
            self.source,
            self.data_dir,
            opener=flaky_opener,
            sleeper=delays.append,
        )

        self.assertEqual(record["status"], "downloaded")
        self.assertEqual(calls, 3)
        self.assertEqual(delays, [1.0, 2.0])
        self.assertEqual(
            (self.data_dir / "example" / "ratings.csv").read_bytes(),
            b"recovered",
        )

    def test_download_datasets_creates_manifest(self) -> None:
        records = download_datasets(
            self.data_dir,
            include_imdb=False,
            movielens="none",
            opener=self.fake_opener,
        )

        self.assertEqual(records, [])
        self.assertEqual(
            (self.data_dir / "download_manifest.json").read_text(encoding="utf-8"),
            "[]\n",
        )

    def test_source_selection_supports_development_and_research(self) -> None:
        small = selected_sources(include_imdb=True, movielens="small")
        research = selected_sources(include_imdb=False, movielens="research")

        self.assertEqual(len(small), 3)
        self.assertEqual(research[0].filename, "ml-32m.zip")

    def test_download_context_keeps_certificate_verification_enabled(self) -> None:
        context = _default_ssl_context()

        self.assertNotEqual(context.verify_mode, 0)
        self.assertTrue(context.check_hostname)


if __name__ == "__main__":
    unittest.main()
