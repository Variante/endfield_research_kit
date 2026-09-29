"""Authenticate the current LevelEnemyData enum and nullable-float read.

The selected wrapper reads enemyDefaultActionType as a signed Int32 and
extraDelayToRecycleTime as a native Nullable<float> value. The source receipt
shows an authored enum value without a native name and the flag-first eight
byte nullable layout. Runtime enemy behavior is outside this boundary.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path, PurePosixPath
from typing import Any

from scripts.common import check_installed_native_inputs, sha256_file
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp import protocol
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.game_data.memorypack.wrapper_members import derive_from_image


SCHEMA = "endfield.level-enemy-default-action-native.v1"
LABEL = "levelEnemyDefaultActionNative"
DEFAULT_CONTRACT = CONTRACTS_DIR / "level_enemy_default_action_native.json"


def _contract(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_bytes())
    owner = value.get("owner") or {}
    enum = value.get("enum") or {}
    source = value.get("sourceReceipt") or {}
    fields = owner.get("fields") or []
    if (
        value.get("schema") != SCHEMA
        or value.get("status") != "exact-current-build"
        or value.get("evidenceBoundary") != "direct"
        or set(value.get("nativeInputs") or {})
        != {"GameAssembly.dll", "global-metadata.dat", "UnityPlayer.dll"}
        or owner.get("wrappedType") != "Beyond.Gameplay.LevelEnemyData"
        or owner.get("wrapperType")
        != "Beyond.MemoryPack.Beyond_Gameplay_LevelEnemyDataForMemoryPack"
        or owner.get("serializedMemberCount") != 30
        or [row.get("memberIndex") for row in fields] != [18, 19, 21]
        or [row.get("name") for row in fields]
        != ["enemyDefaultActionType", "enemyGroupId", "extraDelayToRecycleTime"]
        or [row.get("declaredType") for row in fields]
        != ["Beyond.Gameplay.AI.EnemyDefaultActionType", "int", "System.Nullable`1<float>"]
        or len(owner.get("codeWindows") or []) != 3
        or enum.get("typeName") != "Beyond.Gameplay.AI.EnemyDefaultActionType"
        or enum.get("underlyingType") != "int"
        or [(row.get("id"), row.get("name")) for row in enum.get("members") or []]
        != [(0, "Patrol")]
        or not isinstance(source.get("path"), str)
        or not source["path"].startswith("LevelScriptData/")
        or PurePosixPath(source["path"]).is_absolute()
        or ".." in PurePosixPath(source["path"]).parts
        or source.get("expectedStatus") != "named_exact"
        or source.get("enumValue", {}).get("name") is not None
        or source.get("nullableFloat", {}).get("hasValueOffset") != 0
        or source.get("nullableFloat", {}).get("floatOffset") != 4
    ):
        raise ValueError(f"{LABEL}.contract:shape")
    if (
        not isinstance(source.get("sha256"), str)
        or len(source["sha256"]) != 64
        or not isinstance(source.get("length"), int)
        or any(not isinstance(row.get("readCallRva"), int) for row in fields)
    ):
        raise ValueError(f"{LABEL}.contract:receipts")
    return value


def _call_target(image: Any, site: int) -> int:
    raw = image.pe.bytes_at_va(image.pe.image_base + site, 5)
    if raw[0] != 0xE8:
        raise ValueError(f"{LABEL}.native:callsite={site:#x}")
    return site + 5 + struct.unpack_from("<i", raw, 1)[0]


def _validate_native(image: Any, contract: dict[str, Any]) -> None:
    owner = contract["owner"]
    enum = contract["enum"]
    base = image.pe.image_base
    image.validate_method_row(owner["readerMethod"], label=LABEL)
    if image.type_name(owner["wrapperDefinition"]) != owner["wrapperType"]:
        raise ValueError(f"{LABEL}.native:wrapper-type")
    wrapper = derive_from_image(image)[owner["wrapperDefinition"]]
    if (
        wrapper.wrapped_type != owner["wrappedType"]
        or len(wrapper.members) != owner["serializedMemberCount"]
    ):
        raise ValueError(f"{LABEL}.native:wrapper-shape")
    definition = enum["typeDefinition"]
    if image.type_name(definition) != enum["typeName"]:
        raise ValueError(f"{LABEL}.native:enum-type")
    value_fields = [
        field for field in image.metadata.fields_for(image.metadata.types[definition])
        if image.metadata.string(field.name_index) == "value__"
    ]
    if len(value_fields) != 1:
        raise ValueError(f"{LABEL}.native:enum-value-field")
    pointer = image.pe.u64_at_va(
        int(image.registration["types"], 16) + value_fields[0].type_index * 8
    )
    if protocol.runtime_type_name(image.pe, image.metadata, pointer) != enum["underlyingType"]:
        raise ValueError(f"{LABEL}.native:enum-backing")
    actual_members = protocol.native_enum_members(
        image.metadata, BodyIndex(image).enum_defaults, image.pe, image.registration,
        enum["typeName"],
    )
    if actual_members != enum["members"]:
        raise ValueError(f"{LABEL}.native:enum-members")
    image.check_windows(owner["codeWindows"], label=LABEL)
    sites = owner["fields"]
    previous = owner["codeWindows"][0]["startRva"]
    for row in sites:
        member = wrapper.members[row["memberIndex"]]
        method = image.metadata.methods[row["setterMethodIndex"]]
        if (
            member.name != row["name"]
            or member.declared_type != row["declaredType"]
            or member.method_index != row["setterMethodIndex"]
            or image.metadata.string(method.name_index) != f"set___{row['name']}__"
            or image.method_pointer_va(method) != base + row["setterTargetRva"]
            or not previous < row["readCallRva"] < row["setterCallRva"]
            < owner["codeWindows"][0]["endRva"]
            or _call_target(image, row["readCallRva"]) != row["readTargetRva"]
            or _call_target(image, row["setterCallRva"]) != row["setterTargetRva"]
        ):
            raise ValueError(f"{LABEL}.native:read-setter={row['name']}")
        previous = row["setterCallRva"]
    if (
        sites[0]["readTargetRva"] != sites[1]["readTargetRva"]
        or sites[0]["readTargetRva"] != owner["codeWindows"][1]["startRva"]
        or sites[2]["readTargetRva"] != owner["codeWindows"][2]["startRva"]
    ):
        raise ValueError(f"{LABEL}.native:read-helper-window")
    # The Int32 helper loads four bytes and advances the reader by four.
    helper = sites[0]["readTargetRva"]
    instructions = BodyIndex(image)._decode(base + helper, owner["codeWindows"][1]["endRva"] - helper)
    if not any(row["text"] == "add [rbx+0x50], 0x4" for row in instructions):
        raise ValueError(f"{LABEL}.native:int32-reader-width")


def _validate_source(contract: dict[str, Any], source_path: Path) -> None:
    receipt = contract["sourceReceipt"]
    relative = PurePosixPath(receipt["path"])
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"{LABEL}.source:unsafe-path")
    data = source_path.read_bytes()
    digest = hashlib.sha256(data).hexdigest().upper()
    if len(data) != receipt["length"] or digest != receipt["sha256"].upper():
        raise ValueError(
            f"{LABEL}.source:source-sha256={source_path}:"
            f"expected={receipt['length']}/{receipt['sha256']},actual={len(data)}/{digest}"
        )
    for key in ("enumValue", "nullableFloat"):
        row = receipt[key]
        expected = bytes.fromhex(row["rawHex"])
        actual = data[row["offset"]:row["offset"] + len(expected)]
        if actual != expected:
            raise ValueError(f"{LABEL}.source:{key}-bytes={source_path}@{row['offset']}")
    nullable = receipt["nullableFloat"]
    raw = bytes.fromhex(nullable["rawHex"])
    if (
        len(raw) != 8 or raw[0] != 1 or raw[1:4] != b"\0\0\0"
        or struct.unpack_from("<f", raw, 4)[0] != nullable["value"]
    ):
        raise ValueError(f"{LABEL}.source:nullable-layout")
    from scripts.game_data.codecs.levelscript.current_action_sequence import (
        frame_levelscript_current_action_sequence_leader_enter,
    )
    result = frame_levelscript_current_action_sequence_leader_enter(data)
    if result.get("schemaStatus") != receipt["expectedStatus"] or result.get("bytesConsumed") != len(data):
        raise ValueError(f"{LABEL}.source:cursor={source_path}")


def validate_level_enemy_default_action_native_contract(
    *, contract_path: Path = DEFAULT_CONTRACT, game_root: Path | None = None,
    source_path: Path | None = None,
) -> dict[str, Any]:
    """Fail closed on selected native inputs, owner reads, enum, and optional source."""
    try:
        contract = _contract(Path(contract_path))
        expected = contract["nativeInputs"]
        root = Path(game_root) if game_root is not None else None
        gate = check_installed_native_inputs(
            expected["GameAssembly.dll"], expected["global-metadata.dat"],
            gameassembly=root.parent / "GameAssembly.dll" if root else None,
            metadata=root / "il2cpp_data/Metadata/global-metadata.dat" if root else None,
        )
        if gate.status != "validated":
            return {"status": gate.status, "failedGate": "installed_native_inputs", "detail": gate.detail}
        unity = gate.gameassembly.parent / "UnityPlayer.dll"
        if not unity.is_file() or sha256_file(unity).upper() != expected["UnityPlayer.dll"].upper():
            return {"status": "mismatched", "failedGate": "UnityPlayer.dll",
                    "detail": "selected UnityPlayer.dll missing or different"}
        _validate_native(open_native_image(gate.gameassembly, gate.metadata), contract)
        if source_path is not None:
            _validate_source(contract, Path(source_path))
        return {"status": "validated", "evidenceBoundary": "direct",
                "sourceReceiptCount": int(source_path is not None)}
    except (OSError, ValueError, KeyError, TypeError, IndexError) as error:
        return {"status": "validation_failed", "failedGate": str(error).split(":", 1)[0],
                "detail": str(error)[:400]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-root", type=Path)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--source", type=Path)
    args = parser.parse_args(argv)
    result = validate_level_enemy_default_action_native_contract(
        contract_path=args.contract, game_root=args.game_root, source_path=args.source,
    )
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "validated" else 2


if __name__ == "__main__":
    raise SystemExit(main())
