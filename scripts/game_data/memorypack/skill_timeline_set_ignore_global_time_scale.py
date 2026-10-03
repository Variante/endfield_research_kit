"""Selected-source SkillData 0x0152 SetIgnoreGlobalTimeScaleAction reader.

The native gate proves seven ordered reads, including the finite
TargetSettings child. The CLI checks one saved logical SkillData source;
the shared reader reuses this grammar only after the same native gate.
Whole-source publication belongs to the complete SkillData family gate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path
from typing import Any, Mapping

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.il2cpp.context import method_spec_record, method_spec_usage_index
from scripts.game_data.il2cpp.context_audit_memorypack import buff_action_read_order
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import (
    MODULE_REPO_ROOT,
    _atomic_write_json,
    _guard_output_path,
)


LABEL = "skillTimelineSetIgnoreGlobalTimeScale"
TAG = 0x0152
CONTRACT_PATH = CONTRACTS_DIR / "skill_timeline_set_ignore_global_time_scale_native.json"
WRAPPER_NAME = "Beyond.MemoryPack.Beyond_Gameplay_Core_SetIgnoreGlobalTimeScaleAction_DataForMemoryPack"
TYPE_NAME = "Beyond.Gameplay.Core.SetIgnoreGlobalTimeScaleAction+Data"
FIELD_NAMES = (
    "isEnable", "priorityLevel", "priorityOffset", "serverActionIndex",
    "ignoreGlobalTimeScale", "revertOnEnd", "targetSettings",
)
READ_KINDS = (
    "bool-byte", "enum32", "scalar32", "scalar32", "bool-byte", "bool-byte",
    "target-profile",
)
CONTEXT_TYPES = (
    "Beyond.Gameplay.Core.AbilityAction+AbilityActionData+Priority",
    "Beyond.Gameplay.Core.TargetSettings",
)
SETTERS = (
    ("set___ignoreGlobalTimeScale__", "System.Boolean"),
    ("set___revertOnEnd__", "System.Boolean"),
    ("set___targetSettings__", "Beyond.Gameplay.Core.TargetSettings"),
)


def _contract() -> dict[str, Any]:
    contract, _ = read_reviewed_contract(
        CONTRACT_PATH,
        schema="endfield.skill-timeline-set-ignore-global-time-scale-native-contract.v1",
        label=LABEL, status="exact-current-build",
    )
    reads = contract.get("orderedSourceReads")
    contexts = contract.get("genericContexts")
    setters = contract.get("setterMethods")
    setter_calls = contract.get("setterCallsites")
    selected = contract.get("selectedSource")
    if (
        contract.get("dispatcher", {}).get("unionTag") != TAG
        or contract["dispatcher"].get("wrapperName") != WRAPPER_NAME
        or contract.get("serializedMemberCount") != len(FIELD_NAMES)
        or not isinstance(reads, list) or len(reads) != len(FIELD_NAMES)
        or [row.get("memberIndex") for row in reads] != list(range(len(FIELD_NAMES)))
        or tuple(row.get("fieldName") for row in reads) != FIELD_NAMES
        or tuple(row.get("readKind") for row in reads) != READ_KINDS
        or not isinstance(contexts, list)
        or [row.get("memberIndex") for row in contexts] != [1, 6]
        or tuple(row.get("typeName") for row in contexts) != CONTEXT_TYPES
        or not isinstance(setters, list)
        or tuple(tuple(row[1:]) for row in setters) != SETTERS
        or not isinstance(setter_calls, list) or len(setter_calls) != 3
        or [row.get("memberIndex") for row in setter_calls] != [4, 5, 6]
        or [row.get("methodIndex") for row in setter_calls] != [row[0] for row in setters]
        or contract.get("primitiveReadContract") != "buff_10c_native.json"
        or contract.get("nestedProfileContract") != "buff_ec_native.json"
        or contract.get("catalogContract") != "levelscript_union_tags.json"
        or len(contract.get("methods", ())) != 2
        or len(contract.get("codeWindows", ())) != 2
        or bytes.fromhex(contract.get("memberCountInstruction", {}).get("hex", ""))
        != b"\x80\x7c\x24\x38\x07"
        or not isinstance(selected, dict)
        or not str(selected.get("virtualPath", "")).startswith("Data/Json/SkillData/")
        or type(selected.get("length")) is not int
        or type(selected.get("firstActionOffset")) is not int
        or len(str(selected.get("logicalSha256", ""))) != 64
        or len(str(selected.get("logicalMd5", ""))) != 32
    ):
        raise ValueError(f"{LABEL}.contract:source-shape")
    return contract


def _check_call(image: Any, row: Mapping[str, Any], *, rva_key: str,
                hex_key: str, target_key: str) -> int:
    rva = row[rva_key]
    raw = image.pe.bytes_at_va(image.pe.image_base + rva, 5)
    if raw[:1] != b"\xe8" or raw.hex().upper() != row[hex_key]:
        raise ValueError(f"{LABEL}.native:source-call={rva:#x}")
    target = rva + 5 + struct.unpack_from("<i", raw, 1)[0]
    if target != row[target_key]:
        raise ValueError(f"{LABEL}.native:source-target={rva:#x}")
    return target


def _check_context(image: Any, context: Mapping[str, Any]) -> None:
    cell, usage = image.nested_usage_cell(dict(context), label=LABEL)
    index = method_spec_usage_index(
        usage, image.registration["methodSpecsCount"], source=LABEL, offset=cell,
    )
    address = int(image.registration["methodSpecs"], 16) + index * 12
    spec = method_spec_record(
        image.pe.bytes_at_va(address, 12), len(image.metadata.methods),
        image.registration["genericInstsCount"], source=LABEL, offset=address,
    )
    arguments = image.instantiations.resolve(spec[2]).arguments
    if len(arguments) != 1:
        raise ValueError(f"{LABEL}.native:generic-arity")
    argument = bytes.fromhex(arguments[0].raw_type_record_hex)
    definition = struct.unpack_from("<Q", argument)[0]
    if (
        index != context["methodSpecIndex"] or list(spec) != context["methodSpec"]
        or argument.hex().upper() != context["argumentRawHex"]
        or argument[10] != context["typeKind"]
        or definition != context["typeDefinition"]
        or image.type_name(definition) != context["typeName"]
    ):
        raise ValueError(f"{LABEL}.native:generic-type={context['memberIndex']}")


def validate_current_native_contract(*, gameassembly: Path, metadata: Path) -> dict[str, Any]:
    """Recheck the selected build, route, source order, and nested types."""
    contract = _contract()
    expected = contract["nativeInputs"]
    gate = check_installed_native_inputs(
        expected["GameAssembly.dll"], expected["global-metadata.dat"],
        gameassembly=Path(gameassembly), metadata=Path(metadata),
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise ValueError(f"{LABEL}.native:{gate.status}:{gate.detail}")
    unity = gate.gameassembly.parent / "UnityPlayer.dll"
    if (not unity.is_file() or hashlib.sha256(unity.read_bytes()).hexdigest().upper()
            != expected["UnityPlayer.dll"]):
        raise ValueError(f"{LABEL}.native:UnityPlayer.dll:missing-or-mismatched")
    catalog = json.loads((CONTRACTS_DIR / contract["catalogContract"]).read_bytes())
    route = catalog.get("families", {}).get("AbilityActionData", [])[TAG]
    switch = catalog.get("switches", {}).get("AbilityActionData", {})
    if (
        catalog.get("schema") != "endfield.levelscript-union-tags.v1"
        or catalog.get("nativeInputs", {}).get("gameAssemblySha256") != expected["GameAssembly.dll"]
        or catalog.get("nativeInputs", {}).get("metadataSha256") != expected["global-metadata.dat"]
        or route.get("tag") != TAG or route.get("wrapperName") != WRAPPER_NAME
        or route.get("wrappedType") != TYPE_NAME
        or route.get("memberCount") != len(FIELD_NAMES)
        or switch.get("entryCount") != len(catalog["families"]["AbilityActionData"])
    ):
        raise ValueError(f"{LABEL}.native:catalog-drift")
    image = open_native_image(gate.gameassembly, gate.metadata)
    if (int(switch["tableVa"], 16)
            != image.pe.image_base + contract["dispatcher"]["switchTableRva"]):
        raise ValueError(f"{LABEL}.native:switch-table")
    image.validate_dispatcher(contract["dispatcher"], label=LABEL)
    methods = [image.validate_method_row(row, label=LABEL) for row in contract["methods"]]
    image.check_windows(contract["codeWindows"], label=LABEL)
    count = contract["memberCountInstruction"]
    image.check_instruction_windows([[count["rva"], count["hex"]]], label=LABEL)
    owner = image.metadata.types[contract["dispatcher"]["wrapperTypeDefinition"]]
    if image.setter_methods(owner, parameter="typeName", label=LABEL) != contract["setterMethods"]:
        raise ValueError(f"{LABEL}.native:setter-order")

    primitive = json.loads((CONTRACTS_DIR / contract["primitiveReadContract"]).read_bytes())
    targets = {row["sourceTargetRva"] for row in contract["orderedSourceReads"]
               if row["readKind"] in ("bool-byte", "enum32", "scalar32")}
    targets.add(contract["memberHeaderSourceCall"]["sourceTargetRva"])
    windows = [row for row in primitive.get("codeWindows", ())
               if row.get("startRva") in targets]
    if primitive.get("schemaVersion") != 1 or {row["startRva"] for row in windows} != targets:
        raise ValueError(f"{LABEL}.native:primitive-source-drift")
    image.check_windows(windows, label=LABEL)
    target = json.loads((CONTRACTS_DIR / contract["nestedProfileContract"]).read_bytes())
    if (target.get("schemaVersion") != 1
            or len(target.get("anonymousReadOrder", {}).get("member13", ())) != 13):
        raise ValueError(f"{LABEL}.native:target-profile-drift")
    buff_action_read_order(
        image.pe, image.metadata, image.registration, image.instantiations,
        image.modules, image.owners, source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / contract["nestedProfileContract"],
    )
    reader_window = contract["codeWindows"][0]
    previous = -1
    for call in (contract["memberHeaderSourceCall"], *contract["orderedSourceReads"]):
        rva = call["sourceCallsiteRva"]
        if not reader_window["startRva"] <= rva < reader_window["endRva"] - 4 or rva <= previous:
            raise ValueError(f"{LABEL}.native:source-order")
        previous = rva
        _check_call(image, call, rva_key="sourceCallsiteRva", hex_key="sourceCallHex",
                    target_key="sourceTargetRva")
    for setter in contract["setterCallsites"]:
        rva = setter["callsiteRva"]
        if not reader_window["startRva"] <= rva < reader_window["endRva"] - 4:
            raise ValueError(f"{LABEL}.native:setter-outside-reader")
        pointer = _check_call(image, setter, rva_key="callsiteRva", hex_key="callHex",
                              target_key="targetRva")
        method = image.metadata.methods[setter["methodIndex"]]
        if image.method_pointer_va(method) != image.pe.image_base + pointer:
            raise ValueError(f"{LABEL}.native:setter-target={rva:#x}")
    for context in contract["genericContexts"]:
        _check_context(image, context)
    return {"status": "validated", "unionTag": TAG, "nativeInputs": expected,
            "methodIndices": methods, "sourceReadCount": len(READ_KINDS),
            "genericContextCount": len(CONTEXT_TYPES)}


def _consume_action(reader: Reader, width: int) -> dict[str, Any]:
    """Consume one reached action with the caller's bounded cursor."""
    offset = reader.pos
    if width != 3 or reader.data[offset:offset + 3] != b"\xfa\x52\x01":
        raise ValueError(f"{LABEL}.source:tag-mismatch")
    reader.take(3, "union-tag")
    if reader.peek() == 0xFF:
        reader.take(1, "null-wrapper")
        return {"status": "exact-null-wrapper", "tag": TAG, "start": offset,
                "end": reader.pos, "fields": []}
    reader.header(len(FIELD_NAMES))
    fields = []
    for name, kind in zip(FIELD_NAMES, READ_KINDS):
        start = reader.pos
        if kind == "bool-byte":
            reader.take(1, name)
        elif kind in ("enum32", "scalar32"):
            reader.take(4, name)
        elif kind == "target-profile":
            reader.target_profile()
        else:
            raise ValueError(f"{LABEL}.reader:unknown-kind={kind}")
        fields.append({"name": name, "kind": kind, "start": start, "end": reader.pos})
    return {"status": "exact-stored-action-span", "tag": TAG, "start": offset,
            "end": reader.pos, "fields": fields,
            "evidenceBoundary": "stored action framing only"}


def decode_action(data: bytes, offset: int, *, validation: Mapping[str, Any]) -> dict[str, Any]:
    """Consume one native-gated action at an explicit source offset."""
    if validation.get("status") != "validated" or validation.get("unionTag") != TAG:
        raise ValueError(f"{LABEL}.native:not-validated")
    if type(offset) is not int or offset < 0 or offset + 4 > len(data):
        raise ValueError(f"{LABEL}.source:offset-outside-source")
    reader = Reader(data, f"{LABEL}.source")
    reader.pos = offset
    return _consume_action(reader, 3)


def decode_shared_action(reader: Reader, depth: int, tag: int, width: int) -> None:
    """Allow a source-scoped shared-sequence replay after its native gate."""
    del depth
    if tag != TAG:
        raise ValueError(f"{LABEL}.unionTag:unsupported")
    _consume_action(reader, width)


def decode_selected_source(source: Path, *, gameassembly: Path,
                           metadata: Path) -> dict[str, Any]:
    """Authenticate the frozen Pograni source, then parse its first 0x0152."""
    contract = _contract()
    selected = contract["selectedSource"]
    validation = validate_current_native_contract(
        gameassembly=gameassembly, metadata=metadata,
    )
    data = Path(source).read_bytes()
    sha256 = hashlib.sha256(data).hexdigest().upper()
    md5 = hashlib.md5(data).hexdigest().upper()
    if (len(data), sha256, md5) != (
        selected["length"], selected["logicalSha256"], selected["logicalMd5"]
    ):
        raise ValueError(f"{LABEL}.source:logical-bytes-mismatch")
    action = decode_action(data, selected["firstActionOffset"], validation=validation)
    return {
        "schema": "endfield.skill-set-ignore-global-time-scale-selected-source.v1",
        "status": "source-scoped-diagnostic",
        "publicationEligible": False,
        "source": {"path": Path(source).resolve().as_posix(),
                   "virtualPath": selected["virtualPath"], "length": len(data),
                   "logicalSha256": sha256, "logicalMd5": md5},
        "nativeValidation": validation,
        "action": action,
        "evidenceBoundary": (
            "Selected copied bytes and selected-build native reads prove one stored "
            "0x0152 action span. The enclosing ActionGroup, whole SkillData EOF, "
            "current VFS chunk and runtime action execution are not established."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--gameassembly", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not any(args.output.resolve().is_relative_to((MODULE_REPO_ROOT / root).resolve())
               for root in ("reports", "tmp", "scratch")):
        raise ValueError(f"{LABEL}.output:expected-reports-or-disposable-root")
    _guard_output_path(args.output, [args.source, args.gameassembly, args.metadata,
                                     CONTRACT_PATH])
    result = decode_selected_source(
        args.source, gameassembly=args.gameassembly, metadata=args.metadata,
    )
    _atomic_write_json(args.output, result)
    print(json.dumps({"status": result["status"], "action": result["action"],
                      "output": str(args.output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
