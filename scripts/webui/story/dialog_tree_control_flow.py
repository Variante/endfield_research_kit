#!/usr/bin/env python3
"""Recover reusable native contracts for serialized DialogTree controls.

The recovery is family-driven rather than content-driven.  A family spec names
managed schema members (node type, selector enum, serialized selector path,
and static port-map field); the implementation derives method pointers, enum
values, named port order, and the external-index continuation path from the
installed IL2CPP metadata and GameAssembly.  Mission ids, Story keys, object
ids, OCR, and manual overrides are never inputs.

The current consumer uses this for ``DialogTreeOpenUINode``.  The decoder is
kept generic so another node family with a static
``Dictionary<enum,List<string>>`` port contract can use the same validation and
corpus projection.
"""

from __future__ import annotations

import hashlib
import json
import re
import struct
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


from scripts.game_data.il2cpp.body_claims import BodyIndex, ClaimError
from scripts.game_data.il2cpp.context import usage_method_spec, unresolved_usage_index
from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.game_data.il2cpp import static_dictionary
from scripts.game_data.il2cpp.protocol import read_compressed_int32
from scripts.repo_paths import REPO_ROOT

ROOT = REPO_ROOT
from scripts.common import (
    resolve_installed_game_data_root,
    sha256_file_upper as sha256_file,
)

from scripts.game_data.ifix_patch_native import (
    DEFAULT_CONTRACT as DEFAULT_IFIX_CONTRACT,
    load_ifix_patch_contract,
    project_current_ifix_evidence,
)

DEFAULT_GAME_ROOT = resolve_installed_game_data_root()
DEFAULT_GAME_ASSEMBLY = DEFAULT_GAME_ROOT.parent / "GameAssembly.dll"
DEFAULT_METADATA = DEFAULT_GAME_ROOT / "il2cpp_data" / "Metadata" / "global-metadata.dat"
DEFAULT_ANIMESTUDIO_CLI = (
    ROOT / "tools" / "AnimeStudio" / "AnimeStudio.CLI" / "bin" / "Release"
    / "net9.0-windows" / "AnimeStudio.CLI.exe"
)

RUNTIME_PRIMITIVES = {
    0x01: "void", 0x02: "bool", 0x03: "char", 0x04: "sbyte",
    0x05: "byte", 0x06: "short", 0x07: "ushort", 0x08: "int",
    0x09: "uint", 0x0A: "long", 0x0B: "ulong", 0x0C: "float",
    0x0D: "double", 0x0E: "System.String", 0x18: "nint",
    0x19: "nuint", 0x1C: "object",
}


class ContractError(RuntimeError):
    """Raised when original inputs cannot satisfy a bounded native contract."""


@dataclass(frozen=True)
class ExternalResultRouterSpec:
    """Schema for a shipped-script result router consumed by a native family.

    The spec names protocol symbols and source locations, never content ids or
    mission instances.  The same parser can therefore audit a different
    phase/result protocol without adding per-panel recovery rules.
    """

    source_root_marker: str
    router_path: str
    defaults_path: str
    open_message: str
    override_message: str
    defaults_table: str
    native_next_expression: str
    native_default_expression: str = ""


@dataclass(frozen=True)
class StaticPortFamilySpec:
    family: str
    node_type: str
    selector_enum_type: str
    serialized_selector_path: tuple[str, ...]
    static_port_map_field: str
    node_action_method: str
    manager_type: str
    manager_action_method: str
    global_action_type: str
    global_action_method: str
    manager_next_method: str
    controller_type: str
    controller_next_method: str
    selector_action_type: str = ""
    selector_string_method: str = ""
    external_result_router: ExternalResultRouterSpec | None = None
    static_default_map_field: str = ""
    default_index_method: str = ""
    default_index_by_name_method: str = ""


OPEN_UI_RESULT_ROUTER = ExternalResultRouterSpec(
    source_root_marker="Lua/Data/LuaScripts",
    router_path="Phase/Dialog/PhaseDialog.lua",
    defaults_path="Const/DialogConst.lua",
    open_message="DIALOG_OPEN_UI",
    override_message="DIALOG_CHANGE_NEXT_INDEX",
    defaults_table="DIALOG_PHASE_2_NEXT_INDEX",
    native_next_expression="GameWorld.dialogManager:Next",
    native_default_expression="CS.Beyond.Gameplay.DialogTreeOpenUINode.GetDefaultNextIndexByPanelName",
)


OPEN_UI_FAMILY = StaticPortFamilySpec(
    family="dialog_tree_open_ui",
    node_type="Beyond.Gameplay.DialogTreeOpenUINode",
    selector_enum_type="Beyond.Gameplay.DialogEnums+DialogOpenUIType",
    serialized_selector_path=("_actionData", "panelType"),
    static_port_map_field="s_panelOutConnections",
    node_action_method="DoAction",
    manager_type="Beyond.Gameplay.Core.DialogManager",
    manager_action_method="OpenUI",
    global_action_type="Beyond.Gameplay.Actions.GameAction",
    global_action_method="DialogOpenUIPanel",
    manager_next_method="Next",
    controller_type="Beyond.Gameplay.DialogTreeController",
    controller_next_method="Next",
    selector_action_type="Beyond.Gameplay.DialogOpenUIAction",
    selector_string_method="get_panelId",
    external_result_router=OPEN_UI_RESULT_ROUTER,
    static_default_map_field="s_defaultNextIndexes",
    default_index_method="GetDefaultNextIndex",
    default_index_by_name_method="GetDefaultNextIndexByPanelName",
)


_CONTRACT_CACHE: dict[tuple[Any, ...], dict[str, Any]] = {}
_CONTRACT_FAILURE_CACHE: dict[tuple[Any, ...], str] = {}


def repo_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except (OSError, ValueError):
        return str(path.resolve())


def _validated_current_ifix_evidence(
    ifix_audit: dict[str, Any],
    *,
    relevant_prefixes: set[str],
    source: Path,
) -> dict[str, Any]:
    if ifix_audit.get("status") != "validated":
        failure = (ifix_audit.get("validationFailures") or [{}])[0]
        raise ContractError(
            "validator=dialog_tree_static_port_contract "
            "gate=current_ifix_contract "
            "expected='validated' "
            f"actual={ifix_audit.get('status')!r} "
            f"source={failure.get('sourceFile') or source} "
            f"detail={failure!r}"
        )
    current_ifix = project_current_ifix_evidence(
        ifix_audit,
        relevant_prefixes=relevant_prefixes,
    )
    relevant_ifix = current_ifix["relevantFixedMethods"]
    if relevant_ifix:
        raise ContractError(
            "validator=dialog_tree_static_port_contract gate=current_ifix_exclusion "
            f"expected=[] actual={relevant_ifix!r} source={source}"
        )
    return current_ifix


def _runtime_type_name(
    pe: Any,
    metadata: Any,
    type_va: int,
    *,
    depth: int = 0,
    seen: frozenset[int] = frozenset(),
) -> str:
    """Decode one installed Il2CppType, including generic instances."""
    if depth > 10 or type_va in seen:
        return "<recursive-runtime-type>"
    offset, _section, _rva = pe.file_offset_for_va(type_va)
    if offset is None:
        return f"<type-va:0x{type_va:x}>"
    data = struct.unpack_from("<Q", pe.buf, offset)[0]
    bits = struct.unpack_from("<I", pe.buf, offset + 8)[0]
    kind = (bits >> 16) & 0xFF
    if kind in RUNTIME_PRIMITIVES:
        return RUNTIME_PRIMITIVES[kind]
    if kind in {0x11, 0x12}:
        return (
            metadata.type_full_name(metadata.types[data])
            if 0 <= data < len(metadata.types)
            else f"<typedef:{data}>"
        )
    if kind == 0x0F:
        return _runtime_type_name(
            pe, metadata, data, depth=depth + 1, seen=seen | {type_va}
        ) + "*"
    if kind == 0x1D:
        return _runtime_type_name(
            pe, metadata, data, depth=depth + 1, seen=seen | {type_va}
        ) + "[]"
    if kind == 0x15:
        generic_offset, _section, _rva = pe.file_offset_for_va(data)
        if generic_offset is None:
            return f"<generic:0x{data:x}>"
        definition_va, class_inst_va = struct.unpack_from(
            "<QQ", pe.buf, generic_offset
        )
        definition = _runtime_type_name(
            pe,
            metadata,
            definition_va,
            depth=depth + 1,
            seen=seen | {type_va},
        )
        if not class_inst_va:
            return definition
        count = pe.u32_at_va(class_inst_va)
        argv = pe.u64_at_va(class_inst_va + 8)
        if count > 64:
            return f"{definition}<invalid-argc:{count}>"
        arguments = [
            _runtime_type_name(
                pe,
                metadata,
                pe.u64_at_va(argv + index * 8),
                depth=depth + 1,
                seen=seen | {type_va},
            )
            for index in range(count)
        ]
        return f"{definition}<{','.join(arguments)}>"
    return f"<runtime-type:0x{kind:x}>"


def _metadata_runtime_type_name(
    pe: Any,
    metadata: Any,
    mapper: Any,
    metadata_registration: int,
    metadata_type_index: int,
) -> str:
    summary = mapper.metadata_registration_summary(pe, metadata_registration)
    count = int(summary["typesCount"])
    if not 0 <= metadata_type_index < count:
        return f"<type-index:{metadata_type_index}>"
    types_va = int(summary["types"], 16)
    type_va = pe.u64_at_va(types_va + metadata_type_index * 8)
    return (
        _runtime_type_name(pe, metadata, type_va)
        if type_va
        else f"<type-index:{metadata_type_index}>"
    )


def _enum_members(metadata: Any, type_name: str) -> list[dict[str, Any]]:
    defaults: dict[int, int] = {}
    default_section = metadata.sections["fieldDefaultValues"]
    if default_section.size % 12:
        raise ContractError("fieldDefaultValues is not aligned to 12-byte records")
    for offset in range(
        default_section.offset,
        default_section.offset + default_section.size,
        12,
    ):
        field_index, _type_index, data_index = struct.unpack_from(
            "<iii", metadata.buf, offset
        )
        defaults[field_index] = data_index
    data_section = metadata.sections["fieldAndParameterDefaultValueData"]
    matches = [
        type_def
        for type_def in metadata.types
        if metadata.type_full_name(type_def) == type_name
    ]
    if len(matches) != 1:
        raise ContractError(f"expected one enum {type_name}, found {len(matches)}")
    members: list[dict[str, Any]] = []
    for field in metadata.fields_for(matches[0]):
        name = metadata.string(field.name_index)
        if name == "value__" or field.index not in defaults:
            continue
        offset = data_section.offset + defaults[field.index]
        try:
            value, _ = read_compressed_int32(metadata.buf, offset)
        except (ValueError, IndexError, struct.error) as error:
            raise ContractError(
                f"validator=dialog_tree_static_port_contract gate=enum_default "
                f"enum={type_name} field={name} fieldIndex={field.index} "
                f"source=fieldAndParameterDefaultValueData+{defaults[field.index]} "
                f"expected=complete-current-compressed-Int32 actual={str(error)[:300]}"
            ) from error
        members.append({
            "value": value,
            "name": name,
            "fieldIndex": field.index,
            "token": f"0x{field.token:08x}",
        })
    return sorted(members, key=lambda row: (row["value"], row["name"]))


def _method_rows(metadata: Any, type_name: str, method_name: str) -> list[Any]:
    rows: list[Any] = []
    for type_def in metadata.types:
        if metadata.type_full_name(type_def) != type_name:
            continue
        for method in metadata.methods_for(type_def):
            if metadata.string(method.name_index) == method_name:
                rows.append(method)
    return rows


def _method_record(metadata: Any, method: Any, pointer: int, source: str) -> dict[str, Any]:
    owner = metadata.type_full_name(metadata.types[method.declaring_type])
    return {
        "type": owner,
        "method": metadata.string(method.name_index),
        "methodIndex": method.index,
        "token": f"0x{method.token:08x}",
        "address": f"0x{pointer:x}",
        "pointerSource": source,
    }


def _call_targets(instructions: Iterable[dict[str, Any]]) -> list[int]:
    targets: list[int] = []
    for row in instructions:
        match = re.fullmatch(r"call 0x([0-9a-f]+)", str(row.get("text") or ""))
        if match:
            targets.append(int(match.group(1), 16))
    return targets


def _decode_string_literal_handle(pe: Any, metadata: Any, slot_va: int) -> dict[str, Any]:
    """Decode the current-build tagged metadata handle stored at one slot.

    ``il2cpp_codegen_initialize_runtime_metadata`` extracts the kind from bits
    29..31 and the source index from ``(encoded >> 1) & 0x0fffffff``.  Kind 5
    addresses the global-metadata string-literal table.
    """
    encoded = pe.u64_at_va(slot_va)
    kind = encoded >> 29
    source_index = (encoded >> 1) & 0x0FFFFFFF
    result = {
        "slotVa": f"0x{slot_va:x}",
        "encodedHandle": f"0x{encoded:x}",
        "kind": kind,
        "sourceIndex": source_index,
    }
    if kind != 5:
        result["status"] = "not_string_literal"
        return result
    literal_section = metadata.sections["stringLiteral"]
    data_section = metadata.sections["stringLiteralData"]
    if source_index >= literal_section.size // 8:
        result["status"] = "string_literal_index_out_of_bounds"
        return result
    length, data_index = struct.unpack_from(
        "<II",
        metadata.buf,
        literal_section.offset + source_index * 8,
    )
    if data_index + length > data_section.size:
        result["status"] = "string_literal_data_out_of_bounds"
        return result
    result.update({
        "status": "decoded",
        "value": metadata.buf[
            data_section.offset + data_index:
            data_section.offset + data_index + length
        ].decode("utf-8", errors="replace"),
    })
    return result


def parse_static_enum_string_list_initializer(
    instructions: list[dict[str, Any]],
    *,
    dictionary_add_targets: set[int],
    decode_literal_slot: Any,
    expected_dictionary_type: str,
    decode_add_context: Any,
) -> list[dict[str, Any]]:
    """Parse repeated ``Dictionary.Add(enum, List<string>)`` initializer blocks.

    Each Add's R9 MethodSpec must name the selected closed dictionary. Shared
    generic code addresses alone cannot distinguish another dictionary in the
    same initializer. Unknown or clobbered contexts fail closed.

    The parser depends only on calling convention and metadata-handle shape.
    It does not contain enum values, strings, method addresses, or content ids.
    """
    rows: list[dict[str, Any]] = []
    try:
        blocks = list(static_dictionary.dictionary_add_blocks(
            instructions, add_targets=dictionary_add_targets,
            expected_type=expected_dictionary_type, decode_context=decode_add_context,
            validator="dialog_tree_static_port_contract",
        ))
    except ValueError as exc:
        raise ContractError(str(exc)) from exc
    for instruction, block, context in blocks:
        selector: int | None = None
        for row in reversed(block):
            text = str(row.get("text") or "")
            immediate = re.fullmatch(r"mov edx, 0x([0-9a-f]+)", text)
            if immediate:
                selector = int(immediate.group(1), 16)
                break
            if text == "xor edx, edx":
                selector = 0
                break
        labels: list[dict[str, Any]] = []
        for index, row in enumerate(block):
            slot_match = re.fullmatch(
                r"mov rdx, \[rip[+-]0x[0-9a-f]+ => 0x([0-9a-f]+)\]",
                str(row.get("text") or ""),
            )
            if not slot_match:
                continue
            # A string argument must feed a call before rdx is overwritten.
            has_call = False
            for follower in block[index + 1:index + 6]:
                follower_text = str(follower.get("text") or "")
                if follower_text.startswith(("mov rdx,", "xor edx,")):
                    break
                if follower_text.startswith("call 0x"):
                    has_call = True
                    break
            if not has_call:
                continue
            decoded = decode_literal_slot(int(slot_match.group(1), 16))
            if decoded.get("status") == "decoded":
                labels.append(decoded)
        if selector is None:
            raise ContractError(
                f"dictionary Add at {instruction.get('va')} has no enum selector"
            )
        if not labels:
            raise ContractError(
                f"dictionary Add at {instruction.get('va')} has no string labels"
            )
        rows.append({
            "selectorValue": selector,
            "labels": labels,
            "dictionaryAddCallVa": instruction.get("va"),
            "dictionaryAddContext": context,
        })
    if not rows:
        raise ContractError("static initializer contains no enum/list dictionary rows")
    selectors = [row["selectorValue"] for row in rows]
    if len(selectors) != len(set(selectors)):
        raise ContractError("static initializer repeats an enum selector")
    return rows


def _lua_source_record(
    path: str,
    raw: bytes,
    *,
    source_root_marker: str,
    relationship: str,
) -> dict[str, Any]:
    logical_path = "/".join((source_root_marker.strip("/"), path.strip("/")))
    return {
        "kind": "original_game_lua",
        "sourceFile": f"installed StreamingAssets VFS/{logical_path}",
        "logicalPath": logical_path,
        "sha256": hashlib.sha256(raw).hexdigest().upper(),
        "relationship": relationship,
        "materialized": False,
    }


def _lua_line(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _lua_excerpt(text: str, offset: int, *, radius: int = 1) -> str:
    lines = text.splitlines()
    line = _lua_line(text, offset)
    start = max(line - radius - 1, 0)
    end = min(line + radius, len(lines))
    return "\n".join(lines[start:end]).strip()


def _lua_symbol_aliases(text: str) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for match in re.finditer(
        r"\blocal\s+([A-Za-z_]\w*)\s*=\s*(?:PhaseId|PanelId)\.([A-Za-z_]\w*)",
        text,
    ):
        aliases[match.group(1)] = match.group(2)
    return aliases


def _resolve_lua_phase(expression: str, aliases: dict[str, str]) -> str:
    value = expression.strip()
    direct = re.fullmatch(r"(?:PhaseId|PanelId)\.([A-Za-z_]\w*)", value)
    if direct:
        return direct.group(1)
    return aliases.get(value, "")


def _simple_lua_integer_values(text: str, expression: str, offset: int) -> list[int]:
    value = expression.strip()
    if re.fullmatch(r"-?\d+", value):
        return [int(value)]
    if not re.fullmatch(r"[A-Za-z_]\w*", value):
        return []
    # Bounded, deliberately conservative local data flow.  Only literal
    # assignments in the current function body are promoted.  Argument/table
    # values remain dynamic instead of being guessed.
    prefix = text[:offset]
    function_start = max(prefix.rfind("function("), prefix.rfind("function "))
    scope = prefix[max(function_start, 0):]
    values = {
        int(match.group(1))
        for match in re.finditer(
            rf"(?:\blocal\s+)?{re.escape(value)}\s*=\s*(-?\d+)\b",
            scope,
        )
    }
    return sorted(values)


def _hl_lua_function_definitions(text: str) -> list[dict[str, Any]]:
    """Return schema-shaped HL method declarations without naming any controller.

    Endfield's shipped Lua registers class methods through ``Owner.Method =
    HL.* << function(...)``.  The next such declaration is a conservative end
    boundary: nested callbacks remain inside their owning registered method,
    while an expression outside that interval is never attributed to it.
    """
    pattern = re.compile(
        r"(?m)^\s*(?P<qualified>[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+)\s*=\s*"
        r"HL\.[^\n]*?<<\s*function\s*\((?P<parameters>[^)]*)\)"
    )
    matches = list(pattern.finditer(text))
    definitions: list[dict[str, Any]] = []
    for index, match in enumerate(matches):
        qualified = match.group("qualified")
        owner, method = qualified.rsplit(".", 1)
        parameters = [
            value.strip()
            for value in match.group("parameters").split(",")
            if value.strip()
        ]
        definitions.append({
            "owner": owner,
            "method": method,
            "parameters": parameters,
            "start": match.start(),
            "bodyStart": match.end(),
            "end": matches[index + 1].start() if index + 1 < len(matches) else len(text),
        })
    return definitions


def _hl_lua_function_at(
    definitions: list[dict[str, Any]],
    offset: int,
) -> dict[str, Any] | None:
    return next(
        (
            definition
            for definition in reversed(definitions)
            if definition["bodyStart"] <= offset < definition["end"]
        ),
        None,
    )


def _lua_balanced_call_arguments(text: str, open_paren: int) -> list[str] | None:
    """Split a Lua call's top-level arguments, failing closed on bad syntax."""
    if open_paren >= len(text) or text[open_paren] != "(":
        return None
    pairs = {"(": ")", "[": "]", "{": "}"}
    stack = [")"]
    quote = ""
    escaped = False
    start = open_paren + 1
    arguments: list[str] = []
    index = start
    while index < len(text):
        char = text[index]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = ""
            index += 1
            continue
        if char in ("'", '"'):
            quote = char
        elif char in pairs:
            stack.append(pairs[char])
        elif char in ")]}]":
            if not stack or char != stack[-1]:
                return None
            stack.pop()
            if not stack:
                tail = text[start:index].strip()
                if tail or arguments:
                    arguments.append(tail)
                return arguments
        elif char == "," and len(stack) == 1:
            arguments.append(text[start:index].strip())
            start = index + 1
        index += 1
    return None


def _lua_formal_literal_call_paths(
    text: str,
    expression: str,
    offset: int,
) -> list[dict[str, Any]]:
    """Find literal in-class call arguments feeding a registered HL method.

    These rows prove concrete shipped-Lua paths but deliberately do not close
    the formal parameter's complete runtime domain: native/reflection callers
    or dynamically typed receivers may still supply other values.
    """
    value = expression.strip()
    if not re.fullmatch(r"[A-Za-z_]\w*", value):
        return []
    definitions = _hl_lua_function_definitions(text)
    producer_function = _hl_lua_function_at(definitions, offset)
    if not producer_function or value not in producer_function["parameters"]:
        return []
    parameter_index = producer_function["parameters"].index(value)
    owner = str(producer_function["owner"])
    method = str(producer_function["method"])
    rows: list[dict[str, Any]] = []

    self_pattern = re.compile(rf"\bself\s*:\s*{re.escape(method)}\s*\(")
    for match in self_pattern.finditer(text):
        caller = _hl_lua_function_at(definitions, match.start())
        if not caller or caller["owner"] != owner:
            continue
        # Lua's colon call supplies self implicitly.  Registered instance
        # methods conventionally expose that as their first formal parameter.
        argument_index = parameter_index - (
            1 if producer_function["parameters"][:1] == ["self"] else 0
        )
        if argument_index < 0:
            continue
        arguments = _lua_balanced_call_arguments(text, match.end() - 1)
        if arguments is None or argument_index >= len(arguments):
            continue
        argument = arguments[argument_index]
        if not re.fullmatch(r"-?\d+", argument):
            continue
        rows.append({
            "kind": "literal_in_class_method_call_argument",
            "value": int(argument),
            "expression": argument,
            "owner": owner,
            "callerMethod": caller["method"],
            "calleeMethod": method,
            "line": _lua_line(text, match.start()),
            "excerpt": _lua_excerpt(text, match.start()),
        })

    qualified_pattern = re.compile(
        rf"\b{re.escape(owner)}\s*\.\s*{re.escape(method)}\s*\("
    )
    for match in qualified_pattern.finditer(text):
        arguments = _lua_balanced_call_arguments(text, match.end() - 1)
        if arguments is None or parameter_index >= len(arguments):
            continue
        argument = arguments[parameter_index]
        if not re.fullmatch(r"-?\d+", argument):
            continue
        rows.append({
            "kind": "literal_qualified_method_call_argument",
            "value": int(argument),
            "expression": argument,
            "owner": owner,
            "callerMethod": (_hl_lua_function_at(definitions, match.start()) or {}).get("method", ""),
            "calleeMethod": method,
            "line": _lua_line(text, match.start()),
            "excerpt": _lua_excerpt(text, match.start()),
        })
    rows.sort(key=lambda row: (row["line"], row["kind"], row["value"]))
    return rows


def parse_lua_external_result_router(
    lua_sources: dict[str, bytes],
    spec: ExternalResultRouterSpec,
    *,
    native_defaults: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Recover defaults and producers from a complete shipped Lua corpus.

    Every occurrence of the override protocol must parse as its declaration,
    receiver registration, or a producer call.  Unknown occurrences fail the
    audit closed so a client update cannot silently invalidate reachability.
    """
    validator = "dialog_tree_external_result_router"
    normalized = {path.replace("\\", "/"): raw for path, raw in lua_sources.items()}
    missing = [path for path in (spec.router_path, spec.defaults_path) if path not in normalized]
    if missing:
        raise ContractError(
            f"validator={validator} gate=required_sources expected="
            f"{[spec.router_path, spec.defaults_path]!r} actual_missing={missing!r}"
        )
    decoded = {
        path: raw.decode("utf-8-sig")
        for path, raw in normalized.items()
    }
    router_text = decoded[spec.router_path]
    router_checks = {
        "open_message_receiver": rf"\[MessageConst\.{re.escape(spec.open_message)}\]",
        "selector_string_to_phase": r"PhaseId\s*\[\s*panelIdStr\s*\]",
        "temporary_result_write": r"m_tempNextIndex\s*=\s*args\.nextIndex",
        "temporary_result_read": r"m_tempNextIndex\s*>=\s*0",
        "transition_calls_next": r"self:Next\s*\(\s*nextIndex\s*\)",
        "native_next_bridge": rf"{re.escape(spec.native_next_expression)}\s*\(\s*num\s*\)",
    }
    checks: list[dict[str, Any]] = []
    for gate, pattern in router_checks.items():
        count = len(re.findall(pattern, router_text))
        checks.append({"gate": gate, "expected": 1, "actual": count, "passed": count == 1})
    native_mode = bool(spec.native_default_expression and spec.native_default_expression in router_text)
    if native_mode:
        owner = Path(spec.router_path).stem
        functions = {f"{row['owner']}.{row['method']}": row
                     for row in _hl_lua_function_definitions(router_text)}
        expected_bodies = {
            f"{owner}.GetNextIndex": (
                "local suc, phaseDialog = PhaseManager:IsOpen(PHASE_ID) if not suc then return 0 end "
                "if phaseDialog.m_tempNextIndex >= 0 then return phaseDialog.m_tempNextIndex end "
                f"return {owner}.GetDefaultNextIndex(phaseId) end"
            ),
            f"{owner}.GetDefaultNextIndex": (
                "local phaseName = PhaseManager:GetPhaseName(phaseId) "
                f'return {spec.native_default_expression}(phaseName or "") end'
            ),
        }
        for name, expected_body in expected_bodies.items():
            definition = functions.get(name)
            actual = (router_text[definition["bodyStart"]:definition["end"]]
                      if definition else "")
            actual = " ".join(re.sub(r"--[^\n]*", "", actual).split())
            checks.append({"gate": f"native_default_function:{name}",
                           "expected": expected_body, "actual": actual[:800],
                           "passed": actual == expected_body})
        bridge_pattern = rf"local\s+nextIndex\s*=\s*{re.escape(owner)}\.GetNextIndex\(self\.m_openedPhaseId\)"
        bridge_count = len(re.findall(bridge_pattern,router_text))
        checks.extend([
            {"gate": "transition_uses_native_default_router", "expected": 1,
             "actual": bridge_count, "passed": bridge_count == 1},
            {"gate": "native_defaults_authenticated", "expected": "validated",
             "actual": (native_defaults or {}).get("status"),
             "passed": (native_defaults or {}).get("status") == "validated"},
        ])
    else:
        count = len(re.findall(r"s_nextIndexConfig\s*\[\s*phaseId\s*\]\s*or\s*0", router_text))
        checks.append({"gate": "configured_default_read", "expected": 1,
                       "actual": count, "passed": count == 1})
    failed = next((row for row in checks if not row["passed"]), None)
    if failed:
        raise ContractError(
            f"validator={validator} gate={failed['gate']} expected={str(failed['expected'])[:800]!r} actual={str(failed['actual'])[:800]!r} "
            f"source={spec.router_path} sha256={hashlib.sha256(normalized[spec.router_path]).hexdigest().upper()}"
        )

    defaults_text = decoded[spec.defaults_path]
    table_match = re.search(
        rf"\b{re.escape(spec.defaults_table)}\s*=\s*\{{(?P<body>.*?)\}}",
        defaults_text,
        re.S,
    )
    if not native_mode and not table_match:
        raise ContractError(
            f"validator={validator} gate=defaults_table expected={spec.defaults_table!r} "
            f"actual=missing source={spec.defaults_path}"
        )
    defaults: dict[str, int] = dict(native_defaults["phaseDefaults"]) if native_mode else {}
    body = "" if native_mode else table_match.group("body")
    consumed = []
    for match in re.finditer(r"\b([A-Za-z_]\w*)\s*=\s*(-?\d+)\s*,?", body):
        phase, raw_index = match.groups()
        if phase in defaults:
            raise ContractError(
                f"validator={validator} gate=unique_phase_default expected=unique "
                f"actual={phase!r} source={spec.defaults_path}"
            )
        defaults[phase] = int(raw_index)
        consumed.append(match.span())
    residue = list(body)
    for start, end in consumed:
        residue[start:end] = " " * (end - start)
    residue_text = re.sub(r"--[^\n]*", "", "".join(residue)).strip()
    if residue_text:
        raise ContractError(
            f"validator={validator} gate=defaults_table_entries expected=name_integer_pairs "
            f"actual={residue_text[:120]!r} source={spec.defaults_path}"
        )

    producers: list[dict[str, Any]] = []
    occurrence_diagnostics: list[dict[str, Any]] = []
    override_pattern = re.compile(
        rf"(?:Notify|MessageNotify)\s*\(\s*MessageConst\.{re.escape(spec.override_message)}"
        r"\s*,\s*\{(?P<table>.*?)\}\s*\)",
        re.S,
    )
    direct_pattern = re.compile(
        rf"{re.escape(spec.native_next_expression)}\s*\(\s*(?P<index>[^)]*)\)",
        re.S,
    )
    for path, text in sorted(decoded.items()):
        aliases = _lua_symbol_aliases(text)
        parsed_override_offsets: set[int] = set()
        for match in override_pattern.finditer(text):
            table = match.group("table")
            phase_match = re.search(r"\bphaseId\s*=\s*([^,}]+)", table)
            index_match = re.search(r"\bnextIndex\s*=\s*([^,}]+)", table)
            if not phase_match or not index_match:
                raise ContractError(
                    f"validator={validator} gate=override_fields expected=phaseId,nextIndex "
                    f"actual={table[:160]!r} source={path} line={_lua_line(text, match.start())}"
                )
            phase_expression = phase_match.group(1).strip()
            index_expression = index_match.group(1).strip()
            phase = _resolve_lua_phase(phase_expression, aliases)
            if not phase:
                raise ContractError(
                    f"validator={validator} gate=override_phase_resolution expected=PhaseId_symbol "
                    f"actual={phase_expression!r} source={path} line={_lua_line(text, match.start())}"
                )
            literal_call_paths = _lua_formal_literal_call_paths(
                text,
                index_expression,
                match.start(),
            )
            values = (
                sorted({int(row["value"]) for row in literal_call_paths})
                if literal_call_paths
                else _simple_lua_integer_values(text, index_expression, match.start())
            )
            producers.append({
                "kind": "override_message",
                "phaseName": phase,
                "indexExpression": index_expression,
                "possibleIndexes": values,
                "indexStatus": (
                    "literal_call_paths_with_dynamic_residual"
                    if literal_call_paths
                    else ("bounded_literals" if values else "dynamic_expression")
                ),
                "valueFlowEvidence": literal_call_paths,
                "line": _lua_line(text, match.start()),
                "excerpt": _lua_excerpt(text, match.start()),
                "source": _lua_source_record(
                    path,
                    normalized[path],
                    source_root_marker=spec.source_root_marker,
                    relationship="dialog_ui_result_override_producer",
                ),
            })
            parsed_override_offsets.add(text.find(spec.override_message, match.start(), match.end()))

        occurrence_offsets = [m.start() for m in re.finditer(re.escape(spec.override_message), text)]
        for offset in occurrence_offsets:
            if offset in parsed_override_offsets:
                occurrence_diagnostics.append({"source": path, "line": _lua_line(text, offset), "kind": "producer"})
                continue
            line_text = text.splitlines()[_lua_line(text, offset) - 1]
            declaration = bool(re.search(
                rf"^\s*(?:{re.escape(spec.override_message)}\s*=|"
                rf"[\"']{re.escape(spec.override_message)}[\"']\s*,?)",
                line_text,
            ))
            receiver = bool(re.search(rf"\[\s*MessageConst\.{re.escape(spec.override_message)}\s*\]", line_text))
            if declaration or receiver:
                occurrence_diagnostics.append({
                    "source": path,
                    "line": _lua_line(text, offset),
                    "kind": "declaration" if declaration else "receiver",
                })
                continue
            raise ContractError(
                f"validator={validator} gate=override_occurrence_census expected=declaration|receiver|producer "
                f"actual={line_text.strip()[:160]!r} source={path} line={_lua_line(text, offset)}"
            )

        # The router's own Next wrapper is the bridge under validation, not a
        # phase-specific result producer.
        if path == spec.router_path:
            continue
        phase_candidates = sorted(set(aliases.values()))
        for match in direct_pattern.finditer(text):
            expression = match.group("index").strip()
            literal_call_paths = _lua_formal_literal_call_paths(
                text,
                expression,
                match.start(),
            )
            values = (
                sorted({int(row["value"]) for row in literal_call_paths})
                if literal_call_paths
                else _simple_lua_integer_values(text, expression, match.start())
            )
            if len(phase_candidates) != 1:
                raise ContractError(
                    f"validator={validator} gate=direct_next_phase_resolution expected=one_local_phase_or_panel "
                    f"actual={phase_candidates!r} source={path} line={_lua_line(text, match.start())}"
                )
            producers.append({
                "kind": "direct_native_next",
                "phaseName": phase_candidates[0],
                "indexExpression": expression,
                "possibleIndexes": values,
                "indexStatus": (
                    "literal_call_paths_with_dynamic_residual"
                    if literal_call_paths
                    else ("bounded_literals" if values else "dynamic_expression")
                ),
                "valueFlowEvidence": literal_call_paths,
                "line": _lua_line(text, match.start()),
                "excerpt": _lua_excerpt(text, match.start()),
                "source": _lua_source_record(
                    path,
                    normalized[path],
                    source_root_marker=spec.source_root_marker,
                    relationship="dialog_ui_direct_result_producer",
                ),
            })

    producers.sort(key=lambda row: (
        row["phaseName"], row["source"]["logicalPath"], row["line"], row["kind"]
    ))
    by_phase: dict[str, list[dict[str, Any]]] = {}
    for producer in producers:
        by_phase.setdefault(producer["phaseName"], []).append(producer)
    return {
        "schema": "dialogExternalResultRouter.v2",
        "status": "validated",
        "defaultIndex": 0,
        "phaseDefaults": defaults,
        "defaultPolicySource": "native_dictionary" if native_mode else "lua_table",
        "producers": producers,
        "producersByPhase": by_phase,
        "sourceCorpus": {
            "fileCount": len(normalized),
            "completeOverrideOccurrenceCount": len(occurrence_diagnostics),
            "overrideProducerCount": sum(row["kind"] == "override_message" for row in producers),
            "directProducerCount": sum(row["kind"] == "direct_native_next" for row in producers),
        },
        "routerSource": _lua_source_record(
            spec.router_path,
            normalized[spec.router_path],
            source_root_marker=spec.source_root_marker,
            relationship="dialog_ui_result_router",
        ),
        "defaultsSource": native_defaults["source"] if native_mode else _lua_source_record(
            spec.defaults_path,
            normalized[spec.defaults_path],
            source_root_marker=spec.source_root_marker,
            relationship="dialog_ui_result_defaults",
        ),
        "validation": {"validator": validator, "status": "validated", "checks": checks},
        "evidenceBoundary": (
            "The complete shipped Lua corpus proves default and explicit producer paths into "
            "DialogManager.Next(index). Producer presence does not observe a player result, prove "
            "mission activation, or make a missing current producer permanently unreachable."
        ),
    }


def recover_installed_lua_external_result_router(
    spec: ExternalResultRouterSpec,
    *,
    game_root: Path = DEFAULT_GAME_ROOT,
    animestudio_cli: Path = DEFAULT_ANIMESTUDIO_CLI,
    native_defaults: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Target-dump and validate the complete installed Lua corpus."""
    validator = "dialog_tree_external_result_router"
    if not animestudio_cli.is_file():
        raise ContractError(
            f"validator={validator} gate=animestudio_cli expected=file actual=missing "
            f"source={animestudio_cli}"
        )
    streaming_assets = game_root / "StreamingAssets"
    if not streaming_assets.is_dir():
        raise ContractError(
            f"validator={validator} gate=streaming_assets expected=directory actual=missing "
            f"source={streaming_assets}"
        )
    with tempfile.TemporaryDirectory(prefix="endfield-dialog-result-router-") as temporary:
        output = Path(temporary)
        command = [
            str(animestudio_cli), "dump",
            "--streaming-assets", str(streaming_assets),
            "--fallback-assets", str(game_root),
            "--output", str(output),
            "--block-type", "lua",
            "--file-regex", r"\.lua$",
        ]
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        summary = f"{completed.stdout}\n{completed.stderr}"
        if completed.returncode:
            raise ContractError(
                f"validator={validator} gate=complete_lua_dump expected=returncode_0 "
                f"actual={completed.returncode} diagnostic={summary[-1000:]!r}"
            )
        completion = re.findall(r"Extracted\s+(\d+)\s*/\s*(\d+)\s+files", summary)
        if len(completion) != 1 or completion[0][0] != completion[0][1]:
            raise ContractError(
                f"validator={validator} gate=complete_lua_dump expected=one_complete_count "
                f"actual={completion!r} diagnostic={summary[-1000:]!r}"
            )
        root_matches = [path for path in output.rglob("LuaScripts") if path.is_dir()]
        if len(root_matches) != 1:
            raise ContractError(
                f"validator={validator} gate=lua_source_root expected=1 actual={len(root_matches)} "
                f"source={output}"
            )
        source_root = root_matches[0]
        lua_paths = sorted(source_root.rglob("*.lua"))
        expected_count = int(completion[0][1])
        if len(lua_paths) != expected_count:
            raise ContractError(
                f"validator={validator} gate=materialized_lua_count expected={expected_count} "
                f"actual={len(lua_paths)} source={source_root}"
            )
        sources = {
            path.relative_to(source_root).as_posix(): path.read_bytes()
            for path in lua_paths
        }
        result = parse_lua_external_result_router(sources, spec, native_defaults=native_defaults)
    result["sourceCorpus"].update({
        "dumpedFileCount": expected_count,
        "animeStudioCli": str(animestudio_cli.resolve()),
        "animeStudioCliSha256": sha256_file(animestudio_cli),
        "streamingAssets": str(streaming_assets.resolve()),
        "mode": "complete_targeted_installed_vfs_lua_dump",
    })
    return result


def _recover_static_port_family_contract_uncached(
    spec: StaticPortFamilySpec,
    *,
    game_assembly_path: Path = DEFAULT_GAME_ASSEMBLY,
    metadata_path: Path = DEFAULT_METADATA,
    ifix_contract_path: Path = DEFAULT_IFIX_CONTRACT,
) -> dict[str, Any]:
    """Recover and fail-closed validate one installed multi-output family."""
    cache_key = (
        spec,
        str(game_assembly_path.resolve()),
        str(metadata_path.resolve()),
        str(ifix_contract_path.resolve()),
    )
    if cache_key in _CONTRACT_CACHE:
        return _CONTRACT_CACHE[cache_key]
    for path in (game_assembly_path, metadata_path):
        if not path.is_file():
            raise ContractError(f"missing original input: {path}")

    image = open_native_image(game_assembly_path, metadata_path)
    body_index = BodyIndex(image)
    mapper, metadata, pe = image.mapper, image.metadata, image.pe
    metadata_registration = image.metadata_registration
    method_by_pointer = body_index.names_by_pointer

    def one_method(type_name: str, method_name: str, parameter_count: int | None = None) -> Any:
        matches = _method_rows(metadata, type_name, method_name)
        if parameter_count is not None:
            matches = [m for m in matches if m.parameter_count == parameter_count]
        if len(matches) != 1:
            raise ContractError(
                f"expected one {type_name}.{method_name}/{parameter_count}, found {len(matches)}"
            )
        return matches[0]

    def pointer_record(method: Any) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        pointer = image.method_pointer_va(method)
        pointer_source = "codegen_module"
        owner = metadata.type_full_name(metadata.types[method.declaring_type])
        try:
            body = body_index.body(owner, metadata.string(method.name_index), parameters=[
                metadata.metadata_type_name(parameter.type_index)
                for parameter in metadata.parameters_for(method)
            ])
        except ClaimError as exc:
            raise ContractError(str(exc)) from exc
        if not pointer:
            pointer = body.pointer
            pointer_source = "generic_method_pointer"
        if body.pointer != pointer or pointer not in body_index.extents:
            raise ContractError(
                "validator=dialog_tree_static_port_contract gate=owned_method_body "
                f"expected='registered pointer with pdata extent' actual={body.pointer:#x} "
                f"source={owner}.{metadata.string(method.name_index)}"
            )
        record = _method_record(metadata, method, pointer, pointer_source)
        record["bodyRange"] = {
            "startVa": f"0x{pointer:x}", "endVa": f"0x{pointer + body.size:x}",
            "sha256": hashlib.sha256(pe.bytes_at_va(pointer, body.size)).hexdigest().upper(),
            "boundary": "registered primary pdata body; owned/followed fragments included in checks",
        }
        record["fragmentInstructionCount"] = len(body.fragment_rows)
        return record, body.all_rows

    type_matches = [
        type_def
        for type_def in metadata.types
        if metadata.type_full_name(type_def) == spec.node_type
    ]
    if len(type_matches) != 1:
        raise ContractError(f"expected one node type {spec.node_type}, found {len(type_matches)}")
    node_type = type_matches[0]
    field_matches = [
        field
        for field in metadata.fields_for(node_type)
        if metadata.string(field.name_index) == spec.static_port_map_field
    ]
    if len(field_matches) != 1:
        raise ContractError(
            f"expected one {spec.node_type}.{spec.static_port_map_field}, found {len(field_matches)}"
        )
    port_field = field_matches[0]
    port_field_type = _metadata_runtime_type_name(
        pe,
        metadata,
        mapper,
        metadata_registration,
        port_field.type_index,
    )
    expected_type_fragments = (
        "System.Collections.Generic.Dictionary",
        spec.selector_enum_type,
        "System.Collections.Generic.List",
        "System.String",
    )
    if not all(fragment in port_field_type for fragment in expected_type_fragments):
        raise ContractError(
            f"static port field type mismatch: expected {expected_type_fragments}, actual {port_field_type}"
        )

    cctor = one_method(spec.node_type, ".cctor", 0)
    cctor_record, cctor_instructions = pointer_record(cctor)
    dictionary_add_targets = {
        pointer
        for pointer, rows in method_by_pointer.items()
        if any(
            str(row.get("type") or "").startswith("System.Collections.Generic.Dictionary")
            and row.get("method") == "Add"
            for row in rows
        )
    }
    spec_va = int(image.registration["methodSpecs"], 16)
    spec_records = pe.bytes_at_va(spec_va, image.registration["methodSpecsCount"] * 12)

    def decode_generic_context(slot: int, target: int, method_name: str) -> dict[str, Any]:
        raw = pe.bytes_at_va(slot, 8)
        context = usage_method_spec(
            raw, spec_records, len(metadata.methods), image.instantiations.count,
            source=str(game_assembly_path), usage_offset=slot, records_offset=spec_va,
        )
        spec_index = context["index"]
        definition = context["definition"]
        method = metadata.methods[definition]
        owner = metadata.type_full_name(metadata.types[method.declaring_type])
        # A concrete MethodSpec need not have its own canonical registration.
        # The direct call independently names the same open Add definition;
        # only the exact R9 usage supplies the closed arguments, never the
        # Object instantiation sharing that native body.
        matching_definition = any(row.get("methodIndex") == definition
                                  for row in method_by_pointer.get(target, []))
        expected_return = {"Add": "System.Void", "TryGetValue": "System.Boolean", "TryParse": "System.Boolean"}[method_name]
        if (metadata.string(method.name_index) != method_name
                or not matching_definition
                or metadata.metadata_type_name(method.return_type) != expected_return):
            raise ValueError(f"MethodSpec={spec_index} target={target:#x} expected=matching open {method_name} definition actual={owner}.{metadata.string(method.name_index)} matched={matching_definition}")
        def arguments(index: int) -> list[str]:
            if index < 0:
                return []
            return [_runtime_type_name(pe, metadata, arg.type_pointer_va)
                    for arg in image.instantiations.resolve(index).arguments]
        closed_args = arguments(context["classInstantiationIndex"])
        return {
            "usageSlotVa": f"0x{slot:x}", "usageRawHex": raw.hex().upper(),
            "methodSpecIndex": spec_index, "methodPointerVa": f"0x{target:x}",
            "methodDefinitionIndex": definition, "methodSpecRawHex": context["rawHex"],
            "declaringType": f"{owner}<{','.join(closed_args)}>" if closed_args else owner,
            "classArguments": closed_args,
            "methodArguments": arguments(context["methodInstantiationIndex"]),
            "methodName": method_name,
            "evidenceBoundary": "exact call target open definition and supplied closed MethodSpec; no canonical concrete entry or runtime MethodInfo resolution inferred",
        }
    def decode_add_context(slot: int, target: int) -> dict[str, Any]:
        context = decode_generic_context(slot, target, "Add")
        if (not context["declaringType"].startswith("System.Collections.Generic.Dictionary")
                or len(context["classArguments"]) != 2 or context["methodArguments"]):
            raise ValueError(f"expected=closed two-argument Dictionary.Add actual={context!r}")
        return context
    initializer_rows = parse_static_enum_string_list_initializer(
        cctor_instructions,
        dictionary_add_targets=dictionary_add_targets,
        decode_literal_slot=lambda slot: _decode_string_literal_handle(
            pe, metadata, slot
        ),
        expected_dictionary_type=port_field_type,
        decode_add_context=decode_add_context,
    )
    enum_rows = _enum_members(metadata, spec.selector_enum_type)
    enum_by_value = {int(row["value"]): row for row in enum_rows}
    for row in initializer_rows:
        enum_row = enum_by_value.get(int(row["selectorValue"]))
        if enum_row is None:
            raise ContractError(
                f"static port selector {row['selectorValue']} is absent from {spec.selector_enum_type}"
            )
        row["selectorName"] = enum_row["name"]

    method_specs = [
        ("nodeAction", spec.node_type, spec.node_action_method, 0),
        ("managerAction", spec.manager_type, spec.manager_action_method, 1),
        ("globalAction", spec.global_action_type, spec.global_action_method, 1),
        ("managerNext", spec.manager_type, spec.manager_next_method, 1),
        ("controllerNext", spec.controller_type, spec.controller_next_method, 1),
    ]
    if spec.selector_action_type and spec.selector_string_method:
        method_specs.append((
            "selectorString",
            spec.selector_action_type,
            spec.selector_string_method,
            0,
        ))
    if spec.static_default_map_field:
        method_specs.extend([
            ("defaultIndex", spec.node_type, spec.default_index_method, 1),
            ("defaultIndexByName", spec.node_type, spec.default_index_by_name_method, 1),
        ])
    native_methods: dict[str, dict[str, Any]] = {}
    decoded_methods: dict[str, list[dict[str, Any]]] = {}
    for key, type_name, method_name, parameter_count in method_specs:
        record, instructions = pointer_record(
            one_method(type_name, method_name, parameter_count)
        )
        native_methods[key] = record
        decoded_methods[key] = instructions

    def address(key: str) -> int:
        return int(native_methods[key]["address"], 16)

    validations = [
        {
            "gate": "node_action_calls_manager_action",
            "expected": native_methods["managerAction"]["address"],
            "actual": [f"0x{x:x}" for x in _call_targets(decoded_methods["nodeAction"])],
            "passed": address("managerAction") in _call_targets(decoded_methods["nodeAction"]),
        },
        {
            "gate": "manager_action_calls_global_action",
            "expected": native_methods["globalAction"]["address"],
            "actual": [f"0x{x:x}" for x in _call_targets(decoded_methods["managerAction"])],
            "passed": address("globalAction") in _call_targets(decoded_methods["managerAction"]),
        },
        {
            "gate": "controller_accepts_explicit_nonnegative_index",
            "expected": "signed-negative test before continuation",
            "actual": [row.get("text") for row in decoded_methods["controllerNext"]],
            "passed": any(
                str(row.get("text") or "").startswith("jns 0x")
                for row in decoded_methods["controllerNext"]
            ),
        },
    ]
    if "selectorString" in native_methods:
        validations.append({
            "gate": "global_action_calls_selector_string",
            "expected": native_methods["selectorString"]["address"],
            "actual": [f"0x{x:x}" for x in _call_targets(decoded_methods["globalAction"])],
            "passed": address("selectorString") in _call_targets(decoded_methods["globalAction"]),
        })
    failed = [row for row in validations if not row["passed"]]
    if failed:
        first = failed[0]
        raise ContractError(
            "validator=dialog_tree_static_port_contract "
            f"gate={first['gate']} expected={first['expected']!r} actual={first['actual']!r}"
        )

    ifix_audit = load_ifix_patch_contract(
        ifix_contract_path,
        gameassembly=game_assembly_path,
        metadata=metadata_path,
    )
    relevant_prefixes = {
        f"{type_name}::{method_name}("
        for _key, type_name, method_name, _parameter_count in method_specs
    }
    current_ifix = _validated_current_ifix_evidence(
        ifix_audit,
        relevant_prefixes=relevant_prefixes,
        source=ifix_contract_path,
    )

    native_defaults = None
    if spec.static_default_map_field:
        defaults_field = [field for field in metadata.fields_for(node_type)
                          if metadata.string(field.name_index) == spec.static_default_map_field]
        expected_default_type = f"System.Collections.Generic.Dictionary`2<{spec.selector_enum_type},int>"
        if len(defaults_field) != 1 or _metadata_runtime_type_name(
                pe, metadata, mapper, metadata_registration, defaults_field[0].type_index) != expected_default_type:
            raise ContractError("validator=dialog_tree_native_default gate=declared_dictionary expected=enum_Int32 actual=missing_or_changed")
        default_rows = static_dictionary.parse_enum_int_initializer(
            cctor_instructions, add_targets=dictionary_add_targets,
            expected_type=expected_default_type, decode_context=decode_add_context,
            validator="dialog_tree_native_default",
        )
        field_offset = body_index.field_offset(f"{spec.node_type}::{spec.static_default_map_field}")

        def static_field_program(rows: list[dict], store: bool) -> list[int]:
            matches = []
            operand = f"[rcx+0x{field_offset:x}]" if field_offset else "[rcx]"
            terminal = f"mov {operand}, rbx" if store else f"mov rcx, {operand}"
            for ordinal, (first, second, third) in enumerate(zip(rows, rows[1:], rows[2:])):
                load = re.fullmatch(r"mov rax, \[rip[+-]0x[0-9a-f]+ => 0x([0-9a-f]+)\]", str(first.get("text") or ""))
                if (not load or second.get("text") != "mov rcx, [rax+0xb8]"
                        or third.get("text") != terminal):
                    continue
                cell = int(load.group(1), 16)
                type_index = unresolved_usage_index(pe.bytes_at_va(cell, 8), image.registration["typesCount"],
                                                   tag=1, source=str(game_assembly_path), offset=cell)
                if _metadata_runtime_type_name(pe, metadata, mapper, metadata_registration, type_index) == spec.node_type:
                    matches.append(ordinal+2)
            return matches

        getter = decoded_methods["defaultIndex"]
        by_name = decoded_methods["defaultIndexByName"]
        lookup_proofs = []
        for index, row in enumerate(getter):
            call = re.fullmatch(r"call 0x([0-9a-f]+)", str(row.get("text") or ""))
            if not call or index < 3:
                continue
            target = int(call.group(1), 16)
            if not any(r.get("method") == "TryGetValue" for r in method_by_pointer.get(target, [])):
                continue
            context_load = re.fullmatch(r"mov r9, \[rip[+-]0x[0-9a-f]+ => 0x([0-9a-f]+)\]", str(getter[index-3].get("text") or ""))
            out = re.fullmatch(r"lea r8, \[rsp\+0x([0-9a-f]+)\]", str(getter[index-2].get("text") or ""))
            if not context_load or not out or getter[index-1].get("text") != "mov edx, ebx":
                continue
            context = decode_generic_context(int(context_load.group(1),16), target, "TryGetValue")
            displacement = int(out.group(1),16)
            if (context["declaringType"] != expected_default_type or context["methodArguments"]
                    or not any(r.get("text") == "mov ebx, ecx" for r in getter[:index])
                    or not any(r.get("text") == f"and [rsp+0x{displacement:x}], 0x0" for r in getter[:index])):
                continue
            raw = pe.bytes_at_va(int(row["va"],16)+5,14)
            mask = static_dictionary.prove_masked_int32_lookup_return(raw, displacement)
            field_reads = static_field_program(getter[:index-3],False)
            if (len(field_reads) != 1 or mask["stackReleaseBytes"] != 0x20
                    or [r.get("text") for r in getter[:2]] != ["push rbx", "sub rsp, 0x20"]
                    or any(re.match(r"(?:mov|lea|xor|pop|add|sub|and|or) (?:rcx|ecx)(?:,|$)", str(r.get("text") or ""))
                           for r in getter[field_reads[0]+1:index-3])):
                continue
            lookup_proofs.append({"context": context, **mask})
        parse_proofs = []
        for index, row in enumerate(by_name):
            call = re.fullmatch(r"call 0x([0-9a-f]+)", str(row.get("text") or ""))
            if not call or index < 3 or index+6 >= len(by_name):
                continue
            target = int(call.group(1),16)
            if not any(r.get("type") == "System.Enum" and r.get("method") == "TryParse" for r in method_by_pointer.get(target, [])):
                continue
            context_load = re.fullmatch(r"mov r8, \[rip[+-]0x[0-9a-f]+ => 0x([0-9a-f]+)\]", str(by_name[index-3].get("text") or ""))
            out = re.fullmatch(r"lea rdx, \[rsp\+0x([0-9a-f]+)\]", str(by_name[index-2].get("text") or ""))
            if not context_load or not out or by_name[index-1].get("text") != "mov rcx, rbx":
                continue
            context = decode_generic_context(int(context_load.group(1),16), target, "TryParse")
            if context["methodArguments"] != [spec.selector_enum_type] or context["classArguments"]:
                continue
            follow = [r.get("text") for r in by_name[index+1:index+7]]
            branch = re.fullmatch(r"jne 0x([0-9a-f]+)", str(follow[1]))
            normal = follow[0] == "test al, al" and branch and follow[2:] == ["xor eax, eax", "add rsp, 0x20", "pop rbx", "ret"]
            tail = f"jmp {native_methods['defaultIndex']['address']}"
            if (normal and int(branch.group(1),16) == int(by_name[index+7]["va"],16)
                    and any(r.get("text") == "mov rbx, rcx" for r in by_name[:index])
                    and any(r.get("text") == f"mov ecx, [rsp+0x{out.group(1)}]" for r in by_name[index+7:])
                    and tail in [r.get("text") for r in by_name[index+7:]]):
                parse_proofs.append({"context": context, "falseReturn": 0, "trueContinuation": native_methods["defaultIndex"]})
        field_stores = static_field_program(cctor_instructions,True)
        first_add = min(int(row["dictionaryAddCallVa"],16) for row in default_rows)
        first_index = next(i for i,r in enumerate(cctor_instructions) if int(r["va"],16) == first_add)
        retained_dictionary = len(field_stores) == 1 and field_stores[0] > first_index
        if retained_dictionary:
            retained_dictionary = not any(
                re.match(r"(?:mov|lea|xor|pop|add|sub|and|or) (?:rbx|ebx)(?:,|$)", str(r.get("text") or ""))
                for r in cctor_instructions[first_index+1:field_stores[0]])
            for entry in default_rows:
                call_index = next(i for i,r in enumerate(cctor_instructions)
                                  if r["va"] == entry["dictionaryAddCallVa"])
                if call_index >= field_stores[0]:
                    retained_dictionary = False
                for r in reversed(cctor_instructions[first_index-4:call_index]):
                    text = str(r.get("text") or "")
                    if text == "mov rcx, rbx":
                        break
                    if text.startswith("call ") or re.match(r"(?:mov|lea|xor|and|or|add|sub) (?:rcx|ecx)(?:,|$)",text):
                        retained_dictionary = False
                        break
                else:
                    retained_dictionary = False
        if len(lookup_proofs) != 1 or len(parse_proofs) != 1 or not retained_dictionary:
            raise ContractError("validator=dialog_tree_native_default gate=default_consumer "
                                "expected='one typed lookup, one enum parse and same static field write/read' "
                                f"actual={(len(lookup_proofs),len(parse_proofs),retained_dictionary)!r} source={game_assembly_path}")
        phase_defaults = {}
        for row in default_rows:
            enum = enum_by_value.get(row["selectorValue"])
            if enum is None:
                raise ContractError(f"validator=dialog_tree_native_default gate=enum_selector actual={row['selectorValue']}")
            row["selectorName"] = enum["name"]
            phase_defaults[enum["name"]] = row["value"]
        native_defaults = {"status": "validated", "defaultIndex": 0, "phaseDefaults": phase_defaults,
                           "field": spec.static_default_map_field, "fieldOffset": field_offset,
                           "initializerRows": default_rows, "lookupProofs": lookup_proofs, "panelNameProofs": parse_proofs,
                           "source": {"kind": "original_game_binary", "sourceFile": str(game_assembly_path.resolve()),
                                      "sha256": sha256_file(game_assembly_path)},
                           "evidenceBoundary": "exact stored defaults and unpatched native getter programs; actual UI result, initialization and execution remain unobserved"}

    external_result_router = None
    if spec.external_result_router is not None:
        try:
            installed_game_root = metadata_path.resolve().parents[2]
        except IndexError as exc:
            raise ContractError(
                "validator=dialog_tree_external_result_router gate=game_root_derivation "
                f"expected=Endfield_Data_layout actual={metadata_path}"
            ) from exc
        external_result_router = recover_installed_lua_external_result_router(
            spec.external_result_router,
            game_root=installed_game_root,
            native_defaults=native_defaults,
        )

    game_hash = sha256_file(game_assembly_path)
    metadata_hash = sha256_file(metadata_path)
    contract = {
        "schema": "dialogTreeStaticPortFamilyContract.v3",
        "status": "validated",
        "family": spec.family,
        "nodeType": spec.node_type,
        "selectorEnumType": spec.selector_enum_type,
        "serializedSelectorPath": list(spec.serialized_selector_path),
        "staticPortMapField": {
            "name": spec.static_port_map_field,
            "token": f"0x{port_field.token:08x}",
            "type": port_field_type,
        },
        "enumMembers": enum_rows,
        "portMaps": [
            {
                "selectorValue": row["selectorValue"],
                "selectorName": row["selectorName"],
                "labels": [literal["value"] for literal in row["labels"]],
                "literalEvidence": row["labels"],
                "dictionaryAddCallVa": row["dictionaryAddCallVa"],
                "dictionaryAddContext": row["dictionaryAddContext"],
            }
            for row in initializer_rows
        ],
        "nativeMethods": native_methods,
        "staticInitializer": cctor_record,
        "validation": {
            "validator": "dialog_tree_static_port_contract",
            "status": "validated",
            "checks": validations,
            "sourceFiles": [str(game_assembly_path.resolve()), str(metadata_path.resolve())],
            "sourceHashes": {
                "GameAssembly.dll": game_hash,
                "global-metadata.dat": metadata_hash,
            },
        },
        "currentIFix": current_ifix,
        "externalResultRouter": external_result_router,
        "nativeDefaults": native_defaults,
        "selectionRule": (
            "A nonnegative DialogManager.Next(index) reaches DialogTreeController.Next(index), "
            "which uses that explicit serialized outgoing ordinal. Negative indexes use the "
            "node's GetNextIndex fallback. The shipped Lua phase router supplies a validated phase default "
            "and accepts explicit result-index overrides before calling that native continuation. "
            "Named static port-list order labels the matching serialized outgoing ordinal."
        ),
        "evidenceBoundary": (
            "This recovers authored multi-output alternatives, exact native port names, and "
            "current shipped Lua producers. It does not observe which UI result occurred, "
            "assign mission ownership, prove activation, or prove cross-file chronology. A "
            "missing producer means none was found in this complete shipped Lua corpus, not "
            "that the authored arm is permanently unreachable."
        ),
        "sources": {
            "gameAssembly": str(game_assembly_path.resolve()),
            "gameAssemblySha256": game_hash,
            "globalMetadata": str(metadata_path.resolve()),
            "globalMetadataSha256": metadata_hash,
        },
    }
    _CONTRACT_CACHE[cache_key] = contract
    return contract


def recover_static_port_family_contract(
    spec: StaticPortFamilySpec,
    *,
    game_assembly_path: Path = DEFAULT_GAME_ASSEMBLY,
    metadata_path: Path = DEFAULT_METADATA,
    ifix_contract_path: Path = DEFAULT_IFIX_CONTRACT,
) -> dict[str, Any]:
    """Recover one contract once, including memoizing deterministic failures."""
    cache_key = (
        spec,
        str(game_assembly_path.resolve()),
        str(metadata_path.resolve()),
        str(ifix_contract_path.resolve()),
    )
    cached_failure = _CONTRACT_FAILURE_CACHE.get(cache_key)
    if cached_failure is not None:
        raise ContractError(cached_failure)
    cached_contract = _CONTRACT_CACHE.get(cache_key)
    if cached_contract is not None:
        return cached_contract
    try:
        return _recover_static_port_family_contract_uncached(
            spec,
            game_assembly_path=game_assembly_path,
            metadata_path=metadata_path,
            ifix_contract_path=ifix_contract_path,
        )
    except (OSError, ValueError, ContractError) as exc:
        message = str(exc)
        _CONTRACT_FAILURE_CACHE[cache_key] = message
        raise


def selector_value(node: dict[str, Any], path: Iterable[str]) -> tuple[int, bool]:
    value: Any = node
    for key in path:
        if not isinstance(value, dict) or key not in value:
            return 0, True
        value = value[key]
    if isinstance(value, bool) or not isinstance(value, int):
        raise ContractError(f"serialized selector is not an integer: {value!r}")
    return value, False


def project_serialized_family_node(
    node: dict[str, Any],
    outgoing: list[tuple[int, str]],
    *,
    target_types: dict[str, str],
    contract: dict[str, Any],
) -> dict[str, Any]:
    """Project one serialized node through a recovered native family contract."""
    selector, defaulted = selector_value(
        node, contract.get("serializedSelectorPath") or []
    )
    enum_by_value = {
        int(row["value"]): str(row["name"])
        for row in contract.get("enumMembers") or []
    }
    if selector not in enum_by_value:
        raise ContractError(f"selector {selector} is absent from installed enum")
    port_map = next(
        (
            row
            for row in contract.get("portMaps") or []
            if int(row.get("selectorValue", -1)) == selector
        ),
        None,
    )
    labels = list((port_map or {}).get("labels") or [])
    if labels and len(labels) != len(outgoing):
        raise ContractError(
            "validator=dialog_tree_serialized_multi_output "
            "gate=named_port_count_matches_outgoing "
            f"expected={len(labels)} actual={len(outgoing)} selector={selector}"
        )
    router = contract.get("externalResultRouter") or {}
    phase_defaults = router.get("phaseDefaults") or {}
    default_index = int(phase_defaults.get(
        enum_by_value[selector],
        router.get("defaultIndex", 0),
    )) if router else None
    if default_index is not None and not 0 <= default_index < len(outgoing):
        raise ContractError(
            "validator=dialog_tree_serialized_multi_output "
            "gate=runtime_default_index_in_outgoing_range "
            f"expected=0..{len(outgoing) - 1} actual={default_index} "
            f"selector={selector} phase={enum_by_value[selector]}"
        )
    phase_producers = list(
        (router.get("producersByPhase") or {}).get(enum_by_value[selector]) or []
    )
    dynamic_producers = [
        producer for producer in phase_producers
        if producer.get("indexStatus") in {
            "dynamic_expression",
            "literal_call_paths_with_dynamic_residual",
        }
    ]

    def compact_producer(producer: dict[str, Any]) -> dict[str, Any]:
        source = producer.get("source") or {}
        return {
            "kind": producer.get("kind") or "",
            "indexExpression": producer.get("indexExpression") or "",
            "indexStatus": producer.get("indexStatus") or "",
            "possibleIndexes": producer.get("possibleIndexes") or [],
            "valueFlowEvidence": producer.get("valueFlowEvidence") or [],
            "line": producer.get("line"),
            "excerpt": producer.get("excerpt") or "",
            "sourceFile": source.get("sourceFile") or "",
            "sha256": source.get("sha256") or "",
        }

    arms = []
    for ordinal, (connection_index, target_id) in enumerate(outgoing):
        producer_evidence: list[dict[str, Any]] = []
        if default_index == ordinal:
            configured_default = enum_by_value[selector] in phase_defaults
            default_source = (
                router.get("defaultsSource") if configured_default
                else router.get("routerSource")
            ) or {}
            producer_evidence.append({
                "kind": "configured_phase_default" if configured_default else "implicit_phase_default",
                "indexExpression": str(default_index),
                "possibleIndexes": [default_index],
                "line": None,
                "excerpt": "",
                "sourceFile": default_source.get("sourceFile") or "",
                "sha256": default_source.get("sha256") or "",
            })
        producer_evidence.extend(
            compact_producer(producer)
            for producer in phase_producers
            if ordinal in (producer.get("possibleIndexes") or [])
        )
        dynamic_evidence = [compact_producer(producer) for producer in dynamic_producers]
        has_dynamic_residual = any(
            producer.get("indexStatus") == "literal_call_paths_with_dynamic_residual"
            for producer in phase_producers
            if ordinal in (producer.get("possibleIndexes") or [])
        )
        arms.append({
            "connectionOrdinal": ordinal,
            "connectionIndex": connection_index,
            "outcomeLabel": labels[ordinal] if ordinal < len(labels) else "",
            "outcomeStatus": "native_named_port" if ordinal < len(labels) else "external_index_unlabeled",
            "runtimeProducerStatus": (
                (
                    "shipped_lua_producer_with_dynamic_residual"
                    if has_dynamic_residual
                    else "shipped_lua_producer"
                )
                if producer_evidence
                else (
                    "shipped_lua_dynamic_index_unbounded"
                    if dynamic_evidence
                    else "no_shipped_lua_producer_found"
                )
            ) if router else "external_router_not_recovered",
            "runtimeProducerKinds": sorted({
                str(producer.get("kind") or "") for producer in producer_evidence
            }),
            "runtimeProducerEvidence": producer_evidence,
            "runtimeDynamicProducerEvidence": dynamic_evidence,
            "targetNodeId": target_id,
            "targetNodeType": target_types.get(target_id, ""),
        })
    projected = {
        "selectorValue": selector,
        "selectorName": enum_by_value[selector],
        "selectorDefaulted": defaulted,
        "portContractStatus": "native_named_ports" if labels else "external_index_unlabeled",
        "arms": arms,
    }
    if router:
        projected.update({
            "runtimeRouterStatus": "shipped_lua_router_validated",
            "runtimeDefaultIndex": default_index,
            "runtimeProducedArmCount": sum(
                arm["runtimeProducerStatus"] in {
                    "shipped_lua_producer",
                    "shipped_lua_producer_with_dynamic_residual",
                }
                for arm in arms
            ),
            "runtimeUnproducedArmCount": sum(
                arm["runtimeProducerStatus"] == "no_shipped_lua_producer_found" for arm in arms
            ),
            "runtimeDynamicProducerArmCount": sum(
                arm["runtimeProducerStatus"] in {
                    "shipped_lua_dynamic_index_unbounded",
                    "shipped_lua_producer_with_dynamic_residual",
                }
                for arm in arms
            ),
            "runtimeDynamicProducers": [compact_producer(row) for row in dynamic_producers],
        })
    return projected
