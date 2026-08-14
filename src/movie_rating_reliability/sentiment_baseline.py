"""Fixed, interpretable English sentiment baseline for V1.1."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from statistics import mean, median
from typing import Any


TOKEN = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")

# This compact lexicon is frozen before rating-model evaluation. It intentionally
# favors common, unambiguous review words over broad vocabulary coverage.
POSITIVE_WORDS = frozenset({
    "amazing", "beautiful", "best", "brilliant", "charming", "clever",
    "compelling", "delightful", "enjoyable", "excellent", "exciting",
    "fantastic", "favorite", "fun", "funny", "good", "great", "impressive",
    "incredible", "interesting", "loved", "masterpiece", "memorable",
    "moving", "outstanding", "perfect", "powerful", "recommended",
    "refreshing", "satisfying", "smart", "solid", "strong", "stunning",
    "superb", "surprising", "touching", "wonderful", "worthwhile",
})
NEGATIVE_WORDS = frozenset({
    "annoying", "awful", "bad", "boring", "confusing", "cringe",
    "disappointing", "dreadful", "dull", "forgettable", "frustrating",
    "hated", "horrible", "incoherent", "lame", "mess", "messy", "poor",
    "predictable", "ridiculous", "shallow", "slow", "stupid", "terrible",
    "tired", "unconvincing", "uninteresting", "unoriginal", "unwatchable",
    "weak", "worse", "worst", "waste",
})
NEGATORS = frozenset({
    "aren't", "can't", "didn't", "doesn't", "don't", "hardly", "isn't",
    "never", "no", "not", "wasn't", "weren't", "without", "won't",
    "wouldn't",
})
NEGATION_WINDOW = 3
OUTPUT_FIELDS = [
    "movielens_id", "imdb_id", "tmdb_id", "release_year", "review_count",
    "sentiment_score", "positive_hits", "negative_hits", "lexicon_hits",
    "token_count", "lexicon_coverage",
]


def score_text(text: str) -> dict[str, int | float]:
    """Score text from -1 to 1 using fixed words and local negation flips."""

    tokens = [match.group(0).lower() for match in TOKEN.finditer(text)]
    positive = 0
    negative = 0
    for index, token in enumerate(tokens):
        polarity = 1 if token in POSITIVE_WORDS else -1 if token in NEGATIVE_WORDS else 0
        if not polarity:
            continue
        context = tokens[max(0, index - NEGATION_WINDOW):index]
        if sum(word in NEGATORS for word in context) % 2:
            polarity *= -1
        if polarity > 0:
            positive += 1
        else:
            negative += 1
    hits = positive + negative
    return {
        "sentiment_score": round((positive - negative) / hits, 6) if hits else 0.0,
        "positive_hits": positive,
        "negative_hits": negative,
        "lexicon_hits": hits,
        "token_count": len(tokens),
        "lexicon_coverage": round(hits / len(tokens), 6) if tokens else 0.0,
    }


def build_sentiment_features(
    sample_path: Path,
    output_path: Path,
    summary_path: Path,
) -> dict[str, Any]:
    """Create local movie-level sentiment features and a text-free summary."""

    rows: list[dict[str, Any]] = []
    seen_tmdb_ids: set[int] = set()
    for line_number, line in enumerate(
        sample_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        source = json.loads(line)
        tmdb_id = int(source["tmdb_id"])
        if tmdb_id in seen_tmdb_ids:
            raise ValueError(f"Duplicate TMDB ID {tmdb_id} at line {line_number}")
        seen_tmdb_ids.add(tmdb_id)
        scores = score_text(str(source["aggregated_review_text"]))
        rows.append({
            "movielens_id": source["movielens_id"],
            "imdb_id": source["imdb_id"],
            "tmdb_id": tmdb_id,
            "release_year": int(source["release_year"]),
            "review_count": int(source["review_count"]),
            **scores,
        })
    if not rows:
        raise ValueError(f"No sample rows found in {sample_path}")
    rows.sort(key=lambda row: row["tmdb_id"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    output_bytes = output_path.read_bytes()
    scores = [float(row["sentiment_score"]) for row in rows]
    coverages = [float(row["lexicon_coverage"]) for row in rows]
    zero_hit_movies = sum(int(row["lexicon_hits"]) == 0 for row in rows)
    summary = {
        "stage": "v1_1_fixed_sentiment_baseline",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "method": "fixed_english_lexicon_with_three_token_negation_v1",
        "method_fitted_to_ratings": False,
        "positive_lexicon_size": len(POSITIVE_WORDS),
        "negative_lexicon_size": len(NEGATIVE_WORDS),
        "negation_window_tokens": NEGATION_WINDOW,
        "movie_count": len(rows),
        "movie_count_with_lexicon_hits": len(rows) - zero_hit_movies,
        "movie_count_without_lexicon_hits": zero_hit_movies,
        "sentiment_score_min": min(scores),
        "sentiment_score_median": round(median(scores), 6),
        "sentiment_score_mean": round(mean(scores), 6),
        "sentiment_score_max": max(scores),
        "mean_lexicon_coverage": round(mean(coverages), 6),
        "total_positive_hits": sum(int(row["positive_hits"]) for row in rows),
        "total_negative_hits": sum(int(row["negative_hits"]) for row in rows),
        "input_sha256": hashlib.sha256(sample_path.read_bytes()).hexdigest(),
        "output_sha256": hashlib.sha256(output_bytes).hexdigest(),
        "output_schema": OUTPUT_FIELDS,
        "review_text_in_output": False,
        "author_fields_in_output": False,
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return summary
