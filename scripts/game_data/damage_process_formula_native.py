"""Authenticate a reviewed conditional ProcessDamage arithmetic fragment.

The expression is a bounded disassembly reading. Validation authenticates its
selected image, named entries, raw windows and external literals; it does not
prove complete control flow, runtime selection or final settlement.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract

CONTRACT = CONTRACTS_DIR / "damage_process_formula_native.json"
SCHEMA = "endfield.damage-process-formula-native-contract.v1"


def validate_windows(image, contract):
    """Check only declarations in the reviewed contract against opened bytes."""
    failures = []
    for window in contract["windows"]:
        raw = image.pe.bytes_at_va(image.pe.image_base + int(window["rva"], 16), window["byteCount"])
        actual = hashlib.sha256(raw).hexdigest()
        if actual.lower() != window["sha256"].lower():
            failures.append(dict(check="native_window", symbol=window["name"],
                                 expected=window["sha256"], actual=actual))
    for literal in contract["literals"]:
        expected = literal["bits"].lower()
        actual = image.pe.bytes_at_va(image.pe.image_base + int(literal["rva"], 16), len(bytes.fromhex(expected))).hex()
        if actual != expected:
            failures.append(dict(check="native_literal", symbol=literal["rva"],
                                 expected=expected, actual=actual))
    return failures


def load_damage_process_formula(*, gameassembly=None, metadata=None,
                                expected_gameassembly_sha256="", expected_metadata_sha256=""):
    """Withhold the expression on missing inputs, drift or incomplete checks."""
    if (gameassembly is None) != (metadata is None):
        raise ValueError("gameassembly and metadata must be supplied together")
    contract, digest = read_reviewed_contract(CONTRACT, schema=SCHEMA,
                                             label="damage_process_formula", status="reviewed")
    pins = contract["nativeInputs"]
    base = dict(schema=SCHEMA, contractSha256=digest, expression=None, methods=[],
                evidenceBoundary=contract["evidenceBoundary"], conditions=contract["conditions"],
                unresolved=contract["unresolved"], nativeInputs={}, nativePaths={})

    def reject(status, check, detail, failures=None):
        return dict(base, status=status, detail=str(detail)[:1200],
                    failures=failures or [dict(check=check, symbol="nativeInputs", detail=str(detail)[:1200])])

    for name, supplied in (("gameAssemblySha256", expected_gameassembly_sha256),
                            ("metadataSha256", expected_metadata_sha256)):
        if supplied and supplied.lower() != pins[name].lower():
            return reject("mismatched", "requested_native_identity", f"{name}: requested {supplied}, contract {pins[name]}")
    gate = check_installed_native_inputs(pins["gameAssemblySha256"], pins["metadataSha256"],
                                         gameassembly=gameassembly, metadata=metadata)
    base["nativeInputs"] = dict(gameAssemblySha256=getattr(gate, "gameassembly_sha256", ""),
                                metadataSha256=getattr(gate, "metadata_sha256", ""))
    base["nativePaths"] = dict(gameAssembly=str(getattr(gate, "gameassembly", gameassembly)),
                               metadata=str(getattr(gate, "metadata", metadata)))
    if not gate.validated:
        return reject(gate.status, "installed_native_inputs", gate.detail)
    try:
        image = open_native_image(gate.gameassembly, gate.metadata)
        for name, raw in (("gameAssemblySha256", image.pe.buf), ("metadataSha256", image.metadata.buf)):
            actual = hashlib.sha256(raw).hexdigest()
            if actual.lower() != pins[name].lower():
                return reject("mismatched", "opened_native_inputs", f"{name}: expected {pins[name]}, actual {actual}")
        failures = validate_windows(image, contract)
        rows = []
        for spec in contract["methods"]:
            body = image.body_index.body(spec["type"], spec["method"])
            actual = body.pointer - image.pe.image_base
            if actual != int(spec["rva"], 16):
                failures.append(dict(check="named_entry", symbol=body.symbol,
                                     expected=spec["rva"], actual=hex(actual)))
            rows.append(dict(symbol=body.symbol, rva=hex(actual)))
    except (OSError, ValueError, RuntimeError, KeyError, IndexError, struct.error) as exc:
        return reject("pendingReview", "damage_process_formula_evaluation", exc)
    after = check_installed_native_inputs(pins["gameAssemblySha256"], pins["metadataSha256"],
                                          gameassembly=gate.gameassembly, metadata=gate.metadata)
    if not after.validated:
        return reject(after.status, "installed_native_inputs_after", after.detail)
    if failures:
        return reject("pendingReview", "damage_process_formula_evaluation", f"{len(failures)} check(s) failed", failures)
    return dict(base, status="validated", detail="", expression=contract["expression"], methods=rows, failures=[])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gameassembly", type=Path)
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if (args.gameassembly is None) != (args.metadata is None):
        parser.error("--gameassembly and --metadata must be supplied together")
    result = load_damage_process_formula(gameassembly=args.gameassembly, metadata=args.metadata)
    print(json.dumps(result, indent=2) if args.json else f"damage-process-formula: {result['status']} {result['detail']}")
    return 0 if result["status"] == "validated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
