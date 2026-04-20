"""Configuration sources."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping, Protocol

from .exceptions import MLPConfigSourceError


class ConfigSource(Protocol):
    def load(self) -> Mapping[str, str]:
        ...


class EnvSource:
    """Read values from an environment mapping."""

    def __init__(self, environ: Mapping[str, str] | None = None) -> None:
        self._environ = environ

    def load(self) -> Mapping[str, str]:
        return dict(os.environ if self._environ is None else self._environ)


class MappingSource:
    """Read values from an explicit mapping."""

    def __init__(self, values: Mapping[str, str]) -> None:
        self._values = dict(values)

    def load(self) -> Mapping[str, str]:
        return dict(self._values)


class DotEnvSource:
    """Read values from a .env file using python-dotenv when installed."""

    def __init__(self, path: str | Path, *, required: bool = False) -> None:
        self._path = Path(path)
        self._required = required

    def load(self) -> Mapping[str, str]:
        if not self._path.exists():
            if self._required:
                raise MLPConfigSourceError(f".env file not found: {self._path}")
            return {}

        try:
            from dotenv import dotenv_values
        except ImportError as exc:
            raise MLPConfigSourceError(
                'DotEnvSource requires python-dotenv. Install it with: '
                'pip install "mlp-config[dotenv]"'
            ) from exc

        loaded = dotenv_values(self._path)
        return {key: value for key, value in loaded.items() if value is not None}
