"""Prove each reached derived-plan wrapper's header count and read order natively.

``derived_plans`` frames a whole-record family from metadata alone: the member
list is the wrapper's setters in method-index order, and the header the plan
checks is that list's length.  Reaching physical EOF with every identifier
matching its filename shows the plan is self-consistent on the corpus; the
Skill decoder's policy is that such an EOF never promotes a row, because none
of it was read out of the generated reader that actually consumes the bytes.

This audit reads that reader.  For every wrapper a family's records reach with
a non-null body, it opens the wrapper's generated ``Deserialize`` (resolved by
type and method name on the selected build, plus every chained ``.pdata``
fragment the body owns) and checks two build-independent claims:

* ``headerCount`` -- every ``MemoryPackSerializationException.
  ThrowInvalidPropertyCount`` call the body makes passes, as its second
  argument (``dl``/``edx``), the same immediate, and that immediate equals the
  plan's member count.  MemoryPack's generated reader throws exactly when the
  stored header exceeds the count it was generated for, so the immediate is
  the reader's own declared count, not a pattern match on a compare;
* ``setterOrder`` -- the order in which the body first writes each member
  follows the plan's member order, and every *own* member is written.  A
  write is a call of the member's generated setter or, where the compiler
  inlined it, a store to the member's field: the field offset comes from the
  selected build's runtime field-offset table for the wrapped type, and the
  store must go through a register the body loaded from the wrapper's
  instance field (or got from its ``get___instance`` accessor), or -- for a
  wrapped value type -- through the wrapper itself.  Inherited members are
  often stored into the base type's fields and are only counted as
  ``membersUnobserved``; the base wrapper's own body proves them.

A wrapper with no generated ``Deserialize`` of its own (a raw struct, a union
base whose tag the union formatter reads) is reported as ``noOwnBody``: the
claims do not apply to it, and ``derived_plans`` frames it by a different rule.

What this proves: the plan's member count and own-member write order match
the selected build's generated reader for each passing wrapper (tier
``direct``).  The walk is linear over address-ordered rows, keeping only
callee-saved register roles across jumps; it does not prove which reader
primitive each member uses.
What it does not prove: the plan's per-member read *kinds* (fixed width,
string, nested object, list, union) -- those stay ``structuralOnly`` from
metadata types -- the union tag tables (``union_dispatch`` reads them), what
any member means, or any runtime value.  A file is ``nativeOrderChecked``
only when every wrapper it reaches passes both claims; that is a statement
about this audit's two claims, never a promotion of the file's framing.

Nothing build-locked is recorded: bodies, setters and the throw helper are
resolved by name on whichever build is installed, behind the shared native
input gate, so a client update re-proves rather than fails a pin.
"""
from __future__ import annotations

import argparse
import json
import re
import struct
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.il2cpp.body_claims import BodyIndex, ClaimError
from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets
from scripts.game_data.memorypack.buff_actions import Unsupported
from scripts.game_data.memorypack.derived_plans import (
    WHOLE_RECORD_FAMILIES,
    load_registry,
)
from scripts.game_data.memorypack.derived_values import ValueReader
from scripts.game_data.memorypack.wrapper_members import (
    INSTANCE_FIELD_NAMES,
    WrapperType,
    derive_from_image,
)
from scripts.game_data.string_pool import export_string_pool
from scripts.repo_paths import REPO_ROOT as REPO
from scripts.source_paths import ExportLayout

SCHEMA = "endfield.memorypack-wrapper-body-audit.v1"
DEFAULT_OUTPUT = REPO / "reports/animestudio/wrapper_body_audit_latest.json"
THROW_TYPE = "MemoryPack.MemoryPackSerializationException"
THROW_METHOD = "ThrowInvalidPropertyCount"
DESERIALIZE = "Deserialize"
NULL_MARKER = 0xFF
# How far back from a throw call the expected-count argument may be loaded.
# The argument setup is a handful of moves; a longer walk would cross into a
# different block's register state.
ARGUMENT_WINDOW = 8
_EXPECTED_IMMEDIATE = re.compile(r"mov (?:dl|edx), (0x[0-9a-f]+)$")
_BLOCK_END = re.compile(r"(?:call|jmp|jcc|j[a-z]+|ret)\b")


class AuditRefused(RuntimeError):
    """The selected build or export cannot support the audit."""


def _va(row: dict[str, Any]) -> int:
    value = row["va"]
    return int(value, 16) if isinstance(value, str) else int(value)


def _call_target(text: str) -> int | None:
    parts = text.split()
    if len(parts) == 2 and parts[0] == "call" and parts[1].startswith("0x"):
        return int(parts[1], 16)
    return None


def expected_count_argument(rows: list[dict[str, Any]], call_index: int) -> int | None:
    """The ``dl``/``edx`` immediate loaded for the call at ``call_index``.

    Walks back inside the call's own block only: the first instruction that
    writes ``dl``/``edx`` decides, and any earlier call, jump or return ends the
    walk unresolved, because ``edx`` is volatile across calls.
    """
    for row in reversed(rows[max(0, call_index - ARGUMENT_WINDOW):call_index]):
        text = row["text"]
        match = _EXPECTED_IMMEDIATE.match(text)
        if match:
            return int(match.group(1), 16)
        if text in ("xor edx, edx", "xor dl, dl"):
            return 0
        if re.search(r"\b(?:edx|dl|dx|rdx)\b", text.split(",")[0]) and not text.startswith(("cmp ", "test ")):
            return None
        if _BLOCK_END.match(text):
            return None
    return None


_REGISTER_FAMILIES = (
    ("rax", "eax", "ax", "al"), ("rbx", "ebx", "bx", "bl"), ("rcx", "ecx", "cx", "cl"),
    ("rdx", "edx", "dx", "dl"), ("rsi", "esi", "si", "sil"), ("rdi", "edi", "di", "dil"),
    ("rbp", "ebp", "bp", "bpl"),
) + tuple((f"r{n}", f"r{n}d", f"r{n}w", f"r{n}b") for n in range(8, 16))
_REGISTER = {alias: family[0] for family in _REGISTER_FAMILIES for alias in family}
_VOLATILE = {"rax", "rcx", "rdx", "r8", "r9", "r10", "r11"}
_STORE = re.compile(r"(?:mov|movss|movsd|movups|movdqu|movaps|movq|movd) \[(\w+)(?:\+0x([0-9a-f]+))?\], ")


def _offsets(image: Any, definition: int) -> dict[str, int]:
    try:
        return runtime_type_field_offsets(image.metadata, image.pe, image.registration, definition)
    except RuntimeError:
        return {}


def _chain(wrappers: dict[str, WrapperType], wrapper: WrapperType) -> list[WrapperType]:
    chain = [wrapper]
    while chain[-1].parent_name in wrappers and len(chain) < 32:
        chain.append(wrappers[chain[-1].parent_name])
    return chain


_DEFINITIONS: dict[int, dict[str, int]] = {}


def _definition_by_name(image: Any) -> dict[str, int]:
    table = _DEFINITIONS.get(id(image))
    if table is None:
        table = {}
        for index in range(len(image.metadata.types)):
            table.setdefault(image.type_name(index), index)
        _DEFINITIONS[id(image)] = table
    return table


class _WriteSites:
    """Where one wrapper's body can write a member, resolved on the selected build.

    ``instance`` holds the wrapper chain's instance-field offsets (a derived
    wrapper caches the cast instance beside its base's), ``getters`` the
    pointers of their generated ``get_<instance field>`` accessors, and
    ``fields`` the wrapped type's member field offsets -- for a wrapped value
    type, already rebased to the struct stored inline in the wrapper.  Field
    offsets of the most-derived wrapped type cover inherited members too,
    because a derived class keeps its base's field offsets.
    """

    def __init__(self, image: Any, bodies: BodyIndex, wrappers: dict[str, WrapperType],
                 wrapper: WrapperType) -> None:
        chain = _chain(wrappers, wrapper)
        self.instance: set[int] = set()
        instance_names: set[str] = set()
        for item in chain:
            for name, offset in _offsets(image, item.type_definition).items():
                if name in INSTANCE_FIELD_NAMES:
                    self.instance.add(offset)
                    instance_names.add(name)
        chain_names = {item.name for item in chain}
        # The accessor is named after the property, which need not match the
        # backing field (``__realInstance`` is read through ``get___instance``).
        wanted = {f"get_{name}" for name in INSTANCE_FIELD_NAMES}
        self.getters = {
            pointer for pointer, entries in bodies.names_by_pointer.items()
            if any(entry.get("type") in chain_names and entry.get("method") in wanted
                   for entry in entries)
        }
        self.value_type = wrapper.wrapped_is_value_type
        definition = _definition_by_name(image).get(wrapper.wrapped_type or "")
        offsets = _offsets(image, definition) if definition is not None else {}
        base = 0
        if self.value_type:
            # A boxed value type's offsets count the 0x10 object header; inline
            # in the wrapper the struct starts at the instance field itself.
            base = (min(self.instance) - 0x10) if len(self.instance) == 1 else None
        self.fields: dict[int, str] = {}
        if base is not None:
            seen: Counter[int] = Counter()
            for member in wrapper.members:
                if member.name in offsets:
                    seen[offsets[member.name] + base] += 1
                    self.fields[offsets[member.name] + base] = member.name
            for offset, count in seen.items():
                if count > 1:
                    self.fields.pop(offset, None)


def member_write_order(
    image: Any, bodies: BodyIndex, wrappers: dict[str, WrapperType], wrapper: WrapperType,
    rows: list[dict[str, Any]],
) -> list[str]:
    """Members in the order the body first writes them.

    A write is either a call to the member's generated setter or, where the
    compiler inlined that setter, a store into the member's field.  For a
    wrapped reference type the store goes through a register holding the
    wrapped object (loaded from an instance field, or returned by an instance
    getter); for a wrapped value type it goes through a register holding the
    wrapper itself, which the body dereferences out of its by-ref value
    argument (``rdx`` at entry).
    """
    metadata = image.metadata
    setter_member = {
        image.method_pointer_va(metadata.methods[member.method_index]): member.name
        for member in wrapper.members
    }
    sites = _WriteSites(image, bodies, wrappers, wrapper)
    state: dict[str, str] = {"rdx": "ref"}
    written: list[str] = []

    def record(name: str | None) -> None:
        if name is not None and name not in written:
            written.append(name)

    for instruction in rows:
        text = instruction["text"]
        target = _call_target(text)
        if target is not None:
            record(setter_member.get(target))
            for register in _VOLATILE:
                state.pop(register, None)
            if target in sites.getters:
                state["rax"] = "object"
            continue
        if text.startswith("jmp ") or text.startswith("ret"):
            # Rows are in address order, so the next block may be entered from
            # elsewhere.  Generated readers keep their roles (reader, value
            # ref, wrapper) in callee-saved registers for the whole body, so
            # only the volatile ones are forgotten here.
            for register in _VOLATILE:
                state.pop(register, None)
            continue
        store = _STORE.match(text)
        if store:
            holder = state.get(_REGISTER.get(store.group(1), ""))
            offset = int(store.group(2) or "0", 16)
            if holder == ("wrapper" if sites.value_type else "object"):
                record(sites.fields.get(offset))
            elif holder is not None and holder.startswith("field:"):
                # A reference store goes through ``lea rcx, [holder+field]``
                # so the write barrier receives the slot address.
                record(sites.fields.get(int(holder[6:]) + offset))
            continue
        parts = text.split(None, 1)
        if len(parts) != 2 or parts[0] in ("cmp", "test", "push") or parts[0].startswith("j"):
            continue
        operands = [item.strip() for item in parts[1].split(",", 1)]
        destination = _REGISTER.get(operands[0])
        if destination is None:
            continue
        source = operands[1] if len(operands) == 2 else ""
        produced = None
        if parts[0] == "lea":
            memory = re.fullmatch(r"\[(\w+)\+0x([0-9a-f]+)\]", source)
            if memory and state.get(_REGISTER.get(memory.group(1), "")) == (
                    "wrapper" if sites.value_type else "object"):
                produced = f"field:{int(memory.group(2), 16)}"
        elif parts[0] == "mov":
            if source in _REGISTER and _REGISTER[source] == source:
                produced = state.get(source)
            else:
                memory = re.fullmatch(r"\[(\w+)(?:\+0x([0-9a-f]+))?\]", source)
                if memory:
                    held = state.get(_REGISTER.get(memory.group(1), ""))
                    offset = int(memory.group(2) or "0", 16)
                    if held == "ref" and offset == 0:
                        produced = "wrapper"
                    elif held == "wrapper" and offset in sites.instance:
                        produced = "object"
        if produced is None:
            state.pop(destination, None)
        else:
            state[destination] = produced
    return written


def audit_wrapper(
    bodies: BodyIndex, image: Any, wrappers: dict[str, WrapperType], wrapper: WrapperType,
) -> dict[str, Any]:
    """Both claims for one wrapper, with bounded expected-versus-actual detail."""
    row: dict[str, Any] = {
        "wrapper": wrapper.name,
        "typeDefinition": wrapper.type_definition,
        "planMemberCount": wrapper.serialized_member_count,
    }
    if not wrapper.own_deserialize:
        return dict(row, status="noOwnBody")
    try:
        body = bodies.body(wrapper.name, DESERIALIZE)
    except ClaimError as error:
        return dict(row, status="bodyUnresolved", detail=str(error))
    primary = list(body.rows)
    rows = primary + list(body.fragment_rows)
    names = bodies.names_by_pointer

    expected: list[int | None] = []
    for index, instruction in enumerate(rows):
        target = _call_target(instruction["text"])
        if target is None:
            continue
        if any(entry.get("type") == THROW_TYPE and entry.get("method") == THROW_METHOD
               for entry in names.get(target, ())):
            expected.append(expected_count_argument(rows, index))
    counts = sorted({value for value in expected if value is not None})
    if not expected:
        header = {"status": "noThrowCall"}
    elif None in expected or len(counts) != 1:
        header = {"status": "ambiguous", "expectedArguments": expected[:8]}
    elif counts[0] != wrapper.serialized_member_count:
        header = {"status": "mismatched", "native": counts[0],
                  "plan": wrapper.serialized_member_count}
    else:
        header = {"status": "proved", "native": counts[0], "throwCalls": len(expected)}

    called = member_write_order(image, bodies, wrappers, wrapper, primary)
    plan_order = [member.name for member in wrapper.members]
    filtered = [name for name in plan_order if name in called]
    own_names = {member.name for member in wrapper.own_members}
    own_missing = [name for name in plan_order if name in own_names and name not in called]
    if called != filtered:
        order = {"status": "mismatched", "bodyOrder": called[:16], "planOrder": filtered[:16]}
    elif own_missing:
        order = {"status": "ownMemberNotWritten", "missing": own_missing[:16]}
    else:
        order = {"status": "proved", "membersWritten": len(called),
                 "membersUnobserved": len(plan_order) - len(called)}
    status = "proved" if header["status"] == order["status"] == "proved" else "refused"
    return dict(row, status=status, headerCount=header, setterOrder=order)


class _ReachReader(ValueReader):
    """A value reader that records every wrapper body it opens non-null."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.reached: set[int] = set()

    def _value_object(self, definition: int, depth: int) -> Any:
        if self.pos < len(self.data) and self.peek() != NULL_MARKER:
            self.reached.add(definition)
        return super()._value_object(definition, depth)


def reach_census(directory: Path, definition: int, registry: Any, strings: Any) -> dict[str, Any]:
    """Which wrappers each closed file reaches; refused files are counted, not read."""
    per_file: dict[str, set[int]] = {}
    refused: list[dict[str, str]] = []
    for path in sorted(directory.glob("*.json")):
        data = path.read_bytes()
        reader = _ReachReader(data, path.name, registry=registry, strings=strings)
        try:
            reader.read_record(definition)
        except (Unsupported, ValueError, IndexError, struct.error) as error:
            refused.append({"file": path.stem, "detail": str(error)[:160]})
            continue
        if reader.pos != len(data):
            refused.append({"file": path.stem, "detail": f"short-of-eof:{reader.pos}/{len(data)}"})
            continue
        per_file[path.stem] = reader.reached
    return {"perFile": per_file, "refused": refused}


def build(family: str, output: Path, export_root: Path | None = None) -> dict[str, Any]:
    started = time.perf_counter()
    output = output.resolve()
    if (REPO / "reports").resolve() not in output.parents:
        raise AuditRefused(f"output-must-be-under={REPO / 'reports'}")
    type_name = WHOLE_RECORD_FAMILIES.get(family)
    if type_name is None:
        raise AuditRefused(f"family={family}:not-a-whole-record-family")
    gate = check_installed_native_inputs()
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise AuditRefused(f"native-inputs:{gate.status}:{gate.detail}")
    registry, plan_audit = load_registry(gameassembly=gate.gameassembly, metadata=gate.metadata)
    definition = registry.named_roots.get(type_name)
    if definition is None:
        raise AuditRefused(f"family={family}:unplanned:{plan_audit.get('status')}")
    layout = ExportLayout(root=export_root) if export_root is not None else ExportLayout.configured()
    directory = layout.json_dir / family
    if not directory.is_dir():
        raise AuditRefused(f"missing-export={directory}")
    strings = export_string_pool(layout.json_dir)
    census = reach_census(directory, definition, registry, strings)

    image = open_native_image(gate.gameassembly, gate.metadata)
    wrappers = derive_from_image(image)
    bodies = BodyIndex(image)
    by_name = {wrapper.name: wrapper for wrapper in wrappers.values()}
    files_by_wrapper: Counter[int] = Counter()
    for reached in census["perFile"].values():
        files_by_wrapper.update(reached)
    rows: dict[int, dict[str, Any]] = {}
    for wrapper_definition in files_by_wrapper:
        wrapper = wrappers.get(wrapper_definition)
        rows[wrapper_definition] = (
            {"typeDefinition": wrapper_definition, "status": "notAWrapper"}
            if wrapper is None else audit_wrapper(bodies, image, by_name, wrapper))
        rows[wrapper_definition]["files"] = files_by_wrapper[wrapper_definition]

    def passes(item: int, claim: str | None) -> bool:
        row = rows[item]
        if row["status"] == "noOwnBody":
            return True
        if claim is None:
            return row["status"] == "proved"
        return row.get(claim, {}).get("status") == "proved"

    header_checked = [stem for stem, reached in census["perFile"].items()
                      if all(passes(item, "headerCount") for item in reached)]
    checked = [stem for stem, reached in census["perFile"].items()
               if all(passes(item, None) for item in reached)]
    statuses = Counter(row["status"] for row in rows.values())
    refusals = sorted((row for row in rows.values() if row["status"] not in ("proved", "noOwnBody")),
                      key=lambda row: (-row["files"], row.get("wrapper", "")))
    report = {
        "schema": SCHEMA,
        "family": family,
        "rootType": type_name,
        "nativeInputs": {"gameAssembly": str(gate.gameassembly), "metadata": str(gate.metadata),
                         "status": gate.status},
        "stringPool": strings is not None,
        "summary": {
            "files": len(census["perFile"]) + len(census["refused"]),
            "framedToEof": len(census["perFile"]),
            "refused": len(census["refused"]),
            "nativeHeaderChecked": len(header_checked),
            "nativeOrderChecked": len(checked),
            "wrappersReached": len(rows),
            "wrapperStatuses": dict(sorted(statuses.items())),
            "elapsedSeconds": round(time.perf_counter() - started, 3),
        },
        "refusedFiles": census["refused"][:20],
        "wrapperRefusals": refusals,
        "wrappers": sorted(rows.values(), key=lambda row: (-row["files"], row.get("wrapper", ""))),
        "boundary": (
            "headerCount and setterOrder are direct reads of the selected build's generated "
            "Deserialize bodies. Per-member read kinds stay structuralOnly from metadata, a "
            "nativeOrderChecked file is not a promoted framing, and no stored value is a "
            "runtime value."
        ),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--family", default="SkillData", choices=sorted(WHOLE_RECORD_FAMILIES))
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--export-root", type=Path, default=None)
    args = parser.parse_args(argv)
    try:
        report = build(args.family, args.output, args.export_root)
    except AuditRefused as error:
        print(json.dumps({"status": "refused", "detail": str(error)}), file=sys.stderr)
        return 1
    summary = report["summary"]
    print(json.dumps(summary, sort_keys=True))
    for row in report["wrapperRefusals"][:10]:
        print(f"refused {row['files']:5d} {row.get('wrapper', row['typeDefinition'])}: "
              f"{row['status']} header={row.get('headerCount')} order={row.get('setterOrder')}")
    return 0 if summary["nativeOrderChecked"] == summary["files"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
