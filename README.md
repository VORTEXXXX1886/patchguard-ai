# patchguard-ai

A Python CLI for validating repository health before a patch is handed off to a coding assistant. It checks configured validation commands, required files, and the scope of changed files, then reports failures in plain text or JSON. When a check fails, it can also generate a copyable prompt for a follow-up coding assistant without sending your code anywhere.

## What it does

- Runs repository-configured validation commands such as tests or compile checks.
- Verifies required files exist.
- Checks changed files against allowed path patterns.
- Supports base-aware comparisons using Git refs.
- Produces a copyable failure handoff prompt for a coding assistant.
- Keeps everything local; it does not upload code or apply fixes automatically.

## Requirements

- Python 3.10 or newer
- Git (for changed-file checks)

## Install

From a fresh clone:

```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
python -m pip install -e . pytest
```

Or install the package directly from the repo root:

```bash
python -m pip install .
```

## Quick start

Create `.patchguard.yml` in the repository root:

```yaml
commands:
  - python -m pytest -q
  - python -m compileall -q src

required_files:
  - README.md
  - pyproject.toml

allowed_paths:
  - "src/**"
  - "tests/**"
```

Run it from the repository you want to validate:

```bash
patchguard-ai
```

The CLI executes configured commands with the repository as its working directory. Only use config you trust; commands run through a shell.

## Options

Check a different repository:

```bash
patchguard-ai --path /path/to/project
```

Use a specific config file:

```bash
patchguard-ai --path . --config path/to/.patchguard.yml
```

Compare against a Git base ref and include committed changes since the merge base:

```bash
patchguard-ai --base origin/main
```

Print machine-readable JSON:

```bash
patchguard-ai --format json
```

Generate a copyable failure prompt:

```bash
patchguard-ai --format prompt
```

The command exits with status `0` when all checks pass, and `1` when any configured check fails.

## Hand off a failure to a coding assistant

When checks fail, generate a copyable prompt:

```bash
patchguard-ai --format prompt
```

Paste the output into a coding assistant such as Copilot Chat, ChatGPT, Claude Code, or Codex. The prompt includes:

- repository path
- comparison base, if used
- changed files
- scope violations
- missing required files
- failing command output

This is a manual handoff. The assistant still needs repository access to inspect and edit files.

## Safety and limitations

- Patchguard is a local validator; it does not upload source code or output to an AI service.
- It does not apply fixes automatically.
- Changed-file detection includes staged, unstaged, and untracked files, and `--base` covers commits since the merge base.
- Required-file checks verify presence only; they do not inspect file contents.
- A passing check does not prove a patch is correct, complete, or secure.
- Configured commands run in a shell. Do not run untrusted configuration.

## Development

Run the test suite:

```bash
python -m pytest -q
```

This project is intentionally small and focused on validation behavior. Most work should be easy to test with the existing pytest suite.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for local setup and contribution workflow.

## License

MIT. See [LICENSE](LICENSE).
