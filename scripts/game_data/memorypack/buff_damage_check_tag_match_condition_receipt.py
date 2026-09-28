"""Exact selected one-action CheckTagMatch damage condition span.

It checks the selected native six-member action, simple
TargetSettings/DirectionSettings/SelectorData children and a positive raw
GameplayTagQuery, then replays one ``CheckTagMatch`` condition against current
VFS logical hashes. ``memorypack.buff_corpus`` admits it with one tag-five,
tag-zero or tag-three processor through all 30 original root fields, source
ID and EOF. Raw tag values are stored authored data, not a runtime match.

Takes the shared ``buff_damage_*`` receipt arguments (see
``buff_damage_modifier_receipt``); the conventional ``--output`` is
``reports/animestudio/buff_damage_check_tag_match_condition_current_latest.json``.
"""
from __future__ import annotations

import hashlib
import json
import struct
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.context import method_spec_usage_index
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.memorypack.action_dispatcher import load_action_routes
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack import buff_damage_modifier_receipt as modifier
from scripts.game_data.memorypack import buff_damage_sequence_action_condition_receipt as sequence
from scripts.game_data.memorypack import buff_direction_settings_child_receipt as direction
from scripts.game_data.memorypack import buff_find_settings_child_receipt as query
from scripts.game_data.memorypack import buff_selector_data_child_receipt as selector
from scripts.game_data.memorypack import buff_target_settings_child_receipt as target


LABEL = "buffDamageCheckTagMatchCondition"
SCHEMA = "endfield.buff-damage-check-tag-match-condition-receipt.v1"
NATIVE_SCHEMA = "endfield.buff-damage-check-tag-match-condition-native-contract.v1"
CONTRACT_PATH = CONTRACTS_DIR / "buff_damage_check_tag_match_condition_native.json"


def _contract() -> dict[str, Any]:
    contract, _digest = read_reviewed_contract(
        CONTRACT_PATH, schema=NATIVE_SCHEMA, status="exact-current-build", label=LABEL,
    )
    plan = contract.get("actionMemberPlan")
    shape = contract.get("selectedTargetShape")
    if (
        contract.get("reviewedDependencies") != [
            "levelscript_union_tags.json", "buff_7c_native.json",
            "buff_damage_sequence_action_condition_native.json",
            "buff_find_settings_child_native.json",
        ]
        or contract.get("unionFamily") != "AbilityActionData"
        or type(contract.get("unionTag")) is not int
        or not 0 <= contract["unionTag"] <= 65535
        or contract.get("sequenceMemberCount") != 3
        or contract.get("sequenceTerminalByteCount") != 2
        or not isinstance(plan, list) or len(plan) != 6
        or [row.get("kind") for row in plan] != [
            "bool-byte", "enum32", "int32", "int32", "target-settings",
            "gameplay-tag-query",
        ]
        or [row.get("width") for row in plan[:4]] != [1, 4, 4, 4]
        or len({row.get("name") for row in plan}) != len(plan)
        or any(not row.get("name") or not row.get("declaredType") for row in plan)
        or not isinstance(shape, dict)
        or shape.get("nonnullTargetMemberCount") != 13
        or shape.get("nonnullDirectionMemberCount") != 8
        or shape.get("nonnullSelectorMemberCount") != 3
        or shape.get("nullDirectionReferences") != ["source", "target"]
        or shape.get("emptyTargetStrings") != [
            "centerContextKey", "ownerContextKey", "targetContextKey", "targetGroupKey",
        ]
        or shape.get("nullSelectorUnion") != "finderData"
        or shape.get("emptySelectorLists") != ["postProcessorData", "validatorData"]
        or shape.get("positiveQueryTagCounts") != [1, 2]
        or len(contract.get("sourceMethodIndices", [])) != 2
        or len(contract.get("sourceWindowStarts", [])) != 4
        or len(contract.get("sourceContextRvas", [])) != 2
    ):
        raise ValueError(f"{LABEL}.contract:shape")
    return contract


def _member_plan(registry: Any, definition: int) -> list[dict[str, Any]]:
    return [
        {"name": member.name, "kind": member.kind, "width": member.width,
         "ref": member.ref, "declaredType": registry.wrapped_names.get(member.ref)}
        for member in registry.plans[definition]
    ]


def validate_current_native_contract() -> dict[str, Any]:
    """Check the selected action and all reached simple nested readers."""
    contract = _contract()
    dependencies = contract["reviewedDependencies"]
    catalog = json.loads((CONTRACTS_DIR / dependencies[0]).read_bytes())
    source = json.loads((CONTRACTS_DIR / dependencies[1]).read_bytes())
    selected_sequence = json.loads((CONTRACTS_DIR / dependencies[2]).read_bytes())
    selected_query = json.loads((CONTRACTS_DIR / dependencies[3]).read_bytes())
    expected = contract["nativeInputs"]
    if (
        catalog.get("schema") != "endfield.levelscript-union-tags.v1"
        or catalog.get("nativeInputs") != {
            "gameAssemblySha256": expected["GameAssembly.dll"],
            "metadataSha256": expected["global-metadata.dat"],
        }
        or source.get("schemaVersion") != 1
        or source.get("anonymousReadOrder", {}).get("member6") != [
            "byte", "scalar32", "scalar32", "scalar32",
            "target-profile", "query-profile",
        ]
        or selected_sequence.get("schema")
        != "endfield.buff-damage-sequence-action-condition-native-contract.v1"
        or selected_sequence.get("nativeInputs") != expected
        or selected_sequence.get("memberCount") != contract["sequenceMemberCount"]
        or selected_sequence.get("terminalByteCount")
        != contract["sequenceTerminalByteCount"]
        or selected_query.get("schema")
        != "endfield.buff-find-settings-child-native-contract.v1"
        or selected_query.get("nativeInputs") != expected
    ):
        raise ValueError(f"{LABEL}.contract:dependency-drift")
    reviewed = [row for row in catalog["families"][contract["unionFamily"]]
                if row.get("tag") == contract["unionTag"]]
    methods = [row for row in source["methods"]
               if row[0] in contract["sourceMethodIndices"]]
    windows = [row for row in source["codeWindows"]
               if row["startRva"] in contract["sourceWindowStarts"]]
    contexts = [row for row in source["nestedContexts"]
                if row["instructionRva"] in contract["sourceContextRvas"]]
    if (
        len(reviewed) != 1
        or reviewed[0].get("wrapperName") != contract["wrapperType"]
        or reviewed[0].get("wrappedType") != contract["wrappedType"]
        or reviewed[0].get("memberCount") != len(contract["actionMemberPlan"])
        or [row[0] for row in methods] != contract["sourceMethodIndices"]
        or [row["startRva"] for row in windows] != contract["sourceWindowStarts"]
        or [row["instructionRva"] for row in contexts] != contract["sourceContextRvas"]
    ):
        raise ValueError(f"{LABEL}.contract:route-or-source")
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
    sequence_native = sequence.validate_current_native_contract()
    if sequence_native.get("status") != "validated":
        return {"status": sequence_native.get("status", "failed"),
                "sequence": sequence_native}
    routes, route_audit = load_action_routes(
        gameassembly=gate.gameassembly, metadata=gate.metadata,
    )
    route = routes.get(contract["unionTag"])
    plan = contract["actionMemberPlan"]
    compatible = {"bool-byte": ("bool", 1), "enum32": ("enum", 4),
                  "int32": ("scalar32", 4),
                  "target-settings": ("object", None),
                  "gameplay-tag-query": ("object", None)}
    if (
        route_audit.get("status") != "validated"
        or {name: str(value).upper() for name, value in
            route_audit.get("nativeInputs", {}).items()} != {
                "GameAssembly.dll": expected["GameAssembly.dll"],
                "global-metadata.dat": expected["global-metadata.dat"],
            }
        or route is None or route.status != "resolved"
        or route.wrapper_name != contract["wrapperType"]
        or route.inherited_member_count != 4
        or list(route.member_order) != [row["name"] for row in plan]
        or list(route.member_declared_types) != [row["declaredType"] for row in plan]
        or list(zip(route.member_kinds, route.member_widths, strict=True))
        != [compatible[row["kind"]] for row in plan]
    ):
        raise ValueError(f"{LABEL}.native:dispatcher-or-wrapper-drift")
    image = open_native_image(gate.gameassembly, gate.metadata)
    for method in methods:
        image.validate_method_row(method, label=LABEL)
    image.check_windows(windows, label=LABEL)
    for index, context in enumerate(contexts):
        cell, usage = image.nested_usage_cell(context, label=LABEL)
        spec_index = method_spec_usage_index(
            usage, image.registration["methodSpecsCount"],
            source=str(image.gameassembly), offset=cell,
        )
        if spec_index != context["methodSpecIndex"]:
            raise ValueError(f"{LABEL}.native:method-spec-index:{index}")
        spec = list(struct.unpack(
            "<iii", image.pe.bytes_at_va(
                int(image.registration["methodSpecs"], 16) + spec_index * 12, 12,
            ),
        ))
        arguments = image.instantiations.resolve(spec[2]).arguments
        if (
            spec != context["methodSpec"]
            or len(arguments) != 1
            or arguments[0].raw_type_record_hex != context["argumentRawHex"]
            or image.type_name(context["typeDefinition"]) != context["typeName"]
            or context["typeName"] != plan[4 + index]["declaredType"]
        ):
            raise ValueError(f"{LABEL}.native:nested-context:{index}")
    target_native = target.validate_current_native_contract()
    direction_native = direction.validate_current_native_contract(target_native=target_native)
    selector_native = selector.validate_current_native_contract(target_native=target_native)
    query_native = query.validate_current_native_contract()
    if (
        any(nested.get("status") != "validated"
            or nested.get("nativeInputs") != expected
            for nested in (target_native, direction_native, selector_native, query_native))
        or query_native.get("readOrders", {}).get("query-profile") != ["queryType", "tags"]
    ):
        raise ValueError(f"{LABEL}.native:nested-reader-drift")
    registry = target_native["_registry"]
    target_plan = _member_plan(registry, target_native["targetDefinition"])
    direction_plan = _member_plan(registry, direction_native["directionDefinition"])
    selector_plan = _member_plan(registry, selector_native["selectorDefinition"])
    shape = contract["selectedTargetShape"]
    if (
        len(target_plan) != shape["nonnullTargetMemberCount"]
        or len(direction_plan) != shape["nonnullDirectionMemberCount"]
        or len(selector_plan) != shape["nonnullSelectorMemberCount"]
        or [row["name"] for row in target_plan] != target_native["targetMemberNames"]
        or [row["name"] for row in direction_plan] != direction_native["directMemberNames"]
        or [row["name"] for row in selector_plan] != selector_native["directMemberNames"]
        or {row["name"] for row in target_plan if row["kind"] == "string"}
        != set(shape["emptyTargetStrings"])
        or {row["name"] for row in direction_plan if row["kind"] == "object"}
        != set(shape["nullDirectionReferences"])
        or [row["name"] for row in selector_plan if row["kind"] == "union"]
        != [shape["nullSelectorUnion"]]
        or {row["name"] for row in selector_plan if row["kind"] == "list"}
        != set(shape["emptySelectorLists"])
        or next((row["declaredType"] for row in target_plan
                 if row["name"] == "advancedDirection"), None)
        != "Beyond.Gameplay.Core.DirectionSettings"
        or next((row["declaredType"] for row in target_plan
                 if row["name"] == "selectorData"), None)
        != "Beyond.Gameplay.Core.Selector+SelectorData"
    ):
        raise ValueError(f"{LABEL}.native:nested-plan-shape")
    return {
        "status": "validated", "nativeInputs": expected,
        "unionTag": contract["unionTag"], "wrapperType": contract["wrapperType"],
        "wrappedType": contract["wrappedType"],
        "actionMemberPlan": plan,
        "sequenceMemberCount": contract["sequenceMemberCount"],
        "sequenceTerminalByteCount": contract["sequenceTerminalByteCount"],
        "sequenceNative": {"status": "validated"},
        "targetPlan": target_plan, "directionPlan": direction_plan,
        "selectorPlan": selector_plan,
        "queryFieldNames": query_native["readOrders"]["query-profile"],
        "selectedTargetShape": shape,
        "nestedNative": {"target": "validated", "direction": "validated",
                         "selector": "validated", "query": "validated"},
        "evidenceBoundary": contract["evidenceBoundary"],
    }


def _fixed(reader: Reader, member: dict[str, Any]) -> dict[str, Any]:
    width = member.get("width")
    if type(width) is not int or width <= 0:
        raise ValueError(f"{LABEL}.plan:fixed-width:{member.get('name')}")
    start = reader.pos
    raw = reader.take(width, member["name"])
    return {"name": member["name"], "kind": member["kind"],
            "start": start, "end": reader.pos, "rawHex": raw.hex().upper()}


def _simple_direction(reader: Reader, native: dict[str, Any]) -> dict[str, Any]:
    start = reader.pos
    plan = native["directionPlan"]
    shape = native["selectedTargetShape"]
    reader.header(len(plan))
    fields = []
    for member in plan:
        if member["kind"] == "fixed":
            fields.append(_fixed(reader, member))
        elif member["kind"] == "object" and member["name"] in shape["nullDirectionReferences"]:
            field_start = reader.pos
            if reader.take(1, member["name"]) != b"\xff":
                raise ValueError(f"{LABEL}.direction:nonnull-reference:{member['name']}")
            fields.append({"name": member["name"], "kind": "null-object",
                           "start": field_start, "end": reader.pos})
        else:
            raise ValueError(f"{LABEL}.direction:unsupported-member:{member['name']}")
    if (len(fields) != shape["nonnullDirectionMemberCount"]
            or fields[0]["start"] != start + 1
            or any(left["end"] != right["start"] for left, right in zip(fields, fields[1:]))):
        raise ValueError(f"{LABEL}.direction:field-tiling")
    return {"status": "exact-simple-direction", "start": start, "end": reader.pos,
            "memberCount": len(fields), "namedFields": fields,
            "recursiveNamedSchemaExact": True}


def _simple_selector(reader: Reader, native: dict[str, Any]) -> dict[str, Any]:
    start = reader.pos
    plan = native["selectorPlan"]
    shape = native["selectedTargetShape"]
    reader.header(len(plan))
    fields = []
    for member in plan:
        field_start = reader.pos
        if member["kind"] == "union" and member["name"] == shape["nullSelectorUnion"]:
            if reader.take(1, member["name"]) != b"\xff":
                raise ValueError(f"{LABEL}.selector:nonnull-finder")
            field = {"name": member["name"], "kind": "null-union"}
        elif member["kind"] == "list" and member["name"] in shape["emptySelectorLists"]:
            if reader.count(1, nullable=True) != 0:
                raise ValueError(f"{LABEL}.selector:nonempty-list:{member['name']}")
            field = {"name": member["name"], "kind": "empty-list", "count": 0}
        else:
            raise ValueError(f"{LABEL}.selector:unsupported-member:{member['name']}")
        fields.append(dict(field, start=field_start, end=reader.pos))
    if (len(fields) != shape["nonnullSelectorMemberCount"]
            or fields[0]["start"] != start + 1
            or any(left["end"] != right["start"] for left, right in zip(fields, fields[1:]))):
        raise ValueError(f"{LABEL}.selector:field-tiling")
    return {"status": "exact-simple-selector", "start": start, "end": reader.pos,
            "memberCount": len(fields), "namedFields": fields,
            "recursiveNamedSchemaExact": True}


def _simple_target(reader: Reader, native: dict[str, Any]) -> dict[str, Any]:
    start = reader.pos
    plan = native["targetPlan"]
    shape = native["selectedTargetShape"]
    reader.header(len(plan))
    fields = []
    for member in plan:
        field_start = reader.pos
        if member["kind"] == "fixed":
            field = _fixed(reader, member)
        elif member["kind"] == "string" and member["name"] in shape["emptyTargetStrings"]:
            if reader.take(4, member["name"]) != b"\x00" * 4:
                raise ValueError(f"{LABEL}.target:nonempty-string:{member['name']}")
            field = {"name": member["name"], "kind": "empty-string",
                     "start": field_start, "end": reader.pos}
        elif member["kind"] == "object" and member["name"] == "advancedDirection":
            child = _simple_direction(reader, native)
            field = {"name": member["name"], "kind": "direction-settings",
                     "start": field_start, "end": reader.pos, "namedChild": child}
        elif member["kind"] == "object" and member["name"] == "selectorData":
            child = _simple_selector(reader, native)
            field = {"name": member["name"], "kind": "selector-data",
                     "start": field_start, "end": reader.pos, "namedChild": child}
        else:
            raise ValueError(f"{LABEL}.target:unsupported-member:{member['name']}")
        fields.append(field)
    if (len(fields) != shape["nonnullTargetMemberCount"]
            or fields[0]["start"] != start + 1
            or any(left["end"] != right["start"] for left, right in zip(fields, fields[1:]))):
        raise ValueError(f"{LABEL}.target:field-tiling")
    return {"status": "exact-simple-target", "start": start, "end": reader.pos,
            "memberCount": len(fields), "namedFields": fields,
            "recursiveNamedSchemaExact": True}


def _positive_query(reader: Reader, native: dict[str, Any]) -> dict[str, Any]:
    start = reader.pos
    names = native["queryFieldNames"]
    if names != ["queryType", "tags"]:
        raise ValueError(f"{LABEL}.query:field-plan")
    reader.header(len(names))
    type_start = reader.pos
    query_type = reader.take(4, names[0])
    tags_start = reader.pos
    count = reader.count(4, reserve=native["sequenceTerminalByteCount"], nullable=True)
    if count not in native["selectedTargetShape"]["positiveQueryTagCounts"]:
        raise ValueError(f"{LABEL}.query:unsupported-tag-count={count}")
    tags = [reader.take(4, names[1]).hex().upper() for _ in range(count)]
    fields = [
        {"name": names[0], "kind": "enum32", "start": type_start,
         "end": tags_start, "rawHex": query_type.hex().upper()},
        {"name": names[1], "kind": "counted-raw32", "start": tags_start,
         "end": reader.pos, "count": count, "rawElementsHex": tags},
    ]
    return {"status": "exact-positive-query", "start": start, "end": reader.pos,
            "memberCount": len(fields), "namedFields": fields,
            "recursiveNamedSchemaExact": True}


def decode_check_tag_match_condition(
    data: bytes, *, source: str, logical_sha256: str,
    start: int, end: int, native_validation: dict[str, Any],
) -> dict[str, Any]:
    """Replay the selected simple target and query to one condition endpoint."""
    contract = _contract()
    if (
        native_validation.get("status") != "validated"
        or native_validation.get("nativeInputs") != contract["nativeInputs"]
        or native_validation.get("unionTag") != contract["unionTag"]
        or native_validation.get("actionMemberPlan") != contract["actionMemberPlan"]
        or native_validation.get("selectedTargetShape") != contract["selectedTargetShape"]
        or native_validation.get("sequenceNative", {}).get("status") != "validated"
        or native_validation.get("nestedNative") != {
            "target": "validated", "direction": "validated",
            "selector": "validated", "query": "validated",
        }
    ):
        raise ValueError(f"{LABEL}.native:unvalidated")
    if (
        not isinstance(data, bytes)
        or not isinstance(logical_sha256, str)
        or len(logical_sha256) != 64
        or hashlib.sha256(data).hexdigest().upper() != logical_sha256.upper()
    ):
        raise ValueError(f"{LABEL}.source:sha256")
    if not isinstance(source, str):
        raise ValueError(f"{LABEL}.source:path")
    virtual = PurePosixPath(source)
    if (
        virtual.is_absolute()
        or virtual.parts[:3] != ("Data", "Json", "BuffData")
        or len(virtual.parts) != 4 or ".." in virtual.parts
        or not source.endswith(".json")
    ):
        raise ValueError(f"{LABEL}.source:path")
    if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(data):
        raise ValueError(f"{LABEL}.source:range")
    reader = Reader(data, source, end)
    reader.pos = start
    reader.header(native_validation["sequenceMemberCount"])
    count = reader.count(1, reserve=native_validation["sequenceTerminalByteCount"], nullable=True)
    if count != 1:
        raise ValueError(f"{LABEL}.sequence:action-count={count}")
    action_start = reader.pos
    tag = reader.nested_union_tag((native_validation["unionTag"],), "condition-action")
    if tag != native_validation["unionTag"] or reader.peek() == 0xFF:
        raise ValueError(f"{LABEL}.action:selected-nonnull-wrapper")
    tag_end = reader.pos
    plan = native_validation["actionMemberPlan"]
    reader.header(len(plan))
    fields = []
    for member in plan[:4]:
        field_start = reader.pos
        raw = reader.take(member["width"], member["name"])
        fields.append({"name": member["name"], "declaredType": member["declaredType"],
                       "kind": member["kind"], "start": field_start,
                       "end": reader.pos, "rawHex": raw.hex().upper()})
    target_start = reader.pos
    target_child = _simple_target(reader, native_validation)
    fields.append({"name": plan[4]["name"], "declaredType": plan[4]["declaredType"],
                   "kind": plan[4]["kind"], "start": target_start,
                   "end": reader.pos, "namedChild": target_child})
    query_start = reader.pos
    query_child = _positive_query(reader, native_validation)
    fields.append({"name": plan[5]["name"], "declaredType": plan[5]["declaredType"],
                   "kind": plan[5]["kind"], "start": query_start,
                   "end": reader.pos, "namedChild": query_child})
    action_end = reader.pos
    terminal = reader.take(native_validation["sequenceTerminalByteCount"], "sequence-terminals")
    if (
        reader.pos != end
        or fields[0]["start"] != tag_end + 1
        or fields[-1]["end"] != action_end
        or any(left["end"] != right["start"] for left, right in zip(fields, fields[1:]))
        or target_child["end"] != fields[4]["end"]
        or query_child["end"] != fields[5]["end"]
    ):
        raise ValueError(f"{LABEL}.cursor:expected={end} actual={reader.pos}")
    return {
        "schema": SCHEMA, "status": "exact-one-action-sequence",
        "source": source, "logicalSha256": logical_sha256.upper(),
        "start": start, "end": end, "actionCount": 1,
        "sequenceMemberCount": native_validation["sequenceMemberCount"],
        "action": {"tag": tag, "start": action_start, "end": action_end,
                   "wrapperType": native_validation["wrapperType"],
                   "wrappedType": native_validation["wrappedType"],
                   "memberCount": len(fields), "namedFields": fields,
                   "wholeStoredSpanExact": True, "recursiveNamedSchemaExact": True},
        "terminalRawHex": terminal.hex().upper(),
        "wholeStoredSpanExact": True, "recursiveNamedSchemaExact": True,
        "wholeBuffDataExact": False,
        "evidenceBoundary": native_validation["evidenceBoundary"],
    }


def audit_current_positive_frames(
    report_path: Path, export_root: Path, *, expected_input_set_sha256: str,
) -> dict[str, Any]:
    """Join exact simple-target condition spans to current VFS identities."""
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
    if native.get("status") != "validated":
        raise ValueError(f"{LABEL}.native:{native.get('status')}")
    modifier_native = modifier.validate_current_native_contract()
    if modifier_native.get("status") != "validated":
        raise ValueError(f"{LABEL}.modifier-native:{modifier_native.get('status')}")
    rows = []
    for source_row in report["files"]:
        if (
            source_row.get("rootPositiveDamageFrameCandidate") is not True
            or source_row.get("rootPositiveDamageCandidate") is True
        ):
            continue
        identity = source_row["identity"]
        source = identity["fileName"]
        virtual = PurePosixPath(source)
        if (
            identity.get("status") != "verified"
            or identity.get("inputSetSha256") != expected_set
            or virtual.parts[:3] != ("Data", "Json", "BuffData")
            or len(virtual.parts) != 4
        ):
            raise ValueError(f"{LABEL}.report:identity:{source}")
        accepted = [candidate for candidate in source_row["candidates"]
                    if candidate.get("readerAcceptedThroughEof") is True]
        if len(accepted) != 1:
            raise ValueError(f"{LABEL}.report:accepted-candidate:{source}")
        blocker = accepted[0]["namedSchemaReceipt"]["firstBlocker"]
        if (
            blocker.get("field") != "damageModifier"
            or blocker.get("category") != "positive-modifier-recursive-proof"
        ):
            raise ValueError(f"{LABEL}.report:damage-first-blocker:{source}")
        path = export_root / virtual.name
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest().upper()
        if len(data) != identity["length"] or digest != source_row["logicalSha256"]:
            raise ValueError(f"{LABEL}.source:logical-bytes:{source}")
        parent = modifier.decode_damage_modifier_collection(
            data, blocker["start"], blocker["end"], source=source,
            native_validation=modifier_native,
        )
        if parent.get("count") != 1 or len(parent.get("elements", [])) != 1:
            continue
        fields = parent["elements"][0]["fields"]
        condition = fields[0]
        if (
            condition.get("name") != "condition"
            or condition.get("actionTags") != [native["unionTag"]]
            or condition.get("actionUnionCount") != 1
        ):
            continue
        processor_tags = [item["tag"] for item in fields[1]["processors"]]
        try:
            decoded = decode_check_tag_match_condition(
                data, source=source, logical_sha256=digest,
                start=condition["start"], end=condition["end"],
                native_validation=native,
            )
        except ValueError as exc:
            rows.append({"source": source, "logicalSha256": digest,
                         "conditionStatus": "unsupported-selected-variant",
                         "refusal": f"{type(exc).__name__}: {exc}",
                         "processorTags": processor_tags,
                         "projectedRootWithSelectedProcessor": False})
            continue
        rows.append({
            "source": source, "logicalSha256": digest,
            "conditionStatus": decoded["status"], "conditionReceipt": decoded,
            "processorTags": processor_tags,
            "projectedRootWithSelectedProcessor": processor_tags == [5],
        })
    exact = [row for row in rows if row["conditionStatus"] == "exact-one-action-sequence"]
    tags = Counter(tuple(row["processorTags"]) for row in rows)
    return {
        "schema": "endfield.buff-damage-check-tag-match-condition-corpus.v1",
        "status": "complete", "publicationEligible": False,
        "inputSetSha256": expected_set,
        "sourceReport": str(report_path),
        "sourceReportSha256": hashlib.sha256(report_bytes).hexdigest().upper(),
        "nativeValidation": native,
        "summary": {
            "oneActionConditionReached": len(rows),
            "oneActionConditionExact": len(exact),
            "unsupportedSelectedVariants": len(rows) - len(exact),
            "processorTags": {",".join(map(str, key)): value
                              for key, value in sorted(tags.items())},
            "projectedRootWithSelectedProcessor": sum(
                row["projectedRootWithSelectedProcessor"] for row in exact
            ),
            "wholeBuffDataPromoted": 0,
        },
        "rows": rows,
        "evidenceBoundary": (
            "Current VFS-verified identities and logical hashes join a selected "
            "one-action CheckTagMatch condition and its exact simple target/query "
            "variant. Root projection is a frontier rank, not a whole-BuffData receipt."
        ),
    }


__all__ = [
    "audit_current_positive_frames", "decode_check_tag_match_condition",
    "validate_current_native_contract",
]


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--buff-report", type=Path, required=True)
    parser.add_argument("--export-root", type=Path, required=True)
    parser.add_argument("--expected-input-set-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit_current_positive_frames(
        args.buff_report, args.export_root,
        expected_input_set_sha256=args.expected_input_set_sha256,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
