from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class CollectCandidateScriptTests(unittest.TestCase):
    def test_placeholder_token_stops_before_network_request(self) -> None:
        environment = os.environ.copy()
        environment["TMDB_BEARER_TOKEN"] = (
            "replace_with_your_tmdb_api_read_access_token"
        )
        result = subprocess.run(
            [sys.executable, "scripts/collect_candidate_tmdb.py", "--limit", "1"],
            cwd=PROJECT_ROOT,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not configured", result.stderr)
        self.assertNotIn("URLError", result.stderr)
