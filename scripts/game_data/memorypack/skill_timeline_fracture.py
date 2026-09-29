"""Selected-native SkillData FractureAction 0x00BE stored reader.

The selected Buff frontier already reviews this action dispatcher and its
fifteen source reads. This reader reuses that contract for SkillData framing;
the stored fields do not establish a live fracture or target choice.
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


LABEL = "skillTimelineFracture"
TAG = 0x00BE
CONTRACT_PATH = CONTRACTS_DIR / "buff_frontier9.json"
TYPE_NAME = "Beyond.Gameplay.Core.FractureAction+Data"
WRAPPER_NAME = "Beyond.MemoryPack.Beyond_Gameplay_Core_FractureAction_DataForMemoryPack"
FIELD_NAMES = (
    "isEnable", "priorityLevel", "priorityOffset", "serverActionIndex",
    "attackerTargetSettings", "blowOffDistance", "blowOffHeight", "deadOption",
    "directionSettings", "distanceRandomRange", "isExtra", "overwriteHeight",
    "targetSettings", "totalTime", "immobilizedTime",
)
READ_KINDS = (
    "byte", "scalar32", "scalar32", "scalar32", "target-settings",
    "blackboard-double", "blackboard-double", "enum32", "direction-settings",
    "blackboard-double", "bool", "bool", "target-settings",
    "blackboard-double", "float32",
)


def _contract() -> dict[str, Any]:
    contract, _ = read_reviewed_contract(
        CONTRACT_PATH, schema="endfield.buff-frontier9-native-contract.v1",
        label=LABEL, status="exact-current-build",
    )
    rows = [row for row in contract.get("actions", ()) if row.get("unionTag") == TAG]
    if (
        len(rows) != 1 or rows[0].get("serializedMemberCount") != len(FIELD_NAMES)
        or rows[0].get("actualTypeName") != TYPE_NAME
        or rows[0].get("wrapperName") != WRAPPER_NAME
        or tuple(rows[0].get("readOrder", ())) != READ_KINDS
        or len(rows[0].get("nestedContextUsage", ())) != 7
    ):
        raise ValueError(f"{LABEL}.contract:source-shape")
    return contract


def validate_current_native_contract(*, gameassembly: Path, metadata: Path) -> dict[str, Any]:
    """Authenticate the reviewed Buff frontier against explicit selected inputs."""
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
    rows, audit = buff_frontiers_native.load_rows(
        "frontier9", game_root=selected_metadata.parents[2],
    )
    row = rows.get(TAG)
    if (
        audit.get("status") != "validated" or not isinstance(row, dict)
        or row.get("actualTypeName") != TYPE_NAME
        or row.get("wrapperName") != WRAPPER_NAME
        or row.get("serializedMemberCount") != len(FIELD_NAMES)
        or tuple(row.get("readOrder", ())) != READ_KINDS
        or len(row.get("nestedContextUsage", ())) != 7
    ):
        raise ValueError(f"{LABEL}.native:frontier9:{audit.get('status')}")
    return {"status": "validated", "unionTag": TAG, "nativeInputs": expected,
            "sourceReadCount": len(READ_KINDS), "nestedContextCount": 7}


def _consume_action(reader: Reader, width: int) -> dict[str, Any]:
    if width != 1 or reader.data[reader.pos:reader.pos + width] != b"\xBE":
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    start = reader.pos
    reader.take(width, "union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-wrapper")
        return {"status": "exact-null-wrapper", "start": start, "end": reader.pos}
    reader.header(len(FIELD_NAMES))
    fields = []
    for name, kind in zip(FIELD_NAMES, READ_KINDS):
        field_start = reader.pos
        if kind in ("byte", "bool"):
            reader.take(1, name)
        elif kind in ("scalar32", "enum32", "float32"):
            reader.take(4, name)
        elif kind == "target-settings":
            reader.target_profile()
        elif kind == "blackboard-double":
            reader.scalar_payload()
        elif kind == "direction-settings":
            reader.direction_profile()
        else:
            raise AssertionError(kind)
        fields.append({"name": name, "kind": kind, "start": field_start,
                       "end": reader.pos})
    return {"status": "exact-stored-action-span", "start": start,
            "end": reader.pos, "tag": TAG, "fields": fields,
            "evidenceBoundary": "stored framing only"}


def decode_action(data: bytes, offset: int, *, validation: Mapping[str, Any]) -> dict[str, Any]:
    if validation.get("status") != "validated" or validation.get("unionTag") != TAG:
        raise ValueError(f"{LABEL}.native:not-validated")
    if type(offset) is not int or offset < 0 or offset + 2 > len(data):
        raise ValueError(f"{LABEL}.source:offset-outside-source")
    reader = Reader(data, f"{LABEL}.source")
    reader.pos = offset
    return _consume_action(reader, 1)


def decode_shared_action(reader: Reader, depth: int, tag: int, width: int) -> None:
    del depth
    if tag != TAG:
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    _consume_action(reader, width)
