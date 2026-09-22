"""Build a fail-closed current-build JsonData union atlas.

The atlas reads reviewed, byte-pinned contracts, authenticates the selected
native inputs, parses GameAssembly/metadata once, validates their native
identities, and writes generated evidence under reports/.

It does not discover union layouts or promote schemas.  Unsupported contract
facts remain present only through their contract hash and are listed as trust
gaps in the report.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import struct
import sys
import time
from pathlib import Path
from typing import Any, Iterable

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import NativeImage
from scripts.game_data.memorypack.wrapper_members import derive_from_image
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
# the byte-pinned JSON contracts.  Adding a shape requires an explicit adapter
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
    "endfield.action-map-layouts.v2": ("levelscript_actions", frozenset({None})),
    "endfield.skill-timeline-continuous-find-target-native-contract.v1": ("selector_routes", frozenset({"exact-current-build"})),
    "endfield.skill-timeline-create-buff-native-contract.v1": ("dispatcher", frozenset({"exact-current-build"})),
    "endfield.skill-timeline-find-target-native-contract.v1": ("selector_routes", frozenset({"exact-current-build"})),
    "endfield.skill-timeline-play-animation-native-contract.v1": ("identity_only", frozenset({"exact-current-build"})),
    "endfield.skill-timeline-play-animation-step-native-contract.v1": ("dispatcher", frozenset({"exact-current-build"})),
    "endfield.skill-timeline-shared-sequence-native-contract.v1": ("shared_sequence", frozenset({"exact-current-build-composite"})),
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


def _assignment_strings(path: Path) -> list[tuple[str, str]]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    except (OSError, SyntaxError, UnicodeError):
        return []
    found: list[tuple[str, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            # ``CONTRACT_SHA256 = "..."`` in a single-contract loader.
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            value = node.value
            if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
                continue
            for target in targets:
                if isinstance(target, ast.Name) and target.id.endswith("CONTRACT_SHA256"):
                    found.append((target.id, value.value.upper()))
        elif isinstance(node, ast.Call):
            # A registry of contracts pins each digest as a literal argument
            # of its record constructor (``Frontier("frontier8", ..., sha, ...)``).
            func = node.func
            callee = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
            if not callee:
                continue
            for argument in [*node.args, *(keyword.value for keyword in node.keywords)]:
                if (
                    isinstance(argument, ast.Constant)
                    and isinstance(argument.value, str)
                    and len(argument.value) == 64
                    and all(c in "0123456789abcdefABCDEF" for c in argument.value)
                ):
                    found.append((f"{callee}()", argument.value.upper()))
    return found


def _pin_for_contract(contract: Path, digest: str) -> dict[str, str]:
    candidates: list[dict[str, str]] = []
    for source in GAME_DATA.rglob("*.py"):
        text = source.read_text(encoding="utf-8-sig", errors="replace")
        if contract.name not in text and source.stem != contract.stem:
            continue
        for constant, value in _assignment_strings(source):
            if value == digest:
                candidates.append({
                    "loader": source.relative_to(REPO).as_posix(),
                    "constant": constant,
                    "sha256": value,
                })
    if len(candidates) != 1:
        raise ValueError(
            f"contract-pin={contract.relative_to(REPO)} expected-one-match actual={candidates}"
        )
    return candidates[0]


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
            raise ValueError(f"usage-cell={usage_va:#x}")
        if "registeredTypeIndex" not in row:
            return
        index = unresolved_usage_index(
            raw, self.registration["typesCount"], tag=1,
            source="GameAssembly.dll", offset=usage_va,
        )
        if index != row["registeredTypeIndex"]:
            raise ValueError(f"registered-type-index={usage_va:#x}:{index}")
        type_pointer = self.pe.u64_at_va(int(self.registration["types"], 16) + index * 8)
        if "typePointerVa" in row and type_pointer != int(row["typePointerVa"], 0):
            raise ValueError(f"type-pointer={usage_va:#x}:{type_pointer:#x}")
        if "typePointerRva" in row and type_pointer != self.pe.image_base + _int(row["typePointerRva"]):
            raise ValueError(f"type-pointer={usage_va:#x}:{type_pointer:#x}")
        definition = struct.unpack_from("<Q", self.pe.bytes_at_va(type_pointer, 16))[0]
        expected_definition = row.get("wrapperTypeDefinition", row.get("typeDefinition"))
        if expected_definition is not None and definition != expected_definition:
            raise ValueError(f"type-definition={usage_va:#x}:{definition}")
        expected_name = row.get("wrapperName")
        if expected_name is not None:
            actual_name = self.md.type_full_name(self.md.types[definition])
            if actual_name != expected_name:
                raise ValueError(f"type-name={usage_va:#x}:{actual_name}")

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
    counts = {"methods": 0, "dispatcherMethods": 0, "windows": 0, "instructions": 0,
              "switchRoutes": 0, "usageCells": 0, "methodSpecs": 0,
              "actionMapIdentities": 0}
    methods: set[tuple[Any, ...]] = set()
    windows: set[tuple[int, int, str]] = set()
    instructions: set[tuple[int, str]] = set()
    usages: set[tuple[str, str]] = set()
    switches: set[tuple[int, int, int]] = set()
    action_identities: set[tuple[str, str]] = set()
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
                ctx.validate_usage(node)
                usages.add(key)
        if {"switchTableRva", "switchEntryCount", "unionTag"} <= node.keys():
            key = (node["switchTableRva"], node["switchEntryCount"], node["unionTag"])
            if key not in switches:
                ctx.validate_switch(node)
                switches.add(key)
        identity = node.get("nativeIdentity")
        if isinstance(identity, dict) and "branchCodeHex" in identity:
            key = (identity["branchBodyVa"], identity["usageRawHex"])
            if key not in action_identities:
                ctx.validate_action_map_identity(identity)
                action_identities.add(key)
        elif isinstance(identity, dict) and ("usageCellRva" in identity or "usageCellVa" in identity):
            merged = {**identity}
            if "wrapperName" in node:
                merged["wrapperName"] = node["wrapperName"]
            key = (str(merged.get("usageCellRva", merged.get("usageCellVa"))), merged["usageRawHex"])
            if key not in usages:
                ctx.validate_usage(merged)
                usages.add(key)
        if {"typeDefinition", "methodToken", "methodRva"} <= node.keys():
            key = (_int(node["typeDefinition"]), _int(node["methodToken"]))
            if key not in dispatcher_identities:
                ctx.validate_dispatcher_identity(node)
                dispatcher_identities.add(key)
        if node.get("methodSpecProvider") is True:
            key = (str(node.get("usageCellRva")), int(node.get("index", -1)))
            if key not in method_spec_providers:
                ctx.validate_method_spec_provider(node)
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
        for layout in value["layouts"]:
            rows.append({
                **common, "dispatcherFamily": f"LevelScript:{layout['family']}",
                "physicalTag": layout["tag"], "serializedMemberCount": layout["memberCount"],
                "wrapperName": layout["wrapperName"], "readOrder": layout.get("fields"),
                "setterMethods": layout.get("nativeIdentity", {}).get("generatedSetterOrder"),
                "trust": "native-validated-reviewed-row",
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


def _enrich_generated_members(image: NativeImage, rows: list[dict[str, Any]]) -> dict[str, Any]:
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
    derived = derive_from_image(image)
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


def build(output: Path, contracts: list[Path]) -> dict[str, Any]:
    started = time.perf_counter()
    output = output.resolve()
    reports = (REPO / "reports").resolve()
    if reports not in output.parents:
        raise ValueError(f"output-must-be-under={reports}")
    loaded: list[tuple[Path, dict[str, Any], str, dict[str, str]]] = []
    expected_inputs: dict[str, str] | None = None
    input_set: str | None = None
    for path in contracts:
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest().upper()
        value = json.loads(raw)
        schema = value.get("schema")
        if schema not in SUPPORTED_SCHEMAS:
            raise ValueError(f"unsupported-contract-schema={path.relative_to(REPO)}:{schema!r}")
        if value.get("status") not in SUPPORTED_SCHEMAS[schema][1]:
            raise ValueError(
                f"contract-status={path.relative_to(REPO)}:{value.get('status')!r}"
            )
        pin = _pin_for_contract(path, digest)
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
        row_input_set = value.get("inputSetSha256")
        if row_input_set:
            if input_set is None:
                input_set = row_input_set.upper()
            elif input_set != row_input_set.upper():
                raise ValueError(f"input-set-disagreement={path.relative_to(REPO)}")
        for dependency in value.get("dependencies", []):
            dependency_path = path.parent / dependency["path"]
            if not dependency_path.exists():
                dependency_path = GAME_DATA / dependency["path"]
            actual = _sha(dependency_path)
            if actual != dependency["sha256"].upper():
                raise ValueError(
                    f"dependency-sha256={path.relative_to(REPO)}:{dependency['path']}:"
                    f"expected={dependency['sha256']}:actual={actual}"
                )
        loaded.append((path, value, digest, pin))
    assert expected_inputs is not None
    gate = check_installed_native_inputs(
        expected_inputs["GameAssembly.dll"], expected_inputs["global-metadata.dat"]
    )
    if gate.status != "validated":
        raise ValueError(f"installed-native-inputs={gate.status}:{gate.detail}")
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
    for path, value, digest, pin in loaded:
        counts = _validate_contract_native(ctx, value)
        for key, count in counts.items():
            totals[key] += count
        rows = _atlas_rows(path, value, digest)
        source_rows.extend(rows)
        contract_rows.append({
            "path": path.relative_to(REPO).as_posix(), "sha256": digest,
            "pin": pin, "schema": value.get("schema"), "status": value.get("status"),
            "validatedNativeFacts": counts, "atlasRows": len(rows),
        })
    atlas = _normalize_atlas_rows(source_rows)
    enrichment = _enrich_generated_members(ctx.image, atlas)
    report = {
        "schema": "endfield.jsondata-native-union-atlas.v1",
        "status": "validated",
        "generatedBy": Path(__file__).relative_to(REPO).as_posix(),
        "nativeInputs": expected_inputs,
        "inputSetSha256": input_set,
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
            "LevelScript switch-table entry bytes are not re-decoded generically; dispatcher method pointers, branch bytes, usage cells, registered types, and contract bytes are authenticated.",
            "Only explicitly supported contract schema versions are admitted; a new shape requires a reviewed adapter update.",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--contract", action="append", type=Path,
                        help="explicit reviewed contract; repeat to override default discovery")
    args = parser.parse_args()
    contracts = [path.resolve() for path in args.contract] if args.contract else _default_contracts()
    try:
        report = build(args.output, contracts)
    except (OSError, ValueError, KeyError, IndexError, TypeError, struct.error) as error:
        print(json.dumps({"status": "failed", "detail": str(error)}), file=sys.stderr)
        return 1
    print(json.dumps(report["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
