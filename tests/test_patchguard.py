from pathlib import Path

from patchguard_ai import checks
from patchguard_ai.config import default_config_path, load_config


def test_default_config_path() -> None:
    root = Path("/tmp/demo")
    assert default_config_path(root) == root / ".patchguard.yml"


def test_load_config(tmp_path: Path) -> None:
    config_file = tmp_path / ".patchguard.yml"
    config_file.write_text(
        "commands:\n"
        "  - pytest -q\n"
        "allowed_paths:\n"
        "  - 'src/**'\n"
        "required_files:\n"
        "  - README.md\n",
        encoding="utf-8",
    )

    config = load_config(config_file)

    assert config.commands == ["pytest -q"]
    assert config.allowed_paths == ["src/**"]
    assert config.required_files == ["README.md"]


def test_run_checks_reports_scope_and_missing_file(
    tmp_path: Path,
    monkeypatch,
) -> None:
    (tmp_path / "README.md").write_text("Project docs\n", encoding="utf-8")
    config_file = tmp_path / ".patchguard.yml"
    config_file.write_text(
        "allowed_paths:\n"
        "  - 'src/**'\n"
        "required_files:\n"
        "  - README.md\n"
        "  - LICENSE\n",
        encoding="utf-8",
    )
    config = load_config(config_file)

    monkeypatch.setattr(
        checks,
        "_git_changed_files",
        lambda _root: ["src/app.py", "docs/notes.md"],
    )

    results = checks.run_checks(tmp_path, config)

    assert results["scope_violations"] == ["docs/notes.md"]
    assert results["missing_files"] == ["LICENSE"]
    assert results["passed"] is False


def test_run_checks_reports_command_failure(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config_file = tmp_path / ".patchguard.yml"
    config_file.write_text("commands:\n  - pytest -q\n", encoding="utf-8")
    config = load_config(config_file)

    monkeypatch.setattr(checks, "_git_changed_files", lambda _root: [])
    monkeypatch.setattr(
        checks,
        "run_command",
        lambda _command, _cwd: (False, "tests failed"),
    )

    results = checks.run_checks(tmp_path, config)

    assert results["passed"] is False
    assert results["command_results"] == [
        {
            "command": "pytest -q",
            "passed": False,
            "output": "tests failed",
        }
    ]
