#!/usr/bin/env python3
"""Build the installed-binary contract for CallServer callback header UIDs."""
from __future__ import annotations

import argparse
import importlib.util
import json
import struct
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from common import (  # noqa: E402
    resolve_installed_game_data_root,
    sha256_file as shared_sha256_file,
)

DEFAULT_GAME_ROOT = resolve_installed_game_data_root()
DEFAULT_GAMEASSEMBLY = DEFAULT_GAME_ROOT.parent / "GameAssembly.dll"
DEFAULT_METADATA = (
    DEFAULT_GAME_ROOT / "il2cpp_data" / "Metadata" / "global-metadata.dat"
)
DEFAULT_OUT = (
    ROOT
    / "reports"
    / "mission_order"
    / "levelscript_callserver_callback_contract.json"
)

GAMEASSEMBLY_SHA256 = (
    "0C5573679BC6DEC2D068A14335466DB7CCF20AF9BAE2B983FB9D45677D80FFCE"
)
METADATA_SHA256 = (
    "90C58E26E87C7227A85DDA3FEDF6CE5ED0B06DC1F76E0ABBE75AB20750ADF97E"
)
CALLSERVER_EXECUTE_VA = 0x1845F6000
CALLSERVER_OUTPUT_SETTER_VA = 0x1841ADEB0
CALLSERVER_CALLBACK_COLD_VA = 0x1852F012A
ACTIONBASE_SET_WAIT_VA = 0x1875F1180


def sha256_file(path: Path) -> str:
    return shared_sha256_file(path).upper()


def load_pe_image_type() -> Any:
    helper = ROOT / "tools" / "endfield-il2cpp" / "map_body_targets_to_gameassembly.py"
    spec = importlib.util.spec_from_file_location(
        "endfield_callserver_pe_helper",
        helper,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load PE helper: {helper}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.PeImage


def rel32_target(pe: Any, instruction_va: int) -> int:
    raw = pe.bytes_at_va(instruction_va, 5)
    if len(raw) != 5 or raw[0] != 0xE8:
        raise ValueError(
            f"expected E8 rel32 call at 0x{instruction_va:x}; actual={raw.hex()}"
        )
    return instruction_va + 5 + struct.unpack_from("<i", raw, 1)[0]


def rel32_branch_target(pe: Any, instruction_va: int, opcode: bytes) -> int:
    raw = pe.bytes_at_va(instruction_va, len(opcode) + 4)
    if len(raw) != len(opcode) + 4 or raw[: len(opcode)] != opcode:
        raise ValueError(
            f"expected {opcode.hex()} rel32 branch at 0x{instruction_va:x}; "
            f"actual={raw.hex()}"
        )
    return instruction_va + len(raw) + struct.unpack_from("<i", raw, len(opcode))[0]


def expect_bytes(pe: Any, va: int, expected: bytes, label: str) -> dict[str, str]:
    actual = pe.bytes_at_va(va, len(expected))
    if actual != expected:
        raise ValueError(
            f"{label} byte gate failed at 0x{va:x}; "
            f"expected={expected.hex()} actual={actual.hex()}"
        )
    return {
        "label": label,
        "va": f"0x{va:x}",
        "bytes": expected.hex(" "),
    }


def build_contract(gameassembly: Path, metadata: Path) -> dict[str, Any]:
    gameassembly = gameassembly.resolve()
    metadata = metadata.resolve()
    game_hash = sha256_file(gameassembly)
    metadata_hash = sha256_file(metadata)
    failures: list[dict[str, str]] = []
    if game_hash != GAMEASSEMBLY_SHA256:
        failures.append({
            "gate": "gameassembly_sha256",
            "expected": GAMEASSEMBLY_SHA256,
            "actual": game_hash,
        })
    if metadata_hash != METADATA_SHA256:
        failures.append({
            "gate": "global_metadata_sha256",
            "expected": METADATA_SHA256,
            "actual": metadata_hash,
        })
    if failures:
        raise ValueError(json.dumps(failures, indent=2))

    PeImage = load_pe_image_type()
    pe = PeImage(gameassembly)
    byte_gates = [
        expect_bytes(
            pe,
            CALLSERVER_OUTPUT_SETTER_VA + 0x1C,
            bytes.fromhex("48 89 98 d8 00 00 00"),
            "MemoryPack setter stores _callClientOutputUIDs at this+0xd8",
        ),
        expect_bytes(
            pe,
            CALLSERVER_EXECUTE_VA + 0x148,
            bytes.fromhex("48 8b 8b d8 00 00 00"),
            "CallServer.Execute reads _callClientOutputUIDs from this+0xd8",
        ),
        expect_bytes(
            pe,
            CALLSERVER_CALLBACK_COLD_VA,
            bytes.fromhex("48 8b 93 d8 00 00 00 45 33 c0 48 8b cb e8"),
            "callback cold branch forwards the same list as argument two",
        ),
        expect_bytes(
            pe,
            ACTIONBASE_SET_WAIT_VA + 0x20,
            bytes.fromhex("48 8d 8b 80 00 00 00 48 89 bb 80 00 00 00"),
            "ActionBase stores the header UID wait list at this+0x80",
        ),
    ]
    cold_target = rel32_branch_target(
        pe,
        CALLSERVER_EXECUTE_VA + 0x156,
        bytes.fromhex("0f 8f"),
    )
    if cold_target != CALLSERVER_CALLBACK_COLD_VA:
        raise ValueError(
            "CallServer callback cold-branch target changed: "
            f"expected=0x{CALLSERVER_CALLBACK_COLD_VA:x} actual=0x{cold_target:x}"
        )
    set_wait_target = rel32_target(pe, CALLSERVER_CALLBACK_COLD_VA + 0xD)
    if set_wait_target != ACTIONBASE_SET_WAIT_VA:
        raise ValueError(
            "CallServer callback setter target changed: "
            f"expected=0x{ACTIONBASE_SET_WAIT_VA:x} actual=0x{set_wait_target:x}"
        )

    return {
        "schema": "callServerCallbackNativeContract.v1",
        "status": "validated",
        "sources": {
            "gameAssemblySha256": game_hash,
            "globalMetadataSha256": metadata_hash,
        },
        "callServer": {
            "type": "Beyond.Gameplay.Actions.CallServer",
            "typeToken": "0x02001861",
            "executeMethodToken": "0x06008f04",
            "executeMethodVa": f"0x{CALLSERVER_EXECUTE_VA:x}",
            "outputField": "_callClientOutputUIDs",
            "outputFieldToken": "0x040069fe",
            "outputFieldOffset": "this+0xd8",
            "memoryPackSetterMethodToken": "0x0600c1e1",
            "memoryPackSetterMethodVa": f"0x{CALLSERVER_OUTPUT_SETTER_VA:x}",
            "callbackColdBranchVa": f"0x{CALLSERVER_CALLBACK_COLD_VA:x}",
        },
        "actionBase": {
            "type": "Beyond.Gameplay.Actions.ActionBase",
            "typeToken": "0x0200124e",
            "setWaitMethod": "SetResultWaitForPossibleSubExecutor",
            "setWaitMethodToken": "0x06007e87",
            "setWaitMethodVa": f"0x{ACTIONBASE_SET_WAIT_VA:x}",
            "waitHeaderUidListOffset": "this+0x80",
        },
        "validation": {
            "byteGates": byte_gates,
            "callbackColdBranchTarget": f"0x{cold_target:x}",
            "setWaitCallTarget": f"0x{set_wait_target:x}",
            "validationFailures": [],
        },
        "evidenceBoundary": (
            "The installed binary proves that non-empty CallServer output strings "
            "are possible sub-executor header UIDs. They define callback control "
            "topology inside one LevelScript; they do not identify a mission owner "
            "or imply that every possible callback executes."
        ),
        "usesOcrOrManualOrder": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gameassembly", type=Path, default=DEFAULT_GAMEASSEMBLY)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    contract = build_contract(args.gameassembly, args.metadata)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(contract, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        "CallServer callback native contract validated: "
        f"{args.out} ({len(contract['validation']['byteGates'])} byte gates)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
