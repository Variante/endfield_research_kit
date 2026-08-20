#!/usr/bin/env python3
"""Recover the shipped BeyondDynamicBone PlayerLoop insertion contract.

This is deliberately evidence-driven: native rows are accepted only when the
explicit installed GameAssembly.dll and global-metadata.dat still match the
reviewed hashes.  Missing or mismatched inputs produce an ``unavailable``
contract and never publish guessed PlayerLoop anchors.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "scratch/character_recovery/secondary_dynamics_owner"
DEFAULT_NATIVE = EVIDENCE / "runtime_native.json"
DEFAULT_PLAYERLOOP_METADATA = EVIDENCE / "playerloop_metadata.json"
DEFAULT_OUTPUT = ROOT / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation/playerloop_recovery_contract.json"
DEFAULT_GAME_ASSEMBLY = Path(r"D:/Program Files/Endfield Game/GameAssembly.dll")
DEFAULT_METADATA = Path(r"D:/Program Files/Endfield Game/Endfield_Data/il2cpp_data/Metadata/global-metadata.dat")
EXPECTED_GAME_ASSEMBLY_SHA256 = "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce"
EXPECTED_METADATA_SHA256 = "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e"
ADD_LOOP_TARGET = "0x183325090"
ADD_LOOP_METHOD_INDEX = 386538
SET_LOOP_METHOD_INDEX = 385094


class ContractError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _pe_sections(image: bytes) -> tuple[int, list[tuple[int, int, int, int]]]:
    pe = struct.unpack_from("<I", image, 0x3C)[0]
    if image[pe:pe + 4] != b"PE\0\0":
        raise ContractError("GameAssembly.dll is not a PE image")
    coff = pe + 4
    count = struct.unpack_from("<H", image, coff + 2)[0]
    optional_size = struct.unpack_from("<H", image, coff + 16)[0]
    optional = coff + 20
    if struct.unpack_from("<H", image, optional)[0] != 0x20B:
        raise ContractError("GameAssembly.dll is not PE32+")
    base = struct.unpack_from("<Q", image, optional + 24)[0]
    section_table = optional + optional_size
    sections = []
    for index in range(count):
        offset = section_table + index * 40
        virtual_size, virtual_address, raw_size, raw_pointer = struct.unpack_from("<IIII", image, offset + 8)
        sections.append((virtual_address, max(virtual_size, raw_size), raw_pointer, raw_size))
    return base, sections


def _va_offset(image: bytes, base: int, sections: list[tuple[int, int, int, int]], va: int) -> int:
    rva = va - base
    for address, size, raw, raw_size in sections:
        if address <= rva < address + size:
            offset = raw + rva - address
            if offset + 8 <= len(image):
                return offset
    raise ContractError(f"native VA is outside GameAssembly.dll: 0x{va:x}")


def _literal(metadata: bytes, index: int) -> str:
    # v29+ header: stringLiteral and stringLiteralData are the first two rows.
    literal_offset, literal_size = struct.unpack_from("<II", metadata, 8)
    data_offset, data_size = struct.unpack_from("<II", metadata, 16)
    if index < 0 or index * 8 + 8 > literal_size:
        raise ContractError(f"string literal index out of bounds: {index}")
    length, data_index = struct.unpack_from("<II", metadata, literal_offset + index * 8)
    if data_index + length > data_size:
        raise ContractError(f"string literal data out of bounds: {index}")
    return metadata[data_offset + data_index:data_offset + data_index + length].decode("utf-8", "replace")


def _decode_slot(image: bytes, base: int, sections: list[tuple[int, int, int, int]], metadata: bytes, va: int) -> dict[str, Any]:
    offset = _va_offset(image, base, sections, va)
    encoded = struct.unpack_from("<Q", image, offset)[0]
    kind = encoded >> 29
    source_index = (encoded >> 1) & 0x0FFFFFFF
    result: dict[str, Any] = {"slotVa": f"0x{va:x}", "encodedHandle": f"0x{encoded:x}", "kind": kind, "sourceIndex": source_index}
    if kind != 5:
        result["status"] = "not_string_literal"
        return result
    result["status"] = "decoded"
    result["value"] = _literal(metadata, source_index)
    return result


def _target_va(row: dict[str, Any]) -> int:
    return int(str(row.get("targetVa", "0")), 0)


def _stack_value(context: dict[str, Any], slot: str) -> bool | None:
    matches: list[str] = []
    pattern = re.compile(
        rf"^mov \[rsp\+{re.escape(slot)}\], (0x[01]|r14|r14b|r14d)$"
    )
    for instruction in context.get("nearbyInstructions", []):
        text = str(instruction.get("text", ""))
        match = pattern.fullmatch(text)
        if match:
            matches.append(match.group(1))
    if len(matches) != 1:
        return None
    return matches[0] == "0x1"


def recover(native: dict[str, Any], loop_metadata: dict[str, Any], image: bytes, metadata: bytes) -> dict[str, Any]:
    base, sections = _pe_sections(image)
    target = next((row for row in native.get("bodyTargets", []) if row.get("type") == "BeyondDynamicBone.MagicaManager" and row.get("method") == "SetCustomGameLoop"), None)
    if not target or int(target.get("methodIndex", -1)) != SET_LOOP_METHOD_INDEX:
        raise ContractError("native evidence lacks MagicaManager.SetCustomGameLoop")
    calls = [row for row in target.get("directCalls", []) if _target_va(row) == int(ADD_LOOP_TARGET, 0)]
    if len(calls) != 7:
        raise ContractError(f"expected seven AddPlayerLoop calls, found {len(calls)}")
    offsets = [int(row.get("offset", -1)) for row in calls]
    if offsets != sorted(set(offsets)):
        raise ContractError("AddPlayerLoop calls are duplicated or not in native offset order")
    parameter_row = next((row for row in loop_metadata.get("bodyTargets", []) if row.get("type") == "BeyondDynamicBone.PlayerLoopUtils" and row.get("method") == "AddPlayerLoop"), None)
    if not parameter_row or parameter_row.get("methodIndex") != ADD_LOOP_METHOD_INDEX or parameter_row.get("parameters") != ["method", "playerLoop", "categoryName", "systemName", "last", "before"]:
        raise ContractError("PlayerLoopUtils.AddPlayerLoop signature evidence is incomplete")
    rows = []
    for ordinal, call in enumerate(calls, 1):
        context = call.get("argumentContext") or {}
        writes = context.get("argRegisterWrites") or {}
        category_ref = str((writes.get("r8", {}).get("write") or {}).get("value", ""))
        system_ref = str((writes.get("r9", {}).get("write") or {}).get("value", ""))
        category_va = int(category_ref.rsplit("=>", 1)[1].rstrip("] "), 16) if "=>" in category_ref else None
        system_va = int(system_ref.rsplit("=>", 1)[1].rstrip("] "), 16) if "=>" in system_ref else None
        if category_va is None:
            raise ContractError(f"AddPlayerLoop #{ordinal} lacks category string slot")
        if system_va is None and ordinal == 1:
            system = {
                "status": "unresolved_initialized_static_field",
                "typeInfoSlotVa": "0x18e371250",
                "encodedTypeHandle": "0x20050b0d",
                "candidateValue": "ScriptRunDelayedTasks",
                "candidateEvidence": (
                    "the same metadata literal is directly decoded for ordinal 3; "
                    "the ordinal-1 TypeInfo static field has not yet been mapped "
                    "to that literal"
                ),
            }
        elif system_va is None:
            raise ContractError(f"AddPlayerLoop #{ordinal} lacks system string slot")
        else:
            system = _decode_slot(image, base, sections, metadata, system_va)
        rows.append({
            "ordinal": ordinal,
            "nativeCallOffset": call["offset"],
            "nativeCallVa": f"0x{int(target['methodPointerVa'], 0) + call['offset']:x}",
            "categoryName": _decode_slot(image, base, sections, metadata, category_va),
            "systemName": system,
            "last": _stack_value(context, "0x20"),
            "before": _stack_value(context, "0x28"),
        })
    if any(row["last"] is None or row["before"] is None for row in rows):
        raise ContractError("one or more AddPlayerLoop bool arguments are unresolved")
    return {
        "schema": "endfieldPlayerLoopRecoveryContract.v1",
        "status": "partial_unresolved_first_system_anchor",
        "manager": "BeyondDynamicBone.MagicaManager",
        "method": "SetCustomGameLoop",
        "methodIndex": SET_LOOP_METHOD_INDEX,
        "playerLoopUtility": {"type": "BeyondDynamicBone.PlayerLoopUtils", "method": "AddPlayerLoop", "methodIndex": ADD_LOOP_METHOD_INDEX, "parameters": parameter_row["parameters"]},
        "insertions": rows,
        "evidenceBoundary": "Exact native call order, all category anchors, six of seven system anchors, and all last/before arguments are recovered for the pinned client. Ordinal 1 still reads an unresolved initialized TypeInfo static field and is not published as an exact system anchor.",
    }


def build_contract(game_assembly: Path, metadata_path: Path, native_path: Path, loop_metadata_path: Path) -> dict[str, Any]:
    source = {"gameAssembly": str(game_assembly.resolve()), "globalMetadata": str(metadata_path.resolve()), "nativeEvidence": str(native_path.resolve()), "playerLoopMetadata": str(loop_metadata_path.resolve())}
    failures = []
    for label, path, expected in (("GameAssembly.dll", game_assembly, EXPECTED_GAME_ASSEMBLY_SHA256), ("global-metadata.dat", metadata_path, EXPECTED_METADATA_SHA256)):
        if not path.is_file():
            failures.append(f"missing {label}: {path}")
            continue
        actual = sha256(path)
        if actual != expected:
            failures.append(f"mismatched {label} sha256: expected {expected}, actual {actual}")
    if failures:
        return {"schema": "endfieldPlayerLoopRecoveryContract.v1", "status": "unavailable", "validationFailures": failures, "source": source, "evidenceBoundary": "Native PlayerLoop claims are withheld until the explicit pinned GameAssembly.dll and global-metadata.dat inputs validate."}
    try:
        native = json.loads(native_path.read_text(encoding="utf-8"))
        loop_metadata = json.loads(loop_metadata_path.read_text(encoding="utf-8"))
        recorded_metadata = loop_metadata.get("metadata") or {}
        if recorded_metadata.get("sha256") != EXPECTED_METADATA_SHA256:
            raise ContractError("playerloop metadata evidence is for a different global-metadata.dat")
        contract = recover(native, loop_metadata, game_assembly.read_bytes(), metadata_path.read_bytes())
    except (OSError, ValueError, KeyError, TypeError, AttributeError, IndexError,
            struct.error, ContractError, json.JSONDecodeError) as exc:
        return {"schema": "endfieldPlayerLoopRecoveryContract.v1", "status": "unavailable", "validationFailures": [str(exc)], "source": source, "evidenceBoundary": "Native PlayerLoop claims are withheld when evidence parsing or ABI validation fails."}
    contract["source"] = source
    contract["sourceHashes"] = {"GameAssembly.dll": EXPECTED_GAME_ASSEMBLY_SHA256, "global-metadata.dat": EXPECTED_METADATA_SHA256}
    contract["evidenceHashes"] = {
        "runtime_native.json": sha256(native_path),
        "playerloop_metadata.json": sha256(loop_metadata_path),
    }
    contract["validation"] = {"status": "partial", "gate": "explicit_current_native_inputs", "checks": ["GameAssembly.dll sha256", "global-metadata.dat sha256", "playerloop evidence embedded metadata sha256", "PlayerLoopUtils.AddPlayerLoop signature", "seven ordered native AddPlayerLoop calls", "six direct metadata string-literal system handles", "unique exact last/before stack writes"], "unresolved": ["ordinal 1 systemName TypeInfo static field -> exact string literal"]}
    return contract


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-assembly", type=Path, default=DEFAULT_GAME_ASSEMBLY)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--native-evidence", type=Path, default=DEFAULT_NATIVE)
    parser.add_argument("--playerloop-metadata", type=Path, default=DEFAULT_PLAYERLOOP_METADATA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = build_contract(args.game_assembly, args.metadata, args.native_evidence, args.playerloop_metadata)
    serialized = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    matches = None
    publishable = result["status"] in {
        "validated",
        "partial_unresolved_first_system_anchor",
    }
    if args.check:
        matches = args.output.is_file() and args.output.read_text(encoding="utf-8") == serialized
    elif publishable:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "output": str(args.output),
        "matches": matches,
        "validationFailures": result.get("validationFailures", []),
    }, ensure_ascii=False))
    if args.check:
        return 0 if publishable and matches else 1
    return 0 if publishable else 1


if __name__ == "__main__":
    raise SystemExit(main())
