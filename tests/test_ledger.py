from __future__ import annotations

import pytest

from mlp.config import Config, MLPConfigValueError


def test_accessor_registers_before_validation_and_invalid_is_snapshotted() -> None:
    config = Config.from_mapping({"PORT": "abc"})

    with pytest.raises(MLPConfigValueError):
        config.require_int("PORT")

    assert config.snapshot()["PORT"] == {
        "status": "invalid",
        "expected_type": "int",
        "required": True,
        "sensitive": False,
        "value": "abc",
        "error": "invalid int",
    }


def test_missing_required_appears_in_snapshot() -> None:
    config = Config.from_mapping({})

    with pytest.raises(Exception):
        config.require_str("URL")

    assert config.snapshot()["URL"]["status"] == "missing"  # type: ignore[index]
    assert config.snapshot()["URL"]["required"] is True  # type: ignore[index]


def test_snapshot_only_includes_accessed_keys() -> None:
    config = Config.from_mapping({"A": "1", "B": "2"})

    config.require_str("A")

    assert list(config.snapshot()) == ["A"]


def test_sensitive_true_and_heuristic_redact() -> None:
    config = Config.from_mapping({"URL": "postgres://secret", "API_TOKEN": "token"})

    config.require_str("URL", sensitive=True)
    config.require_str("API_TOKEN")

    assert config.snapshot()["URL"]["value"] == "<redacted>"  # type: ignore[index]
    assert config.snapshot()["API_TOKEN"]["value"] == "<redacted>"  # type: ignore[index]


def test_sensitive_false_cannot_unmark_sensitive_key() -> None:
    config = Config.from_mapping({"PASSWORD": "secret"})

    config.require_str("PASSWORD")
    config.require_str("PASSWORD", sensitive=False)

    assert config.snapshot()["PASSWORD"]["sensitive"] is True  # type: ignore[index]
    assert config.snapshot()["PASSWORD"]["value"] == "<redacted>"  # type: ignore[index]


def test_later_sensitive_true_redacts_previous_visible_value() -> None:
    config = Config.from_mapping({"URL": "visible"})

    config.require_str("URL", sensitive=False)
    assert config.snapshot()["URL"]["value"] == "visible"  # type: ignore[index]

    config.require_str("URL", sensitive=True)

    assert config.snapshot()["URL"]["sensitive"] is True  # type: ignore[index]
    assert config.snapshot()["URL"]["value"] == "<redacted>"  # type: ignore[index]

