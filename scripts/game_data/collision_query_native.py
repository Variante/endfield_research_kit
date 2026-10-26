"""Authenticate query observers on explicit native files; never attach or run game code.

Native registration is a runtime gate, not an inference from paired arrays.
The contract proves the literal/resolver/cache/caller route and target ABI;
the observer must additionally see that caller and its matching live cache.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct

from scripts.common import check_installed_native_inputs, sha256_file
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.corpus_common import atomic_write_text
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract, NATIVE_MAPPER_PATH
from scripts.game_data.il2cpp.pe_exports import resolve_named_exports
from scripts.game_data.il2cpp.protocol import load_native_mapper, runtime_type_field_offsets
from scripts.game_data.mission_trace_capture_prepare import SelectedMethods
from scripts.repo_paths import REPO_ROOT

CONTRACT = CONTRACTS_DIR / "collision_query_native.json"
SCHEMA = "endfield.collision-query-native.v1"
# These are compiled signatures and capacities, not selected-build addresses.
ABI = {
    "capsule_results": (("pointer", "pointer", "pointer", "f32", "pointer", "pointer", "f32", "i32", "i32"), "i32", 16),
    "sphere_results": (("pointer", "pointer", "f32", "pointer", "pointer", "f32", "i32", "i32"), "i32", 17),
    "ray_results": (("pointer", "pointer", "pointer", "f32", "i32", "i32"), "i32", 18),
    "overlap_results": (("pointer", "pointer", "pointer", "f32", "pointer", "i32", "i32"), "i32", 19),
    "ray_single": (("pointer", "pointer", "f32", "pointer", "i32", "i32"), "bool", 20),
    "sphere_single": (("pointer", "pointer", "f32", "pointer", "f32", "pointer", "i32", "i32"), "bool", 21),
    "collider_filter": (("pointer", "pointer", "bool", "pointer"), "bool", 23),
    "movement": (("pointer", "pointer", "pointer", "bool", "pointer", "f32", "f32", "bool", "pointer"), "bool", 24),
    "floor": (("pointer", "pointer", "pointer", "f32", "pointer"), "void", 25),
    "movement_overlap": (("pointer", "pointer", "pointer", "f32", "bool", "bool", "pointer"), "i32", 26),
    "penetration": (("pointer", "pointer", "f32", "pointer", "pointer", "pointer", "pointer", "pointer", "pointer"), "bool", 27),
    "report_dispatch": (("pointer", "u8"), "void", 28),
    "report_build": (("pointer",), "void", 29),
    "hit_conversion": (("pointer", "pointer", "bool"), "void", 30),
    "proxy_layer": (("pointer", "pointer"), "i32", 32),
    "collider_options": (("pointer", "pointer"), "i32", 33),
    "proxy_from_hit": (("pointer", "pointer", "pointer"), "pointer", 34),
    "cast_buffer": (("pointer",), "pointer", 35),
    "overlap_buffer": (("pointer",), "pointer", 36),
}


def require(condition, detail):
    if not condition:
        raise ValueError("collision-query-native:" + detail)


def validate_image(image, player, contract):
    """Return authenticated pins; literal/cache operands are independently checked."""
    require(contract.get("schema") == SCHEMA and contract.get("status") == "reviewed", "schema/status")
    require(tuple(h["role"] for h in contract["hooks"]) == tuple(ABI), "hook identity/order")
    images = dict(gameAssembly=image.pe, unityPlayer=player)
    selected = SelectedMethods(image)
    targets={image.pe.image_base+h['rva'] for h in contract['hooks'] if h['module']=='gameAssembly'}
    aliases={pointer:[] for pointer in targets}
    for method in image.metadata.methods:
        pointer=image.method_pointer_va(method)
        if pointer in aliases:
            aliases[pointer].append(method.index)
    pins = []
    hooks = []
    for h in contract["hooks"]:
        args, returns, kind = ABI[h["role"]]
        require((tuple(h["abi"]["arguments"]), h["abi"]["returnMode"], h["kind"]) == (args, returns, kind), "compiled ABI:" + h["role"])
        require(h['abi'].get('hiddenReturnBytes', 0) == (24 if h['role']=='proxy_from_hit' else 0), 'hidden return carrier:'+h['role'])
        pe = images[h["module"]]
        require(16 <= h["bodyBytes"] <= 4096, "hook body bound:" + h["role"])
        raw = pe.bytes_at_va(pe.image_base + h["rva"], h["bodyBytes"])
        require(hashlib.sha256(raw).hexdigest() == h["bodySha256"].lower(), "hook body hash:" + h["role"])
        for probe in h["entryProbes"]:
            at, value = probe["offset"], bytes.fromhex(probe["bytes"])
            require(value and at >= 0 and raw[at:at+len(value)] == value, "entry witness:" + h["role"])
        if h["module"] == "gameAssembly":
            image.validate_method_row([h["index"], h["type"], h["method"], h["rva"]], label="collision-query:" + h["role"])
            method = image.metadata.methods[h["index"]]
            params = []
            for p in image.metadata.parameters_for(method):
                type_pointer = image.pe.u64_at_va(int(image.registration["types"], 16)+p.type_index*8)
                params.append(dict(name=image.metadata.string(p.name_index), type=selected.type_name(p.type_index),
                                   byref=bool(image.pe.bytes_at_va(type_pointer, 16)[11] & 32)))
            require((params, selected.type_name(method.return_type), bool(method.flags & 16)) ==
                    (h["parameters"], h["returnType"], h["static"]), "metadata signature/byref:" + h["role"])
            require(aliases[image.pe.image_base+h['rva']] == [h["index"]], "folded hook:" + h["role"])
        hooks.append({**h, "expectedBytes": raw.hex()})
    for w in contract["codeWindows"]:
        require(0 < w["bytes"] <= 4096, "window bounds:" + w["role"])
        pe = images[w["module"]]
        raw = pe.bytes_at_va(pe.image_base+w["rva"], w["bytes"])
        require(hashlib.sha256(raw).hexdigest() == w["sha256"].lower(), "window hash:" + w["role"])
        pins.append({**w, "expectedBytes": raw.hex()})
    for t in contract["types"]:
        td = selected.index.types.get(t["type"])
        require(td is not None and td.index == t["index"] and selected.is_value_type(t["type"]) == t["value"], "type identity:" + t["type"])
        if t["value"]:
            require(selected.value_size(t["type"]) == t["size"], "unboxed size:" + t["type"])
        fields = {image.metadata.string(f.name_index): f for f in image.metadata.fields_for(td)}
        offsets = runtime_type_field_offsets(image.metadata, image.pe, image.registration, td.index)
        for f in t["fields"]:
            actual = fields.get(f["name"])
            require(actual is not None and selected.type_name(actual.type_index) == f["type"] and
                    offsets[f["name"]]-(16 if t["value"] else 0) == f["offset"], "field:" + t["type"] + "::" + f["name"])
    sizes = {t["type"]: t["size"] for t in contract["types"]}
    for name, size in (("UnityEngine.RaycastHit", 64), ("UnityEngine.ECSColliderResultProxy", 24),
                       ("UnityEngine.Vector3", 12), ("UnityEngine.Quaternion", 16),
                       ("Beyond.Gameplay.Core.MovementComponent+FindFloorResult", 152)):
        require(sizes.get(name) == size, "compiled carrier size:" + name)
    for p in contract["probes"]:
        pe = images[p["module"]]
        raw = bytes.fromhex(p["bytes"])
        require(raw and pe.bytes_at_va(pe.image_base+p["rva"], len(raw)) == raw, "native writer/guard probe:" + p["meaning"])
    for p in contract["fieldOperands"]:
        pe = images[p["module"]]
        prefix = bytes.fromhex(p["prefix"])
        raw = pe.bytes_at_va(pe.image_base+p["rva"], len(prefix)+p["width"])
        require(raw[:len(prefix)] == prefix, "field operand prefix:" + p["path"])
        expected = contract
        for part in p["path"].split("."):
            expected = expected[part]
        value = 0 if p["implicitZero"] else int.from_bytes(raw[len(prefix):], "little")
        require(value == expected, "field operand value:" + p["path"])
    require(tuple(b["role"] for b in contract["bindings"]) == tuple(ABI)[:6], "binding identity/order")
    for b in contract["bindings"]:
        validate_binding(image.pe, b)
        require(b["functionRva"] == next(h["rva"] for h in hooks if h["role"] == b["role"]), "binding target:" + b["role"])
    api = contract["arrayLengthApi"]
    export = resolve_named_exports(image.pe, (api["name"],))["selectedExports"]
    require(len(export) == 1 and not export[0]["isForwarder"] and export[0]["targetRva"] == api["rva"], "array length export")
    raw = image.pe.bytes_at_va(image.pe.image_base+api["rva"], api["bytes"])
    require(raw.hex() == api["expectedBytes"] and hashlib.sha256(raw).hexdigest() == api["sha256"], "array length implementation")
    for name, value in contract["limits"].items():
        require(type(value) is int and 1 <= value <= (60000 if name.endswith("Millis") else 65536), "sampling bound:" + name)
    require(contract["limits"]["maxPerQuery"] <= 64 and contract["arrayLayout"]["maxLength"] <= 1048576, "result buffer bounds")
    return dict(hooks=hooks, pins=pins, contract=contract)


def validate_binding(pe, b):
    """Check literal load, resolver call, cache store/load and register call."""
    for at_key, bytes_key in (("lookupRva", "lookupBytes"), ("cacheStoreRva", "cacheStoreBytes"),
                              ("cacheLoadRva", "cacheLoadBytes"), ("callRva", "callBytes")):
        raw = bytes.fromhex(b[bytes_key])
        require(pe.bytes_at_va(pe.image_base+b[at_key], len(raw)) == raw, "binding bytes:" + b["role"] + ":" + at_key)
    lookup = bytes.fromhex(b["lookupBytes"])
    require(len(lookup) == 12 and lookup[:3] == bytes.fromhex("488d0d") and lookup[7] == 0xe8, "lookup instructions:" + b["role"])
    require(b["lookupRva"]+7+struct.unpack_from("<i", lookup, 3)[0] == b["literalRva"] and
            b["lookupRva"]+12+struct.unpack_from("<i", lookup, 8)[0] == b["resolverRva"], "lookup targets:" + b["role"])
    name = b["name"].encode("ascii")+b"\0"
    require(len(name) <= 1024 and pe.bytes_at_va(pe.image_base+b["literalRva"], len(name)) == name, "lookup name:" + b["role"])
    require(b["tableName"] == b["name"].split("(")[0], "lookup API name:" + b["role"])
    store, load = bytes.fromhex(b["cacheStoreBytes"]), bytes.fromhex(b["cacheLoadBytes"])
    register = b["indirectRegister"]
    require(store[:3] == bytes.fromhex("488905") and len(store) == 7 and
            b["cacheStoreRva"]+7+struct.unpack_from("<i", store, 3)[0] == b["cacheCellRva"], "cache store:" + b["role"])
    require(register in ("rax", "r8", "r9") and len(load) == 7 and
            load[:3].hex() == {"rax": "488b05", "r8": "4c8b05", "r9": "4c8b0d"}[register] and
            b["cacheLoadRva"]+7+struct.unpack_from("<i", load, 3)[0] == b["cacheCellRva"], "cache load:" + b["role"])
    call = bytes.fromhex(b["callBytes"])
    require(call.hex() == {"rax": "ffd0", "r8": "41ffd0", "r9": "41ffd1"}[register] and
            b["returnRva"] == b["callRva"]+len(call), "indirect call:" + b["role"])


def load(*, gameassembly: Path, metadata: Path, unityplayer: Path, image=None):
    contract, digest = read_reviewed_contract(CONTRACT, schema=SCHEMA, label="collision-query", status="reviewed")
    inputs = contract["nativeInputs"]
    gate = check_installed_native_inputs(inputs["gameAssemblySha256"], inputs["metadataSha256"], gameassembly=gameassembly, metadata=metadata)
    require(gate.status == "validated", "installed inputs:" + gate.status + ":" + gate.detail)
    require(unityplayer.is_file() and sha256_file(unityplayer).lower() == inputs["unityPlayerSha256"].lower(), "UnityPlayer missing/mismatched")
    if image is None:
        image = open_native_image(gameassembly, metadata)
    require(image.gameassembly.resolve() == gameassembly.resolve() and image.metadata_path.resolve() == metadata.resolve(), "opened input identity")
    player = load_native_mapper(NATIVE_MAPPER_PATH).PeImage(unityplayer)
    result = validate_image(image, player, contract)
    after = check_installed_native_inputs(inputs["gameAssemblySha256"], inputs["metadataSha256"], gameassembly=gameassembly, metadata=metadata)
    require(after.status == "validated" and sha256_file(unityplayer).lower() == inputs["unityPlayerSha256"].lower(), "native inputs changed during validation")
    return {**result, "contractSha256": digest, "status": "validated"}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--game-root", type=Path, required=True)
    p.add_argument("--output", type=Path, default=REPO_ROOT/"reports/runtime_capture/collision/query-native-validation.json")
    args = p.parse_args(argv)
    output = args.output.resolve()
    require(any(output.is_relative_to(REPO_ROOT/r) for r in ("reports", "scratch", "tmp")), "generated output root")
    root = args.game_root.resolve()
    if root.name == "Endfield_Data":
        root = root.parent
    try:
        result = load(gameassembly=root/"GameAssembly.dll", metadata=root/"Endfield_Data/il2cpp_data/Metadata/global-metadata.dat", unityplayer=root/"UnityPlayer.dll")
        report = dict(status="validated", hooks=len(result["hooks"]), windows=len(result["pins"]),
                      nativeInputs=result["contract"]["nativeInputs"], evidenceBoundary=result["contract"]["evidenceBoundary"])
    except (OSError, ValueError, KeyError, IndexError, RuntimeError) as error:
        report = dict(status="failed", diagnostics=[dict(validator="collision_query_native", check="selected_abi_binding", detail=str(error)[:1200])])
    atomic_write_text(output, json.dumps(report, indent=2)+"\n")
    print(json.dumps(report), flush=True)
    return 0 if report["status"] == "validated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
