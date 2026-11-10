# patchguard-ai

A small Python CLI for running repository-configured validation commands and checking changed-file scope. It can also format failed checks as a copyable prompt for a coding assistant. Patchguard does **not** call an AI service or modify code automatically.

## Requirements

- Python 3.10 or newer
- Git, for changed-file checks

## Install

From the repository root:

```bash
python -m pip install .
```

For development, create and activate a virtual environment, then install the project and pytest:

```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
python -m pip install -e . pytest
```

If PowerShell blocks the activation script, allow it for the current terminal only, then activate:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
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

Commands run in a shell with the repository as the working directory. Only use configuration you trust.

`allowed_paths` can list glob patterns for changed-file checks:

```yaml
allowed_paths:
  - "src/**"
  - "tests/**"
```

## Run checks

Run against the current directory:

```bash
patchguard-ai
```

Or inspect another repository / use a specific config:

```bash
patchguard-ai --path /path/to/project
patchguard-ai --path . --config path/to/.patchguard.yml
```

Use `--base` to include committed changes since the merge base with a Git ref, and `--format json` for machine-readable output:

```bash
patchguard-ai --base origin/main
patchguard-ai --format json
```

The command exits with status `0` when all checks pass and `1` when a check fails.

## Create a coding-assistant handoff prompt

Use `--format prompt` to print a ready-to-copy prompt containing the repository path, detected changed files, and failure details:

```bash
patchguard-ai --format prompt
```

When checks pass, it prints that no failure prompt is needed. When checks fail, copy the printed text and paste it into a coding assistant such as ChatGPT, Copilot Chat, Claude Code, or Codex. Ask the assistant to investigate and suggest or make a fix, then rerun Patchguard yourself:

```bash
patchguard-ai
```

**This is a manual handoff, not a live AI integration.** Patchguard does not send your code or output to an AI, and it does not automatically apply a suggested fix. Review the generated prompt before sharing it; failure output may contain private paths, code, or other sensitive information. Command output included in the prompt is capped at 8,000 characters.

### Safely test prompt generation

You can simulate a failed check with a temporary config. In PowerShell, run this from the repository root:

```powershell
@'
commands:
  - python -m pytest --this-option-does-not-exist
required_files: []
'@ | Set-Content -Encoding utf8 .patchguard-test.yml

python -m patchguard_ai.cli --config .patchguard-test.yml --format prompt
Remove-Item .patchguard-test.yml
```

The deliberately invalid pytest option makes the check fail, so Patchguard prints a sample handoff prompt and exits with status `1`—that is expected for this test. The prompt will mention the temporary config file as changed while it exists. Remove the temporary file afterward, as shown. No project code needs to be changed. If you have no coding assistant, you can paste the generated prompt into ChatGPT or Copilot Chat to test the handoff; Patchguard itself does not connect to either one.

## Current limitations and safety

- Changed-file detection includes staged, unstaged, and untracked files. Use `--base` to also include committed changes since the merge base.
- Required-file checks test for existence only; they do not inspect file contents.
- A passing report is not proof that a patch is correct, complete, or secure.
- Configured commands are executed through a shell. Do not run untrusted configuration.
- Prompt output is diagnostic context for an assistant, not a guarantee of a correct fix.

## Development

Run the test suite:

```bash
python -m pytest -q
```

## License

MIT
