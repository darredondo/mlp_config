from __future__ import annotations

from mlp.config import Config


def test_prefixed_concatenates_prefixes_and_uses_absolute_key() -> None:
    config = Config.from_mapping({"APP_DB_URL": "postgres"}, prefix="APP_")
    db = config.prefixed("DB_")

    assert db.require_str("URL") == "postgres"
    assert list(config.snapshot()) == ["APP_DB_URL"]


def test_prefixed_shares_ledger() -> None:
    config = Config.from_mapping({"DB_URL": "postgres"})
    db = config.prefixed("DB_")

    db.require_str("URL", sensitive=True)

    assert config.snapshot()["DB_URL"]["value"] == "<redacted>"  # type: ignore[index]

