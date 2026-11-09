from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from patchguard_ai.checks import run_checks
from patchguard_ai.config import default_config_path, load_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="patchguard-ai",
        description="Check changed-file scope and configured repository checks.",
    )
    parser.add_argument("--path", default=".", type=Path, help="Repository path to inspect")
    parser.add_argument("--config", type=Path, help="Path to a .patchguard.yml file")
    parser.add_argument(
        "--base",
        help="Git ref to compare against (for example, origin/main); includes commits since the merge base",
    )
    parser.add_argument("--format", choices=("text", "json"), default="text", help="Output format")
    return parser


def _text_report(results: dict) -> str:
    lines = [f"patchguard-ai: {results['path']}"]
    if results["base"]:
        lines.append(f"Comparison base: {results['base']}")
    lines.append(f"Status: {'PASS' if results['passed'] else 'FAIL'}")

    if results["git_error"]:
        lines.append(f"Git error: {results['git_error']}")

    lines.append(f"Changed files: {len(results['changed_files'])}")
    if results["scope_violations"]:
        lines.append("Scope violations:")
        lines.extend(f"  - {item}" for item in results["scope_violations"])
    if results["missing_files"]:
        lines.append("Missing required files:")
        lines.extend(f"  - {item}" for item in results["missing_files"])

    for item in results["command_results"]:
        status = "PASS" if item["passed"] else "FAIL"
        lines.append(f"[{status}] {item['command']}")
        if item["output"]:
            lines.append("  " + item["output"].replace("\n", "\n  "))

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    repo_root = args.path.expanduser().resolve()
    config_path = args.config.expanduser().resolve() if args.config else default_config_path(repo_root)

    if not repo_root.exists():
        parser.error(f"path does not exist: {repo_root}")
    if not repo_root.is_dir():
        parser.error(f"path is not a directory: {repo_root}")
    if not config_path.exists():
        parser.error(f"config file not found: {config_path}")

    config = load_config(config_path)
    results = run_checks(repo_root, config, base=args.base)

    if args.format == "json":
        print(json.dumps(results, indent=2))
    else:
        print(_text_report(results))

    return 0 if results["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
