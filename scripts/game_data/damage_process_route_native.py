"""Authenticate bounded Process call markers and default branch inputs.

This deliberately does not prove a full CFG or dynamic selector reachability.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
from pathlib import Path

from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.damage_process_formula_native import validate_windows
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract

CONTRACT = CONTRACTS_DIR / "damage_process_route_native.json"
SCHEMA = "endfield.damage-process-route-native-contract.v1"


def need(actual, expected, check):
    if actual != expected:
        raise ValueError(f"{check}: expected={expected!r}, actual={actual!r}")


def validate_joins(pe, contract, methods):
    """Check physical call/field joins and both explicit bypass edges."""
    base = pe.image_base
    read = pe.bytes_at_va
    at = lambda r: base + int(r, 16)
    j = contract["joins"]
    fields = {x["field"]: x for x in contract["fields"]}
    for call in contract["calls"]:
        address = at(call["rva"]); raw = read(address, 5)
        need(raw[:1], b"\xe8", "direct-call:" + call["name"])
        need(address + 5 + struct.unpack_from("<i", raw, 1)[0], methods[call["target"]], "call-target:" + call["name"])
        need(address + 5, at(call["returnRva"]), "call-return:" + call["name"])
    pack = read(at(j["packArgumentLeaRva"]), 8)
    defender = read(at(j["defenderArgumentLeaRva"]), 8)
    need(pack[:4], bytes.fromhex("488d8c24"), "pack-this-lea")
    need(defender[:4], pack[:4], "defender-lock-lea")
    need(struct.unpack_from("<i", pack, 4)[0], j["framePackOffset"], "pack-frame")
    offset = fields["Beyond.Gameplay.Core.DamagePackData::defender"]["offset"] - j["boxedHeaderBytes"]
    need(struct.unpack_from("<i", defender, 4)[0], j["framePackOffset"] + offset, "defender-address-join")
    raw = read(at(j["damageTypeLoadRva"]), 7)
    need(raw[:3], bytes.fromhex("8b8c24"), "damage-type-ECX-load")
    offset = fields["Beyond.Gameplay.Core.DamagePackData::damageType"]["offset"] - j["boxedHeaderBytes"]
    need(struct.unpack_from("<i", raw, 3)[0], j["framePackOffset"] + offset, "damage-type-address-join")
    raw = read(at(j["specialCallRva"]), 5)
    need(raw[:1], b"\xe8", "health-predicate-call")
    predicate = at(j["specialPredicateRva"])
    need(at(j["specialCallRva"]) + 5 + struct.unpack_from("<i", raw, 1)[0], predicate, "health-predicate-target")
    getter = methods["healthGetter"]
    from scripts.game_data.il2cpp.context import rip_qword_load_target
    roots = []
    for pointer, root_offset, table_offset, cold in (
            (predicate, j["specialRootLoadOffset"], j["specialTableLoadOffset"], j["specialColdRva"]),
            (getter, j["healthGetterRootLoadOffset"], j["healthGetterTableLoadOffset"], j["healthGetterColdRva"])):
        address = pointer + root_offset
        roots.append(rip_qword_load_target(read(address, 7), address, source="damage-route-health"))
        need(read(pointer + table_offset, 4), bytes.fromhex("4c8b48") + bytes([j["healthTableOffset"]]), "health-table-load")
        need(read(pointer + table_offset + 4, 3), bytes.fromhex("4d85c9"), "health-table-null-test")
        branch_at = pointer + table_offset + 7
        branch = read(branch_at, 6)
        need(branch[:2], bytes.fromhex("0f85"), "health-table-nonnull-edge")
        need(branch_at + 6 + struct.unpack_from("<i", branch, 2)[0], at(cold), "health-cold-edge-target")
        need(read(at(cold), 7), bytes.fromhex("498b81") + struct.pack("<i", j["healthFunctionOffset"]), "health-slot-load")
        need(read(at(cold) + 7, 3), bytes.fromhex("4885c0"), "health-slot-null-test")
        branch = read(at(cold) + 10, 6)
        need(branch[:2], bytes.fromhex("0f84"), "health-slot-null-edge")
        need(at(cold) + 16 + struct.unpack_from("<i", branch, 2)[0], pointer + table_offset + 13, "health-original-edge-target")
        need(read(at(cold) + 29, 3), bytes.fromhex("ffd090"), "health-replacement-call")
        branch = read(at(cold) + 32, 5)
        need(branch[:1], b"\xe9", "health-replacement-continuation")
        continuation = (j["specialIndependentCompareOffset"] if pointer == predicate else j["healthGetterRestoreOffset"])
        need(at(cold) + 37 + struct.unpack_from("<i", branch, 1)[0], pointer + continuation, "health-replacement-result-join")
    need(roots[0], roots[1], "same-health-selector-root")
    data_offset = fields["Beyond.Gameplay.Core.AbilitySystem::<data>k__BackingField"]["offset"]
    health_offset = fields["Beyond.Gameplay.Core.AbilitySystemData::healthType"]["offset"]
    for pointer, data_at, health_at in ((predicate, j["specialDefaultDataLoadOffset"], j["specialDefaultHealthLoadOffset"]),
                                      (getter, j["healthGetterDefaultDataLoadOffset"], j["healthGetterDefaultHealthLoadOffset"])):
        need(read(pointer + data_at, 7), bytes.fromhex("488b81") + struct.pack("<i", data_offset), "data-reference-load")
        need(read(pointer + health_at, 6), bytes.fromhex("8b80") + struct.pack("<i", health_offset), "health-enum-load")
    health_enum = next(x["members"] for x in contract["enums"] if x["type"] == "Beyond.Gameplay.Core.HealthType")
    need(read(predicate + j["specialIndependentCompareOffset"], 3), bytes.fromhex("83f8") + bytes([health_enum["Independent"]]), "health-independent-compare")
    uses = methods["usesRaw"]
    address = uses + j["usesRawRootLoadOffset"]
    uses_root = rip_qword_load_target(read(address, 7), address, source="damage-route-raw")
    factor = at(j["factorSelectorRva"])
    factor_root = rip_qword_load_target(read(factor, 7), factor, source="damage-route-factor")
    need(uses_root, factor_root, "same-raw-factor-root")
    need(roots[0], factor_root, "same-health-factor-root")
    need(read(factor + 7, 4), bytes.fromhex("488b48") + bytes([j["factorTableOffset"]]), "factor-table-load")
    need(j["usesRawTableOffset"], j["factorTableOffset"], "same-raw-factor-table-family")
    need(j["healthTableOffset"] != j["factorTableOffset"], True, "distinct-health-table-family")
    need(read(uses + 7, 4), bytes.fromhex("4c8b48") + bytes([j["usesRawTableOffset"]]), "raw-table-load")
    need(read(uses + 16, 7), bytes.fromhex("498b81") + struct.pack("<i", j["usesRawFunctionOffset"]), "raw-replacement-slot")
    for edge in (14, 26):
        branch = read(uses + edge, 2)
        need(branch[:1], b"\x74", "raw-null-selection-edge")
        need(uses + edge + 2 + struct.unpack_from("<b", branch, 1)[0], uses + j["usesRawDefaultOffset"], "raw-original-edge-target")
    need(read(uses + 40, 3), bytes.fromhex("48ffe0"), "raw-replacement-tail")
    first, second = j["usesRawTrueCodes"]
    expected = bytes.fromhex("83f9") + bytes([first]) + bytes.fromhex("7503b001c383f9") + bytes([second]) + bytes.fromhex("0f94c0c3")
    need(read(uses + j["usesRawDefaultOffset"], len(expected)), expected, "raw-default-return-program")
    for edge in j["skipBranches"]:
        address = at(edge["rva"]); raw = read(address, 6)
        need(raw[:2], bytes.fromhex("0f85"), "bypass-conditional:" + edge["name"])
        need(address + 6 + struct.unpack_from("<i", raw, 2)[0], at(edge["targetRva"]), "bypass-target:" + edge["name"])
    merge = j["alternativeMerge"]
    address = at(merge["rawJumpRva"]); raw = read(address, 2)
    need(raw[:1], b"\xeb", "raw-result-merge-jump")
    need(address + 2 + struct.unpack_from("<b", raw, 1)[0], at(merge["mergeRva"]), "raw-result-merge-target")
    address = at(merge["specialLastLoadRva"]); expected = bytes.fromhex(merge["specialLastLoadBytes"])
    need(read(address, len(expected)), expected, "special-result-final-load")
    need(address + len(expected), at(merge["mergeRva"]), "special-result-merge-fallthrough")


def evaluate_route(image, contract):
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.protocol import native_enum_members, field_defaults
    selected = NativeReferenceContext(image); md = image.metadata
    failures = validate_windows(image, contract)
    if failures:
        raise ValueError(str(failures[0]))
    methods = {}
    for spec in contract["methods"]:
        td = selected.index.types[spec["type"]]
        matches = [m for m in md.methods_for(td) if md.string(m.name_index) == spec["method"]]
        need(len(matches), 1, "unique-method:" + spec["key"])
        method = matches[0]
        actual = [selected.type_name(method.return_type), bool(method.flags & 16),
                  [selected.type_name(p.type_index) for p in md.parameters_for(method)]]
        need(actual, [spec["return"], spec["static"], spec["parameters"]], "method-signature:" + spec["key"])
        pointer = image.method_pointer_va(method)
        need(pointer - image.pe.image_base, int(spec["rva"], 16), "method-entry:" + spec["key"])
        methods[spec["key"]] = pointer
    for spec in contract["fields"]:
        need(list(selected.field(spec["field"])[1:]), [spec["type"], spec["offset"]], "field:" + spec["field"])
    for spec in contract["enums"]:
        rows = native_enum_members(md, field_defaults(md), image.pe, image.registration, spec["type"])
        need({r["name"]: r["id"] for r in rows}, spec["members"], "enum:" + spec["type"])
    validate_joins(image.pe, contract, methods)


def load_damage_process_route(*, gameassembly=None, metadata=None):
    if (gameassembly is None) != (metadata is None):
        raise ValueError("gameassembly and metadata must be supplied together")
    contract, digest = read_reviewed_contract(CONTRACT, schema=SCHEMA, label="damage_process_route", status="reviewed")
    pins = contract["nativeInputs"]
    base = dict(schema=SCHEMA, contractSha256=digest, evidenceBoundary="conditional", facts=None,
                actualSelectorReached=None, actualFactor=None)
    def reject(status, check, detail):
        return dict(base, status=status, detail=str(detail)[:1500], failures=[dict(check=check, detail=str(detail)[:1500])])
    gate = check_installed_native_inputs(pins["gameAssemblySha256"], pins["metadataSha256"], gameassembly=gameassembly, metadata=metadata)
    base["nativeInputs"] = {"gameAssemblySha256": getattr(gate, "gameassembly_sha256", ""), "metadataSha256": getattr(gate, "metadata_sha256", "")}
    if not gate.validated:
        return reject(gate.status, "installed_native_inputs", gate.detail)
    try:
        image = open_native_image(gate.gameassembly, gate.metadata)
        for key, raw in (("gameAssemblySha256", image.pe.buf), ("metadataSha256", image.metadata.buf)):
            actual = hashlib.sha256(raw).hexdigest()
            if actual.lower() != pins[key].lower():
                return reject("mismatched", "opened_native_inputs", f"{key}: expected {pins[key]}, actual {actual}")
        evaluate_route(image, contract)
    except (OSError, ValueError, RuntimeError, KeyError, IndexError, struct.error) as exc:
        return reject("pendingReview", "route_evaluation", exc)
    after = check_installed_native_inputs(pins["gameAssemblySha256"], pins["metadataSha256"], gameassembly=gate.gameassembly, metadata=gate.metadata)
    if not after.validated:
        return reject(after.status, "installed_native_inputs_after", after.detail)
    return dict(base, status="validated", detail="", failures=[], facts=contract["facts"])


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--gameassembly", type=Path); p.add_argument("--metadata", type=Path); p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)
    if (args.gameassembly is None) != (args.metadata is None): p.error("supply both native paths")
    result = load_damage_process_route(gameassembly=args.gameassembly, metadata=args.metadata)
    print(json.dumps(result, indent=2) if args.json else f"damage-process-route: {result['status']} {result['detail']}")
    return 0 if result["status"] == "validated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
