"""Access ledger used to build safe configuration snapshots."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from typing import Literal

from .redaction import is_sensitive_key, render_value

AccessStatus = Literal["ok", "missing", "invalid"]


@dataclass(slots=True)
class AccessRecord:
    key: str
    resolved_key: str
    expected_type: str
    required: bool
    found: bool
    status: AccessStatus
    sensitive: bool
    raw_value: str | None
    value_repr: object | None
    error: str | None


class AccessLedger:
    """Tracks explicit accesses and applies monotonic sensitivity policy."""

    def __init__(self) -> None:
        self._records: OrderedDict[str, AccessRecord] = OrderedDict()
        self._sensitive_keys: set[str] = set()

    def has_accessed(self, resolved_key: str) -> bool:
        return resolved_key in self._records

    def resolve_sensitive(self, resolved_key: str, sensitive: bool | None) -> bool:
        policy_sensitive = is_sensitive_key(resolved_key) if sensitive is None else sensitive
        final_sensitive = policy_sensitive or resolved_key in self._sensitive_keys
        if final_sensitive:
            self._sensitive_keys.add(resolved_key)
        return final_sensitive

    def record(
        self,
        *,
        key: str,
        resolved_key: str,
        expected_type: str,
        required: bool,
        found: bool,
        status: AccessStatus,
        sensitive: bool,
        raw_value: str | None,
        value_repr: object | None,
        error: str | None,
    ) -> None:
        if sensitive:
            self._sensitive_keys.add(resolved_key)
        final_sensitive = resolved_key in self._sensitive_keys or sensitive
        self._records[resolved_key] = AccessRecord(
            key=key,
            resolved_key=resolved_key,
            expected_type=expected_type,
            required=required,
            found=found,
            status=status,
            sensitive=final_sensitive,
            raw_value=raw_value,
            value_repr=render_value(value_repr, sensitive=final_sensitive),
            error=error,
        )

    def snapshot(self) -> dict[str, object]:
        result: dict[str, object] = {}
        for resolved_key, record in self._records.items():
            sensitive = resolved_key in self._sensitive_keys or record.sensitive
            item: dict[str, object] = {
                "status": record.status,
                "expected_type": record.expected_type,
                "required": record.required,
                "sensitive": sensitive,
                "value": render_value(record.raw_value, sensitive=sensitive),
            }
            if record.error is not None:
                item["error"] = record.error
            result[resolved_key] = item
        return result

