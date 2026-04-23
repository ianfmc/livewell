# Contributing

## Branching & Workflow
- Primary branch: **main**
- Create short-lived feature branches from `main`:
  - `feature/<name>` for new features
  - `fix/<name>` for bug fixes
  - `exp/<name>` for experiments/spikes
- Open a Pull Request (PR) to merge back into `main`.
- Keep PRs small and focused. Include a clear description and checklist.

## Commits
- Use clear, imperative messages:
  - `feat: add EMA/ATR feature builder`
  - `fix: handle empty RSS feed gracefully`
  - `docs: expand backtesting instructions`

## Notebooks & Data
- Place notebooks in `notebooks/` and small sample data in `data/`.
- Large or private datasets belong in a bucket (S3/GCS) or a separate data repo—do **not** commit them.
- Outputs go in `outputs/` (e.g., daily `recommendations/` CSVs). Avoid committing large binaries.

## Configuration
- Keep tunables in `configs/` (e.g., `strategy.yaml`).
- Do not hard-code secrets. Use environment variables or a secret manager.

## Tests & Quality
- Add or update tests for new logic under `tests/`.
- Ensure lint checks and basic tests pass before opening a PR.

## Releases
- Tag with SemVer when we reach meaningful milestones (e.g., `v0.1.0` for MVP).
- Add short release notes summarizing changes and migration steps if any.

## Security & Compliance
- Never commit credentials, tokens, or private API keys.
- Report security concerns privately to the maintainer.

## Code of Conduct
- Be respectful. Assume positive intent. Review in good faith.