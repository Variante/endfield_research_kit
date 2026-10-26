"""Selected-build BlackboardDouble child reader: pooled key, bool, single.

The BuffData root reads ``addingCooldown``, ``duration`` and
``triggerInterval`` (and many Buff children read their BlackboardDouble
members) through the generic ``ReadValue`` clone whose method-spec context
names ``Beyond.Blackboard+BlackboardDouble``; the root contract proves that
call and store. This module proves the wrapper's own
``BlackboardDoubleForMemoryPack.Deserialize`` body on the installed build.

``derive`` re-reads everything from the selected image and the validator
requires the reviewed contract to equal that derivation, so no RVA, hash or
offset is carried over from a previous build:

* reader identity by name and its complete AMD64 unwind family as hashed
  code windows;
* the one-byte member header: ``cmp bpl,-1`` (null wrapper) followed by
  ``cmp bpl,<setter count>`` with the base wrapper's generated setter order
  ``blackboardKey: String``, ``useBlackboardKey: Boolean``, ``value: Single``;
* the key as an inline pooled read (reader RDI, signed Int32 index in EBX):
  the null (-2), empty (-1) and pool-lookup paths are each walked instruction
  by instruction to one join, against the symbols re-proved from the shared
  ``memorypack_pooled_string_reader_native.json`` lookup helper;
* each value's store into the wrapped instance through ``___instance`` at the
  offset the base wrapper's own generated setter body writes (the setter
  bodies are decoded; open-generic offsets are never assumed), in read order.

Wire form (tier ``exact`` for the selected normal paths): ``FF`` null, or
``03`` + Int32 pool index + one bool byte + four Single bytes. Not proved:
refill/cold error parity, string-pool selection for an export (the caller
supplies the export's pool), blackboard lookup or any evaluated value.

Run ``python -m scripts.game_data.memorypack.buff_blackboard_double_native
--write`` to regenerate the contract on the selected build.
"""
from __future__ import annotations

import json
import re
import struct
import sys
from typing import Any

from scripts.common import check_installed_native_inputs, sha256_file_upper
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import (
    native_validation_failure,
    open_native_image,
    read_reviewed_contract,
)
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.string_source_instructions import decode_string_source_instructions
from scripts.game_data.memorypack.pooled_inline_sources import _Path, _symbols, rip
from scripts.game_data.memorypack.pooled_source_helper import _contract as _pooled_contract

CONTRACT_PATH = CONTRACTS_DIR / "buff_blackboard_double_native.json"
SCHEMA = "endfield.buff-blackboard-double-native-contract.v1"
LABEL = "buffBlackboardDouble"
WRAPPER = "Beyond.MemoryPack.Beyond_Blackboard_BlackboardDoubleForMemoryPack"
BASE_WRAPPER = "Beyond.MemoryPack.Beyond_Blackboard_BlackboardParamBase_float_double_ForMemoryPack"
WRAPPED_TYPE = "Beyond.Blackboard+BlackboardDouble"
INSTANCE_TYPE = "Beyond.Blackboard+BlackboardParamBase`2<float,double>"
READ_ORDER = (("blackboardKey", "System.String"), ("useBlackboardKey", "System.Boolean"),
              ("value", "System.Single"))
EVIDENCE = {
    "exact": "Selected reader identity, complete unwind-family code windows, the FF/member-count "
             "header, the three generated base-wrapper setters with their parameter types and "
             "decoded instance-field stores, and the pooled-key null/empty/lookup paths joining "
             "one key store, then the bool and Single reads and stores in setter order.",
    "conditional": "Normal selected paths only: sufficient contiguous bytes, initialized pool, "
                   "non-null wrapper and instance. Refill, cold and throw exits are excluded.",
    "unresolved": "Which StringPool an export uses is supplied by the caller; blackboard lookup, "
                  "useBlackboardKey semantics and evaluated values are not proved.",
}


def _fail(detail: str) -> None:
    raise ValueError(f"{LABEL}.native:{detail}")


def _decode(image: Any, start: int, end: int) -> list[dict[str, Any]]:
    base = image.pe.image_base
    return decode_string_source_instructions(
        image.mapper, image.pe.bytes_at_va(base + start, end - start), base + start)


def _window(image: Any, start: int, end: int, index: int) -> dict[str, Any]:
    import hashlib
    raw = image.pe.bytes_at_va(image.pe.image_base + start, end - start)
    return {"startRva": start, "endRva": end, "sha256": hashlib.sha256(raw).hexdigest().upper(),
            "boundary": f"complete unwind-chain range {index} of the selected reader family"}


def _type(ctx: NativeReferenceContext, name: str) -> Any:
    td = ctx.index.types.get(name)
    if td is None:
        _fail(f"type={name}")
    return td


def _setter_store(image: Any, method_index: int, instance: int, type_name: str) -> int:
    """Return the instance-field offset one generated base setter writes."""
    base = image.pe.image_base
    entry = image.method_pointer_va(image.metadata.methods[method_index]) - base
    ranges = [r["runtimeTriple"][:2] for r in image.unwind_index.family(entry)["ranges"]]
    if len(ranges) != 1:
        _fail(f"setter-family={method_index}")
    rows = _decode(image, *ranges[0])
    texts = [r["text"] for r in rows]
    holder = {"System.String": "rbx", "System.Boolean": "rax", "System.Single": "rax"}[type_name]
    source = {"System.String": "rdx", "System.Boolean": "dl", "System.Single": "xmm1"}[type_name]
    loads = [i for i, t in enumerate(texts) if t == f"mov {holder}, [rcx+{instance:#x}]"]
    pattern = (r"movss \[" if type_name == "System.Single" else r"mov \[") + holder + \
        r"\+(0x[0-9a-f]+)\], " + source
    stores = [(i, re.fullmatch(pattern, t)) for i, t in enumerate(texts)]
    stores = [(i, m) for i, m in stores if m]
    if len(loads) != 1 or len(stores) != 1 or not loads[0] < stores[0][0]:
        _fail(f"setter-store={method_index}")
    if texts[loads[0] + 1] != f"test {holder}, {holder}":
        _fail(f"setter-null-guard={method_index}")
    return int(stores[0][1][1], 16)


def _unique(rows: list[dict[str, Any]], text: str, *, after: int = 0) -> int:
    found = [i for i, r in enumerate(rows) if i > after and r["text"] == text]
    if len(found) != 1:
        _fail(f"instruction={text!r}:found={len(found)}")
    return found[0]


def _key_path(rows: list[dict[str, Any]], entry: int, *, pool: int, empty: int,
              lookup: int, mode: str) -> tuple[int, list[int]]:
    """Walk one pooled-key path (reader RDI, index EBX) to its join."""
    g = _Path(rows)
    g.at = entry
    rip(g, "rax", pool)
    g.take("mov rcx, [rax+0xb8]", "cmp qword [rcx], 0x0")
    g.branch(4, False)
    g.take("cmp dword [rdi+0x30], 0x4")
    g.branch(13, True)
    g.take("mov rax, [rdi+0x50]", "mov ebx, [rax]", "mov ebp, [rdi+0x30]", "add ebp, -0x4")
    g.branch(9, True)
    g.take("add qword [rdi+0x50], 0x4", "add dword [rdi+0x40], 0x4",
           "add dword [rdi+0x44], 0x4", "mov [rdi+0x30], ebp", "cmp ebx, -0x2")
    g.branch(4, mode == "null")
    if mode == "null":
        g.take("xor ebx, ebx")
        g.jump()
    else:
        g.take("cmp ebx, -0x1")
        g.branch(4, mode == "empty")
        if mode == "empty":
            rip(g, "rbx", empty)
            g.jump()
        else:
            rip(g, "rax", pool)
            g.take("mov rcx, [rax+0xb8]", "mov rbp, [rcx]", "test rbp, rbp")
            g.branch(4, False)
            g.take("xor r8d, r8d", "mov edx, ebx", "mov rcx, rbp")
            g.call(lookup)
            g.jump()
            g.take("mov rbx, rax")
    return g.at, g.seen


def derive(image: Any, inputs: dict[str, str]) -> dict[str, Any]:
    """Re-derive every reviewed fact of the child reader from the selected image."""
    from scripts.game_data.levelscript_two_routes_native import _deserialize_method
    base = image.pe.image_base
    ctx = NativeReferenceContext(image)
    wrapper_td = _type(ctx, WRAPPER)
    if ctx.parent(WRAPPER) != BASE_WRAPPER:
        _fail("base-wrapper")
    base_td = _type(ctx, BASE_WRAPPER)
    holder = runtime_type_field_offsets(image.metadata, image.pe, image.registration, base_td.index)
    if list(holder) != ["___instance"]:
        _fail(f"base-wrapper-fields={list(holder)}")
    instance = holder["___instance"]
    holder_field = image.metadata.fields_for(base_td)[0]
    if ctx.type_name(holder_field.type_index) != INSTANCE_TYPE:
        _fail("instance-type")
    real = [f for f in image.metadata.fields_for(wrapper_td)
            if image.metadata.string(f.name_index) == "__realInstance"]
    if len(real) != 1 or ctx.type_name(real[0].type_index) != WRAPPED_TYPE:
        _fail("wrapped-type")
    setters = image.setter_methods(base_td, parameter="typeName", label=LABEL)
    if [(s[1], s[2]) for s in setters] != [(f"set___{n}__", t) for n, t in READ_ORDER]:
        _fail(f"setters={setters}")
    offsets = {name: _setter_store(image, s[0], instance, t)
               for (name, t), s in zip(READ_ORDER, setters)}

    reader = _deserialize_method(image, WRAPPER)
    if image.metadata.methods[reader[0]].declaring_type != wrapper_td.index:
        _fail("reader-owner")
    ranges = sorted(r["runtimeTriple"][:2] for r in image.unwind_index.family(reader[3])["ranges"])
    if ranges[0][0] != reader[3]:
        _fail("reader-family-entry")
    rows = [row for start, end in ranges for row in _decode(image, start, end)]
    rva = {i: int(r["va"], 16) - base for i, r in enumerate(rows)}
    null_at = _unique(rows, "cmp bpl, -0x1")
    count_at = _unique(rows, f"cmp bpl, {len(setters):#x}", after=null_at)

    fact = _pooled_contract()
    if {k: v.upper() for k, v in fact["nativeInputs"].items()} != {k: v.upper() for k, v in inputs.items()}:
        _fail("pooled-contract-native-inputs")
    symbols = _symbols(image, fact)
    entries = [i for i, r in enumerate(rows) if i > count_at and r["text"].startswith("mov rax, [rip")
               and i + 1 < len(rows) and rows[i + 1]["text"] == "mov rcx, [rax+0xb8]"]
    if not entries:
        _fail("key-entry")
    entry_va = int(rows[entries[0]]["va"], 16)
    paths = {mode: _key_path(rows, entry_va, mode=mode, **symbols)
             for mode in ("null", "empty", "lookup")}
    joins = {at for at, _ in paths.values()}
    if len(joins) != 1:
        _fail("key-join")
    g = _Path(rows)
    g.at = joins.pop()
    join_rva = g.at - base
    g.take("test r14, r14")
    g.branch(4, False)
    g.take(f"mov r8, [r14+{instance:#x}]", "test r8, r8")
    g.branch(4, False)
    barrier = g.row()
    if not bytes.fromhex(barrier["bytes"]).startswith(b"\x83\x3d"):
        _fail("key-barrier-flag")
    key_store = g.row()
    if key_store["text"] != f"mov [r8+{offsets['blackboardKey']:#x}], rbx":
        _fail("key-store")
    key_index = rows.index(key_store)

    bool_read = _unique(rows, "movzx r14d, byte [rax]", after=key_index)
    bool_store = _unique(rows, f"mov [rcx+{offsets['useBlackboardKey']:#x}], al", after=bool_read)
    if [r["text"] for r in rows[bool_store - 2:bool_store]] != ["test r14b, r14b", "setne al"] \
            or f"mov rcx, [rbx+{instance:#x}]" not in [r["text"] for r in rows[bool_read:bool_store]]:
        _fail("bool-store")
    value_read = _unique(rows, "movss xmm6, [rax]", after=bool_store)
    value_store = _unique(rows, f"movss [rax+{offsets['value']:#x}], xmm6", after=value_read)
    if f"mov rax, [rbx+{instance:#x}]" not in [r["text"] for r in rows[value_read:value_store]]:
        _fail("value-store")

    def site(i: int) -> list[Any]:
        return [rva[i], rows[i]["bytes"].replace(" ", "").upper()]

    return {
        "schema": SCHEMA,
        "status": "exact-current-build",
        "nativeInputs": dict(inputs),
        "reviewedDependencies": ["memorypack_pooled_string_reader_native.json"],
        "wrapper": WRAPPER,
        "baseWrapper": BASE_WRAPPER,
        "wrappedType": WRAPPED_TYPE,
        "readerMethod": reader,
        "codeWindows": [_window(image, s, e, i) for i, (s, e) in enumerate(ranges)],
        "setterMethods": setters,
        "instanceOffset": instance,
        "fieldOffsets": offsets,
        "nullInstruction": site(null_at),
        "memberCountInstruction": site(count_at),
        "keyPooledEntryRva": entry_va - base,
        "keyJoinRva": join_rva,
        "stores": {"blackboardKey": site(key_index), "useBlackboardKey": site(bool_store),
                   "value": site(value_store)},
        "reads": {"useBlackboardKey": site(bool_read), "value": site(value_read)},
        "wire": [{"name": "blackboardKey", "encoding": "int32-pool-index", "bytes": 4},
                 {"name": "useBlackboardKey", "encoding": "byte", "bytes": 1},
                 {"name": "value", "encoding": "single-raw", "bytes": 4}],
        "evidenceBoundary": EVIDENCE,
    }


def _contract() -> dict[str, Any]:
    value, _ = read_reviewed_contract(CONTRACT_PATH, schema=SCHEMA, status="exact-current-build",
                                      label=LABEL)
    return value


def validate_current_native_contract(*, gameassembly: Any = None, metadata: Any = None) -> dict[str, Any]:
    """Gate the installed build, then require the contract to equal a fresh derivation."""
    try:
        contract = _contract()
        pins = contract["nativeInputs"]
        gate = check_installed_native_inputs(pins["GameAssembly.dll"], pins["global-metadata.dat"],
                                             gameassembly=gameassembly, metadata=metadata)
        if gate.status != "validated":
            return {"status": gate.status, "detail": gate.detail}
        unity = gate.gameassembly.parent / "UnityPlayer.dll"
        if not unity.is_file():
            return {"status": "missing", "detail": f"{unity} is absent"}
        if sha256_file_upper(unity) != pins["UnityPlayer.dll"].upper():
            return {"status": "mismatched", "detail": "UnityPlayer.dll hash differs"}
        image = open_native_image(gate.gameassembly, gate.metadata)
        derived = json.loads(json.dumps(derive(image, pins)))
        for key in sorted(set(contract) | set(derived)):
            if contract.get(key) != derived.get(key):
                _fail(f"derivation-differs={key}")
        return {"status": "validated", "nativeInputs": pins, "wire": contract["wire"],
                "fieldOffsets": contract["fieldOffsets"], "evidenceBoundary": EVIDENCE}
    except (ValueError, KeyError, IndexError, TypeError, OSError) as error:
        return native_validation_failure(error, label=LABEL, source_path=CONTRACT_PATH)


def decode_blackboard_double(data: bytes, start: int, end: int | None = None, *,
                             strings: Any = None, label: str = LABEL) -> dict[str, Any]:
    """Decode one stored BlackboardDouble; ``end`` (when given) must be the exact end."""
    from scripts.game_data.string_pool import resolve_string_pool_index
    limit = len(data) if end is None else end
    if type(start) is not int or not 0 <= start < limit <= len(data):
        raise ValueError(f"{label}.boundary:invalid")
    if data[start] == 0xFF:
        cursor = start + 1
        if end is not None and cursor != end:
            raise ValueError(f"{label}.null:trailing-bytes")
        return {"status": "exact-null", "startOffset": start, "consumedEnd": cursor,
                "memberCount": None, "fields": [], "wholeValueExact": True}
    if data[start] != len(READ_ORDER):
        raise ValueError(f"{label}.header:expected={len(READ_ORDER)} actual={data[start]}")
    cursor = start + 1
    if limit - cursor < 9:
        raise ValueError(f"{label}.members:truncated")
    pool_index = struct.unpack_from("<i", data, cursor)[0]
    if pool_index < -2:
        raise ValueError(f"{label}.blackboardKey.poolIndex:{pool_index}")
    key: dict[str, Any] = {"name": "blackboardKey", "start": cursor, "end": cursor + 4,
                           "declaredType": "string", "poolIndex": pool_index,
                           "encoding": "int32-pool-index", "boundaryClass": "exact-cursor"}
    if pool_index in (-1, -2) or strings is not None:
        key["value"] = resolve_string_pool_index(pool_index, strings, f"{label}.blackboardKey")
        key["resolved"] = True
    else:
        key["value"] = None
        key["resolved"] = False
    cursor += 4
    flag = {"name": "useBlackboardKey", "start": cursor, "end": cursor + 1, "declaredType": "bool",
            "rawByte": data[cursor], "boundaryClass": "exact-cursor"}
    cursor += 1
    value = {"name": "value", "start": cursor, "end": cursor + 4, "declaredType": "float",
             "rawBitsHex": data[cursor:cursor + 4].hex().upper(), "boundaryClass": "exact-cursor"}
    cursor += 4
    if end is not None and cursor != end:
        raise ValueError(f"{label}.cursor:expected={end} actual={cursor}")
    return {"status": "exact", "startOffset": start, "consumedEnd": cursor, "memberCount": 3,
            "headerRange": [start, start + 1], "fields": [key, flag, value],
            "wholeValueExact": True,
            "fieldOrderSource": "selected native BlackboardDouble reader and generated base setters",
            "evidenceBoundary": "Stored child fields; pooled key index, raw bool byte and Single bits."}


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    from scripts.game_data.levelscript_two_routes_native import open_selected_build
    image, inputs = open_selected_build()
    value = derive(image, inputs)
    text = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
    if "--write" in argv:
        CONTRACT_PATH.write_bytes(text.encode("utf-8"))
        print(f"wrote {CONTRACT_PATH}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
