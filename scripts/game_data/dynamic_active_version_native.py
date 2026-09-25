"""Validate the selected source of DynamicStreaming's active version fields."""

from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.call_graph import CallGraph, loaded_literals
from scripts.game_data.il2cpp.context import unresolved_usage_index
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets, runtime_type_name
from scripts.repo_paths import REPO_ROOT


CONTRACT = CONTRACTS_DIR / "dynamic_active_version_native.json"
SCHEMA = "endfield.dynamic-active-version-native-contract.v10"
DEFAULT_JSON = REPO_ROOT / "reports/animestudio/dynamic_active_version_native_latest.json"


class DynamicActiveVersionNativeError(ValueError):
    """The selected active-version source chain differs from its reviewed body."""


def _number(value: Any) -> int:
    return int(str(value), 0)


def _target(raw: bytes, rva: int, kind: str) -> int:
    if kind in {"call", "jmp"} and len(raw) == 5 and raw[0] == (0xE8 if kind == "call" else 0xE9):
        return rva + 5 + struct.unpack_from("<i", raw, 1)[0]
    conditional_opcodes = {"je": b"\x0f\x84", "jne": b"\x0f\x85", "jle": b"\x0f\x8e"}
    if kind in conditional_opcodes and len(raw) == 6 and raw[:2] == conditional_opcodes[kind]:
        return rva + 6 + struct.unpack_from("<i", raw, 2)[0]
    short_opcodes = {"je8": 0x74, "jne8": 0x75}
    if kind in short_opcodes and len(raw) == 2 and raw[0] == short_opcodes[kind]:
        return rva + 2 + struct.unpack_from("<b", raw, 1)[0]
    raise DynamicActiveVersionNativeError(f"selected {kind} encoding differs at 0x{rva:X}")


def _register_move(raw: bytes) -> tuple[int, int]:
    """Return (destination, source) for one x64 register-to-register mov."""
    if len(raw) == 3 and raw[:2] in (b"\x48\x8b", b"\x4c\x8b") and raw[2] & 0xC0 == 0xC0:
        rex = raw[0]
        return ((raw[2] >> 3) & 7) + (8 if rex & 4 else 0), (raw[2] & 7) + (8 if rex & 1 else 0)
    if len(raw) == 2 and raw[0] == 0x8B and raw[1] & 0xC0 == 0xC0:
        return (raw[1] >> 3) & 7, raw[1] & 7
    raise DynamicActiveVersionNativeError("selected source register-move encoding differs")


def validate_active_version_source(
    gameassembly: Path,
    metadata: Path,
    *,
    contract_path: Path = CONTRACT,
) -> dict[str, Any]:
    """Authenticate the login handoff, message setter, parser and guarded stores."""
    contract, digest = read_reviewed_contract(
        contract_path, schema=SCHEMA, label="dynamic_active_version", status="validated"
    )
    inputs = contract["nativeInputs"]
    gate = check_installed_native_inputs(
        inputs["gameAssemblySha256"], inputs["metadataSha256"],
        gameassembly=Path(gameassembly), metadata=Path(metadata),
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise DynamicActiveVersionNativeError(
            f"installed_native_inputs:{gate.status}:{gate.detail}"
        )
    image = open_native_image(gameassembly, metadata)
    methods = contract["methods"]
    method_roles = {
        "_ResolveActiveVersion", "get_player", "get_branchVersion", "_ParseVersion",
        "set_branchVersion", "SyncBranchVersion", "MoveNext",
        "_NetConnectAndGSLogin", "netLoginMoveNext", "GetResponse", "SetSucceed",
        "_SessionLoginThreadTask", "_ReadMessageInSessionThread", "get_msgId",
        "GetNetMessageFromDataBytes", "FastRegisterMessage", "RegisterSCMessage",
    }
    if len(methods) != len(method_roles) or {
        row.get("role", row["name"]) for row in methods
    } != method_roles:
        raise DynamicActiveVersionNativeError("selected source method set differs")
    type_table = int(image.registration["types"], 16)
    for row in methods:
        index = int(row["index"])
        image.validate_method_row(
            [index, row["type"], row["name"], _number(row["rva"])],
            label="dynamic_active_version",
        )
        method = image.metadata.methods[index]
        parameters = [item.type_index for item in image.metadata.parameters_for(method)]
        if parameters != row["parameterTypeIndices"]:
            raise DynamicActiveVersionNativeError(
                f"selected source parameter types differ: {row['name']}"
            )
        return_va = image.pe.u64_at_va(type_table + method.return_type * 8)
        if runtime_type_name(image.pe, image.metadata, return_va) != row["returnType"]:
            raise DynamicActiveVersionNativeError(
                f"selected source return type differs: {row['name']}"
            )

    fields = contract["fields"]
    field_names = {
        "playerInfoSystem", "m_branchVersion", "f14_",
        "<loginRespRef>5__5", "value", "loginRespRef", "<loginHandler>5__5", "m_resp",
        "headMsg", "msgBody", "msgid_", "s_sc_id2MessageType",
        "m_activeMajor", "m_activeMinor", "m_activePhase",
    }
    if len(fields) != len(field_names) or {row["name"] for row in fields} != field_names:
        raise DynamicActiveVersionNativeError("selected source field set differs")
    type_indexes: dict[str, list[int]] = {}
    for index in range(len(image.metadata.types)):
        type_indexes.setdefault(image.type_name(index), []).append(index)
    offsets: dict[str, int] = {}
    for row in fields:
        matches = type_indexes.get(row["type"], [])
        if len(matches) != 1:
            raise DynamicActiveVersionNativeError(
                f"selected source declaring type differs: {row['type']}"
            )
        type_index = matches[0]
        declared = image.metadata.types[type_index]
        offset = _number(row["offset"])
        field_offsets = runtime_type_field_offsets(
            image.metadata, image.pe, image.registration, type_index
        )
        if field_offsets.get(row["name"]) != offset:
            raise DynamicActiveVersionNativeError(
                f"selected source field offset differs: {row['name']}"
            )
        named = [
            item for item in image.metadata.fields_for(declared)
            if image.metadata.string(item.name_index) == row["name"]
        ]
        if len(named) != 1:
            raise DynamicActiveVersionNativeError(
                f"selected source field identity differs: {row['name']}"
            )
        field_va = image.pe.u64_at_va(type_table + named[0].type_index * 8)
        if runtime_type_name(image.pe, image.metadata, field_va) != row["fieldType"]:
            raise DynamicActiveVersionNativeError(
                f"selected source field type differs: {row['name']}"
            )
        offsets[row["name"]] = offset
    if offsets["m_activeMinor"] != offsets["m_activeMajor"] + 4:
        raise DynamicActiveVersionNativeError("selected active major/minor field spacing differs")
    if offsets["msgBody"] != offsets["headMsg"] + 8:
        raise DynamicActiveVersionNativeError("selected response head/body field spacing differs")

    windows = [
        {**row, "startRva": _number(row["startRva"]), "endRva": _number(row["endRva"])}
        for row in contract["windows"]
    ]
    window_names = method_roles | {"ResolveColdAllZero", "ParseColdZeroOutputs"}
    if len(windows) != len(window_names) or {row["name"] for row in windows} != window_names:
        raise DynamicActiveVersionNativeError("selected source code-window set differs")
    for row in windows:
        if row["endRva"] <= row["startRva"]:
            raise DynamicActiveVersionNativeError(
                f"selected source code-window bounds differ: {row['name']}"
            )
    for method in methods:
        role = method.get("role", method["name"])
        window = next(row for row in windows if row["name"] == role)
        if window["startRva"] != _number(method["rva"]):
            raise DynamicActiveVersionNativeError(
                f"selected source method/window start differs: {role}"
            )
    image.check_windows(windows, label="dynamic_active_version")

    def checked_bytes(rva: int, length: int) -> bytes:
        if not any(
            row["startRva"] <= rva and rva + length <= row["endRva"]
            for row in windows
        ):
            raise DynamicActiveVersionNativeError(
                f"source instruction outside checked window: 0x{rva:X}"
            )
        return image.pe.bytes_at_va(image.pe.image_base + rva, length)

    checks = {row["role"]: row for row in contract["instructionChecks"]}
    required_checks = {
        "parserZero", "parserInitMajor", "parserInitMinor", "parserInitPhase",
        "majorGroupCount", "majorGroupIndex", "minorGroupIndex",
        "phaseGroupCount", "phaseCheckGroupIndex", "phaseCaptureNonempty",
        "phaseParseGroupIndex", "parserResetMajor", "parserResetMinor",
        "parserResetPhase",
        "defaultMajorMinor", "defaultPhase", "playerInfoField",
        "argPhase", "argMinor", "argString", "argMajor",
        "loadMajor", "loadMinor", "loadPhase",
        "storeMajor", "storeMinor", "storePhase",
        "branchVersionField", "coldMinorTest", "coldPhaseTest",
        "syncMessageBinding", "syncReceiverBinding", "syncMessageField",
        "syncSetterReceiver", "setterValueBinding", "setterReceiverBinding",
        "setterFieldWrite", "loginCoroutineReceiver", "loginResponseRefField",
        "objectRefValueField", "loginMessageArgument",
        "loginResponseRefStore", "loginResponseRefArg",
        "netLoginInputRef", "netLoginRefStore", "netLoginHandlerStore",
        "netLoginHandlerRead", "netLoginRefRead", "netLoginRefValueStore",
        "getResponseField", "setSucceedResponseBinding", "setSucceedResponseStore",
        "sessionResponseStack", "sessionResponseArgument",
        "sessionReadOutputArgument", "sessionReadResultTest", "sessionMessageIdReceiver",
        "sessionLoginMessageId", "sessionBodyTypeLoad", "sessionBodyCastCompare",
        "sessionEncrypResponseArg", "readOutputBinding", "readDecoderOutputArg",
        "decoderHeadTypeLoad", "decoderMessageIdField", "decoderMappedTypeRead",
        "decoderMessageMapField",
        "decoderMessageBinding", "decoderMergeReceiver", "decoderHeadArgument",
        "decoderResponseLocal", "decoderBodyStore", "decoderOutputPointer",
        "decoderOutputFirstCopy", "decoderOutputSecondCopy",
        "responseGetterHeadField", "responseGetterHeadTypeLoad",
        "responseGetterMessageIdField",
        "fastRegisterMessageTypeLoad", "fastRegisterTypeArgument",
        "fastRegisterMessageId", "registerTypeBinding", "registerIdBinding",
        "registerMessageMapField", "registerTypeValue", "registerIdKey",
    }
    if len(contract["instructionChecks"]) != len(required_checks) or set(checks) != required_checks:
        raise DynamicActiveVersionNativeError("selected source instruction roles differ")
    raw_checks: dict[str, bytes] = {}
    for role, row in checks.items():
        raw = bytes.fromhex(row["hex"])
        if not raw or checked_bytes(_number(row["rva"]), len(raw)) != raw:
            raise DynamicActiveVersionNativeError(
                f"selected source instruction differs: {role}"
            )
        raw_checks[role] = raw
    group_indices = contract["parserGroupIndices"]
    group_thresholds = contract["parserGroupCountThresholds"]
    if set(group_indices) != {"major", "minor", "phase"} or set(group_thresholds) != {"major", "phase"}:
        raise DynamicActiveVersionNativeError("selected parser group declaration differs")
    if (
        raw_checks["parserInitMajor"] != raw_checks["parserResetMajor"]
        or raw_checks["parserInitMinor"] != raw_checks["parserResetMinor"]
        or raw_checks["parserInitPhase"] != raw_checks["parserResetPhase"]
        or raw_checks["majorGroupIndex"][1:] != int(group_indices["major"]).to_bytes(4, "little")
        or raw_checks["minorGroupIndex"][1:] != int(group_indices["minor"]).to_bytes(4, "little")
        or raw_checks["phaseCheckGroupIndex"][1:] != int(group_indices["phase"]).to_bytes(4, "little")
        or raw_checks["phaseParseGroupIndex"][1:] != int(group_indices["phase"]).to_bytes(4, "little")
        or raw_checks["majorGroupCount"][-1] != int(group_thresholds["major"])
        or raw_checks["phaseGroupCount"][-1] != int(group_thresholds["phase"])
        or raw_checks["defaultMajorMinor"][-1] != offsets["m_activeMajor"]
        or raw_checks["defaultPhase"][2] != offsets["m_activePhase"]
        or struct.unpack_from("<I", raw_checks["defaultPhase"], 3)[0]
        != int(contract["defaultPhaseValue"])
        or struct.unpack_from("<I", raw_checks["playerInfoField"], 3)[0]
        != offsets["playerInfoSystem"]
        or struct.unpack_from("<I", raw_checks["branchVersionField"], 3)[0]
        != offsets["m_branchVersion"]
        or raw_checks["syncMessageField"][-1] != offsets["f14_"]
        or struct.unpack_from("<I", raw_checks["setterFieldWrite"], 3)[0]
        != offsets["m_branchVersion"]
        or raw_checks["loginResponseRefField"][-1] != offsets["<loginRespRef>5__5"]
        or raw_checks["loginResponseRefStore"][-1] != offsets["<loginRespRef>5__5"]
        or raw_checks["loginResponseRefArg"][-1] != offsets["<loginRespRef>5__5"]
        or raw_checks["objectRefValueField"][-1] != offsets["value"]
        or raw_checks["netLoginRefStore"][-1] != offsets["loginRespRef"]
        or raw_checks["netLoginRefRead"][-1] != offsets["loginRespRef"]
        or raw_checks["netLoginHandlerStore"][-1] != offsets["<loginHandler>5__5"]
        or raw_checks["netLoginHandlerRead"][-1] != offsets["<loginHandler>5__5"]
        or raw_checks["netLoginRefValueStore"][-1] != offsets["value"]
        or raw_checks["getResponseField"][-1] != offsets["m_resp"]
        or raw_checks["setSucceedResponseStore"][-1] != offsets["m_resp"]
        or raw_checks["storeMajor"][-1] != offsets["m_activeMajor"]
        or raw_checks["storeMinor"][-1] != offsets["m_activeMinor"]
        or raw_checks["storePhase"][-1] != offsets["m_activePhase"]
        or raw_checks["sessionReadOutputArgument"][-1]
        != raw_checks["sessionMessageIdReceiver"][-1]
        or raw_checks["sessionResponseStack"][-1]
        - raw_checks["sessionReadOutputArgument"][-1]
        != offsets["msgBody"] - 16
        or raw_checks["decoderMessageIdField"][-1] != offsets["msgid_"]
        or raw_checks["responseGetterMessageIdField"][-1] != offsets["msgid_"]
        or struct.unpack_from("<I", raw_checks["decoderBodyStore"], 4)[0]
        - struct.unpack_from("<I", raw_checks["decoderResponseLocal"], 4)[0]
        != offsets["msgBody"] - 16
        or raw_checks["sessionLoginMessageId"][-1] != 1
        or raw_checks["decoderMessageMapField"][-1] != offsets["s_sc_id2MessageType"]
        or raw_checks["registerMessageMapField"][-1] != offsets["s_sc_id2MessageType"]
        or struct.unpack_from("<I", raw_checks["fastRegisterMessageId"], 1)[0] != 1
    ):
        raise DynamicActiveVersionNativeError("selected source field operand differs")
    if (
        _register_move(raw_checks["fastRegisterTypeArgument"]) != (2, 0)
        or _register_move(raw_checks["registerTypeBinding"]) != (7, 2)
        or _register_move(raw_checks["registerTypeValue"]) != (8, 7)
        or _register_move(raw_checks["registerIdBinding"]) != (6, 1)
        or _register_move(raw_checks["registerIdKey"]) != (2, 6)
    ):
        raise DynamicActiveVersionNativeError("selected source message registration argument chain differs")
    for name in ("Major", "Minor", "Phase"):
        if raw_checks["arg" + name][-1] != raw_checks["load" + name][-1]:
            raise DynamicActiveVersionNativeError(
                f"selected source parser output handoff differs: {name}"
            )

    graph = CallGraph(image)
    parser_window = next(row for row in windows if row["name"] == "_ParseVersion")
    parser_literals = loaded_literals(
        graph,
        image.pe.image_base + parser_window["startRva"],
        parser_window["endRva"] - parser_window["startRva"],
    )
    if parser_literals != {contract["versionRegexLiteral"]}:
        raise DynamicActiveVersionNativeError("selected version regex literal differs")
    usage_rows = contract["typeUsages"]
    usage_roles = {"decoderHead", "responseGetterHead", "sessionResponseBody", "registeredLoginMessage"}
    if len(usage_rows) != len(usage_roles) or {row["role"] for row in usage_rows} != usage_roles:
        raise DynamicActiveVersionNativeError("selected source type-usage roles differ")
    for row in usage_rows:
        rva = _number(row["instructionRva"])
        instruction = checked_bytes(rva, 7)
        if instruction[:2] not in (b"\x48\x8b", b"\x4c\x8b") or instruction[2] & 0xC7 != 0x05:
            raise DynamicActiveVersionNativeError(f"selected source type load differs: {row['role']}")
        cell = image.pe.image_base + rva + 7 + struct.unpack_from("<i", instruction, 3)[0]
        if cell - image.pe.image_base != _number(row["usageCellRva"]):
            raise DynamicActiveVersionNativeError(f"selected source type cell differs: {row['role']}")
        index = unresolved_usage_index(
            image.pe.bytes_at_va(cell, 8), image.registration["typesCount"],
            tag=int(row["tag"]), source=str(image.gameassembly), offset=cell,
        )
        type_va = image.pe.u64_at_va(type_table + index * 8)
        if index != int(row["registeredTypeIndex"]) or runtime_type_name(
            image.pe, image.metadata, type_va
        ) != row["runtimeType"]:
            raise DynamicActiveVersionNativeError(f"selected source type differs: {row['role']}")
    calls = contract["calls"]
    call_roles = {
        "majorGroupCountCall", "majorGetGroup", "minorGetGroup",
        "phaseGroupCountCall", "phaseCheckGetGroup", "phaseParseGetGroup",
        "getPlayer", "getBranchVersion", "parseBranchVersion",
        "regexMatch", "tryParseMajor", "tryParseMinor", "tryParsePhase",
        "syncSetBranchVersion", "syncGetBranchVersion", "syncIfixIsPatched",
        "loginSyncBranchVersion", "loginNetConnectAndGSLogin",
        "netLoginAsync", "netLoginIsSucceed", "netLoginGetResponse",
        "sessionSetSucceed", "sessionHandleLoginEncryp",
        "sessionReadResponse", "sessionGetMessageId", "readDecodeMessage",
        "decoderReadHeader", "decoderLookupMessageType", "decoderCreateMessage",
        "decoderMergeMessage", "decoderSetResponseHead",
        "fastGetLoginMessageType", "fastRegisterLoginMessage",
        "registerMessageMapTryAdd", "fastRegistrationPatched", "registerSCMessagePatched",
    }
    if len(calls) != len(call_roles) or {row["role"] for row in calls} != call_roles:
        raise DynamicActiveVersionNativeError("selected source call roles differ")
    for row in calls:
        rva = _number(row["rva"])
        target = _number(row["targetRva"])
        if (
            _target(checked_bytes(rva, 5), rva, "call") != target
            or row["target"] not in graph.names_by_pointer.get(image.pe.image_base + target, ())
        ):
            raise DynamicActiveVersionNativeError(
                f"selected source call differs: {row['role']}"
            )

    branches = contract["branches"]
    branch_roles = {
        "insufficientMajorGroups", "majorParseFailureExits",
        "minorParseFailureExits", "missingPhaseGroupSkips",
        "phaseParseFailureResets",
        "allZeroCold", "minorNonzeroStores", "phaseNonzeroStores", "allZeroExits",
        "syncPatchedBranch",
        "netLoginFailureBranch", "sessionLoginFailureBranch",
        "sessionReadSuccessBranch", "sessionWrongMessageId", "decoderUnknownMessageType",
        "fastRegistrationPatchBranch", "registerSCMessagePatchBranch",
    }
    if len(branches) != len(branch_roles) or {row["role"] for row in branches} != branch_roles:
        raise DynamicActiveVersionNativeError("selected source branch roles differ")
    for row in branches:
        rva = _number(row["rva"])
        kind = row["kind"]
        length = 5 if kind == "jmp" else 2 if kind.endswith("8") else 6
        if _target(checked_bytes(rva, length), rva, kind) != _number(row["targetRva"]):
            raise DynamicActiveVersionNativeError(
                f"selected source branch differs: {row['role']}"
            )
    return {
        "schema": "endfield.dynamic-active-version-native-audit.v1",
        "status": "validated",
        "contractSha256": digest,
        "nativeInputs": inputs,
        "methodsChecked": len(methods),
        "fieldsChecked": len(fields),
        "codeWindowsChecked": len(windows),
        "callsChecked": len(calls),
        "branchesChecked": len(branches),
        "typeUsagesChecked": len(usage_rows),
        "defaultPhaseValue": int(contract["defaultPhaseValue"]),
        "versionRegexLiteral": contract["versionRegexLiteral"],
        "parserGroupIndices": group_indices,
        "evidenceBoundary": contract["evidenceBoundary"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gameassembly", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    args = parser.parse_args(argv)
    try:
        report = validate_active_version_source(args.gameassembly, args.metadata)
    except (OSError, ValueError, KeyError, IndexError, RuntimeError) as error:
        print(f"dynamic-active-version-native: {error}", file=sys.stderr)
        return 1
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"DynamicStreaming active-version source validated: {args.output_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
