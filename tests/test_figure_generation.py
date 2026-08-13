from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from movie_rating_reliability.figure_generation import write_horizontal_bar_chart  # noqa: E402


class FigureGenerationTests(unittest.TestCase):
    def test_svg_contains_accessible_text_and_escaped_labels(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "chart.svg"
            write_horizontal_bar_chart(
                path,
                title="A & B",
                subtitle="Lower is better",
                rows=[("One < Two", 0.25)],
                maximum=1.0,
                accent="#123456",
            )
            content = path.read_text(encoding="utf-8")
            self.assertIn("<title id=\"title\">A &amp; B</title>", content)
            self.assertIn("One &lt; Two", content)
            self.assertIn("0.2500", content)

    def test_invalid_chart_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                write_horizontal_bar_chart(
                    Path(directory) / "chart.svg",
                    title="Invalid",
                    subtitle="No rows",
                    rows=[],
                    maximum=1.0,
                    accent="#000000",
                )


if __name__ == "__main__":
    unittest.main()
