# Reports

This directory will contain reproducible summaries of project results.

Generated charts belong in `figures/`. Only the two named V1 aggregate SVG
figures are published; other generated figures remain ignored by Git.

Runtime summaries belong in `generated/`. They are reproducible and ignored by
Git, while `.gitkeep` preserves the directory in a fresh clone.

Rebuild the published figures from the local generated V1 summaries with:

```bash
python3 scripts/generate_v1_figures.py
```
