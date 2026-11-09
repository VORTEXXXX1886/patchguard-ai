from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class PatchguardConfig:
    commands: list[str]
    allowed_paths: list[str]
    required_files: list[str]

    @classmethod
    def load(cls, path: Path) -> "PatchguardConfig":
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return cls(
            commands=[str(item) for item in data.get("commands", [])],
            allowed_paths=[str(item) for item in data.get("allowed_paths", [])],
            required_files=[str(item) for item in data.get("required_files", [])],
        )


def load_config(path: Path) -> PatchguardConfig:
    return PatchguardConfig.load(path)


def default_config_path(root: Path) -> Path:
    return root / ".patchguard.yml"
