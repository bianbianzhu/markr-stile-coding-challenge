Be concise, sacrifice the grammar for the sake of conciseness.

EVERYTHING IN ENGLISH.

Python tooling: use `uv` for dependency management, virtualenvs, and locking. Do not use `pip`, `poetry`, `pipenv`, `conda`, or `pip-tools`. Dockerfiles must install via `uv sync --frozen` from `pyproject.toml` + `uv.lock`. Local dev: `uv sync`, `uv run pytest`, `uv run ruff check .`, `uv run mypy src/markr`.
