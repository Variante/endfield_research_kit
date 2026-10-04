"""Validate reviewed LevelScript union Deserialize call order on a selected build.

The contract records a bounded native body and each read/setter call pair. A
validated row proves the generated reader consumes the named fields in order;
the shared ActionSerializedMap codec still owns the wire cursor and corpus gate.

It covers the promoted routes of `action_map_layouts.json` (ActionBase,
GetterBase and ActionHeader), checking each selected reader's body hash and
ordered read/setter calls. A missing or different installed build returns no
validated rows. The audit is written to
`reports/game_data/levelscript_route_deserialize_native.json` (`--report`).

The selected union branch establishes wrapper identity; the generated
`Deserialize` body establishes member count and read order. Rows named here
include `ScriptEvent_OnScriptEnd`, which adds a `ScriptEndReason` parameter
whose underlying value is a signed integer, and `NpcProxyGetter`, which adds
one string parameter. The same contract schema is reused by
`levelscript_entity_attach_native.json` and
`levelscript_spawner_camera_native.json`, which the route codecs
`codecs.levelscript.entity_attach` and `codecs.levelscript.spawner_camera`
read. None of these rows proves evaluation, execution or event causality.

The stored-route contract also covers shared decoration, transform,
interactive-state, focus-toast, cinematic-control, bounty-registration and
rolling-stone-launcher actions, plus the integer-subtraction getter's stored
operands. It reuses reviewed Param grammars, including
bounded entity/ID/blackboard lists and mask values; it does not widen their
accepted child shapes. A newly admitted enum Param must additionally declare
its underlying type, checked against the selected metadata's value__ field.
V3 additionally requires a typed ReadPackable context and reviewed default
collection composition for plain lists. The integer switch's List<int>
registration, concrete list/primitive readers and symbolic generic contexts
establish count-plus-Int32 storage independently of live provider replacement.
Typed output parameters require their own selected ReadValue contexts, even
when an established wire grammar is shared with another output type. The
patrol-event header retains entity, key and patrol-ID outputs, while the
camera-effect action retains an effect-ID output. Header filter/trigger enums
additionally require an explicit signed-Int32 backing declaration. The stored
NPC name/proxy operands and challenge-banner action use existing Param and
base-action grammars. None establishes a resolved output or an event firing.

Run as: python -m scripts.game_data.levelscript_route_deserialize_native
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import struct
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs, write_canonical_json
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.il2cpp.context import generic_method_candidates, method_spec_record, method_spec_usage_index
from scripts.game_data.il2cpp.formatter_composition import _vtable, validate_generic_contexts, validate_typed_usage_context
from scripts.game_data.il2cpp.native_image import NativeImage
from scripts.game_data.il2cpp.protocol import runtime_type_name
from scripts.game_data.memorypack.union_dispatch import read_union_switch
from scripts.game_data.memorypack.wrapper_members import derive_from_image
from scripts.repo_paths import REPO_ROOT


CONTRACT_PATH = CONTRACTS_DIR / "levelscript_route_deserialize_native.json"
LAYOUT_PATH = REPO_ROOT / "scripts/game_data/codecs/levelscript/action_map_layouts.json"
DEFAULT_REPORT = REPO_ROOT / "reports/game_data/levelscript_route_deserialize_native.json"
SCHEMA = "endfield.levelscript-route-deserialize-native.v1"
TYPED_SCHEMA = "endfield.levelscript-route-deserialize-native.v2"
COLLECTION_SCHEMA = "endfield.levelscript-route-deserialize-native.v3"
UNION_BASES = {
    "ActionBase": "Beyond_Gameplay_Actions_ActionBaseForMemoryPack",
    "GetterBase": "Beyond_Gameplay_Actions_PureGetterForMemoryPack",
    "ActionHeader": "Beyond_Gameplay_Actions_ActionHeaderForMemoryPack",
}
PARAM_ENUM_UNDERLYING = {'Beyond.Gameplay.Actions.Param`1<Beyond.GEnums.GeneralAbilityType>': ('Beyond.GEnums.GeneralAbilityType',
                                                                       'int'),
 'Beyond.Gameplay.Actions.Param`1<Beyond.Gameplay.Actions.ShowUIToast+ShowToastType>': ('Beyond.Gameplay.Actions.ShowUIToast+ShowToastType',
                                                                                        'int'),
 'Beyond.Gameplay.Actions.Param`1<Beyond.Gameplay.MountPoint>': ('Beyond.Gameplay.MountPoint',
                                                                 'int'),
 'Beyond.Gameplay.Actions.Param`1<Beyond.Gameplay.RollingStoneController+ManipulateLauncherOp>': ('Beyond.Gameplay.RollingStoneController+ManipulateLauncherOp',
                                                                                                  'int'),
    'Beyond.Gameplay.Actions.Param`1<Beyond.Gameplay.Core.MovementComponent+GroundedMoveGait>': ('Beyond.Gameplay.Core.MovementComponent+GroundedMoveGait', 'int')}
HEADER_ENUM_UNDERLYING = {
    name: (name, "int") for name in (
        "Beyond.Gameplay.Actions.FilterLevel",
        "Beyond.Gameplay.Actions.FilterMask",
        "Beyond.Gameplay.Actions.TriggerActiveDuring",
        "Beyond.Gameplay.Actions.EntityEventHeader+TriggerTarget",
    )
}


def _relative_call_target(image: NativeImage, rva: int) -> int:
    raw = image.pe.bytes_at_va(image.pe.image_base + rva, 5)
    if raw[0] != 0xE8:
        raise ValueError(f"levelscriptRouteDeserialize.native:not-relative-call={rva:#x}")
    return rva + 5 + struct.unpack_from("<i", raw, 1)[0]


def _runtime_parameter_name(image: NativeImage, type_index: int) -> str:
    types = int(image.registration["types"], 16)
    type_va = image.pe.u64_at_va(types + type_index * 8)
    return runtime_type_name(image.pe, image.metadata, type_va)


def _typed_read_context(image: NativeImage, item: dict[str, Any], previous: int) -> None:
    """Join the actual ReadValue instruction to its selected generic argument."""
    context = item["typedReadContext"]
    reader_method = "ReadPackable" if item["declaredType"] == "System.Collections.Generic.List`1<int>" else "ReadValue"
    if (not previous < context["instructionRva"] < item["readCallRva"]
            or not context["instructionHex"].upper().startswith("488B15")):
        raise ValueError(f"levelscriptRouteDeserialize.native:typed-context-order={item['name']}")
    cell, usage = image.nested_usage_cell(context, label="levelscriptRouteDeserialize")
    index = method_spec_usage_index(
        usage, image.registration["methodSpecsCount"], source="levelscriptRouteDeserialize", offset=cell,
    )
    address = int(image.registration["methodSpecs"], 16) + index * 12
    spec = method_spec_record(
        image.pe.bytes_at_va(address, 12), len(image.metadata.methods),
        image.registration["genericInstsCount"], source="levelscriptRouteDeserialize", offset=address,
    )
    method = image.metadata.methods[spec[0]]
    if (index != context["methodSpecIndex"] or list(spec) != context["methodSpec"]
            or image.type_name(method.declaring_type) != "MemoryPack.MemoryPackReader"
            or image.metadata.string(method.name_index) != reader_method
            or context["readerType"] != "MemoryPack.MemoryPackReader"
            or context["readerMethod"] != reader_method):
        raise ValueError(f"levelscriptRouteDeserialize.native:typed-context-method={item['name']}")
    instance = image.instantiations.resolve(spec[2])
    if len(instance.arguments) != 1:
        raise ValueError(f"levelscriptRouteDeserialize.native:typed-context-arity={item['name']}")
    argument = instance.arguments[0]
    actual = runtime_type_name(image.pe, image.metadata, argument.type_pointer_va)
    if (actual != item["declaredType"] or actual != context["argumentType"]
            or argument.raw_type_record_hex.upper() != context["argumentRawHex"].upper()):
        raise ValueError(f"levelscriptRouteDeserialize.native:typed-context-argument={item['name']}:expected={item['declaredType']}:actual={actual}")


def _typed_route(image: NativeImage, bodies: BodyIndex, wrapper: Any, row: dict[str, Any]) -> None:
    """V2 additionally proves complete body extent, header and typed members."""
    key = row["family"], row["tag"]
    members = wrapper.members
    if (wrapper.name != row["wrapperName"] or wrapper.wrapped_type != row["typeName"]
            or wrapper.type_definition != row["typeDefinition"]
            or len(members) != row["memberCount"]
            or len(wrapper.inherited_members) != row["inheritedMemberCount"]
            or [[member.name.lstrip("_"), member.declared_type, member.declaring_wrapper, member.method_index]
                for member in members] != [[item["name"], item["declaredType"], item["declaringWrapper"], item["setterMethodIndex"]]
                                          for item in row["readOrder"]]):
        raise ValueError(f"levelscriptRouteDeserialize.native:wrapper-members={key}")
    aliases = {'Beyond.GEnums.ScopeName': 'int32',
 'Beyond.Gameplay.Actions.FilterLevel': 'int32',
 'Beyond.Gameplay.Actions.FilterMask': 'int32',
 'Beyond.Gameplay.Actions.TriggerActiveDuring': 'int32',
 'Beyond.Gameplay.Actions.EntityEventHeader+TriggerTarget': 'int32',
 'Beyond.Gameplay.Actions.ParamOutput`1<Beyond.Gameplay.Core.EntityPtr>': 'ParamOutput<EntityPtr>',
 'Beyond.Gameplay.Actions.ParamOutput`1<int>': 'ParamOutput<int>',
 'Beyond.Gameplay.Actions.ParamOutput`1<string>': 'ParamOutput<string>',
 'Beyond.Gameplay.Actions.ParamOutput`1<ulong>': 'ParamOutput<ulong>',
 'Beyond.Gameplay.Actions.Param`1<Beyond.GEnums.GeneralAbilityType>': 'Param<GeneralAbilityType>',
 'Beyond.Gameplay.Actions.Param`1<Beyond.Gameplay.Actions.ShowUIToast+ShowToastType>': 'Param<ShowUIToast.ShowToastType>',
 'Beyond.Gameplay.Actions.Param`1<Beyond.Gameplay.CommonMaskBlendData>': 'Param<CommonMaskBlendData>',
 'Beyond.Gameplay.Actions.Param`1<Beyond.Gameplay.Core.EntityPtr>': 'Param<EntityPtr>',
 'Beyond.Gameplay.Actions.Param`1<Beyond.Gameplay.Core.GameplayTag>': 'Param<GameplayTag>',
 'Beyond.Gameplay.Actions.Param`1<Beyond.Gameplay.Core.GlobalBuffId>': 'Param<GlobalBuffId>',
 'Beyond.Gameplay.Actions.Param`1<Beyond.Gameplay.Core.LevelScriptPtr>': 'Param<LevelScriptPtr>',
 'Beyond.Gameplay.Actions.Param`1<Beyond.Gameplay.Core.LsmPtr>': 'Param<LsmPtr>',
 'Beyond.Gameplay.Actions.Param`1<Beyond.Gameplay.MountPoint>': 'Param<MountPoint>',
 'Beyond.Gameplay.Actions.Param`1<Beyond.Gameplay.RollingStoneController+ManipulateLauncherOp>': 'Param<RollingStoneController.ManipulateLauncherOp>',
 'Beyond.Gameplay.Actions.Param`1<Beyond.LangKey>': 'Param<LangKey>',
 'Beyond.Gameplay.Actions.Param`1<System.Collections.Generic.List`1<Beyond.BlackboardKVPair>>': 'Param<List<BlackboardKVPair>>',
 'Beyond.Gameplay.Actions.Param`1<System.Collections.Generic.List`1<Beyond.Gameplay.Actions.NpcAtmosphericOverrideEnvTalk+EnvTalkStruct>>': 'Param<List<NpcAtmosphericOverrideEnvTalk.EnvTalkStruct>>',
 'Beyond.Gameplay.Actions.Param`1<System.Collections.Generic.List`1<Beyond.Gameplay.Actions.NpcOverrideEnvTalk+EnvTalkStruct>>': 'Param<List<NpcOverrideEnvTalk.EnvTalkStruct>>',
 'Beyond.Gameplay.Actions.Param`1<System.Collections.Generic.List`1<Beyond.Gameplay.Actions.NpcProxyOverrideEnvTalk+EnvTalkStruct>>': 'Param<List<NpcProxyOverrideEnvTalk.EnvTalkStruct>>',
 'Beyond.Gameplay.Actions.Param`1<System.Collections.Generic.List`1<Beyond.Gameplay.Core.EntityPtr>>': 'Param<List<EntityPtr>>',
 'Beyond.Gameplay.Actions.Param`1<System.Collections.Generic.List`1<ulong>>': 'Param<List<ulong>>',
 'Beyond.Gameplay.Actions.Param`1<UnityEngine.Vector3>': 'Param<Vector3>',
 'Beyond.Gameplay.Actions.Param`1<bool>': 'Param<bool>',
 'Beyond.Gameplay.Actions.Param`1<float>': 'Param<float>',
 'Beyond.Gameplay.Actions.Param`1<int>': 'Param<int>',
 'Beyond.Gameplay.Actions.Param`1<string>': 'Param<string>',
 'Beyond.Gameplay.Actions.Param`1<uint>': 'Param<uint>',
 'Beyond.Gameplay.Actions.Param`1<ulong>': 'Param<ulong>',
 'Beyond.Gameplay.DestroyBallReason': 'int32',
 'System.Collections.Generic.List`1<int>': 'List<int>',
 'bool': 'bool',
 'int': 'int32',
 'string': 'string',
    'Beyond.Gameplay.Actions.ParamOutput`1<float>': 'ParamOutput<float>',
    'Beyond.Gameplay.Actions.Param`1<Beyond.Gameplay.Core.MovementComponent+GroundedMoveGait>': 'Param<MovementComponent.GroundedMoveGait>',
    'Beyond.Gameplay.Actions.Param`1<System.Collections.Generic.List`1<int>>': 'Param<List<int>>'}
    if [[member.name.lstrip("_"), aliases.get(member.declared_type)] for member in members] != row["fields"]:
        raise ValueError(f"levelscriptRouteDeserialize.native:codec-kinds={key}")
    for member in members:
        if (aliases.get(member.declared_type) == "int32" and member.declared_type != "int"
                and (member.kind, member.underlying_kind, member.width) != ("enum", "scalar32", 4)):
            raise ValueError(f"levelscriptRouteDeserialize.native:scope-enum-backing={key}")
    body = bodies.body(row["wrapperName"], "Deserialize")
    base = image.pe.image_base
    fragments = row["deserializeFragmentWindows"]
    image.check_windows(fragments, label="levelscriptRouteDeserialize")
    actual_fragments = [(start-base, start+size-base) for start, size in bodies.chained_fragments.get(body.pointer, ())]
    recorded_fragments = [(fragment["startRva"], fragment["endRva"]) for fragment in fragments]
    if (body.pointer != base + row["deserializeRva"] or body.size != row["normalBodyLength"]
            or actual_fragments != recorded_fragments
            or any(not any(base+start <= int(value["va"], 16) < base+end for start, end in recorded_fragments)
                   for value in body.fragment_rows)):
        raise ValueError(f"levelscriptRouteDeserialize.native:complete-method-window={key}")
    instruction = row["memberCountInstruction"]
    count_row = next((value for value in body.rows if int(value["va"], 16) == base + instruction["rva"]), None)
    if (count_row is None or count_row["bytes"].replace(" ", "").upper() != instruction["hex"].upper()
            or not count_row["text"].startswith("cmp ")
            or int(count_row["text"].rsplit(", ", 1)[-1], 0) != row["memberCount"]
            or not row["deserializeRva"] < instruction["rva"] < row["readOrder"][0]["readCallRva"]):
        raise ValueError(f"levelscriptRouteDeserialize.native:member-count-instruction={key}")
    previous = instruction["rva"]
    for item in row["readOrder"]:
        is_param = item["declaredType"].startswith((
            "Beyond.Gameplay.Actions.Param`1<", "Beyond.Gameplay.Actions.ParamOutput`1<",
        )) or item["declaredType"] == "System.Collections.Generic.List`1<int>"
        if is_param != ("typedReadContext" in item):
            raise ValueError(f"levelscriptRouteDeserialize.native:required-typed-context={key}/{item['name']}")
        if is_param:
            _typed_read_context(image, item, previous)
        previous = item["setterCallRva"]


def _validate_collection_readers(image: NativeImage, contract: dict[str, Any]) -> None:
    """Join reviewed default collection registration, contexts and concrete ABI."""
    rows = contract.get("collectionReaders", [])
    needed = {kind for route in contract["routes"] for _, kind in route["fields"] if kind.startswith("List<")}
    if len(rows) != len(needed) or {row["codecKind"] for row in rows} != needed:
        raise ValueError("levelscriptRouteDeserialize.contract:collection-reader-set")
    for row in rows:
        if (row["codecKind"], row["declaredType"], row["elementType"], row["storedCountWidth"], row["storedElementWidth"], row["nullCount"]) != (
                "List<int>", "System.Collections.Generic.List`1<int>", "int", 4, 4, -1):
            raise ValueError("levelscriptRouteDeserialize.contract:collection-grammar")
        allocation, constructor, registration = [row[key] for key in ("allocation", "constructor", "registration")]
        if (allocation["typeName"] != "MemoryPack.Formatters.ListFormatter`1<int>"
                or constructor["typeName"] != "MemoryPack.Formatters.ListFormatter`1"
                or constructor["methodName"] != ".ctor" or constructor["classArguments"] != ["int"]
                or registration["typeName"] != "MemoryPack.MemoryPackFormatterProvider"
                or registration["methodName"] != "Register" or registration["methodArguments"] != [row["declaredType"]]
                or not allocation["instructionRva"] < constructor["instructionRva"] < registration["instructionRva"]):
            raise ValueError("levelscriptRouteDeserialize.contract:collection-registration")
        for usage in (allocation, constructor, registration):
            validate_typed_usage_context(image, usage, label="levelscriptCollection")
        instructions = row["registrationInstructions"]
        if not {"mov rbx, rax", "mov rcx, rax", "mov rcx, rbx"} <= {item["text"] for item in instructions}:
            raise ValueError("levelscriptRouteDeserialize.contract:collection-registration-flow")
        image.check_instruction_windows([[int(item["va"], 16)-image.pe.image_base, item["bytes"]] for item in instructions], label="levelscriptCollection")
        image.check_windows(row["codeWindows"], label="levelscriptCollection")
        contexts = {(item["typeName"], item.get("methodName")) for item in row["genericContexts"]}
        if not {("MemoryPack.Formatters.ListFormatter`1", None),
                ("MemoryPack.MemoryPackReader", "ReadPackable"),
                ("MemoryPack.MemoryPackFormatterProvider", "GetFormatter")} <= contexts:
            raise ValueError("levelscriptRouteDeserialize.contract:collection-context-owners")
        if (len(row["semanticInstructions"]) != 4 or {item["claim"] for item in row["semanticInstructions"]}
                != {"cmp [rdx+0x30], 0x4", "cmp r12d, -0x1", "mov [rdx+0x20+rcx*4], r12d"}):
            raise ValueError("levelscriptRouteDeserialize.contract:collection-wire-witnesses")
        image.check_instruction_windows([[item["rva"], item["hex"]] for item in row["semanticInstructions"]], label="levelscriptCollection")
        validate_generic_contexts(image, row["genericContexts"], label="levelscriptCollection")
        bindings = row["genericBodies"]
        if len(bindings) != 2 or {item["typeName"] for item in bindings} != {
                "MemoryPack.Formatters.ListFormatter`1", "MemoryPack.Formatters.UnmanagedFormatter`1"}:
            raise ValueError("levelscriptRouteDeserialize.contract:collection-concrete-readers")
        code = image.mapper.code_registration_summary(image.pe, image.code_registration)
        table_va = int(image.registration["genericMethodTable"], 16)
        table = image.pe.bytes_at_va(table_va, image.registration["genericMethodTableCount"]*16)
        for binding in bindings:
            index = binding["methodSpecIndex"]
            address = int(image.registration["methodSpecs"],16) + index*12
            spec = method_spec_record(image.pe.bytes_at_va(address,12), len(image.metadata.methods), image.registration["genericInstsCount"], source="levelscriptCollection", offset=address)
            method = image.metadata.methods[spec[0]]
            args = [runtime_type_name(image.pe,image.metadata,arg.type_pointer_va) for arg in image.instantiations.resolve(spec[1]).arguments]
            if (list(spec) != binding["methodSpec"] or spec[2] != -1 or args != ["int"]
                    or image.type_name(method.declaring_type) != binding["typeName"]
                    or image.metadata.string(method.name_index) != "Deserialize"):
                raise ValueError("levelscriptRouteDeserialize.native:collection-reader-identity")
            _vtable(image, method.declaring_type, 5, spec[0], "levelscriptCollection")
            candidates = generic_method_candidates(table, image.registration["genericMethodTableCount"], image.registration["methodSpecsCount"], {index}, code["genericMethodPointersCount"], code["invokerPointersCount"], source="levelscriptCollection", offset=table_va)
            for candidate in candidates:
                candidate["pointerRva"] = image.pe.u64_at_va(int(code["genericMethodPointers"],16)+candidate["indices"][0]*8)-image.pe.image_base
            if candidates != binding["codeCandidates"] or len(candidates) != 1:
                raise ValueError("levelscriptRouteDeserialize.native:collection-reader-code")
            if candidates[0]["pointerRva"] not in {window["startRva"] for window in row["codeWindows"]}:
                raise ValueError("levelscriptRouteDeserialize.contract:collection-reader-window")


def _source_receipts(contract: dict[str, Any], export_root: Path, ledger_path: Path, summary_path: Path) -> int:
    """Replay only declared native-proved spans joined to a complete receipt."""
    summary = json.loads(summary_path.read_bytes())
    output = summary.get("provenance", {}).get("outputFiles", {})
    if (summary.get("status") != "complete" or output.get("length") != ledger_path.stat().st_size
            or output.get("sha256", "").upper() != hashlib.sha256(ledger_path.read_bytes()).hexdigest().upper()):
        raise ValueError("levelscriptRouteDeserialize.source:summary-ledger-join")
    ledger: dict[str, dict[str, Any]] = {}
    with gzip.open(ledger_path, "rt", encoding="utf8") as stream:
        for line in stream:
            row = json.loads(line)
            if row.get("family") == "LevelScriptData":
                path = row["exportRelativePath"]
                if path in ledger:
                    raise ValueError(f"levelscriptRouteDeserialize.source:duplicate-ledger-row={path}")
                ledger[path] = row
    from scripts.game_data.codecs.levelscript.action_map import _Cursor

    checked = 0
    root = export_root.resolve()
    for route in contract["routes"]:
        if not route.get("sourceReceipts"):
            raise ValueError(f"levelscriptRouteDeserialize.source:missing-route-receipt={route['family']}/{route['tag']}")
        tag = route["tag"]
        prefix = (bytes((tag,)) if tag < 250 else b"\xFA" + struct.pack("<H", tag)) + bytes((route["memberCount"],))
        for path, digest, start, end, span_digest in route["sourceReceipts"]:
            source = (root / path).resolve()
            if not source.is_relative_to(root):
                raise ValueError(f"levelscriptRouteDeserialize.source:outside-export-root={path}")
            data = source.read_bytes()
            actual = hashlib.sha256(data).hexdigest().upper()
            if (actual != digest.upper() or ledger.get(path, {}).get("logicalSha256", "").upper() != digest.upper()
                    or ledger.get(path, {}).get("length") != len(data)):
                raise ValueError(f"levelscriptRouteDeserialize.source:source-ledger-join={path}:expected={digest}/{len(data)}:actual={actual}")
            if not 0 <= start < end <= len(data) or data[start:start+len(prefix)] != prefix:
                raise ValueError(f"levelscriptRouteDeserialize.source:union-prefix={path}@{start}:expected={prefix.hex().upper()}")
            if hashlib.sha256(data[start:end]).hexdigest().upper() != span_digest.upper():
                raise ValueError(f"levelscriptRouteDeserialize.source:span-sha256={path}@{start}:expected={span_digest}")
            cursor = _Cursor(data, start + len(prefix))
            for name, kind in route["fields"]:
                try:
                    cursor.value(kind, "storedRoutes." + name)
                except (ValueError, IndexError) as exc:
                    raise ValueError(f"levelscriptRouteDeserialize.source:field={path}@{cursor.offset}/{name}:{exc}") from exc
            if cursor.offset != end:
                raise ValueError(f"levelscriptRouteDeserialize.source:end-offset={path}:expected={end}:actual={cursor.offset}")
            checked += 1
    return checked


def _validate(
    *, contract_path: Path = CONTRACT_PATH, layout_path: Path = LAYOUT_PATH,
    export_root: Path | None = None, ledger_path: Path | None = None, summary_path: Path | None = None,
) -> dict[str, Any]:
    contract = json.loads(contract_path.read_bytes())
    if contract.get("schema") not in (SCHEMA, TYPED_SCHEMA, COLLECTION_SCHEMA):
        raise ValueError("levelscriptRouteDeserialize.contract:unsupported-schema")
    typed = contract["schema"] in (TYPED_SCHEMA, COLLECTION_SCHEMA)
    if typed and contract.get("status") != "exact-current-build":
        raise ValueError("levelscriptRouteDeserialize.contract:unsupported-status")
    native_inputs = contract["nativeInputs"]
    gate = check_installed_native_inputs(
        native_inputs["gameAssembly"]["sha256"],
        native_inputs["metadata"]["sha256"],
    )
    audit: dict[str, Any] = {
        "schema": "endfield.levelscript-route-deserialize-native-audit.v2" if typed else "endfield.levelscript-route-deserialize-native-audit.v1",
        "status": gate.status,
        "nativeGate": gate.detail,
        "validatedRows": [],
    }
    if gate.status != "validated":
        return audit

    image = NativeImage(gate.gameassembly, gate.metadata, label="levelscriptRouteDeserialize")
    if contract["schema"] == COLLECTION_SCHEMA:
        _validate_collection_readers(image, contract)
    elif any(kind.startswith("List<") for route in contract.get("routes", []) for _, kind in route.get("fields", [])):
        raise ValueError("levelscriptRouteDeserialize.contract:collection-reader-v3-required")
    recorded_enums = contract.get("enumUnderlying", [])
    required_enums = {PARAM_ENUM_UNDERLYING[item["declaredType"]]
                      for row in contract["routes"] for item in row["readOrder"]
                      if item["declaredType"] in PARAM_ENUM_UNDERLYING}
    actual_enums = {(enum["typeName"], enum["underlyingType"]) for enum in recorded_enums}
    if not required_enums.issubset(actual_enums):
        raise ValueError("levelscriptRouteDeserialize.contract:required-param-enum-underlying="
                         f"expected={sorted(required_enums)}:actual={sorted(actual_enums)}")
    header_enums = {HEADER_ENUM_UNDERLYING[item["declaredType"]]
                    for row in contract["routes"] for item in row["readOrder"]
                    if item["declaredType"] in HEADER_ENUM_UNDERLYING}
    if not header_enums.issubset(actual_enums):
        raise ValueError("levelscriptRouteDeserialize.contract:required-header-enum-underlying="
                         f"expected={sorted(header_enums)}:actual={sorted(actual_enums)}")
    for enum in recorded_enums:
        definition = enum["typeDefinition"]
        if image.type_name(definition) != enum["typeName"]:
            raise ValueError(f"levelscriptRouteDeserialize.native:enum-type={definition}")
        fields = image.metadata.fields_for(image.metadata.types[definition])
        value_fields = [field for field in fields if image.metadata.string(field.name_index) == "value__"]
        if len(value_fields) != 1 or _runtime_parameter_name(image, value_fields[0].type_index) != enum["underlyingType"]:
            raise ValueError(f"levelscriptRouteDeserialize.native:enum-underlying={definition}")
    layouts = json.loads(layout_path.read_bytes())
    if layouts.get("schema") != "endfield.action-map-layouts.v3":
        raise ValueError("levelscriptRouteDeserialize.layout:unsupported-schema")
    selected = {(row["family"], row["tag"]): row for row in layouts["layouts"]}
    wrappers = derive_from_image(image) if any("nativeIdentity" in row for row in contract["routes"]) else None
    bodies = BodyIndex(image) if typed else None
    if typed:
        targets = {item["readTargetRva"] for row in contract["routes"] for item in row["readOrder"] if "typedReadContext" in item}
        windows = contract["typedReaderWindows"]
        if {window["startRva"] for window in windows} != targets:
            raise ValueError("levelscriptRouteDeserialize.contract:typed-reader-windows")
        image.check_windows(windows, label="levelscriptRouteDeserialize")
        for window in windows:
            pointer = image.pe.image_base + window["startRva"]
            fragments = window["fragmentWindows"]
            image.check_windows(fragments, label="levelscriptRouteDeserialize")
            actual_fragments = [(start-image.pe.image_base, start+size-image.pe.image_base)
                                for start, size in bodies.chained_fragments.get(pointer, ())]
            recorded_fragments = [(fragment["startRva"], fragment["endRva"]) for fragment in fragments]
            if (bodies.extents.get(pointer) != image.pe.image_base + window["endRva"]
                    or actual_fragments != recorded_fragments):
                raise ValueError(f"levelscriptRouteDeserialize.native:typed-reader-extent={window['startRva']:#x}")
    switches: dict[str, dict[str, Any]] = {}
    for row in contract["routes"]:
        key = row["family"], row["tag"]
        layout = selected.get(key)
        if layout is None or layout["wrapperName"] != row["wrapperName"]:
            raise ValueError(f"levelscriptRouteDeserialize.layout:missing-route={key}")
        order = row["readOrder"]
        if typed and "nativeIdentity" not in row:
            raise ValueError(f"levelscriptRouteDeserialize.contract:required-native-identity={key}")
        if layout["memberCount"] != row["memberCount"] or [field[0] for field in layout["fields"]] != [item["name"] for item in order]:
            raise ValueError(f"levelscriptRouteDeserialize.layout:field-order={key}")
        if "fields" in row and layout["fields"] != row["fields"]:
            raise ValueError(f"levelscriptRouteDeserialize.layout:field-kinds={key}")
        if "nativeIdentity" in row:
            identity = row["nativeIdentity"]
            if row["family"] not in switches:
                switches[row["family"]] = read_union_switch(
                    image, UNION_BASES[row["family"]], wrappers=wrappers,
                )
            switch = switches[row["family"]]
            entry = switch["entries"][row["tag"]]
            expected = (
                identity["dispatcherVa"], identity["switchTableVa"],
                identity["switchTargetVa"], identity["branchBodyVa"],
                identity["usageCellVa"], identity["registeredTypeIndex"],
                identity["typeDefinition"], row["wrapperName"],
            )
            actual = (
                switch["dispatcherVa"], switch["tableVa"],
                entry["targetVa"], entry["bodyVa"],
                entry["usageCellVa"], entry["registeredTypeIndex"],
                entry["typeDefinition"], entry["wrapperName"],
            )
            if tuple(str(value).lower() for value in actual) != tuple(str(value).lower() for value in expected):
                raise ValueError(f"levelscriptRouteDeserialize.native:union-identity={key}")
            if image.pe.bytes_at_va(int(identity["branchBodyVa"], 16), len(identity["branchCodeHex"]) // 2).hex() != identity["branchCodeHex"].lower():
                raise ValueError(f"levelscriptRouteDeserialize.native:branch-code={key}")
            if image.pe.bytes_at_va(int(identity["usageCellVa"], 16), len(identity["usageRawHex"]) // 2).hex() != identity["usageRawHex"].lower():
                raise ValueError(f"levelscriptRouteDeserialize.native:usage-cell={key}")
        start = row["deserializeRva"]
        image.validate_method_row([
            row["deserializeMethodIndex"], row["wrapperName"], "Deserialize", start,
        ])
        body = image.pe.bytes_at_va(image.pe.image_base + start, row["normalBodyLength"])
        if hashlib.sha256(body).hexdigest().upper() != row["normalBodySha256"].upper():
            raise ValueError(f"levelscriptRouteDeserialize.native:body-sha256={key}")
        previous_setter = -1
        for item in order:
            read_call = item["readCallRva"]
            setter_call = item["setterCallRva"]
            if not (start <= read_call < setter_call < start + len(body)) or read_call <= previous_setter:
                raise ValueError(f"levelscriptRouteDeserialize.native:read-order={key}/{item['name']}")
            if _relative_call_target(image, read_call) != item["readTargetRva"]:
                raise ValueError(f"levelscriptRouteDeserialize.native:read-call={key}/{item['name']}")
            setter = image.metadata.methods[item["setterMethodIndex"]]
            if image.metadata.string(setter.name_index) != item["setterName"] or image.method_pointer_va(setter) != image.pe.image_base + item["setterTargetRva"]:
                raise ValueError(f"levelscriptRouteDeserialize.native:setter={key}/{item['name']}")
            if _relative_call_target(image, setter_call) != item["setterTargetRva"]:
                raise ValueError(f"levelscriptRouteDeserialize.native:setter-call={key}/{item['name']}")
            parameters = image.metadata.parameters_for(setter)
            if len(parameters) != 1 or _runtime_parameter_name(image, parameters[0].type_index) != item["declaredType"]:
                raise ValueError(f"levelscriptRouteDeserialize.native:setter-parameter={key}/{item['name']}")
            previous_setter = setter_call
        if typed:
            _typed_route(image, bodies, wrappers[row["typeDefinition"]], row)
        audit["validatedRows"].append({
            "family": row["family"], "tag": row["tag"],
            "memberCount": row["memberCount"],
            "deserializeRva": start,
            **({"wrapperName": row["wrapperName"], "fields": row["fields"]} if typed else {}),
        })
    if export_root is not None:
        if not typed or ledger_path is None or summary_path is None:
            raise ValueError("levelscriptRouteDeserialize.source:explicit-v2-ledger-summary-required")
        audit["sourceReceiptsChecked"] = _source_receipts(contract, export_root, ledger_path, summary_path)
    elif ledger_path is not None or summary_path is not None:
        raise ValueError("levelscriptRouteDeserialize.source:explicit-export-root-required")
    return audit


def validate(
    *, contract_path: Path = CONTRACT_PATH, layout_path: Path = LAYOUT_PATH,
    export_root: Path | None = None, ledger_path: Path | None = None, summary_path: Path | None = None,
) -> dict[str, Any]:
    """V2 failures are actionable audit rows; keep V1's exception API intact."""
    typed = json.loads(contract_path.read_bytes()).get("schema") in (TYPED_SCHEMA, COLLECTION_SCHEMA)
    try:
        return _validate(contract_path=contract_path, layout_path=layout_path, export_root=export_root,
                         ledger_path=ledger_path, summary_path=summary_path)
    except (KeyError, IndexError, TypeError, ValueError, OSError, RuntimeError) as exc:
        if not typed:
            raise
        detail = str(exc)
        check = detail.split(":", 1)[-1].split("=", 1)[0]
        return {"schema": "endfield.levelscript-route-deserialize-native-audit.v2",
                "status": "validation_failed", "validatedRows": [], "validator": "levelscriptRouteDeserialize",
                "failedCheck": check, "detail": detail,
                "validationFailures": [{"check": check, "source": str(contract_path), "actual": detail[:1000]}]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=CONTRACT_PATH)
    parser.add_argument("--export-root", type=Path)
    parser.add_argument("--ledger", type=Path)
    parser.add_argument("--summary", type=Path)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    audit = validate(contract_path=args.contract, export_root=args.export_root,
                     ledger_path=args.ledger, summary_path=args.summary)
    write_canonical_json(args.report, audit)
    print(audit["status"], "routes", len(audit["validatedRows"]), "report", args.report)
    if audit.get("detail"):
        print(audit["detail"])


if __name__ == "__main__":
    main()
