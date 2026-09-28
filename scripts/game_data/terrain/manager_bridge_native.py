"""Authenticate the selected managed Terrain-manager internal-call bridge.

This joins a registered IL2CPP method to a UnityPlayer internal-call table
entry and that entry's native setup call. It does not identify a LAYER file,
its owner-local resource, or a managed TextureResources field.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs, sha256_file_upper
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import NativeImage, read_reviewed_contract
from scripts.repo_paths import REPO_ROOT


SCHEMA = "endfield.terrain-manager-bridge-native-contract.v1"
DEFAULT_CONTRACT = CONTRACTS_DIR / "terrain_manager_bridge_native.json"
DEFAULT_OUTPUT = REPO_ROOT / "reports/terrain/manager_bridge_native.json"


def _number(value: Any) -> int:
    return int(str(value), 0)


def _bytes(pe: Any, rva: int, size: int) -> bytes:
    return pe.bytes_at_va(pe.image_base + rva, size)


def _rip_target(pe: Any, rva: int, prefix: bytes, label: str) -> int:
    raw = _bytes(pe, rva, len(prefix) + 4)
    if not raw.startswith(prefix):
        raise ValueError(f"{label}:rip-instruction")
    return rva + len(raw) + struct.unpack_from("<i", raw, len(prefix))[0]


def _call(pe: Any, rva: int, target: int, label: str) -> None:
    raw = _bytes(pe, rva, 5)
    if raw[0] != 0xE8 or rva + 5 + struct.unpack_from("<i", raw, 1)[0] != target:
        raise ValueError(f"{label}:direct-call-target")


def _check_windows(ga: Any, unity: Any, mapper: Any, rows: list[dict[str, Any]]) -> None:
    images = {"GameAssembly.dll": ga, "UnityPlayer.dll": unity}
    if {row["module"] for row in rows} != set(images):
        raise ValueError("windows:module-coverage")
    extents = {name: mapper.pdata_function_extents(pe) for name, pe in images.items()}
    for row in rows:
        pe = images[row["module"]]
        start, end = _number(row["startRva"]), _number(row["endRva"])
        if end <= start:
            raise ValueError(f"windows:{row['module']}:bounds")
        if extents[row["module"]].get(pe.image_base + start) != pe.image_base + end:
            raise ValueError(f"windows:{row['module']}:{start:#x}:pdata")
        digest = hashlib.sha256(_bytes(pe, start, end - start)).hexdigest().upper()
        if digest != row["sha256"].upper():
            raise ValueError(f"windows:{row['module']}:{start:#x}:sha256")


def verify_registration_tables(pe: Any, row: dict[str, Any]) -> dict[str, Any]:
    """Check parallel static name/function slots and the unique terrain entry."""
    count, index = row["count"], row["index"]
    names_rva, functions_rva = _number(row["nameArrayRva"]), _number(row["functionArrayRva"])
    if not isinstance(count, int) or not isinstance(index, int) or not 0 <= index < count <= 100000:
        raise ValueError("registration:count-or-index")
    if functions_rva != names_rva + (count + 1) * 8:
        raise ValueError("registration:parallel-array-adjacency")
    names_raw = _bytes(pe, names_rva, (count + 1) * 8)
    functions_raw = _bytes(pe, functions_rva, count * 8)
    if struct.unpack_from("<Q", names_raw, count * 8)[0] != 0:
        raise ValueError("registration:name-array-sentinel")
    names: list[str] = []
    for slot in range(count):
        name_va = struct.unpack_from("<Q", names_raw, slot * 8)[0]
        function_va = struct.unpack_from("<Q", functions_raw, slot * 8)[0]
        name_offset, name_section, _ = pe.file_offset_for_va(name_va)
        function_offset, function_section, _ = pe.file_offset_for_va(function_va)
        if name_offset is None or name_section != ".rdata":
            raise ValueError(f"registration:name-pointer:{slot}")
        if function_offset is None or function_section != ".text":
            raise ValueError(f"registration:function-pointer:{slot}")
        name = pe.c_string_at_va(name_va)
        if not name:
            raise ValueError(f"registration:empty-name:{slot}")
        names.append(name)
    if names.count(row["name"]) != 1 or names[index] != row["name"]:
        raise ValueError("registration:unique-method-name")
    name_va = struct.unpack_from("<Q", names_raw, index * 8)[0]
    function_va = struct.unpack_from("<Q", functions_raw, index * 8)[0]
    if name_va != pe.image_base + _number(row["nameStringRva"]):
        raise ValueError("registration:name-string-pointer")
    if function_va != pe.image_base + _number(row["functionRva"]):
        raise ValueError("registration:function-pointer")
    return {"name": row["name"], "entryIndex": index,
            "nameStringRva": row["nameStringRva"], "backendRva": row["functionRva"],
            "parallelEntryCount": count}


def verify_bridge(image: NativeImage, unity: Any, contract: dict[str, Any]) -> dict[str, Any]:
    """Prove the selected stored route up to the UnityPlayer setup entry."""
    ga = image.pe
    method_row = contract["method"]
    method = image.metadata.methods[method_row["index"]]
    if (image.type_name(method.declaring_type) != method_row["type"]
            or image.metadata.string(method.name_index) != method_row["name"]
            or image.method_pointer_va(method) != ga.image_base + _number(method_row["rva"])):
        raise ValueError("method:metadata-identity-or-pointer")
    if len(image.metadata.parameters_for(method)) != method_row["parameterCount"]:
        raise ValueError("method:parameter-count")
    expected_windows = {
        ("GameAssembly.dll", _number(contract["resolver"]["rva"])),
        ("GameAssembly.dll", _number(method_row["rva"])),
        ("UnityPlayer.dll", _number(contract["backend"]["rva"])),
        ("UnityPlayer.dll", _number(contract["backend"]["setupTargetRva"])),
    }
    if {(row["module"], _number(row["startRva"])) for row in contract["windows"]} != expected_windows:
        raise ValueError("windows:required-entry-coverage")
    _check_windows(ga, unity, image.mapper, contract["windows"])

    signature = method_row["resolverString"]
    registration = contract["registration"]
    if (not signature.startswith(registration["name"] + "(")
            or not signature.endswith(")")):
        raise ValueError("method:signature-name-contract")
    if ga.c_string_at_va(ga.image_base + _number(method_row["resolverStringRva"]), limit=1024) != signature:
        raise ValueError("method:resolver-string")
    cell_load = _rip_target(ga, _number(method_row["cacheLoadRva"]), b"\x48\x8b\x05",
                            "method:cache-load")
    cell_store = _rip_target(ga, _number(method_row["cacheStoreRva"]), b"\x48\x89\x05",
                             "method:cache-store")
    if cell_load != cell_store:
        raise ValueError("method:cache-cell-differs")
    if (_rip_target(ga, _number(method_row["resolverStringLoadRva"]), b"\x48\x8d\x0d",
                    "method:signature-load") != _number(method_row["resolverStringRva"])):
        raise ValueError("method:signature-load-target")
    resolver = contract["resolver"]
    _call(ga, _number(method_row["resolverCallRva"]), _number(resolver["rva"]),
          "method:resolver-call")
    if _bytes(ga, _number(method_row["tailJumpRva"]), 3) != b"\x48\xff\xe0":
        raise ValueError("method:resolved-function-jump")

    branch = _bytes(ga, _number(resolver["lookupMissBranchRva"]), 2)
    if (branch[0] != 0x74 or _number(resolver["lookupMissBranchRva"]) + 2
            + struct.unpack("<b", branch[1:])[0] != _number(resolver["lookupMissTargetRva"])):
        raise ValueError("resolver:lookup-miss-branch")
    if _bytes(ga, _number(resolver["openParenConstantRva"]), 5) != b"\xba\x28\x00\x00\x00":
        raise ValueError("resolver:open-paren-search-byte")
    for source, target, label in (
        ("openParenSearchCallRva", "openParenSearchTargetRva", "open-paren-search"),
        ("prefixCopyCallRva", "prefixCopyTargetRva", "prefix-copy"),
        ("secondLookupCompareCallRva", "secondLookupCompareTargetRva", "second-lookup"),
    ):
        _call(ga, _number(resolver[source]), _number(resolver[target]), f"resolver:{label}")
    entry = verify_registration_tables(unity, registration)
    backend = contract["backend"]
    if _number(backend["rva"]) != _number(registration["functionRva"]):
        raise ValueError("backend:registration-target")
    _call(unity, _number(backend["setupCallRva"]), _number(backend["setupTargetRva"]),
          "backend:setup-call")
    return {"method": f"{method_row['type']}.{method_row['name']}",
            "managedMethodRva": method_row["rva"], "resolverStringRva": method_row["resolverStringRva"],
            "registration": entry, "setupCallRva": backend["setupCallRva"],
            "setupTargetRva": backend["setupTargetRva"]}


def validate_terrain_manager_bridge(*, game_root: Path,
                                    contract_path: Path = DEFAULT_CONTRACT) -> dict[str, Any]:
    """Fail closed on any missing or changed selected native input."""
    try:
        contract, digest = read_reviewed_contract(
            contract_path, schema=SCHEMA, status="validated", label="terrain-manager-bridge"
        )
        expected = contract["nativeInputs"]
        if not isinstance(expected, dict):
            raise ValueError("nativeInputs:not-object")
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        return {"status": "validation_failed", "bridge": None, "reason": f"contract={error}"}
    root = Path(game_root)
    gameassembly = root.parent / "GameAssembly.dll"
    metadata = root / "il2cpp_data/Metadata/global-metadata.dat"
    unityplayer = root.parent / "UnityPlayer.dll"
    gate = check_installed_native_inputs(
        str(expected.get("gameAssemblySha256") or ""),
        str(expected.get("metadataSha256") or ""),
        gameassembly=gameassembly, metadata=metadata,
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        return {"status": gate.status, "bridge": None, "reason": gate.detail}
    try:
        unity_hash = sha256_file_upper(unityplayer)
    except OSError as error:
        return {"status": "missing", "bridge": None, "reason": f"UnityPlayer.dll={error}"}
    if unity_hash != str(expected.get("unityPlayerSha256") or "").upper():
        return {"status": "mismatched", "bridge": None, "reason": "UnityPlayer.dll hash differs"}
    try:
        image = NativeImage(gameassembly, metadata, label="terrain-manager-bridge")
        unity = image.mapper.PeImage(unityplayer)
        bridge = verify_bridge(image, unity, contract)
    except (OSError, ValueError, KeyError, TypeError, IndexError, struct.error, RuntimeError) as error:
        return {"status": "validation_failed", "bridge": None, "reason": str(error)}
    return {"status": "validated", "bridge": bridge, "nativeInputs": expected,
            "contractSha256": digest, "evidenceBoundary": contract["evidenceBoundary"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-root", type=Path, required=True,
                        help="Explicit selected Endfield_Data root")
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output.resolve()
    if (REPO_ROOT / "reports").resolve() not in output.parents:
        parser.error("--output must be under reports/")
    result = validate_terrain_manager_bridge(game_root=args.game_root, contract_path=args.contract)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Terrain manager native bridge: {result['status']}")
    if result["status"] != "validated":
        print(result.get("reason", ""))
    return 0 if result["status"] == "validated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
