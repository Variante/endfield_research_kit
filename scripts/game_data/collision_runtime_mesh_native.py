"""Authenticate collision field/window contracts on explicitly selected files.

Build declarations live in the reviewed JSON, never in this algorithm. Missing
or mismatched native inputs return no layout. This validates stored code and
type/field relationships; saved-window readers prove observed bytes. The
default contract is Unity Mesh's held PxBVH34TriangleMesh layout; shape and
actor readers explicitly select their own schema, contract and validator name.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct

from scripts.common import check_installed_native_inputs, sha256_file
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import NATIVE_MAPPER_PATH
from scripts.game_data.il2cpp.protocol import load_native_mapper

SCHEMA = "endfield.collision-runtime-mesh-native-contract.v1"
CONTRACT = CONTRACTS_DIR / "collision_runtime_mesh_native.json"


def _field(contract, path):
    value = contract["layout"]
    for part in path.split("."):
        value = value[part]
    return value


def validate_code_layout(pe, contract, *, schema):
    """Authenticate code windows and operands without inventing a concrete type."""
    if contract.get("schema") != schema or contract.get("status") != "reviewed":
        raise ValueError("contract schema/status")
    windows = {}
    for row in contract["codeWindows"]:
        if row["role"] in windows or not 0 < row["bytes"] <= 4096:
            raise ValueError("duplicate/oversized code window:" + row["role"])
        raw = pe.bytes_at_va(pe.image_base + row["rva"], row["bytes"])
        if hashlib.sha256(raw).hexdigest() != row["sha256"].lower():
            raise ValueError("code window hash:" + row["role"])
        windows[row["role"]] = (row, raw)
    if contract.get("unwindFamilies"):
        from scripts.game_data.il2cpp.unwind_chains import read_exception_directory, UnwindChainIndex
        table, size, raw = read_exception_directory(pe)
        index = UnwindChainIndex(raw, lambda r, n: pe.bytes_at_va(pe.image_base+r, n),
                                 table_rva=table, image_size=size)
        for family in contract["unwindFamilies"]:
            row, _ = windows[family["role"]]
            actual = [part["runtimeTriple"] for part in index.family(family["rva"])["ranges"]]
            if actual != family["runtimeRanges"] or row["rva"] != family["rva"]:
                raise ValueError("unwind family:" + family["role"])
            if (min(a for a, _, _ in actual) != row["rva"] or
                    max(b for _, b, _ in actual) != row["rva"]+row["bytes"]):
                raise ValueError("incomplete unwind window:" + family["role"])
    for probe in contract["probes"]:
        raw = windows[probe["role"]][1]
        value = bytes.fromhex(probe["hex"])
        if not value or probe["offset"] < 0 or raw[probe["offset"]:probe["offset"]+len(value)] != value:
            raise ValueError("instruction probe:" + probe["role"])
    checked = set()
    for operand in contract["fieldOperands"] + contract["targetOperands"]:
        row, raw = windows[operand["role"]]
        prefix = bytes.fromhex(operand["prefix"])
        at, mode = operand["offset"], operand["mode"]
        width = 1 if mode in ("u8", "i8") else 4
        if mode not in ("u8", "i8", "u32", "rip32", "rel32") or not prefix or at < 0 or raw[at:at+len(prefix)] != prefix:
            raise ValueError("operand instruction:" + operand["role"])
        end = at + len(prefix) + width
        if end > len(raw):
            raise ValueError("clipped operand:" + operand["role"])
        value = int.from_bytes(raw[at+len(prefix):end], "little", signed=mode in ("i8", "rip32", "rel32"))
        if mode in ("rip32", "rel32"):
            value += row["rva"] + end
        expected = _field(contract, operand["field"]) if "field" in operand else operand["targetRva"]
        if value != expected:
            raise ValueError(f"operand value:{operand['role']}:expected={expected},actual={value}")
        if "field" in operand:
            checked.add(operand["field"])
    # Every field interpreted by the decoder must have an instruction operand.
    required = {group + "." + name for group, fields in contract["layout"].items() for name in fields}
    if checked != required:
        raise ValueError("incomplete layout operands:" + repr(sorted(required ^ checked)))
    return windows


def validate_layout(pe, contract, *, schema=SCHEMA):
    """Validate typed collision fields, dispatch slots and concrete type names."""
    windows = validate_code_layout(pe, contract, schema=schema)
    for slot in contract["vtableSlots"]:
        expected = pe.image_base + windows[slot["role"]][0]["rva"]
        if pe.u64_at_va(pe.image_base + slot["tableRva"] + slot["slot"]*8) != expected:
            raise ValueError("vtable target:" + slot["role"])
    for dispatch in contract.get("virtualDispatches", []):
        row, raw = windows[dispatch["role"]]
        at = dispatch["offset"]
        if dispatch["width"] not in (1, 4) or not 0 <= dispatch["slot"] <= 4096:
            raise ValueError("virtual dispatch bounds:" + dispatch["role"])
        instruction = bytes.fromhex(dispatch["prefix"])+int(dispatch["slot"]*8).to_bytes(dispatch["width"], "little")
        if at < 0 or raw[at:at+len(instruction)] != instruction:
            raise ValueError("virtual dispatch:" + dispatch["role"])
        if not any(slot["tableRva"] == dispatch["tableRva"] and slot["slot"] == dispatch["slot"] and
                   slot["role"] == dispatch["targetRole"] for slot in contract["vtableSlots"]):
            raise ValueError("unbound virtual dispatch:" + dispatch["role"])
    name = contract["typeName"]
    if pe.bytes_at_va(pe.image_base+name["rva"], len(name["ascii"])+1) != name["ascii"].encode("ascii")+b"\0":
        raise ValueError("concrete type name")
    return contract


def _load(*, gameassembly, metadata, unityplayer, contract_path, schema, validator, validate):
    """Return (layout contract or None, bounded structured gate diagnostics)."""
    audit = dict(status="failed", validator=validator, diagnostics=[])
    try:
        contract = json.loads(contract_path.read_text("utf-8"))
        inputs = contract["nativeInputs"]
        gate = check_installed_native_inputs(inputs["gameAssemblySha256"], inputs["metadataSha256"],
                                            gameassembly=gameassembly, metadata=metadata)
        audit.update(status=gate.status, detail=gate.detail, nativeInputs=inputs)
        if gate.status != "validated":
            return None, audit
        if not unityplayer.is_file():
            audit.update(status="missing", detail="UnityPlayer.dll missing:"+str(unityplayer))
            return None, audit
        actual = sha256_file(unityplayer)
        if actual.lower() != inputs["unityPlayerSha256"].lower():
            audit.update(status="mismatched", detail="UnityPlayer.dll hash differs", actualUnityPlayerSha256=actual)
            return None, audit
        pe = load_native_mapper(NATIVE_MAPPER_PATH).PeImage(unityplayer)
        # Bind the opened buffer as well as the file checks to the selected build.
        if hashlib.sha256(pe.buf).hexdigest() != actual.lower():
            raise ValueError("opened UnityPlayer image differs from selected file")
        validate(pe, contract, schema=schema)
        # Authenticate the image again after reading; do not publish on drift.
        after = check_installed_native_inputs(inputs["gameAssemblySha256"], inputs["metadataSha256"],
                                             gameassembly=gameassembly, metadata=metadata)
        if after.status != "validated" or sha256_file(unityplayer) != actual:
            raise ValueError("selected native inputs changed during validation:"+after.status)
        audit.update(status="validated", codeWindows=len(contract["codeWindows"]), fields=len(contract["fieldOperands"]))
        return contract, audit
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, struct.error) as exc:
        audit.update(status="failed", diagnostics=[dict(check="native_layout", source=str(contract_path), detail=str(exc)[:1200])])
        return None, audit


def load_layout(*, gameassembly: Path, metadata: Path, unityplayer: Path, contract_path: Path = CONTRACT,
                schema=SCHEMA, validator="collision_runtime_mesh_native"):
    """Authenticate a typed field contract on explicitly selected native files."""
    return _load(gameassembly=gameassembly, metadata=metadata, unityplayer=unityplayer,
                 contract_path=contract_path, schema=schema, validator=validator, validate=validate_layout)


def load_code_layout(*, gameassembly: Path, metadata: Path, unityplayer: Path, contract_path: Path,
                     schema, validator, validate=validate_code_layout):
    """Authenticate a code/operand contract with an explicit semantic validator."""
    return _load(gameassembly=gameassembly, metadata=metadata, unityplayer=unityplayer,
                 contract_path=contract_path, schema=schema, validator=validator, validate=validate)
