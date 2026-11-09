# patchguard-ai

A small Python CLI for running repository-configured validation commands and checking required files. It is intended to help make patch verification repeatable; it does not determine whether code is correct or safe.

## Requirements

- Python 3.10 or newer
- Git, if you want to check changed files

## Install

From the repository root:

```bash
python -m pip install .
```

For development:

```bash
python -m pip install -e .
python -m pip install pytest
```

## Configure

Create `.patchguard.yml` in the repository root:

```yaml
commands:
  - python -m pytest -q
  - python -m compileall -q src

required_files:
  - README.md
  - pyproject.toml
```

Commands in this file are executed by a shell with the repository as its working directory. Only use configuration you trust.

`allowed_paths` can list glob patterns for changed-file checks:

```yaml
allowed_paths:
  - "src/**"
  - "tests/**"
```

## Run

Check the current directory:

```bash
patchguard-ai
```

Check another repository:

```bash
patchguard-ai --path /path/to/project
```

Use a specific config file:

```bash
patchguard-ai --path . --config path/to/.patchguard.yml
```

Print JSON instead of text:

```bash
patchguard-ai --format json
```

The command exits with status `1` when a configured check fails, and `0` when all configured checks pass.

## Current limitations

- Changed-file detection currently uses `git diff --name-only HEAD`. It does not include untracked files and does not compare changes against a pull request's base branch.
- Required-file checks test for existence only; they do not inspect file contents.
- A passing report is not proof that a patch is correct, complete, or secure.
- Configured commands are executed through a shell. Do not run untrusted configuration.

## Development

Run the test suite:

```bash
python -m pytest -q
```

## License

MIT
