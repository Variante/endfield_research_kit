"""Authenticate the selected ResourceGroup LogicState query gate offline.

The registered ``_FillTargetStateGroupSet`` unpatched body calls the checked
``get_LogicState`` getter, then tests its returned UInt32 against the named
incoming UInt32 ``mask`` parameter. Zero intersection takes a forward branch
past the subsequent Group getter to the loop advance. This proves a selected
query filter, not the activation predicate of every resource consumer.

The explicit selected IL2CPP inputs, generated resource layout, caller
signature, complete main body window and argument/return handoff all gate the
result. The anonymous descriptor-source helper and iFix branches remain open.
No export, corpus receipt or live process is read by this native-only audit.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.dynamic_resource_comp_native import validate_native_layout
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.protocol import runtime_type_name
from scripts.repo_paths import REPO_ROOT

CONTRACT = CONTRACTS_DIR / "dynamic_resource_state_native.json"
SCHEMA = "endfield.dynamic-resource-state-native-contract.v1"
DEFAULT_OUTPUT = REPO_ROOT / "reports/dynamic_streaming/resource_state_native_latest.json"


class DynamicResourceStateError(ValueError):
    """The selected native inputs or reviewed scalar handoff differs."""


def _relative_call(raw: bytes, offset: int, base: int, target: int, label: str) -> None:
    if not 0 <= offset <= len(raw) - 5 or raw[offset] != 0xE8:
        raise DynamicResourceStateError(f"{label}:expected direct rel32 call at +{offset:#x}")
    actual = base + offset + 5 + struct.unpack_from("<i", raw, offset + 1)[0]
    if actual != target:
        raise DynamicResourceStateError(f"{label}:expected target={target:#x} actual={actual:#x}")


def _mask_gate(raw: bytes, spec: dict[str, Any], *, base: int,
               logic_getter: int, group_getter: int, parameter_position: int) -> dict[str, Any]:
    """Prove the bounded Win64 caller-stack and getter-result handoff.

    This family has a saved entry RSP in RAX and an RBP frame based on RAX.
    Parameters beyond the three instance-register arguments begin at entry
    RSP+0x28. The selected test must address that exact incoming argument.
    """
    frame = int(spec["frameSetupOffset"])
    call = int(spec["getterCallOffset"])
    later = int(spec["laterGroupCallOffset"])
    target = int(spec["zeroBranchTargetOffset"])
    if parameter_position < 3 or raw[:3] != b"\x48\x8b\xc4":
        raise DynamicResourceStateError("mask-argument:expected instance stack argument and saved entry RSP")
    if not 3 <= frame <= len(raw) - 4 or raw[frame:frame + 3] != b"\x48\x8d\x68":
        raise DynamicResourceStateError("mask-argument:expected RBP frame from saved entry RSP")
    frame_delta = struct.unpack_from("<b", raw, frame + 3)[0]
    entry_offset = 0x28 + (parameter_position - 3) * 8
    _relative_call(raw, call, base, logic_getter, "LogicState-getter")
    # mov [rbp+local],eax; test [rbp+argument],eax; je next-iteration
    after = call + 5
    if (after + 8 > len(raw) or raw[after:after + 2] != b"\x89\x45"
            or raw[after + 3:after + 5] != b"\x85\x45" or raw[after + 6] != 0x74):
        raise DynamicResourceStateError("LogicState-mask:expected returned EAX store, direct TEST and JE")
    local_delta = struct.unpack_from("<b", raw, after + 2)[0]
    test_delta = struct.unpack_from("<b", raw, after + 5)[0]
    actual_entry = frame_delta + test_delta
    if actual_entry != entry_offset or local_delta >= 0:
        raise DynamicResourceStateError(
            f"mask-argument:expected entryRSP+{entry_offset:#x} actual={actual_entry:#x}; local={local_delta}"
        )
    branch_target = after + 8 + struct.unpack_from("<b", raw, after + 7)[0]
    if branch_target != target or not after + 8 <= later < target <= len(raw) - 2:
        raise DynamicResourceStateError(
            f"LogicState-mask:expected forward skip={target:#x} actual={branch_target:#x}"
        )
    _relative_call(raw, later, base, group_getter, "subsequent-Group-getter")
    if raw[target:target + 2] != b"\xff\xc3":
        raise DynamicResourceStateError("LogicState-mask:expected next-iteration cursor increment")
    return {
        "scalar": spec["resourceScalar"], "parameter": spec["maskParameter"],
        "predicate": "(LogicState & mask) != 0",
        "zeroIntersection": "branches past subsequent Group getter to loop advance",
        "maskEntryStackOffset": entry_offset,
    }


def _runtime_type(image: Any, type_index: int) -> str:
    if not 0 <= type_index < image.registration["typesCount"]:
        raise DynamicResourceStateError(f"signature:type-index={type_index}")
    pointer = image.pe.u64_at_va(int(image.registration["types"], 16) + type_index * 8)
    return runtime_type_name(image.pe, image.metadata, pointer)


def audit(*, gameassembly: Path, metadata: Path) -> dict[str, Any]:
    contract, digest = read_reviewed_contract(
        CONTRACT, schema=SCHEMA, label="dynamic_resource_state", status="validated",
    )
    inputs = contract["nativeInputs"]
    gate = check_installed_native_inputs(
        inputs["gameAssemblySha256"], inputs["metadataSha256"],
        gameassembly=gameassembly, metadata=metadata,
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise DynamicResourceStateError(f"installed_native_inputs:{gate.status}:{gate.detail}")
    layout, _, _, _, source, _ = validate_native_layout(gameassembly, metadata)
    if source["nativeInputs"] != inputs:
        raise DynamicResourceStateError("resource-layout:selected native inputs differ")
    image = open_native_image(gameassembly, metadata)
    selected = contract["method"]
    index = image.validate_method_row(
        [selected["index"], selected["type"], selected["method"], selected["rva"]],
        label="dynamic_resource_state",
    )
    method = image.metadata.methods[index]
    parameters = [{"name": image.metadata.string(p.name_index), "type": _runtime_type(image, p.type_index)}
                  for p in image.metadata.parameters_for(method)]
    if (method.flags & 0x10 or parameters != selected["parameters"]
            or _runtime_type(image, method.return_type) != selected["returnType"]):
        raise DynamicResourceStateError(f"caller-signature:expected={selected['parameters']!r} actual={parameters!r}")
    spec = contract["maskGate"]
    matches = [position for position, p in enumerate(parameters)
               if p == {"name": spec["maskParameter"], "type": "uint"}]
    if len(matches) != 1 or spec["resourceScalar"] != "LogicState":
        raise DynamicResourceStateError("mask-argument:named UInt32 parameter or scalar differs")
    window = contract["window"]
    if int(window["rva"]) != int(selected["rva"]) or not 0 < int(window["length"]) <= 4096:
        raise DynamicResourceStateError("caller-window:invalid selected boundary")
    base = image.pe.image_base + int(window["rva"])
    raw = image.pe.bytes_at_va(base, int(window["length"]))
    actual = hashlib.sha256(raw).hexdigest().upper()
    if actual != window["sha256"]:
        raise DynamicResourceStateError(f"caller-window:expected={window['sha256']} actual={actual}")
    fields = {row["name"]: row for row in layout["resourceGroup"]["fields"]}
    getter = lambda name: image.method_pointer_va(image.metadata.methods[int(fields[name]["getterMethodIndex"])])
    rule = _mask_gate(raw, spec, base=base, logic_getter=getter("LogicState"),
                      group_getter=getter("Group"), parameter_position=matches[0])
    return {
        "format": "endfield.dynamic-resource-state-native-audit.v1", "status": "validated",
        "contractSha256": digest, "nativeInputs": source["nativeInputs"],
        "caller": selected, "window": window, "rule": rule,
        "evidenceBoundary": contract["evidenceBoundary"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gameassembly", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        report = audit(gameassembly=args.gameassembly, metadata=args.metadata)
    except (OSError, ValueError, KeyError, IndexError, RuntimeError) as exc:
        print(f"dynamic-resource-state-native: {exc}", file=sys.stderr)
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"DynamicStreaming resource state gate passed: {report['rule']['predicate']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
