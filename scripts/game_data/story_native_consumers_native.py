"""Prove the Story builders' named native consumers on the installed build.

``contracts/story_native_consumers.json`` states, per consumer group, which
methods Story evidence cites and what each body does as checkable claims, plus
a ``cited`` map of methods Story rows only name, resolved to a token and address
on the selected build without a claim about their meaning. The
claims are evaluated by name against whichever build is installed, so a client
update re-proves them instead of failing a pinned token, address or hash.

Opening the native index takes most of a minute, so the result is cached in a
report keyed by the installed GameAssembly/metadata hashes and the contract's
bytes; any change to either re-evaluates. A group whose claims fail, one marked
``pendingReview`` because its code moved and the reviewed meaning was not
re-checked, or a missing install yields a non-validated group, and consumers
must publish no native conclusion from it.
"""
from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from scripts.common import (
    STORY_RECOVERY_REPORTS_DIR,
    check_installed_native_inputs,
    write_canonical_json,
)
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.body_claims import BodyIndex, ClaimError
from scripts.game_data.il2cpp.body_claims import evaluate as evaluate_claims
from scripts.game_data.il2cpp.native_image import open_native_image


SCHEMA = "endfield.story-native-consumers.v1"
REPORT_SCHEMA = "storyNativeConsumersEvaluation.v1"
DEFAULT_CONTRACT = CONTRACTS_DIR / "story_native_consumers.json"
DEFAULT_REPORT = STORY_RECOVERY_REPORTS_DIR / "story_native_consumers.json"


def _evaluate(contract: dict[str, Any], index: BodyIndex) -> dict[str, Any]:
    groups: dict[str, Any] = {}
    for name, group in contract["groups"].items():
        rows, failures = evaluate_claims(index, group["methods"])
        offsets: dict[str, str] = {}
        for field_name in group.get("fields") or []:
            try:
                offsets[field_name] = f"0x{index.field_offset(field_name):x}"
            except ClaimError as error:
                failures.append({"symbol": field_name, "claim": "fields", "reason": str(error)})
        status = "mismatched" if failures else "validated"
        if status == "validated" and group.get("pendingReview"):
            status = "pending_review"
        groups[name] = {
            "status": status,
            "mappingId": group["mappingId"],
            "methods": [
                {
                    "method": row["symbol"],
                    "token": row["token"],
                    "address": row["address"],
                    "fallbackPatchId": index.ifix_patch_id(int(row["address"], 16)),
                    "contract": row["contract"],
                }
                for row in rows
            ],
            "fieldOffsets": offsets,
            "pendingReview": group.get("pendingReview", ""),
            "failures": failures,
        }
    return groups


def _resolve_cited(contract: dict[str, Any], index: BodyIndex) -> dict[str, Any]:
    """Token and address of each cited method, when one body carries the name."""
    cited: dict[str, Any] = {}
    for display, full in (contract.get("cited") or {}).items():
        pointers = sorted(index.pointers_by_name.get(full) or [])
        row: dict[str, Any] = {"method": full, "token": None, "address": None, "fallbackPatchId": None}
        if len(pointers) == 1:
            names = [
                entry for entry in index.names_by_pointer[pointers[0]]
                if f"{entry.get('type')}.{entry.get('method')}" == full
            ]
            row["token"] = names[0].get("token") if names else None
            row["address"] = f"0x{pointers[0]:x}"
            row["fallbackPatchId"] = index.ifix_patch_id(pointers[0])
        else:
            row["overloads"] = len(pointers)
        cited[display] = row
    return cited


@lru_cache(maxsize=None)
def load_story_native_consumers(
    contract_path: Path = DEFAULT_CONTRACT,
    report_path: Path = DEFAULT_REPORT,
) -> dict[str, Any]:
    """Return every consumer group's status on the installed build."""
    raw = Path(contract_path).read_bytes()
    contract = json.loads(raw)
    if contract.get("schema") != SCHEMA:
        raise ValueError(f"{contract_path}: schema {contract.get('schema')!r}, expected {SCHEMA}")
    native = check_installed_native_inputs()
    if not native.validated:
        return {"status": native.status, "detail": native.detail, "groups": {}}
    key = {
        "_schema": REPORT_SCHEMA,
        "contractSha256": hashlib.sha256(raw).hexdigest(),
        "gameAssemblySha256": native.gameassembly_sha256.upper(),
        "globalMetadataSha256": native.metadata_sha256.upper(),
    }
    try:
        cached = json.loads(Path(report_path).read_bytes())
    except (OSError, ValueError):
        cached = {}
    if isinstance(cached, dict) and all(cached.get(k) == v for k, v in key.items()):
        return {"status": "validated", **cached}
    index = BodyIndex(open_native_image(native.gameassembly, native.metadata))
    result = {
        **key,
        "groups": _evaluate(contract, index),
        "cited": _resolve_cited(contract, index),
    }
    write_canonical_json(Path(report_path), result)
    return {"status": "validated", **result}


def validated_group(name: str) -> dict[str, Any] | None:
    """The named group with the build hashes, or None unless its claims hold."""
    evaluation = load_story_native_consumers()
    group = (evaluation.get("groups") or {}).get(name)
    if evaluation.get("status") != "validated" or not group or group.get("status") != "validated":
        return None
    return {
        **group,
        "gameAssemblySha256": evaluation["gameAssemblySha256"],
        "globalMetadataSha256": evaluation["globalMetadataSha256"],
    }


def consumer_rows(name: str, methods: list[str]) -> list[dict[str, Any]]:
    """``method``/``token``/``address`` rows for the named methods of a validated group."""
    group = validated_group(name)
    if group is None:
        return []
    by_name = {row["method"]: row for row in group["methods"]}
    return [dict(by_name[method]) for method in methods]


def cited(display: str) -> dict[str, Any]:
    """The installed build's ``method``/``token``/``address`` for a cited name.

    Token and address are None when the build is not validated, the name is
    not in the contract's ``cited`` map, or several overloads share it.
    """
    evaluation = load_story_native_consumers()
    row = (evaluation.get("cited") or {}).get(display)
    if evaluation.get("status") != "validated" or not row:
        return {"method": display, "token": None, "address": None, "fallbackPatchId": None}
    return dict(row)


def cited_token(display: str) -> str | None:
    return cited(display)["token"]


def cited_address(display: str) -> str | None:
    return cited(display)["address"]


__all__ = [
    "cited",
    "cited_address",
    "cited_token",
    "DEFAULT_CONTRACT",
    "DEFAULT_REPORT",
    "SCHEMA",
    "consumer_rows",
    "load_story_native_consumers",
    "validated_group",
]
