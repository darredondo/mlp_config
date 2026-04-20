"""Public Config object and typed accessors."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence, TypeVar, cast

from .exceptions import (
    MLPConfigFrozenError,
    MLPConfigMissingError,
    MLPConfigValueError,
)
from .immutable import deep_freeze
from .ledger import AccessLedger
from .redaction import render_error_value
from .sources import ConfigSource, DotEnvSource, EnvSource, MappingSource

T = TypeVar("T")


@dataclass(slots=True)
class _FrozenState:
    frozen: bool = False


class Config:
    """Lightweight bootstrap configuration reader."""

    def __init__(
        self,
        values: Mapping[str, str],
        *,
        prefix: str = "",
        ledger: AccessLedger | None = None,
        frozen_state: _FrozenState | None = None,
        case_sensitive: bool = True,
        copy_values: bool = True,
    ) -> None:
        self._case_sensitive = case_sensitive
        if case_sensitive and not copy_values:
            self._values = cast(dict[str, str], values)
        elif case_sensitive:
            self._values = dict(values)
        else:
            self._values = {key.upper(): value for key, value in values.items()}
        self._prefix = prefix if case_sensitive else prefix.upper()
        self._ledger = ledger if ledger is not None else AccessLedger()
        self._frozen_state = frozen_state if frozen_state is not None else _FrozenState()

    @classmethod
    def from_env(cls, *, prefix: str = "", environ: Mapping[str, str] | None = None) -> Config:
        return cls.from_sources([EnvSource(environ)], prefix=prefix)

    @classmethod
    def from_sources(cls, sources: Sequence[ConfigSource], *, prefix: str = "") -> Config:
        values: dict[str, str] = {}
        for source in sources:
            values.update(source.load())
        return cls(values, prefix=prefix)

    @classmethod
    def from_mapping(cls, values: Mapping[str, str], *, prefix: str = "") -> Config:
        return cls.from_sources([MappingSource(values)], prefix=prefix)

    @classmethod
    def from_dotenv(
        cls,
        path: str | Path,
        *,
        prefix: str = "",
        required: bool = False,
    ) -> Config:
        return cls.from_sources([DotEnvSource(path, required=required)], prefix=prefix)

    def freeze(self) -> None:
        self._frozen_state.frozen = True

    def prefixed(self, prefix: str) -> Config:
        return Config(
            self._values,
            prefix=f"{self._prefix}{prefix if self._case_sensitive else prefix.upper()}",
            ledger=self._ledger,
            frozen_state=self._frozen_state,
            case_sensitive=self._case_sensitive,
            copy_values=False,
        )

    def snapshot(self) -> dict[str, object]:
        return self._ledger.snapshot()

    def has(self, key: str) -> bool:
        resolved_key = self._resolve_key(key)
        self._ensure_allowed(resolved_key)
        found = resolved_key in self._values
        sensitive = self._ledger.resolve_sensitive(resolved_key, None)
        self._ledger.record(
            key=key,
            resolved_key=resolved_key,
            expected_type="presence",
            required=False,
            found=found,
            status="ok" if found else "missing",
            sensitive=sensitive,
            raw_value=self._values.get(resolved_key),
            value_repr=found,
            error=None,
        )
        return found

    def get_raw(
        self,
        key: str,
        default: str | None = None,
        *,
        sensitive: bool | None = None,
    ) -> str | None:
        return self._access(
            key,
            expected_type="raw",
            required=False,
            default=default,
            sensitive=sensitive,
            converter=lambda raw: raw,
        )

    def require_raw(self, key: str, *, sensitive: bool | None = None) -> str:
        return cast(
            str,
            self._access(
                key,
                expected_type="raw",
                required=True,
                default=None,
                sensitive=sensitive,
                converter=lambda raw: raw,
            ),
        )

    def get_str(
        self,
        key: str,
        default: str | None = None,
        *,
        strip: bool = True,
        sensitive: bool | None = None,
    ) -> str | None:
        return self._access(
            key,
            expected_type="str",
            required=False,
            default=default,
            sensitive=sensitive,
            converter=lambda raw: raw.strip() if strip else raw,
        )

    def require_str(self, key: str, *, strip: bool = True, sensitive: bool | None = None) -> str:
        return cast(
            str,
            self._access(
                key,
                expected_type="str",
                required=True,
                default=None,
                sensitive=sensitive,
                converter=lambda raw: raw.strip() if strip else raw,
            ),
        )

    def get_int(
        self,
        key: str,
        default: int | None = None,
        *,
        sensitive: bool | None = None,
    ) -> int | None:
        return self._access(
            key,
            expected_type="int",
            required=False,
            default=default,
            sensitive=sensitive,
            converter=_parse_int,
        )

    def require_int(self, key: str, *, sensitive: bool | None = None) -> int:
        return cast(
            int,
            self._access(
                key,
                expected_type="int",
                required=True,
                default=None,
                sensitive=sensitive,
                converter=_parse_int,
            ),
        )

    def get_float(
        self,
        key: str,
        default: float | None = None,
        *,
        sensitive: bool | None = None,
    ) -> float | None:
        return self._access(
            key,
            expected_type="float",
            required=False,
            default=default,
            sensitive=sensitive,
            converter=_parse_float,
        )

    def require_float(self, key: str, *, sensitive: bool | None = None) -> float:
        return cast(
            float,
            self._access(
                key,
                expected_type="float",
                required=True,
                default=None,
                sensitive=sensitive,
                converter=_parse_float,
            ),
        )

    def get_bool(
        self,
        key: str,
        default: bool | None = None,
        *,
        sensitive: bool | None = None,
    ) -> bool | None:
        return self._access(
            key,
            expected_type="bool",
            required=False,
            default=default,
            sensitive=sensitive,
            converter=_parse_bool,
        )

    def require_bool(self, key: str, *, sensitive: bool | None = None) -> bool:
        return cast(
            bool,
            self._access(
                key,
                expected_type="bool",
                required=True,
                default=None,
                sensitive=sensitive,
                converter=_parse_bool,
            ),
        )

    def get_list(
        self,
        key: str,
        default: tuple[str, ...] | None = None,
        *,
        separator: str = ",",
        strip_items: bool = True,
        allow_empty: bool = False,
        sensitive: bool | None = None,
    ) -> tuple[str, ...] | None:
        def convert(raw: str) -> tuple[str, ...]:
            items = raw.split(separator)
            if strip_items:
                items = [item.strip() for item in items]
            if not allow_empty:
                items = [item for item in items if item != ""]
            return tuple(items)

        return self._access(
            key,
            expected_type="list",
            required=False,
            default=default,
            sensitive=sensitive,
            converter=convert,
        )

    def require_list(
        self,
        key: str,
        *,
        separator: str = ",",
        strip_items: bool = True,
        allow_empty: bool = False,
        sensitive: bool | None = None,
    ) -> tuple[str, ...]:
        def convert(raw: str) -> tuple[str, ...]:
            items = raw.split(separator)
            if strip_items:
                items = [item.strip() for item in items]
            if not allow_empty:
                items = [item for item in items if item != ""]
            return tuple(items)

        return cast(
            tuple[str, ...],
            self._access(
                key,
                expected_type="list",
                required=True,
                default=None,
                sensitive=sensitive,
                converter=convert,
            ),
        )

    def get_json(
        self,
        key: str,
        default: object | None = None,
        *,
        sensitive: bool | None = None,
    ) -> object | None:
        return self._access(
            key,
            expected_type="json",
            required=False,
            default=deep_freeze(default) if default is not None else None,
            sensitive=sensitive,
            converter=_parse_json,
        )

    def require_json(self, key: str, *, sensitive: bool | None = None) -> object:
        return self._access(
            key,
            expected_type="json",
            required=True,
            default=None,
            sensitive=sensitive,
            converter=_parse_json,
        )

    def get_json_list(
        self,
        key: str,
        default: tuple[object, ...] | None = None,
        *,
        sensitive: bool | None = None,
    ) -> tuple[object, ...] | None:
        return self._access(
            key,
            expected_type="json_list",
            required=False,
            default=tuple(deep_freeze(item) for item in default) if default is not None else None,
            sensitive=sensitive,
            converter=_parse_json_list,
        )

    def require_json_list(self, key: str, *, sensitive: bool | None = None) -> tuple[object, ...]:
        return cast(
            tuple[object, ...],
            self._access(
                key,
                expected_type="json_list",
                required=True,
                default=None,
                sensitive=sensitive,
                converter=_parse_json_list,
            ),
        )

    def _access(
        self,
        key: str,
        *,
        expected_type: str,
        required: bool,
        default: T | None,
        sensitive: bool | None,
        converter: Callable[[str], T],
    ) -> T | None:
        resolved_key = self._resolve_key(key)
        self._ensure_allowed(resolved_key)
        raw_value = self._values.get(resolved_key)
        found = raw_value is not None
        final_sensitive = self._ledger.resolve_sensitive(resolved_key, sensitive)

        if not found:
            self._ledger.record(
                key=key,
                resolved_key=resolved_key,
                expected_type=expected_type,
                required=required,
                found=False,
                status="missing",
                sensitive=final_sensitive,
                raw_value=None,
                value_repr=default,
                error="missing required value" if required else None,
            )
            if required:
                raise self._missing_error(key, resolved_key, expected_type, final_sensitive)
            return default

        self._ledger.record(
            key=key,
            resolved_key=resolved_key,
            expected_type=expected_type,
            required=required,
            found=True,
            status="invalid",
            sensitive=final_sensitive,
            raw_value=raw_value,
            value_repr=None,
            error=f"invalid {expected_type}",
        )

        try:
            value = converter(raw_value)
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise self._value_error(
                key,
                resolved_key,
                expected_type,
                raw_value,
                final_sensitive,
                "invalid value" if final_sensitive else str(exc),
            ) from exc

        self._ledger.record(
            key=key,
            resolved_key=resolved_key,
            expected_type=expected_type,
            required=required,
            found=True,
            status="ok",
            sensitive=final_sensitive,
            raw_value=raw_value,
            value_repr=value,
            error=None,
        )
        return value

    def _resolve_key(self, key: str) -> str:
        resolved_key = f"{self._prefix}{key}"
        return resolved_key if self._case_sensitive else resolved_key.upper()

    def _ensure_allowed(self, resolved_key: str) -> None:
        if self._frozen_state.frozen and not self._ledger.has_accessed(resolved_key):
            raise MLPConfigFrozenError(
                f"Configuration is frozen; cannot access new key {resolved_key!r}."
            )

    def _missing_error(
        self,
        key: str,
        resolved_key: str,
        expected_type: str,
        sensitive: bool,
    ) -> MLPConfigMissingError:
        value = render_error_value(None, sensitive=sensitive)
        return MLPConfigMissingError(
            f"Missing required config key {key!r} resolved as {resolved_key!r}; "
            f"expected {expected_type}; value={value}."
        )

    def _value_error(
        self,
        key: str,
        resolved_key: str,
        expected_type: str,
        raw_value: str,
        sensitive: bool,
        detail: str,
    ) -> MLPConfigValueError:
        value = render_error_value(raw_value, sensitive=sensitive)
        return MLPConfigValueError(
            f"Invalid config key {key!r} resolved as {resolved_key!r}; "
            f"expected {expected_type}; value={value}; error={detail}."
        )


def _parse_int(raw: str) -> int:
    return int(raw.strip())


def _parse_float(raw: str) -> float:
    return float(raw.strip())


def _parse_bool(raw: str) -> bool:
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    raise ValueError("invalid boolean")


def _parse_json(raw: str) -> object:
    return deep_freeze(json.loads(raw))


def _parse_json_list(raw: str) -> tuple[object, ...]:
    value = json.loads(raw)
    if not isinstance(value, list):
        raise ValueError("expected JSON list")
    return tuple(deep_freeze(item) for item in value)
