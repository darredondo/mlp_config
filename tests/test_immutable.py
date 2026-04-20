from __future__ import annotations

from types import MappingProxyType

import pytest

from mlp.config import Config
from mlp.config.immutable import deep_freeze


def test_get_list_returns_tuple() -> None:
    assert Config.from_mapping({"A": "x,y"}).require_list("A") == ("x", "y")


def test_get_json_dict_returns_mapping_proxy() -> None:
    value = Config.from_mapping({"A": '{"x": 1}'}).require_json("A")
    assert isinstance(value, MappingProxyType)


def test_nested_structures_are_deep_frozen() -> None:
    value = deep_freeze({"a": [{"b": {1, 2}}]})

    assert isinstance(value, MappingProxyType)
    assert value["a"][0]["b"] == frozenset({1, 2})  # type: ignore[index]


def test_mutating_returned_json_fails() -> None:
    value = Config.from_mapping({"A": '{"x": [1]}'}).require_json("A")

    with pytest.raises(TypeError):
        value["x"] = []  # type: ignore[index]
    with pytest.raises(AttributeError):
        value["x"].append(2)  # type: ignore[index, union-attr]

