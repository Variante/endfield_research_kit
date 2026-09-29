"""Exact selected four-action gradual-damage SequenceActionData child."""
from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path, PurePosixPath
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.context import method_spec_usage_index
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.memorypack.action_dispatcher import load_action_routes
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack import buff_adding_cooldown as blackboard
from scripts.game_data.memorypack import buff_damage_check_decorate_mask_condition_receipt as decorate
from scripts.game_data.memorypack import buff_damage_check_tag_match_condition_receipt as target
from scripts.game_data.memorypack import buff_damage_modifier_receipt as modifier
from scripts.game_data.memorypack import buff_damage_modify_dynamic_blackboard_child_receipt as dynamic
from scripts.game_data.memorypack import buff_damage_sequence_action_condition_receipt as sequence
from scripts.game_data.memorypack import buff_find_settings_child_receipt as finder


LABEL = "buffDamageGradualCondition"
SCHEMA = "endfield.buff-damage-gradual-condition-receipt.v1"
NATIVE_SCHEMA = "endfield.buff-damage-gradual-condition-native-contract.v2"
CONTRACT_PATH = CONTRACTS_DIR / "buff_damage_gradual_condition_native.json"


def _contract() -> dict[str, Any]:
    contract, _ = read_reviewed_contract(
        CONTRACT_PATH, schema=NATIVE_SCHEMA, status="exact-current-build", label=LABEL,
    )
    tags = contract.get("selectedActionTags")
    plans = contract.get("actionMemberPlans") or {}
    sources = contract.get("sourceContracts") or {}
    read_orders = contract.get("sourceReadOrders") or {}
    contexts = contract.get("sourceContextMemberIndices") or {}
    if (
        not isinstance(tags, list) or len(tags) != 4
        or any(type(tag) is not int or tag < 0 for tag in tags)
        or len(set(tags)) != len(tags)
        or type(contract.get("sequenceMemberCount")) is not int
        or contract["sequenceMemberCount"] <= 0
        or not isinstance(contract.get("selectedTerminalRawHex"), str)
        or len(bytes.fromhex(contract["selectedTerminalRawHex"])) != 2
        or type(contract.get("selectedProcessorTag")) is not int
        or contract["selectedProcessorTag"] < 0
        or type(contract.get("inheritedActionMemberCount")) is not int
        or contract["inheritedActionMemberCount"] <= 0
        or set(sources) != {str(tags[1]), str(tags[3])}
        or set(plans) != set(sources) or set(read_orders) != set(sources)
        or set(contexts) != set(sources)
        or any(Path(path).name != path or not path.endswith(".json")
               for path in sources.values())
        or any(len(plans[key]) != len(read_orders[key]) for key in plans)
        or any(not isinstance(contexts[key], list)
               or len(contexts[key]) != 3
               or contexts[key] != sorted(set(contexts[key]))
               or any(type(index) is not int or not 0 <= index < len(plans[key])
                      for index in contexts[key])
               for key in contexts)
        or any(len({row.get("name") for row in plan}) != len(plan)
               for plan in plans.values())
        or any(not row.get("name") or not row.get("declaredType") or not row.get("kind")
               for plan in plans.values() for row in plan)
        or not contract.get("selectedFinderReadOrder")
        or not contract.get("selectedBlackboardReadOrder")
        or not isinstance(contract.get("selectedFinderShape"), dict)
    ):
        raise ValueError(f"{LABEL}.contract:shape")
    return contract


def _check_source_contexts(image: Any, source: dict[str, Any], *, tag: int,
                           plan: list[dict[str, Any]],
                           member_indices: list[int]) -> None:
    for method in source["methods"]:
        image.validate_method_row(method, label=LABEL)
    image.check_windows(source["codeWindows"], label=LABEL)
    if len(source["nestedContexts"]) != len(member_indices):
        raise ValueError(f"{LABEL}.native:context-count:{tag}")
    for context, member_index in zip(source["nestedContexts"], member_indices, strict=True):
        cell, usage = image.nested_usage_cell(context, label=LABEL)
        index = method_spec_usage_index(
            usage, image.registration["methodSpecsCount"],
            source=str(image.gameassembly), offset=cell,
        )
        if index != context["methodSpecIndex"]:
            raise ValueError(f"{LABEL}.native:method-spec-index:{tag}:{member_index}")
        spec = list(struct.unpack(
            "<iii", image.pe.bytes_at_va(
                int(image.registration["methodSpecs"], 16) + index * 12, 12,
            ),
        ))
        arguments = image.instantiations.resolve(spec[2]).arguments
        if (
            spec != context["methodSpec"] or len(arguments) != 1
            or arguments[0].raw_type_record_hex != context["argumentRawHex"]
            or image.type_name(context["typeDefinition"]) != context["typeName"]
            or context["typeName"] != plan[member_index]["declaredType"]
        ):
            raise ValueError(f"{LABEL}.native:nested-context:{tag}:{member_index}")


def validate_current_native_contract() -> dict[str, Any]:
    """Recheck both new readers and compose the already reviewed children."""
    contract = _contract()
    expected = contract["nativeInputs"]
    catalog = json.loads((CONTRACTS_DIR / "levelscript_union_tags.json").read_bytes())
    selected_sequence = json.loads((CONTRACTS_DIR /
        "buff_damage_sequence_action_condition_native.json").read_bytes())
    if (
        catalog.get("schema") != "endfield.levelscript-union-tags.v1"
        or catalog.get("nativeInputs") != {
            "gameAssemblySha256": expected["GameAssembly.dll"],
            "metadataSha256": expected["global-metadata.dat"],
        }
        or selected_sequence.get("nativeInputs") != expected
        or selected_sequence.get("memberCount") != contract["sequenceMemberCount"]
        or selected_sequence.get("terminalByteCount")
            != len(bytes.fromhex(contract["selectedTerminalRawHex"]))
    ):
        raise ValueError(f"{LABEL}.contract:dependency-drift")
    gate = check_installed_native_inputs(
        expected["GameAssembly.dll"], expected["global-metadata.dat"],
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        return {"status": gate.status, "detail": gate.detail}
    unity = Path(gate.gameassembly).parent / "UnityPlayer.dll"
    if not unity.is_file():
        return {"status": "missing", "detail": str(unity)}
    if hashlib.sha256(unity.read_bytes()).hexdigest().upper() != expected["UnityPlayer.dll"]:
        return {"status": "mismatched", "detail": "UnityPlayer.dll hash differs"}
    routes, audit = load_action_routes(
        gameassembly=gate.gameassembly, metadata=gate.metadata,
    )
    if audit.get("status") != "validated" or {
        name: str(value).upper() for name, value in audit.get("nativeInputs", {}).items()
    } != {key: expected[key] for key in ("GameAssembly.dll", "global-metadata.dat")}:
        raise ValueError(f"{LABEL}.native:action-dispatcher")
    image = open_native_image(gate.gameassembly, gate.metadata)
    compatible = {
        "bool-byte": ("bool", 1), "enum32": ("enum", 4),
        "int32": ("scalar32", 4), "buff-find-settings": ("object", None),
        "target-settings": ("object", None), "string": ("string", None),
        "blackboard-double": ("object", None),
    }
    for key, path in contract["sourceContracts"].items():
        tag = int(key, 10)
        source = json.loads((CONTRACTS_DIR / path).read_bytes())
        plan = contract["actionMemberPlans"][key]
        route = routes.get(tag)
        reviewed = catalog["families"]["AbilityActionData"][tag]
        if (
            source.get("schemaVersion") != 1
            or source.get("anonymousReadOrder", {}).get(f"member{len(plan)}")
                != contract["sourceReadOrders"][key]
            or route is None or route.status != "resolved"
            or route.wrapper_name != reviewed.get("wrapperName")
            or route.inherited_member_count != contract["inheritedActionMemberCount"]
            or reviewed.get("memberCount") != len(plan)
            or list(route.member_order) != [row["name"] for row in plan]
            or list(route.member_declared_types) != [row["declaredType"] for row in plan]
            or list(zip(route.member_kinds, route.member_widths, strict=True))
                != [compatible[row["kind"]] for row in plan]
        ):
            raise ValueError(f"{LABEL}.native:route-or-source:{tag}")
        _check_source_contexts(
            image, source, tag=tag, plan=plan,
            member_indices=contract["sourceContextMemberIndices"][key],
        )
    nested = {
        "sequence": sequence.validate_current_native_contract(),
        "decorate": decorate.validate_current_native_contract(),
        "dynamic": dynamic.validate_current_native_contract(),
        "finder": finder.validate_current_native_contract(),
        "target": target.validate_current_native_contract(),
        "blackboard": blackboard.validate_current_native_contract(),
    }
    if any(row.get("status") != "validated" for row in nested.values()):
        failed = next(name for name, row in nested.items() if row.get("status") != "validated")
        return {"status": nested[failed].get("status", "failed"), "failedChild": failed}
    for name in ("decorate", "dynamic", "finder", "target"):
        if nested[name].get("nativeInputs") != expected:
            raise ValueError(f"{LABEL}.native:nested-inputs:{name}")
    if (blackboard._contract().get("nativeInputs") != expected
            or nested["blackboard"].get("nativeStatus") != "validated"
            or nested["blackboard"].get("sourceStoreValidated") is not True):
        raise ValueError(f"{LABEL}.native:blackboard-inputs-or-store")
    for name, index in (("decorate", 0), ("dynamic", 2)):
        if nested[name].get("unionTag") != contract["selectedActionTags"][index]:
            raise ValueError(f"{LABEL}.native:nested-union-tag:{name}")
    if (nested["finder"].get("readOrders", {}).get("finder-profile")
            != contract["selectedFinderReadOrder"]):
        raise ValueError(f"{LABEL}.native:finder-read-order")
    if nested["target"].get("selectedTargetShape") is None:
        raise ValueError(f"{LABEL}.native:target-shape")
    if (nested["blackboard"].get("selectedReadOrder")
            != contract["selectedBlackboardReadOrder"]):
        raise ValueError(f"{LABEL}.native:blackboard-read-order")
    return {
        "status": "validated", "nativeInputs": expected,
        "selectedActionTags": contract["selectedActionTags"],
        "selectedProcessorTag": contract["selectedProcessorTag"],
        "sequenceMemberCount": contract["sequenceMemberCount"],
        "selectedTerminalRawHex": contract["selectedTerminalRawHex"],
        "selectedFinderShape": contract["selectedFinderShape"],
        "actionMemberPlans": contract["actionMemberPlans"],
        **{name + "Native": value for name, value in nested.items()},
        "evidenceBoundary": contract["evidenceBoundary"],
    }


def _read_fields(reader: Reader, *, plan: list[dict[str, Any]],
                 source: str, logical_sha256: str,
                 native: dict[str, Any]) -> list[dict[str, Any]]:
    fields = []
    for member in plan:
        start = reader.pos
        kind = member["kind"]
        child = None
        if kind in ("bool-byte", "enum32", "int32", "int64"):
            raw = reader.take(member["width"], member["name"])
        elif kind == "string":
            reader.byte_payload()
            raw = reader.data[start:reader.pos]
        elif kind == "buff-find-settings":
            reader.finder_profile()
            child = finder.decode_find_settings_child_receipt(
                reader.data, source=source, logical_sha256=logical_sha256,
                start=start, end=reader.pos,
                native_validation=native["finderNative"],
            )
            shape = native["selectedFinderShape"]
            if (
                child.get("status") != "named-direct-members-exact-span"
                or child.get("wholeChildSpanExact") is not True
                or child.get("buffIdListCount") != shape["buffIdListCount"]
                or child.get("tagCount") != shape["tagCount"]
                or child["namedFields"][2].get("queryStatus") != shape["queryStatus"]
            ):
                raise ValueError(f"{LABEL}.finder:selected-shape")
        elif kind == "target-settings":
            reader.target_profile()
            nested = Reader(reader.data, source, reader.pos)
            nested.pos = start
            child = target._simple_target(nested, native["targetNative"])
            if (
                child.get("status") != "exact-simple-target"
                or child.get("recursiveNamedSchemaExact") is not True
                or child.get("start") != start or child.get("end") != reader.pos
                or nested.pos != reader.pos
            ):
                raise ValueError(f"{LABEL}.target:selected-shape")
        elif kind == "blackboard-double":
            reader.scalar_payload()
            child = blackboard.decode_adding_cooldown(
                reader.data, start, reader.pos,
                native_validation=native["blackboardNative"],
            )
            if (
                child.get("wholeValueExact") is not True
                or child.get("startOffset") != start
                or child.get("consumedEnd") != reader.pos
            ):
                raise ValueError(f"{LABEL}.blackboard:selected-shape")
        else:
            raise ValueError(f"{LABEL}.action:unsupported-member:{kind}")
        field = {
            "name": member["name"], "declaredType": member["declaredType"],
            "kind": kind, "start": start, "end": reader.pos,
        }
        if child is None:
            field["rawHex"] = raw.hex().upper()
        else:
            field["namedChild"] = child
        fields.append(field)
    return fields


def decode_gradual_condition(
    data: bytes, *, source: str, logical_sha256: str,
    start: int, end: int, native_validation: dict[str, Any],
) -> dict[str, Any]:
    """Replay all four action wrappers and every selected nested child."""
    native = native_validation
    contract = _contract()
    if (
        native.get("status") != "validated"
        or native.get("nativeInputs") != contract["nativeInputs"]
        or native.get("selectedActionTags") != contract["selectedActionTags"]
        or native.get("selectedProcessorTag") != contract["selectedProcessorTag"]
        or native.get("selectedFinderShape") != contract["selectedFinderShape"]
        or native.get("sequenceMemberCount") != contract["sequenceMemberCount"]
        or native.get("selectedTerminalRawHex") != contract["selectedTerminalRawHex"]
        or native.get("actionMemberPlans") != contract["actionMemberPlans"]
        or any(native.get(name + "Native", {}).get("status") != "validated"
               for name in ("sequence", "decorate", "dynamic", "finder", "target", "blackboard"))
    ):
        raise ValueError(f"{LABEL}.native:unvalidated")
    if (
        not isinstance(data, bytes) or not isinstance(logical_sha256, str)
        or len(logical_sha256) != 64
        or hashlib.sha256(data).hexdigest().upper() != logical_sha256.upper()
    ):
        raise ValueError(f"{LABEL}.source:sha256")
    if not isinstance(source, str):
        raise ValueError(f"{LABEL}.source:path")
    virtual = PurePosixPath(source)
    if (
        virtual.is_absolute() or virtual.parts[:3] != ("Data", "Json", "BuffData")
        or len(virtual.parts) != 4 or ".." in virtual.parts
        or not source.endswith(".json")
        or type(start) is not int or type(end) is not int
        or not 0 <= start < end <= len(data)
    ):
        raise ValueError(f"{LABEL}.source:path-or-range")
    reader = Reader(data, source, end)
    reader.pos = start
    reader.header(native["sequenceMemberCount"])
    terminal_size = len(bytes.fromhex(native["selectedTerminalRawHex"]))
    if reader.count(1, reserve=terminal_size) != len(native["selectedActionTags"]):
        raise ValueError(f"{LABEL}.sequence:action-count")
    actions = []
    for tag in native["selectedActionTags"]:
        action_start = reader.pos
        reader.action(0)
        action_end = reader.pos
        if reader.records[-1].get("tag") != tag:
            raise ValueError(f"{LABEL}.action:tag")
        if tag == native["selectedActionTags"][2]:
            child = dynamic.decode_modify_dynamic_blackboard_child(
                data, source=source, logical_sha256=logical_sha256,
                start=action_start, end=action_end,
                native_validation=native["dynamicNative"],
            )
            if child.get("recursiveNamedSchemaExact") is not True:
                raise ValueError(f"{LABEL}.dynamic:child")
            fields = [
                {"name": field["fieldName"], "kind": field["kind"],
                 "start": field["start"], "end": field["end"],
                 **({"namedChild": field["namedChild"]} if "namedChild" in field else
                    {"rawHex": data[field["start"]:field["end"]].hex().upper()})}
                for field in child["namedFields"]
            ]
        else:
            selected = Reader(data, source, action_end)
            selected.pos = action_start
            if selected.nested_union_tag((tag,), "condition-action") != tag or selected.peek() == 0xFF:
                raise ValueError(f"{LABEL}.action:nonnull-wrapper:{tag}")
            plan = (native["decorateNative"]["actionMemberPlan"]
                    if tag == native["selectedActionTags"][0]
                    else native["actionMemberPlans"][str(tag)])
            selected.header(len(plan))
            fields = _read_fields(
                selected, plan=plan, source=source,
                logical_sha256=logical_sha256, native=native,
            )
            if selected.pos != action_end:
                raise ValueError(f"{LABEL}.action:end:{tag}")
        if (
            not fields or fields[0]["start"] <= action_start
            or any(left["end"] != right["start"] for left, right in zip(fields, fields[1:]))
            or fields[-1]["end"] != action_end
        ):
            raise ValueError(f"{LABEL}.action:field-tiling:{tag}")
        actions.append({
            "tag": tag, "start": action_start, "end": action_end,
            "memberCount": len(fields), "namedFields": fields,
            "wholeStoredSpanExact": True, "recursiveNamedSchemaExact": True,
        })
    terminal = reader.take(terminal_size, "sequence-terminals").hex().upper()
    if (
        terminal != native["selectedTerminalRawHex"] or reader.pos != end
        or any(left["end"] != right["start"] for left, right in zip(actions, actions[1:]))
        or actions[-1]["end"] + terminal_size != end
    ):
        raise ValueError(f"{LABEL}.sequence:terminal-or-end")
    return {
        "schema": SCHEMA, "status": "exact-four-action-sequence",
        "source": source, "logicalSha256": logical_sha256.upper(),
        "start": start, "end": end, "actionCount": len(actions),
        "actions": actions, "terminalRawHex": terminal,
        "wholeStoredSpanExact": True, "recursiveNamedSchemaExact": True,
        "wholeBuffDataExact": False, "evidenceBoundary": native["evidenceBoundary"],
    }


def audit_current_positive_frames(
    report_path: Path, export_root: Path, *, expected_input_set_sha256: str,
    selected_source: str,
) -> dict[str, Any]:
    """Join one caller-selected source identity to the exact condition child."""
    report_bytes = report_path.read_bytes()
    report = json.loads(report_bytes)
    expected_set = expected_input_set_sha256.upper()
    if (
        len(expected_set) != 64
        or any(ch not in "0123456789ABCDEF" for ch in expected_set)
        or report.get("inputSetSha256") != expected_set
        or report.get("status") != "complete"
        or report.get("publicationEligible") is not True
        or report.get("provenance", {}).get("buffPositiveDamageNativeValidation", {}).get("status")
            != "validated"
    ):
        raise ValueError(f"{LABEL}.report:current-provenance")
    native = validate_current_native_contract()
    modifier_native = modifier.validate_current_native_contract()
    if native.get("status") != "validated" or modifier_native.get("status") != "validated":
        raise ValueError(f"{LABEL}.native:unvalidated")
    matches = [row for row in report["files"]
               if row.get("identity", {}).get("fileName") == selected_source]
    if len(matches) != 1:
        raise ValueError(f"{LABEL}.report:selected-source-count={len(matches)}")
    source_row = matches[0]
    identity = source_row["identity"]
    source = identity["fileName"]
    virtual = PurePosixPath(source)
    if (source_row.get("rootPositiveDamageFrameCandidate") is not True
            or source_row.get("rootPositiveDamageCandidate") is True
            or identity.get("status") != "verified"
            or identity.get("inputSetSha256") != expected_set
            or virtual.parts[:3] != ("Data", "Json", "BuffData")
            or len(virtual.parts) != 4):
        raise ValueError(f"{LABEL}.report:selected-identity:{source}")
    accepted = [item for item in source_row["candidates"]
                if item.get("readerAcceptedThroughEof") is True]
    if len(accepted) != 1:
        raise ValueError(f"{LABEL}.report:accepted-candidate:{source}")
    blocker = accepted[0]["namedSchemaReceipt"]["firstBlocker"]
    if (blocker.get("field") != "damageModifier"
            or blocker.get("category") != "positive-modifier-recursive-proof"):
        raise ValueError(f"{LABEL}.report:damage-first-blocker:{source}")
    data = (export_root / virtual.name).read_bytes()
    digest = hashlib.sha256(data).hexdigest().upper()
    if len(data) != identity["length"] or digest != source_row["logicalSha256"]:
        raise ValueError(f"{LABEL}.source:logical-bytes:{source}")
    parent = modifier.decode_damage_modifier_collection(
        data, blocker["start"], blocker["end"], source=source,
        native_validation=modifier_native,
    )
    if parent.get("count") != 1 or len(parent.get("elements") or []) != 1:
        raise ValueError(f"{LABEL}.source:damage-item-count:{source}")
    condition, processors = parent["elements"][0]["fields"][:2]
    if (condition.get("actionTags") != native["selectedActionTags"]
            or condition.get("actionUnionCount") != len(native["selectedActionTags"])
            or [row.get("tag") for row in processors.get("processors") or []]
                != [native["selectedProcessorTag"]]):
        raise ValueError(f"{LABEL}.source:selected-pattern:{source}")
    receipt = decode_gradual_condition(
        data, source=source, logical_sha256=digest,
        start=condition["start"], end=condition["end"],
        native_validation=native,
    )
    prior = report["provenance"]["buffPositiveDamageNativeValidation"]
    if (prior.get("status") != "validated"
            or prior.get("nativeInputs") != native["nativeInputs"]
            or prior.get("root", {}).get("nativeInputs") != native["nativeInputs"]):
        raise ValueError(f"{LABEL}.report:positive-native-receipt")
    from scripts.game_data.memorypack import buff_root_no_positive as root_reader
    if not root_reader.is_positive_damage_candidate(source_row, length=len(data)):
        raise ValueError(f"{LABEL}.report:positive-root-frame")
    whole_root = root_reader.decode_positive_damage_buff(
        data, source=source, expected_sha256=digest,
        native_validation=prior["root"],
        positive_damage_validation={**prior, "gradualCondition": native},
    )
    if (whole_root.get("status") != "named-exact-full"
            or whole_root.get("wholeSchemaExact") is not True
            or whole_root.get("rootMemberCount")
                != prior["root"]["root"]["memberCount"]
            or whole_root.get("bytesConsumed") != len(data)
            or whole_root.get("physicalEof") != len(data)):
        raise ValueError(f"{LABEL}.source:root-eof")
    rows = [{"source": source, "logicalSha256": digest,
             "conditionReceipt": receipt,
             "processorTags": [native["selectedProcessorTag"]],
             "wholeRootReceipt": whole_root, "wholeRootExact": True}]
    return {
        "schema": "endfield.buff-damage-gradual-condition-source-audit.v1",
        "status": "complete", "publicationEligible": False,
        "inputSetSha256": expected_set, "sourceReport": str(report_path),
        "sourceReportSha256": hashlib.sha256(report_bytes).hexdigest().upper(),
        "nativeValidation": native, "summary": {"selectedFiles": len(rows),
            "exactConditionChildren": len(rows), "exactWholeRoots": len(rows)},
        "rows": rows,
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--buff-report", type=Path, required=True)
    parser.add_argument("--export-root", type=Path, required=True)
    parser.add_argument("--expected-input-set-sha256", required=True)
    parser.add_argument("--source", required=True,
                        help="One VFS BuffData virtual path to validate")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit_current_positive_frames(
        args.buff_report, args.export_root,
        expected_input_set_sha256=args.expected_input_set_sha256,
        selected_source=args.source,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
