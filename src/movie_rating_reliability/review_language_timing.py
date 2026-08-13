"""Conservative language and timing audit for locally held TMDB reviews."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any


WORD = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ']+")
ENGLISH_MARKERS = {
    "a", "about", "after", "all", "also", "an", "and", "are", "as", "at",
    "be", "because", "but", "by", "can", "did", "do", "does", "film", "for",
    "from", "had", "has", "have", "he", "her", "his", "i", "if", "in", "is",
    "it", "its", "movie", "my", "not", "of", "on", "one", "or", "she", "so",
    "that", "the", "their", "there", "they", "this", "to", "was", "we", "were",
    "what", "when", "which", "who", "will", "with", "would", "you", "your",
}
NON_ENGLISH_MARKERS = {
    "de", "del", "des", "die", "der", "das", "el", "ella", "en", "es", "et",
    "est", "esta", "este", "für", "gli", "il", "ist", "la", "las", "le", "les",
    "los", "mais", "mit", "não", "não", "non", "para", "pas", "por", "que",
    "qui", "se", "si", "son", "sono", "sur", "una", "une", "uno", "und", "un",
}


def classify_language(text: str) -> dict[str, Any]:
    """Return a conservative English/non-English/undetermined classification."""

    tokens = [token.lower() for token in WORD.findall(text)]
    if len(tokens) < 8:
        return {"label": "undetermined", "word_count": len(tokens), "evidence": 0.0}
    counts = Counter(tokens)
    english = sum(counts[word] for word in ENGLISH_MARKERS)
    other = sum(counts[word] for word in NON_ENGLISH_MARKERS)
    non_latin = sum(
        1 for character in text
        if character.isalpha() and not ("A" <= character <= "Z" or "a" <= character <= "z")
    )
    letters = sum(character.isalpha() for character in text)
    non_latin_ratio = non_latin / letters if letters else 0.0
    marker_share = english / len(tokens)
    if non_latin_ratio >= 0.15 or other >= english + 3:
        label = "likely_non_english"
    elif english >= 4 and marker_share >= 0.08 and english >= other + 2:
        label = "likely_english"
    else:
        label = "undetermined"
    return {
        "label": label,
        "word_count": len(tokens),
        "evidence": round(marker_share, 4),
    }


def audit_language_and_timing(
    raw_dir: Path,
    summary_path: Path,
    *,
    imdb_cutoff: datetime,
    movielens_cutoff: datetime,
) -> dict[str, Any]:
    """Audit review language evidence and creation times without publishing text."""

    movie_rows: list[dict[str, Any]] = []
    total_reviews = 0
    reviews_with_created_at = 0
    before_imdb = 0
    before_movielens = 0
    movies_with_pre_imdb_reviews = 0
    movies_with_pre_movielens_reviews = 0
    for path in sorted(raw_dir.glob("*.json"), key=lambda item: int(item.stem)):
        record = json.loads(path.read_text(encoding="utf-8"))
        results = record.get("payload", {}).get("results", [])
        nonempty = [
            item for item in results
            if isinstance(item, dict) and str(item.get("content", "")).strip()
        ]
        if not nonempty:
            continue
        combined = "\n".join(str(item["content"]) for item in nonempty)
        language = classify_language(combined)
        created_times = []
        for item in nonempty:
            total_reviews += 1
            created = _parse_timestamp(str(item.get("created_at", "")))
            if created is None:
                continue
            reviews_with_created_at += 1
            created_times.append(created)
            before_imdb += created <= imdb_cutoff
            before_movielens += created <= movielens_cutoff
        pre_imdb_count = sum(value <= imdb_cutoff for value in created_times)
        pre_movielens_count = sum(value <= movielens_cutoff for value in created_times)
        movies_with_pre_imdb_reviews += pre_imdb_count > 0
        movies_with_pre_movielens_reviews += pre_movielens_count > 0
        movie_rows.append({
            "tmdb_id": int(path.stem),
            "review_count": len(nonempty),
            "language_label": language["label"],
            "language_word_count": language["word_count"],
            "language_evidence": language["evidence"],
            "reviews_with_created_at": len(created_times),
            "reviews_on_or_before_imdb_cutoff": pre_imdb_count,
            "reviews_on_or_before_movielens_cutoff": pre_movielens_count,
            "all_reviews_on_or_before_imdb_cutoff": (
                len(created_times) == len(nonempty)
                and all(value <= imdb_cutoff for value in created_times)
            ),
            "all_reviews_on_or_before_movielens_cutoff": (
                len(created_times) == len(nonempty)
                and all(value <= movielens_cutoff for value in created_times)
            ),
        })
    labels = Counter(row["language_label"] for row in movie_rows)
    covered_movies = len(movie_rows)
    likely_english_rate = (
        labels["likely_english"] / covered_movies if covered_movies else 0.0
    )
    summary = {
        "stage": "tmdb_review_language_timing_audit",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "covered_movie_count": covered_movies,
        "language_method": "conservative_explainable_marker_rules_v1",
        "language_movie_counts": dict(sorted(labels.items())),
        "likely_english_movie_rate": round(likely_english_rate, 4),
        "language_gate_passed": (
            likely_english_rate >= 0.8
            and labels["undetermined"] / covered_movies <= 0.1
        ) if covered_movies else False,
        "total_nonempty_review_count": total_reviews,
        "reviews_with_created_at": reviews_with_created_at,
        "imdb_cutoff_utc": imdb_cutoff.isoformat(),
        "reviews_on_or_before_imdb_cutoff": before_imdb,
        "movies_with_reviews_on_or_before_imdb_cutoff": movies_with_pre_imdb_reviews,
        "movielens_cutoff_utc": movielens_cutoff.isoformat(),
        "reviews_on_or_before_movielens_cutoff": before_movielens,
        "movies_with_reviews_on_or_before_movielens_cutoff": (
            movies_with_pre_movielens_reviews
        ),
        "strict_timing_coverage_rate_over_holdout": round(
            movies_with_pre_movielens_reviews / 189, 4
        ),
        "movie_audits": movie_rows,
        "raw_review_text_published": False,
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def validate_languages_with_langdetect(raw_dir: Path, *, seed: int = 510) -> dict[str, Any]:
    """Independently validate movie-majority language with optional langdetect."""

    try:
        from langdetect import DetectorFactory, detect
    except ImportError as error:
        raise RuntimeError(
            "Install the pinned audit dependency from requirements-dev.txt."
        ) from error
    DetectorFactory.seed = seed
    review_labels: Counter[str] = Counter()
    movie_labels: Counter[str] = Counter()
    for path in sorted(raw_dir.glob("*.json"), key=lambda item: int(item.stem)):
        record = json.loads(path.read_text(encoding="utf-8"))
        labels = []
        for item in record.get("payload", {}).get("results", []):
            text = str(item.get("content", "")).strip()
            if not text:
                continue
            try:
                label = detect(text)
            except Exception:
                label = "undetermined"
            labels.append(label)
            review_labels[label] += 1
        if labels:
            movie_labels[Counter(labels).most_common(1)[0][0]] += 1
    covered = sum(movie_labels.values())
    return {
        "method": "langdetect_1.0.9_movie_majority",
        "seed": seed,
        "covered_movie_count": covered,
        "movie_majority_language_counts": dict(sorted(movie_labels.items())),
        "review_language_counts": dict(sorted(review_labels.items())),
        "english_movie_majority_rate": round(
            movie_labels["en"] / covered, 4
        ) if covered else 0.0,
    }


def _parse_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
