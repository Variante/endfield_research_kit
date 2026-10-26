"""Authenticate reviewed Buff healing settlement windows on a selected build.

The contract describes conditional compiled paths, not admitted live captures.
All build-specific declarations belong in the contract. Byte authentication
does not turn the reviewed disassembly into a whole-method CFG proof.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.protocol import field_defaults, native_enum_members

CONTRACT = CONTRACTS_DIR / "buff_healing_settlement_native.json"
SCHEMA = "endfield.buff-healing-settlement-native-contract.v2"


def validate_windows(image, contract):
    """Return bounded, actionable drift diagnostics without publishing formulas."""
    failures = []

    def check(name, expected, actual):
        if expected != actual:
            failures.append({"check": name, "expected": expected, "actual": actual})

    for window in contract["codeWindows"]:
        name = window["name"]
        raw = image.pe.bytes_at_va(image.pe.image_base + window["rva"], window["byteCount"])
        check(name + ":bytes", window["sha256"], hashlib.sha256(raw).hexdigest())
        if "methodIndex" in window:
            method = image.metadata.methods[window["methodIndex"]]
            owner = image.metadata.types[method.declaring_type]
            check(name + ":owner", window["type"], image.metadata.type_full_name(owner))
            check(name + ":method", window["method"], image.metadata.string(method.name_index))
            check(name + ":entry", window["rva"], image.method_pointer_va(method) - image.pe.image_base)
    for literal in contract["literals"]:
        expected = bytes.fromhex(literal["bytesHex"])
        actual = image.pe.bytes_at_va(image.pe.image_base + literal["rva"], len(expected))
        check(f"literal:{literal['rva']}", expected.hex(), actual.hex())
    snapshot = contract["interpretation"].get("attributeSnapshots")
    if snapshot:
        windows = {r["name"]: r for r in contract["codeWindows"]}
        owner = windows[snapshot["snapshotMethod"]]
        getter = windows[snapshot["getter"]]
        for copy in snapshot["copies"]:
            end = copy["returnRva"]
            raw = image.pe.bytes_at_va(image.pe.image_base + end - 5, 5)
            check(copy["side"] + ":getter-call", "e8", raw[:1].hex())
            check(copy["side"] + ":getter-target", getter["rva"], end + struct.unpack_from("<i", raw, 1)[0])
            post = copy["postReturnWindow"]
            check(copy["side"] + ":post-return-start", end, post["rva"])
            check(copy["side"] + ":copy-window-owned", True,
                  owner["rva"] <= end - 5 < post["rva"] + post["byteCount"] <= owner["rva"] + owner["byteCount"])
            raw = image.pe.bytes_at_va(image.pe.image_base + post["rva"], post["byteCount"])
            check(copy["side"] + ":copy-window-bytes", post["sha256"], hashlib.sha256(raw).hexdigest())
            encoded = bytes.fromhex(post["copyInstructionBytes"])
            check(copy["side"] + ":copy-instruction-owned", True,
                  post["rva"] <= post["copyInstructionRva"] and
                  post["copyInstructionRva"] + len(encoded) == post["rva"] + post["byteCount"])
            actual = image.pe.bytes_at_va(image.pe.image_base + post["copyInstructionRva"], len(encoded))
            check(copy["side"] + ":copy-instruction", encoded.hex(), actual.hex())
    population = contract["interpretation"].get("eventContextPopulationSites")
    if population:
        windows = {r["name"]: r for r in contract["codeWindows"]}
        owner = windows[population["caller"]]
        getter = windows[population["getter"]]
        dispatcher = windows["Beyond.Gameplay.Core.AbilitySystem.TriggerEvent"]
        events = contract["enumMembers"]["Beyond.Gameplay.Core.AbilitySystem+Event"]
        for site in population["sites"]:
            for call, target, label in ((site["returnRva"] - 5, getter["rva"], "population"),
                                         (site["dispatchCallRva"], dispatcher["rva"], "dispatch")):
                raw = image.pe.bytes_at_va(image.pe.image_base + call, 5)
                check(site["event"] + ":" + label + "-owned", True,
                      owner["rva"] <= call < call + 5 <= owner["rva"] + owner["byteCount"])
                check(site["event"] + ":" + label + "-opcode", "e8", raw[:1].hex())
                check(site["event"] + ":" + label + "-target", target, call + 5 + struct.unpack_from("<i", raw, 1)[0])
            raw = image.pe.bytes_at_va(image.pe.image_base + site["eventArgumentRva"], 5)
            check(site["event"] + ":event-argument-owned", True,
                  owner["rva"] <= site["eventArgumentRva"] < site["eventArgumentRva"] + 5 <= site["dispatchCallRva"])
            check(site["event"] + ":event-argument", (b'\xba' + struct.pack('<I', events[site["event"]])).hex(), raw.hex())
    index = BodyIndex(image)
    for field in contract["fields"]:
        check(field["field"] + ":offset", field["metadataOffset"], index.field_offset(field["field"]))
    defaults = field_defaults(image.metadata)
    for name, expected in contract["enumMembers"].items():
        members = native_enum_members(image.metadata, defaults, image.pe, image.registration, name)
        actual = {r["name"]: r["id"] for r in members}
        for member, value in expected.items():
            check(name + "." + member, value, actual.get(member))
    return failures


def load_healing_settlement(*, gameassembly: Path | None = None, metadata: Path | None = None):
    contract, _ = read_reviewed_contract(CONTRACT, schema=SCHEMA, status="reviewed",
                                         label="buff_healing_settlement")
    pins = contract["nativeInputs"]
    gate = check_installed_native_inputs(pins["gameAssemblySha256"], pins["metadataSha256"],
                                         gameassembly=gameassembly, metadata=metadata)
    result = {"schema": "endfield.buff-healing-settlement-audit.v1", "status": gate.status,
              "detail": gate.detail, "contract": CONTRACT.as_posix(), "failures": [],
              "interpretation": {}, "evidenceBoundary": contract["evidenceBoundary"],
              "runtimeMeaningExact": False}
    if not gate.validated:
        return result
    try:
        image = open_native_image(gate.gameassembly, gate.metadata)
        failures = validate_windows(image, contract)
    except (ValueError, RuntimeError, KeyError, IndexError) as exc:
        failures = [{"check": "native-window-validation", "actual": str(exc)}]
    after = check_installed_native_inputs(pins["gameAssemblySha256"], pins["metadataSha256"],
                                          gameassembly=gate.gameassembly, metadata=gate.metadata)
    result["nativeInputs"] = pins
    result["failures"] = [{**f, "validator": "buff_healing_settlement", "source": CONTRACT.as_posix(),
                           "nativeInputs": pins} for f in failures]
    if not after.validated:
        result.update(status=after.status, detail=after.detail)
        result["failures"].append({"validator": "buff_healing_settlement",
            "check": "native-inputs-after", "source": str(gate.gameassembly),
            "expected": pins, "actual": after.detail})
    elif failures:
        result.update(status="pendingReview", detail=f"{len(failures)} failed check(s)")
    else:
        result.update(status="validated", interpretation=contract["interpretation"])
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gameassembly", type=Path)
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    from scripts.repo_paths import REPO_ROOT
    target = args.output.resolve()
    if not any(target.is_relative_to(REPO_ROOT / p) for p in ("reports", "scratch", "tmp")):
        parser.error("--output must be under reports/, scratch/ or tmp/")
    result = load_healing_settlement(gameassembly=args.gameassembly, metadata=args.metadata)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes((json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode())
    print(json.dumps({k: result[k] for k in ("status", "detail", "failures")}, ensure_ascii=False))
    return 0 if result["status"] == "validated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
