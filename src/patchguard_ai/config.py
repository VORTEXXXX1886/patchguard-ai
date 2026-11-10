from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path

import yaml


class ConfigError(ValueError):
    """Raised when the Patchguard YAML configuration is invalid."""


@dataclass
class PatchguardConfig:
    commands: list[str]
    allowed_paths: list[str]
    required_files: list[str]
    command_timeout: float = 300.0

    @classmethod
    def load(cls, path: Path) -> "PatchguardConfig":
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, yaml.YAMLError) as exc:
            raise ConfigError(f"cannot read config file {path}: {exc}") from exc

        if data is None:
            data = {}
        if not isinstance(data, dict):
            raise ConfigError("config must be a YAML mapping at the top level")

        list_values: dict[str, list[str]] = {}
        for key in ("commands", "allowed_paths", "required_files"):
            value = data.get(key, [])
            if not isinstance(value, list):
                raise ConfigError(f"'{key}' must be a YAML list of strings")
            if any(not isinstance(item, str) or not item.strip() for item in value):
                raise ConfigError(f"every item in '{key}' must be a non-empty string")
            list_values[key] = value

        timeout = data.get("command_timeout", 300)
        if (
            isinstance(timeout, bool)
            or not isinstance(timeout, (int, float))
            or not math.isfinite(timeout)
            or timeout <= 0
        ):
            raise ConfigError("'command_timeout' must be a positive number of seconds")

        return cls(
            commands=list_values["commands"],
            allowed_paths=list_values["allowed_paths"],
            required_files=list_values["required_files"],
            command_timeout=float(timeout),
        )


def load_config(path: Path) -> PatchguardConfig:
    return PatchguardConfig.load(path)


def default_config_path(root: Path) -> Path:
    return root / ".patchguard.yml"
