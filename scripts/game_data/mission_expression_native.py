"""Authenticate reviewed native Mission parser, Param and objective-path facts.

Large parser bodies are reviewed byte windows, distinct from the small symbolic
control-flow proofs in mission_shared_native. The contract owns build anchors;
this loader verifies current ownership, declarations, bytes and MethodSpec joins.
It never treats an open generic layout as a closed Param field layout.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.context import usage_method_spec, type_parameter_owner, unresolved_usage_index
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.protocol import runtime_type_name
from scripts.game_data.mission_shared_native import OwnedBodyIndex, _gate_row
from scripts.repo_paths import REPO_ROOT

SCHEMA = "endfield.mission-expression-native-contract.v4"
REPORT_SCHEMA = "endfield.mission-expression-native-evaluation.v4"
DEFAULT_CONTRACT = CONTRACTS_DIR / "mission_expression_native.json"


def check_contract(image: Any, contract: dict[str, Any], *, index: Any = None) -> dict[str, Any]:
    """Check a caller-authenticated opened image; no filesystem/native gate here."""
    index = index if index is not None else OwnedBodyIndex(image)
    context = NativeReferenceContext(image, index=index)
    pe, metadata = image.pe, image.metadata
    failures, rows, activation_proofs, selectors, objective_proofs = [], [], [], [], []

    def require(equal: bool, check: str, source: str, expected: Any, actual: Any) -> None:
        if not equal:
            raise ValueError(json.dumps({"failedCheck": check, "sourcePath": source,
                "expected": str(expected)[:500], "actual": str(actual)[:500]}, ensure_ascii=True))

    def check_window(window: dict[str, Any], source: str) -> None:
        start, end = window["startRva"], window["endRva"]
        require(type(start) is int and type(end) is int and 0 <= start < end and end-start <= 65536,
                "window_bounds", source, "bounded 1..65536 byte window", [start, end])
        actual = hashlib.sha256(pe.bytes_at_va(pe.image_base+start, end-start)).hexdigest().upper()
        require(actual == window["sha256"].upper(), "window_sha256", source, window["sha256"], actual)

    def attempt(source: str, fn: Any) -> None:
        try:
            fn()
        except (ValueError, KeyError, IndexError, AttributeError, RuntimeError) as exc:
            try:
                failure = json.loads(str(exc))
                if not isinstance(failure, dict):
                    raise ValueError()
            except (ValueError, TypeError):
                failure = {"failedCheck": "selected_declaration_or_bytes", "sourcePath": source,
                           "expected": "reviewed selected native facts", "actual": str(exc)[:1000]}
            failure["validator"] = "mission_expression_native"
            failures.append(failure)

    def method(symbol: str, spec: dict[str, Any]) -> None:
        method_index, owner, name, entry = spec["method"]
        selected = metadata.methods[method_index]
        actual = metadata.type_full_name(metadata.types[selected.declaring_type])+"."+metadata.string(selected.name_index)
        require(actual == owner+"."+name, "method_identity", symbol, owner+"."+name, actual)
        if "sharedRepresentation" not in spec:
            require(image.method_pointer_va(selected) == pe.image_base+entry, "method_pointer", symbol,
                    entry, image.method_pointer_va(selected)-pe.image_base)
        else:
            actual_indices = {row.get("methodIndex") for row in index.names_by_pointer.get(pe.image_base+entry, ())}
            require(method_index in actual_indices, "registered_shared_method", symbol,
                    method_index, sorted(actual_indices, key=str))
        params = [context.type_name(p.type_index) for p in metadata.parameters_for(selected)]
        require(params == spec["parameters"] and context.type_name(selected.return_type) == spec["returnType"]
                and bool(selected.flags & 16) == spec["static"], "method_signature", symbol,
                [spec["parameters"], spec["returnType"], spec["static"]],
                [params, context.type_name(selected.return_type), bool(selected.flags & 16)])
        pointer = pe.image_base+entry
        regions = [(pointer, index._extent(pointer)), *sorted(index.chained_fragments.get(pointer, ()))]
        expected = [(pe.image_base+w["startRva"], w["endRva"]-w["startRva"]) for w in spec["ownedWindows"]]
        require(regions == expected, "owned_body_regions", symbol, expected, regions)
        for window in spec["ownedWindows"]:
            check_window(window, symbol)
        rows.append({"symbol": symbol, "method": spec["method"], "checkedOwnedWindows": len(regions),
                     "checkedBytes": sum(size for _, size in regions)})

    for symbol, spec in contract["methods"].items():
        attempt(symbol, lambda symbol=symbol, spec=spec: method(symbol, spec))
    for symbol, spec in contract["helpers"].items():
        def helper(symbol: str = symbol, spec: dict = spec) -> None:
            pointer = pe.image_base+spec["entryRva"]
            actual = [(pointer, index._extent(pointer)), *sorted(index.chained_fragments.get(pointer, ()))]
            expected = [(pe.image_base+w["startRva"], w["endRva"]-w["startRva"]) for w in spec["ownedWindows"]]
            require(actual == expected, "helper_owned_regions", symbol, expected, actual)
            for window in spec["ownedWindows"]:
                check_window(window, symbol)
            caller = contract["methods"][spec["calledBy"]]
            body = [r for w in caller["ownedWindows"] for r in index._decode(
                pe.image_base+w["startRva"], w["endRva"]-w["startRva"])]
            targets = [int(r["va"], 16)+5+int.from_bytes(bytes.fromhex(r["bytes"])[1:], "little", signed=True)
                       for r in body if len(bytes.fromhex(r["bytes"])) == 5 and bytes.fromhex(r["bytes"])[0] == 0xe8]
            require(pointer in targets, "helper_direct_caller", symbol, pointer, targets[:32])
        attempt(symbol, helper)
    for qualified, expected in contract["fields"].items():
        attempt(qualified, lambda q=qualified, e=expected: require(list(context.field(q)) == e,
                "typed_field", q, e, list(context.field(q))))
    for enum, expected in contract["enums"].items():
        def check_enum(enum: str = enum, expected: dict = expected) -> None:
            require(context.is_enum(enum) and context.field(enum+"::value__")[1] == "int",
                    "enum_backing", enum, "Int32 enum", context.parent(enum))
            actual = {name: index.enum_member_id(enum, name) for name in expected}
            require(actual == expected, "enum_values", enum, expected, actual)
        attempt(enum, check_enum)
    from scripts.game_data.il2cpp.call_graph import CallGraph, loaded_literals
    graph = CallGraph(image)
    for symbol, expected in contract["literals"].items():
        def literals(symbol: str = symbol, expected: list = expected) -> None:
            actual: set[str] = set()
            for w in contract["methods"][symbol]["ownedWindows"]:
                actual |= loaded_literals(graph, pe.image_base+w["startRva"], w["endRva"]-w["startRva"])
            require(sorted(actual) == expected, "native_literals", symbol, expected, sorted(actual))
        attempt(symbol, literals)
    def caller_contains(caller: str, start: int, size: int) -> None:
        windows = contract["methods"][caller]["ownedWindows"]
        require(any(w["startRva"] <= start and start+size <= w["endRva"] for w in windows),
                "caller_owned_site", caller, "site inside an exact caller window", [start, size])

    def selected_spec(cell: int) -> dict[str, Any]:
        base = int(image.registration["methodSpecs"], 16)
        return usage_method_spec(pe.bytes_at_va(cell, 8), pe.bytes_at_va(base, image.registration["methodSpecsCount"]*12),
            len(metadata.methods), image.instantiations.count, source=str(image.gameassembly), usage_offset=cell, records_offset=base)

    def arguments(selected: dict[str, Any], key: str) -> list[str]:
        value = selected[key]
        return [runtime_type_name(pe, metadata, a.type_pointer_va)
                for a in image.instantiations.resolve(value).arguments] if value >= 0 else []

    for site in contract["callSites"]:
        def call_site(site: dict = site) -> None:
            caller_contains(site["caller"], site["loadRva"], 7)
            caller_contains(site["caller"], site["callRva"], 5)
            load, call = pe.image_base+site["loadRva"], pe.image_base+site["callRva"]
            raw = pe.bytes_at_va(load, 7)
            require(raw[:3] == b"\x4c\x8b\x0d", "methodinfo_load", site["caller"], "R9 RIP qword load", raw.hex())
            cell = load+7+int.from_bytes(raw[3:], "little", signed=True)
            raw_call = pe.bytes_at_va(call, 5)
            target = call+5+int.from_bytes(raw_call[1:], "little", signed=True)
            require(raw_call[0] == 0xe8 and target == pe.image_base+site["targetRva"],
                    "resolver_call", site["caller"], site["targetRva"], target-pe.image_base)
            selected = selected_spec(cell)
            args = arguments(selected, "methodInstantiationIndex")
            require(selected["definition"] == site["methodDefinition"] and selected["classInstantiationIndex"] == -1
                    and args == site["methodArguments"], "caller_methodspec", site["caller"],
                    [site["methodDefinition"], -1, site["methodArguments"]],
                    [selected["definition"], selected["classInstantiationIndex"], args])
        attempt(site["caller"], call_site)
    for site in contract["usageCells"]:
        def usage(site: dict = site) -> None:
            caller_contains(site["caller"], site["loadRva"], 7)
            load = pe.image_base+site["loadRva"]
            raw = pe.bytes_at_va(load, 7)
            require(raw[:3].hex().upper() == site["loadPrefixHex"], "usage_load", site["caller"], site["loadPrefixHex"], raw.hex())
            cell = load+7+int.from_bytes(raw[3:], "little", signed=True)
            if site["kind"] == "type":
                selected = unresolved_usage_index(pe.bytes_at_va(cell, 8), image.registration["typesCount"],
                    tag=1, source=str(image.gameassembly), offset=cell)
                require(context.type_name(selected) == site["name"], "closed_delegate_type", site["caller"],
                        site["name"], context.type_name(selected))
            elif site["kind"] == "method":
                selected = unresolved_usage_index(pe.bytes_at_va(cell, 8), len(metadata.methods),
                    tag=3, source=str(image.gameassembly), offset=cell)
                m = metadata.methods[selected]
                name = metadata.type_full_name(metadata.types[m.declaring_type])+"."+metadata.string(m.name_index)
                actual = [selected, name, image.method_pointer_va(m)-pe.image_base]
                require(actual == [site["methodIndex"], site["name"], site["entryRva"]], "callback_method_usage", site["caller"],
                        [site["methodIndex"], site["name"], site["entryRva"]], actual)
            elif site["kind"] == "methodSpec":
                selected = selected_spec(cell)
                actual = [selected["definition"], arguments(selected, "classInstantiationIndex"), arguments(selected, "methodInstantiationIndex")]
                require(actual == [site["definition"], site["classArguments"], site["methodArguments"]],
                        "event_key_singleton", site["caller"], [site["definition"], site["classArguments"], site["methodArguments"]], actual)
            else:
                require(False, "usage_kind", site["caller"], "type, method or methodSpec", site["kind"])
        attempt(site["caller"], usage)
    for field in contract["wrapperFields"]:
        def wrapper(field: dict = field) -> None:
            owner = field["wrapper"]
            actual = list(context.field(owner+"::__instance"))
            require(actual == field["instanceField"] and actual[1] == "Beyond.Gameplay.Actions.Param`1<"+field["argument"]+">",
                    "closed_wrapper_instance", owner, field["instanceField"], actual)
            for name, value in (("paramSource", field["paramSourceOffset"]), ("constValue", field["constValueOffset"]),
                                ("idRef", field["idRefOffset"]), ("path", field["pathOffset"])):
                spec = contract["methods"][owner+".set___"+name+"__"]
                raw = pe.bytes_at_va(pe.image_base+spec["method"][3], spec["ownedWindows"][0]["endRva"]-spec["ownedWindows"][0]["startRva"])
                opcode = b"\x48\x89\x51" if name == "path" or name == "constValue" and field["argument"] == "string" else b"\x89\x50"
                require(raw.count(opcode+bytes([value])) == 1, "generated_named_setter_cell", owner+"::"+name,
                        opcode.hex()+f"{value:02x}", raw.hex())
            spec = contract["methods"][owner+".CreateInstance"]
            raw = pe.bytes_at_va(pe.image_base+spec["method"][3], spec["ownedWindows"][0]["endRva"]-spec["ownedWindows"][0]["startRva"])
            require(raw.count(b"\x83\x48"+bytes([field["idRefOffset"]])+b"\xff") == 1,
                    "wrapper_default_idref", owner, "named idRef set to -1", raw.hex())
        attempt(field["wrapper"], wrapper)
    def owned_bytes(symbol: str, start: int, raw: bytes, check: str) -> None:
        caller_contains(symbol, start, len(raw))
        actual = pe.bytes_at_va(pe.image_base+start, len(raw))
        require(actual == raw, check, symbol, raw.hex(), actual.hex())

    def named_call(symbol: str, start: int, target: int | None = None, name: str | None = None) -> None:
        caller_contains(symbol, start, 5)
        raw = pe.bytes_at_va(pe.image_base+start, 5)
        actual = start+5+int.from_bytes(raw[1:], "little", signed=True)
        require(raw[0] in (0xe8, 0xe9), "direct_call_opcode", symbol, "direct call or tail jump", raw.hex())
        if target is not None:
            require(actual == target, "parameter_call_target", symbol, target, actual)
        if name is not None:
            require(name in index.names_of(pe.image_base+actual), "parameter_named_reader", symbol,
                    name, index.names_of(pe.image_base+actual)[:12])

    programs = contract["parameterPrograms"]
    for selected in programs["valueConstructors"]:
        def constructor(selected: dict = selected) -> None:
            symbol = selected["method"]
            spec = contract["methods"][symbol]
            raw = pe.bytes_at_va(pe.image_base+spec["method"][3], spec["ownedWindows"][0]["endRva"]-spec["ownedWindows"][0]["startRva"])
            # Complete ordinary constructor bodies have one source-zero store,
            # one path-null store and two sentinel stores around the value copy.
            source = b"\x89\x41"+bytes([selected["sourceOffset"]])
            path = b"\x48\x89\x41"+bytes([selected["pathOffset"]])
            sentinel = b"\xc7\x41"+bytes([selected["idRefOffset"]])+b"\xff"*4
            reference = selected["representation"] == "reference"
            value = (b"\x4d\x89\x4a" if reference else b"\x45\x89\x51")+bytes([selected["constValueOffset"]])
            second = (b"\x41\xc7\x42" if reference else b"\x41\xc7\x41")+bytes([selected["idRefOffset"]])+b"\xff"*4
            endpoint = (len(raw) >= 5 and raw[-5] == 0xe9) if reference else raw.endswith(b"\xc3")
            require(raw.startswith(b"\x48\x83\xec\x28\x33\xc0") and raw.count(source) == 1
                    and raw.count(path) == 1 and raw[6:6+len(sentinel)] == sentinel
                    and raw.count(second) == 1 and raw.count(value) == 1 and endpoint,
                    "value_constructor_stores", symbol, "complete selected zero/null/sentinel/value constructor", raw.hex())
        attempt(selected["method"], constructor)
    for selected in programs["deserializers"]:
        def deserialize(selected: dict = selected) -> None:
            symbol, owner = selected["method"], selected["wrapper"]
            require(selected["countRegister"] in {"sil", "bpl"}, "param_count_register", symbol,
                    "sil or bpl", selected["countRegister"])
            guard = b"\x40\x80\xfe\x04" if selected["countRegister"] == "sil" else b"\x40\x80\xfd\x04"
            owned_bytes(symbol, selected["countGuardRva"], guard, "param_property_count_guard")
            fields = selected["fields"]
            require([field["field"] for field in fields] == ["constValue", "idRef", "paramSource", "path"],
                    "param_reader_field_order", symbol, "constValue,idRef,paramSource,path", [field["field"] for field in fields])
            positions = []
            for field in fields:
                named_call(symbol, field["readCallRva"], target=contract["helpers"][field["readerHelper"]]["entryRva"])
                if "setter" in field:
                    require(field["setter"] == owner+".set___"+field["field"]+"__", "param_named_setter", symbol,
                            owner+".set___"+field["field"]+"__", field["setter"])
                    named_call(symbol, field["setterCallRva"], target=contract["methods"][field["setter"]]["method"][3])
                    positions.extend([field["readCallRva"], field["setterCallRva"]])
                else:
                    wrapper = next(row for row in contract["wrapperFields"] if row["wrapper"] == owner)
                    offsets = {"constValue": wrapper["constValueOffset"], "idRef": wrapper["idRefOffset"],
                               "paramSource": wrapper["paramSourceOffset"], "path": wrapper["pathOffset"]}
                    expected = (b"\x48\x89\x41" if field["field"] in {"constValue", "path"} else b"\x89\x41")+bytes([offsets[field["field"]]])
                    require(bytes.fromhex(field["storeHex"]) == expected, "param_inline_field_cell", symbol,
                            expected.hex(), field["storeHex"])
                    owned_bytes(symbol, field["storeRva"], bytes.fromhex(field["storeHex"]), "param_inline_store")
                    positions.extend([field["readCallRva"], field["storeRva"]])
            require(selected["countGuardRva"] < positions[0] and positions == sorted(set(positions)),
                    "param_reader_site_order", symbol, "guard then four distinct read/store sites in reviewed straight branch", positions)
        attempt(selected["method"], deserialize)
    for selected in programs["activationCalls"]:
        def activation(selected: dict = selected) -> None:
            for site in selected["calls"]:
                named_call(selected["method"], site["callRva"], target=site["targetRva"], name=site["method"])
            positions = [site["callRva"] for site in selected["calls"]]
            require(positions == sorted(set(positions)), "activation_reviewed_site_order", selected["method"],
                    "distinct sites in reviewed normal branch", positions)
            from scripts.game_data.il2cpp.mission_condition_flow import prove_state_activation_order
            owner, _, name = selected["method"].rpartition(".")
            proof = prove_state_activation_order(index, index.body(owner, name))
            require(proof["callOrder"] == [site["method"] for site in selected["calls"]],
                    "activation_branch_order", selected["method"], [site["method"] for site in selected["calls"]], proof["callOrder"])
            activation_proofs.append(proof)
        attempt(selected["method"], activation)
    def generic_declarations() -> None:
        td = index.types["Beyond.Gameplay.Actions.Param`1"]
        declared = {metadata.string(f.name_index): f for f in metadata.fields_for(td)}
        require(context.type_name(declared["paramSource"].type_index) == "int", "param_source_type", "Param`1", "int", context.type_name(declared["paramSource"].type_index))
        require(context.type_name(declared["idRef"].type_index) == "int", "param_idref_type", "Param`1", "int", context.type_name(declared["idRef"].type_index))
        raw = pe.bytes_at_va(context.type_pointer(declared["constValue"].type_index), 16)
        require(raw[10] == 0x13, "param_value_var", "Param`1", "owned VAR", raw.hex())
        variable = int.from_bytes(raw[:8], "little")
        binding = type_parameter_owner(metadata.buf, variable, [t.generic_container_index for t in metadata.types], source=str(image.metadata_path))
        require(binding["typeIndex"] == td.index and binding["ordinal"] == 0,
                "param_value_owner", "Param`1", [td.index, 0], [binding["typeIndex"], binding["ordinal"]])
    attempt("Beyond.Gameplay.Actions.Param`1", generic_declarations)
    attempt("getterLeaf", lambda: check_window(contract["getterLeaf"]["window"], "get_useGetter direct-call leaf"))
    from scripts.game_data.il2cpp.mission_param_flow import prove_source_selector
    for leaf in contract["sourceSelectors"]:
        def selector(leaf: dict = leaf) -> None:
            symbol, entry = leaf["symbol"], pe.image_base+leaf["entryRva"]
            selected = metadata.methods[leaf["methodIndex"]]
            actual = metadata.type_full_name(metadata.types[selected.declaring_type])+"."+metadata.string(selected.name_index)
            require(actual == symbol and metadata.type_full_name(metadata.types[selected.declaring_type]) == "Beyond.Gameplay.Actions.Param`1"
                    and not selected.flags & 16 and selected.parameter_count == 0
                    and context.type_name(selected.return_type) == "bool", "selector_declaration", symbol,
                    "named instance no-argument Boolean getter", actual)
            aliases = index.names_by_pointer.get(entry, ())
            matched = [row for row in aliases if row.get("methodIndex") == leaf["methodIndex"]
                       and [a["typeName"] for a in row.get("classInstantiation", {}).get("arguments", ())] == leaf["classArguments"]
                       and [a["typeName"] for a in row.get("methodInstantiation", {}).get("arguments", ())] == leaf["methodArguments"]]
            require(bool(matched), "selector_registered_context", symbol,
                    [leaf["methodIndex"], leaf["classArguments"], leaf["methodArguments"]], "missing" if not matched else "matched")
            window = leaf["window"]
            require(window["startRva"] == leaf["entryRva"], "selector_entry", symbol, leaf["entryRva"], window["startRva"])
            check_window(window, symbol)
            witnesses = [row for row in contract["wrapperFields"] if row["wrapper"] == leaf["wrapperWitness"]]
            require(len(witnesses) == 1, "selector_cell_witness", symbol, "one checked concrete wrapper", len(witnesses))
            witness = witnesses[0]
            raw = pe.bytes_at_va(entry, window["endRva"]-window["startRva"])
            proof = prove_source_selector(raw, witness["paramSourceOffset"])
            require(proof["selectedSources"] == leaf["selectedSources"], "selector_membership", symbol,
                    leaf["selectedSources"], proof["selectedSources"])
            selectors.append({"symbol": symbol, **proof})
        attempt(leaf["symbol"], selector)
    for site in contract["resolverCalls"]:
        attempt(site["caller"], lambda site=site: named_call(site["caller"], site["callRva"],
                                                           target=site["targetRva"], name=site["method"]))
    def objective_path() -> None:
        from scripts.game_data.il2cpp.mission_condition_flow import prove_objective_initializer, prove_combined_client_activation
        spec = contract["objectiveActivation"]
        if not spec:
            return
        chain = spec["initializerAbsentOverrides"]
        require(bool(chain) and chain[0] == "Beyond.Gameplay.CombineCondition", "objective_inheritance", "objectiveActivation", "CombineCondition ancestry", chain)
        for owner, parent in zip(chain, [*chain[1:], "Beyond.Gameplay.GameCondition"]):
            require(context.parent(owner) == parent, "objective_parent", owner, parent, context.parent(owner))
            declared = [metadata.string(m.name_index) for m in metadata.methods_for(index.types[owner])]
            require("InitAsObjectiveCondition" not in declared, "objective_initializer_override", owner,
                    "no InitAsObjectiveCondition override", [name for name in declared if name == "InitAsObjectiveCondition"])
        for key, fn in (("defaultInitializer", prove_objective_initializer), ("combinedClientLoop", prove_combined_client_activation)):
            owner, _, name = spec[key].rpartition(".")
            require(spec[key] in contract["methods"], "objective_owned_method", key, "authenticated owned method", spec[key])
            objective_proofs.append(fn(index, index.body(owner, name)))
    attempt("objectiveActivation", objective_path)
    return {"status": "validation_failed" if failures else "validated", "methods": [] if failures else rows,
            "diagnostics": failures, "grammar": {} if failures else contract["grammar"],
            "parameterResolution": {} if failures else contract["parameterResolution"],
            "ownerLookup": {} if failures else contract["ownerLookup"],
            "eventPublication": {} if failures else contract["eventPublication"],
            "parameterLoading": {} if failures else contract["parameterLoading"],
            "activationOrderProofs": [] if failures else activation_proofs,
            "sourceSelectors": [] if failures else selectors,
            "objectiveActivation": {} if failures else {**contract["objectiveActivation"], "proofs": objective_proofs},
            "evidenceBoundary": contract["evidenceBoundary"]}


def evaluate(*, image: Any = None, gameassembly: Path | None = None, metadata: Path | None = None,
             contract_path: Path = DEFAULT_CONTRACT, index: Any = None) -> dict[str, Any]:
    contract, digest = read_reviewed_contract(contract_path, schema=SCHEMA, status="reviewed", label="mission_expression")
    native = contract["nativeInputs"]
    if image is not None:
        gameassembly, metadata = image.gameassembly, image.metadata_path
    before = check_installed_native_inputs(native["gameAssemblySha256"], native["metadataSha256"],
                                          gameassembly=gameassembly, metadata=metadata)
    result = {"schema": REPORT_SCHEMA, "status": before.status, "nativeGate": _gate_row(before),
              "contract": {"path": str(contract_path), "sha256": digest}, "methods": [], "diagnostics": []}
    if before.status != "validated":
        return result
    image = image if image is not None else open_native_image(before.gameassembly, before.metadata)
    result.update(check_contract(image, contract, index=index))
    after = check_installed_native_inputs(native["gameAssemblySha256"], native["metadataSha256"],
                                         gameassembly=before.gameassembly, metadata=before.metadata)
    result["nativeGateAfter"] = _gate_row(after)
    if after.status != "validated":
        result.update(status=after.status, methods=[], grammar={}, parameterResolution={}, ownerLookup={}, eventPublication={}, parameterLoading={}, activationOrderProofs=[], sourceSelectors=[], objectiveActivation={})
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gameassembly", type=Path)
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--report", type=Path, default=REPO_ROOT/"reports/runtime_capture/mission-expression-native-reviewed.json")
    args = parser.parse_args(argv)
    path = args.report.resolve()
    if not any(path.is_relative_to(REPO_ROOT/root) for root in ("reports", "scratch", "tmp")):
        parser.error("generated report must stay in reports/, scratch/ or tmp/")
    try:
        result = evaluate(gameassembly=args.gameassembly, metadata=args.metadata)
    except (ValueError, RuntimeError, OSError, KeyError, IndexError, AttributeError) as exc:
        result = {"schema": REPORT_SCHEMA, "status": "validation_failed", "methods": [], "diagnostics": [
            {"validator": "mission_expression_native", "failedCheck": "contract_or_image", "sourcePath": str(DEFAULT_CONTRACT),
             "expected": "selected reviewed native inputs", "actual": str(exc)[:1000]}]}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(result, indent=2)+"\n").encode())
    print(f"Mission expression native: {result['status']}; {len(result['methods'])} methods; {path}")
    if result.get("diagnostics"):
        print(json.dumps(result["diagnostics"][0]))
    return 0 if result["status"] == "validated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
