"""Secret detection and safe value rendering."""

from __future__ import annotations

REDACTED = "<redacted>"
_SECRET_MARKERS = (
    "PASSWORD",
    "PASS",
    "SECRET",
    "TOKEN",
    "API_KEY",
    "AUTH",
    "PRIVATE_KEY",
    "CREDENTIAL",
)
_MAX_VISIBLE_LENGTH = 120


def is_sensitive_key(key: str) -> bool:
    """Return whether a key name should be treated as sensitive by default."""

    upper_key = key.upper()
    return any(marker in upper_key for marker in _SECRET_MARKERS)


def render_value(value: object | None, *, sensitive: bool) -> object | None:
    """Render a value for diagnostics without leaking secrets."""

    if value is None:
        return None
    if sensitive:
        return REDACTED
    if isinstance(value, str):
        return _truncate(value)
    return value


def render_error_value(value: str | None, *, sensitive: bool) -> str:
    """Render raw input for exception messages."""

    if value is None:
        return "<missing>"
    if sensitive:
        return REDACTED
    return repr(_truncate(value))


def redact_config(values: dict[str, object]) -> dict[str, object]:
    """Return a shallow redacted copy using the built-in key-name heuristic."""

    return {
        key: render_value(value, sensitive=is_sensitive_key(key))
        for key, value in values.items()
    }


def _truncate(value: str) -> str:
    if len(value) <= _MAX_VISIBLE_LENGTH:
        return value
    return f"{value[:_MAX_VISIBLE_LENGTH]}..."
