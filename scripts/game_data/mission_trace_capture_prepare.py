"""Prepare bounded named mission observers from the explicitly selected client.

This is offline preparation for EndfieldCapture, never a live attachment. The
reviewed recipe contains names and typed field paths; all addresses and code
windows are derived again and published only under an ignored output root.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import struct
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs, sha256_file
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.mission_trace_abi import prove_string_argument_mode
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.il2cpp.native_image import NativeImage
from scripts.game_data.il2cpp.protocol import (
    field_defaults, read_compressed_int32, read_compressed_uint32,
    runtime_type_field_offsets, runtime_type_name,
)
from scripts.repo_paths import REPO_ROOT

RECIPE_PATH = CONTRACTS_DIR / "mission_trace_capture.json"
PROFILE_RECIPES = {"mission": RECIPE_PATH, "buff": CONTRACTS_DIR / "buff_runtime_trace_capture.json"}
RECIPE_SCHEMA = "endfield.mission-trace-capture-recipe.v3"
REFERENCE_RECIPE_SCHEMA = "endfield.mission-trace-capture-recipe.v4"
BUILD_SCHEMA = "endfieldCapture.missionTraceBuild.v1"
ABI_ID = "win64.transparent_entry_snapshot.v1"
NO_CHAIN = 4097
MAX_HOOKS = 96
MAX_BODY_BYTES = 1024 * 1024
_NAME = re.compile(r"[A-Za-z0-9_.$<>+`-]{1,127}\Z")
_WIDTH = {"bool": 8, "int": 32, "uint": 32, "long": 64, "ulong": 64}
_VALUE_KIND = {"bool": 5, "int": 2, "uint": 2, "long": 1, "ulong": 1, "string": 3}


class PreparationError(ValueError):
    """A selected method or field no longer matches the reviewed observer."""


def read_recipe(path: Path = RECIPE_PATH) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schema") not in {RECIPE_SCHEMA, REFERENCE_RECIPE_SCHEMA}:
        raise PreparationError("mission_trace.recipe: unsupported schema")
    hooks = value.get("hooks")
    if not isinstance(hooks, list) or not 1 <= len(hooks) <= MAX_HOOKS:
        raise PreparationError(f"mission_trace.recipe: expected 1..{MAX_HOOKS} hooks")
    names = [hook.get("name") for hook in hooks]
    if any(not isinstance(name, str) or not _NAME.fullmatch(name) for name in names) or len(set(names)) != len(names):
        raise PreparationError("mission_trace.recipe: invalid or duplicate hook names")
    return value


class SelectedMethods:
    """Metadata signatures, current field offsets, and physical native entries."""

    def __init__(self, image: NativeImage):
        self.image = image
        self.index = BodyIndex(image)
        self._type_names: dict[int, str] = {}
        self._field_cache: dict[str, dict[str, tuple[str, int, int]]] = {}

    def type_name(self, type_index: int) -> str:
        if type_index not in self._type_names:
            address = int(self.image.registration["types"], 16) + type_index * 8
            self._type_names[type_index] = runtime_type_name(self.image.pe, self.image.metadata, self.image.pe.u64_at_va(address))
        return self._type_names[type_index]

    def parent(self, name: str) -> str:
        td = self.index.types.get(name)
        if td is None and "<" in name and name.endswith(">"):
            td = self.index.types.get(name.split("<", 1)[0])
            if td is not None and td.generic_container_index < 0:
                td = None
        parent = self.type_name(td.parent_index) if td is not None and td.parent_index >= 0 else ""
        # A closed generic's non-generic ancestor is a metadata relationship,
        # not proof of instantiated field offsets or a value argument's ABI.
        # Substitution-dependent ancestry needs a separate resolver.
        return "" if "VAR[" in parent else parent

    def is_enum(self, name: str) -> bool:
        return self.parent(name) == "System.Enum"

    def is_value_type(self, name: str) -> bool:
        return self.parent(name) in {"System.ValueType", "System.Enum"}

    def value_size(self, name: str) -> int:
        """Derive unboxed size from this build's Il2CppTypeDefinitionSizes."""
        td = self.index.types.get(name)
        if td is None and name.endswith("<string>"):
            return self.string_value_layout(name)["unboxedBytes"]
        if td is None or not self.is_value_type(name):
            raise PreparationError(f"mission_trace.abi: not a named value type: {name}")
        registration = self.image.registration
        count = int(registration["typeDefinitionsSizesCount"])
        if not 0 <= td.index < count:
            raise PreparationError(f"mission_trace.abi: type size index outside selected table: {name}")
        table = int(registration["typeDefinitionsSizes"], 16)
        row = self.image.pe.u64_at_va(table + td.index * 8)
        if not row:
            raise PreparationError(f"mission_trace.abi: missing selected type size: {name}")
        size = self.image.pe.u32_at_va(row) - 16
        if not 1 <= size <= 4096:
            raise PreparationError(f"mission_trace.abi: invalid unboxed value size: {name}:{size}")
        return size

    def string_value_layout(self, name: str) -> dict[str, Any]:
        """Prove a closed, sequential, single-reference generic value wrapper.

        Open generic size/offset tables contain placeholders, not the closed
        layout. A sole string field, sequential layout and default class size
        establish offset zero and eight bytes on the selected Win64 ABI. Reject
        every other generic layout instead of substituting placeholder offsets.
        """
        label = f"mission_trace.abi: generic string wrapper {name}"
        td = self.index.types.get(name[:-8]) if name.endswith("<string>") else None
        if (td is None or self.parent(name) != "System.ValueType"
                or td.flags & 0x18 != 0x08 or not td.bitfield & 0x800
                or td.field_count != 1 or td.generic_container_index < 0):
            raise PreparationError(f"{label}: requires sequential single-field value type with default class size")
        metadata = self.image.metadata
        section = metadata.sections["genericContainers"]
        offset = section.offset + td.generic_container_index * 16
        if not section.offset <= offset <= section.offset + section.size - 16:
            raise PreparationError(f"{label}: generic container outside selected metadata")
        owner, count, is_method, parameter = struct.unpack_from("<iiii", metadata.buf, offset)
        if owner != td.index or count != 1 or is_method != 0 or parameter < 0:
            raise PreparationError(f"{label}: generic container identity/arity drift")
        fields = list(metadata.fields_for(td))
        if (len(fields) != 1 or self.type_name(fields[0].type_index) != f"VAR[{parameter}]"
                or self.field_attributes(fields[0].type_index) & 0x10):
            raise PreparationError(f"{label}: sole instance field must be the selected type parameter")
        return {"definition": name[:-8], "field": metadata.string(fields[0].name_index),
                "closedType": name, "fieldType": "string", "unboxedOffset": 0, "unboxedBytes": 8,
                "evidence": "selected generic container and sole instance VAR field; sequential layout; default class size; Win64 reference layout"}

    def enum_members(self, name: str) -> dict[str, Any]:
        """Read signed/unsigned Int32 defaults using selected primitive types."""
        _owner, underlying, _offset = self.field(f"{name}::value__")
        if underlying not in {"int", "uint"} or not self.is_enum(name):
            raise PreparationError(f"mission_trace.enum: unsupported enum backing: {name}:{underlying}")
        td = self.index.types[name]
        defaults = field_defaults(self.image.metadata)
        section = self.image.metadata.sections["fieldAndParameterDefaultValueData"]
        rows = []
        for field in self.image.metadata.fields_for(td):
            member = self.image.metadata.string(field.name_index)
            if member == "value__":
                continue
            default = defaults.get(field.index)
            if default is None:
                raise PreparationError(f"mission_trace.enum: missing member default: {name}.{member}")
            primitive, data_index = default
            if self.type_name(primitive) != underlying:
                raise PreparationError(f"mission_trace.enum: member primitive drift: {name}.{member}")
            offset = section.offset + data_index
            if not section.offset <= offset < section.offset + section.size:
                raise PreparationError(f"mission_trace.enum: member offset outside blob: {name}.{member}")
            reader = read_compressed_int32 if underlying == "int" else read_compressed_uint32
            try:
                value, size = reader(self.image.metadata.buf[section.offset:section.offset + section.size], data_index)
            except (ValueError, IndexError, struct.error) as exc:
                raise PreparationError(f"mission_trace.enum: invalid member encoding: {name}.{member}: {exc}") from exc
            if offset + size > section.offset + section.size:
                raise PreparationError(f"mission_trace.enum: member exceeds blob: {name}.{member}")
            rows.append({"value": value, "name": member, "fieldIndex": field.index,
                         "token": f"0x{field.token:08x}", "dataIndex": data_index,
                         "encodedBytes": self.image.metadata.buf[offset:offset + size].hex()})
        return {"type": name, "storageType": underlying, "valueBits": 32,
                "signed": underlying == "int", "members": rows,
                "source": "selected metadata default blob and native MetadataRegistration.types"}

    def string_argument_proof(self, hook: dict[str, Any], arg: int, mode: str) -> dict[str, Any]:
        if not 0 <= arg < 4:
            raise PreparationError(f"{hook['name']}: string wrapper proof requires a GP register argument")
        _method, _parameters, pointer = self.resolve(hook)
        end = self.index.extents.get(pointer)
        if end is None or not 16 <= end - pointer <= 16384:
            raise PreparationError(f"{hook['name']}: missing bounded native string-wrapper consumer body")
        equality = self.index.body("System.String", "op_Equality", parameters=["System.String", "System.String"])
        consumer = equality.pointer
        # Some builds register a tiny op_Equality wrapper that clears only
        # MethodInfo and tail-jumps to the named two-string Equals body.
        # Preserve both string registers; do not follow arbitrary helpers.
        tail = equality.rows[-1] if equality.rows else {}
        target = re.fullmatch(r"jmp 0x([0-9a-f]+)", tail.get("text", ""))
        prefix = [row.get("text") for row in equality.rows[:-1]]
        if (target and prefix in ([], ["xor r8d, r8d"])
                and "System.String.Equals" in self.index.names_of(int(target.group(1), 16))
                and ["System.String", "System.String"] in self.index.parameter_types(int(target.group(1), 16))):
            consumer = int(target.group(1), 16)
        try:
            proof = prove_string_argument_mode(self.index._decode(pointer, end - pointer),
                argument_register=("rcx", "rdx", "r8", "r9")[arg], equality_pointer=consumer, mode=mode)
            proof["consumerRva"] = f"0x{consumer - self.image.pe.image_base:x}"
            if consumer != equality.pointer:
                proof["consumer"] = "System.String.Equals(string,string)"
                proof["via"] = {"symbol": equality.symbol, "rva": f"0x{equality.pointer - self.image.pe.image_base:x}",
                    "bodySha256": hashlib.sha256(self.image.pe.bytes_at_va(equality.pointer, equality.size)).hexdigest(),
                    "evidence": "named equality wrapper preserves both string arguments and tail-jumps to named Equals"}
            return proof
        except ValueError as exc:
            raise PreparationError(f"{hook['name']}: string wrapper native argument proof failed: {exc}") from exc

    def is_owner(self, actual: str, owner: str) -> bool:
        seen: set[str] = set()
        while actual and actual not in seen:
            if actual == owner:
                return True
            seen.add(actual)
            actual = self.parent(actual)
        return False

    def field(self, qualified: str) -> tuple[str, str, int]:
        owner, separator, name = qualified.partition("::")
        if not separator:
            raise PreparationError(f"mission_trace.field: unqualified field {qualified}")
        if owner not in self._field_cache:
            td = self.index.types.get(owner)
            if td is None:
                if not owner.endswith("<string>"):
                    raise PreparationError(f"mission_trace.field: missing owner {owner}")
                layout = self.string_value_layout(owner)
                self._field_cache[owner] = {layout["field"]: ("string", 16, 0)}
            else:
                offsets = runtime_type_field_offsets(self.image.metadata, self.image.pe, self.image.registration, td.index)
                self._field_cache[owner] = {
                    self.image.metadata.string(f.name_index): (self.type_name(f.type_index), offsets[self.image.metadata.string(f.name_index)], self.field_attributes(f.type_index))
                    for f in self.image.metadata.fields_for(td)
                }
        if name not in self._field_cache[owner]:
            raise PreparationError(f"mission_trace.field: missing field {qualified}")
        field_type, offset, attributes = self._field_cache[owner][name]
        if attributes & 0x10:
            raise PreparationError(f"mission_trace.field: sampled field became static: {qualified}")
        return owner, field_type, offset

    def field_attributes(self, type_index: int) -> int:
        """Read FieldAttributes from the selected declared Il2CppType."""
        if not 0 <= type_index < self.image.registration["typesCount"]:
            raise PreparationError(f"mission_trace.field: type index outside selected table: {type_index}")
        table = int(self.image.registration["types"], 16)
        pointer = self.image.pe.u64_at_va(table + type_index * 8)
        if not pointer:
            raise PreparationError(f"mission_trace.field: missing declared native type: {type_index}")
        return int.from_bytes(self.image.pe.bytes_at_va(pointer + 8, 2), "little")

    def resolve(self, hook: dict[str, Any]) -> tuple[Any, list[dict[str, str]], int]:
        td = self.index.types.get(hook["type"])
        if td is None:
            raise PreparationError(f"{hook['name']}: missing type {hook['type']}")
        candidates = []
        for m in self.image.metadata.methods[td.method_start:td.method_start + td.method_count]:
            if self.image.metadata.string(m.name_index) != hook["method"]:
                continue
            parameters = [{"name": self.image.metadata.string(p.name_index), "type": self.type_name(p.type_index)} for p in self.image.metadata.parameters_for(m)]
            if parameters == hook["parameters"]:
                candidates.append((m, parameters))
        if len(candidates) != 1:
            raise PreparationError(f"{hook['name']}: signature matched {len(candidates)} methods; expected {hook['parameters']!r}")
        method, parameters = candidates[0]
        actual_return = self.type_name(method.return_type)
        if actual_return != hook["returnType"] or bool(method.flags & 0x10) != hook["static"]:
            raise PreparationError(f"{hook['name']}: return/static drift; expected {hook['returnType']}/{hook['static']}, actual {actual_return}/{bool(method.flags & 0x10)}")
        if actual_return not in {"void", "bool", "int", "uint", "long", "ulong"} and not self.is_enum(actual_return):
            raise PreparationError(f"{hook['name']}: hidden return ABI unsupported for {actual_return}")
        pointer = self.image.method_pointer_va(method)
        # Folded native bodies can receive unrelated instance types. Reject them
        # rather than applying one owner's field layout to another caller.
        aliases = self.index.names_by_pointer.get(pointer) or []
        symbols = {f"{row.get('type')}.{row.get('method')}" for row in aliases}
        alias_indices = {row.get("methodIndex") for row in aliases}
        expected = f"{hook['type']}.{hook['method']}"
        if symbols != {expected} or alias_indices != {method.index}:
            raise PreparationError(f"{hook['name']}: shared or unregistered native body; aliases={sorted(symbols)!r}, methodIndices={sorted(str(index) for index in alias_indices)!r}")
        return method, parameters, pointer

    def argument(self, hook: dict[str, Any], name: str) -> tuple[int, str]:
        if name == "this":
            if hook["static"]:
                raise PreparationError(f"{hook['name']}: static method has no this")
            return 0, hook["type"]
        hits = [(position, p["type"]) for position, p in enumerate(hook["parameters"]) if p["name"] == name]
        if len(hits) != 1:
            raise PreparationError(f"{hook['name']}: argument missing/duplicate {name}")
        position, parameter_type = hits[0]
        slot = position + int(not hook["static"])
        if slot > 7:
            raise PreparationError(f"{hook['name']}: argument beyond bounded ABI slots: {name}")
        return slot, parameter_type

    def compile_field(self, hook: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
        arg, current_type = self.argument(hook, spec["argument"])
        path = spec.get("path") or []
        chains: list[int] = []
        offset = 0
        inline = False
        representation = spec.get("argumentRepresentation")
        native_argument_proof = None
        if representation is None and path and spec["argument"] != "this" and self.is_value_type(current_type):
            raise PreparationError(f"{hook['name']}.{spec['label']}: value-type argument path requires explicit argumentRepresentation")
        if representation is not None:
            if not isinstance(representation, dict) or representation.get("mode") not in {"indirectValue", "inlineValue"}:
                raise PreparationError(f"{hook['name']}.{spec['label']}: unsupported argument representation")
            actual_size = self.value_size(current_type)
            if representation.get("bytes") != actual_size:
                raise PreparationError(f"{hook['name']}.{spec['label']}: value ABI size drift; expected {representation.get('bytes')}, actual {actual_size}")
            if representation["mode"] == "indirectValue":
                if actual_size in {1, 2, 4, 8}:
                    if (actual_size != 8 or not current_type.endswith("<string>")
                            or spec["type"] != "string" or len(path) != 1
                            or representation.get("nativeProof") != "stringEqualityArgument"):
                        raise PreparationError(f"{hook['name']}.{spec['label']}: indirect value requires native string argument proof or Win64 indirect aggregate size")
                    native_argument_proof = self.string_argument_proof(hook, arg, "indirectValue")
            elif actual_size != 8 or len(path) != 1 or spec["type"] != "string":
                raise PreparationError(f"{hook['name']}.{spec['label']}: inline value supports only an eight-byte string wrapper")
            elif current_type.endswith("<string>"):
                if representation.get("nativeProof") != "stringEqualityArgument":
                    raise PreparationError(f"{hook['name']}.{spec['label']}: generic string wrapper requires native argument proof; layout does not establish passing mode")
                native_argument_proof = self.string_argument_proof(hook, arg, "inlineValue")
            if not path:
                raise PreparationError(f"{hook['name']}.{spec['label']}: value argument requires a reviewed field path")
            inline = True
        resolved_path: list[dict[str, Any]] = []
        for position, step in enumerate(path):
            owner, actual_type, field_offset = self.field(step["field"])
            if not self.is_owner(current_type, owner) or actual_type != step["type"]:
                raise PreparationError(f"{hook['name']}.{spec['label']}: field path drift at {step['field']}; receiver={current_type}, actualType={actual_type}, expectedType={step['type']}")
            # Runtime offsets on a value type include the boxed object header.
            # Inline payloads begin at that type's first unboxed data byte.
            field_offset -= 16 if inline else 0
            if position == 0 and representation is not None:
                field_bytes = _WIDTH.get(actual_type, 0) // 8
                if not field_bytes:
                    field_bytes = self.value_size(actual_type) if self.is_value_type(actual_type) else 8
                if field_offset < 0 or field_offset + field_bytes > actual_size:
                    raise PreparationError(f"{hook['name']}.{spec['label']}: field extent outside unboxed argument: offset={field_offset}, bytes={field_bytes}, size={actual_size}")
            offset += field_offset
            if not 0 <= offset <= 4096:
                raise PreparationError(f"{hook['name']}.{spec['label']}: field offset outside 0..4096")
            resolved_path.append({"field": step["field"], "type": actual_type, "offset": field_offset})
            if owner.endswith("<string>") and owner not in self.index.types:
                resolved_path[-1]["layoutProof"] = self.string_value_layout(owner)
            current_type = actual_type
            if position != len(path) - 1:
                inline = step.get("mode") == "inline"
                if inline != self.is_value_type(actual_type):
                    raise PreparationError(f"{hook['name']}.{spec['label']}: intermediate representation drift at {step['field']}")
                if not inline:
                    chains.append(offset)
                    offset = 0
        if current_type != spec["type"]:
            raise PreparationError(f"{hook['name']}.{spec['label']}: expected {spec['type']}, actual {current_type}")
        value_representation = spec.get("valueRepresentation")
        if value_representation not in {None, "referenceIdentity"}:
            raise PreparationError(f"{hook['name']}.{spec['label']}: unsupported value representation")
        reference_identity = value_representation == "referenceIdentity"
        if reference_identity and (representation is not None or current_type not in self.index.types
                                   or self.is_value_type(current_type)):
            raise PreparationError(f"{hook['name']}.{spec['label']}: reference identity requires a named managed reference type, not a value layout")
        enum = self.is_enum(current_type)
        underlying = "ulong" if reference_identity else current_type
        if enum:
            _owner, underlying, _offset = self.field(f"{current_type}::value__")
            if underlying not in {"int", "uint"}:
                raise PreparationError(f"{hook['name']}.{spec['label']}: enum storage drift for {current_type}; expected int/uint, actual {underlying}")
        width = 64 if reference_identity else _WIDTH.get(current_type, 32 if enum else None)
        if not path and current_type != "string":
            if current_type in {"float", "double"}:
                raise PreparationError(f"{hook['name']}.{spec['label']}: floating register argument is unsupported by the GP/stack observer ABI")
            if width is None:
                raise PreparationError(f"{hook['name']}.{spec['label']}: unsupported argument type {current_type}")
            kind = 4
        else:
            kind = 1 if reference_identity else _VALUE_KIND.get(current_type, 2 if enum else None)
            if kind is None:
                raise PreparationError(f"{hook['name']}.{spec['label']}: unsupported leaf type {current_type}")
        # A stored System.String is an object reference, whereas a direct
        # string argument already points at the IL2CPP string object. The
        # observer's kind=3 reads its length/data from that object, so the
        # final stored reference must be dereferenced as well.
        inline_string = representation is not None and representation["mode"] == "inlineValue"
        if inline_string and (offset != 0 or chains):
            raise PreparationError(f"{hook['name']}.{spec['label']}: inline string wrapper is not a sole reference at offset zero")
        if kind == 3 and path and not inline_string:
            chains.append(offset)
            offset = 0
        if len(chains) > 2:
            raise PreparationError(f"{hook['name']}.{spec['label']}: exceeds two field indirections")
        chain0, chain1 = (chains + [NO_CHAIN, NO_CHAIN])[:2]
        result = {"label": spec["label"], "type": current_type, "valueBits": width, "arg": arg, "kind": kind,
                  "offset": offset, "chain0": chain0, "chain1": chain1, "fieldPath": resolved_path,
                  "argumentName": spec["argument"], "role": spec.get("role", "observation"),
                  "storageType": underlying, "signed": underlying in {"int", "long"},
                  "observation": "argument" if not path else "receiver-field" if spec["argument"] == "this" else "argument-field"}
        if reference_identity:
            result["valueRepresentation"] = "referenceIdentity"
        if representation is not None:
            result["argumentRepresentation"] = {**representation,
                "evidence": "selected generic layout and separately checked native argument proof" if native_argument_proof else "selected Il2CppTypeDefinitionSizes.instance_size minus object header; Win64 aggregate ABI"}
            if native_argument_proof:
                result["argumentRepresentation"]["nativeArgumentProof"] = native_argument_proof
        return result


def compile_hooks(selected: SelectedMethods, recipe: dict[str, Any]) -> list[dict[str, Any]]:
    if not 1 <= len(recipe["hooks"]) <= MAX_HOOKS:
        raise PreparationError(f"mission_trace.recipe: expected 1..{MAX_HOOKS} hooks")
    hooks = []
    seen_rvas: set[int] = set()
    for spec in recipe["hooks"]:
        if any(field.get("valueRepresentation") is not None for field in spec["fields"]) and recipe.get("schema") != REFERENCE_RECIPE_SCHEMA:
            raise PreparationError("mission_trace.recipe: reference identities require recipe v4")
        method, _parameters, pointer = selected.resolve(spec)
        end = selected.index.extents.get(pointer)
        if end is None or not 16 <= end - pointer <= MAX_BODY_BYTES:
            raise PreparationError(f"{spec['name']}: missing bounded .pdata entry or body outside 16..{MAX_BODY_BYTES} bytes")
        body_size = end - pointer
        window_size = min(body_size, 64)
        body = selected.image.pe.bytes_at_va(pointer, body_size)
        fields = [selected.compile_field(spec, field) for field in spec["fields"]]
        labels = [f["label"] for f in fields]
        if len(fields) > 8 or len(set(labels)) != len(labels):
            raise PreparationError(f"{spec['name']}: more than eight fields or duplicate field labels")
        rva = pointer - selected.image.pe.image_base
        if rva in seen_rvas:
            raise PreparationError(f"{spec['name']}: duplicate native entry")
        seen_rvas.add(rva)
        hooks.append({"name": spec["name"], "module": "GameAssembly.dll", "rva": f"0x{rva:x}", "abiId": ABI_ID,
                      "expectedBytes": body[:window_size].hex(),
                      "readProgram": "".join(f"{f['arg']},{f['kind']},{f['offset']},{f['chain0']},{f['chain1']};" for f in fields),
                      "fields": fields, "symbol": f"{spec['type']}.{spec['method']}",
                      "methodIndex": method.index, "returnType": spec["returnType"], "parameters": spec["parameters"],
                      "bodyBytes": body_size, "bodySha256": hashlib.sha256(body).hexdigest(),
                      "receiverIdentity": None if spec["static"] else {"arg": 0, "type": spec["type"], "source": "raw entry argument"},
                      "semanticRole": spec.get("semanticRole", "named entry observation"),
                      "evidenceBoundary": spec["evidenceBoundary"]})
    return hooks


def prepare(game_dir: Path, mission: str = "all", *, recipe: dict[str, Any] | None = None,
            profile: str = "mission") -> dict[str, Any]:
    if profile not in PROFILE_RECIPES or (profile == "buff" and mission != "all"):
        raise PreparationError("mission_trace.profile: expected mission or buff; buff requires --mission all")
    game_dir = Path(game_dir).resolve()
    if game_dir.name.casefold() == "endfield_data":
        game_dir = game_dir.parent
    if not re.fullmatch(r"[a-z0-9_]{1,80}", mission):
        raise PreparationError("mission_trace: invalid focus mission")
    files = {"executable": ("Endfield.exe", game_dir / "Endfield.exe"),
             "gameAssembly": ("GameAssembly.dll", game_dir / "GameAssembly.dll"),
             "metadata": ("Endfield_Data/il2cpp_data/Metadata/global-metadata.dat", game_dir / "Endfield_Data/il2cpp_data/Metadata/global-metadata.dat")}
    gate = check_installed_native_inputs(gameassembly=files["gameAssembly"][1], metadata=files["metadata"][1])
    if not gate.validated:
        raise PreparationError(f"mission_trace.native: {gate.status}: {gate.detail}")
    recipe = read_recipe(PROFILE_RECIPES[profile]) if recipe is None else recipe
    pins = {}
    for role, (relative, path) in files.items():
        if not path.is_file():
            raise PreparationError(f"mission_trace.native: missing {relative}")
        digest = {"gameAssembly": gate.gameassembly_sha256, "metadata": gate.metadata_sha256}.get(role) or sha256_file(path)
        pins[role] = {"relativePath": relative, "bytes": path.stat().st_size, "sha256": digest}
    selected = SelectedMethods(NativeImage(gate.gameassembly, gate.metadata, label="mission_trace"))
    hooks = compile_hooks(selected, recipe)
    enum_types = sorted({field["type"] for hook in hooks for field in hook["fields"] if selected.is_enum(field["type"])})
    enum_definitions = {name: selected.enum_members(name) for name in enum_types}
    # Nothing is published if an installer changed the selected inputs mid-run.
    final_gate = check_installed_native_inputs(gate.gameassembly_sha256, gate.metadata_sha256,
                                              gameassembly=gate.gameassembly, metadata=gate.metadata)
    if not final_gate.validated or sha256_file(files["executable"][1]) != pins["executable"]["sha256"]:
        raise PreparationError("mission_trace.native: selected inputs changed during preparation")
    return {"schema": BUILD_SCHEMA, "gameBuild": f"endfield-gameassembly-{gate.gameassembly_sha256[:12]}",
            "profile": "mission-trace", "processName": "Endfield.exe", "files": pins,
            "preparedAt": datetime.now(timezone.utc).isoformat(),
            "focusMission": mission, "recordingScope": "buff-runtime-unfiltered" if profile == "buff" else "all-named-context-unfiltered",
            "missionSelection": {"mode": "not-selected" if profile == "buff" else "all-missions" if mission == "all" else "named-analysis-focus", "nativeFilter": False},
            "recipeSchema": recipe["schema"], "missionTraceHooks": hooks,
            "enumDefinitions": enum_definitions,
            "coverageGaps": recipe.get("coverageGaps", []),
            "evidenceBoundary": recipe["evidenceBoundary"]}


def checked_output(path: Path) -> Path:
    resolved = path.resolve()
    allowed = [REPO_ROOT / root for root in ("reports", "scratch", "tmp")]
    if not any(resolved.is_relative_to(root.resolve()) for root in allowed):
        raise PreparationError(f"mission_trace.output: generated output must be under reports/, scratch/, or tmp/: {resolved}")
    return resolved


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-dir", type=Path, default=os.environ.get("ENDFIELD_GAME_ROOT"), required=not bool(os.environ.get("ENDFIELD_GAME_ROOT")))
    parser.add_argument("--mission", default="all", help="Offline analysis label only; native observations are unfiltered (default: all).")
    parser.add_argument("--profile", choices=tuple(PROFILE_RECIPES), default="mission", help="Reviewed observer recipe; buff records Buff lifecycle and selected action entries.")
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "reports/runtime_capture/mission-trace-build.json")
    parser.add_argument("--report", type=Path, default=REPO_ROOT / "reports/runtime_capture/mission-trace-preflight.json")
    args = parser.parse_args(argv)
    output = checked_output(args.output)
    report_path = checked_output(args.report)
    if output == report_path:
        raise PreparationError("mission_trace.output: profile and report must be distinct")
    try:
        manifest = prepare(args.game_dir, args.mission, profile=args.profile)
    except (PreparationError, OSError, RuntimeError, KeyError, ValueError) as exc:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps({"schema": "endfield.mission-trace-preparation.v1", "status": "failed", "focusMission": args.mission, "detail": str(exc)}, indent=2), encoding="utf-8")
        print(f"[mission_trace_capture_prepare] failed: {exc}")
        return 1
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps({"schema": "endfield.mission-trace-preparation.v1", "status": "validated", "focusMission": args.mission,
                                      "profile": str(output), "hookCount": len(manifest["missionTraceHooks"]),
                                      "liveAttached": False, "evidenceBoundary": manifest["evidenceBoundary"]}, indent=2) + "\n", encoding="utf-8")
    print(f"[mission_trace_capture_prepare] validated: {len(manifest['missionTraceHooks'])} named bounded hooks; offline only; {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
