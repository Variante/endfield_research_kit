"""Selected-native SkillData DispelAction 0x009F stored-action reader.

The Buff reader's independently reviewed nine-member source order is reused
here for SkillData, including native-gated shared admission. The complete
SkillData family gate owns publication; stored values do not prove runtime
dispel behavior or selected targets.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.il2cpp.context_audit_memorypack import buff_action_read_order
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.derived_schema import resolve_routes


LABEL = "skillTimelineDispel"
CONTRACT_PATH = CONTRACTS_DIR / "skill_timeline_dispel_native.json"
SCHEMA = "endfield.skill-timeline-dispel-native-contract.v1"


def _contract() -> dict[str, Any]:
    contract, _ = read_reviewed_contract(
        CONTRACT_PATH, schema=SCHEMA, status="exact-current-build", label=LABEL,
    )
    names = contract.get("fieldNames")
    kinds = contract.get("readKinds")
    if (
        type(contract.get("unionTag")) is not int
        or not isinstance(names, list)
        or not isinstance(kinds, list)
        or len(names) != len(kinds)
        or len(kinds) != contract.get("serializedMemberCount")
        or len(set(names)) != len(names)
        or not all(isinstance(name, str) and name for name in names)
        or not all(kind in {"byte", "scalar32", "target-profile", "query-profile"}
                   for kind in kinds)
        or not isinstance(contract.get("wrapperName"), str)
        or not isinstance(contract.get("actualTypeName"), str)
        or not isinstance(contract.get("nativeInputs"), dict)
        or not isinstance(contract.get("selectedSource"), dict)
    ):
        raise ValueError(f"{LABEL}.contract:source-shape")
    path = Path(str(contract.get("sourceReadContract", "")))
    if path.name != str(path) or path.suffix != ".json":
        raise ValueError(f"{LABEL}.contract:source-dependency-path")
    return contract


def validate_current_native_contract(*, gameassembly: Path, metadata: Path) -> dict[str, Any]:
    """Authenticate selected methods, code windows, contexts, and wrapper plan."""
    contract = _contract()
    expected = contract["nativeInputs"]
    gate = check_installed_native_inputs(
        expected["GameAssembly.dll"], expected["global-metadata.dat"],
        gameassembly=Path(gameassembly), metadata=Path(metadata),
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise ValueError(f"{LABEL}.native:{gate.status}:{gate.detail}")
    unity = gate.gameassembly.parent / "UnityPlayer.dll"
    if not unity.is_file():
        raise ValueError(f"{LABEL}.native:UnityPlayer.dll:missing")
    with unity.open("rb") as stream:
        unity_hash = hashlib.file_digest(stream, "sha256").hexdigest().upper()
    if unity_hash != expected["UnityPlayer.dll"]:
        raise ValueError(f"{LABEL}.native:UnityPlayer.dll:mismatched")

    source_path = CONTRACTS_DIR / contract["sourceReadContract"]
    source = json.loads(source_path.read_bytes())
    key = contract["sourceReadOrderKey"]
    kinds = contract["readKinds"]
    if (
        source.get("schemaVersion") != 1
        or len(source.get("methods", ())) != 2
        or source["methods"][1][1] != contract["wrapperName"]
        or source.get("anonymousReadOrder") != {key: kinds}
        or len(source.get("nestedContexts", ())) != 5
        or [row.get("typeName") for row in source["nestedContexts"]]
        != [
            "Beyond.Gameplay.Core.AbilityAction+AbilityActionData+Priority",
            "Beyond.Gameplay.Core.DispelLevel",
            "Beyond.Gameplay.Core.TargetSettings",
            "Beyond.Gameplay.Core.TargetSettings",
            "Beyond.Gameplay.Core.GameplayTagQuery",
        ]
    ):
        raise ValueError(f"{LABEL}.native:buff-source-shape")

    image = open_native_image(gate.gameassembly, gate.metadata)
    audited = buff_action_read_order(
        image.pe, image.metadata, image.registration, image.instantiations,
        image.modules, image.owners, source=str(gate.gameassembly),
        contract_path=source_path,
    )
    if audited.get("anonymousReadOrder") != {key: kinds}:
        raise ValueError(f"{LABEL}.native:audited-read-order")
    routes, resolver, audit = resolve_routes(
        gameassembly=gate.gameassembly, metadata=gate.metadata,
    )
    selected = routes.get(contract["unionTag"], {})
    definition = selected.get("wrapperTypeDefinition")
    plan = resolver.plans.get(definition) if resolver is not None else None
    if (
        audit.get("status") != "validated"
        or audit.get("routeAudit") != "validated"
        or selected.get("status") != "determined"
        or selected.get("wrapperName") != contract["wrapperName"]
        or selected.get("evidenceTier") != "structuralOnly"
        or not isinstance(plan, tuple)
        or len(plan) != contract["serializedMemberCount"]
        or [member.name for member in plan] != contract["fieldNames"]
        or resolver.wrappers[definition].wrapped_type != contract["actualTypeName"]
    ):
        raise ValueError(f"{LABEL}.native:generated-wrapper-plan")
    for member, kind in zip(plan, kinds):
        if kind in ("byte", "scalar32"):
            if member.kind != "fixed" or member.width != (1 if kind == "byte" else 4):
                raise ValueError(f"{LABEL}.native:fixed-member={member.name}")
        else:
            expected_type = (
                "Beyond.Gameplay.Core.TargetSettings" if kind == "target-profile"
                else "Beyond.Gameplay.Core.GameplayTagQuery"
            )
            if (member.kind != "object" or member.ref not in resolver.wrappers
                    or resolver.wrappers[member.ref].wrapped_type != expected_type):
                raise ValueError(f"{LABEL}.native:nested-member={member.name}")
    return {
        "status": "validated", "unionTag": contract["unionTag"],
        "nativeInputs": expected, "sourceReadCount": len(kinds),
        "nestedContextCount": len(source["nestedContexts"]),
        "codeWindowCount": len(source["codeWindows"]),
        "evidenceBoundary": contract["evidenceBoundary"],
    }


def _consume_action(reader: Reader, width: int) -> dict[str, Any]:
    contract = _contract()
    tag = contract["unionTag"]
    if width != 1 or reader.data[reader.pos:reader.pos + width] != bytes((tag,)):
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    start = reader.pos
    reader.take(width, "union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-wrapper")
        return {"status": "exact-null-wrapper", "start": start, "end": reader.pos}
    reader.header(contract["serializedMemberCount"])
    fields = []
    for name, kind in zip(contract["fieldNames"], contract["readKinds"]):
        field_start = reader.pos
        if kind == "byte":
            reader.take(1, name)
        elif kind == "scalar32":
            reader.take(4, name)
        elif kind == "target-profile":
            reader.target_profile()
        elif kind == "query-profile":
            reader.query_profile()
        else:
            raise AssertionError(kind)
        fields.append({"name": name, "kind": kind,
                       "start": field_start, "end": reader.pos})
    return {"status": "exact-stored-action-span", "tag": tag,
            "start": start, "end": reader.pos, "fields": fields,
            "evidenceBoundary": "stored framing only"}


def decode_action(data: bytes, offset: int, *, validation: Mapping[str, Any]) -> dict[str, Any]:
    if validation.get("status") != "validated" or validation.get("unionTag") != _contract()["unionTag"]:
        raise ValueError(f"{LABEL}.native:not-validated")
    if type(offset) is not int or offset < 0 or offset + 2 > len(data):
        raise ValueError(f"{LABEL}.source:offset-outside-source")
    reader = Reader(data, f"{LABEL}.source")
    reader.pos = offset
    return _consume_action(reader, 1)


def decode_shared_action(reader: Reader, depth: int, tag: int, width: int) -> None:
    del depth
    if tag != _contract()["unionTag"]:
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    _consume_action(reader, width)
