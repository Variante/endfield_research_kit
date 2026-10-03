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
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.il2cpp.native_image import NativeImage
from scripts.game_data.il2cpp.protocol import (
    field_defaults, read_compressed_int32, read_compressed_uint32,
    runtime_type_field_offsets, runtime_type_name,
)
from scripts.repo_paths import REPO_ROOT

RECIPE_PATH = CONTRACTS_DIR / "mission_trace_capture.json"
RECIPE_SCHEMA = "endfield.mission-trace-capture-recipe.v2"
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
    if not isinstance(value, dict) or value.get("schema") != RECIPE_SCHEMA:
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
        return self.type_name(td.parent_index) if td is not None and td.parent_index >= 0 else ""

    def is_enum(self, name: str) -> bool:
        return self.parent(name) == "System.Enum"

    def is_value_type(self, name: str) -> bool:
        return self.parent(name) in {"System.ValueType", "System.Enum"}

    def value_size(self, name: str) -> int:
        """Derive unboxed size from this build's Il2CppTypeDefinitionSizes."""
        td = self.index.types.get(name)
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
                raise PreparationError(f"mission_trace.field: missing owner {owner}")
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
                    raise PreparationError(f"{hook['name']}.{spec['label']}: indirect value requires Win64 indirect aggregate size")
            elif actual_size != 8 or len(path) != 1 or spec["type"] != "string":
                raise PreparationError(f"{hook['name']}.{spec['label']}: inline value supports only an eight-byte string wrapper")
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
        enum = self.is_enum(current_type)
        underlying = current_type
        if enum:
            _owner, underlying, _offset = self.field(f"{current_type}::value__")
            if underlying not in {"int", "uint"}:
                raise PreparationError(f"{hook['name']}.{spec['label']}: enum storage drift for {current_type}; expected int/uint, actual {underlying}")
        width = _WIDTH.get(current_type, 32 if enum else None)
        if not path and current_type != "string":
            if current_type in {"float", "double"}:
                raise PreparationError(f"{hook['name']}.{spec['label']}: floating register argument is unsupported by the GP/stack observer ABI")
            if width is None:
                raise PreparationError(f"{hook['name']}.{spec['label']}: unsupported argument type {current_type}")
            kind = 4
        else:
            kind = _VALUE_KIND.get(current_type, 2 if enum else None)
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
        if representation is not None:
            result["argumentRepresentation"] = {**representation,
                "evidence": "selected Il2CppTypeDefinitionSizes.instance_size minus object header; Win64 aggregate ABI"}
        return result


def compile_hooks(selected: SelectedMethods, recipe: dict[str, Any]) -> list[dict[str, Any]]:
    if not 1 <= len(recipe["hooks"]) <= MAX_HOOKS:
        raise PreparationError(f"mission_trace.recipe: expected 1..{MAX_HOOKS} hooks")
    hooks = []
    seen_rvas: set[int] = set()
    for spec in recipe["hooks"]:
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


def prepare(game_dir: Path, mission: str = "all", *, recipe: dict[str, Any] | None = None) -> dict[str, Any]:
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
    recipe = read_recipe() if recipe is None else recipe
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
            "focusMission": mission, "recordingScope": "all-named-context-unfiltered",
            "missionSelection": {"mode": "all-missions" if mission == "all" else "named-analysis-focus", "nativeFilter": False},
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
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "reports/runtime_capture/mission-trace-build.json")
    parser.add_argument("--report", type=Path, default=REPO_ROOT / "reports/runtime_capture/mission-trace-preflight.json")
    args = parser.parse_args(argv)
    output = checked_output(args.output)
    report_path = checked_output(args.report)
    if output == report_path:
        raise PreparationError("mission_trace.output: profile and report must be distinct")
    try:
        manifest = prepare(args.game_dir, args.mission)
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
