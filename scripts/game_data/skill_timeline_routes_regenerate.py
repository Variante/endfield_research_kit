"""Regenerate the uniform skill-timeline action-route contracts on the selected build.

Covers the contract family whose top level is exactly ``ROUTE_SHAPE``: one
AbilityAction union route (``dispatcher``), its wrapper reader and formatter
``methods``, ``memberCountInstruction``, ``codeWindows``, ``setterMethods``,
``orderedSourceReads``, ``nestedContexts`` and ``dependencies``.  The family
is found by shape, never by a file list, so a contract that grows another
section leaves the family and needs its own review.

What it re-derives from the installed build, each from a name, never from an
old address: the dispatcher row (union tag, switch table identity, target
route, usage cell, registered type) looked up by ``wrapperName``; method rows
by type and method name; complete pdata code windows plus their chained
fragments; the member-count header (the unique ``cmp <byte>, N`` in the
reader body); setter rows by declaration order; the ordered source reads; the
nested generic contexts; and ``nativeInputs``.

How the source reads are selected.  The reader-save register is read from the
prologue (the first ``mov <callee-saved>, rcx``), because the code generator
does not keep one convention (RBP on one route, RDI on another).  A reader
call is a ``call`` whose most recent ``mov rcx, ...`` loaded that register.
The reviewed reads partition their members by call target; the selected run
is the unique contiguous run of reader calls after the header whose target
partition equals that reviewed partition.  Each target group must hold one
read-kind class (``KIND_CLASSES``), every class must resolve to one target
across all regenerated contracts, and the bool/int32/byte-payload/generic
classes must equal the re-proved ``skill_custom_root_motion`` primitives,
whose bool and int32 bodies are proved again by ``prove_primitive``.

Nested contexts are the ``mov rdx, [rip]`` method-spec loads in the normal
read path; each is joined to the member whose read call consumes it.  A
context on a member the review lists must carry the reviewed type; a context
the review does not list is admitted only as a value-type (``typeKind 0x11``)
enum load consumed by that member's int32 primitive, which is an unmanaged
read and not a nested profile.  Anything else refuses.

What it never changes: field names, read kinds, member count, setter names
and types, reviewed context types, ``dependencies``, ``schema``, ``status``.
It refuses (writing nothing for that contract) when the wrapper's member list
or a setter differs, the header or the read run is absent or ambiguous, a
context does not join, or a context row carries a key it cannot derive.  A
refused contract keeps its old ``nativeInputs`` and therefore stays
``mismatched``; it is reported, never loosened.

It proves stored framing only, and it does not regenerate a dependency: the
``dependencies`` formatter-window contracts are separate reviewed data, and
the CLI reports whether each one currently authenticates on the selected
build so a consumer validator's remaining refusal is visible.
Writes require every declared dependency to pass its composed current gate;
a refused dependency preserves that route's existing contract.

Run: ``python -m scripts.game_data.skill_timeline_routes_regenerate --regenerate [--write] [--only NAME]``.
"""
from __future__ import annotations

if __name__ == "__main__" and not __package__:
    raise SystemExit("Use python -m scripts.game_data.skill_timeline_routes_regenerate")

import argparse
import copy
import hashlib
import json
import re
import struct
import sys
from pathlib import Path
from typing import Any, Callable

from scripts.game_data.buff_frontiers_regenerate import _method_row, _nested_contexts, _norm, _read_switch
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.context import generic_type_carrier
from scripts.game_data.il2cpp.rgctx_symbols import validate_claims
from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
from scripts.game_data.levelscript_two_routes_native import RouteRefused, _window, open_selected_build
from scripts.game_data.memorypack.wrapper_members import derive_from_image
from scripts.game_data.skill_custom_root_motion_regenerate import prove_primitive
from scripts.repo_paths import REPO_ROOT

ROUTE_SHAPE = frozenset((
    "codeWindows", "dependencies", "dispatcher", "evidenceBoundary", "memberCountInstruction",
    "methods", "nativeInputs", "nestedContexts", "orderedSourceReads", "schema",
    "serializedMemberCount", "setterMethods", "status",
))
BASE_SEQUENCE_SHAPE = ROUTE_SHAPE - {"dependencies", "serializedMemberCount"}
REFERENCE_CONTRACT = "skill_custom_root_motion_native.json"
KIND_CLASSES = {
    "bool-byte": "bool",
    "int32": "int32", "enum-int32": "int32", "scalar32": "int32", "enum32": "int32",
    "byte-payload": "bytes", "string": "bytes",
    "float32-bits": "float32", "raw-float32-bits": "float32",
    "list-generic": "list", "string-list": "list",
    "layer-mask-raw4": "layer-mask", "gameplay-tag32": "gameplay-tag",
    "blackboard-double": "generic", "blackboard-scalar": "generic", "blackboard-vector3": "generic",
    "curve-profile": "generic", "direction-profile": "generic", "nested-generic": "generic",
    "scalar-payload": "generic", "sequence-profile": "generic", "skill-alert-profile": "generic",
    "target-profile": "generic", "target-settings": "generic",
}
# Classes the re-proved CustomRootMotion route already fixes on this build.
REFERENCE_CLASSES = ("bool", "int32", "bytes", "generic")
_CALLEE_SAVED = ("rbx", "rbp", "rdi", "rsi", "r12", "r13", "r14", "r15")
_DERIVED_CONTEXT_KEYS = frozenset((
    "memberIndex", "instructionRva", "instructionHex", "consumerCallRva", "consumerTargetRva",
    "cellVa", "cellRva", "usageRawHex", "methodSpecIndex", "methodSpec", "argumentRawHex",
    "typeDefinition", "typeName", "generic", "typeKind",
    "classCarrier", "classInstantiation", "elementRawHex", "elementTypeDefinition", "elementTypeName",
))


def normalized_route(contract: dict[str, Any]) -> tuple[dict[str, Any], frozenset[str]]:
    """Adapt only the reviewed base-sequence shape; preserve its declared shape."""
    keys = frozenset(contract)
    if keys == ROUTE_SHAPE:
        return copy.deepcopy(contract), frozenset()
    if keys == BASE_SEQUENCE_SHAPE:
        result = copy.deepcopy(contract)
        result.update(dependencies=[], serializedMemberCount=len(contract["orderedSourceReads"]))
        return result, frozenset(("dependencies", "serializedMemberCount"))
    raise RouteRefused("shape:not-the-uniform-route-family")


def route_family() -> list[str]:
    """Contract file names whose top level is exactly ``ROUTE_SHAPE`` (reference excluded)."""
    names = []
    for path in sorted(CONTRACTS_DIR.glob("skill_*.json")):
        if path.name != REFERENCE_CONTRACT and frozenset(json.loads(path.read_bytes())) in (ROUTE_SHAPE, BASE_SEQUENCE_SHAPE):
            names.append(path.name)
    return names


def _va(value: Any) -> int:
    return int(value, 16) if isinstance(value, str) else int(value)


def _hex(row: dict[str, Any]) -> str:
    raw = row["bytes"]
    return (raw.replace(" ", "") if isinstance(raw, str) else bytes(raw).hex()).upper()


def read_kind(row: dict[str, Any]) -> str:
    return row.get("readKind", row.get("kind"))


def decode_body(image: Any, extents: dict[int, int], fragments: dict[int, Any], start: int
                ) -> list[tuple[int, int, list[dict[str, Any]]]]:
    """Decode the pdata extent and its chained fragments as ``(start, end, rows)`` spans."""
    if start not in extents:
        raise RouteRefused(f"pdata={start - image.pe.image_base:#x}")
    spans = [(start, extents[start])] + [(f, f + size) for f, size in fragments.get(start, ())]
    out = []
    for lo, hi in sorted(spans):
        rows = image.mapper.decode_x64_subset(image.pe.bytes_at_va(lo, hi - lo), lo, stop_offset=hi - lo)
        out.append((lo, hi, [dict(r, va=_va(r["va"])) for r in rows]))
    return out


def reader_register(rows: list[dict[str, Any]]) -> str:
    """The callee-saved register the prologue copies the reader (RCX) into."""
    for row in rows:
        text = row["text"]
        if text.startswith("call "):
            break
        match = re.fullmatch(r"mov (\w+), rcx", text)
        if match and match.group(1) in _CALLEE_SAVED:
            return match.group(1)
    raise RouteRefused("reader-register:no-prologue-save")


def _is_cmp_r8_imm8(row: dict[str, Any]) -> bool:
    """``80 /7 ib``: an 8-bit compare, read from the opcode, not the operand text."""
    raw = bytes.fromhex(_hex(row))
    if raw and 0x40 <= raw[0] <= 0x4F:
        raw = raw[1:]
    return len(raw) >= 3 and raw[0] == 0x80 and (raw[1] >> 3) & 7 == 7


def find_header(spans: list[tuple[int, int, list[dict[str, Any]]]], count: int) -> tuple[int, int]:
    """``(span index, row index)`` of the unique byte compare against the member count."""
    pattern = re.compile(rf"cmp [^,]+, 0x{count:x}")
    hits = [(s, i) for s, (_lo, _hi, rows) in enumerate(spans) for i, row in enumerate(rows)
            if pattern.fullmatch(row["text"]) and _is_cmp_r8_imm8(row)]
    if len(hits) != 1:
        raise RouteRefused(f"header-count={count}:matches={len(hits)}")
    return hits[0]


def reader_calls(rows: list[dict[str, Any]], register: str) -> list[dict[str, Any]]:
    """Calls whose latest RCX load since the previous call is the saved reader."""
    calls, rcx = [], None
    for row in rows:
        text = row["text"]
        if text.startswith("db "):
            raise RouteRefused(f"normal-path-undecodable={row['va']:#x}")
        if text.startswith(("mov rcx,", "lea rcx,", "xor ecx,")):
            rcx = text
        if text.startswith("call "):
            if rcx == f"mov rcx, {register}" and text.startswith("call 0x"):
                calls.append(row)
            rcx = None
    return calls


def _partition(targets: list[int]) -> frozenset[frozenset[int]]:
    groups: dict[int, set[int]] = {}
    for index, target in enumerate(targets):
        groups.setdefault(target, set()).add(index)
    return frozenset(frozenset(g) for g in groups.values())


def select_run(calls: list[dict[str, Any]], reviewed: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The unique contiguous run of reader calls grouping members like the review."""
    count = len(reviewed)
    expected = _partition([r["sourceTargetRva"] for r in reviewed])
    targets = [int(c["text"].split()[1], 16) for c in calls]
    runs = [i for i in range(len(calls) - count + 1) if _partition(targets[i:i + count]) == expected]
    if len(runs) != 1:
        raise RouteRefused(f"read-run:expected={count}:reader-calls={len(calls)}:matches={len(runs)}")
    return calls[runs[0]:runs[0] + count]


def check_read_setter_transfers(rows: list[dict[str, Any]], reads: list[dict[str, Any]],
                                setter_targets: list[int], *, base: int) -> None:
    """Bind every selected read return to its named setter on the nonnull path.

    Each complete transfer has a receiver null-test to an owned exception
    CALL/int3, zero MethodInfo, an exact return-to-argument move, and a direct
    call to the selected named setter. No intervening transform is admitted.
    """
    by = {row["va"]: index for index, row in enumerate(rows)}
    by_va = {row["va"]: row for row in rows}
    if len(setter_targets) != len(reads):
        raise RouteRefused("source-setter-count")
    for read, target in zip(reads, setter_targets):
        at = base + read["sourceCallsiteRva"]
        part = rows[by[at] + 1:by[at] + 7]
        if len(part) != 6:
            raise RouteRefused(f"source-setter-truncated:member={read['memberIndex']}")
        test, branch, method_info, transfer, receiver, call = part
        match = re.fullmatch(r"test (\w+), \1", test["text"])
        if match is None or match[1] not in _CALLEE_SAVED or receiver["text"] != f"mov rcx, {match[1]}":
            raise RouteRefused(f"source-setter-receiver:member={read['memberIndex']}")
        raw = bytes.fromhex(_hex(branch))
        if len(raw) == 2 and raw[0] == 0x74:
            destination = branch["va"] + 2 + struct.unpack_from('<b', raw, 1)[0]
        elif len(raw) == 6 and raw[:2] == b'\x0f\x84':
            destination = branch["va"] + 6 + struct.unpack_from('<i', raw, 2)[0]
        else:
            raise RouteRefused(f"source-setter-nonnull-branch:member={read['memberIndex']}")
        exception = by_va.get(destination)
        terminal = by_va.get(destination + 5)
        if exception is None or _hex(exception)[:2] != 'E8' or terminal is None or _hex(terminal) != 'CC':
            raise RouteRefused(f"source-setter-exception-owner:member={read['memberIndex']}")
        cls = KIND_CLASSES[read_kind(read)]
        moves = ({'0FB6D0', '8AD0'} if cls == 'bool' else {'0F28C8'} if cls == 'float32'
                 else {'8BD0'} if cls in ('int32', 'layer-mask', 'gameplay-tag') else {'488BD0'})
        if _hex(method_info) != '4533C0' or _hex(transfer) not in moves:
            raise RouteRefused(f"source-setter-value-transfer:member={read['memberIndex']}:class={cls}"
                               f":expected=4533C0/{sorted(moves)}:actual={_hex(method_info)}/{_hex(transfer)}")
        call_raw = bytes.fromhex(_hex(call))
        if len(call_raw) != 5 or call_raw[0] != 0xE8 or call["va"] + 5 + struct.unpack_from('<i', call_raw, 1)[0] != target:
            raise RouteRefused(f"source-setter-call:member={read['memberIndex']}")


def reference_primitives(contract: dict[str, Any] | None = None) -> dict[str, int]:
    """Class -> target RVA from the re-proved CustomRootMotion contract."""
    if contract is None:
        contract = json.loads((CONTRACTS_DIR / REFERENCE_CONTRACT).read_bytes())
    found: dict[str, set[int]] = {}
    for row in contract["orderedSourceReads"]:
        cls = KIND_CLASSES.get(read_kind(row))
        if cls in REFERENCE_CLASSES:
            found.setdefault(cls, set()).add(row["sourceTargetRva"])
    if any(len(found.get(c, ())) != 1 for c in REFERENCE_CLASSES):
        raise RouteRefused(f"reference-primitives:{ {k: sorted(v) for k, v in found.items()} }")
    return {c: next(iter(found[c])) for c in REFERENCE_CLASSES}


def _tag_text(tag: int) -> str:
    return f"0x{tag:04X}"


def _retag(value: Any, old: str, new: str) -> Any:
    if isinstance(value, str):
        return value.replace(old, new)
    if isinstance(value, dict):
        return {k: _retag(v, old, new) for k, v in value.items()}
    return value


def regenerate(contract: dict[str, Any], image: Any, inputs: dict[str, str], *,
               switch: dict[str, Any], extents: dict[int, int], fragments: dict[int, Any],
               wrappers: Any) -> dict[str, Any]:
    """Return the regenerated contract or raise ``RouteRefused``."""
    contract, adapter_keys = normalized_route(contract)
    base = image.pe.image_base
    wrapper = contract["dispatcher"]["wrapperName"]
    reviewed = contract["orderedSourceReads"]
    count = contract["serializedMemberCount"]
    if len(reviewed) != count or [r["memberIndex"] for r in reviewed] != list(range(count)):
        raise RouteRefused("reviewed-read-order")
    unknown = sorted({read_kind(r) for r in reviewed} - set(KIND_CLASSES))
    if unknown:
        raise RouteRefused(f"read-kind-class:unreviewed={unknown}")
    found = [w for w in wrappers.values() if w.name == wrapper]
    if len(found) != 1:
        raise RouteRefused(f"wrapper={wrapper}:matches={len(found)}")
    installed = [m.name for m in found[0].members]
    names = [r["fieldName"] for r in reviewed]
    if installed != names:
        raise RouteRefused(f"wrapper-members:reviewed={names}:installed={installed}")
    entries = [e for e in switch["entries"] if e.get("wrapperName") == wrapper]
    if len(entries) != 1:
        raise RouteRefused(f"dispatcher-wrapper={wrapper}:matches={len(entries)}")
    entry = entries[0]
    out = copy.deepcopy(contract)
    old_tag, new_tag = _tag_text(contract["dispatcher"]["unionTag"]), _tag_text(entry["tag"])
    dispatcher = out["dispatcher"]
    table, target, cell = _va(switch["tableVa"]), _va(entry["targetVa"]), _va(entry["usageCellVa"])
    route = contract["dispatcher"]["routeWindow"]
    dispatcher.update(
        unionTag=entry["tag"], switchTableRva=table - base, switchEntryCount=switch["entryCount"],
        switchTableSha256=hashlib.sha256(image.pe.bytes_at_va(table, switch["entryCount"] * 4)).hexdigest().upper(),
        switchTargetRva=target - base, usageCellRva=cell - base,
        usageRawHex=image.pe.bytes_at_va(cell, 8).hex().upper(),
        registeredTypeIndex=entry["registeredTypeIndex"], wrapperTypeDefinition=entry["typeDefinition"],
        routeWindow=_window(image, target, target + route["endRva"] - route["startRva"],
                            route.get("boundary", "").replace(old_tag, new_tag)),
    )
    if "boundary" not in route:
        del dispatcher["routeWindow"]["boundary"]
    out["evidenceBoundary"] = _retag(contract["evidenceBoundary"], old_tag, new_tag)
    out["methods"] = [_method_row(image, m) for m in contract["methods"]]
    out["codeWindows"] = []
    for method in out["methods"]:
        start = base + method[3]
        if start not in extents:
            raise RouteRefused(f"pdata={method[3]:#x}")
        out["codeWindows"].append(_window(image, start, extents[start], "complete pdata function extent"))
        for fragment, size in fragments.get(start, ()):
            out["codeWindows"].append(_window(image, fragment, fragment + size, "complete chained pdata fragment"))
    spans = decode_body(image, extents, fragments, base + out["methods"][0][3])
    register = reader_register(spans[0][2])
    span_index, row_index = find_header(spans, count)
    lo, hi, rows = spans[span_index]
    header = rows[row_index]
    out["memberCountInstruction"] = {"rva": header["va"] - base, "hex": _hex(header)}
    reads = select_run(reader_calls(rows[row_index + 1:], register), reviewed)
    owner = image.metadata.types[entry["typeDefinition"]]
    setters = image.setter_methods(owner, parameter="typeName", label="skillTimelineRoutesRegenerate")
    if [[_norm(x) for x in r[1:]] for r in setters] != [[_norm(x) for x in r[1:]] for r in contract["setterMethods"]]:
        raise RouteRefused("setter-names-or-types:review-required")
    out["setterMethods"] = setters
    for row, call in zip(out["orderedSourceReads"], reads):
        row.update(sourceCallsiteRva=call["va"] - base, sourceCallHex=_hex(call),
                   sourceTargetRva=int(call["text"].split()[1], 16) - base)
    all_rows = [row for _lo, _hi, part in spans for row in part]
    check_read_setter_transfers(all_rows, out["orderedSourceReads"],
        [image.method_pointer_va(image.metadata.methods[member.method_index]) for member in found[0].members], base=base)
    targets: dict[str, set[int]] = {}
    for row in out["orderedSourceReads"]:
        targets.setdefault(KIND_CLASSES[read_kind(row)], set()).add(row["sourceTargetRva"])
    if any(len(v) != 1 for v in targets.values()) or len({next(iter(v)) for v in targets.values()}) != len(targets):
        raise RouteRefused(f"class-targets:{ {k: sorted(v) for k, v in targets.items()} }")
    out["nestedContexts"] = _contexts(image, contract, out["orderedSourceReads"], header, reads)
    out["nativeInputs"] = {k: inputs[k] for k in contract["nativeInputs"]}
    for key in adapter_keys:
        del out[key]
    # Native context dataclasses may expose tuple fields. The reviewed data
    # structure is JSON, so derive the same array/key representation that is
    # published and strictly compared on the next validation.
    return contract_json(out)


def _contexts(image: Any, contract: dict[str, Any], reads: list[dict[str, Any]],
              header: dict[str, Any], calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    base = image.pe.image_base
    reviewed = contract["nestedContexts"]
    extra = sorted({k for c in reviewed for k in c} - _DERIVED_CONTEXT_KEYS)
    if extra:
        raise RouteRefused(f"nested-context-keys:underivable={extra}:review-required")
    indexed = all("memberIndex" in c for c in reviewed)
    if not indexed and any("memberIndex" in c for c in reviewed):
        raise RouteRefused("nested-context-mixed-member-index")
    normal = {"startRva": header["va"] - base, "endRva": calls[-1]["va"] + 5 - base}
    by_call = {r["sourceCallsiteRva"]: r for r in reads}
    wanted = {c["memberIndex"]: c["typeName"] for c in reviewed} if indexed else {}
    shapes = {c["memberIndex"]: list(c) for c in reviewed} if indexed else {}
    if indexed and len(wanted) != len(reviewed):
        raise RouteRefused("nested-context-duplicate-member:review-required")
    out = []
    for context in _nested_contexts(image, normal):
        read = by_call.get(context["consumerCallRva"])
        if read is None:
            raise RouteRefused(f"nested-context-unjoined={context['instructionRva']:#x}:{context['typeName']}")
        member = read["memberIndex"]
        expected = (next((c for c in reviewed if c["memberIndex"] == member), None)
                    if indexed else (reviewed[len(out)] if len(out) < len(reviewed) else None))
        if expected and context["typeName"] == expected["typeName"]:
            if indexed and context["typeName"] != wanted.pop(member):
                raise RouteRefused(f"nested-context-type:member={member}:installed={context['typeName']}")
            row = dict(context, memberIndex=member, cellRva=context["cellVa"] - base)
            if expected.get("classCarrier") is not None:
                argument = bytes.fromhex(context["argumentRawHex"])
                if argument[10] != 0x15:
                    raise RouteRefused(f"nested-context-generic-kind:member={member}")
                pointer = struct.unpack_from("<Q", argument)[0]
                carrier_raw = image.pe.bytes_at_va(pointer, 32)
                base_raw = image.pe.bytes_at_va(struct.unpack_from("<Q", carrier_raw)[0], 16)
                instance = image.instantiations.resolve(context["methodSpec"][2])
                carrier = generic_type_carrier(argument, carrier_raw, base_raw,
                    type_pointer=instance.arguments[0].type_pointer_va,
                    type_count=len(image.metadata.types), source=str(image.gameassembly))
                nested = image.instantiations.resolve_pointer(carrier["classInstantiationPointerVa"])
                if len(nested.arguments) != 1:
                    raise RouteRefused(f"nested-context-element-arity:member={member}")
                element = bytes.fromhex(nested.arguments[0].raw_type_record_hex)
                if element[10] != 0x12 or element[11] & 0x7f:
                    raise RouteRefused(f"nested-context-element-reference:member={member}")
                definition = struct.unpack_from("<Q", element)[0]
                row.update(classCarrier=carrier, classInstantiation=nested.as_dict(),
                    elementRawHex=element.hex().upper(), elementTypeDefinition=definition,
                    elementTypeName=image.type_name(definition))
                if row["elementTypeName"] != expected["elementTypeName"]:
                    raise RouteRefused(f"nested-context-element-identity:member={member}")
            out.append({k: row[k] for k in expected})
        elif not (context["typeKind"] == 0x11 and KIND_CLASSES[read_kind(read)] == "int32"):
            raise RouteRefused(f"nested-context-unreviewed:member={member}:{context['typeName']}")
    if wanted or len(out) != len(reviewed):
        raise RouteRefused(f"nested-context-missing:{sorted(wanted)}")
    if indexed and [c["memberIndex"] for c in out] != [c["memberIndex"] for c in reviewed]:
        raise RouteRefused("nested-context-order")
    return out


def check_family_primitives(image: Any, results: dict[str, dict[str, Any]], reference: dict[str, int]) -> None:
    """Every class resolves to one target across contracts, equal to the reference ones."""
    targets: dict[str, set[int]] = {}
    for contract in results.values():
        for row in contract["orderedSourceReads"]:
            targets.setdefault(KIND_CLASSES[read_kind(row)], set()).add(row["sourceTargetRva"])
    for cls, found in targets.items():
        if len(found) != 1:
            raise RouteRefused(f"family-primitive={cls}:{sorted(found)}")
        if cls in reference and found != {reference[cls]}:
            raise RouteRefused(f"family-primitive={cls}:installed={sorted(found)}:reference={reference[cls]}")
    base = image.pe.image_base
    for cls, kind in (("bool", "bool-byte"), ("int32", "int32")):
        if cls in targets:
            prove_primitive(image, base + next(iter(targets[cls])), kind)
    if "float32" in targets:
        from scripts.game_data.memorypack import buff_ec_profiles_native as ec
        from scripts.game_data.memorypack.buff_profile_source import float32_program
        target = base + next(iter(targets["float32"]))
        _family, _windows, rows = ec.family(image, target - base)
        float32_program(rows, target, ec.source_offsets(image))


def dependency_status(image: Any, contract: dict[str, Any]) -> dict[str, str]:
    """Report complete allowlisted dependency proofs and exact parent joins."""
    from scripts.game_data.memorypack.skill_timeline_dependencies import validate_dependency
    out = {}
    for dependency in contract.get("dependencies", []):
        try:
            validate_dependency(image, contract, dependency, label=dependency["path"])
            out[dependency["path"]] = "validated"
        except (ValueError, OSError, KeyError, IndexError, TypeError) as error:
            out[dependency["path"]] = f"mismatched:{error}"
    return out


def regenerate_family(names: list[str], *, opener: Callable[[], tuple[Any, dict[str, str]]] = open_selected_build
                      ) -> tuple[Any, dict[str, dict[str, Any]], dict[str, str]]:
    """Return ``(image, regenerated by name, refusal by name)``."""
    image, inputs = opener()
    reference = json.loads((CONTRACTS_DIR / REFERENCE_CONTRACT).read_bytes())
    if {k: str(v).upper() for k, v in reference["nativeInputs"].items()} != \
            {k: str(inputs[k]).upper() for k in reference["nativeInputs"]}:
        return image, {}, {n: "reference-contract:not-regenerated-for-selected-build" for n in names}
    context = dict(switch=_read_switch(image), extents=dict(image.mapper.pdata_function_extents(image.pe)),
                   fragments={}, wrappers=image.memorypack_wrappers)
    results, refused = {}, {}
    for name in names:
        try:
            contract = json.loads((CONTRACTS_DIR / name).read_bytes())
            for method in contract["methods"]:
                selected = _method_row(image, method)
                start = selected[3]
                context['fragments'][image.pe.image_base + start] = [
                    (image.pe.image_base + lo, hi - lo)
                    for lo, hi, _ in (r["runtimeTriple"] for r in image.unwind_index.family(start)["ranges"])
                    if lo != start]
            results[name] = regenerate(contract, image, inputs, **context)
        except (RouteRefused, ValueError, KeyError, IndexError, TypeError, OSError, StopIteration, struct.error) as error:
            refused[name] = str(error)
    if results:
        try:
            check_family_primitives(image, results, reference_primitives(reference))
        except (RouteRefused, ValueError) as error:
            refused.update({n: f"family:{error}" for n in results})
            results = {}
    return image, results, refused


def contract_json(value: dict[str, Any]) -> dict[str, Any]:
    """Represent a derived declaration exactly as its persisted JSON."""
    return json.loads(json.dumps(value))


def _reviewed_inputs() -> dict[str, str]:
    """Bookend the discoverable reviewed contract set, including dependencies.

    These are run-local input receipts, never a pin on a tracked file. A new,
    removed or edited declaration during derivation must not be overwritten or
    reported as the input to a successful current validation.
    """
    return {str(path.resolve()): hashlib.sha256(path.read_bytes()).hexdigest().upper()
            for path in sorted(CONTRACTS_DIR.glob("*.json"))}


def _require_reviewed_inputs(before: dict[str, str]) -> None:
    after = _reviewed_inputs()
    changed = sorted(path for path in before.keys() | after.keys()
                     if before.get(path) != after.get(path))
    if changed:
        path = changed[0]
        raise RouteRefused(f"reviewed-input-drift:source={path}:"
                           f"expected={before.get(path)}:actual={after.get(path)}:"
                           f"changedCount={len(changed)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--regenerate", action="store_true")
    mode.add_argument("--validate", action="store_true", help="rederive and compare current reviewed contracts without writing")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--only", action="append", help="contract file name (repeatable)")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    if args.write and not args.regenerate:
        parser.error("--write requires --regenerate")
    family = route_family()
    names = args.only or family
    if set(names) - set(family):
        parser.error(f"not in the route family: {sorted(set(names) - set(family))}")
    if args.report and not args.report.resolve().is_relative_to((REPO_ROOT / "reports").resolve()):
        parser.error("--report must be below the repository reports/ directory")
    try:
        reviewed_inputs = _reviewed_inputs()
        image, results, refused = regenerate_family(names)
    except (RouteRefused, ValueError, KeyError, IndexError, TypeError, OSError, RuntimeError, struct.error) as error:
        rows = [{"contract": name, "refused": f"selected-build-initialization:{error}", "written": False}
                for name in names]
        for row in rows:
            print(json.dumps(row))
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps({"contracts": rows}, indent=2) + "\n", encoding="utf-8")
        return 1
    selected_inputs = next(iter(results.values()))["nativeInputs"] if results else None
    if args.validate:
        for name in list(results):
            try:
                reviewed = json.loads((CONTRACTS_DIR / name).read_bytes())
                validate_claims(reviewed, results[name], label=name + ".current")
                validate_claims(results[name], reviewed, label=name + ".declaration")
            except (ValueError, OSError) as error:
                refused[name] = "current-contract-diff:" + str(error)[:1400]
                del results[name]
    dependencies = {name: dependency_status(image, value) for name, value in results.items()}
    if args.write or args.validate:
        for name in list(results):
            failed = {path: status for path, status in dependencies[name].items() if status != "validated"}
            if failed:
                refused[name] = "dependencies:" + json.dumps(failed, sort_keys=True)
                del results[name]
    if (args.write or args.validate) and results:
        try:
            inputs = next(iter(results.values()))["nativeInputs"]
            _publication_gate(image, inputs)
            _require_reviewed_inputs(reviewed_inputs)
        except (RouteRefused, ValueError, OSError) as error:
            refused.update({name: f"publication:{error}" for name in results})
            results = {}
    rows = []
    for name in names:
        row: dict[str, Any] = {"contract": name, "refused": refused.get(name),
                               "written": bool(args.write and name in results)}
        if args.validate:
            row["validated"] = name in results
        if name in results:
            row["unionTag"] = _tag_text(results[name]["dispatcher"]["unionTag"])
            row["dependencies"] = dependencies[name]
            if args.write:
                text = json.dumps(results[name], indent=2, ensure_ascii=False) + "\n"
                (CONTRACTS_DIR / name).write_bytes(text.replace("\n", "\r\n").encode("utf-8"))
        print(json.dumps(row))
        rows.append(row)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps({"nativeInputs": selected_inputs, "contracts": rows}, indent=2) + "\n", encoding="utf-8")
    return 1 if refused else 0


if __name__ == "__main__":
    sys.exit(main())
