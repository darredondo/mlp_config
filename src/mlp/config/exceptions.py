"""Exceptions raised by mlp_config."""

from __future__ import annotations


class MLPConfigError(Exception):
    """Base error for configuration failures."""


class MLPConfigMissingError(MLPConfigError):
    """Raised when a required configuration key is missing."""


class MLPConfigValueError(MLPConfigError):
    """Raised when a configuration value cannot be converted or validated."""


class MLPConfigFrozenError(MLPConfigError):
    """Raised when code tries to access a new key after configuration freeze."""


class MLPConfigSourceError(MLPConfigError):
    """Raised when a configuration source cannot be loaded."""

