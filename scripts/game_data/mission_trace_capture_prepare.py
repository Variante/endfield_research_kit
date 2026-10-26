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
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.reference_layouts import single_reference_generic_field
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
GENERIC_RECIPE_SCHEMA = "endfield.mission-trace-capture-recipe.v5"
ASSIGNMENT_RECIPE_SCHEMA = "endfield.mission-trace-capture-recipe.v6"
LAYOUT_RECIPE_SCHEMA = "endfield.mission-trace-capture-recipe.v7"
STATE_RECIPE_SCHEMA = "endfield.mission-trace-capture-recipe.v8"
NUMERIC_RECIPE_SCHEMA = "endfield.mission-trace-capture-recipe.v9"
RESOLUTION_RECIPE_SCHEMA = "endfield.mission-trace-capture-recipe.v10"
BUNDLE_RECIPE_SCHEMA = "endfield.mission-trace-capture-recipe.v11"
RECEIVER_RECIPE_SCHEMA = "endfield.mission-trace-capture-recipe.v12"
IMAGE_RECIPE_SCHEMA = "endfield.mission-trace-capture-recipe.v13"
CALLER_RECIPE_SCHEMA = "endfield.mission-trace-capture-recipe.v14"
BUILD_SCHEMA = "endfieldCapture.missionTraceBuild.v1"
ABI_ID = "win64.transparent_entry_snapshot.v1"
NO_CHAIN = 4097
MAX_HOOKS = 96
MAX_BODY_BYTES = 1024 * 1024
_NAME = re.compile(r"[A-Za-z0-9_.$<>+`-]{1,127}\Z")
_WIDTH = {"bool": 8, "int": 32, "uint": 32, "long": 64, "ulong": 64, "float": 32, "double": 64}
_VALUE_KIND = {"bool": 5, "int": 2, "uint": 2, "long": 1, "ulong": 1, "string": 3, "float": 2, "double": 1}


class PreparationError(ValueError):
    """A selected method or field no longer matches the reviewed observer."""


def read_recipe(path: Path = RECIPE_PATH, *, _ancestors: tuple[Path, ...] = ()) -> dict[str, Any]:
    path = path.resolve()
    if path in _ancestors or len(_ancestors) >= 4:
        raise PreparationError('mission_trace.recipe: inheritance cycle or depth limit')
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schema") not in {RECIPE_SCHEMA, REFERENCE_RECIPE_SCHEMA, GENERIC_RECIPE_SCHEMA, ASSIGNMENT_RECIPE_SCHEMA, LAYOUT_RECIPE_SCHEMA, STATE_RECIPE_SCHEMA, NUMERIC_RECIPE_SCHEMA, RESOLUTION_RECIPE_SCHEMA, BUNDLE_RECIPE_SCHEMA, RECEIVER_RECIPE_SCHEMA, IMAGE_RECIPE_SCHEMA, CALLER_RECIPE_SCHEMA}:
        raise PreparationError("mission_trace.recipe: unsupported schema")
    base_name = value.get('inheritsRecipe')
    if base_name is not None:
        if value['schema'] not in {NUMERIC_RECIPE_SCHEMA, RESOLUTION_RECIPE_SCHEMA, BUNDLE_RECIPE_SCHEMA, RECEIVER_RECIPE_SCHEMA, IMAGE_RECIPE_SCHEMA, CALLER_RECIPE_SCHEMA} or not isinstance(base_name, str) or not re.fullmatch(r'[A-Za-z0-9_-]+\.json', base_name):
            raise PreparationError('mission_trace.recipe: v9 requires a bounded sibling base filename')
        base_path = path.resolve().parent / base_name
        if base_path.parent != CONTRACTS_DIR.resolve() or base_path == path.resolve():
            raise PreparationError('mission_trace.recipe: base must be another reviewed sibling contract')
        base = json.loads(base_path.read_bytes())
        if not isinstance(base, dict) or 'inheritsRecipe' in base and value['schema'] not in {RESOLUTION_RECIPE_SCHEMA,BUNDLE_RECIPE_SCHEMA, RECEIVER_RECIPE_SCHEMA, IMAGE_RECIPE_SCHEMA, CALLER_RECIPE_SCHEMA}:
            raise PreparationError('mission_trace.recipe: nested inheritance is unsupported')
        base = read_recipe(base_path, _ancestors=(*_ancestors, path))
        if not isinstance(value.get('hooks'), list):
            raise PreparationError('mission_trace.recipe: derived hooks must be an array')
        value = {**value, 'hooks': base['hooks'] + value['hooks'],
                 'coverageGaps': base.get('coverageGaps', []) + value.get('coverageGaps', [])}
    updates = value.pop('hookUpdates', [])
    if updates:
        if value['schema'] not in {RESOLUTION_RECIPE_SCHEMA,BUNDLE_RECIPE_SCHEMA, RECEIVER_RECIPE_SCHEMA, IMAGE_RECIPE_SCHEMA, CALLER_RECIPE_SCHEMA} or base_name is None or not isinstance(updates, list):
            raise PreparationError('mission_trace.recipe: hook updates require v10 inheritance')
        targets = {h['name']: h for h in value['hooks']}
        seen = set()
        for update in updates:
            if (not isinstance(update, dict) or not {'name'} <= set(update) <= {'name','appendFields','observationMode'}
                    or update['name'] not in targets or update['name'] in seen
                    or not isinstance(update.get('appendFields', []), list)
                    or update.get('observationMode', 'paired') != 'paired'):
                raise PreparationError('mission_trace.recipe: invalid, duplicate or unknown hook update')
            seen.add(update['name']);target=targets[update['name']]
            target['fields'] = target['fields'] + update.get('appendFields', [])
            if 'observationMode' in update:target['observationMode'] = 'paired'
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
        from .il2cpp.context import type_image_owners
        owners=type_image_owners(image.metadata.buf,len(image.metadata.types),source=str(image.metadata_path))
        self._type_definitions={};self._type_images={};self._declaring_image_proofs={}
        for td in image.metadata.types:
            name=image.metadata.type_full_name(td)
            self._type_definitions.setdefault(name,[]).append(td)
            self._type_images[td.index]=(owners[td.index],image.metadata.string(image.metadata.images[owners[td.index]].name_index))
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
        if td is None and name.startswith('Beyond.EventData`2<'):
            from .mission_trace_state_observers import event_layout
            return event_layout(self, name)['unboxedBytes']
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

    def paired_inline_value_argument(self, name: str) -> dict[str, Any]:
        """A concrete 1/2/4/8-byte struct occupies one ordinary Win64 GP slot.

        This forwards raw register bits; it does not dereference those bits or
        infer field values. Other aggregates retain their explicit ABI owners.
        ABI reference: https://learn.microsoft.com/en-us/cpp/build/x64-calling-convention
        """
        td = self.index.types.get(name)
        if td is None or td.generic_container_index >= 0 or not self.is_value_type(name):
            raise PreparationError(f"mission_trace.paired: requires concrete nongeneric value type: {name}")
        size = self.value_size(name)
        if size not in {1, 2, 4, 8}:
            raise PreparationError(f"mission_trace.paired: inline GP aggregate size unsupported: {name}:{size}")
        return {"type": name, "unboxedBytes": size, "mode": "inlineGpBits",
                "evidence": "selected Il2CppTypeDefinitionSizes; ordinary Win64 integer-sized aggregate argument ABI"}

    def paired_indirect_value_argument(self, hook, parameter):
        """Forward a selected concrete aggregate pointer, never its inline bits.

        Non-integer-sized Win64 aggregates use an indirect temporary; a declared
        byref also uses a pointer. Require an explicit bounded field witness.
        """
        name = parameter['type']
        td = self.index.types.get(name)
        if td is None or td.generic_container_index >= 0 or not self.is_value_type(name):
            raise PreparationError('mission_trace.paired: concrete indirect aggregate required')
        size = self.value_size(name)
        if size in {1, 2, 4, 8}:
            raise PreparationError('mission_trace.paired: integer-sized aggregate needs its own ABI')
        witness = {'mode': 'indirectValue', 'bytes': size}
        if not any(f.get('argument') == parameter['name'] and f.get('path')
                   and f.get('argumentRepresentation') == witness for f in hook['fields']):
            raise PreparationError('mission_trace.paired: explicit indirect aggregate field witness required')
        method, _, _ = self.resolve(hook)
        params = [p for p in self.image.metadata.parameters_for(method)
                  if self.image.metadata.string(p.name_index) == parameter['name']]
        if len(params) != 1:
            raise PreparationError('mission_trace.paired: indirect aggregate parameter ambiguous')
        index = params[0].type_index
        pointer = self.image.pe.u64_at_va(int(self.image.registration['types'], 16) + index * 8)
        raw = self.image.pe.bytes_at_va(pointer, 16) if pointer else b''
        if len(raw) != 16 or raw[10] != 0x11 or raw[11] & 0x7f not in {0, 0x20}:
            raise PreparationError('mission_trace.paired: selected aggregate type or decoration differs')
        return {'type': name, 'unboxedBytes': size, 'mode': 'indirectValue',
                'nativeTypeRecordHex': raw.hex(), 'nativeTypeIndex': index,
                'byref': bool(raw[11] & 0x20),
                'evidence': 'selected concrete value size/type; Win64 indirect aggregate or declared byref pointer'}

    def normal_value_receiver(self, hook):
        """Normal nongeneric value methods receive an unboxed this pointer."""
        name = hook['type']; td = self.index.types.get(name)
        if (hook['static'] or td is None or td.generic_container_index >= 0
                or not self.is_value_type(name) or self.is_enum(name)):
            raise PreparationError('mission_trace.receiver: concrete nongeneric value receiver required')
        method, _, pointer = self.resolve(hook)
        size = self.value_size(name)
        return {'argument':'this','type':name,'mode':'indirectValue','unboxedBytes':size,
                'typeDefinitionIndex':td.index,'methodIndex':method.index,
                'boxedHeaderBytes':16,'passing':'normalMethodUnboxedThisPointer',
                'evidence':'selected normal method pointer, concrete value owner and type-definition size; receiver points at unboxed data'}

    def opaque_byref_value_argument(self,hook,parameter):
        name=parameter['type'];td=self.index.types.get(name)
        if td is None or td.generic_container_index>=0 or not self.is_value_type(name) or self.is_enum(name):
            raise PreparationError('mission_trace.paired: opaque byref needs concrete value type')
        method,_,_=self.resolve(hook)
        params=[p for p in self.image.metadata.parameters_for(method) if self.image.metadata.string(p.name_index)==parameter['name']]
        if len(params)!=1:raise PreparationError('mission_trace.paired: opaque byref parameter ambiguous')
        index=params[0].type_index;ptr=self.image.pe.u64_at_va(int(self.image.registration['types'],16)+index*8)
        raw=self.image.pe.bytes_at_va(ptr,16) if ptr else b''
        if len(raw)!=16 or raw[10]!=17 or raw[11]&0x7f!=0x20 or int.from_bytes(raw[:8],'little')!=td.index:
            raise PreparationError('mission_trace.paired: declared undecorated value byref required')
        return {'argument':parameter['name'],'type':name,'mode':'opaqueValueByRef','bytes':8,
                'nativeTypeRecordHex':raw.hex(),'nativeTypeIndex':index,'typeDefinitionIndex':td.index,
                'byref':True,'pointeeRead':False,'evidence':'selected value-type byref is forwarded as a pointer; no pointee layout used'}

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
        """Read selected Int32 or fixed Int64 enum defaults without truncation."""
        _owner, underlying, _offset = self.field(f"{name}::value__")
        if underlying not in {"int", "uint", "long", "ulong"} or not self.is_enum(name):
            raise PreparationError(f"mission_trace.enum: unsupported enum backing: {name}:{underlying}")
        if underlying in {'long', 'ulong'}:
            from .il2cpp.enum64_defaults import native_enum64_members
            defaults = field_defaults(self.image.metadata)
            for field in self.image.metadata.fields_for(self.index.types[name]):
                member = self.image.metadata.string(field.name_index)
                if member != 'value__' and field.index not in defaults:
                    raise PreparationError(f'mission_trace.enum: missing member default: {name}.{member}')
            try:
                members = native_enum64_members(self.image.metadata, defaults,
                    self.image.pe, self.image.registration, name)
            except (ValueError, RuntimeError) as exc:
                raise PreparationError(f'mission_trace.enum: invalid Int64 defaults: {name}: {exc}') from exc
            return {'type': name, 'storageType': underlying, 'valueBits': 64,
                    'signed': underlying == 'long',
                    'members': [{**{k: v for k, v in row.items() if k != 'id'}, 'value': row['id']}
                                for row in members],
                    'source': 'selected metadata fixed-width default blob and native MetadataRegistration.types'}
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
        types=self._type_definitions.get(hook['type'],[])
        declaring=hook.get('declaringImage')
        if declaring is not None:
            types=[td for td in types if self._type_images[td.index][1]==declaring]
        if len(types)!=1:
            raise PreparationError(f"{hook['name']}: declaring type matched {len(types)} definitions; type={hook['type']}, image={declaring}; ambiguous names require declaringImage")
        td=types[0]
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
        if actual_return in {'float', 'double'}:
            self.scalar_return_abi(method.return_type, actual_return)
        elif actual_return not in {"void", "bool", "int", "uint", "long", "ulong"} and not self.is_enum(actual_return):
            proof = self.reference_return_abi(method.return_type)
            if proof is None:
                raise PreparationError(f"{hook['name']}: hidden return ABI unsupported for {actual_return}")
            if not hasattr(self, "_return_abi_proofs"):
                self._return_abi_proofs = {}
            self._return_abi_proofs[hook["name"]] = proof
        pointer = self.image.method_pointer_va(method)
        generic = hook.get("genericEntry")
        if generic is not None:
            if pointer or not isinstance(generic, dict) or set(generic) != {"classArguments", "methodArguments"}:
                raise PreparationError(f"{hook['name']}: generic entry requires a null normal slot and explicit instantiation arguments")
            if any(not isinstance(generic[key], list) or len(generic[key]) > 64 or
                   any(not isinstance(item, str) or not item for item in generic[key]) for key in generic):
                raise PreparationError(f"{hook['name']}: invalid generic instantiation arguments")
            try:
                if not hasattr(self, "_generic_entries"):
                    self._generic_entries = GenericEntries(self.image)
                proof = self._generic_entries.resolve(method.index, generic["classArguments"], generic["methodArguments"])
            except ValueError as exc:
                raise PreparationError(f"{hook['name']}: {exc}") from exc
            pointer = proof["pointer"]
            if not hasattr(self, "_generic_proofs"):
                self._generic_proofs = {}
            self._generic_proofs[hook["name"]] = proof
        # Folded native bodies can receive unrelated instance types. Reject them
        # rather than applying one owner's field layout to another caller.
        aliases = self.index.names_by_pointer.get(pointer) or []
        symbols = {f"{row.get('type')}.{row.get('method')}" for row in aliases}
        alias_indices = {row.get("methodIndex") for row in aliases}
        expected = f"{hook['type']}.{hook['method']}"
        if symbols != {expected} or alias_indices != {method.index}:
            raise PreparationError(f"{hook['name']}: shared or unregistered native body; expected={expected}, methodIndex={method.index}; aliasCount={len(symbols)}, aliases={sorted(symbols)[:8]!r}; methodIndexCount={len(alias_indices)}, methodIndices={sorted(str(index) for index in alias_indices)[:8]!r}")
        if declaring is not None:
            image_index,image_name=self._type_images[td.index]
            self._declaring_image_proofs[hook['name']]={'imageName':image_name,'imageIndex':image_index,
                'type':hook['type'],'typeDefinitionIndex':td.index,'methodIndex':method.index,
                'methodStart':td.method_start,'methodCount':td.method_count,
                'evidence':'selected metadata image type partition and exact method owner; no last-name dictionary selection'}
        return method, parameters, pointer

    def scalar_return_abi(self, type_index: int, name: str) -> dict[str, Any]:
        """Require an undecorated selected R4/R8; never infer an XMM input ABI."""
        table = int(self.image.registration['types'], 16)
        if not 0 <= type_index < self.image.registration['typesCount']:
            raise PreparationError('mission_trace.return: scalar type outside selected table')
        pointer = self.image.pe.u64_at_va(table + type_index * 8)
        raw = self.image.pe.bytes_at_va(pointer, 16) if pointer else b''
        if len(raw) != 16 or raw[10] != {'float': 0x0c, 'double': 0x0d}[name] or raw[11] & 0x7f:
            raise PreparationError('mission_trace.return: decorated or nonfloating scalar return')
        return {'type': name, 'bits': _WIDTH[name], 'register': 'xmm0',
                'representation': 'rawIeee754Bits', 'nativeTypeIndex': type_index,
                'nativeTypeRecordHex': raw.hex(),
                'evidence': 'selected undecorated IL2CPP R4/R8; Win64 scalar return ABI'}

    def scalar_byref_argument(self, hook: dict[str, Any], name: str) -> dict[str, Any]:
        method, _parameters, _pointer = self.resolve(hook)
        matches = [p for p in self.image.metadata.parameters_for(method)
                   if self.image.metadata.string(p.name_index) == name]
        if len(matches) != 1:
            raise PreparationError('mission_trace.argument: scalar byref parameter missing/duplicate')
        param = matches[0]; scalar = self.type_name(param.type_index)
        if not 0 <= param.type_index < self.image.registration['typesCount']:
            raise PreparationError('mission_trace.argument: scalar byref type outside selected table')
        pointer = self.image.pe.u64_at_va(int(self.image.registration['types'], 16) + param.type_index * 8)
        raw = self.image.pe.bytes_at_va(pointer, 16) if pointer else b''
        if scalar not in {'bool', 'float', 'double'} or len(raw) != 16 or raw[10] != {'bool': 2, 'float': 12, 'double': 13}[scalar] or raw[11] & 0x7f != 0x20:
            raise PreparationError('mission_trace.argument: selected undecorated Boolean or floating byref required')
        return {'mode': 'scalarByRef', 'type': scalar, 'bytes': _WIDTH[scalar] // 8,
                'nativeTypeIndex': param.type_index, 'byref': True,
                'nativeTypeRecordHex': raw.hex(),
                'evidence': 'selected Boolean/R4/R8 Il2CppType byref bit; bounded pointee read, GP pointer forwarded'}

    def enum_return_abi(self, type_index, name):
        if not self.is_enum(name) or self.field(name+'::value__')[1] != 'int':
            raise PreparationError('mission_trace.return: selected Int32 enum required')
        td=self.index.types[name]
        pointer=self.image.pe.u64_at_va(int(self.image.registration['types'],16)+type_index*8)
        raw=self.image.pe.bytes_at_va(pointer,16) if pointer else b''
        if len(raw)!=16 or raw[10]!=0x11 or raw[11]&0x7f or int.from_bytes(raw[:8],'little')!=td.index:
            raise PreparationError('mission_trace.return: enum type or decoration differs')
        return {'type':name,'storageType':'int','bits':32,'register':'eax',
                'nativeTypeRecordHex':raw.hex(),'nativeTypeIndex':type_index,'typeDefinitionIndex':td.index,
                'evidence':'selected undecorated enum value and Int32 value__ declaration; Win64 EAX return'}

    def reference_return_abi(self, type_index: int) -> dict[str, Any] | None:
        """A direct declared CLASS returns a pointer without a hidden buffer.

        This admits no generic, decorated, byref, array or value-type return.
        The observer does not read RAX or retain the returned reference.
        """
        registration = self.image.registration
        if not 0 <= type_index < registration["typesCount"]:
            raise PreparationError("mission_trace.return: type index outside selected table")
        table = int(registration["types"], 16)
        pointer = self.image.pe.u64_at_va(table + type_index * 8)
        if not pointer:
            raise PreparationError("mission_trace.return: missing selected native type")
        raw = self.image.pe.bytes_at_va(pointer, 16)
        if len(raw) != 16 or raw[10] != 0x12 or raw[11] != 0:
            return None
        definition_index = int.from_bytes(raw[:8], "little")
        name = self.type_name(type_index)
        td = self.index.types.get(name)
        if td is None or td.index != definition_index or self.is_value_type(name):
            return None
        return {"mode": "directReference", "returnType": name,
                "typeIndex": type_index, "typeDefinitionIndex": definition_index,
                "evidence": "selected undecorated IL2CPP_TYPE_CLASS; Win64 pointer return has no hidden return-buffer argument",
                "returnObserved": False}

    def scalar_register_argument(self, hook, name):
        method, _, _ = self.resolve(hook)
        arg, t = self.argument(hook, name)
        if (hook['static'] or arg != 2 or t != 'double' or hook['returnType'] != 'void'
                or len(hook['parameters']) != 2 or hook['parameters'][0]['type'] != 'string'):
            raise PreparationError('mission_trace.argument: only selected Double input at slot two of an instance void entry is supported')
        parameters=[p for p in self.image.metadata.parameters_for(method) if self.image.metadata.string(p.name_index)==name]
        if len(parameters)!=1:raise PreparationError('mission_trace.argument: scalar input parameter ambiguous')
        proof=self.scalar_return_abi(parameters[0].type_index,'double')
        return {**proof,'mode':'scalarRegister','argument':name,'slot':2,'register':'xmm2','bytes':8,
                'evidence':'selected undecorated R8 value input; Win64 positional XMM2 argument forwarded by a typed mixed caller'}

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
        scalar_byref = isinstance(representation, dict) and representation.get('mode') == 'scalarByRef'
        scalar_register = isinstance(representation, dict) and representation.get('mode') == 'scalarRegister'
        if scalar_register:
            if path or representation != {'mode':'scalarRegister','type':'double'}:
                raise PreparationError('mission_trace.argument: sole Double register parameter required')
            native_argument_proof = self.scalar_register_argument(hook,spec['argument'])
        if scalar_byref:
            if path or spec['argument'] == 'this' or representation != {'mode': 'scalarByRef', 'type': current_type}:
                raise PreparationError('mission_trace.argument: scalar byref requires a sole named parameter pointee')
            native_argument_proof = self.scalar_byref_argument(hook, spec['argument'])
        if representation is None and path and self.is_value_type(current_type):
            raise PreparationError(f"{hook['name']}.{spec['label']}: value-type argument path requires explicit argumentRepresentation")
        if representation is not None and not scalar_byref and not scalar_register:
            if not isinstance(representation, dict) or representation.get("mode") not in {"indirectValue", "inlineValue"}:
                raise PreparationError(f"{hook['name']}.{spec['label']}: unsupported argument representation")
            if spec['argument'] == 'this':
                native_argument_proof = self.normal_value_receiver(hook)
                if representation.get('mode') != 'indirectValue':
                    raise PreparationError('mission_trace.receiver: normal value receiver is an unboxed pointer')
            actual_size = self.value_size(current_type)
            if representation.get("bytes") != actual_size:
                raise PreparationError(f"{hook['name']}.{spec['label']}: value ABI size drift; expected {representation.get('bytes')}, actual {actual_size}")
            if representation["mode"] == "indirectValue":
                if current_type.startswith('Beyond.EventData`2<'):
                    from .mission_trace_state_observers import event_argument_proof
                    native_argument_proof = event_argument_proof(self, hook, arg)
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
            layout_proof = None
            if 'paramWitness' in step:
                from .mission_trace_state_observers import param_field
                try:
                    owner, actual_type, field_offset, layout_proof = param_field(self, step['field'], step['paramWitness'], current_type)
                except ValueError as exc:
                    raise PreparationError(f"{hook['name']}.{spec['label']}: {exc}") from exc
            elif current_type.startswith('Beyond.EventData`2<'):
                from .mission_trace_state_observers import event_layout
                layout_proof = event_layout(self, current_type)
                owner, separator, name = step['field'].partition('::')
                cell = layout_proof['fields'].get(name)
                if not separator or owner != current_type or cell is None or not inline:
                    raise PreparationError('state EventData witness: field or passing representation differs')
                actual_type, field_offset = cell['type'], cell['offset'] + 16
            elif step.get('layoutWitness') == 'Beyond.Blackboard+BlackboardDouble':
                from .mission_trace_buff_observers import double_field
                if inline:
                    raise PreparationError('Buff scalar witness: reference receiver required')
                try:
                    owner, actual_type, field_offset, layout_proof = double_field(
                        self, step['field'], step['layoutWitness'], current_type)
                except ValueError as exc:
                    raise PreparationError(f"{hook['name']}.{spec['label']}: {exc}") from exc
            elif step.get('layoutWitness') == 'Beyond.Gameplay.Core.AbilitySystem':
                from .mission_trace_buff_observers import client_hp_field
                if not inline:
                    raise PreparationError('HP cell witness: inline stored value required')
                try:
                    owner, actual_type, field_offset, layout_proof = client_hp_field(
                        self, step['field'], step['layoutWitness'], current_type)
                except ValueError as exc:
                    raise PreparationError(f"{hook['name']}.{spec['label']}: {exc}") from exc
            elif "layoutWitness" in step:
                owner, separator, name = step["field"].partition("::")
                if not separator or step["layoutWitness"] != current_type or inline:
                    raise PreparationError(f"{hook['name']}.{spec['label']}: layout witness must be the current named reference receiver")
                try:
                    layout_proof = single_reference_generic_field(self, owner=owner, field=name, witness=current_type)
                except ValueError as exc:
                    raise PreparationError(f"{hook['name']}.{spec['label']}: {exc}") from exc
                actual_type, field_offset = layout_proof["fieldType"], layout_proof["fieldOffset"]
            else:
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
            if position == 0 and spec['argument'] == 'this' and native_argument_proof is not None:
                resolved_path[-1]['boxedOffset'] = field_offset + 16
                resolved_path[-1]['storageBytes'] = field_bytes
            if layout_proof is not None:
                resolved_path[-1]["layoutProof"] = layout_proof
            elif owner.endswith("<string>") and owner not in self.index.types:
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
        param_identity = False
        if reference_identity and spec.get('paramIdentityWitness'):
            from .mission_trace_state_observers import param_layout
            layout = param_layout(self, spec['paramIdentityWitness'])
            if current_type != layout['instanceField'][1] or not path:
                raise PreparationError('state Param identity: receiver path differs')
            param_identity = True
        if reference_identity and (representation is not None or (current_type not in self.index.types and not param_identity)
                                   or self.is_value_type(current_type)):
            raise PreparationError(f"{hook['name']}.{spec['label']}: reference identity requires a named managed reference type, not a value layout")
        enum = self.is_enum(current_type)
        underlying = "ulong" if reference_identity else current_type
        if enum:
            _owner, underlying, _offset = self.field(f"{current_type}::value__")
            if underlying not in {"int", "uint", "long", "ulong"}:
                raise PreparationError(f"{hook['name']}.{spec['label']}: unsupported enum storage: {current_type}:{underlying}")
        width = 64 if reference_identity else _WIDTH.get(underlying, 32 if enum else None)
        if scalar_register:
            kind = 4
        elif scalar_byref:
            kind = _VALUE_KIND[current_type]
        elif not path and current_type != "string":
            if current_type in {"float", "double"}:
                raise PreparationError(f"{hook['name']}.{spec['label']}: floating register argument is unsupported by the GP/stack observer ABI")
            if width is None:
                raise PreparationError(f"{hook['name']}.{spec['label']}: unsupported argument type {current_type}")
            kind = 4
        else:
            kind = 1 if reference_identity else _VALUE_KIND.get(underlying, 2 if enum else None)
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
                "evidence": "selected Double XMM2 input forwarded through typed caller" if scalar_register else
                    "selected scalar byref parameter and bounded pointee read" if scalar_byref else
                    "selected generic layout and separately checked native argument proof" if native_argument_proof else "selected Il2CppTypeDefinitionSizes.instance_size minus object header; Win64 aggregate ABI"}
            if native_argument_proof:
                result["argumentRepresentation"]["nativeArgumentProof"] = native_argument_proof
            if scalar_byref:
                result['observation'] = 'argument-pointee'
            if scalar_register:
                result['observation'] = 'argument-register-bits'
        return result


def owned_entry_extent(index, pointer: int) -> int | None:
    """Include contiguous fragments only when unwind chaining proves ownership.

    A short .pdata prologue is not the entire caller window. Never bridge a
    gap or absorb a merely adjacent anonymous function to find a desired call.
    Noncontiguous cold fragments remain outside this single-window descriptor.
    """
    end = index.extents.get(pointer)
    if end is None:
        return None
    fragments = dict(getattr(index, 'chained_fragments', {}).get(pointer, ()))
    seen = set()
    while end in fragments:
        size = fragments[end]
        if end in seen or type(size) is not int or size <= 0:
            raise PreparationError('mission_trace.body: invalid owned fragment extent')
        seen.add(end)
        end += size
    return end


def compile_hooks(selected: SelectedMethods, recipe: dict[str, Any]) -> list[dict[str, Any]]:
    if not 1 <= len(recipe["hooks"]) <= MAX_HOOKS:
        raise PreparationError(f"mission_trace.recipe: expected 1..{MAX_HOOKS} hooks")
    hooks = []
    seen_rvas: set[int] = set()
    for spec in recipe["hooks"]:
        if spec.get("genericEntry") is not None and recipe.get("schema") not in {GENERIC_RECIPE_SCHEMA, ASSIGNMENT_RECIPE_SCHEMA, LAYOUT_RECIPE_SCHEMA, STATE_RECIPE_SCHEMA, NUMERIC_RECIPE_SCHEMA, RESOLUTION_RECIPE_SCHEMA, BUNDLE_RECIPE_SCHEMA, RECEIVER_RECIPE_SCHEMA, IMAGE_RECIPE_SCHEMA, CALLER_RECIPE_SCHEMA}:
            raise PreparationError("mission_trace.recipe: generic entries require recipe v5")
        if any(field.get("valueRepresentation") is not None for field in spec["fields"]) and recipe.get("schema") not in {REFERENCE_RECIPE_SCHEMA, GENERIC_RECIPE_SCHEMA, ASSIGNMENT_RECIPE_SCHEMA, LAYOUT_RECIPE_SCHEMA, STATE_RECIPE_SCHEMA, NUMERIC_RECIPE_SCHEMA, RESOLUTION_RECIPE_SCHEMA, BUNDLE_RECIPE_SCHEMA, RECEIVER_RECIPE_SCHEMA, IMAGE_RECIPE_SCHEMA, CALLER_RECIPE_SCHEMA}:
            raise PreparationError("mission_trace.recipe: reference identities require recipe v4")
        if spec.get("anonymousEntry") is not None and recipe.get("schema") not in {ASSIGNMENT_RECIPE_SCHEMA, LAYOUT_RECIPE_SCHEMA, STATE_RECIPE_SCHEMA, NUMERIC_RECIPE_SCHEMA, RESOLUTION_RECIPE_SCHEMA, BUNDLE_RECIPE_SCHEMA, RECEIVER_RECIPE_SCHEMA, IMAGE_RECIPE_SCHEMA, CALLER_RECIPE_SCHEMA}:
            raise PreparationError("mission_trace.recipe: anonymous assignment entries require recipe v6")
        if any("layoutWitness" in step for field in spec["fields"] for step in field.get("path", [])) and recipe.get("schema") not in {LAYOUT_RECIPE_SCHEMA, STATE_RECIPE_SCHEMA, NUMERIC_RECIPE_SCHEMA, RESOLUTION_RECIPE_SCHEMA, BUNDLE_RECIPE_SCHEMA, RECEIVER_RECIPE_SCHEMA, IMAGE_RECIPE_SCHEMA, CALLER_RECIPE_SCHEMA}:
            raise PreparationError("mission_trace.recipe: closed reference layout witnesses require recipe v7")
        if (spec.get('observationMode') is not None or any(f.get('paramIdentityWitness') or
                any('paramWitness' in s for s in f.get('path', [])) or
                f.get('argumentRepresentation', {}).get('nativeProof') == 'stateEventCallback'
                for f in spec['fields'])) and recipe.get('schema') not in {STATE_RECIPE_SCHEMA, NUMERIC_RECIPE_SCHEMA, RESOLUTION_RECIPE_SCHEMA, BUNDLE_RECIPE_SCHEMA, RECEIVER_RECIPE_SCHEMA, IMAGE_RECIPE_SCHEMA, CALLER_RECIPE_SCHEMA}:
            raise PreparationError('mission_trace.recipe: paired state witnesses require recipe v8')
        if spec.get('declaringImage') is not None:
            scalar_types={'bool','int','uint','long','ulong'}
            if (recipe.get('schema') not in {IMAGE_RECIPE_SCHEMA, CALLER_RECIPE_SCHEMA} or not isinstance(spec['declaringImage'],str)
                    or not re.fullmatch(r'[A-Za-z0-9_.-]{1,128}\.dll',spec['declaringImage'])
                    or not spec['static'] or spec['returnType'] not in scalar_types|{'void','float','double'}
                    or any(p['type'] not in scalar_types for p in spec['parameters'])
                    or any(f.get('path') or f['argument']=='this' for f in spec['fields'])):
                raise PreparationError('mission_trace.image: v13 image-qualified static scalar observer required')
        method, _parameters, pointer = selected.resolve(spec)
        abi = ABI_ID
        value_receiver = not spec['static'] and selected.is_value_type(spec['type'])
        receiver_reads = [f for f in spec['fields'] if f['argument']=='this' and f.get('path')]
        if value_receiver and receiver_reads:
            if recipe.get('schema') not in {RECEIVER_RECIPE_SCHEMA,IMAGE_RECIPE_SCHEMA, CALLER_RECIPE_SCHEMA} or spec.get('observationMode') != 'paired':
                raise PreparationError('mission_trace.receiver: value receiver field reads require recipe v12 paired ABI')
            receiver_proof = selected.normal_value_receiver(spec)
            if any(f.get('argumentRepresentation') != {'mode':'indirectValue','bytes':receiver_proof['unboxedBytes']}
                   for f in receiver_reads):
                raise PreparationError('mission_trace.receiver: every value receiver path requires explicit unboxed size')
        if spec.get('observationMode') is not None:
            enum_return=selected.is_enum(spec['returnType'])
            if (spec['observationMode'] != 'paired' or spec.get('genericEntry') or spec.get('anonymousEntry')
                    or spec['returnType'] not in {'void','bool','float','double'} and not (enum_return and recipe.get('schema') in {BUNDLE_RECIPE_SCHEMA,RECEIVER_RECIPE_SCHEMA, IMAGE_RECIPE_SCHEMA, CALLER_RECIPE_SCHEMA})):
                raise PreparationError(f"{spec['name']}: paired observer requires unique nongeneric void/bool/float/double entry")
            if spec['returnType'] in {'float', 'double'} and recipe.get('schema') not in {NUMERIC_RECIPE_SCHEMA, RESOLUTION_RECIPE_SCHEMA, BUNDLE_RECIPE_SCHEMA, RECEIVER_RECIPE_SCHEMA, IMAGE_RECIPE_SCHEMA, CALLER_RECIPE_SCHEMA}:
                raise PreparationError(f"{spec['name']}: floating returns require recipe v9")
            count = len(spec['parameters']) + int(not spec['static']) + 1  # trailing IL2CPP MethodInfo
            if not 1 <= count <= 5:
                raise PreparationError(f"{spec['name']}: paired observer supports one to five GP ABI slots")
            if count == 5 and recipe.get('schema') not in {RESOLUTION_RECIPE_SCHEMA,BUNDLE_RECIPE_SCHEMA, RECEIVER_RECIPE_SCHEMA, IMAGE_RECIPE_SCHEMA, CALLER_RECIPE_SCHEMA}:
                raise PreparationError('mission_trace.recipe: fifth GP slot requires recipe v10')
            aggregate_arguments = []
            scalar_inputs = []
            opaque_arguments=[]
            opaque=spec.get('opaqueByRefArguments',[])
            if not isinstance(opaque,list) or len(set(opaque))!=len(opaque) or any(n not in {p['name'] for p in spec['parameters']} for n in opaque):
                raise PreparationError('mission_trace.recipe: invalid opaque byref arguments')
            for p in spec['parameters']:
                t = p['type']
                if p['name'] in opaque:
                    if recipe.get('schema') not in {BUNDLE_RECIPE_SCHEMA,RECEIVER_RECIPE_SCHEMA, IMAGE_RECIPE_SCHEMA, CALLER_RECIPE_SCHEMA} or any(f['argument']==p['name'] for f in spec['fields']):
                        raise PreparationError('mission_trace.recipe: opaque byref requires v11 and no reads')
                    opaque_arguments.append(selected.opaque_byref_value_argument(spec,p));continue
                if t in {'float', 'double'}:
                    register_fields = [f for f in spec['fields'] if f.get('argument') == p['name']
                                       and f.get('argumentRepresentation') == {'mode':'scalarRegister','type':'double'}]
                    if register_fields:
                        if recipe.get('schema') not in {RESOLUTION_RECIPE_SCHEMA,BUNDLE_RECIPE_SCHEMA, RECEIVER_RECIPE_SCHEMA, IMAGE_RECIPE_SCHEMA, CALLER_RECIPE_SCHEMA} or count != 4 or t != 'double':
                            raise PreparationError('mission_trace.recipe: selected mixed Double input requires v10/four slots')
                        scalar_inputs.append(selected.scalar_register_argument(spec,p['name']))
                        continue
                    witnesses = [f for f in spec['fields'] if f.get('argument') == p['name']
                                 and f.get('argumentRepresentation') == {'mode': 'scalarByRef', 'type': t}]
                    if recipe.get('schema') not in {NUMERIC_RECIPE_SCHEMA, RESOLUTION_RECIPE_SCHEMA, BUNDLE_RECIPE_SCHEMA, RECEIVER_RECIPE_SCHEMA, IMAGE_RECIPE_SCHEMA, CALLER_RECIPE_SCHEMA} or not witnesses:
                        raise PreparationError(f"{spec['name']}: paired observer refuses XMM arguments without a selected scalar byref witness")
                    selected.scalar_byref_argument(spec, p['name'])
                    continue
                if 'VAR[' in t:
                    raise PreparationError(f"{spec['name']}: paired observer refuses unresolved or XMM arguments")
                if selected.is_value_type(t) and not selected.is_enum(t):
                    if t in _WIDTH:
                        continue
                    if t.startswith('Beyond.EventData`2<'):
                        from .mission_trace_state_observers import event_argument_proof, event_layout
                        event_layout(selected, t)
                        event_argument_proof(selected, spec, selected.argument(spec, p['name'])[0])
                    else:
                        indirect = any(f.get('argument') == p['name'] and
                            f.get('argumentRepresentation', {}).get('mode') == 'indirectValue'
                            for f in spec['fields'])
                        if indirect and recipe.get('schema') not in {RESOLUTION_RECIPE_SCHEMA,BUNDLE_RECIPE_SCHEMA, RECEIVER_RECIPE_SCHEMA, IMAGE_RECIPE_SCHEMA, CALLER_RECIPE_SCHEMA}:
                            raise PreparationError('mission_trace.recipe: paired indirect aggregate requires v10')
                        aggregate_arguments.append({"argument": p['name'],
                            **(selected.paired_indirect_value_argument(spec, p) if indirect else
                               selected.paired_inline_value_argument(t))})
            storage_return="int" if enum_return else spec['returnType']
            abi = f"win64.paired_gp_{storage_return}_{count}.v1"
            if scalar_inputs:
                if len(scalar_inputs)!=1:raise PreparationError('mission_trace.recipe: sole mixed Double input required')
                abi='win64.paired_double_slot2_void_4.v1'
        if spec.get('captureScope') is not None:
            if (recipe.get('schema') not in {BUNDLE_RECIPE_SCHEMA,RECEIVER_RECIPE_SCHEMA, IMAGE_RECIPE_SCHEMA, CALLER_RECIPE_SCHEMA} or spec['captureScope'] != 'paired-ancestor'
                    or not abi.startswith('win64.paired_gp_')):
                raise PreparationError('mission_trace.recipe: paired-ancestor scope requires v11 GP paired observer')
            abi=abi.replace('win64.paired_', 'win64.scoped_paired_',1)
        entry = None
        field_abi = spec
        if spec.get("anonymousEntry") is not None:
            from scripts.game_data.il2cpp.assignment_entry import resolve_assignment_entry
            try:
                entry = resolve_assignment_entry(selected.index, spec, caller_index=method.index, caller_pointer=pointer)
            except (ValueError, RuntimeError) as exc:
                raise PreparationError(f"{spec['name']}: {exc}") from exc
            pointer, field_abi = entry["pointer"], entry["abi"]
        end = owned_entry_extent(selected.index, pointer)
        if end is None or not 16 <= end - pointer <= MAX_BODY_BYTES:
            raise PreparationError(f"{spec['name']}: missing bounded .pdata entry or body outside 16..{MAX_BODY_BYTES} bytes")
        body_size = end - pointer
        window_size = min(body_size, 64)
        body = selected.image.pe.bytes_at_va(pointer, body_size)
        fields = [selected.compile_field(field_abi, field) for field in spec["fields"]]
        labels = [f["label"] for f in fields]
        limit = 24 if recipe.get('schema') in {STATE_RECIPE_SCHEMA, NUMERIC_RECIPE_SCHEMA, RESOLUTION_RECIPE_SCHEMA, BUNDLE_RECIPE_SCHEMA, RECEIVER_RECIPE_SCHEMA, IMAGE_RECIPE_SCHEMA, CALLER_RECIPE_SCHEMA} else 8
        if len(fields) > limit or len(set(labels)) != len(labels):
            raise PreparationError(f"{spec['name']}: more than {limit} fields or duplicate field labels")
        rva = pointer - selected.image.pe.image_base
        if rva in seen_rvas:
            raise PreparationError(f"{spec['name']}: duplicate native entry")
        seen_rvas.add(rva)
        hooks.append({"name": spec["name"], "module": "GameAssembly.dll", "rva": f"0x{rva:x}", "abiId": abi,
                      "expectedBytes": body[:window_size].hex(),
                      "readProgram": "".join(f"{f['arg']},{f['kind']},{f['offset']},{f['chain0']},{f['chain1']};" for f in fields),
                      "fields": fields, "symbol": f"{spec['type']}.{spec['method']}",
                      "methodIndex": method.index, "returnType": spec["returnType"], "parameters": spec["parameters"],
                      "bodyBytes": body_size, "bodySha256": hashlib.sha256(body).hexdigest(),
                      "receiverIdentity": None if spec["static"] else {"arg": 0, "type": spec["type"], "source": "raw entry argument"},
                      "semanticRole": spec.get("semanticRole", "named entry observation"),
                      "evidenceBoundary": spec["evidenceBoundary"]})
        if spec.get('declaringImage'):
            hooks[-1]['declaringImage']=spec['declaringImage']
            hooks[-1]['declaringImageProof']=selected._declaring_image_proofs[spec['name']]
        if spec.get('captureScope'):hooks[-1]['captureScope']=spec['captureScope']
        if abi != ABI_ID:
            hooks[-1]['observationMode'] = 'paired'
            hooks[-1]['pairedAbiProof'] = {'argumentSlots': count, 'includesMethodInfo': True,
                'returnType': spec['returnType'], 'phaseFieldPolicy': 'same typed paths at entry and return',
                'boundary': 'synchronous selected GP caller only; exception or stop during invocation rejects completeness'}
            if scalar_inputs:hooks[-1]['pairedAbiProof']['scalarInputs']=scalar_inputs
            if opaque_arguments:hooks[-1]['pairedAbiProof']['opaqueByRefArguments']=opaque_arguments
            if enum_return:
                hooks[-1]['pairedAbiProof']['returnStorage']='int'
                hooks[-1]['pairedAbiProof']['enumReturn']=selected.enum_return_abi(method.return_type,spec['returnType'])
            if spec['returnType'] in {'float', 'double'}:
                hooks[-1]['pairedAbiProof']['scalarReturn'] = selected.scalar_return_abi(method.return_type, spec['returnType'])
            if value_receiver:
                hooks[-1]['pairedAbiProof']['receiverPassing'] = 'normalMethodUnboxedThisPointer'
                if receiver_reads:hooks[-1]['pairedAbiProof']['unboxedReceiver']=receiver_proof
                hooks[-1]['receiverIdentity']['source'] = 'raw normal method unboxed value address; not managed-object identity'
            if aggregate_arguments:
                for mode, key in [('inlineGpBits','inlineAggregateArguments'), ('indirectValue','indirectAggregateArguments')]:
                    selected_arguments = [a for a in aggregate_arguments if a['mode'] == mode]
                    if selected_arguments:hooks[-1]['pairedAbiProof'][key] = selected_arguments
        if spec.get("genericEntry") is not None:
            hooks[-1]["genericEntryProof"] = selected._generic_proofs[spec["name"]]
        if entry is not None:
            hooks[-1].update(anonymousEntryProof=entry["proof"],
                sourceCaller={"symbol": hooks[-1]["symbol"], "methodIndex": method.index,
                              "returnType": spec["returnType"], "parameters": spec["parameters"]},
                symbol=f"anonymous assignment via {hooks[-1]['symbol']}", methodIndex=None,
                returnType="unobserved", parameters=field_abi["parameters"],
                receiverIdentity={"arg": 1, "type": field_abi["parameters"][1]["type"],
                                  "source": "proved helper entry action register; not a returned action"})
        if entry is None and spec["name"] in getattr(selected, "_return_abi_proofs", {}):
            hooks[-1]["returnAbiProof"] = selected._return_abi_proofs[spec["name"]]
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
    enum_types = sorted({field["type"] for hook in hooks for field in hook["fields"] if selected.is_enum(field["type"])} | {hook["returnType"] for hook in hooks if selected.is_enum(hook["returnType"])})
    enum_definitions = {name: selected.enum_members(name) for name in enum_types}
    compile_caller_scopes(selected, hooks, recipe)
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
            "observerPolicy": {'pairedDepthLimit': 64, 'fieldCapacity': 24, 'callbacksCallGameGetters': False},
            "evidenceBoundary": recipe["evidenceBoundary"]}


def compile_caller_scopes(selected, hooks, recipe):
    """Bind a bounded scope to direct E8 calls in already proved named bodies."""
    by_name={h['name']:h for h in hooks}
    for spec in recipe['hooks']:
        callers=spec.get('captureCallerHooks')
        if callers is None:continue
        if (recipe['schema']!=CALLER_RECIPE_SCHEMA or spec.get('captureScope')!='paired-ancestor'
                or not isinstance(callers,list) or not 1<=len(callers)<=16
                or any(not isinstance(n,str) for n in callers) or len(set(callers))!=len(callers)):
            raise PreparationError('mission_trace.caller_scope: v14 requires bounded unique scoped caller hooks')
        target=by_name[spec['name']];target_rva=int(target['rva'],16);proofs=[]
        for name in callers:
            caller=by_name.get(name)
            if not caller or caller is target or caller.get('observationMode')!='paired':
                raise PreparationError('mission_trace.caller_scope: caller must be another paired hook: '+name)
            pointer=selected.image.pe.image_base+int(caller['rva'],16)
            raw=selected.image.pe.bytes_at_va(pointer,caller['bodyBytes'])
            if hashlib.sha256(raw).hexdigest()!=caller['bodySha256']:
                raise PreparationError('mission_trace.caller_scope: caller body changed: '+name)
            for row in selected.index._decode(pointer,len(raw)):
                encoded=bytes.fromhex(row['bytes']);va=int(row['va'],16)
                if (len(encoded)==5 and encoded[0]==0xe8 and
                        va+5+int.from_bytes(encoded[1:],'little',signed=True)==selected.image.pe.image_base+target_rva):
                    proofs.append({'callerHook':name,'callerMethodIndex':caller['methodIndex'],
                        'callerBodySha256':caller['bodySha256'],'callRva':va-selected.image.pe.image_base,
                        'returnRva':va+5-selected.image.pe.image_base,'callBytes':encoded.hex(),'targetRva':target_rva})
        proofs.sort(key=lambda r:r['returnRva'])
        returns=[r['returnRva'] for r in proofs]
        if not 1<=len(proofs)<=32 or len(set(returns))!=len(returns):
            raise PreparationError('mission_trace.caller_scope: no bounded unique direct calls: '+spec['name'])
        target['captureCallerReturnRvas']=','.join(f'{r:x}' for r in returns)
        target['captureCallerProofs']=proofs


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
    parser.add_argument("--recipe", type=Path, help="Optional reviewed recipe under scripts/game_data/contracts/; profile still selects the recording scope.")
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "reports/runtime_capture/mission-trace-build.json")
    parser.add_argument("--report", type=Path, default=REPO_ROOT / "reports/runtime_capture/mission-trace-preflight.json")
    args = parser.parse_args(argv)
    output = checked_output(args.output)
    report_path = checked_output(args.report)
    if output == report_path:
        raise PreparationError("mission_trace.output: profile and report must be distinct")
    try:
        recipe = None
        if args.recipe is not None:
            recipe_path = args.recipe.resolve()
            if not recipe_path.is_relative_to(CONTRACTS_DIR.resolve()) or recipe_path.suffix != ".json":
                raise PreparationError("mission_trace.recipe: override must be a JSON contract under scripts/game_data/contracts/")
            recipe = read_recipe(recipe_path)
        manifest = prepare(args.game_dir, args.mission, recipe=recipe, profile=args.profile)
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
    paired = sum(hook.get('observationMode') == 'paired' for hook in manifest['missionTraceHooks'])
    print(f"[mission_trace_capture_prepare] validated: {len(manifest['missionTraceHooks'])} bounded observers ({paired} paired); offline only; {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
