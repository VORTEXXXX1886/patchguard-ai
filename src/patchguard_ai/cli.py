from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from patchguard_ai.config import default_config_path, load_config
from patchguard_ai.checks import run_checks


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="patchguard-ai",
        description="Check whether a repo or patch is bounded, validated, and review-ready.",
    )
    parser.add_argument("--path", default=".", type=Path, help="Repository path to inspect")
    parser.add_argument("--config", type=Path, help="Path to a .patchguard.yml file")
    parser.add_argument("--format", choices=("text", "json"), default="text", help="Output format")
    return parser


def _text_report(results: dict) -> str:
    lines = [f"patchguard-ai: {results['path']}"]
    lines.append(f"Status: {'PASS' if results['passed'] else 'FAIL'}")
    lines.append(f"Changed files: {len(results['changed_files'])}")

    if results["scope_violations"]:
        lines.append("Scope violations:")
        for item in results["scope_violations"]:
            lines.append(f"  - {item}")

    if results["missing_files"]:
        lines.append("Missing required files:")
        for item in results["missing_files"]:
            lines.append(f"  - {item}")

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
    results = run_checks(repo_root, config)

    if args.format == "json":
        print(json.dumps(results, indent=2))
    else:
        print(_text_report(results))

    return 0 if results["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
