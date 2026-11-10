# Patchguard AI

Patchguard is a Python CLI that checks a repository’s configured validation commands, required files, and changed-file scope. When checks fail, it can also produce a copyable diagnostic prompt for a coding assistant—so you can hand off the failure context without manually collecting it.

**It is a local validation and handoff tool, not an AI agent.** It does not upload your code, contact an AI service, or apply fixes.

## What it does

- Runs validation commands you configure, such as tests or compile checks.
- Checks that required files exist.
- Checks changed files against allowed path patterns.
- Reports results in human-readable output or JSON.
- Formats failures into a prompt you can copy into a coding assistant.

## Requirements

- Python 3.10 or newer
- Git for changed-file checks

## Install

From the repository root:

```bash
python -m pip install .
```

For development, create a virtual environment and install the project with pytest:

```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
python -m pip install -e . pytest
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

Run the checks from your repository:

```bash
patchguard-ai
```

Patchguard runs configured commands with the repository as the working directory. **Only run configurations you trust**: commands are executed through a shell.

## Options

Check another repository or choose a config file:

```bash
patchguard-ai --path /path/to/project
patchguard-ai --path . --config path/to/.patchguard.yml
```

Include committed changes since the merge base with a Git ref, or print machine-readable JSON:

```bash
patchguard-ai --base origin/main
patchguard-ai --format json
```

The command exits with status `0` when all checks pass and `1` when a check fails.

## Hand off a failure to a coding assistant

When checks fail, request a copyable prompt with the failure details and detected changed files:

```bash
patchguard-ai --format prompt
```

Copy the output into a coding assistant such as ChatGPT, Copilot Chat, Claude Code, or Codex. The prompt gives the assistant diagnostic context; the assistant still needs access to the repository files to inspect or change them. Review any suggestions and run your checks again.

If checks pass, Patchguard reports that there is no failure prompt to hand off.

## Safety and limitations

- Prompt generation is a manual handoff; Patchguard does not send source code or output to an AI service.
- Patchguard does not automatically apply suggested fixes.
- Changed-file detection includes staged, unstaged, and untracked files. Use `--base` to include committed changes since the merge base.
- Required-file checks verify existence only; they do not inspect file contents.
- A passing report does not prove a patch is correct, complete, or secure.
- Configured commands run in a shell. Do not run untrusted configuration.

## Development

Run the test suite:

```bash
python -m pytest -q
```

## License

MIT. See [LICENSE](LICENSE).
