# V1 acceptance record

## Outcome

**V1 is complete.** All seven predeclared success criteria have implementation,
documentation, automated checks, and reproducible local evidence. This record
closes the real-data evidence version before V1.1 adds sentiment features.

## Acceptance evidence

### 1. The real snapshot can be rebuilt from source records — passed

- `config/real_snapshot_v1.json` fixes the sampling frame, eligibility rules,
  sample sizes, random seed, source versions, and temporal holdout.
- `scripts/download_data.py`, `scripts/build_real_candidates.py`, and
  `scripts/collect_candidate_tmdb.py` rebuild the local source and processed
  artifacts.
- `scripts/build_v1_source_manifest.py` records source URLs, reference times,
  file sizes, checksums, and the TMDB collection boundary.
- `scripts/audit_real_v1.py` freezes the 941-row analysis table and its
  generating entrypoints.
- `python3 scripts/validate_snapshot_contract.py` passes.

### 2. Matching coverage, missingness, ambiguity, and rejection rules are quantified — passed

- The 1,000 candidates resolve to 941 complete movies: one TMDB 404 and 58
  responses below the fixed TMDB vote threshold.
- MovieLens, IMDb, and TMDB identifiers are unique in the final table.
- Required final fields have no missing values and all ratings remain on the
  declared 1–10 scale.
- Stable IDs eliminate fuzzy matching in V1; five year differences are retained
  as diagnostics because independently returned IMDb IDs agree.
- The local rejection table has 59 rows and the manual-review table has zero
  ambiguous rows. Details are in `docs/v1-data-quality.md`.

### 3. Real statistical results include grouped analysis and limitations — passed

- `docs/v1-results.md` reports pairwise bias, MAE, Pearson and Spearman
  association for 941 movies.
- Results are grouped by release decade, primary genre, and MovieLens rating
  count band.
- Popularity and stricter-support sensitivity checks preserve the main pairwise
  ordering.
- Source-time mismatch, group size, multi-genre simplification, and the
  distinction between association, agreement, and prediction are explicit.

### 4. Ridge is fairly compared with naive baselines on unseen movies — passed

- The fixed outer holdout contains the newest 189 movies from 2015–2022.
- Ridge MAE is 0.2043, compared with 0.7382 for the training mean and 0.2296 for
  the stronger TMDB–MovieLens average.
- Coefficient stability, grouped holdout errors, and the largest residuals are
  documented.

### 5. Preprocessing uses training data only — passed

- Numeric scaling and genre categories are learned separately in each training
  partition.
- Ridge alpha is selected inside the older training period; the outer holdout
  is never used for selection.
- Automated tests assert this boundary. See `docs/modeling.md`.

### 6. Automated tests and the credential-free demo remain stable — passed

- The complete suite passes on Python 3.11, 3.12, 3.13, and 3.14 in GitHub
  Actions.
- `python3 run.py` remains independent of API credentials, network access, and
  real licensed data.
- At V1 closure, 65 local tests pass.

### 7. The sentiment module has an evidence-based Go / No-Go decision — passed

- 151 of 189 holdout movies have non-empty TMDB reviews (79.89%).
- Independent language validation finds English as the majority language for
  all 151 covered movies.
- Applying the strict MovieLens 2023-10-13 cutoff leaves 149 covered movies
  (78.84%).
- Stage 5 therefore reaches a controlled Go for V1.1. Primary sentiment
  analysis must use only reviews created on or before the strict cutoff. See
  `docs/sentiment-go-no-go.md`.

## Reproduction check

Run the public checks from the repository root:

```bash
python3 scripts/validate_snapshot_contract.py
python3 run.py
python3 -m pytest
```

With locally held source data and a configured TMDB token, rebuild the full V1
evidence in the order documented under `scripts/README.md`. Raw source files,
API responses, tokens, processed rows, and generated JSON reports remain
excluded from Git.

## Version boundary

V1 answers the cross-platform reliability question and establishes the
interpretable prediction baseline. V1.1 begins only with the predefined small
sentiment baseline. It does not reopen V1 sampling, matching, or outer-holdout
decisions unless a separately versioned data refresh is declared.
