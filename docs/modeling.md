# Interpretable rating model

## Purpose

The first model predicts an IMDb rating on the 1–10 scale. It is a transparent
baseline for testing the modeling workflow before real matched data are ready.
It is not intended to identify a single true movie rating.

## Inputs and target

Only rows with every required value are used. The target is `imdb_rating_10`.
The inputs are:

- TMDB rating on the 1–10 scale;
- MovieLens rating converted to the 1–10 scale;
- base-10 logarithms of TMDB and MovieLens rating counts;
- release year centered on 2000 and measured in decades; and
- one-hot genre indicators, with the alphabetically first genre as the
  reference category.

IMDb vote count is deliberately excluded. The first model keeps information
from the target platform out of its inputs and makes its prediction question
easy to explain.

## Model and validation

The model is ridge linear regression with a fixed regularization strength of
`alpha = 1.0`. The intercept is not penalized. The coefficient table shows the
direction and size of each relationship while ridge regularization reduces the
instability that can occur with a small, correlated feature set.

Leave-one-out cross-validation creates one fold per complete movie. Each fold
fits the model on all other movies and predicts the held-out movie. A naive
baseline predicts the mean IMDb rating from the same training fold. The report
compares both methods using:

- mean absolute error (MAE);
- root mean squared error (RMSE); and
- R-squared.

Predictions are clipped to the declared 1–10 scale. Coefficients shown in the
report are then fitted once on all complete rows; they are descriptive and are
not the coefficients from any single validation fold.

## Output and limitations

Running `python3 run.py` writes
`reports/generated/prediction_summary.json`. It contains feature definitions,
metrics, coefficients, and one auditable cross-validation prediction per movie.

The included demo data are fictional and generated from a known process. Their
metrics only confirm that the pipeline works. They do not estimate accuracy on
real or future movies. Real-data conclusions require a documented matched
dataset, repeated error analysis, and checks for time, genre, and popularity
effects.

## Real-data V1 evaluation

The real-data workflow uses a temporal holdout: the 752 older movies train the
model and the newest 189 movies form an untouched test set. Inside the training
period, a second temporal split selects Ridge alpha from 0.1, 1.0, and 10.0.
Numeric scaling and genre categories are learned independently within each
training partition, so neither validation nor outer-test rows define the
preprocessing rules.

The final comparison includes two reference points: the training-set mean and
the simple average of TMDB and MovieLens ratings. The generated report also
records coefficient ranges across candidate alpha values, holdout MAE by
primary genre and rating-count band, and the ten largest absolute errors. These
outputs help distinguish overall predictive accuracy from the parts of the
sample where the baseline is less reliable.
