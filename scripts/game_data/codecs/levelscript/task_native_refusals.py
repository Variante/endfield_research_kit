"""Reached task-condition native refusals, separate from unknown stored schemas.

This helper does not decode bytes. Current authenticated union identities,
not an older contract's numeric tags, select which owning audit is
relevant to a failed task-condition read. Unused proof failures are ignored.
"""
from __future__ import annotations

import importlib
import json
from typing import Any

from scripts.game_data import levelscript_union_tags as union_tags

_SOURCES = (
    ("levelscript_task_condition_native", "CONTRACT_PATH", "rows", "load_levelscript_task_condition_rows"),
    ("levelscript_taskmap_condition_native", "DEFAULT_CONTRACT", "routes", "validate_levelscript_taskmap_condition_native_contract"),
    ("levelscript_taskmap_followon_native", "DEFAULT_CONTRACT", "routes", "validate_levelscript_taskmap_followon_native_contract"),
    ("levelscript_taskmap_submit_native", "DEFAULT_CONTRACT", "route", "validate_levelscript_taskmap_submit_native_contract"),
    ("levelscript_taskmap_archery_native", "DEFAULT_CONTRACT", "route", "validate_levelscript_taskmap_archery_native_contract"),
    ("levelscript_check_game_inst_start_duration_native", "DEFAULT_CONTRACT", "route", "validate_levelscript_check_game_inst_start_duration_native_contract"),
    ("levelscript_check_fac_linking_mode_native", "DEFAULT_CONTRACT", "route", "validate_check_fac_linking_mode_native_contract"),
)


def _declared_owners() -> dict[tuple[int, int], list[tuple[str, str, Any]]]:
    owners = {}
    for name, path_attribute, row_key, audit_attribute in _SOURCES:
        module = importlib.import_module("scripts.game_data." + name)
        path = getattr(module, path_attribute)
        try:
            contract = json.loads(path.read_bytes())
        except (OSError, ValueError):
            # No identity may be inferred from a missing/unreadable contract.
            # The original decoder still refuses; no row becomes exact here.
            continue
        if not isinstance(contract, dict):
            continue
        declared = contract.get(row_key)
        rows = [declared] if row_key == "route" else declared
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            wrapper = row.get("wrapperName")
            if not isinstance(wrapper, str):
                continue
            current = union_tags.pair("GameCondition", union_tags.short_name(wrapper))
            if len(current) != 2 or not all(type(value) is int for value in current):
                continue
            # A renamed tag may retain a reviewed shape; a changed member
            # count is an unknown schema, even when the type name survives.
            reviewed_count = row.get("serializedMemberCount", row.get("memberCount"))
            if reviewed_count != current[1]:
                continue
            owners.setdefault(current, []).append((name, str(path), getattr(module, audit_attribute)))
    return owners


def reached_native_refusals(tag: int, member_count: int, *, base_known: bool = False) -> list[dict[str, Any]]:
    """Return only relevant failed audits; an unknown shape returns no claims."""
    tags = union_tags.union_tags_audit()
    if tags.get("status") != "validated":
        return [{"gate": "nativeContract", "owner": "levelscript_union_tags", "status": tags.get("status"),
                 "detail": "taskMap.condition.nativeContract: current union identity unavailable: " + str(tags.get("detail", ""))[:500]}]
    if base_known:
        return []
    failures = []
    for name, path, audit_reader in _declared_owners().get((tag, member_count), []):
        result = audit_reader()
        audit = result[1] if isinstance(result, tuple) else result
        if audit.get("status") == "validated":
            continue
        detail = str(audit.get("detail", ""))[:500]
        failures.append({"gate": "nativeContract", "owner": name, "source": path,
                         "status": audit.get("status"), "expected": "validated",
                         "actual": audit.get("status"), "failedGate": audit.get("failedGate", audit.get("failedCheck")),
                         "validationFailures": (audit.get("validationFailures") or [])[:8],
                         "detail": f"taskMap.condition.nativeContract: owner={name}, status={audit.get('status')}, detail={detail}"})
    return failures
