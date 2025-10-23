# Repository Guidelines

## Project Structure & Module Organization
- `main.py` and `run.py`: entry points for running the app and workflows.
- `gui/` and `mainUI.ui`: UI components and resources.
- `camera/`, `job/`, `model/`, `utils/`, `workflow/`: core Python packages for domain logic.
- `tools/`: helper scripts and maintenance utilities.
- `docs/`: documentation and guides.
- Tests: Python files named `test_*.py` at the repo root (and potentially within modules).

## Build, Test, and Development Commands
- Install deps: `python -m venv .venv && .venv\Scripts\pip install -r requirements.txt` (Windows) or `python3 -m venv .venv && source .venv/bin/pip install -r requirements.txt` (Unix).
- Run app: `python run.py` or `python main.py` depending on your workflow.
- Run tests (preferred): `python run_tests.py`.
- Run tests (pytest, if installed): `python -m pytest -q`.

## Coding Style & Naming Conventions
- Python style: follow PEP 8 with 4‑space indents; keep lines reasonable (< 100 chars).
- Naming: modules/functions `snake_case`, classes `PascalCase`, constants `UPPER_SNAKE_CASE`.
- Imports: absolute where possible; group stdlib/third‑party/local.
- Formatting: use Black or Ruff/Black if available (`python -m black .`). Keep diffs minimal and focused.

## Testing Guidelines
- Framework: tests are `test_*.py` and can run via `run_tests.py` or pytest.
- Scope: add unit tests near changes; focus on `utils/`, `model/`, and workflow logic.
- Fast tests first: avoid heavy I/O or GUI dependence; mock camera/GUI where feasible.
- Target: maintain or improve coverage; add a regression test for each bug fix.

## Commit & Pull Request Guidelines
- Commits: imperative mood, short subject (≤ 72 chars), clear body explaining intent and impact.
- Reference issues: `Fixes #123` or `Refs #123` when applicable.
- PRs: include summary, test plan (commands run), and screenshots/gifs for GUI changes.
- Keep PRs small and focused; update `docs/` when behavior or usage changes.

## Security & Configuration Tips
- Do not commit secrets; keep local credentials out of VCS (use env vars or a local `.env`).
- Configuration: see `camera_config.py` for camera‑related settings; prefer parameterization over hard‑coding.
- Dependencies: update via `requirements.txt`; pin versions when introducing new libs.

