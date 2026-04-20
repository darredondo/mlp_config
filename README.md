# mlp_config

`mlp_config` is a small reusable package for bootstrap configuration in MLP
applications and components. It lives under the shared `mlp` namespace and focuses on
reading, validating, auditing, and safely snapshotting explicitly accessed settings.

It is intentionally not a runtime configuration framework. Use it during application
startup, build the concrete values or component config objects your app needs, call
`freeze()`, and pass those values onward. Do not keep `Config` as a global mutable service
that components query lazily at runtime.

## Install

Core has no runtime dependencies:

```bash
pip install mlp-config
```

`.env` support is optional:

```bash
pip install "mlp-config[dotenv]"
```

Development tools are available through:

```bash
pip install "mlp-config[dev]"
```

## Basic Usage

```python
from mlp.config import Config, DotEnvSource, EnvSource

config = Config.from_sources([
    DotEnvSource(".env", required=False),
    EnvSource(),
])

db = config.prefixed("DB_")
db_url = db.require_str("URL", sensitive=True)

debug = config.get_bool("DEBUG", default=False)

config.freeze()
snapshot = config.snapshot()
```

Sources are applied in order. Later sources overwrite earlier ones, so
`Config.from_sources([DotEnvSource(".env"), EnvSource()])` lets real environment variables
win over `.env`.

`DotEnvSource` uses `python-dotenv`, does not mutate `os.environ`, and raises a clear
`MLPConfigSourceError` if the optional dependency is not installed.

## Bootstrap Discipline

`Config` is designed to make bootstrap explicit:

- read every required key during startup
- validate and convert values immediately
- construct component-specific config objects
- call `freeze()` when bootstrap is complete
- pass plain values or config dataclasses to runtime components

After `freeze()`, accessing a new key raises `MLPConfigFrozenError`. Re-reading a key that
was already accessed is allowed. This catches accidental lazy configuration reads in code
paths that should already be running with concrete values.

## Typed Accessors

Available accessors include:

- `get_raw` / `require_raw`
- `get_str` / `require_str`
- `get_int` / `require_int`
- `get_float` / `require_float`
- `get_bool` / `require_bool`
- `get_list` / `require_list`
- `get_json` / `require_json`
- `get_json_list` / `require_json_list`
- `has`

Booleans accept `1`, `true`, `yes`, `y`, `on` and `0`, `false`, `no`, `n`, `off`,
case-insensitively.

`get_list` is intentionally simple: it splits a string by a separator, defaults to comma,
strips items, and returns a tuple. If list values may contain the separator, use
`get_json_list` or choose a different separator.

Structured accessors return immutable data:

- lists and tuples become tuples
- dicts become `types.MappingProxyType`
- sets become frozensets
- nested structures are frozen recursively

## Access Ledger And Snapshot

`snapshot()` returns only the access ledger. It never dumps all of `os.environ` or all
loaded source values.

```python
config = Config.from_mapping({
    "DB_URL": "postgres://...",
    "PORT": "abc",
    "UNUSED": "not shown",
})

config.require_str("DB_URL", sensitive=True)

try:
    config.require_int("PORT")
except Exception:
    pass

print(config.snapshot())
```

Example shape:

```python
{
    "DB_URL": {
        "status": "ok",
        "expected_type": "str",
        "required": True,
        "sensitive": True,
        "value": "<redacted>",
    },
    "PORT": {
        "status": "invalid",
        "expected_type": "int",
        "required": True,
        "sensitive": False,
        "value": "abc",
        "error": "invalid int",
    },
}
```

The ledger records accesses before validation or conversion. If `PORT="abc"` and
`require_int("PORT")` fails, the invalid raw value is still visible in the safe snapshot
unless the key is sensitive.

## Sensitive Values

All accessors accept `sensitive: bool | None = None`.

- `sensitive=True` always redacts the value
- `sensitive=False` requests visibility, unless the key is already sensitive
- `sensitive=None` applies the built-in key-name heuristic

Sensitivity is monotonic: the most restrictive policy wins. Once a resolved key has been
treated as sensitive, later reads cannot make it visible again.

The built-in heuristic is case-insensitive and covers names containing markers such as
`PASSWORD`, `PASS`, `SECRET`, `TOKEN`, `API_KEY`, `AUTH`, `PRIVATE_KEY`, and `CREDENTIAL`.

## Prefixes

`prefixed()` creates a view over the same config values, ledger, and freeze state.

```python
config = Config.from_mapping({"APP_DB_URL": "postgres"}, prefix="APP_")
db = config.prefixed("DB_")

db.require_str("URL", sensitive=True)

assert "APP_DB_URL" in config.snapshot()
```

Snapshot keys are resolved absolute keys, not relative keys.

## Integration With mlp_db

`mlp_config` does not construct `MLPDatabase`, `RedisCache`, or other component objects.
In V1 it only helps bootstrap their explicit configuration values.

```python
from mlp.config import Config, DotEnvSource, EnvSource
from mlp.db import DatabaseConfig

config = Config.from_sources([
    DotEnvSource(".env", required=False),
    EnvSource(),
])

db_config = config.prefixed("DB_")
database_config = DatabaseConfig(
    url=db_config.require_str("URL", sensitive=True),
)

config.freeze()
print(config.snapshot())
```

## Checks

```bash
python -m pytest
python -m ruff check .
python -m pyright
python -m build
```

