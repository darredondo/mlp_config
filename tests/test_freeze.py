from __future__ import annotations

import pytest

from mlp.config import Config, MLPConfigFrozenError


def test_freeze_blocks_new_key_and_allows_reread() -> None:
    config = Config.from_mapping({"A": "1", "B": "2"})

    assert config.require_str("A") == "1"
    config.freeze()
    assert config.require_str("A") == "1"

    with pytest.raises(MLPConfigFrozenError):
        config.require_str("B")


def test_prefixed_shares_freeze_state() -> None:
    config = Config.from_mapping({"DB_URL": "postgres"})
    db = config.prefixed("DB_")

    config.freeze()

    with pytest.raises(MLPConfigFrozenError):
        db.require_str("URL")


def test_snapshot_stays_stable_after_freeze() -> None:
    config = Config.from_mapping({"A": "1"})
    config.require_str("A")
    before = config.snapshot()

    config.freeze()

    assert config.snapshot() == before

