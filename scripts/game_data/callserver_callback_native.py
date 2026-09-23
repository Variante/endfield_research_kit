"""Load, gate and regenerate the reviewed CallServer callback native contract.

The contract proves that a serialized ``CallServer._callClientOutputUIDs`` list
reaches ``ActionBase.SetResultWaitForPossibleSubExecutor`` as the wait list of
possible sub-executor header UIDs. Four byte gates carry that proof: the
MemoryPack setter stores the list, ``CallServer.Execute`` reads it, a callback
branch of ``Execute`` forwards it as argument two, and the callee stores it in
the ``ActionBase`` wait list.

Only names survive a client update, so ``--regenerate`` re-derives everything
else from the installed build: field offsets from MetadataRegistration, bodies
from ``il2cpp.method_resolver``, and each gate by searching those bodies for
the instruction that carries the claim. A claim it cannot find again is a
failed regeneration, not a stale row.

Run as: python -m scripts.game_data.callserver_callback_native --regenerate [--write]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import sys
from pathlib import Path
from typing import Any

from scripts.common import (
    NATIVE_EVIDENCE_MISSING,
    NATIVE_EVIDENCE_MISMATCHED,
    NATIVE_EVIDENCE_VALIDATED,
    check_installed_native_inputs,
)
from scripts.common import repo_path as _source_file
from scripts.game_data.contracts import CONTRACTS_DIR


SCHEMA = "callServerCallbackNativeContract.v1"
AUDIT_SCHEMA = "callServerCallbackNativeContractAudit.v1"
DEFAULT_CONTRACT = CONTRACTS_DIR / "callserver_callback.json"

CALL_SERVER_TYPE = "Beyond.Gameplay.Actions.CallServer"
ACTION_BASE_TYPE = "Beyond.Gameplay.Actions.ActionBase"
MEMORYPACK_TYPE = "Beyond.MemoryPack.Beyond_Gameplay_Actions_CallServerForMemoryPack"
OUTPUT_FIELD = "_callClientOutputUIDs"
WAIT_LIST_FIELD = "m_waitForExtraUidList"
SET_WAIT_METHOD = "SetResultWaitForPossibleSubExecutor"
MEMORYPACK_SETTER = f"set___{OUTPUT_FIELD}__"


def load_callserver_callback_contract(
    contract_path: Path = DEFAULT_CONTRACT,
    *,
    gameassembly: Path | None = None,
    metadata: Path | None = None,
) -> dict[str, Any]:
    """Return the contract only when it is well formed and its build is installed."""

    path = Path(contract_path)
    source_file = _source_file(path)
    failures: list[dict[str, Any]] = []

    def reject(gate: str, expected: Any, actual: Any) -> None:
        failures.append({
            "validator": "callServerCallbackNativeContract",
            "gate": gate,
            "sourceFile": source_file,
            "expected": expected,
            "actual": actual,
        })

    try:
        raw = path.read_bytes()
        contract = json.loads(raw.decode("utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        reject("read_valid_json", {"readableJsonObject": True}, str(error)[:400])
        return {
            "schema": AUDIT_SCHEMA,
            "status": (
                NATIVE_EVIDENCE_MISSING
                if isinstance(error, OSError)
                else NATIVE_EVIDENCE_MISMATCHED
            ),
            "sourceFile": source_file,
            "sourceSha256": "",
            "nativeContract": {},
            "validationFailures": failures,
            "usesOcrOrManualOrder": False,
        }

    source_sha256 = hashlib.sha256(raw).hexdigest().upper()
    if not isinstance(contract, dict):
        reject("contract_object", {"type": "object"}, {"type": type(contract).__name__})
        contract = {}
    sources = contract.get("sources") if isinstance(contract.get("sources"), dict) else {}
    validation = contract.get("validation") if isinstance(contract.get("validation"), dict) else {}
    for gate, expected, actual in (
        ("schema", SCHEMA, contract.get("schema")),
        ("status", "validated", contract.get("status")),
        ("byte_gate_count", 4, len(validation.get("byteGates") or [])),
        ("native_validation_failures", [], validation.get("validationFailures")),
    ):
        if actual != expected:
            reject(gate, expected, actual)

    native = check_installed_native_inputs(
        str(sources.get("gameAssemblySha256") or ""),
        str(sources.get("globalMetadataSha256") or ""),
        gameassembly=gameassembly,
        metadata=metadata,
    )
    if native.status != NATIVE_EVIDENCE_VALIDATED:
        reject(
            "installed_native_inputs",
            {"status": NATIVE_EVIDENCE_VALIDATED},
            {"status": native.status, "detail": native.detail},
        )

    status = NATIVE_EVIDENCE_VALIDATED
    if failures:
        status = (
            native.status
            if native.status != NATIVE_EVIDENCE_VALIDATED
            else NATIVE_EVIDENCE_MISMATCHED
        )
    return {
        "schema": AUDIT_SCHEMA,
        "status": status,
        "sourceFile": source_file,
        "sourceSha256": source_sha256,
        "nativeContract": contract if not failures else {},
        "validationFailures": failures,
        "usesOcrOrManualOrder": False,
    }


# -- regeneration --------------------------------------------------------------


def _disp32(offset: int) -> bytes:
    return struct.pack("<I", offset)


def _rel32_target(data: bytes, base_va: int, position: int, width: int) -> int:
    return base_va + position + width + struct.unpack_from("<i", data, position + width - 4)[0]


def regenerate(contract: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Re-derive every build-specific row from names; return (contract, refusals)."""
    from scripts.game_data.il2cpp import protocol as il2cpp
    from scripts.game_data.il2cpp.method_resolver import MethodSpec, open_resolver
    from scripts.game_data.il2cpp.native_image import open_native_image

    gate = check_installed_native_inputs()
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        return contract, [f"installed_native_inputs:{gate.status}:{gate.detail}"]
    image = open_native_image(gate.gameassembly, gate.metadata)
    resolver, _receipt = open_resolver(gameassembly=gate.gameassembly, metadata=gate.metadata)
    extents = image.mapper.pdata_function_extents(image.pe)
    refused: list[str] = []

    def method(type_name: str, name: str) -> dict[str, Any]:
        row = resolver.resolve(MethodSpec(type_name, name))
        matches = row.get("matches") or []
        if row.get("status") != "exact" or len(matches) != 1 or matches[0].get("bodyStatus") != "resolved":
            raise LookupError(f"{type_name}.{name}:{row.get('status')}:{len(matches)}")
        match = matches[0]
        va = int(match["methodPointerVa"], 16)
        return {**match, "va": va, "body": image.pe.bytes_at_va(va, match["bodyExtent"])}

    def offsets(type_name: str) -> dict[str, int]:
        index = resolver.type_index(type_name)
        if index is None:
            raise LookupError(f"type-missing:{type_name}")
        return il2cpp.runtime_type_field_offsets(image.metadata, image.pe, image.registration, index)

    def type_token(type_name: str) -> str:
        return f"0x{image.metadata.types[resolver.type_index(type_name)].token:08x}"

    try:
        output_offset = offsets(CALL_SERVER_TYPE)[OUTPUT_FIELD]
        wait_offset = offsets(ACTION_BASE_TYPE)[WAIT_LIST_FIELD]
        execute = method(CALL_SERVER_TYPE, "Execute")
        setter = method(MEMORYPACK_TYPE, MEMORYPACK_SETTER)
        set_wait = method(ACTION_BASE_TYPE, SET_WAIT_METHOD)
    except (LookupError, KeyError, RuntimeError) as error:
        return contract, [f"identity:{error}"]
    out_disp = re.escape(_disp32(output_offset))
    wait_disp = re.escape(_disp32(wait_offset))

    def first(pattern: bytes, data: bytes) -> re.Match[bytes] | None:
        return re.search(pattern, data, re.S)

    gates: list[dict[str, Any]] = []

    store = first(rb"[\x48\x4c]\x89[\x80-\xbf]" + out_disp, setter["body"])
    if store is None:
        refused.append(f"setter-store:{MEMORYPACK_SETTER} does not store this+0x{output_offset:x}")
    else:
        gates.append({
            "label": f"MemoryPack setter stores {OUTPUT_FIELD} at this+0x{output_offset:x}",
            "va": f"0x{setter['va'] + store.start():x}",
            "bytes": store.group(0).hex(" "),
        })

    read = first(rb"[\x48\x4c]\x8b[\x80-\xbf]" + out_disp, execute["body"])
    if read is None:
        refused.append(f"execute-read:CallServer.Execute does not read this+0x{output_offset:x}")
    else:
        gates.append({
            "label": f"CallServer.Execute reads {OUTPUT_FIELD} from this+0x{output_offset:x}",
            "va": f"0x{execute['va'] + read.start():x}",
            "bytes": read.group(0).hex(" "),
        })

    # The callback branch may sit in Execute or in a split-off fragment it
    # branches to; follow Execute's rel32 jumps into .pdata fragments once.
    regions = [(execute["va"], execute["body"])]
    body = execute["body"]
    for position in range(len(body) - 6):
        target = None
        if body[position] == 0xE9:
            target = _rel32_target(body, execute["va"], position, 5)
        elif body[position] == 0x0F and 0x80 <= body[position + 1] <= 0x8F:
            target = _rel32_target(body, execute["va"], position, 6)
        if target is not None and target in extents and not execute["va"] <= target < execute["va"] + len(body):
            regions.append((target, image.pe.bytes_at_va(target, extents[target] - target)))
    forward = None
    for base, data in regions:
        for hit in re.finditer(rb"\x48\x8b[\x90-\x97]" + out_disp + rb"(?:.{0,12}?)\xe8", data, re.S):
            call_at = hit.end() - 1
            if _rel32_target(data, base, call_at, 5) == set_wait["va"]:
                forward = (base, hit)
                break
        if forward:
            break
    if forward is None:
        refused.append(f"callback-forward:no branch passes this+0x{output_offset:x} to {SET_WAIT_METHOD}")
    else:
        base, hit = forward
        gates.append({
            "label": "callback branch forwards the same list as argument two",
            "va": f"0x{base + hit.start():x}",
            "bytes": hit.group(0).hex(" "),
        })

    wait_store = first(rb"[\x48\x4c]\x89[\x80-\xbf]" + wait_disp, set_wait["body"])
    if wait_store is None:
        refused.append(f"wait-store:{SET_WAIT_METHOD} does not store this+0x{wait_offset:x}")
    else:
        gates.append({
            "label": f"ActionBase stores the header UID wait list at this+0x{wait_offset:x}",
            "va": f"0x{set_wait['va'] + wait_store.start():x}",
            "bytes": wait_store.group(0).hex(" "),
        })

    regenerated = {
        "schema": SCHEMA,
        "status": "validated",
        "sources": {
            "gameAssemblySha256": gate.gameassembly_sha256.upper(),
            "globalMetadataSha256": gate.metadata_sha256.upper(),
        },
        "callServer": {
            "type": CALL_SERVER_TYPE,
            "typeToken": type_token(CALL_SERVER_TYPE),
            "executeMethodToken": execute["token"],
            "executeMethodVa": f"0x{execute['va']:x}",
            "outputField": OUTPUT_FIELD,
            "outputFieldOffset": f"this+0x{output_offset:x}",
            "memoryPackSetter": f"{MEMORYPACK_TYPE}.{MEMORYPACK_SETTER}",
            "memoryPackSetterMethodToken": setter["token"],
            "memoryPackSetterMethodVa": f"0x{setter['va']:x}",
            "callbackBranchVa": gates[2]["va"] if len(gates) == 4 else None,
        },
        "actionBase": {
            "type": ACTION_BASE_TYPE,
            "typeToken": type_token(ACTION_BASE_TYPE),
            "setWaitMethod": SET_WAIT_METHOD,
            "setWaitMethodToken": set_wait["token"],
            "setWaitMethodVa": f"0x{set_wait['va']:x}",
            "waitListField": WAIT_LIST_FIELD,
            "waitHeaderUidListOffset": f"this+0x{wait_offset:x}",
        },
        "validation": {
            "byteGates": gates,
            "setWaitCallTarget": f"0x{set_wait['va']:x}",
            "validationFailures": refused,
        },
        "evidenceBoundary": contract.get("evidenceBoundary"),
        "usesOcrOrManualOrder": False,
    }
    return regenerated, refused


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--regenerate", action="store_true")
    parser.add_argument("--write", action="store_true", help="write the regenerated contract")
    args = parser.parse_args(argv)
    if not args.regenerate:
        audit = load_callserver_callback_contract(args.contract)
        print(json.dumps({"status": audit["status"], "failures": audit["validationFailures"]}, indent=1))
        return 0 if audit["status"] == NATIVE_EVIDENCE_VALIDATED else 1
    contract = json.loads(args.contract.read_bytes())
    regenerated, refused = regenerate(contract)
    print(json.dumps({"refused": refused, "byteGates": len(regenerated["validation"]["byteGates"])}, indent=1))
    if refused:
        return 1
    if args.write:
        args.contract.write_bytes((json.dumps(regenerated, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    if not __package__:
        raise SystemExit("Run as: python -m scripts.game_data.callserver_callback_native")
    sys.exit(main())


__all__ = ["load_callserver_callback_contract", "regenerate", "SCHEMA"]
