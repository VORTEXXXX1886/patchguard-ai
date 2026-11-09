from __future__ import annotations

import subprocess
from pathlib import Path

from patchguard_ai import checks
from patchguard_ai.config import default_config_path, load_config


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
        "  - README.md\n",
    )

    assert config.commands == ["pytest -q"]
    assert config.allowed_paths == ["src/**"]
    assert config.required_files == ["README.md"]


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
    monkeypatch.setattr(checks, "run_command", lambda _command, _cwd: (False, "tests failed"))

    results = checks.run_checks(tmp_path, config)

    assert results["passed"] is False
    assert results["command_results"] == [
        {"command": "pytest -q", "passed": False, "output": "tests failed"}
    ]
