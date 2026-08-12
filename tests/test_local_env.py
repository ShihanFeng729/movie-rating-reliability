from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
from movie_rating_reliability.local_env import load_local_env  # noqa: E402


class LocalEnvTests(unittest.TestCase):
    def test_loads_file_without_overwriting_existing_value(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("NEW_TEST_VALUE='abc'\nEXISTING_TEST_VALUE=new\n")
            os.environ["EXISTING_TEST_VALUE"] = "old"
            os.environ.pop("NEW_TEST_VALUE", None)
            load_local_env(path)
            self.assertEqual(os.environ["NEW_TEST_VALUE"], "abc")
            self.assertEqual(os.environ["EXISTING_TEST_VALUE"], "old")
            os.environ.pop("NEW_TEST_VALUE", None)
            os.environ.pop("EXISTING_TEST_VALUE", None)
