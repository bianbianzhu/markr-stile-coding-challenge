Be concise, sacrifice the grammar for the sake of conciseness.

EVERYTHING IN ENGLISH.

Python tooling: use `uv` for dependency management, virtualenvs, and locking. Do not use `pip`, `poetry`, `pipenv`, `conda`, or `pip-tools`. Dockerfiles must install via `uv sync --frozen` from `pyproject.toml` + `uv.lock`. Local dev: `uv sync`, `uv run pytest`, `uv run ruff check .`, `uv run mypy src/markr`.

Do not use git worktree. Just develop in the main branch.

## Simplicity & Surgical Changes

- **Minimum code that solves the problem.** No speculative features. No premature abstractions. No error handling for impossible scenarios. Three similar lines beats premature abstraction. If 200 lines could be 50, rewrite.
- **Touch only what the task requires.** Don't refactor adjacent code. Don't reformat untouched files. Don't fix unrelated issues silently — mention them, leave them. Match existing style even if you'd write it differently.
- Every changed line must trace directly to the user's request.

## Code Standards

- Follow coding principles, like KISS, SOLID, DRY, etc.
