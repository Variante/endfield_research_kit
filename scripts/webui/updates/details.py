"""Deterministic field changes for export-source and catalog comparisons.

Missing members are distinct from null. Lists are matched by authored IDs when
both lists provide unique IDs, otherwise their stored indices are preserved.
"""
from __future__ import annotations

from typing import Any


_MISSING = object()


def _display_value(value: Any) -> Any:
    # JSON numbers beyond JavaScript's safe range lose ID precision in the UI.
    if isinstance(value, int) and not isinstance(value, bool) and abs(value) > 9007199254740991:
        return str(value)
    if isinstance(value, dict):
        return {key: _display_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_display_value(item) for item in value]
    return value


def field_changes(before: Any, after: Any, path: tuple = ()) -> list[dict[str, Any]]:
    if before is not _MISSING and after is not _MISSING and type(before) is type(after) and before == after:
        return []
    # Keep one-sided records field-addressable too, so added/deleted records
    # can show their selected language without displaying every translation.
    if before is _MISSING and isinstance(after, dict) and after:
        return [change for key in sorted(after)
                for change in field_changes(_MISSING, after[key], (*path, key))]
    if after is _MISSING and isinstance(before, dict) and before:
        return [change for key in sorted(before)
                for change in field_changes(before[key], _MISSING, (*path, key))]
    if isinstance(before, dict) and isinstance(after, dict):
        return [change for key in sorted(before.keys() | after.keys())
                for change in field_changes(before.get(key, _MISSING), after.get(key, _MISSING), (*path, key))]
    if isinstance(before, list) and isinstance(after, list):
        for identity in ("id", "key"):
            if before and after and all(isinstance(row, dict) and isinstance(row.get(identity), (str, int))
                                        for row in before + after):
                old = {str(row[identity]): row for row in before}
                new = {str(row[identity]): row for row in after}
                if len(old) == len(before) and len(new) == len(after):
                    return [change for key in sorted(old.keys() | new.keys())
                            for change in field_changes(old.get(key, _MISSING), new.get(key, _MISSING),
                                                        (*path, f"{identity}={key}"))]
        return [change for index in range(max(len(before), len(after)))
                for change in field_changes(before[index] if index < len(before) else _MISSING,
                                            after[index] if index < len(after) else _MISSING, (*path, index))]
    change = {"path": list(path), "status": "added" if before is _MISSING else "deleted" if after is _MISSING else "modified"}
    if before is not _MISSING:
        change["before"] = _display_value(before)
    if after is not _MISSING:
        change["after"] = _display_value(after)
    return [change]


def source_changes(before: dict | None, after: dict | None) -> list[dict[str, Any]]:
    old, new = before or {}, after or {}
    changes = []
    for source in sorted(old.keys() | new.keys()):
        fields = field_changes(old.get(source, _MISSING), new.get(source, _MISSING))
        if fields:
            changes.append({"source": source, "status": "added" if source not in old else "deleted" if source not in new else "modified",
                            "fields": fields})
    return changes
