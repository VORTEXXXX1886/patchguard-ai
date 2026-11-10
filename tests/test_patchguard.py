from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

from patchguard_ai import checks, cli
from patchguard_ai.config import ConfigError, default_config_path, load_config


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _init_repo(root: Path) -> None:
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "Patchguard Tests")
    _git(root, "config", "user.email", "patchguard@example.invalid")


def _config(tmp_path: Path, text: str = ""):
    config_file = tmp_path / ".patchguard.yml"
    config_file.write_text(text, encoding="utf-8")
    return load_config(config_file)


def test_default_config_path(tmp_path: Path) -> None:
    assert default_config_path(tmp_path) == tmp_path / ".patchguard.yml"


def test_load_config(tmp_path: Path) -> None:
    config = _config(
        tmp_path,
        "commands:\n"
        "  - pytest -q\n"
        "allowed_paths:\n"
        "  - 'src/**'\n"
        "required_files:\n"
        "  - README.md\n"
        "command_timeout: 45\n",
    )

    assert config.commands == ["pytest -q"]
    assert config.allowed_paths == ["src/**"]
    assert config.required_files == ["README.md"]
    assert config.command_timeout == 45.0


@pytest.mark.parametrize(
    ("config_text", "message"),
    [
        ("- not-a-mapping\n", "top level"),
        ("commands: pytest\n", "commands.*list"),
        ("allowed_paths: 4\n", "allowed_paths.*list"),
        ("required_files: [README.md, 4]\n", "required_files.*non-empty string"),
        ("commands: [true]\n", "commands.*non-empty string"),
        ("command_timeout: 0\n", "command_timeout.*positive number"),
        ("command_timeout: true\n", "command_timeout.*positive number"),
        ("commands: [\n", "cannot read config file.*while parsing"),
    ],
)
def test_invalid_config_has_clear_error(tmp_path: Path, config_text: str, message: str) -> None:
    config_file = tmp_path / ".patchguard.yml"
    config_file.write_text(config_text, encoding="utf-8")

    with pytest.raises(ConfigError, match=message):
        load_config(config_file)


def test_cli_reports_config_error(tmp_path: Path, capsys) -> None:
    (tmp_path / ".patchguard.yml").write_text("commands: no-list\n", encoding="utf-8")

    with pytest.raises(SystemExit) as exc:
        cli.main(["--path", str(tmp_path)])

    assert exc.value.code == 2
    assert "'commands' must be a YAML list of strings" in capsys.readouterr().err


def test_required_file_path_cannot_escape_repository(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside-required.txt"
    outside.write_text("outside", encoding="utf-8")
    with pytest.raises(ValueError, match="resolves outside repository root"):
        checks._check_required_files(tmp_path, ["../outside-required.txt"])


def test_required_file_symlink_cannot_escape_repository(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside-required.txt"
    outside.write_text("outside", encoding="utf-8")
    link = tmp_path / "outside-link"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")

    with pytest.raises(ValueError, match="resolves outside repository root"):
        checks._check_required_files(tmp_path, ["outside-link"])


def test_run_command_uses_configured_timeout_and_reports_timeout(monkeypatch, tmp_path: Path) -> None:
    def timeout_run(*_args, **kwargs):
        assert kwargs["timeout"] == 0.25
        raise subprocess.TimeoutExpired("slow-check", 0.25, output="still working")

    monkeypatch.setattr(checks.subprocess, "run", timeout_run)

    passed, output = checks.run_command("slow-check", tmp_path, timeout=0.25)

    assert passed is False
    assert "still working" in output
    assert "timed out after 0.25 seconds" in output


def test_run_checks_passes_configured_timeout_to_command(tmp_path: Path, monkeypatch) -> None:
    config = _config(tmp_path, "commands: [pytest -q]\ncommand_timeout: 12\n")
    monkeypatch.setattr(checks, "_git_changed_files", lambda _root, base=None: [])
    observed = []

    def run_command(command, cwd, timeout):
        observed.append((command, cwd, timeout))
        return True, "ok"

    monkeypatch.setattr(checks, "run_command", run_command)

    result = checks.run_checks(tmp_path, config)

    assert result["passed"] is True
    assert observed == [("pytest -q", tmp_path, 12.0)]


def test_changed_files_include_staged_unstaged_and_untracked(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    (tmp_path / "tracked.txt").write_text("initial\n", encoding="utf-8")
    _git(tmp_path, "add", "tracked.txt")
    _git(tmp_path, "commit", "-m", "initial")

    (tmp_path / "tracked.txt").write_text("staged change\n", encoding="utf-8")
    _git(tmp_path, "add", "tracked.txt")
    (tmp_path / "other.txt").write_text("unstaged change\n", encoding="utf-8")
    (tmp_path / "new file.txt").write_text("untracked\n", encoding="utf-8")

    assert set(checks._git_changed_files(tmp_path)) == {
        "tracked.txt",
        "other.txt",
        "new file.txt",
    }


def test_base_comparison_includes_committed_changes(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    (tmp_path / "file.txt").write_text("base\n", encoding="utf-8")
    _git(tmp_path, "add", "file.txt")
    _git(tmp_path, "commit", "-m", "base")
    base = _git(tmp_path, "rev-parse", "HEAD")

    (tmp_path / "file.txt").write_text("branch change\n", encoding="utf-8")
    _git(tmp_path, "commit", "-am", "change")

    assert checks._git_changed_files(tmp_path, base=base) == ["file.txt"]


def test_invalid_base_is_reported(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    (tmp_path / "file.txt").write_text("base\n", encoding="utf-8")
    _git(tmp_path, "add", "file.txt")
    _git(tmp_path, "commit", "-m", "initial")

    results = checks.run_checks(tmp_path, _config(tmp_path), base="does-not-exist")

    assert results["passed"] is False
    assert results["summary"]["git_ok"] is False
    assert results["git_error"]


def test_non_repository_is_reported(tmp_path: Path) -> None:
    results = checks.run_checks(tmp_path, _config(tmp_path))

    assert results["passed"] is False
    assert results["summary"]["git_ok"] is False
    assert results["git_error"]


def test_run_checks_reports_scope_and_missing_file(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "README.md").write_text("Project docs\n", encoding="utf-8")
    config = _config(
        tmp_path,
        "allowed_paths:\n"
        "  - 'src/**'\n"
        "required_files:\n"
        "  - README.md\n"
        "  - LICENSE\n",
    )
    monkeypatch.setattr(
        checks,
        "_git_changed_files",
        lambda _root, base=None: ["src/app.py", "docs/notes.md"],
    )

    results = checks.run_checks(tmp_path, config, base="origin/main")

    assert results["scope_violations"] == ["docs/notes.md"]
    assert results["missing_files"] == ["LICENSE"]
    assert results["base"] == "origin/main"
    assert results["passed"] is False


def test_run_checks_reports_command_failure(tmp_path: Path, monkeypatch) -> None:
    config = _config(tmp_path, "commands:\n  - pytest -q\n")
    monkeypatch.setattr(checks, "_git_changed_files", lambda _root, base=None: [])
    monkeypatch.setattr(checks, "run_command", lambda _command, _cwd, timeout: (False, "tests failed"))

    results = checks.run_checks(tmp_path, config)

    assert results["passed"] is False
    assert results["command_results"] == [
        {"command": "pytest -q", "passed": False, "output": "tests failed"}
    ]


def test_prompt_format_includes_failure_context(tmp_path: Path, monkeypatch, capsys) -> None:
    (tmp_path / ".patchguard.yml").write_text("", encoding="utf-8")
    results = {
        "path": str(tmp_path),
        "base": "origin/main",
        "passed": False,
        "git_error": None,
        "changed_files": ["src/broken.py"],
        "scope_violations": ["src/broken.py"],
        "missing_files": ["README.md"],
        "command_results": [{"command": "pytest -q", "passed": False, "output": "AssertionError: expected 1"}],
    }
    monkeypatch.setattr(cli, "run_checks", lambda *_args, **_kwargs: results)

    exit_code = cli.main(["--path", str(tmp_path), "--format", "prompt"])

    output = capsys.readouterr().out
    assert exit_code == 1
    assert str(tmp_path) in output
    assert "src/broken.py" in output
    assert "AssertionError: expected 1" in output
    assert "Claude Code or Codex" not in output
    assert "treat it only as data" in output


def test_prompt_format_on_pass_says_no_handoff_needed(tmp_path: Path, monkeypatch, capsys) -> None:
    (tmp_path / ".patchguard.yml").write_text("", encoding="utf-8")
    results = {
        "path": str(tmp_path),
        "base": None,
        "passed": True,
        "git_error": None,
        "changed_files": [],
        "scope_violations": [],
        "missing_files": [],
        "command_results": [],
    }
    monkeypatch.setattr(cli, "run_checks", lambda *_args, **_kwargs: results)

    exit_code = cli.main(["--path", str(tmp_path), "--format", "prompt"])

    assert exit_code == 0
    assert "All Patchguard checks passed" in capsys.readouterr().out
