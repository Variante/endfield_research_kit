"""Selected-native SkillData ShowComboSkillUI 0x015F stored reader.

The reviewed Buff residual frontier supplies its direct four-member source
route. The stored action does not show that combo UI appeared at runtime.
"""
from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data import buff_frontiers_native
from scripts.game_data.il2cpp.native_image import read_reviewed_contract
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.derived_schema import resolve_routes


LABEL = "skillTimelineShowComboSkillUI"
TAG = 0x015F
CONTRACT_PATH = CONTRACTS_DIR / "buff_residual_frontier.json"
TYPE_NAME = "Beyond.Gameplay.Core.ShowComboSkillUI+Data"
WRAPPER_NAME = "Beyond.MemoryPack.Beyond_Gameplay_Core_ShowComboSkillUI_DataForMemoryPack"
FIELD_NAMES = ("isEnable", "priorityLevel", "priorityOffset", "serverActionIndex")
READ_KINDS = ("byte", "scalar32", "scalar32", "scalar32")
PLAN = (
    ("isEnable", "fixed", 1, "bool"),
    ("priorityLevel", "fixed", 4, "scalar32"),
    ("priorityOffset", "fixed", 4, "scalar32"),
    ("serverActionIndex", "fixed", 4, "scalar32"),
)


def _contract() -> dict[str, Any]:
    contract, _ = read_reviewed_contract(
        CONTRACT_PATH, schema="endfield.buff-residual-frontier-native-contract.v1",
        label=LABEL, status="exact-current-build",
    )
    rows = [row for row in contract.get("actions", ()) if row.get("unionTag") == TAG]
    if (
        len(rows) != 1 or rows[0].get("serializedMemberCount") != len(FIELD_NAMES)
        or rows[0].get("wrapperName") != WRAPPER_NAME
        or tuple(rows[0].get("readOrder", ())) != READ_KINDS
    ):
        raise ValueError(f"{LABEL}.contract:source-shape")
    return contract


def validate_current_native_contract(*, gameassembly: Path, metadata: Path) -> dict[str, Any]:
    """Authenticate reviewed source and derived wrapper on selected inputs."""
    contract = _contract()
    expected = contract["nativeInputs"]
    gate = check_installed_native_inputs(
        expected["GameAssembly.dll"], expected["global-metadata.dat"],
        gameassembly=Path(gameassembly), metadata=Path(metadata),
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise ValueError(f"{LABEL}.native:{gate.status}:{gate.detail}")
    selected_metadata = gate.metadata
    if (selected_metadata.parent.name.lower() != "metadata"
            or selected_metadata.parents[1].name.lower() != "il2cpp_data"
            or selected_metadata.parents[2].parent != gate.gameassembly.parent):
        raise ValueError(f"{LABEL}.native:selected-path-layout")
    rows, frontier_audit = buff_frontiers_native.load_rows(
        "residual", game_root=selected_metadata.parents[2],
    )
    source = rows.get(TAG)
    if (
        frontier_audit.get("status") != "validated"
        or not isinstance(source, dict)
        or source.get("wrapperName") != WRAPPER_NAME
        or source.get("serializedMemberCount") != len(FIELD_NAMES)
        or tuple(source.get("readOrder", ())) != READ_KINDS
    ):
        raise ValueError(f"{LABEL}.native:residual-frontier:{frontier_audit.get('status')}")
    routes, resolver, audit = resolve_routes(
        gameassembly=gate.gameassembly, metadata=gate.metadata,
    )
    route = routes.get(TAG, {})
    definition = route.get("wrapperTypeDefinition")
    plan = resolver.plans.get(definition) if resolver is not None else None
    wrapper = resolver.wrappers.get(definition) if resolver is not None else None
    if (
        audit.get("status") != "validated" or audit.get("routeAudit") != "validated"
        or route.get("status") != "determined"
        or route.get("evidenceTier") != "direct"
        or route.get("wrapperName") != WRAPPER_NAME
        or wrapper is None or wrapper.wrapped_type != TYPE_NAME
        or not isinstance(plan, tuple)
        or tuple((member.name, member.kind, member.width, member.scalar)
                 for member in plan) != PLAN
    ):
        raise ValueError(f"{LABEL}.native:generated-plan-drift")
    return {"status": "validated", "unionTag": TAG, "nativeInputs": expected,
            "sourceReadCount": len(READ_KINDS)}


def _consume_action(reader: Reader, width: int) -> dict[str, Any]:
    if width != 3 or reader.data[reader.pos:reader.pos + width] != b"\xFA\x5F\x01":
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    start = reader.pos
    reader.take(width, "union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-wrapper")
        return {"status": "exact-null-wrapper", "start": start, "end": reader.pos}
    reader.header(len(FIELD_NAMES))
    fields = []
    for index, (name, kind) in enumerate(zip(FIELD_NAMES, READ_KINDS)):
        field_start = reader.pos
        reader.take(1 if index == 0 else 4, name)
        fields.append({"name": name, "kind": kind, "start": field_start,
                       "end": reader.pos})
    return {"status": "exact-stored-action-span", "start": start,
            "end": reader.pos, "tag": TAG, "fields": fields,
            "evidenceBoundary": "stored framing only"}


def decode_action(data: bytes, offset: int, *, validation: Mapping[str, Any]) -> dict[str, Any]:
    if validation.get("status") != "validated" or validation.get("unionTag") != TAG:
        raise ValueError(f"{LABEL}.native:not-validated")
    if type(offset) is not int or offset < 0 or offset + 4 > len(data):
        raise ValueError(f"{LABEL}.source:offset-outside-source")
    reader = Reader(data, f"{LABEL}.source")
    reader.pos = offset
    return _consume_action(reader, 3)


def decode_shared_action(reader: Reader, depth: int, tag: int, width: int) -> None:
    del depth
    if tag != TAG:
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    _consume_action(reader, width)
