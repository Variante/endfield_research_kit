"""Typed BuffData event-map and SequenceActionData composition.

The two maps share a sequence element type, not a read order. Every positive
action must return its own recursive named receipt. Unknown actions refuse the
map even when the structural reader happens to know their byte length.
"""
from __future__ import annotations
import hashlib
import json
import struct
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.context import method_spec_usage_index
from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets, runtime_type_name
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.corpus_gate import CensusGateError
from scripts.game_data.memorypack.buff_root_no_positive_native import validate_current_native_contract as root_native
from scripts.game_data.memorypack import buff_recursive_actions as actions

LABEL = "buffEventMaps"
CONTRACT_PATH = CONTRACTS_DIR / "buff_event_maps_native.json"
FAMILIES = {"ability": (0, "abilityEventAction"), "buff": (5, "buffEventAction")}


def _native_fail(check: str, *, expected: Any, actual: Any, family: str,
                 method: Any = None) -> None:
    def bounded(value: Any) -> Any:
        if isinstance(value, str):
            return value if len(value) <= 256 else value[:253] + "..."
        if isinstance(value, dict):
            return {str(k): bounded(v) for k, v in list(value.items())[:16]}
        if isinstance(value, (list, tuple)):
            return [bounded(v) for v in value[:16]]
        return value
    error = CensusGateError(f"{LABEL}.{check}", source=CONTRACT_PATH.as_posix(),
                           expected=bounded(expected), actual=bounded(actual))
    error.diagnostic.update({"validator": LABEL, "family": family, "method": method,
                             "nativeInputs": json.loads(CONTRACT_PATH.read_bytes())["nativeInputs"]})
    error.args = (json.dumps(error.diagnostic, sort_keys=True),)
    raise error


def _runtime_shape(image: Any, section: dict[str, Any], *, family: str) -> None:
    from scripts.game_data.memorypack import named_native_records
    def fail(check, expected, actual):
        _native_fail(check, expected=expected, actual=actual, family=family)
    named_native_records.check_runtime_shape(image, section, label=LABEL, fail=fail)


def validate_current_native_contract() -> dict[str, Any]:
    contract = json.loads(CONTRACT_PATH.read_bytes())
    if (contract.get("schema") != "endfield.buff-shared-event-maps-native-contract.v1"
            or contract.get("status") != "exact-current-build"):
        raise ValueError(f"{LABEL}.contract:shape")
    expected = contract["nativeInputs"]
    gate = check_installed_native_inputs(expected["GameAssembly.dll"], expected["global-metadata.dat"])
    if gate.status != "validated":
        return {"status": gate.status, "detail": gate.detail, "check": "native-inputs",
                "contract": CONTRACT_PATH.as_posix(), "nativeInputs": expected}
    root = root_native()
    if root.get("status") != "validated" or root.get("nativeInputs") != expected:
        _native_fail("root-input-drift", expected={"status": "validated", "nativeInputs": expected},
                     actual={k: root.get(k) for k in ("status", "nativeInputs")}, family="root")
    image = open_native_image(gate.gameassembly, gate.metadata)
    root_contract = json.loads((CONTRACTS_DIR / "buff_root_no_positive_native.json").read_bytes())
    orders = {}
    for family, section in contract["maps"].items():
        dependency = json.loads((CONTRACTS_DIR / section["dependency"]).read_bytes())
        if dependency.get("schemaVersion") != 1:
            raise ValueError(f"{LABEL}.native:{family}-dependency-schema")
        for index in section["methodRows"]:
            image.validate_method_row(dependency["methods"][index], label=f"{LABEL}.{family}")
        image.check_windows([dependency["codeWindows"][i] for i in section["codeWindowRows"]], label=f"{LABEL}.{family}")
        if image.type_name(section["wrapperTypeDefinition"]) != section["wrapperName"]:
            raise ValueError(f"{LABEL}.native:{family}-wrapper")
        owner = image.metadata.types[section["wrapperTypeDefinition"]]
        setters = section.get("setterMethods")
        if setters is None:
            ref = section["setterMethodsReference"]
            declaration = json.loads((CONTRACTS_DIR / ref["path"]).read_bytes())
            if declaration.get("nativeInputs") != expected:
                _native_fail("setter-declaration-build", expected=expected,
                             actual=declaration.get("nativeInputs"), family=family, method=ref)
            setters = declaration[ref["section"]]
        if (image.setter_methods(owner, parameter="typeName", label=LABEL) != [r[:3] for r in setters]
                or [r[0] for r in setters] != [r["setterMethodIndex"] for r in section["parameterTypes"]]
                or [r[1].removeprefix("set___").removesuffix("__") for r in setters] != section["readOrder"]):
            _native_fail("map-setters", expected=setters,
                         actual=image.setter_methods(owner, parameter="typeName", label=LABEL),
                         family=family, method=section["wrapperName"])
        field_index, field_name = FAMILIES[family]
        root_field = root_contract["fields"][field_index]
        if (root_field["name"] != field_name
                or root_field["declaredType"] != f"System.Collections.Generic.List`1<{section['runtimeType']['typeName']}>"
                or next(p["typeName"] for r, p in zip(setters, section["parameterTypes"])
                        if r[1] == "set___actions__") != "Beyond.Gameplay.Core.SequenceActionData[]"):
            raise ValueError(f"{LABEL}.native:{family}-root-or-sequence-typed-join")
        for row in setters:
            image.validate_method_row([row[0], section["wrapperName"], row[1], row[3]], label=LABEL)
        for index in section["contextRows"]:
            context = dependency["nestedContexts"][index]
            cell, usage = image.nested_usage_cell(context, label=LABEL)
            spec_index = method_spec_usage_index(usage, image.registration["methodSpecsCount"], source=LABEL, offset=cell)
            spec = list(struct.unpack("<iii", image.pe.bytes_at_va(int(image.registration["methodSpecs"], 16) + spec_index * 12, 12)))
            args = image.instantiations.resolve(spec[2]).arguments
            if (spec_index != context["methodSpecIndex"] or spec != context["methodSpec"]
                    or len(args) != 1 or args[0].raw_type_record_hex != context["argumentRawHex"]
                    or image.type_name(context["typeDefinition"]) != context["typeName"]):
                _native_fail("typed-context", expected={k: context[k] for k in
                    ("methodSpecIndex", "methodSpec", "argumentRawHex", "typeName")},
                    actual={"methodSpecIndex": spec_index, "methodSpec": spec,
                            "argumentRawHex": [arg.raw_type_record_hex for arg in args],
                            "typeName": image.type_name(context["typeDefinition"])},
                    family=family, method=dependency["methods"][section["methodRows"][-1]][0])
        _runtime_shape(image, section, family=family)
        orders[family] = section["readOrder"]
    from scripts.game_data.memorypack import buff_sequence
    sequence_order = buff_sequence.validate_selected_source(image, contract)
    if orders != {"ability": ["abilityEvent", "actions"], "buff": ["actions", "buffEvent"]}:
        raise ValueError(f"{LABEL}.native:ordered-typed-plan")
    child = actions.validate_current_native_contract()
    if (child.get("status") != "validated" or any(child["nativeInputs"][k] != expected[k]
                                                 for k in ("GameAssembly.dll", "global-metadata.dat"))):
        raise ValueError(f"{LABEL}.native:action-build")
    return {"status": "validated", "nativeInputs": expected, "root": root,
            "mapReadOrders": orders, "sequenceReadOrder": sequence_order, "recursiveActions": child,
            "evidenceBoundary": contract["evidenceBoundary"]}


def recorded_native_validation(native: dict[str, Any]) -> dict[str, Any]:
    """Keep executable registries private while recording every reached gate."""
    return {key: native.get(key) for key in ("status", "nativeInputs", "mapReadOrders", "sequenceReadOrder")} | {
        "recursiveActions": {"status": native.get("recursiveActions", {}).get("status"),
            "children": {name: {"status": child.get("status"), "nativeInputs": child.get("nativeInputs")}
                         for name, child in native.get("recursiveActions", {}).get("children", {}).items()}}}


def contract_source_paths() -> list[Path]:
    """Follow reviewed JSON dependency names; outputs and source payloads are excluded."""
    seen = set()
    pending = [CONTRACT_PATH, actions.damage.CONTRACT_PATH, actions.aura_heal.CONTRACT_PATH,
               actions.skill_stack_interrupt.CONTRACT_PATH, actions.vitals.CONTRACT_PATH,
               actions.data_transfer.CONTRACT_PATH, actions.probability.CONTRACT_PATH,
               actions.selector_children.distance_owner.CONTRACT_PATH, actions.entity_count.CONTRACT_PATH, actions.passive_ui.CONTRACT_PATH,
               actions.cost.CONTRACT_PATH, actions.timed_marker.CONTRACT_PATH,
               actions.armor_condition.CONTRACT_PATH, actions.debug_print.CONTRACT_PATH,
               actions.curve_actions.CONTRACT_PATH, actions.animation_curve.CONTRACT_PATH,
               actions.marker_mask_actions.CONTRACT_PATH, actions.tag_sequence_actions.CONTRACT_PATH,
               actions.spawn_entity.CONTRACT_PATH, actions.camera_impulse.CONTRACT_PATH, actions.leaf_actions.CONTRACT_PATH,
               actions.keyword_actions.CONTRACT_PATH, actions.launch_projectile.CONTRACT_PATH, actions.ignite_text.CONTRACT_PATH,
               actions.global_creation.CONTRACT_PATH, actions.switch.CONTRACT_PATH, actions.weapon_visual.CONTRACT_PATH,
               actions.random_point.CONTRACT_PATH, actions.recover_poise.CONTRACT_PATH,
               actions.spell_infliction.CONTRACT_PATH,
               actions.animation_sequences.CONTRACT_PATH,
               actions.custom_event.CONTRACT_PATH, actions.direct_target_actions.CONTRACT_PATH,
               actions.check_distance.CONTRACT_PATH, actions.shape_finder.CONTRACT_PATH,
               actions.finish_global.CONTRACT_PATH, actions.blow_off.CONTRACT_PATH, actions.cast_skill.CONTRACT_PATH,
               actions.animator_param.CONTRACT_PATH, actions.fixed_point.CONTRACT_PATH,
               actions.postprocessors.CONTRACT_PATH, actions.direction_children.CONTRACT_PATH,
               actions.camera_control_state.CONTRACT_PATH]
    def references(value: Any):
        if isinstance(value, dict):
            for child in value.values():
                yield from references(child)
        elif isinstance(value, list):
            for child in value:
                yield from references(child)
        elif isinstance(value, str) and Path(value).name == value and value.endswith(".json"):
            path = CONTRACTS_DIR / value
            if path.is_file():
                yield path
    while pending:
        path = pending.pop().resolve()
        if path in seen:
            continue
        seen.add(path)
        pending.extend(references(json.loads(path.read_bytes())))
    return sorted(seen)


def validate_recorded_event_children(receipt: dict[str, Any], *, native_validation: dict[str, Any],
                                     root_native: dict[str, Any]) -> None:
    """Check recorded typed ownership before the canonical original-byte replay."""
    required = ("create", "iconDuration", "createInput", "blackboard", "target", "effect",
                "effectVectors", "direction", "selector", "characterTeamFinder",
                "finish", "findSettings", "armor", "armorValues", "directTargetActions",
                "ownerSpawnedFinder", "zeroValidators", "tagQueryValidator", "ifElse",
                "compare", "modify", "checkStack", "buffIdActions", "blackboardString", "selectorGeometry", "randomPointFinder", "recoverPoise", "spellInfliction",
                "checkDistance", "shapeFinder", "colliderShape", "animationSequenceActions", "customAbilityEvent", "finishGlobal", "blowOff", "castSkill", "animatorParamAction", "cameraControlState", "fixedPointFinder", "selectorPostprocessors", "directionTargets",
                "damage", "auraHeal", "skillStackInterrupt", "vitals", "dataTransfer", "probability", "distanceValidator", "entityCount", "passiveUi",
                "cost", "timedMarker", "superArmorCondition", "debugPrint", "animationCurve", "curveActions", "markerMaskActions", "sequence", "tagSequenceActions", "spawnEntity", "cameraImpulse", "leafActions", "keywordActions", "launchProjectile", "igniteText", "globalCreation", "switch", "weaponVisual")
    children = native_validation.get("recursiveActions", {}).get("children", {})
    expected_inputs = root_native.get("nativeInputs") or {}
    failed_children = [key for key in required
                       if children.get(key, {}).get("status") != "validated"
                       or any(children.get(key, {}).get("nativeInputs", {}).get(name) != expected_inputs.get(name)
                              for name in ("GameAssembly.dll", "global-metadata.dat"))]
    if (native_validation.get("status") != "validated"
            or native_validation.get("nativeInputs") != root_native.get("nativeInputs")
            or native_validation.get("mapReadOrders") != {"ability": ["abilityEvent", "actions"], "buff": ["actions", "buffEvent"]}
            or native_validation.get("sequenceReadOrder") != ["actionData", "onlyExecuteWhenSourceIsGuard", "onlyExecuteWhenSourceIsMainChar"]
            or native_validation.get("recursiveActions", {}).get("status") != "validated"
            or failed_children):
        raise CensusGateError("buff-shared-event-native-receipt", source=receipt.get("source", ""),
                              expected="current root, map, sequence, and recursive action gates",
                              actual={"status": native_validation.get("status"), "failedChildren": failed_children,
                                      "nativeInputs": native_validation.get("nativeInputs")})
    fields = receipt.get("fields") or []
    for family, (index, name) in FAMILIES.items():
        field = fields[index] if len(fields) == 30 else {}
        child = field.get("child") or {}
        if (field.get("name") != name or child.get("schema") != "endfield.buff-event-map-list-receipt.v1"
                or child.get("status") != "named-event-map-list-exact"
                or child.get("family") != family or child.get("rootFieldIndex") != index
                or child.get("rootFieldName") != name
                or child.get("wholeStoredSchemaExact") is not True
                or child.get("source") != receipt.get("source")
                or child.get("logicalSha256") != receipt.get("logicalSha256")
                or [child.get("start"), child.get("end")] != [field.get("start"), field.get("end")]
                or child.get("count") != field.get("count")
                or type(child.get("count")) is not int or child["count"] < -1
                or len(child.get("maps") or []) != max(0, child["count"])):
            raise CensusGateError("buff-shared-event-parent-child-join", source=receipt.get("source", ""),
                                  expected={"field": name, "family": family, "span": [field.get("start"), field.get("end")]},
                                  actual={key: child.get(key) for key in ("status", "family", "start", "end", "count", "wholeStoredSchemaExact")})


def decode_event_map_list(data: bytes, *, source: str, logical_sha256: str,
                          start: int, end: int, family: str,
                          native_validation: dict[str, Any], require_end: bool = True) -> dict[str, Any]:
    """Read a typed list from its first count, composing each original action."""
    if family not in FAMILIES or native_validation.get("status") != "validated":
        raise ValueError(f"{LABEL}:native-or-family")
    if (not isinstance(data, bytes) or not source or type(start) is not int or type(end) is not int
            or not 0 <= start < end <= len(data)
            or not isinstance(logical_sha256, str)
            or hashlib.sha256(data).hexdigest().upper() != logical_sha256.upper()):
        raise ValueError(f"{LABEL}:source-range-or-sha256")
    expected_order = ["abilityEvent", "actions"] if family == "ability" else ["actions", "buffEvent"]
    if (native_validation.get("mapReadOrders", {}).get(family) != expected_order
            or native_validation.get("sequenceReadOrder") != ["actionData", "onlyExecuteWhenSourceIsGuard", "onlyExecuteWhenSourceIsMainChar"]
            or native_validation.get("recursiveActions", {}).get("status") != "validated"):
        raise ValueError(f"{LABEL}:native-plan")
    reader = Reader(data, source, end)
    reader.pos = start
    def read_sequence() -> dict[str, Any]:
        from scripts.game_data.memorypack import buff_sequence
        begin = reader.pos
        value = buff_sequence.decode_value(data, source, logical_sha256, begin, reader.limit,
            native_validation["recursiveActions"], 0, require_end=False)
        reader.pos = value["end"]
        if value["status"] == "exact-null":
            return {"start": begin, "end": reader.pos, "status": "exact-null", "namedFields": []}
        fields = [{"name": "actionData", "start": begin + 1, "end": value["flags"][0]["start"],
                   "count": value["count"], "elements": value["actions"]}, *value["flags"]]
        return {"start": begin, "end": reader.pos, "status": "named-sequence-exact", "namedFields": fields}
    count = reader.count(1, nullable=True)
    maps = []
    for _ in range(max(0, count)):
        begin = reader.pos
        if reader.peek() == 0xFF:
            reader.take(1, "null-map")
            maps.append({"start": begin, "end": reader.pos, "status": "exact-null", "namedFields": []})
            continue
        reader.header(2)
        fields = []
        for name in expected_order:
            a = reader.pos
            if name == "actions":
                n = reader.count(1, reserve=4 if family == "buff" else 0, nullable=True)
                sequences = [read_sequence() for _ in range(max(0, n))]
                fields.append({"name": name, "start": a, "end": reader.pos, "count": n, "elements": sequences})
            else:
                raw = reader.take(4, name)
                fields.append({"name": name, "start": a, "end": reader.pos, "rawHex": raw.hex().upper()})
        maps.append({"start": begin, "end": reader.pos, "status": "named-map-exact", "namedFields": fields})
    if require_end and reader.pos != end:
        raise ValueError(f"{LABEL}:field-end={reader.pos}; expected={end}")
    return {"schema": "endfield.buff-event-map-list-receipt.v1", "status": "named-event-map-list-exact",
            "source": source, "logicalSha256": logical_sha256.upper(), "family": family,
            "rootFieldIndex": FAMILIES[family][0], "rootFieldName": FAMILIES[family][1],
            "start": start, "end": reader.pos, "count": count, "maps": maps,
            "wholeStoredSchemaExact": True, "liveProviderSelectionKnown": False,
            "runtimeEventExecutionKnown": False, "wholeBuffDataExact": False}
