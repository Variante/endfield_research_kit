"""Check recorded synchronous source-selection chains without asynchronous joins.

The selected native owner supplies a minimal authenticated declaration. This
reader uses that declaration and already admitted capture pairs; it opens no
native image and promotes no managed request, file, codec or lifetime claim.
"""
from __future__ import annotations

from collections import Counter
from bisect import bisect_left, bisect_right
import math
import json
import re
from typing import Any, Callable


SCHEMA = "endfield.audio-source-bridge-relations.v1"
DECLARATION_SCHEMA = "endfield.wwise-source-bridge-relations.v1"
MAX_SAMPLES = 48
MAX_ROWS = 32
MAX_PATH_SAMPLES = 4
ROLES = ("sourceSelector", "sourceClone", "sourceSetWideText", "ownerFactory", "ownerConstructor", "ownerConsumer", "sourceLock")
SAMPLE_ROLES = ("selector", "clone", "setter", "factory", "constructor", "consumer", "lock")
BOUNDARY = ("Same-thread immediate recorded nesting, exact selected callsites and config dispatch, "
            "descriptor text to cloned source, constructed owner and consumer/Lock pointer transport only. "
            "Retained text/output pointers and zero byte count are not media bytes. Managed request to queue ownership, "
            "allocation generation/lifetime, backing file, codec/decode success and audibility remain unresolved.")


def _pointer(value: Any, *, nonzero: bool = False) -> int | None:
    if not isinstance(value, str) or re.fullmatch(r"0x[0-9a-fA-F]{1,16}", value) is None:
        return None
    number = int(value, 16)
    return number if (0 < number if nonzero else 0 <= number) and number < 0x800000000000 else None


def _rva(value: Any) -> int:
    if not isinstance(value, str) or re.fullmatch(r"0x[0-9a-fA-F]{1,8}", value) is None:
        raise ValueError("unbounded or malformed declared RVA")
    return int(value, 16)


def _field(hook: dict[str, Any], argument: str, offset: int, kind: str,
           chain: list[int] | None = None, phase: str | None = None) -> str:
    index = hook["args"][argument]["index"]
    found = [read["name"] for read in hook["memory"]
             if read["argIndex"] == index and read["offset"] == offset and read["kind"] == kind
             and read.get("pointerOffsets", []) == (chain or [])
             and (phase is None or read.get("samplePhase") == phase)]
    if len(found) != 1:
        raise ValueError(f"missing or ambiguous authenticated {kind} field for {argument}")
    return found[0]


def audit_bridge_relations(admitted: dict[tuple[str, str], tuple[dict[str, Any], dict[str, Any]]],
        hooks: dict[str, dict[str, Any]], profile: dict[str, Any], module_facts: dict[str, list[dict[str, Any]]],
        bridge_declaration: dict[str, Any] | None, issue: Callable[..., None],
        recorded: dict[tuple[str, str], dict[str, Any]] | None = None) -> dict[str, Any]:
    """Audit every applicable pair; cap presentation independently of validation."""
    if bridge_declaration is None:
        return {}
    spec = bridge_declaration
    try:
        if spec.get("schema") != DECLARATION_SCHEMA or set(spec["roles"]) != set(ROLES):
            raise ValueError("missing exact reviewed bridge relation roles")
        role_hooks = {}
        kinds = set()
        for role in ROLES:
            declaration = spec["roles"][role]
            kind = declaration["sourceKind"]
            if not isinstance(kind, str) or not 1 <= len(kind) <= 96 or kind in kinds:
                raise ValueError("missing unique bounded bridge source kind")
            kinds.add(kind)
            _rva(declaration["entryRva"])
            hook = hooks[declaration["sourceKind"]]
            if (hook["rva"] != declaration["entryRva"]
                    or json.dumps(hook["args"], sort_keys=True) != json.dumps(declaration["args"], sort_keys=True)):
                raise ValueError("profile hook differs from authenticated bridge relation role")
            role_hooks[role] = hook
        if profile["nativeModuleName"] != spec["moduleName"]:
            raise ValueError("profile native module differs from authenticated bridge module")
        layouts, owner = spec["bridgeLayouts"], spec["ownerLayout"]
        if (not isinstance(layouts, dict) or len(layouts) > 4 or any(not isinstance(layout, dict) or len(layout) > 32
                or any(type(value) is not int or not 0 <= value <= 4096 for value in layout.values()) for layout in layouts.values())
                or not isinstance(owner, dict) or set(owner) != {"consumerOwnerOffset", "primarySourcePointerOffset", "consumerSourcePointerOffset", "consumerOutputOffset"}
                or any(type(value) is not int or not 0 <= value <= 4096 for value in owner.values())):
            raise ValueError("unbounded or malformed bridge layout roles")
        if owner["primarySourcePointerOffset"] != owner["consumerOwnerOffset"] + owner["consumerSourcePointerOffset"]:
            raise ValueError("primary and consumer source storage roles disagree")
        source_fields, output_fields = spec["sourceFields"], spec["outputFields"]
        if (not isinstance(source_fields, list) or not isinstance(output_fields, list) or not isinstance(spec["configDispatchRows"], list)
                or not 1 <= len(source_fields) <= 32 or not 1 <= len(output_fields) <= 32 or not 1 <= len(spec["configDispatchRows"]) <= 32):
            raise ValueError("unbounded bridge relation fields or dispatch rows")
        for fields in (source_fields, output_fields):
            field_names = set()
            for row in fields:
                if (not isinstance(row, dict) or not isinstance(row.get("name"), str) or not 1 <= len(row["name"]) <= 96
                        or row["name"] in field_names or row.get("kind") not in ("pointer", "u32")
                        or type(row.get("offset")) is not int or not 0 <= row["offset"] <= 4096):
                    raise ValueError("unbounded or malformed bridge typed field")
                field_names.add(row["name"])
        _rva(spec["consumerAddressPointRva"])
        callers = spec["callers"]
        if not isinstance(callers, dict) or set(callers) != set(ROLES) - {"sourceSelector"}:
            raise ValueError("missing exact bounded bridge caller roles")
        for addresses in callers.values():
            if not isinstance(addresses, list) or not 1 <= len(addresses) <= 4 or len({_rva(address) for address in addresses}) != len(addresses):
                raise ValueError("unbounded or duplicate bridge caller RVAs")
        dispatch_points = set()
        for row in spec["configDispatchRows"]:
            if not isinstance(row, dict) or row.get("dispatchKind") not in ("directFactory", "conditionalFactoryWrapper"):
                raise ValueError("missing reviewed bounded bridge dispatch row")
            point = _rva(row["addressPointRva"])
            target = _rva(row["targetRva"])
            if (point in dispatch_points or type(row.get("entrySlot")) is not int or not 0 <= row["entrySlot"] <= 4096 or row["entrySlot"] % 8
                    or row["dispatchKind"] == "directFactory" and target != _rva(spec["roles"]["ownerFactory"]["entryRva"])):
                raise ValueError("ambiguous or malformed bridge dispatch target/slot")
            dispatch_points.add(point)
        selector_hook, setter_hook = role_hooks["sourceSelector"], role_hooks["sourceSetWideText"]
        blob, allocation, descriptor = layouts["playbackBlob"], layouts["externalAllocation"], layouts["descriptor"]
        count_field = _field(selector_hook, "playbackBlobPointer", allocation["count"], "u32", [blob["externalAllocationPointer"]])
        descriptor_fields = {name: _field(selector_hook, "playbackBlobPointer", allocation["firstDescriptor"] + offset,
                                      "pointer" if name.endswith("Pointer") else "u32", [blob["externalAllocationPointer"]])
                             for name, offset in descriptor.items()}
        text_field = _field(selector_hook, "playbackBlobPointer", 0, "utf16Direct",
                            [blob["externalAllocationPointer"], allocation["firstDescriptor"] + descriptor["wideTextPointer"]])
        setter_text_field = _field(setter_hook, "descriptorWideTextPointer", 0, "utf16Direct")
        config_field = _field(selector_hook, "playbackBlobPointer", 0, "pointer", [blob["configInterfacePointer"]])
        serial_field = _field(selector_hook, "playbackBlobPointer", blob["serialWord"], "u32")
        stored_source_field = _field(role_hooks["ownerConstructor"], "anonymousPrimaryOwnerPointer", owner["primarySourcePointerOffset"], "pointer", phase="result")
        embedded_point_field = _field(role_hooks["ownerConstructor"], "anonymousPrimaryOwnerPointer", owner["consumerOwnerOffset"], "pointer", phase="result")
        consumer_source_field = _field(role_hooks["ownerConsumer"], "anonymousCallerOwnerPointer", owner["consumerSourcePointerOffset"], "pointer")
        source_maps = {}
        for role in ("sourceSelector", "sourceClone", "sourceSetWideText", "ownerFactory", "ownerConstructor", "sourceLock"):
            argument = "originalSourcePointer" if role in ("sourceSelector", "sourceClone") else "sourceThisPointer"
            source_maps[role] = {row["name"]: _field(role_hooks[role], argument, row["offset"], row["kind"]) for row in source_fields}
        output_maps = {role: {row["name"]: _field(role_hooks[role], argument, base + row["offset"], row["kind"])
                             for row in output_fields}
                       for role, argument, base in (("ownerConsumer", "anonymousCallerOwnerPointer", owner["consumerOutputOffset"]),
                                                    ("sourceLock", "mediaRefOutputPointer", 0))}
        data_field = next(row["name"] for row in source_fields if row["offset"] == layouts["source"]["dataPointer"] and row["kind"] == "pointer")
        match_field = next(row["name"] for row in source_fields if row["offset"] == layouts["source"]["matchWord"] and row["kind"] == "u32")
        output_data_field = "mediaRefDataPointer"
        output_size_field = "mediaRefByteCount"
        if output_data_field not in output_maps["sourceLock"] or output_size_field not in output_maps["sourceLock"]:
            raise ValueError("missing authenticated output data/count roles")
    except (AttributeError, KeyError, TypeError, ValueError, StopIteration) as error:
        issue("bridgeDeclaration", expected="authenticated bounded bridge relation declaration and exact profile fields", actual=str(error)[:160])
        return {}

    def module_rva(session: str, address: Any) -> str | None:
        pointer = _pointer(address, nonzero=True)
        if pointer is None:
            return None
        found = []
        for fact in module_facts.get(session, []):
            base = _pointer(fact.get("base"), nonzero=True)
            if fact.get("moduleName") == spec["moduleName"] and base is not None and type(fact.get("size")) is int:
                delta = pointer - base
                if 0 <= delta < fact["size"]:
                    found.append(hex(delta))
        return found[0] if len(found) == 1 else None

    # Include structurally complete recorded intervals so an omitted intermediate
    # hook cannot make a grandchild appear to be an immediate child.
    intervals = dict(admitted)
    incomplete: dict[tuple[str, Any], list[tuple[int, dict[str, Any]]]] = {}
    for key, pair in (recorded or {}).items():
        if key in intervals:
            continue
        if pair.get("duplicate") or len(pair.get("calls", [])) != 1 or len(pair.get("results", [])) != 1:
            for row in [*pair.get("calls", []), *pair.get("results", [])]:
                thread = row.get("threadId")
                if (type(thread) in (int, str) and str(thread).isdigit() and len(str(thread)) <= 10
                        and 0 < int(thread) <= 0xffffffff and type(row.get("seq")) is int):
                    incomplete.setdefault((key[0], thread), []).append((row["seq"], row))
            continue
        call, result = pair["calls"][0], pair["results"][0]
        thread = call.get("threadId")
        valid_thread = (type(thread) in (int, str) and str(thread).isdigit() and len(str(thread)) <= 10
                        and 0 < int(thread) <= 0xffffffff)
        if valid_thread and thread == result.get("threadId") and type(call.get("seq")) is int and type(result.get("seq")) is int and call["seq"] < result["seq"]:
            intervals[key] = (call, result)
    events = sorted((row["seq"], phase, key, row) for key, pair in intervals.items() for phase, row in enumerate(pair))
    stacks: dict[tuple[str, Any], list[str]] = {}
    active_parent, active_result = {}, {}
    for _seq, phase, key, row in events:
        stack = stacks.setdefault((key[0], row["threadId"]), [])
        if phase == 0:
            active_parent[key] = stack[-1] if stack else None
            stack.append(key[1])
        else:
            active_result[key] = stack[-1] if stack else None
            if key[1] in stack:
                stack.remove(key[1])
    for rows in incomplete.values():
        rows.sort(key=lambda value: value[0])
    incomplete_sequences = {key: [seq for seq, _row in rows] for key, rows in incomplete.items()}
    children: dict[tuple[str, str], dict[str, list[tuple[str, str]]]] = {}
    for key, (call, _result) in admitted.items():
        parent_id = call.get("nativeParentCaptureId")
        if parent_id is not None:
            children.setdefault((key[0], parent_id), {}).setdefault(call["sourceKind"], []).append(key)

    def child(parent_key: tuple[str, str], role: str) -> tuple[str, str] | None:
        candidates = children.get(parent_key, {}).get(spec["roles"][role]["sourceKind"], [])
        if not candidates:
            return None
        parent_call, parent_result = admitted[parent_key]
        if len(candidates) != 1:
            issue("bridgeChildMultiplicity", parent_call, role=role, expected="one recorded immediate child", actual=len(candidates))
            return None
        key = candidates[0]
        call, result = admitted[key]
        times = [row.get("monotonicMs") for row in (parent_call, call, result, parent_result)]
        if (call["threadId"] != parent_call["threadId"] or result["threadId"] != parent_call["threadId"]
                or active_parent.get(key) != parent_key[1]
                or active_result.get(key) != key[1] or active_result.get(parent_key) != parent_key[1]
                or not parent_call["seq"] < call["seq"] < result["seq"] < parent_result["seq"]
                or any(type(value) not in (int, float) or not math.isfinite(value) or value < 0 for value in times)
                or times != sorted(times)):
            issue("bridgeParentInterval", call, role=role, expected="same-thread immediate active parent and ordered interval", actual={"parentId": parent_key[1], "activeParentId": active_parent.get(key)})
            return None
        caller = module_rva(key[0], call.get("nativeReturnAddress"))
        if caller not in spec["callers"][role]:
            issue("bridgeCallsite", call, role=role, expected=spec["callers"][role], actual=caller)
            return None
        return key

    def snapshot(role: str, row: dict[str, Any], phase: str) -> dict[str, Any]:
        values = row["memory"] if phase == "entry" else row["memoryAfter"]
        return {name: values[field] for name, field in source_maps[role].items()}

    def same(a: Any, b: Any) -> bool:
        if isinstance(a, str) and isinstance(b, str) and a.startswith("0x") and b.startswith("0x"):
            left, right = _pointer(a), _pointer(b)
            return left is not None and right is not None and left == right
        return a == b

    selectors = [(key, pair) for key, pair in admitted.items() if pair[0]["sourceKind"] == spec["roles"]["sourceSelector"]["sourceKind"]]
    selectors.sort(key=lambda item: item[1][0]["seq"])
    unresolved: Counter[str] = Counter()
    grouped: dict[str, dict[str, Any]] = {}
    single_count = chain_count = sample_count = 0
    for selector_key, (before, after) in selectors:
        memory = before["memory"]
        if memory[count_field] != 1:
            unresolved["outsideSingleDescriptorScope"] += 1
            continue
        single_count += 1
        path, descriptor_pointer = memory[text_field], memory[descriptor_fields["wideTextPointer"]]
        if not isinstance(path, str) or not path or _pointer(descriptor_pointer, nonzero=True) is None:
            unresolved["noNonemptyDescriptorText"] += 1
            continue
        thread_key = (selector_key[0], before["threadId"])
        partial_rows, partial_sequences = incomplete.get(thread_key, []), incomplete_sequences.get(thread_key, [])
        first_partial = bisect_right(partial_sequences, before["seq"])
        last_partial = bisect_left(partial_sequences, after["seq"])
        if first_partial < last_partial:
            issue("bridgeIncompleteInterval", partial_rows[first_partial][1],
                  expected="complete recorded native intervals inside selected selector",
                  actual={"selectorCaptureId": selector_key[1], "incompleteEventCount": last_partial - first_partial})
            continue
        selected = {"sourceSelector": selector_key}
        for role in ("sourceClone", "sourceSetWideText", "ownerFactory", "ownerConsumer"):
            selected[role] = child(selector_key, role)
        if any(value is None for value in selected.values()):
            unresolved["missingCompleteSelectionChildren"] += 1
            continue
        selected["ownerConstructor"] = child(selected["ownerFactory"], "ownerConstructor")
        selected["sourceLock"] = child(selected["ownerConsumer"], "sourceLock")
        if selected["ownerConstructor"] is None or selected["sourceLock"] is None:
            unresolved["missingConstructorOrLock"] += 1
            continue
        pairs = {role: admitted[key] for role, key in selected.items()}
        clone_call, clone_result = pairs["sourceClone"]
        setter_call, setter_result = pairs["sourceSetWideText"]
        factory_call, factory_result = pairs["ownerFactory"]
        ctor_call, ctor_result = pairs["ownerConstructor"]
        consumer_call, consumer_result = pairs["ownerConsumer"]
        lock_call, lock_result = pairs["sourceLock"]
        source_pointer = clone_result["returnValue"]
        primary_pointer = factory_result["returnValue"]
        if _pointer(source_pointer, nonzero=True) is None or _pointer(primary_pointer, nonzero=True) is None:
            unresolved["nullAllocationResult"] += 1
            continue
        config_rva = module_rva(selector_key[0], memory[config_field])
        dispatch = next((row for row in spec["configDispatchRows"] if row["addressPointRva"] == config_rva), None)
        if dispatch is None:
            issue("bridgeConfigDispatch", before, expected="authenticated config address point and factory route", actual=config_rva)
            continue
        original = before["decodedArguments"]["originalSourcePointer"]
        source_after = snapshot("sourceSetWideText", setter_result, "result")
        consumer_owner = consumer_call["decodedArguments"]["anonymousCallerOwnerPointer"]
        output_pointer = lock_call["decodedArguments"]["mediaRefOutputPointer"]
        consumer_number = _pointer(consumer_owner, nonzero=True)
        if consumer_number is None:
            issue("bridgeOwnerPointer", consumer_call, expected="nonzero bounded recorded consumer owner", actual=str(consumer_owner)[:80])
            continue
        output_after = {name: lock_result["memoryAfter"][field] for name, field in output_maps["sourceLock"].items()}
        expected_consumer = _pointer(primary_pointer, nonzero=True) + owner["consumerOwnerOffset"]
        expected_output = consumer_number + owner["consumerOutputOffset"]
        checks = {
            "originalSource": same(clone_call["decodedArguments"]["originalSourcePointer"], original),
            "descriptorMatch": memory[descriptor_fields["matchWord"]] == snapshot("sourceSelector", before, "entry")[match_field],
            "setterSource": same(setter_call["decodedArguments"]["sourceThisPointer"], source_pointer),
            "setterTextPointer": same(setter_call["decodedArguments"]["descriptorWideTextPointer"], descriptor_pointer),
            "setterText": setter_call["memory"][setter_text_field] == path and setter_result["memoryAfter"][setter_text_field] == path,
            "factorySource": same(factory_call["decodedArguments"]["sourceThisPointer"], source_pointer),
            "constructorSource": same(ctor_call["decodedArguments"]["sourceThisPointer"], source_pointer),
            "constructorOwner": same(ctor_call["decodedArguments"]["anonymousPrimaryOwnerPointer"], primary_pointer) and same(ctor_result["returnValue"], primary_pointer),
            "constructorStoredSource": same(ctor_result["memoryAfter"][stored_source_field], source_pointer),
            "constructorAddressPoint": module_rva(selector_key[0], ctor_result["memoryAfter"][embedded_point_field]) == spec["consumerAddressPointRva"],
            "consumerOwner": expected_consumer < 0x800000000000 and _pointer(consumer_owner) == expected_consumer,
            "consumerSource": same(consumer_call["memory"][consumer_source_field], source_pointer) and same(consumer_result["memoryAfter"][consumer_source_field], source_pointer),
            "lockSource": same(lock_call["decodedArguments"]["sourceThisPointer"], source_pointer),
            "outputAddress": expected_output < 0x800000000000 and _pointer(output_pointer) == expected_output,
            "retainedTextPointer": _pointer(source_after[data_field], nonzero=True) is not None and same(source_after[data_field], output_after[output_data_field]),
            "zeroOutputByteCount": output_after[output_size_field] == 0,
            "siblingSequence": clone_result["seq"] < setter_call["seq"] and setter_result["seq"] < factory_call["seq"] and factory_result["seq"] < consumer_call["seq"],
            "siblingTime": clone_result["monotonicMs"] <= setter_call["monotonicMs"] <= setter_result["monotonicMs"] <= factory_call["monotonicMs"] <= factory_result["monotonicMs"] <= consumer_call["monotonicMs"],
        }
        selector_fields = [count_field, text_field, config_field, serial_field, *descriptor_fields.values()]
        checks["selectorStableFields"] = all(same(memory[field], after["memoryAfter"][field]) for field in selector_fields)
        original_snapshot = snapshot("sourceSelector", before, "entry")
        for role, row, phase in (("sourceClone", clone_call, "entry"), ("sourceClone", clone_result, "result"), ("sourceSetWideText", setter_call, "entry")):
            checks[role + "." + phase + ".originalFields"] = all(same(value, original_snapshot[name]) for name, value in snapshot(role, row, phase).items())
        for role in ("ownerFactory", "ownerConstructor", "sourceLock"):
            for phase, row in zip(("entry", "result"), pairs[role]):
                checks[role + "." + phase + ".selectedFields"] = all(same(value, source_after[name]) for name, value in snapshot(role, row, phase).items())
        for phase, parent_row, child_row in (("entry", consumer_call, lock_call), ("result", consumer_result, lock_result)):
            name = "memory" if phase == "entry" else "memoryAfter"
            checks["consumerOutput." + phase] = all(same(parent_row[name][output_maps["ownerConsumer"][field]], child_row[name][output_maps["sourceLock"][field]]) for field in output_maps["sourceLock"])
        failed = [name for name, valid in checks.items() if not valid]
        if failed:
            issue("bridgePointerTransport", before, expected="reviewed synchronous descriptor/source/owner/output relation", actual={"failedFields": failed[:32], "selectorCaptureId": selector_key[1]})
            continue
        chain_count += 1
        row = grouped.setdefault(path, {"path": path, "chainCount": 0, "samples": []})
        row["chainCount"] += 1
        if sample_count < MAX_SAMPLES and len(row["samples"]) < MAX_PATH_SAMPLES:
            sample_count += 1
            ids = {sample + "CaptureId": selected[role][1] for role, sample in zip(ROLES, SAMPLE_ROLES)}
            row["samples"].append({"sessionId": selector_key[0], **ids, "threadId": before["threadId"],
                "sequence": {sample: [pairs[role][0]["seq"], pairs[role][1]["seq"]] for role, sample in zip(ROLES, SAMPLE_ROLES)},
                "monotonicMs": {sample: [pairs[role][0]["monotonicMs"], pairs[role][1]["monotonicMs"]] for role, sample in zip(ROLES, SAMPLE_ROLES)},
                "originalSourcePointer": original, "selectedSourcePointer": source_pointer,
                "primaryOwnerPointer": primary_pointer, "consumerOwnerPointer": consumer_owner, "outputPointer": output_pointer,
                "descriptorWideTextPointer": descriptor_pointer, "retainedTextPointer": source_after[data_field],
                "playbackSerialWord": memory[serial_field], "configAddressPointRva": config_rva,
                "configDispatchKind": dispatch["dispatchKind"], "sourceAfter": source_after, "lockOutputAfter": output_after})
    ordered = sorted(grouped.values(), key=lambda row: (-row["chainCount"], row["path"]))
    for row in ordered:
        row["samplesTruncated"] = row["chainCount"] > len(row["samples"])
    return {"schema": SCHEMA, "selectorPairCount": len(selectors), "singleDescriptorSelectorCount": single_count,
            "pathChainCount": chain_count, "distinctPathCount": len(ordered), "rows": ordered[:MAX_ROWS],
            "sampleLimit": MAX_SAMPLES, "perPathSampleLimit": MAX_PATH_SAMPLES, "samplesTruncated": chain_count > sample_count,
            "rowLimit": MAX_ROWS, "rowsTruncated": len(ordered) > MAX_ROWS,
            "omittedPathCount": max(0, len(ordered) - MAX_ROWS),
            "omittedChainCount": sum(row["chainCount"] for row in ordered[MAX_ROWS:]),
            "unresolvedCounts": dict(sorted(unresolved.items())), "evidenceBoundary": BOUNDARY}
