from __future__ import annotations

import builtins

import pytest

from mlp.config import Config, DotEnvSource, EnvSource, MappingSource, MLPConfigSourceError


def test_env_source_reads_mapping() -> None:
    assert EnvSource({"A": "1"}).load() == {"A": "1"}


def test_mapping_source_copies_values() -> None:
    values = {"A": "1"}
    source = MappingSource(values)
    values["A"] = "2"
    assert source.load() == {"A": "1"}


def test_source_precedence_later_sources_win() -> None:
    config = Config.from_sources([MappingSource({"A": "from-file"}), MappingSource({"A": "env"})])
    assert config.require_str("A") == "env"


def test_dotenv_missing_optional_returns_empty(tmp_path) -> None:
    assert DotEnvSource(tmp_path / ".env", required=False).load() == {}


def test_dotenv_missing_required_raises(tmp_path) -> None:
    with pytest.raises(MLPConfigSourceError):
        DotEnvSource(tmp_path / ".env", required=True).load()


def test_dotenv_dependency_missing_has_clear_message(tmp_path, monkeypatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("A=1\n", encoding="utf-8")
    original_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):  # type: ignore[no-untyped-def]
        if name == "dotenv":
            raise ImportError("missing")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(MLPConfigSourceError, match="mlp-config\\[dotenv\\]"):
        DotEnvSource(env_file).load()

