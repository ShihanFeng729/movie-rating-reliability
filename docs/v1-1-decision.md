# V1.1 predefined sentiment decision

## Decision

**Stop increasing model complexity in the current V1.1 sentiment branch.**

This is a planned negative result, not a pipeline failure. The frozen sentiment
extension was evaluated on exactly the same 149 outer-test movies as the base
Ridge, and the two success criteria were fixed before the comparison was run.

## Criteria and observed evidence

| Criterion | Required | Observed | Result |
|---|---:|---:|---|
| Overall MAE improvement | At least 0.0100 | 0.0011 | Did not pass |
| Time groups with lower MAE | At least 3 of 4 | 2 of 4 | Did not pass |

Both criteria had to pass. Neither passed, so V1.1 does not support adding more
complex sentiment models under the current sample and evaluation design. The
coverage-matched base Ridge remains the preferred model for this experiment.

## What this conclusion means

- The simple sentiment feature produces a small overall numerical improvement,
  but it is below the predefined minimum and is not consistent across periods.
- The result does not show that review text can never help rating prediction.
- Training sentiment coverage is only 325/752 movies, while strict test coverage
  is 149/189, so uneven feature availability remains an important limitation.
- A future text study would need a separately specified version, improved and
  more even training coverage, and new thresholds fixed before seeing results.
- The current V1.1 branch will preserve this negative result instead of trying
  additional models until one happens to improve the same holdout.

## Reproduce the decision

After rebuilding the local V1.1 inputs, run:

```bash
python3 scripts/decide_v1_1_sentiment.py
```

The script reconstructs both fixed models, verifies the same-sample comparison,
and writes the ignored machine-readable decision to
`reports/generated/v1_1_sentiment_decision.json`. It does not modify the model,
sample, time groups, or thresholds.

The generated decision SHA-256 is
`9b31666251bc5fdecfebc83c1013dfc88e38cc430ebc28e15f4f9d0c80680129`.

V1.1 is formally closed in [`v1-1-closure.md`](v1-1-closure.md). The optional
weaker-timing sensitivity analysis is deliberately not run because it cannot
change this primary decision.
