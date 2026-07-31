# Tests

This directory contains automated tests for the Python package.

Tests should use synthetic fixtures whenever possible so they do not require
licensed datasets, live API calls, or a personal API key.

Create a project-specific environment, install the development dependency, and
run the same suite used by GitHub Actions:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pytest
```

On Windows, use `.venv\Scripts\activate` for the activation step.
The test files use Python's built-in `unittest` style. Pytest discovers and
runs them, then provides a concise summary and useful failure output.
