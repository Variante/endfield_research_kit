"""Build a fail-closed current-build JsonData union atlas.

The atlas reads reviewed contracts, authenticates the selected
native inputs, parses GameAssembly/metadata once, validates their native
identities, and writes generated evidence under reports/.

It does not discover union layouts or promote schemas.  Unsupported contract
facts remain present only through their contract hash and are listed as trust
gaps in the report.

It covers the reviewed Skill, Buff and LevelScript union contracts through one
shared current-build PE/metadata context.  Every tag stays qualified by its
``dispatcherFamily`` -- a numeric tag means nothing outside its own union --
and conflicting identities for one key fail closed.  Setter types, nested
layouts and exact cursors still come from the owning reviewed contract and
reader.  Its purpose is recovery acceleration: frontier ranking reads the
atlas instead of repeating native discovery per route, while publication
still requires the complete family and JsonData corpus gates.  The
``generatedMemberEnrichment`` block (see ``_enrich_generated_members``)
names members from ``memorypack.wrapper_members`` and reports a member-count
conflict instead of overwriting a reviewed row.

The default output is ``reports/animestudio/jsondata_union_atlas_current.json``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
import time
from functools import cached_property
from pathlib import Path
from typing import Any, Iterable

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import NativeImage, NATIVE_MAPPER_PATH, METADATA_HELPER_PATH
from scripts.game_data.dependency_snapshot import local_dependency_paths
from scripts.game_data.corpus_common import atomic_write_text
from scripts.game_data.memorypack.wrapper_members import derive_from_image
from scripts.game_data.memorypack.union_dispatch import read_union_switch, UnionDispatchError
from scripts.repo_paths import REPO_ROOT as REPO
from scripts.game_data.il2cpp.context import (
    GenericInstantiationTable,
    match_image_modules,
    method_spec_record,
    method_spec_usage_index,
    method_token_pointer,
    rip_qword_load_target,
    type_image_owners,
    unresolved_usage_index,
)


GAME_DATA = REPO / "scripts/game_data"
DEFAULT_OUTPUT = REPO / "reports/animestudio/jsondata_union_atlas_current.json"

# Schema versions select adapters; build identities and union rows remain in
# the reviewed JSON contracts.  Adding a shape requires an explicit adapter
# decision instead of being admitted by a filename or coincidental keys.
SUPPORTED_SCHEMAS: dict[str, tuple[str, frozenset[str | None]]] = {
    "endfield.buff-icon-config-native-contract.v1": ("identity_only", frozenset({"exact-current-build"})),
    "endfield.buff-residual-action-native-contract.v1": ("actions", frozenset({"exact-current-build"})),
    "endfield.buff-frontier6-native-contract.v1": ("actions", frozenset({"exact-current-build"})),
    "endfield.buff-frontier7-native-contract.v1": ("actions", frozenset({"exact-current-build"})),
    "endfield.buff-frontier8-native-contract.v1": ("actions", frozenset({"exact-current-build"})),
    "endfield.buff-frontier9-native-contract.v1": ("actions", frozenset({"exact-current-build"})),
    "endfield.buff-residual-frontier-native-contract.v1": ("actions", frozenset({"exact-current-build"})),
    "endfield.levelscript-task-condition-native.v1": ("levelscript_condition", frozenset({"validated"})),
    "endfield.action-map-layouts.v5": ("levelscript_actions", frozenset({None})),
    "endfield.skill-timeline-continuous-find-target-native-contract.v1": ("selector_routes", frozenset({"exact-current-build"})),
    "endfield.skill-timeline-create-buff-native-contract.v1": ("dispatcher", frozenset({"exact-current-build"})),
    "endfield.skill-timeline-find-target-native-contract.v1": ("selector_routes", frozenset({"exact-current-build"})),
    "endfield.skill-timeline-play-animation-native-contract.v1": ("identity_only", frozenset({"exact-current-build"})),
    "endfield.skill-timeline-play-animation-step-native-contract.v1": ("dispatcher", frozenset({"exact-current-build"})),
    "endfield.skill-timeline-shared-sequence-native-contract.v2": ("shared_sequence", frozenset({"exact-current-build-composite"})),
}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _int(value: Any) -> int:
    return int(value, 0) if isinstance(value, str) else int(value)


def _native_inputs(value: dict[str, Any]) -> dict[str, str]:
    aliases = {
        "GameAssembly.dll": ("GameAssembly.dll", "gameassemblySha256", "gameAssembly"),
        "global-metadata.dat": ("global-metadata.dat", "globalMetadataSha256", "metadata"),
        "UnityPlayer.dll": ("UnityPlayer.dll", "unityplayerSha256", "unityPlayer"),
    }
    result: dict[str, str] = {}
    for canonical, keys in aliases.items():
        selected: Any = None
        for key in keys:
            if key in value:
                selected = value[key]
                break
        if isinstance(selected, dict):
            selected = selected.get("sha256")
        if selected is not None:
            if not isinstance(selected, str) or len(selected) != 64:
                raise ValueError(f"native-input-sha256={canonical}:{selected!r}")
            result[canonical] = selected.upper()
    if set(result) < {"GameAssembly.dll", "global-metadata.dat"}:
        raise ValueError(f"native-inputs-incomplete={sorted(result)}")
    return result


def _default_contracts() -> list[Path]:
    selected: dict[str, Path] = {}
    for path in GAME_DATA.rglob("*.json"):
        try:
            value = json.loads(path.read_bytes())
        except (OSError, ValueError):
            continue
        schema = value.get("schema")
        if schema not in SUPPORTED_SCHEMAS:
            continue
        _, statuses = SUPPORTED_SCHEMAS[schema]
        status = value.get("status")
        if status not in statuses:
            raise ValueError(f"contract-status={path.relative_to(REPO)}:{status!r}")
        if schema in selected:
            raise ValueError(
                f"duplicate-contract-schema={schema}:{selected[schema].relative_to(REPO)}:"
                f"{path.relative_to(REPO)}"
            )
        selected[schema] = path
    missing = sorted(set(SUPPORTED_SCHEMAS) - set(selected))
    if missing:
        raise ValueError(f"missing-contract-schemas={missing}")
    return sorted(selected.values())


def _walk(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


class NativeContext:
    def __init__(self, gameassembly: Path, metadata_path: Path):
        image = NativeImage(gameassembly, metadata_path, label="unionAtlas")
        self.image = image
        self.mapper = image.mapper
        self.pe = image.pe
        self.md = image.metadata
        self.code_registration = image.code_registration
        self.registration = image.registration
        self.owners = image.owners
        self.modules = image.modules
        self._method_arrays: dict[str, tuple[int, bytes]] = {}
        self._window_hashes: dict[tuple[int, int], str] = {}
        self._switch_tables: dict[tuple[int, int], bytes] = {}
        self._generic_instantiations: GenericInstantiationTable | None = None

    @cached_property
    def wrapper_members(self) -> dict[int, Any]:
        return derive_from_image(self.image)

    @cached_property
    def condition_switch(self) -> dict[str, Any]:
        return read_union_switch(self.image, "Beyond.MemoryPack.Beyond_Gameplay_GameConditionForMemoryPack",
                                 wrappers=self.wrapper_members)

    def bytes_at_rva(self, rva: int, size: int) -> bytes:
        return self.pe.bytes_at_va(self.pe.image_base + rva, size)

    def window_sha(self, start_rva: int, end_rva: int) -> str:
        if not 0 <= start_rva < end_rva:
            raise ValueError(f"invalid-window={start_rva:#x}:{end_rva:#x}")
        key = (start_rva, end_rva)
        if key not in self._window_hashes:
            self._window_hashes[key] = hashlib.sha256(
                self.bytes_at_rva(start_rva, end_rva - start_rva)
            ).hexdigest().upper()
        return self._window_hashes[key]

    def method_pointer(self, method_index: int) -> int:
        method = self.md.methods[method_index]
        owner = self.md.types[method.declaring_type]
        image = self.md.string(self.md.images[self.owners[method.declaring_type]].name_index)
        if image not in self._method_arrays:
            module = self.modules[image]
            count = self.pe.u32_at_va(module + 8)
            base = self.pe.u64_at_va(module + 16)
            self._method_arrays[image] = (base, self.pe.bytes_at_va(base, count * 8))
        base, pointers = self._method_arrays[image]
        row = method_token_pointer(method.token, pointers, source=image, offset=base)
        return row["pointerVa"]

    def validate_method(self, row: list[Any]) -> None:
        index, type_name, method_name, rva = row
        method = self.md.methods[index]
        actual_type = self.md.type_full_name(self.md.types[method.declaring_type])
        actual_name = self.md.string(method.name_index)
        if (actual_type, actual_name) != (type_name, method_name):
            raise ValueError(
                f"method-identity={index}:expected={(type_name, method_name)!r}:"
                f"actual={(actual_type, actual_name)!r}"
            )
        actual_pointer = self.method_pointer(index)
        expected_pointer = self.pe.image_base + rva
        if actual_pointer != expected_pointer:
            raise ValueError(
                f"method-pointer={index}:expected={expected_pointer:#x}:actual={actual_pointer:#x}"
            )

    def validate_usage(self, row: dict[str, Any]) -> None:
        rva_key = "usageCellRva" if "usageCellRva" in row else None
        va_key = "usageCellVa" if "usageCellVa" in row else None
        if not rva_key and not va_key:
            return
        usage_va = self.pe.image_base + _int(row[rva_key]) if rva_key else _int(row[va_key])
        raw = self.pe.bytes_at_va(usage_va, 8)
        if raw.hex().upper() != row["usageRawHex"].upper():
            raise ValueError(f"usage-cell={usage_va:#x}:expected={row['usageRawHex'].upper()}:actual={raw.hex().upper()}")
        if "registeredTypeIndex" not in row:
            return
        index = unresolved_usage_index(
            raw, self.registration["typesCount"], tag=1,
            source="GameAssembly.dll", offset=usage_va,
        )
        if index != row["registeredTypeIndex"]:
            raise ValueError(f"registered-type-index={usage_va:#x}:expected={row['registeredTypeIndex']}:actual={index}")
        type_pointer = self.pe.u64_at_va(int(self.registration["types"], 16) + index * 8)
        if "typePointerVa" in row and type_pointer != int(row["typePointerVa"], 0):
            raise ValueError(f"type-pointer={usage_va:#x}:expected={int(row['typePointerVa'], 0):#x}:actual={type_pointer:#x}")
        if "typePointerRva" in row and type_pointer != self.pe.image_base + _int(row["typePointerRva"]):
            expected = self.pe.image_base + _int(row["typePointerRva"])
            raise ValueError(f"type-pointer={usage_va:#x}:expected={expected:#x}:actual={type_pointer:#x}")
        definition = struct.unpack_from("<Q", self.pe.bytes_at_va(type_pointer, 16))[0]
        expected_definition = row.get("wrapperTypeDefinition", row.get("typeDefinition"))
        if expected_definition is not None and definition != expected_definition:
            raise ValueError(f"type-definition={usage_va:#x}:expected={expected_definition}:actual={definition}")
        expected_name = row.get("wrapperName")
        if expected_name is not None:
            actual_name = self.md.type_full_name(self.md.types[definition])
            if actual_name != expected_name:
                raise ValueError(f"type-name={usage_va:#x}:expected={expected_name!r}:actual={actual_name!r}")

    def validate_method_spec_provider(self, row: dict[str, Any]) -> None:
        """Authenticate one RIP-loaded MethodSpec and its concrete type argument."""
        usage_va = self.pe.image_base + _int(row["usageCellRva"])
        usage_raw = self.pe.bytes_at_va(usage_va, 8)
        if usage_raw.hex().upper() != row["usageRawHex"].upper():
            raise ValueError(f"method-spec-usage-cell={usage_va:#x}")
        method_spec_index = method_spec_usage_index(
            usage_raw,
            self.registration["methodSpecsCount"],
            source="GameAssembly.dll",
            offset=usage_va,
        )
        if method_spec_index != row["index"]:
            raise ValueError(
                f"method-spec-usage-index={usage_va:#x}:{method_spec_index}"
            )
        for callsite_rva in row["callsiteRvas"]:
            instruction_va = self.pe.image_base + _int(callsite_rva)
            target = rip_qword_load_target(
                self.pe.bytes_at_va(instruction_va, 7),
                instruction_va,
                source="GameAssembly.dll",
            )
            if target != usage_va:
                raise ValueError(
                    f"method-spec-callsite={_int(callsite_rva):#x}:{target:#x}"
                )
        record_va = int(self.registration["methodSpecs"], 16) + method_spec_index * 12
        record_raw = self.pe.bytes_at_va(record_va, 12)
        if record_raw.hex().upper() != row["rawHex"].upper():
            raise ValueError(f"method-spec-record={method_spec_index}")
        definition, class_inst, method_inst = method_spec_record(
            record_raw,
            len(self.md.methods),
            self.registration["genericInstsCount"],
            source="GameAssembly.dll",
            offset=record_va,
        )
        expected = (
            row["methodDefinition"],
            row["classInstantiationIndex"],
            row["methodInstantiationIndex"],
        )
        if (definition, class_inst, method_inst) != expected:
            raise ValueError(
                f"method-spec-record-indices={method_spec_index}:"
                f"{(definition, class_inst, method_inst)!r}"
            )
        if self._generic_instantiations is None:
            self._generic_instantiations = GenericInstantiationTable(
                self.pe.bytes_at_va,
                int(self.registration["genericInsts"], 16),
                self.registration["genericInstsCount"],
                source="GameAssembly.dll",
            )
        instance = self._generic_instantiations.resolve(method_inst)
        if len(instance.arguments) != 1:
            raise ValueError(
                f"method-spec-generic-arguments={method_spec_index}:"
                f"{len(instance.arguments)}"
            )
        argument = instance.arguments[0]
        if argument.raw_type_record_hex.upper() != row["argumentTypeRawHex"].upper():
            raise ValueError(f"method-spec-argument={method_spec_index}")
        type_definition = struct.unpack_from("<Q", bytes.fromhex(argument.raw_type_record_hex))[0]
        if type_definition != row["typeDefinition"]:
            raise ValueError(
                f"method-spec-type-definition={method_spec_index}:{type_definition}"
            )
        actual_name = self.md.type_full_name(self.md.types[type_definition])
        if actual_name != row["typeName"]:
            raise ValueError(f"method-spec-type-name={method_spec_index}:{actual_name}")

    def validate_switch(self, row: dict[str, Any]) -> None:
        required = {"switchTableRva", "switchEntryCount", "switchTableSha256",
                    "switchTargetRva", "unionTag"}
        if not required <= row.keys():
            return
        key = (row["switchTableRva"], row["switchEntryCount"])
        table = self._switch_tables.get(key)
        if table is None:
            table = self.bytes_at_rva(key[0], key[1] * 4)
            self._switch_tables[key] = table
        digest = hashlib.sha256(table).hexdigest().upper()
        if digest != row["switchTableSha256"].upper():
            raise ValueError(f"switch-table={key[0]:#x}")
        target = struct.unpack_from("<I", table, row["unionTag"] * 4)[0]
        if target != row["switchTargetRva"]:
            raise ValueError(f"switch-target={row['unionTag']:#x}:{target:#x}")

    def validate_action_map_identity(self, identity: dict[str, Any]) -> None:
        anchors = ("dispatcherTypeDefinition", "dispatcherMethodToken", "dispatcherMethodVa")
        missing = [name for name in anchors if name not in identity]
        if missing:
            raise ValueError(f"action-map-dispatcher-anchors:expected={list(anchors)!r}:actual=missing{missing!r}")
        start = _int(identity["branchBodyVa"])
        expected = bytes.fromhex(identity["branchCodeHex"])
        if self.pe.bytes_at_va(start, len(expected)) != expected:
            raise ValueError(f"action-map-branch={start:#x}")
        definition = identity["dispatcherTypeDefinition"]
        token = _int(identity["dispatcherMethodToken"])
        matches = [
            index for index, method in enumerate(self.md.methods)
            if method.declaring_type == definition and method.token == token
        ]
        if len(matches) != 1:
            raise ValueError(f"action-map-dispatcher={definition}:{token:#x}:{matches}")
        if self.method_pointer(matches[0]) != _int(identity["dispatcherMethodVa"]):
            raise ValueError(f"action-map-dispatcher-pointer={definition}:{token:#x}")
        self.validate_usage(identity)

    def validate_condition_map_identity(self, row: dict[str, Any]) -> None:
        if row.get("family", "GameCondition") != "GameCondition":
            raise ValueError(f"condition-dispatcher-family={row.get('family')!r}")
        identity = row["nativeIdentity"]
        switch = self.condition_switch
        tag = row["tag"]
        if not isinstance(tag, int) or not 0 <= tag < len(switch["entries"]):
            raise ValueError(f"condition-dispatcher-tag={tag!r}:entry-count={len(switch['entries'])}")
        entry = switch["entries"][tag]
        expected = (identity.get("dispatcherVa", identity.get("dispatcherMethodVa")),
                    identity["switchTableVa"], identity["switchTargetVa"], identity["branchBodyVa"],
                    identity["usageCellVa"], identity["registeredTypeIndex"], identity["typeDefinition"], row["wrapperName"])
        actual = (switch["dispatcherVa"], switch["tableVa"], entry["targetVa"], entry["bodyVa"],
                  entry["usageCellVa"], entry["registeredTypeIndex"], entry["typeDefinition"], entry["wrapperName"])
        if tuple(str(item).lower() for item in actual) != tuple(str(item).lower() for item in expected):
            raise ValueError(f"condition-dispatcher-identity=expected={expected!r}:actual={actual!r}")
        start = _int(identity["branchBodyVa"])
        expected_bytes = bytes.fromhex(identity["branchCodeHex"])
        actual_bytes = self.pe.bytes_at_va(start, len(expected_bytes))
        if actual_bytes != expected_bytes:
            raise ValueError(f"condition-branch={start:#x}:expected={expected_bytes.hex()}:actual={actual_bytes.hex()}")
        # Legacy method-token anchors remain mandatory when present.
        if "dispatcherTypeDefinition" in identity:
            self.validate_action_map_identity({**identity, "wrapperName": row["wrapperName"]})
        else:
            self.validate_usage({**identity, "wrapperName": row["wrapperName"]})

    def validate_dispatcher_identity(self, identity: dict[str, Any]) -> None:
        definition = _int(identity["typeDefinition"])
        token = _int(identity["methodToken"])
        matches = [
            index for index, method in enumerate(self.md.methods)
            if method.declaring_type == definition and method.token == token
        ]
        if len(matches) != 1:
            raise ValueError(f"dispatcher-method={definition}:{token:#x}:{matches}")
        expected = self.pe.image_base + _int(identity["methodRva"])
        if self.method_pointer(matches[0]) != expected:
            raise ValueError(f"dispatcher-method-pointer={definition}:{token:#x}")


def _validate_contract_native(ctx: NativeContext, value: dict[str, Any]) -> dict[str, int]:
    def checked(check: str, node: dict[str, Any], proof: dict[str, Any]) -> None:
        try:
            getattr(ctx, check)(proof)
        except (ValueError, KeyError, IndexError, TypeError, struct.error, UnionDispatchError) as error:
            identity = {key: node[key] for key in ("family", "tag", "wrapperName") if key in node}
            raise ValueError(f"native-check={check}:row={json.dumps(identity, sort_keys=True)}:detail={error}") from error

    counts = {"methods": 0, "dispatcherMethods": 0, "windows": 0, "instructions": 0,
              "switchRoutes": 0, "usageCells": 0, "methodSpecs": 0,
              "actionMapIdentities": 0}
    methods: set[tuple[Any, ...]] = set()
    windows: set[tuple[int, int, str]] = set()
    instructions: set[tuple[int, str]] = set()
    usages: set[tuple[str, str]] = set()
    switches: set[tuple[int, int, int]] = set()
    action_identities: set[tuple[Any, ...]] = set()
    dispatcher_identities: set[tuple[int, int]] = set()
    method_spec_providers: set[tuple[str, int]] = set()
    for node in _walk(value):
        for method in node.get("methods", []):
            if (isinstance(method, list) and len(method) == 4
                    and isinstance(method[0], int) and isinstance(method[3], int)):
                methods.add(tuple(method))
        for key in ("codeWindows", "dataWindows"):
            for window in node.get(key, []):
                if {"startRva", "endRva", "sha256"} <= window.keys():
                    windows.add((_int(window["startRva"]), _int(window["endRva"]), window["sha256"].upper()))
                elif {"rva", "length", "sha256"} <= window.keys():
                    start = _int(window["rva"])
                    windows.add((start, start + _int(window["length"]), window["sha256"].upper()))
        route = node.get("routeWindow")
        if isinstance(route, dict) and {"startRva", "endRva", "sha256"} <= route.keys():
            windows.add((_int(route["startRva"]), _int(route["endRva"]), route["sha256"].upper()))
        for instruction in node.get("instructionWindows", []):
            if isinstance(instruction, list) and len(instruction) >= 2:
                instructions.add((instruction[0], instruction[1].upper()))
        if "instructionRva" in node and "instructionHex" in node:
            instructions.add((node["instructionRva"], node["instructionHex"].upper()))
        if ("usageCellRva" in node or "usageCellVa" in node) and "usageRawHex" in node:
            key = (str(node.get("usageCellRva", node.get("usageCellVa"))), node["usageRawHex"])
            if key not in usages:
                checked("validate_usage", node, node)
                usages.add(key)
        if {"switchTableRva", "switchEntryCount", "unionTag"} <= node.keys():
            key = (node["switchTableRva"], node["switchEntryCount"], node["unionTag"])
            if key not in switches:
                checked("validate_switch", node, node)
                switches.add(key)
        identity = node.get("nativeIdentity")
        if isinstance(identity, dict) and "branchCodeHex" in identity:
            key = (node.get("family"), node.get("tag"), identity["branchBodyVa"], identity["usageRawHex"])
            if key not in action_identities:
                if node.get("family") == "GameCondition":
                    checked("validate_condition_map_identity", node, node)
                else:
                    merged = {**identity}
                    if "wrapperName" in node:
                        merged["wrapperName"] = node["wrapperName"]
                    checked("validate_action_map_identity", node, merged)
                action_identities.add(key)
        elif isinstance(identity, dict) and ("usageCellRva" in identity or "usageCellVa" in identity):
            merged = {**identity}
            if "wrapperName" in node:
                merged["wrapperName"] = node["wrapperName"]
            key = (str(merged.get("usageCellRva", merged.get("usageCellVa"))), merged["usageRawHex"])
            if key not in usages:
                checked("validate_usage", node, merged)
                usages.add(key)
        if {"typeDefinition", "methodToken", "methodRva"} <= node.keys():
            key = (_int(node["typeDefinition"]), _int(node["methodToken"]))
            if key not in dispatcher_identities:
                checked("validate_dispatcher_identity", node, node)
                dispatcher_identities.add(key)
        if node.get("methodSpecProvider") is True:
            key = (str(node.get("usageCellRva")), int(node.get("index", -1)))
            if key not in method_spec_providers:
                checked("validate_method_spec_provider", node, node)
                method_spec_providers.add(key)
    for method in sorted(methods):
        ctx.validate_method(list(method))
    for start, end, expected in sorted(windows):
        actual = ctx.window_sha(start, end)
        if actual != expected:
            raise ValueError(f"window={start:#x}:{end:#x}:expected={expected}:actual={actual}")
    for rva, expected in sorted(instructions):
        raw = ctx.bytes_at_rva(rva, len(expected) // 2)
        if raw.hex().upper() != expected:
            raise ValueError(f"instruction={rva:#x}")
    counts.update(methods=len(methods), dispatcherMethods=len(dispatcher_identities),
                  windows=len(windows), instructions=len(instructions),
                  switchRoutes=len(switches), usageCells=len(usages),
                  methodSpecs=len(method_spec_providers),
                  actionMapIdentities=len(action_identities))
    return counts


def _parse_tag(value: Any) -> int:
    return int(value, 0) if isinstance(value, str) else int(value)


def _atlas_rows(contract_path: Path, value: dict[str, Any], digest: str) -> list[dict[str, Any]]:
    source = contract_path.relative_to(REPO).as_posix()
    schema = value.get("schema")
    adapter = SUPPORTED_SCHEMAS[schema][0]
    common = {"contract": source, "contractSha256": digest, "schema": schema}
    rows: list[dict[str, Any]] = []
    if adapter == "actions":
        for action in value["actions"]:
            rows.append({
                **common, "dispatcherFamily": "AbilityActionData", "physicalTag": action["unionTag"],
                "tagEncodingHex": action.get("encodingHex"),
                "serializedMemberCount": action.get("serializedMemberCount"),
                "wrapperName": action.get("wrapperName"),
                "wrapperTypeDefinition": action.get("wrapperTypeDefinition"),
                "registeredTypeIndex": action.get("registeredTypeIndex"),
                "readOrder": action.get("readOrder"), "setterMethods": action.get("setterMethods"),
                "trust": "native-validated-reviewed-row",
            })
    dispatcher = value.get("dispatcher")
    if adapter == "dispatcher":
        wrapper = value.get("wrapper", {})
        rows.append({
            **common, "dispatcherFamily": "AbilityActionData",
            "physicalTag": dispatcher["unionTag"], "tagEncodingHex": dispatcher.get("encodingHex"),
            "serializedMemberCount": wrapper.get("serializedMemberCount"),
            "wrapperName": dispatcher.get("wrapperName", wrapper.get("typeName")),
            "wrapperTypeDefinition": dispatcher.get("wrapperTypeDefinition", wrapper.get("typeDefinition")),
            "registeredTypeIndex": dispatcher.get("registeredTypeIndex"),
            "readOrder": wrapper.get("selectedReadOrder"),
            "setterMethods": wrapper.get("setterMethods"),
            "trust": "native-validated-reviewed-row",
        })
    if adapter == "shared_sequence":
        for route in value.get("allowedReachedRoutes", []):
            rows.append({
                **common, "dispatcherFamily": "SkillAbilityActionComposite",
                "physicalTag": _parse_tag(route["tag"]),
                "serializedMemberCount": route["memberCount"], "wrapperName": route["typeName"],
                "trust": "dependency-hash-validated-composite-row",
            })
    if adapter == "selector_routes":
        for category, routes in value["selectedSubtypeRoutes"].items():
            for tag, name in routes.items():
                rows.append({
                    **common, "dispatcherFamily": f"SkillSelector:{category}",
                    "physicalTag": _parse_tag(tag), "wrapperName": name,
                    "trust": "dependency-hash-validated-composite-row",
                })
    if adapter == "levelscript_actions":
        # v5 rows carry no per-build tag; the codec resolves each by wrapper
        # through the build-gated union-tags contract and yields nothing
        # unless that gate validates.
        from scripts.game_data.codecs.levelscript import action_map

        layouts, conditions, _audit = action_map._resolved()
        for layout in [*layouts, *conditions]:
            rows.append({
                **common, "dispatcherFamily": f"LevelScript:{layout['family']}",
                "physicalTag": layout["tag"], "serializedMemberCount": layout["memberCount"],
                "wrapperName": layout["wrapperName"], "readOrder": layout.get("fields"),
                "trust": "union-tag-resolved-reviewed-row",
            })
    if adapter == "levelscript_condition":
        for row in value.get("rows", []):
            rows.append({
                **common, "dispatcherFamily": "LevelScript:GameConditionServer",
                "physicalTag": _parse_tag(row["tag"]), "serializedMemberCount": row["memberCount"],
                "wrapperName": row["wrapperName"], "readOrder": row.get("fields"),
                "trust": "native-validated-reviewed-row",
            })
    return rows


def _enrich_generated_members(image: NativeImage, rows: list[dict[str, Any]], *, derived: dict[int, Any] | None = None) -> dict[str, Any]:
    """Name each row's serialized members from the selected build's wrappers.

    A reviewed row records whichever order its own recovery proved, and several
    record a positional read order with no member names at all.  The generated
    wrapper for the same type definition names every member, so this fills in
    ``generatedMemberOrder`` beside the reviewed facts without changing them.

    Rows are matched by explicit ``wrapperTypeDefinition``, or by an
    assembly-qualified wrapper name that names exactly one type in the build.
    A bare name such as ``HitBoxFinder`` is left unmatched rather than joined on
    a suffix, and a derived count that contradicts the reviewed one is reported
    instead of overwriting it.  Where a row already names its members, the
    derived order is compared against them rather than replacing them.
    """
    derived = derive_from_image(image) if derived is None else derived
    by_name: dict[str, Any] = {}
    for wrapper in derived.values():
        by_name[wrapper.name] = None if wrapper.name in by_name else wrapper
    enriched = conflicts = unmatched = 0
    order_checked = order_agreed = 0
    conflict_rows: list[dict[str, Any]] = []
    for row in rows:
        definition = row.get("wrapperTypeDefinition")
        wrapper = derived.get(definition) if isinstance(definition, int) else None
        if wrapper is None:
            name = row.get("wrapperName")
            # Only a complete, unambiguous type name is an identity; a bare
            # action name shared by several wrappers is not.
            if isinstance(name, str) and "." in name:
                wrapper = by_name.get(name)
        if wrapper is None:
            unmatched += 1
            continue
        recorded_order = [
            entry[0] for entry in row.get("readOrder") or []
            if isinstance(entry, (list, tuple)) and entry and isinstance(entry[0], str)
        ]
        if recorded_order:
            order_checked += 1
            # Contracts differ on whether they keep a member's backing-field
            # underscore (``_endFrame`` versus ``endFrame``); that spelling is
            # not an ordering disagreement, so compare without it.
            derived_order = [member.name for member in wrapper.members]
            if [name.lstrip("_") for name in recorded_order] == [
                name.lstrip("_") for name in derived_order
            ]:
                order_agreed += 1
            else:
                conflict_rows.append({
                    "wrapperName": wrapper.name, "physicalTag": row.get("physicalTag"),
                    "check": "memberOrder", "recorded": recorded_order,
                    "derived": derived_order,
                })
        recorded = row.get("serializedMemberCount")
        if isinstance(recorded, int) and recorded != wrapper.serialized_member_count:
            conflicts += 1
            conflict_rows.append({
                "wrapperName": wrapper.name, "physicalTag": row.get("physicalTag"),
                "check": "serializedMemberCount", "recorded": recorded,
                "derived": wrapper.serialized_member_count,
            })
            continue
        row["generatedMemberOrder"] = [member.name for member in wrapper.members]
        row["generatedMemberKinds"] = [member.kind for member in wrapper.members]
        row["generatedInheritedMemberCount"] = len(wrapper.inherited_members)
        enriched += 1
    return {
        "enrichedRows": enriched,
        "unmatchedRows": unmatched,
        "memberCountConflicts": conflicts,
        "memberOrderChecked": order_checked,
        "memberOrderAgreed": order_agreed,
        "conflicts": conflict_rows,
        "evidenceTier": "direct",
        "boundary": (
            "Generated member names and order come from the selected build's "
            "ForMemoryPack setters. They name what a reviewed reader walks; they do "
            "not establish a cursor, a serialized width, or a nested extent."
        ),
    }


def _normalize_atlas_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for row in rows:
        key = (row["dispatcherFamily"], row["physicalTag"], row.get("serializedMemberCount"))
        grouped.setdefault(key, []).append(row)
    normalized: list[dict[str, Any]] = []
    for key, candidates in grouped.items():
        identities: dict[str, dict[str, Any]] = {}
        for row in candidates:
            identity = {
                field: value for field, value in row.items()
                if field not in {"contract", "contractSha256", "schema"}
            }
            identities[json.dumps(identity, sort_keys=True, ensure_ascii=False)] = identity
        if len(identities) != 1:
            raise ValueError(f"conflicting-atlas-key={key!r}")
        identity = next(iter(identities.values()))
        identity["evidenceContracts"] = sorted(
            ({
                "path": row["contract"], "sha256": row["contractSha256"],
                "schema": row["schema"],
            } for row in candidates),
            key=lambda item: (item["path"], item["sha256"]),
        )
        normalized.append(identity)
    normalized.sort(key=lambda row: (
        row["dispatcherFamily"], row["physicalTag"],
        row.get("serializedMemberCount") if row.get("serializedMemberCount") is not None else -1,
        row.get("wrapperName") or "",
    ))
    return normalized


def _proof_sources(contracts: list[Path]) -> list[dict[str, Any]]:
    paths = {Path(__file__).resolve(), *(path.resolve() for path in contracts),
             *local_dependency_paths(["scripts.game_data.native_union_atlas"]),
             NATIVE_MAPPER_PATH.resolve(), METADATA_HELPER_PATH.resolve()}
    for folder in {NATIVE_MAPPER_PATH.parent, METADATA_HELPER_PATH.parent}:
        paths.update(path.resolve() for path in folder.rglob("*.py") if path.is_file())
    return [{"path": str(path), "sha256": _sha(path)} for path in sorted(paths)]


def _guard_output(output: Path, inputs: Iterable[Path]) -> None:
    reports = (REPO / "reports").resolve()
    if reports not in output.resolve().parents:
        raise ValueError(f"output-must-be-under={reports}")
    for source in inputs:
        source = Path(source).resolve()
        if output.resolve() == source or (output.exists() and source.exists() and output.samefile(source)):
            raise ValueError(f"output-input-alias=output={output}:source={source}")


def _proof_source_changes(expected: list[dict[str, Any]], actual: list[dict[str, Any]]) -> dict[str, Any]:
    before = {row["path"]: row["sha256"] for row in expected}
    after = {row["path"]: row["sha256"] for row in actual}
    paths = [path for path in sorted(before.keys() | after.keys()) if before.get(path) != after.get(path)]
    return {"changedFiles": len(paths), "changes": [
        {"path": path, "expectedSha256": before.get(path), "actualSha256": after.get(path)}
        for path in paths[:10]]}


def build(output: Path, contracts: list[Path], *, gameassembly: Path | None = None,
          metadata: Path | None = None) -> dict[str, Any]:
    started = time.perf_counter()
    output = output.resolve()
    _guard_output(output, contracts)
    if (gameassembly is None) != (metadata is None):
        raise ValueError("selected-native-pair-requires-gameassembly-and-metadata")
    _guard_output(output, [path for path in (gameassembly, metadata) if path is not None])
    proof_sources = _proof_sources(contracts)
    proof_inputs = [Path(row["path"]) for row in proof_sources]
    _guard_output(output, proof_inputs)
    proof_digests = {Path(row["path"]).resolve(): row["sha256"] for row in proof_sources}
    loaded: list[tuple[Path, dict[str, Any], str]] = []
    expected_inputs: dict[str, str] | None = None
    for path in contracts:
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest().upper()
        expected_digest = proof_digests.get(path.resolve())
        if digest != expected_digest:
            raise ValueError(f"contract-read-source-drift={path}:expected={expected_digest}:actual={digest}")
        value = json.loads(raw)
        schema = value.get("schema")
        if schema not in SUPPORTED_SCHEMAS:
            raise ValueError(f"unsupported-contract-schema={path.relative_to(REPO)}:{schema!r}")
        if value.get("status") not in SUPPORTED_SCHEMAS[schema][1]:
            raise ValueError(
                f"contract-status={path.relative_to(REPO)}:{value.get('status')!r}"
            )
        if "nativeInputs" not in value:
            # Build-neutral contracts (action-map v5) pin no build; their
            # per-build tags come from the union-tags contract, which does.
            loaded.append((path, value, digest))
            continue
        native = _native_inputs(value["nativeInputs"])
        # Contracts pin different subsets of the same build: every one pins
        # GameAssembly and the metadata, only some also pin UnityPlayer.  Compare
        # the keys the two actually share and accumulate the rest, so a contract
        # that pins more inputs than its predecessor is not read as a conflict
        # against a key the baseline never carried.
        if expected_inputs is None:
            expected_inputs = dict(native)
        else:
            conflicting = sorted(
                key for key, actual in native.items()
                if key in expected_inputs and expected_inputs[key] != actual
            )
            if conflicting:
                raise ValueError(
                    f"native-input-disagreement={path.relative_to(REPO)}:{','.join(conflicting)}"
                )
            expected_inputs.update(native)
        loaded.append((path, value, digest))
    assert expected_inputs is not None
    gate = check_installed_native_inputs(
        expected_inputs["GameAssembly.dll"], expected_inputs["global-metadata.dat"],
        gameassembly=gameassembly, metadata=metadata,
    )
    if gate.status != "validated":
        raise ValueError(f"installed-native-inputs={gate.status}:{gate.detail}")
    native_paths = [gate.gameassembly, gate.metadata, gate.gameassembly.parent / "UnityPlayer.dll"]
    _guard_output(output, [*proof_inputs, *native_paths])
    if "UnityPlayer.dll" in expected_inputs:
        actual_unity = _sha(gate.gameassembly.parent / "UnityPlayer.dll")
        if actual_unity != expected_inputs["UnityPlayer.dll"]:
            raise ValueError(
                f"UnityPlayer.dll-sha256=expected={expected_inputs['UnityPlayer.dll']}:actual={actual_unity}"
            )
    context_start = time.perf_counter()
    ctx = NativeContext(gate.gameassembly, gate.metadata)
    context_seconds = time.perf_counter() - context_start
    contract_rows: list[dict[str, Any]] = []
    source_rows: list[dict[str, Any]] = []
    totals = {"methods": 0, "dispatcherMethods": 0, "windows": 0, "instructions": 0,
              "switchRoutes": 0, "usageCells": 0, "methodSpecs": 0,
              "actionMapIdentities": 0}
    for path, value, digest in loaded:
        try:
            counts = _validate_contract_native(ctx, value)
        except (ValueError, KeyError, IndexError, TypeError, struct.error) as error:
            raise ValueError(f"contract={path}:source-sha256={digest}:detail={error}") from error
        for key, count in counts.items():
            totals[key] += count
        rows = _atlas_rows(path, value, digest)
        source_rows.extend(rows)
        contract_rows.append({
            "path": path.relative_to(REPO).as_posix(), "sha256": digest,
            "schema": value.get("schema"), "status": value.get("status"),
            "validatedNativeFacts": counts, "atlasRows": len(rows),
        })
    atlas = _normalize_atlas_rows(source_rows)
    enrichment = _enrich_generated_members(ctx.image, atlas, derived=ctx.wrapper_members)
    report = {
        "schema": "endfield.jsondata-native-union-atlas.v1",
        "status": "validated",
        "generatedBy": Path(__file__).relative_to(REPO).as_posix(),
        "nativeInputs": expected_inputs,
        "proofSources": proof_sources,
        "context": {
            "gameassembly": str(gate.gameassembly), "metadata": str(gate.metadata),
            "imageBase": ctx.pe.image_base, "codeRegistrationVa": ctx.code_registration,
            "parsedOnce": True, "initializationSeconds": round(context_seconds, 6),
        },
        "summary": {
            "contracts": len(contract_rows), "sourceRows": len(source_rows),
            "atlasRows": len(atlas),
            "dispatcherFamilies": len({row["dispatcherFamily"] for row in atlas}),
            "nativeFactsValidated": totals,
            "generatedMemberEnrichment": enrichment,
            "elapsedSeconds": round(time.perf_counter() - started, 6),
        },
        "contracts": contract_rows,
        "rows": atlas,
        "trustGaps": [
            "The atlas indexes reviewed facts; it does not discover or promote an unknown tag.",
            "Composite Skill rows authenticate dependency bytes but do not repeat every dependency's native proof.",
            "Setter parameter types, nested generic contexts, and prose boundaries are retained in source contracts rather than normalized completely.",
            "LevelScript GameCondition rows are joined to their independently decoded named dispatcher switch; other LevelScript switch-table entry bytes are not re-decoded generically. Recorded dispatcher method pointers, branch bytes, usage cells, registered types, and contract bytes are authenticated.",
            "Only explicitly supported contract schema versions are admitted; a new shape requires a reviewed adapter update.",
        ],
    }
    after = check_installed_native_inputs(
        expected_inputs["GameAssembly.dll"], expected_inputs["global-metadata.dat"],
        gameassembly=gate.gameassembly, metadata=gate.metadata,
    )
    if after.status != "validated":
        raise ValueError(f"publication-native-inputs={after.status}:{after.detail}")
    if "UnityPlayer.dll" in expected_inputs:
        actual_unity = _sha(gate.gameassembly.parent / "UnityPlayer.dll")
        if actual_unity != expected_inputs["UnityPlayer.dll"]:
            raise ValueError(
                f"publication-UnityPlayer.dll-sha256=expected={expected_inputs['UnityPlayer.dll']}:actual={actual_unity}"
            )
    current_sources = _proof_sources(contracts)
    if current_sources != proof_sources:
        changes = _proof_source_changes(proof_sources, current_sources)
        raise ValueError("publication-proof-sources-drift:" + json.dumps(changes, sort_keys=True))
    _guard_output(output, [*proof_inputs, *native_paths])
    atomic_write_text(output, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--contract", action="append", type=Path,
                        help="explicit reviewed contract; repeat to override default discovery")
    parser.add_argument("--gameassembly", type=Path)
    parser.add_argument("--metadata", type=Path)
    args = parser.parse_args()
    contracts = [path.resolve() for path in args.contract] if args.contract else _default_contracts()
    try:
        report = build(args.output, contracts, gameassembly=args.gameassembly, metadata=args.metadata)
    except (OSError, ValueError, KeyError, IndexError, TypeError, struct.error) as error:
        print(json.dumps({"status": "failed", "detail": str(error)}), file=sys.stderr)
        return 1
    print(json.dumps(report["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
