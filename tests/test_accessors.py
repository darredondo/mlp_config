from __future__ import annotations

from types import MappingProxyType

import pytest

from mlp.config import Config, MLPConfigMissingError, MLPConfigValueError


def test_raw_str_int_float_bool_accessors_and_defaults() -> None:
    config = Config.from_mapping(
        {
            "RAW": " raw ",
            "STR": " value ",
            "INT": "42",
            "FLOAT": "2.5",
            "BOOL": "yes",
        }
    )

    assert config.require_raw("RAW") == " raw "
    assert config.require_str("STR") == "value"
    assert config.require_int("INT") == 42
    assert config.require_float("FLOAT") == 2.5
    assert config.require_bool("BOOL") is True
    assert config.get_str("MISSING", default="fallback") == "fallback"
    assert config.get_int("MISSING_INT", default=7) == 7


@pytest.mark.parametrize("raw", ["1", "true", "TRUE", "yes", "y", "on"])
def test_bool_true_variants(raw: str) -> None:
    assert Config.from_mapping({"FLAG": raw}).require_bool("FLAG") is True


@pytest.mark.parametrize("raw", ["0", "false", "FALSE", "no", "n", "off"])
def test_bool_false_variants(raw: str) -> None:
    assert Config.from_mapping({"FLAG": raw}).require_bool("FLAG") is False


def test_invalid_conversions_and_missing_required() -> None:
    config = Config.from_mapping({"INT": "abc", "BOOL": "maybe"})

    with pytest.raises(MLPConfigValueError):
        config.require_int("INT")
    with pytest.raises(MLPConfigValueError):
        config.require_bool("BOOL")
    with pytest.raises(MLPConfigMissingError):
        config.require_str("MISSING")


def test_list_returns_tuple_and_custom_separator() -> None:
    config = Config.from_mapping({"LIST": "a, b,, c", "PIPE": "a|b|c"})

    assert config.require_list("LIST") == ("a", "b", "c")
    assert config.require_list("PIPE", separator="|") == ("a", "b", "c")


def test_json_returns_immutable_structures() -> None:
    config = Config.from_mapping({"JSON": '{"a": [1, {"b": 2}]}'})

    value = config.require_json("JSON")

    assert isinstance(value, MappingProxyType)
    assert value["a"][1]["b"] == 2  # type: ignore[index]
    with pytest.raises(TypeError):
        value["c"] = 3  # type: ignore[index]


def test_json_list_returns_tuple_and_invalid_json() -> None:
    config = Config.from_mapping({"LIST": '[1, {"a": [2]}]', "OBJECT": '{"a": 1}', "BAD": "nope"})

    assert config.require_json_list("LIST") == (1, {"a": (2,)})
    with pytest.raises(MLPConfigValueError):
        config.require_json_list("OBJECT")
    with pytest.raises(MLPConfigValueError):
        config.require_json("BAD")

