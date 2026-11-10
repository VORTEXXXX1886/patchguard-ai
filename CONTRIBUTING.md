# Contributing to patchguard-ai

Thanks for helping improve the project.

## Development setup

```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
python -m pip install -e . pytest
```

## Run the checks locally

From the repository root:

```bash
python -m pytest -q
```

You can also run the tool directly against the repo:

```bash
patchguard-ai
patchguard-ai --format prompt
```

## Repo layout

- `src/patchguard_ai/` — CLI entry point, config loading, and validation logic
- `tests/` — pytest coverage for config parsing and validation behavior
- `.patchguard.yml` — the project’s own validation configuration
- `.github/` — CI and GitHub issue/PR templates

## Suggested workflow

1. Create a feature branch for your change.
2. Keep the patch small and focused.
3. Update or add tests for user-visible behavior.
4. Run the project test suite before opening a PR.
5. Open a pull request using the template in `.github/pull_request_template.md`.

## Before opening a PR

- Make sure the test suite passes.
- Ensure your changes are documented if behavior or configuration changed.
- Avoid unrelated formatting churn.
- Review the diff to confirm the patch stays within scope.

## Reporting issues

Use the issue templates under `.github/ISSUE_TEMPLATE/` and include enough detail for reproduction.
