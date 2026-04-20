from __future__ import annotations

import pytest

from mlp.config import Config, MLPConfigFrozenError, MLPConfigMissingError, MLPConfigValueError


def test_value_error_redacts_secret_and_includes_resolved_key() -> None:
    config = Config.from_mapping({"APP_PASSWORD": "not-an-int"}, prefix="APP_")

    with pytest.raises(MLPConfigValueError) as exc_info:
        config.require_int("PASSWORD")

    message = str(exc_info.value)
    assert "APP_PASSWORD" in message
    assert "<redacted>" in message
    assert "not-an-int" not in message


def test_missing_error_includes_logical_and_resolved_key() -> None:
    config = Config.from_mapping({}, prefix="APP_")

    with pytest.raises(MLPConfigMissingError) as exc_info:
        config.require_str("URL")

    message = str(exc_info.value)
    assert "'URL'" in message
    assert "'APP_URL'" in message
    assert "expected str" in message


def test_frozen_error_is_clear() -> None:
    config = Config.from_mapping({"A": "1"})
    config.freeze()

    with pytest.raises(MLPConfigFrozenError, match="Configuration is frozen"):
        config.require_str("A")

