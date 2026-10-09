"""Source-bound named AnimationCurve storage, with independent native copies.

The selected formatter copies two wrap words and seven words per Keyframe.
Callback resolution names establish stored destinations, not evaluation or
execution of Unity callbacks. Callers still prove each parent typed join.
"""
from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets, runtime_type_name
from scripts.game_data.il2cpp.context import generic_type_carrier
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError
from scripts.game_data.memorypack.wrapper_members import unmanaged_value_sizes_from_image

LABEL = "memorypackAnimationCurve"
CONTRACT_PATH = CONTRACTS_DIR / "memorypack_animation_curve_native.json"


def formatter_curve_type(image: Any) -> dict[str, Any]:
    """Resolve the actual closed argument owned by this selected formatter.

    The caller authenticates the selected image and curve child contract.
    The generic base relationship proves a type join, not curve evaluation.
    """
    contract=_contract();method=image.metadata.methods[contract['sourceMethod'][0]]
    formatter=image.metadata.types[method.declaring_type]
    if image.type_name(formatter.index)!=contract['sourceMethod'][1]:
        _fail('formatter-owner',contract['sourceMethod'][1],image.type_name(formatter.index))
    table=int(image.registration['types'],16);pointer=image.pe.u64_at_va(table+formatter.parent_index*8)
    raw=image.pe.bytes_at_va(pointer,16);carrier=image.pe.bytes_at_va(struct.unpack_from('<Q',raw)[0],32)
    base_raw=image.pe.bytes_at_va(struct.unpack_from('<Q',carrier)[0],16)
    owned=generic_type_carrier(raw,carrier,base_raw,type_pointer=pointer,type_count=len(image.metadata.types),source=str(image.gameassembly))
    if image.type_name(owned['baseDefinitionIndex'])!='MemoryPack.MemoryPackFormatter`1':
        _fail('formatter-base','MemoryPack.MemoryPackFormatter`1',owned)
    instance=image.instantiations.resolve_pointer(owned['classInstantiationPointerVa'])
    if len(instance.arguments)!=1:_fail('formatter-arity',1,len(instance.arguments))
    argument=bytes.fromhex(instance.arguments[0].raw_type_record_hex)
    if argument[10:12]!=b'\x12\0':_fail('formatter-reference-argument','named reference type',argument.hex())
    definition=struct.unpack_from('<Q',argument)[0];name=image.type_name(definition)
    if name!='UnityEngine.AnimationCurve':_fail('formatter-curve-type','UnityEngine.AnimationCurve',name)
    return {'typeDefinition':definition,'typeName':name,'formatterTypeDefinition':formatter.index,
            'baseCarrier':owned,'classInstantiation':instance.as_dict()}


def _contract() -> dict[str, Any]:
    value, _ = read_reviewed_contract(CONTRACT_PATH,
        schema="endfield.memorypack-animation-curve-native-contract.v1",
        status="exact-current-build", label=LABEL)
    fields = value.get("keyframeFields", [])
    if (value.get("storedMemberCount") != 3 or value.get("keyframeBytes") != 28
            or len(fields) != 7 or len({f["fieldName"] for f in fields}) != 7
            or [f["wireOffset"] for f in fields] != list(range(0, 28, 4))
            or any(f["bytes"] != 4 for f in fields)):
        raise ValueError(f"{LABEL}.contract:shape")
    return value


def _fail(check: str, expected: Any, actual: Any, *, field: str = "") -> None:
    error = CensusGateError(f"{LABEL}.{check}", source=CONTRACT_PATH.as_posix(),
        expected=str(expected)[:1024], actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL, field=field)
    raise error


def _program(image: Any, section: dict[str, Any]) -> list[tuple[int, bytes]]:
    window = section["window"]
    image.check_windows([window], label=LABEL)
    cursor = window["startRva"]; result = []
    for at, raw_hex in section["instructions"]:
        raw = bytes.fromhex(raw_hex)
        if at != cursor or not raw or at + len(raw) > window["endRva"]:
            _fail("program-contiguity", cursor, [at, raw_hex])
        result.append((at, raw)); cursor += len(raw)
    if cursor != window["endRva"]:
        _fail("program-end", window["endRva"], cursor)
    image.check_instruction_windows(section["instructions"], label=LABEL)
    return result


def _ordered(rows: list[tuple[int, bytes]], wanted: list[bytes], *, field: str) -> None:
    cursor = 0
    for raw in wanted:
        positions = [j for j in range(cursor, len(rows)) if rows[j][1] == raw]
        if not positions:
            _fail("source-program", raw.hex().upper(), [v.hex().upper() for _, v in rows], field=field)
        cursor = positions[0] + 1


def _relative(row: list[Any], prefix: bytes, size: int, *, field: str) -> int:
    at, raw_hex = row; raw = bytes.fromhex(raw_hex)
    if len(raw) != size or not raw.startswith(prefix):
        _fail("relative-opcode", prefix.hex().upper(), row, field=field)
    return at + size + struct.unpack_from("<i", raw, size - 4)[0]


def _check_curve_copies(image: Any, contract: dict[str, Any]) -> None:
    """Join actual source instructions to actual typed destination offsets."""
    image.validate_method_row(contract["sourceMethod"], label=LABEL)
    image.check_windows(contract["codeWindows"], label=LABEL)
    full = contract["codeWindows"]
    if len(full) != 1 or full[0]["startRva"] != contract["sourceMethod"][3]:
        _fail("formatter-window", contract["sourceMethod"], full)
    full = full[0]
    bounded = contract["headerInstructions"] + contract["arrayAllocation"]["instructions"]
    for section in ("raw8Program", "countProgram", "keyframeProgram"):
        w = contract[section]["window"]
        if not full["startRva"] <= w["startRva"] < w["endRva"] <= full["endRva"]:
            _fail("program-outside-formatter", full, w, field=section)
        bounded += contract[section]["instructions"]
    for binding in contract["icallBindings"]:
        bounded += binding["fallbackInstructions"] + [binding["cacheLoad"], binding["cacheTest"], binding["cacheBranch"]] + binding["argumentInstructions"]
    if any(not full["startRva"] <= row[0] < row[0]+len(bytes.fromhex(row[1])) <= full["endRva"] for row in bounded):
        _fail("instruction-outside-formatter", full, bounded)
    b = contract["readerOffsets"]["bufferPointer"]
    r = contract["readerOffsets"]["remaining"]
    c, s = contract["readerOffsets"]["consumed"]
    if any(type(n) is not int or not 0 <= n < 128 for n in (b, r, c, s)) or len({b, r, c, s}) != 4:
        _fail("reader-offsets", "four distinct disp8 slots", contract["readerOffsets"])
    header = contract["headerInstructions"]
    expected_header = [b"\x4d\x8b\xf0", b"\x48\x8b\xda", b"\x48\x8b\x43"+bytes([b]),
        b"\x0f\xb6\x30", b"\x8b\x7b"+bytes([r]), b"\x83\xef\x01",
        b"\x48\xff\x43"+bytes([b]), b"\xff\x43"+bytes([c]), b"\xff\x43"+bytes([s]),
        b"\x89\x7b"+bytes([r]), b"\x40\x80\xfe\xff", b"\x40\x80\xfe\x03"]
    if [bytes.fromhex(h[1]) for h in header] != expected_header or any(a[0] >= z[0] for a, z in zip(header, header[1:])):
        _fail("header-program", [v.hex().upper() for v in expected_header], header)
    image.check_instruction_windows(header, label=LABEL)
    raw8 = _program(image, contract["raw8Program"])
    _ordered(raw8, [b"\x48\x8b\x43"+bytes([b]), b"\x44\x8b\x20", b"\x44\x8b\x68\x04",
        b"\x44\x89\x64\x24\x20", b"\x44\x89\x6c\x24\x24", b"\x83\xef\x08",
        b"\x48\x83\x43"+bytes([b, 8]), b"\x83\x43"+bytes([c, 8]),
        b"\x83\x43"+bytes([s, 8]), b"\x89\x7b"+bytes([r])], field="wrapModes")
    count = _program(image, contract["countProgram"])
    _ordered(count, [b"\x48\x8b\x43"+bytes([b]), b"\x44\x8b\x38", b"\x83\xee\x04",
        b"\x48\x83\x43"+bytes([b, 4]), b"\x83\x43"+bytes([c, 4]),
        b"\x83\x43"+bytes([s, 4]), b"\x89\x73"+bytes([r])], field="keyCount")
    loop = _program(image, contract["keyframeProgram"])
    # The bounded disassembler splits IMUL's four bytes. Authenticate its
    # concatenated opcode instead of mistaking those fragments for instructions.
    loop_raw = b"".join(v for _, v in loop)
    if loop_raw.count(b"\x48\x6b\xf0\x1c") != 1:
        _fail("key-stride", "one signed index * 28 into RSI", loop_raw.hex().upper())
    _ordered(loop, [b"\x44\x8b\xe5", b"\x44\x3b\x67\x18", b"\x49\x63\xc4",
        b"\x83\x7b"+bytes([r,28]), b"\x48\x8b\x43"+bytes([b]),
        b"\x44\x8b\x6b"+bytes([r]), b"\x41\x83\xed\x1c",
        b"\x48\x83\x43"+bytes([b,28]), b"\x83\x43"+bytes([c,28]),
        b"\x83\x43"+bytes([s,28]), b"\x44\x89\x6b"+bytes([r]),
        b"\x41\xff\xc4", b"\x45\x3b\xe7", b"\x44\x8b\x64\x24\x20",
        b"\x44\x8b\x6c\x24\x24"], field="keyLoop")
    key_type = contract["keyframeTypeDefinition"]
    if image.type_name(key_type) != contract["keyframeTypeName"]:
        _fail("key-type", contract["keyframeTypeName"], image.type_name(key_type))
    offsets = runtime_type_field_offsets(image.metadata, image.pe, image.registration, key_type)
    sizes = unmanaged_value_sizes_from_image(image)
    if sizes.get(contract["keyframeTypeName"]) != contract["keyframeBytes"]:
        _fail("key-unmanaged-size", contract["keyframeBytes"], sizes.get(contract["keyframeTypeName"]))
    fields = contract["keyframeFields"]
    if offsets != {f["fieldName"]: f["runtimeFieldOffset"] for f in fields} or contract["arrayPayloadOffset"] != 32:
        _fail("key-runtime-layout", fields, offsets)
    for f in fields:
        wire = f["wireOffset"]; dest = contract["arrayPayloadOffset"] + wire
        if f["runtimeFieldOffset"] != wire + 16:
            _fail("key-field-offset", wire+16, f["runtimeFieldOffset"], field=f["fieldName"])
        field = next(v for v in image.metadata.fields_for(image.metadata.types[key_type])
                     if image.metadata.string(v.name_index) == f["fieldName"])
        pointer = image.pe.u64_at_va(int(image.registration["types"],16)+field.type_index*8)
        declared = runtime_type_name(image.pe,image.metadata,pointer)
        if declared != f["declaredType"] or declared != ("int" if wire == 16 else "float"):
            _fail("key-field-type", f["declaredType"], declared, field=f["fieldName"])
        if wire == 16:
            load, store = b"\x8b\x48\x10", b"\x89\x4c\x3e"+bytes([dest])
        else:
            reg = 6 + wire//4 - (wire > 16)
            rex = b"\x44" if reg >= 8 else b""
            load = b"\xf3"+rex+b"\x0f\x10"+bytes([(reg%8)*8+(0x40 if wire else 0)])+(bytes([wire]) if wire else b"")
            store = b"\xf3"+rex+b"\x0f\x11"+bytes([0x44+(reg%8)*8,0x3e,dest])
        wanted = [f["sourceInstruction"], f["destinationInstruction"]]
        if [bytes.fromhex(v[1]) for v in wanted] != [load, store] or not wanted[0][0] < wanted[1][0]:
            _fail("key-source-destination", [load.hex().upper(),store.hex().upper()], wanted, field=f["fieldName"])
        if any(v not in contract["keyframeProgram"]["instructions"] for v in wanted):
            _fail("key-copy-outside-loop", "source and destination in bounded loop", wanted, field=f["fieldName"])
        image.check_instruction_windows(wanted,label=LABEL)
    array = contract["arrayAllocation"]
    cell = _relative(array["typeLoad"],b"\x48\x8b\x0d",7,field="keyArrayType")
    word = image.pe.u64_at_va(image.pe.image_base+cell)
    index = (word>>1)&0xfffffff
    if cell != array["cellRva"] or word>>29 != 1 or not word&1 or index >= image.registration["typesCount"]:
        _fail("key-array-type-cell", array["cellRva"], {"cell":cell,"word":word})
    pointer = image.pe.u64_at_va(int(image.registration["types"],16)+index*8)
    name = runtime_type_name(image.pe,image.metadata,pointer)
    if name != array["typeName"] or name != contract["keyframeTypeName"]+"[]":
        _fail("key-array-type", array["typeName"], name)
    rows = array["instructions"]
    if (len(rows)!=4 or rows[0]!=array["typeLoad"] or rows[1][1]!="498BD7" or rows[3][1]!="488BF8"
            or any(a[0]+len(bytes.fromhex(a[1]))!=z[0] for a,z in zip(rows,rows[1:]))
            or _relative(rows[2],b"\xe8",5,field="keyArrayAllocation")!=array["allocationCall"]["targetRva"]):
        _fail("key-array-allocation", "closed type RCX, count RDX, direct call -> RDI", rows)
    image.check_instruction_windows(rows,label=LABEL)
    bindings = contract["icallBindings"]
    if {v["fieldName"] for v in bindings}!={"preWrapMode","postWrapMode","keys"} or len(bindings)!=3:
        _fail("wrap-bindings", "three distinct callback-name bindings", bindings)
    resolver_targets=set()
    for v in bindings:
        field=v["fieldName"]; fallback=v["fallbackInstructions"]
        literal=_relative(fallback[0],b"\x48\x8d\x0d",7,field=field)
        cache=_relative(fallback[2],b"\x48\x89\x05",7,field=field)
        args=v["argumentInstructions"]
        expected_literal=(f"UnityEngine.AnimationCurve::set_{field}(UnityEngine.WrapMode)"
                          if field!="keys" else "UnityEngine.AnimationCurve::SetKeys(UnityEngine.Keyframe[])")
        actual_literal=image.pe.c_string_at_va(image.pe.image_base+literal)
        if (v["literal"]!=expected_literal or actual_literal!=expected_literal or literal!=v["literalRva"]
                or cache!=v["cacheCellRva"] or _relative(v["cacheLoad"],b"\x48\x8b\x05",7,field=field)!=cache
                or len(fallback)!=4 or any(a[0]+len(bytes.fromhex(a[1]))!=z[0] for a,z in zip(fallback,fallback[1:]))
                or _relative(fallback[3],b"\xe9",5,field=field)!=args[0][0]
                or v["cacheTest"]!=[v["cacheLoad"][0]+7,"4885C0"]
                or v["cacheBranch"][0]!=v["cacheLoad"][0]+10
                or _relative(v["cacheBranch"],b"\x0f\x84",6,field=field)!=fallback[0][0]
                or v["cacheBranch"][0]+6!=args[0][0]):
            _fail("callback-name-cache", expected_literal, v, field=field)
        arg_bits={"preWrapMode":"418BD4","postWrapMode":"418BD5","keys":"488BD7"}[field]
        if [a[1] for a in args]!=[arg_bits,"488BCB","FFD0"] or any(a[0]+len(bytes.fromhex(a[1]))!=z[0] for a,z in zip(args,args[1:])):
            _fail("callback-argument", [arg_bits,"488BCB","FFD0"],args,field=field)
        resolver_targets.add(_relative(fallback[1],b"\xe8",5,field=field))
        image.check_instruction_windows(fallback+[v["cacheLoad"],v["cacheTest"],v["cacheBranch"]]+args,label=LABEL)
    if len(resolver_targets)!=1:
        _fail("callback-resolver", "one selected direct resolver target",resolver_targets)


def validate_current_native_contract() -> dict[str, Any]:
    contract=_contract(); expected=contract["nativeInputs"]
    gate=check_installed_native_inputs(expected["GameAssembly.dll"],expected["global-metadata.dat"])
    if gate.status!="validated":
        return {"status":gate.status,"detail":gate.detail,"nativeInputs":expected}
    unity=Path(gate.gameassembly).parent/"UnityPlayer.dll"
    if not unity.is_file():
        return {"status":"missing","detail":"UnityPlayer.dll missing","nativeInputs":expected}
    if hashlib.sha256(unity.read_bytes()).hexdigest().upper()!=expected["UnityPlayer.dll"]:
        return {"status":"mismatched","detail":"UnityPlayer.dll hash differs","nativeInputs":expected}
    dependency=CONTRACTS_DIR/contract["sourceContract"]
    source=json.loads(dependency.read_bytes())
    if source.get("schemaVersion")!=1 or contract["sourceMethod"] not in source["methodGroups"][0]["methods"]:
        _fail("source-formatter", contract["sourceMethod"],source.get("methodGroups"))
    image=open_native_image(gate.gameassembly,gate.metadata)
    _check_curve_copies(image,contract)
    after=check_installed_native_inputs(expected["GameAssembly.dll"],expected["global-metadata.dat"],
        gameassembly=gate.gameassembly,metadata=gate.metadata)
    if after.status!="validated":
        return {"status":after.status,"detail":after.detail,"nativeInputs":expected}
    return {"status":"validated","nativeInputs":expected,"keyframeFields":contract["keyframeFields"],
            "storedMemberCount":contract["storedMemberCount"],"keyframeBytes":contract["keyframeBytes"],
            "evidenceBoundary":contract["evidenceBoundary"]}


def decode_curve(data: bytes, *, source: str, digest: str, start: int, end: int,
                 native_validation: dict[str, Any]) -> dict[str, Any]:
    contract=_contract()
    if (native_validation.get("status")!="validated" or native_validation.get("nativeInputs")!=contract["nativeInputs"]
            or any(native_validation.get(k)!=contract[k] for k in ("keyframeFields","storedMemberCount","keyframeBytes"))
            or not isinstance(data,bytes) or not source or not isinstance(digest,str)
            or hashlib.sha256(data).hexdigest().upper()!=digest.upper()
            or type(start) is not int or type(end) is not int or not 0<=start<end<=len(data)):
        raise ValueError(f"{LABEL}.decode:native-source-or-span")
    reader=Reader(data,source,end);reader.pos=start;fields=[];keys=[];count=None
    is_null=reader.peek()==255
    if is_null:
        reader.take(1,"null-curve")
    else:
        reader.header(contract["storedMemberCount"])
        for name in ("preWrapMode","postWrapMode"):
            at=reader.pos;raw=reader.take(4,name)
            fields.append({"fieldName":name,"start":at,"end":reader.pos,"rawHex":raw.hex().upper()})
        at=reader.pos;count=reader.count(contract["keyframeBytes"],nullable=True)
        for _ in range(max(0,count)):
            begin=reader.pos;members=[]
            for f in contract["keyframeFields"]:
                pos=reader.pos;raw=reader.take(f["bytes"],f["fieldName"])
                members.append({"fieldName":f["fieldName"],"declaredType":f["declaredType"],
                    "start":pos,"end":reader.pos,"rawHex":raw.hex().upper()})
            keys.append({"start":begin,"end":reader.pos,"namedFields":members})
        fields.append({"fieldName":"keys","start":at,"end":reader.pos,"count":count,"elements":keys})
    if reader.pos!=end:
        raise ValueError(f"{LABEL}.decode:curve-end={reader.pos}; expected={end}")
    return {"schema":"endfield.memorypack-animation-curve-receipt.v1","source":source,
        "logicalSha256":digest.upper(),"start":start,"end":end,"null":is_null,"keyCount":count,
        "namedFields":fields,"recursiveStoredSchemaExact":True,"runtimeMeaningExact":False}
