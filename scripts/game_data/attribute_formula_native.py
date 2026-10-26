"""Re-prove the character attribute formula's native structure on the selected build.

The reviewed claims in ``contracts/attribute_formula_native.json`` name the
attribute calculators, modifier-array readers, other-attribute hooks and the
weapon attribute reader by type and method; ``il2cpp/body_claims.py`` proves
them on whichever build is installed. A consumer publishes the formula only
when every claim holds, so a client update that moves the calculation empties
the result instead of keeping a stale formula.
"""

from __future__ import annotations

import argparse
import json
import hashlib
import struct
import sys
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.corpus_common import atomic_write_text
from scripts.repo_paths import REPO_ROOT
from scripts.game_data.il2cpp.body_claims import BodyIndex, evaluate
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.protocol import field_defaults, native_enum_members

CONTRACT = CONTRACTS_DIR / "attribute_formula_native.json"
SCHEMA = "endfield.attribute-formula-native-claims.v2"


def validate_arithmetic_windows(image, index, windows):
    """Authenticate reviewed normal-path SSE bytes and their external literals."""
    failures = []
    for window in windows:
        symbol = f"{window['type']}.{window['method']}"
        try:
            body = index.body(window["type"], window["method"])
            raw = image.pe.bytes_at_va(body.pointer, window["byteCount"])
            actual = hashlib.sha256(raw).hexdigest()
            if actual != window["sha256"]:
                failures.append({"symbol": symbol, "claim": "arithmeticWindow", "reason": f"expected {window['sha256']}, actual {actual}"})
                continue
            for literal in window.get("float64Literals", []):
                offset = literal["instructionOffset"]
                # REX.R selects XMM8-15 in the inlined conversion path.
                rex = raw[offset + 1:offset + 2] == b"\x44"
                opcode = offset + 1 + int(rex)
                end = opcode + 7
                if (raw[offset:offset + 1] != b"\xf2"
                        or raw[opcode:opcode + 2] not in (b"\x0f\x10", b"\x0f\x58", b"\x0f\x59")
                        or len(raw[opcode + 2:end]) != 5
                        or raw[opcode + 2] & 0xc7 != 0x05):
                    raise ValueError(f"literal +{offset}: expected RIP-relative MOVSD/ADDSD/MULSD")
                target = body.pointer + end + struct.unpack_from("<i", raw, opcode + 3)[0]
                value = struct.unpack("<d", image.pe.bytes_at_va(target, 8))[0]
                if value != literal["value"]:
                    failures.append({"symbol": symbol, "claim": "float64Literal", "reason": f"offset {offset}: expected {literal['value']}, actual {value}"})
        except (ValueError, RuntimeError, KeyError, IndexError) as exc:
            failures.append({"symbol": symbol, "claim": "arithmeticWindow", "reason": str(exc)})
    return failures


def load_attribute_formula(*, gameassembly=None, metadata=None,
                           expected_gameassembly_sha256="", expected_metadata_sha256="") -> dict[str, Any]:
    """Reprove the selected pair; publish a formula only after all gates pass."""
    if (gameassembly is None) != (metadata is None):
        raise ValueError("--gameassembly and --metadata must be supplied together")
    contract, digest = read_reviewed_contract(
        CONTRACT, schema=SCHEMA, label="attribute_formula", status="validated")
    gate = check_installed_native_inputs(
        expected_gameassembly_sha256, expected_metadata_sha256,
        gameassembly=gameassembly, metadata=metadata)
    base = dict(schema=SCHEMA, contractSha256=digest, formula=None, methods=[],
                evidenceBoundary=contract["evidenceBoundary"],
                nativePaths={name: str(value) if value is not None else None
                             for name, value in (
                                 ("gameAssembly", getattr(gate, "gameassembly", gameassembly)),
                                 ("metadata", getattr(gate, "metadata", metadata)))},
                nativeInputs=dict(gameAssemblySha256=getattr(gate, "gameassembly_sha256", ""),
                                  metadataSha256=getattr(gate, "metadata_sha256", "")))

    def rejected(status, check, reason):
        return dict(base, status=status, detail=reason,
                    failures=[dict(check=check, symbol="nativeInputs", reason=reason)])

    if not gate.validated:
        return rejected(gate.status, "installed_native_inputs", gate.detail)
    try:
        image = open_native_image(gate.gameassembly, gate.metadata)
        for label, raw, expected in (
                ("GameAssembly.dll", image.pe.buf, gate.gameassembly_sha256),
                ("global-metadata.dat", image.metadata.buf, gate.metadata_sha256)):
            actual = hashlib.sha256(raw).hexdigest()
            if actual.lower() != expected.lower():
                return rejected("mismatched", "opened_native_inputs",
                                f"{label}: expected {expected}, actual {actual}")
        rows, failures = _evaluate_formula(image, contract)
    except (OSError, ValueError, RuntimeError, KeyError, IndexError, struct.error) as exc:
        return rejected("pendingReview", "attribute_formula_evaluation", str(exc)[:1200])
    after = check_installed_native_inputs(
        gate.gameassembly_sha256, gate.metadata_sha256,
        gameassembly=gate.gameassembly, metadata=gate.metadata)
    if not after.validated:
        return rejected(after.status, "installed_native_inputs_after", after.detail)
    failures = [dict(f, check=f.get("check", f.get("claim", "method_claim"))) for f in failures]
    return dict(base, status="pendingReview" if failures else "validated",
                detail=f"{len(failures)} claim(s) failed" if failures else "",
                formula=None if failures else contract["formula"],
                methods=[] if failures else rows, failures=failures)


def _evaluate_formula(image, contract):
    index = BodyIndex(image)
    rows, failures = evaluate(index, contract["methods"])
    failures.extend(validate_arithmetic_windows(image, index, contract["arithmeticWindows"]))
    defaults = field_defaults(image.metadata)
    for type_name, expected in (contract.get("enumClaims") or {}).items():
        try:
            members = native_enum_members(image.metadata, defaults, image.pe, image.registration, type_name)
        except (RuntimeError, ValueError, KeyError, IndexError) as exc:
            failures.append({"symbol": type_name, "claim": "enumMembers", "reason": str(exc)})
            continue
        actual = {member["name"]: member["id"] for member in members}
        if actual != expected:
            failures.append({"symbol": type_name, "claim": "enumMembers",
                             "reason": f"expected={expected!r} actual={actual!r}"})
    try:
        members = native_enum_members(image.metadata, defaults, image.pe, image.registration, "Beyond.GEnums.AttributeType")
        actual = {member["name"]: member["id"] for member in members}
        for name, expected in contract["attributeIds"].items():
            if actual.get(name) != expected:
                failures.append({"symbol": f"AttributeType.{name}", "claim": "enumId", "reason": f"expected {expected}, actual {actual.get(name)}"})
    except (RuntimeError, ValueError, KeyError, IndexError) as exc:
        failures.append({"symbol": "AttributeType", "claim": "enumId", "reason": str(exc)})
    return rows, failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print the full result as JSON")
    parser.add_argument("--gameassembly", type=Path)
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--expected-gameassembly-sha256", default="")
    parser.add_argument("--expected-metadata-sha256", default="")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if (args.gameassembly is None) != (args.metadata is None):
        parser.error("--gameassembly and --metadata must be supplied together")
    output = args.output.resolve() if args.output else None
    if output and not any(output.is_relative_to(REPO_ROOT / root) for root in ("reports", "scratch", "tmp")):
        parser.error("--output must be under reports/, scratch/ or tmp/")
    result = load_attribute_formula(
        gameassembly=args.gameassembly, metadata=args.metadata,
        expected_gameassembly_sha256=args.expected_gameassembly_sha256,
        expected_metadata_sha256=args.expected_metadata_sha256)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(output, json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"attribute-formula: {result['status']} {result.get('detail') or ''}".rstrip())
        for failure in result["failures"]:
            print(f"  {failure['symbol']}: {failure['reason']}", file=sys.stderr)
    return 0 if result["status"] == "validated" else 1


if __name__ == "__main__":
    main_module = "python -m scripts.game_data.attribute_formula_native"
    if __package__ in (None, ""):
        raise SystemExit(f"run as: {main_module}")
    raise SystemExit(main())
