# V1 real-data results

## Snapshot outcome

The fixed sampling contract began with 1,000 candidates. TMDB returned details
for 999 stable IDs; one linked ID returned HTTP 404. After requiring at least
50 TMDB votes, 941 movies remained complete across TMDB, IMDb, and MovieLens.
This exceeds the predeclared target of 750 and minimum of 500 movies.

The source reference times differ: MovieLens 32M was generated in October 2023,
while IMDb and TMDB values were collected later. Results therefore describe
cross-source agreement under that known temporal limitation, not a perfectly
simultaneous snapshot.

## Pairwise reliability

All ratings use a 1–10 scale. Each pair contains all 941 complete movies.

| Pair | Mean difference (left − right) | MAE | Pearson r | Spearman rho |
|---|---:|---:|---:|---:|
| TMDB − IMDb | -0.0258 | 0.2916 | 0.9085 | 0.8978 |
| TMDB − MovieLens | 0.0249 | 0.3723 | 0.8487 | 0.8393 |
| IMDb − MovieLens | 0.0507 | 0.2586 | 0.9347 | 0.9353 |

IMDb and MovieLens show the closest agreement in this sample. TMDB and
MovieLens have the largest average absolute difference. High correlation does
not by itself establish agreement, so the bias and MAE values remain central.

## Ridge temporal holdout

IMDb rating is the prediction target. The 752 older movies form the training
set and the newest 189 movies, released from 2015 through 2022, form the fixed
holdout. Numeric standardization and genre encoding are learned from training
rows only.

The report compares Ridge with the mean IMDb rating of the training data.
Ridge achieved MAE 0.2035, RMSE 0.2851, and R² 0.9047. The training-mean
baseline achieved MAE 0.7382, RMSE 0.9289, and R² -0.0118. The fixed Ridge
alpha validates the planned baseline; any later parameter tuning must occur
only within the training portion.

## Reproduction boundary

Raw source files, API responses, processed rows, and generated JSON reports are
excluded from Git. The repository contains the sampling contract, download and
collection workflows, transformation logic, analysis code, and automated tests
needed to rebuild the results with appropriately licensed source access.
