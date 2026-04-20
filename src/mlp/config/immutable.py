"""Helpers for returning immutable configuration structures."""

from __future__ import annotations

from types import MappingProxyType
from typing import Mapping


def deep_freeze(value: object) -> object:
    """Recursively convert mutable containers into immutable equivalents."""

    if isinstance(value, Mapping):
        return MappingProxyType({key: deep_freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(deep_freeze(item) for item in value)
    if isinstance(value, set):
        return frozenset(deep_freeze(item) for item in value)
    return value

