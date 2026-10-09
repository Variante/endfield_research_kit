"""Named Blackboard children of current-build Buff SetSuperArmorAction spans.

The parent action receipt owns the seven-field action cursor. This adapter
replays it, then joins its two exact child fields to selected inherited
wrapper setters and complete byte-pinned native readers. It does not evaluate
blackboard values or promote the enclosing BuffData record.

Both direct children, ``impactResistance`` and ``superArmorValue``, carry
four ordered members: ``blackboardKey``, ``useBlackboardKey``, ``value`` and
``useCustomValue``. Each child is replayed against the authenticated source
bytes and the exact parent action endpoint. String and flag bytes stay raw.
``TargetSettings`` and the whole-BuffData schema stay open.

``--buff-report`` and ``--action-report`` default to
``reports/animestudio/buffdata_current_latest.json`` and
``buff_action_receipts_current_latest.json`` (the ``0x0159`` spans come from
the latter); the default output is
``reports/animestudio/buff_super_armor_blackboard_children_current_latest.json``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
from collections import Counter
from pathlib import Path
from typing import Any

from scripts.common import (
    NATIVE_EVIDENCE_VALIDATED, ROOT, canonical_json_sha256,
    check_installed_native_inputs,
)
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.memorypack import buff_set_super_armor_action_receipt as parent
from scripts.game_data.memorypack.buff_actions import Reader


LABEL = "buffSuperArmorBlackboardChild"
SCHEMA = "endfield.buff-super-armor-blackboard-child-receipt.v1"
CONTRACT_PATH = CONTRACTS_DIR / "buff_super_armor_blackboard_child_native.json"
REPORTS_ROOT = ROOT / "reports"
DEFAULT_OUTPUT = REPORTS_ROOT / "animestudio/buff_super_armor_blackboard_children_current_latest.json"
SOURCE_PATTERN = re.compile(r"^Data/Json/BuffData/[^/\\]+[.]json$")


def _contract() -> dict[str, Any]:
    value, _digest = read_reviewed_contract(
        CONTRACT_PATH,
        schema="endfield.buff-super-armor-blackboard-child-native-contract.v1",
        status="exact-current-build", label=LABEL,
    )
    fields = value.get("storedReadOrder")
    children = value.get("children")
    chain = value.get("commonInheritance")
    if (
        not isinstance(fields, list) or len(fields) != 4
        or [row[1] for row in fields]
        != ["byte-payload", "byte", "scalar32", "byte"]
        or len({row[0] for row in fields}) != len(fields)
        or not isinstance(children, list) or len(children) != 2
        or len({row["parentFieldIndex"] for row in children}) != len(children)
        or not isinstance(chain, list) or len(chain) < 2
    ):
        raise ValueError(f"{LABEL}.contract:shape")
    setter_names = [row[1].removeprefix("set___").removesuffix("__")
                    for owner in chain for row in owner["setterMethods"]]
    setter_destinations = value.get("inheritedSetterDestinations")
    if (setter_names != [row[0] for row in fields]
            or not isinstance(setter_destinations, list)
            or [row[0] for row in setter_destinations] != setter_names):
        raise ValueError(f"{LABEL}.contract:inherited-setter-order")
    for child in children:
        if (
            len(child["sourceReadCalls"]) != len(fields)
            or len(child["destinations"]) != len(fields)
            or [row[-1] for row in child["sourceReadCalls"]] != setter_names
            or [row[-1] for row in child["destinations"]] != setter_names
            or child["sourceReadCalls"] != sorted(child["sourceReadCalls"], key=lambda row: row[0])
            or child["readerMethodIndex"] == child["formatterMethodIndex"]
        ):
            raise ValueError(f"{LABEL}.contract:child-shape")
    return value


def _call_target(image: Any, rva: int) -> int:
    raw = image.pe.bytes_at_va(image.pe.image_base + rva, 5)
    if raw[:1] != b"\xe8":
        raise ValueError(f"{LABEL}.native:expected-call={rva:#x}")
    return rva + 5 + struct.unpack_from("<i", raw, 1)[0]


def validate_current_native_contract() -> dict[str, Any]:
    """Rejoin the parent route, both inherited wrappers and each source call."""
    contract = _contract()
    expected = contract["nativeInputs"]
    source, catalog = parent._contracts()
    if (
        contract["parentActionContract"] != parent.SOURCE_CONTRACT.name
        or contract["parentCatalogContract"] != parent.CATALOG_CONTRACT.name
        or contract["parentUnionTag"] != parent.TAG
        or catalog["nativeInputs"]["gameAssemblySha256"] != expected["GameAssembly.dll"]
        or catalog["nativeInputs"]["metadataSha256"] != expected["global-metadata.dat"]
        or ["byte-payload" if kind == "nullable byte payload" else kind
            for kind in source["anonymousReadOrder"]["bothNestedMember4"]]
        != [row[1] for row in contract["storedReadOrder"]]
    ):
        raise ValueError(f"{LABEL}.native:parent-contract-drift")
    gate = check_installed_native_inputs(
        expected["GameAssembly.dll"], expected["global-metadata.dat"],
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        return {"status": gate.status, "detail": gate.detail}
    unity = gate.gameassembly.parent / "UnityPlayer.dll"
    if not unity.is_file():
        return {"status": "missing", "detail": str(unity)}
    if hashlib.sha256(unity.read_bytes()).hexdigest().upper() != expected["UnityPlayer.dll"]:
        return {"status": "mismatched", "detail": "UnityPlayer.dll hash differs"}
    parent_native = parent.validate_current_native_contract()
    if (
        parent_native.get("status") != "validated"
        or parent_native.get("unionTag") != contract["parentUnionTag"]
        or any(parent_native.get("nativeInputs", {}).get(name) != expected[name]
               for name in ("GameAssembly.dll", "global-metadata.dat"))
    ):
        raise ValueError(f"{LABEL}.native:parent-route-drift")
    image = open_native_image(gate.gameassembly, gate.metadata)
    chain = contract["commonInheritance"]
    chain_types = []
    setters_by_name = {}
    for owner in chain:
        typ = image.metadata.types[owner["typeDefinition"]]
        if image.metadata.type_full_name(typ) != owner["typeName"]:
            raise ValueError(f"{LABEL}.native:inherited-type={owner['typeDefinition']}")
        if image.setter_methods(typ, parameter="typeName", label=LABEL) != owner["setterMethods"]:
            raise ValueError(f"{LABEL}.native:inherited-setters={owner['typeDefinition']}")
        chain_types.append(typ)
        for method in owner["setterMethods"]:
            setters_by_name[method[1].removeprefix("set___").removesuffix("__")] = method[0]
    if any(derived.parent_index != base.byval_type_index
           for base, derived in zip(chain_types, chain_types[1:])):
        raise ValueError(f"{LABEL}.native:inherited-chain")
    setter_store_offset = {}
    for field_name, method_index, method_rva, store_rva, store_hex in contract["inheritedSetterDestinations"]:
        raw = bytes.fromhex(store_hex)
        if (
            setters_by_name.get(field_name) != method_index
            or image.method_pointer_va(image.metadata.methods[method_index])
            != image.pe.image_base + method_rva
            or not method_rva <= store_rva < method_rva + 0x100
            or image.pe.bytes_at_va(image.pe.image_base + store_rva, len(raw)) != raw
            or not raw
        ):
            raise ValueError(f"{LABEL}.native:inherited-setter-destination={field_name}")
        setter_store_offset[field_name] = raw[-1]

    bindings = []
    parent_fields = parent_native["memberNames"]
    parent_kinds = parent_native["readKinds"]
    nested_contexts = source["nestedContexts"]
    nested_indices = [i for i, kind in enumerate(parent_kinds)
                      if kind in parent._NESTED_KINDS]
    context_by_index = dict(zip(nested_indices, nested_contexts[1:], strict=True))
    parent_methods = {row[0]: row for row in source["methods"]}
    parent_windows = {row["startRva"]: row for row in source["codeWindows"]}
    for child in contract["children"]:
        index = child["parentFieldIndex"]
        if (
            not 0 <= index < len(parent_fields)
            or parent_fields[index] != child["parentFieldName"]
            or parent_kinds[index] != "scalar-flag-payload"
            or context_by_index.get(index, {}).get("typeName") != child["providerType"]
        ):
            raise ValueError(f"{LABEL}.native:parent-field={index}")
        wrapper = image.metadata.types[child["wrapperTypeDefinition"]]
        if (
            image.metadata.type_full_name(wrapper) != child["wrapperTypeName"]
            or wrapper.parent_index != chain_types[-1].byval_type_index
            or image.setter_methods(wrapper, parameter="typeName", label=LABEL)
        ):
            raise ValueError(f"{LABEL}.native:child-wrapper={index}")
        selected_methods = (child["formatterMethodIndex"], child["readerMethodIndex"])
        for method_index in selected_methods:
            if method_index not in parent_methods:
                raise ValueError(f"{LABEL}.native:method-not-in-parent={method_index}")
            image.validate_method_row(parent_methods[method_index], label=LABEL)
        if parent_methods[child["readerMethodIndex"]][1] != child["wrapperTypeName"]:
            raise ValueError(f"{LABEL}.native:reader-wrapper={index}")
        windows = []
        for window_start in child["readerWindowStarts"]:
            if window_start not in parent_windows:
                raise ValueError(f"{LABEL}.native:window-not-in-parent={window_start:#x}")
            windows.append(parent_windows[window_start])
        image.check_windows(windows, label=LABEL)
        body_start = parent_methods[child["readerMethodIndex"]][3]
        body = parent_windows.get(body_start)
        if body is None:
            raise ValueError(f"{LABEL}.native:reader-body-window={index}")
        for position, ((rva, target, field_name), destination) in enumerate(zip(
            child["sourceReadCalls"], child["destinations"], strict=True
        )):
            next_rva = (child["sourceReadCalls"][position + 1][0]
                        if position + 1 < len(child["sourceReadCalls"])
                        else body["endRva"])
            write_rva, opcode, write_target, write_field = destination
            if (
                not body_start <= rva < write_rva < next_rva <= body["endRva"]
                or field_name != write_field
                or _call_target(image, rva) != target
            ):
                raise ValueError(f"{LABEL}.native:read-destination={field_name}")
            if opcode == "call":
                if (
                    _call_target(image, write_rva) != write_target
                    or image.method_pointer_va(image.metadata.methods[setters_by_name[field_name]])
                    != image.pe.image_base + write_target
                ):
                    raise ValueError(f"{LABEL}.native:setter-call={field_name}")
            else:
                raw = bytes.fromhex(opcode)
                if (image.pe.bytes_at_va(image.pe.image_base + write_rva, len(raw)) != raw
                        or raw[-1] != write_target
                        or write_target != setter_store_offset[field_name]):
                    raise ValueError(f"{LABEL}.native:direct-store={field_name}")
        bindings.append({
            "parentFieldIndex": index,
            "parentFieldName": child["parentFieldName"],
            "providerType": child["providerType"],
        })
    return {
        "status": "validated", "nativeInputs": expected,
        "parentNative": parent_native,
        "parentUnionTag": contract["parentUnionTag"],
        "storedReadOrder": contract["storedReadOrder"],
        "bindings": bindings,
        "evidenceBoundary": contract["evidenceBoundary"],
    }


def _decode_child(data: bytes, source: str, field: dict[str, Any],
                  binding: dict[str, Any], order: list[list[str]]) -> dict[str, Any]:
    start, end = field["start"], field["end"]
    reader = Reader(data, source, end)
    reader.pos = start
    if reader.peek() == 0xFF:
        reader.take(1, "null-blackboard-wrapper")
        if reader.pos != end:
            raise ValueError(f"{LABEL}:null-child-end")
        return {"status": "exact-null-wrapper", "start": start, "end": end,
                "providerType": binding["providerType"], "namedFields": [],
                "wholeProviderByteSpanExact": True}
    reader.header(len(order))
    named = []
    for name, kind in order:
        field_start = reader.pos
        if kind == "byte-payload":
            length = reader.count(1, reserve=6, nullable=True)
            payload = reader.take(max(length, 0), f"{name}.bytes")
            value = {"storedByteLength": length,
                     "sourceBytesSha256": (hashlib.sha256(payload).hexdigest().upper()
                                           if length >= 0 else None),
                     "stringDecodeClaimed": False}
        elif kind == "byte":
            raw = reader.take(1, name)
            value = {"rawHex": raw.hex().upper(), "storedByte": raw[0],
                     "booleanValueClaimed": False}
        elif kind == "scalar32":
            raw = reader.take(4, name)
            value = {"rawHex": raw.hex().upper(),
                     "storedInt32": struct.unpack("<i", raw)[0]}
        else:
            raise ValueError(f"{LABEL}:unsupported-kind={kind}")
        named.append({"fieldName": name, "kind": kind,
                      "start": field_start, "end": reader.pos, **value})
    if (reader.pos != end or named[0]["start"] != start + 1
            or any(left["end"] != right["start"]
                   for left, right in zip(named, named[1:]))):
        raise ValueError(f"{LABEL}:child-end={reader.pos};expected={end}")
    return {"status": "named-four-member-exact-span", "start": start,
            "end": end, "providerType": binding["providerType"],
            "namedFields": named, "wholeProviderByteSpanExact": True}


def decode_blackboard_value(data: bytes, *, source: str, logical_sha256: str,
                           start: int, end: int, provider_type: str,
                           native_validation: dict[str, Any]) -> dict[str, Any]:
    """Replay a proved provider; its caller independently owns the typed slot."""
    contract = _contract()
    bindings = [{"parentFieldIndex": row["parentFieldIndex"],
                 "parentFieldName": row["parentFieldName"],
                 "providerType": row["providerType"]} for row in contract["children"]]
    if (native_validation.get("status") != "validated"
            or native_validation.get("nativeInputs") != contract["nativeInputs"]
            or native_validation.get("storedReadOrder") != contract["storedReadOrder"]
            or native_validation.get("bindings") != bindings
            or not isinstance(data, bytes) or not source or not isinstance(logical_sha256, str)
            or hashlib.sha256(data).hexdigest().upper() != logical_sha256.upper()
            or type(start) is not int or type(end) is not int or not 0 <= start < end <= len(data)):
        raise ValueError(f"{LABEL}:value-native-source-or-span")
    selected = [row for row in bindings if row["providerType"] == provider_type]
    if len(selected) != 1:
        raise ValueError(f"{LABEL}:value-provider-not-proved")
    row = _decode_child(data, source, {"start": start, "end": end}, selected[0], contract["storedReadOrder"])
    return {**row, "source": source, "logicalSha256": logical_sha256.upper(),
            "recursiveStoredSchemaExact": True, "runtimeMeaningExact": False}


def decode_super_armor_blackboard_children(
    data: bytes, *, source: str, logical_sha256: str, start: int, end: int,
    native_validation: dict[str, Any],
) -> dict[str, Any]:
    """Reparse one parent action and name both direct Blackboard child spans."""
    contract = _contract()
    if (
        native_validation.get("status") != "validated"
        or native_validation.get("nativeInputs") != contract["nativeInputs"]
        or native_validation.get("parentUnionTag") != contract["parentUnionTag"]
        or native_validation.get("storedReadOrder") != contract["storedReadOrder"]
        or native_validation.get("bindings")
        != [{"parentFieldIndex": row["parentFieldIndex"],
             "parentFieldName": row["parentFieldName"],
             "providerType": row["providerType"]} for row in contract["children"]]
    ):
        raise ValueError(f"{LABEL}:native-not-validated")
    action = parent.decode_set_super_armor_action_receipt(
        data, source=source, logical_sha256=logical_sha256,
        start=start, end=end, native_validation=native_validation["parentNative"],
    )
    if (
        action.get("schema") != parent.SCHEMA
        or action.get("status") != "named-wrapper-exact-span"
        or action.get("wholeActionByteSpanExact") is not True
        or action.get("tag") != contract["parentUnionTag"]
        or action.get("source") != source
        or action.get("logicalSha256") != logical_sha256.upper()
        or action.get("start") != start or action.get("end") != end
    ):
        raise ValueError(f"{LABEL}:parent-action-drift")
    children = []
    for binding in native_validation["bindings"]:
        field = action["namedFields"][binding["parentFieldIndex"]]
        if (field["fieldName"] != binding["parentFieldName"]
                or field["kind"] != "scalar-flag-payload"):
            raise ValueError(f"{LABEL}:parent-child-field-drift")
        child = _decode_child(
            data, source, field, binding, native_validation["storedReadOrder"],
        )
        children.append({"parentFieldName": binding["parentFieldName"],
                         "parentFieldRange": [field["start"], field["end"]],
                         **child})
    return {"schema": SCHEMA, "status": "named-two-children-exact-spans",
            "source": source, "logicalSha256": logical_sha256.upper(),
            "parentTag": contract["parentUnionTag"],
            "parentActionRange": [start, end], "children": children,
            "wholeActionByteSpanExact": True,
            "wholeActionRecursiveSchemaExact": False,
            "wholeBuffDataExact": False,
            "evidenceBoundary": contract["evidenceBoundary"]}


def build_report(
    buff_report: dict[str, Any], action_report: dict[str, Any], *,
    buff_report_path: Path, action_report_path: Path,
    export_root: Path, expected_input_set_sha256: str,
    native_validation: dict[str, Any],
) -> dict[str, Any]:
    """Join every selected action to VFS identity and exact source bytes."""
    tag = _contract()["parentUnionTag"]
    expected = expected_input_set_sha256.upper()
    if not re.fullmatch(r"[0-9A-F]{64}", expected):
        raise ValueError(f"{LABEL}.report:input-set-format")
    outer = buff_report.get("files")
    if (
        buff_report.get("format") != "animestudio-buffdata-current-vfs-corpus"
        or buff_report.get("status") != "complete"
        or buff_report.get("publicationEligible") is not True
        or buff_report.get("wholeSchemaExact") is not False
        or buff_report.get("inputSetSha256", "").upper() != expected
        or not isinstance(outer, list)
        or buff_report.get("summary", {}).get("filesSelected") != len(outer)
        or buff_report.get("summary", {}).get("filesUnique") != len(outer)
        or buff_report.get("summary", {}).get("filesFailed") != 0
        or buff_report.get("summary", {}).get("filesAmbiguous") != 0
        or canonical_json_sha256([
            {"identity": row.get("identity"), "logicalSha256": row.get("logicalSha256")}
            for row in outer
        ]) != buff_report.get("identitySetSha256")
    ):
        raise ValueError(f"{LABEL}.report:outer-vfs-provenance")
    if (
        action_report.get("schema") != "endfield.buff-action-receipt-corpus.v7"
        or action_report.get("status") != "complete"
        or action_report.get("publicationEligible") is not True
        or action_report.get("wholeBuffDataExact") is not False
        or action_report.get("inputSetSha256", "").upper() != expected
        or action_report.get("sourceIdentitySetSha256") != buff_report.get("identitySetSha256")
        or action_report.get("buffReportSha256")
        != hashlib.sha256(buff_report_path.read_bytes()).hexdigest().upper()
        or Path(action_report.get("exportRoot", "")).resolve() != Path(export_root).resolve()
        or action_report.get("nativeInputsByTag", {}).get(f"0x{tag:04X}")
        != {name: native_validation.get("nativeInputs", {}).get(name)
            for name in ("GameAssembly.dll", "global-metadata.dat")}
        or native_validation.get("status") != "validated"
    ):
        raise ValueError(f"{LABEL}.report:action-provenance")
    indexed = {}
    for row in outer:
        identity = row.get("identity") or {}
        source = identity.get("fileName")
        if (not isinstance(source, str) or not SOURCE_PATTERN.fullmatch(source)
                or source in indexed or identity.get("virtualPath") != source):
            raise ValueError(f"{LABEL}.report:outer-source-identity={source}")
        indexed[source] = row
    rows = []
    seen_sources = set()
    for action_file in action_report.get("files", []):
        actions = [row for row in action_file.get("actions", []) if row.get("tag") == tag]
        if not actions:
            continue
        source = action_file.get("source")
        if source not in indexed or source in seen_sources:
            raise ValueError(f"{LABEL}.report:action-source={source}")
        seen_sources.add(source)
        outer_row = indexed[source]
        identity = outer_row["identity"]
        if (
            identity.get("status") != "verified"
            or identity.get("boundaryStatus") != "boundary_verified"
            or identity.get("inputSetSha256", "").upper() != expected
            or action_file.get("logicalSha256") != outer_row.get("logicalSha256")
        ):
            raise ValueError(f"{LABEL}.report:source-vfs-join={source}")
        path = Path(export_root) / "game" / source.removeprefix("Data/")
        data = path.read_bytes()
        logical_sha = hashlib.sha256(data).hexdigest().upper()
        if (
            len(data) != identity.get("length")
            or len(data) != identity.get("actualBytesRead")
            or logical_sha != action_file["logicalSha256"]
            or hashlib.md5(data).hexdigest().upper()
            != identity.get("recomputedFileDataMd5", "").upper()
        ):
            raise ValueError(f"{LABEL}.report:logical-source-bytes={source}")
        seen_ranges = set()
        for action in actions:
            span = (action.get("start"), action.get("end"))
            if span in seen_ranges or action.get("schema") != parent.SCHEMA:
                raise ValueError(f"{LABEL}.report:action-span={source}:{span}")
            seen_ranges.add(span)
            receipt = decode_super_armor_blackboard_children(
                data, source=source, logical_sha256=logical_sha,
                start=span[0], end=span[1], native_validation=native_validation,
            )
            replayed_parent = parent.decode_set_super_armor_action_receipt(
                data, source=source, logical_sha256=logical_sha,
                start=span[0], end=span[1],
                native_validation=native_validation["parentNative"],
            )
            if action != replayed_parent:
                raise ValueError(f"{LABEL}.report:parent-receipt-drift={source}:{span}")
            rows.append(receipt)
    label = f"0x{tag:04X}"
    expected_counts = action_report["summary"]["byTag"][label]
    if (len(rows) != expected_counts["actionSpans"]
            or len(seen_sources) != expected_counts["files"]):
        raise ValueError(f"{LABEL}.report:action-count")
    states = Counter(child["status"] for row in rows for child in row["children"])
    return {
        "schema": SCHEMA, "status": "complete", "publicationEligible": True,
        "inputSetSha256": expected, "wholeBuffDataExact": False,
        "nativeValidation": {key: value for key, value in native_validation.items()
                             if key != "parentNative"},
        "sourceReports": {
            "buff": str(buff_report_path),
            "buffSha256": hashlib.sha256(buff_report_path.read_bytes()).hexdigest().upper(),
            "action": str(action_report_path),
            "actionSha256": hashlib.sha256(action_report_path.read_bytes()).hexdigest().upper(),
        },
        "summary": {"actionSpans": len(rows), "sourceFiles": len(seen_sources),
                    "childSpans": 2 * len(rows), "childStates": dict(sorted(states.items()))},
        "rows": rows, "evidenceBoundary": _contract()["evidenceBoundary"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--buff-report", type=Path, default=REPORTS_ROOT / "animestudio/buffdata_current_latest.json")
    parser.add_argument("--action-report", type=Path, default=REPORTS_ROOT / "animestudio/buff_action_receipts_current_latest.json")
    parser.add_argument("--export-root", type=Path, default=ROOT / "export_full")
    parser.add_argument("--expected-input-set-sha256", required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output.resolve()
    if REPORTS_ROOT.resolve() not in output.parents:
        parser.error(f"output must be under {REPORTS_ROOT}")
    buff_path = args.buff_report.resolve()
    action_path = args.action_report.resolve()
    report = build_report(
        json.loads(buff_path.read_text(encoding="utf-8")),
        json.loads(action_path.read_text(encoding="utf-8")),
        buff_report_path=buff_path, action_report_path=action_path,
        export_root=args.export_root.resolve(),
        expected_input_set_sha256=args.expected_input_set_sha256,
        native_validation=validate_current_native_contract(),
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
