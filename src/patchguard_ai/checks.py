from __future__ import annotations

import fnmatch
import subprocess
from pathlib import Path

from patchguard_ai.config import PatchguardConfig


class GitError(RuntimeError):
    """Raised when the requested git repository cannot be inspected."""


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise GitError("Git executable was not found") from exc

    if result.returncode != 0:
        detail = result.stderr.strip() or f"git {' '.join(args)} failed"
        raise GitError(detail)
    return result


def _git_status_paths(root: Path) -> list[str]:
    # -z prevents Git from quoting filenames containing spaces or other special
    # characters. For renames, porcelain v1 -z emits the new path first and the
    # old path as the following NUL-delimited field.
    output = _git(root, "status", "--porcelain", "-z").stdout
    fields = output.split("\0")
    files: list[str] = []
    index = 0

    while index < len(fields):
        entry = fields[index]
        index += 1
        if not entry:
            continue

        status = entry[:2]
        path = entry[3:]
        if path:
            files.append(path)

        if "R" in status or "C" in status:
            # Skip the old path associated with the rename/copy record.
            index += 1

    return files


def _git_changed_files(root: Path, base: str | None = None) -> list[str]:
    """Return changed files in the worktree and, optionally, since a base ref.

    A base comparison includes committed changes between the merge base and HEAD.
    The current Git status is always included, covering staged, unstaged, and
    untracked files. Git errors (including an unknown base ref) are not hidden.
    """
    _git(root, "rev-parse", "--show-toplevel")

    files: list[str] = []
    if base:
        diff = _git(root, "diff", "--name-only", "-z", f"{base}...HEAD", "--")
        files.extend(path for path in diff.stdout.split("\0") if path)

    files.extend(_git_status_paths(root))
    return list(dict.fromkeys(files))


def _matches_any(patterns: list[str], file_path: str) -> bool:
    return any(
        fnmatch.fnmatch(file_path, pattern)
        or fnmatch.fnmatch(file_path, f"{pattern}/**")
        for pattern in patterns
    )


def _check_allowed_paths(
    changed_files: list[str], allowed_paths: list[str]
) -> tuple[bool, list[str]]:
    if not allowed_paths:
        return True, []

    violations = [
        file_path for file_path in changed_files
        if not _matches_any(allowed_paths, file_path)
    ]
    return not violations, violations


def _check_required_files(root: Path, required_files: list[str]) -> tuple[bool, list[str]]:
    resolved_root = root.resolve()
    missing: list[str] = []
    for relative_path in required_files:
        candidate = (root / relative_path).resolve()
        if not candidate.is_relative_to(resolved_root):
            raise ValueError(
                f"required file path '{relative_path}' resolves outside repository root"
            )
        if not candidate.exists():
            missing.append(relative_path)
    return not missing, missing


def run_command(
    command: str, cwd: Path, timeout: float = 300.0
) -> tuple[bool, str]:
    try:
        completed = subprocess.run(
            command,
            shell=True,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
        combined = "\n".join(part for part in [completed.stdout, completed.stderr] if part)
        return completed.returncode == 0, combined.strip()
    except subprocess.TimeoutExpired as exc:
        parts = [exc.stdout, exc.stderr]
        output = "\n".join(
            part.decode(errors="replace") if isinstance(part, bytes) else part
            for part in parts
            if part
        ).strip()
        message = f"command timed out after {timeout:g} seconds"
        return False, "\n".join(part for part in (output, message) if part)
    except Exception as exc:  # pragma: no cover - defensive path
        return False, str(exc)


def run_checks(root: Path, config: PatchguardConfig, base: str | None = None) -> dict:
    git_error: str | None = None
    try:
        changed_files = _git_changed_files(root, base)
    except GitError as exc:
        changed_files = []
        git_error = str(exc)

    allowed_ok, scope_violations = _check_allowed_paths(changed_files, config.allowed_paths)
    required_ok, missing_files = _check_required_files(root, config.required_files)

    command_results: list[dict[str, str | bool]] = []
    for command in config.commands:
        success, output = run_command(command, root, timeout=config.command_timeout)
        command_results.append({"command": command, "passed": success, "output": output})

    commands_ok = all(item["passed"] for item in command_results)
    git_ok = git_error is None
    passed = git_ok and allowed_ok and required_ok and commands_ok

    return {
        "path": str(root),
        "base": base,
        "passed": passed,
        "git_error": git_error,
        "changed_files": changed_files,
        "scope_violations": scope_violations,
        "missing_files": missing_files,
        "command_results": command_results,
        "summary": {
            "git_ok": git_ok,
            "allowed_paths_ok": allowed_ok,
            "required_files_ok": required_ok,
            "commands_ok": commands_ok,
        },
    }
