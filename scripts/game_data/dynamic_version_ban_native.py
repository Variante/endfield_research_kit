"""Validate the selected DynamicStreaming version-ban consumer path."""

from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs, sha256_file
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.dynamic_version_native import validate_native_layout as validate_version_layout
from scripts.game_data.il2cpp.call_graph import CallGraph
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets, runtime_type_name
from scripts.repo_paths import REPO_ROOT


CONTRACT = CONTRACTS_DIR / "dynamic_version_ban_native.json"
SCHEMA = "endfield.dynamic-version-ban-native-contract.v1"
DEFAULT_JSON = REPO_ROOT / "reports/animestudio/dynamic_version_ban_native_latest.json"


class DynamicVersionBanNativeError(ValueError):
    """The selected build or one of its checked ban-set instructions differs."""


def _target_rva(raw: bytes, rva: int, kind: str) -> int:
    if kind == "call" and len(raw) == 5 and raw[0] == 0xE8:
        return rva + len(raw) + struct.unpack_from("<i", raw, 1)[0]
    if kind == "jle" and len(raw) == 2 and raw[0] == 0x7E:
        return rva + len(raw) + struct.unpack_from("<b", raw, 1)[0]
    if kind == "jne" and len(raw) == 6 and raw[:2] == b"\x0f\x85":
        return rva + len(raw) + struct.unpack_from("<i", raw, 2)[0]
    if kind == "jge" and len(raw) == 6 and raw[:2] == b"\x0f\x8d":
        return rva + len(raw) + struct.unpack_from("<i", raw, 2)[0]
    raise DynamicVersionBanNativeError(f"selected {kind} encoding differs at 0x{rva:X}")


def validate_native_consumer(gameassembly: Path, metadata: Path) -> dict[str, Any]:
    """Authenticate fields, full body windows, calls, and branch destinations."""
    contract, digest = read_reviewed_contract(CONTRACT, schema=SCHEMA,
                                             label="dynamic_version_ban", status="validated")
    inputs = contract["nativeInputs"]
    gate = check_installed_native_inputs(
        inputs["gameAssemblySha256"], inputs["metadataSha256"],
        gameassembly=Path(gameassembly), metadata=Path(metadata),
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise DynamicVersionBanNativeError(f"installed_native_inputs:{gate.status}:{gate.detail}")
    unity = Path(gameassembly).parent / "UnityPlayer.dll"
    if not unity.is_file() or sha256_file(unity).upper() != inputs["unityPlayerSha256"]:
        raise DynamicVersionBanNativeError("installed_native_inputs:mismatched:UnityPlayer.dll missing or hash differs")
    version_layout, version_provenance = validate_version_layout(gameassembly, metadata)
    if (version_layout["entryWidth"] != 16 or version_layout["entryIdOffset"] != 0
            or version_layout["entryVersionOffset"] != 8):
        raise DynamicVersionBanNativeError("selected version-entry layout differs")
    image = open_native_image(gameassembly, metadata)
    methods = contract["methods"]
    if {row["method"] for row in methods} != {
        "LoadFromBasePath", "_ResolveActiveVersion", "IsEntityVersionBanned",
        "IsBanned", "Reset", ".ctor",
    } or len(methods) != 6:
        raise DynamicVersionBanNativeError("selected ban method set differs")
    for row in methods:
        index = int(row["index"])
        image.validate_method_row([index, row["type"], row["method"], int(row["rva"])],
                                  label="dynamic_version_ban")
        method = image.metadata.methods[index]
        parameters = [image.metadata.metadata_type_name(item.type_index)
                      for item in image.metadata.parameters_for(method)]
        returned = image.metadata.metadata_type_name(method.return_type)
        if parameters != row["parameters"] or returned != row["returnType"]:
            raise DynamicVersionBanNativeError(f"selected ban signature differs: {row['method']}")
    type_indices = {image.type_name(i): i for i in range(len(image.metadata.types))}
    fields: dict[str, int] = {}
    expected_fields = {"m_banned", "m_activeMajor", "m_activeMinor", "m_activePhase",
                       "m_needCheck", "m_versionBanSet"}
    if {row["name"] for row in contract["fields"]} != expected_fields or len(contract["fields"]) != 6:
        raise DynamicVersionBanNativeError("selected ban field set differs")
    for row in contract["fields"]:
        type_index = type_indices.get(row["type"])
        if type_index is None:
            raise DynamicVersionBanNativeError(f"selected ban type missing: {row['type']}")
        offsets = runtime_type_field_offsets(image.metadata, image.pe, image.registration, type_index)
        name = row["name"]
        if offsets.get(name) != int(row["offset"]):
            raise DynamicVersionBanNativeError(f"selected ban field offset differs: {name}")
        field = next((field for field in image.metadata.fields_for(image.metadata.types[type_index])
                      if image.metadata.string(field.name_index) == name), None)
        if field is None:
            raise DynamicVersionBanNativeError(f"selected ban field missing: {name}")
        table_va = int(image.registration["types"], 16)
        type_va = image.pe.u64_at_va(table_va + field.type_index * 8)
        if runtime_type_name(image.pe, image.metadata, type_va) != row["fieldType"]:
            raise DynamicVersionBanNativeError(f"selected ban field type differs: {name}")
        fields[name] = int(row["offset"])
    windows = contract["windows"]
    if {row["name"] for row in windows} != {row["method"] for row in methods} | {"IsBannedCold"}:
        raise DynamicVersionBanNativeError("selected ban body window set differs")
    if len(windows) != 7:
        raise DynamicVersionBanNativeError("duplicate selected ban body window")
    image.check_windows(windows, label="dynamic_version_ban")

    def checked_bytes(rva: int, length: int) -> bytes:
        if not any(int(w["startRva"]) <= rva and rva + length <= int(w["endRva"])
                   for w in windows):
            raise DynamicVersionBanNativeError(f"ban instruction outside checked window: 0x{rva:X}")
        return image.pe.bytes_at_va(image.pe.image_base + rva, length)

    checks = {row["role"]: row for row in contract["instructionChecks"]}
    expected_checks = {
        "loadInitialNeedCheck", "loadActivePhaseFullGuard", "loadMajorCompare",
        "loadMinorCompare", "entryVersionCompare", "candidateSkip", "loadSet",
        "candidateCount", "needCheckCount", "needCheckFromCandidateCount",
        "needCheckSet", "sceneBanSet",
        "sceneIdToCall", "queryNeedCheck", "querySet", "queryIdToContains",
        "resetNeedCheck", "constructorSet",
    }
    if set(checks) != expected_checks or len(contract["instructionChecks"]) != len(expected_checks):
        raise DynamicVersionBanNativeError("selected ban instruction roles differ")
    for role, row in checks.items():
        raw = bytes.fromhex(row["hex"])
        if not raw or checked_bytes(int(row["rva"]), len(raw)) != raw:
            raise DynamicVersionBanNativeError(f"selected ban instruction differs: {role}")
    offset_roles = {
        "loadInitialNeedCheck": ("m_needCheck", -1),
        "loadActivePhaseFullGuard": ("m_activePhase", -2),
        "loadMajorCompare": ("m_activeMajor", -1),
        "loadMinorCompare": ("m_activeMinor", -1),
        "entryVersionCompare": ("m_activePhase", -1),
        "loadSet": ("m_banned", -1),
        "needCheckSet": ("m_needCheck", -1),
        "queryNeedCheck": ("m_needCheck", -1),
        "querySet": ("m_banned", -1),
        "resetNeedCheck": ("m_needCheck", -2),
        "constructorSet": ("m_banned", -1),
    }
    for role, (field, position) in offset_roles.items():
        if bytes.fromhex(checks[role]["hex"])[position] != fields[field]:
            raise DynamicVersionBanNativeError(f"selected ban instruction field differs: {role}")
    if struct.unpack_from("<I", bytes.fromhex(checks["sceneBanSet"]["hex"]), 3)[0] != fields["m_versionBanSet"]:
        raise DynamicVersionBanNativeError("selected scene ban-set field differs")

    graph = CallGraph(image)
    names_by_pointer = graph.names_by_pointer
    expected_calls = {"loadResolve", "entryVersion", "entryId", "addId", "sceneToBanSet",
                      "containsId", "resetClear", "constructorHashSet", "loadPatchGuard",
                      "scenePatchGuard", "queryPatchGuard"}
    if {row["role"] for row in contract["calls"]} != expected_calls or len(contract["calls"]) != len(expected_calls):
        raise DynamicVersionBanNativeError("selected ban call roles differ")
    for row in contract["calls"]:
        rva, target = int(row["rva"]), int(row["targetRva"])
        actual = _target_rva(checked_bytes(rva, 5), rva, "call")
        if actual != target or row["target"] not in names_by_pointer.get(image.pe.image_base + target, ()):
            raise DynamicVersionBanNativeError(f"selected ban call differs: {row['role']}")
    expected_branches = {
        "loadPatchOverride", "activeFullSkip", "majorMismatch", "minorMismatch",
        "candidateSkipWhenVersionNotGreater", "scenePatchOverride",
        "queryPatchOverride", "queryNeedCheckTrue", "resetPatchOverride",
    }
    if {row["role"] for row in contract["branches"]} != expected_branches or len(contract["branches"]) != len(expected_branches):
        raise DynamicVersionBanNativeError("selected ban branch roles differ")
    for row in contract["branches"]:
        rva, kind = int(row["rva"]), row["kind"]
        length = 2 if kind == "jle" else 6
        if _target_rva(checked_bytes(rva, length), rva, kind) != int(row["targetRva"]):
            raise DynamicVersionBanNativeError(f"selected ban branch differs: {row['role']}")
    return {
        "schema": "endfield.dynamic-version-ban-native-audit.v1",
        "status": "validated",
        "contractSha256": digest,
        "versionContractSha256": version_provenance["contractSha256"],
        "nativeInputs": inputs,
        "methodsChecked": len(methods),
        "fieldsChecked": len(fields),
        "codeWindowsChecked": len(windows),
        "callsChecked": len(contract["calls"]),
        "branchesChecked": len(contract["branches"]),
        "evidenceBoundary": contract["evidenceBoundary"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gameassembly", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    args = parser.parse_args(argv)
    try:
        report = validate_native_consumer(args.gameassembly, args.metadata)
    except (OSError, ValueError, KeyError, IndexError, RuntimeError) as error:
        print(f"dynamic-version-ban-native: {error}", file=sys.stderr)
        return 1
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"DynamicStreaming version-ban native contract validated: {args.output_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
