"""Explicit struct source programs, separate from runtime-size inference.

Unmanaged twelve-byte reads copy eight plus four source bytes and advance
twelve; inline sixteen-byte reads copy the parent buffer and update its
cursor. Both independently prove the complete temporary-to-field transfer.
"""
from __future__ import annotations
import struct
from typing import Any, Callable
from scripts.game_data.il2cpp.protocol import runtime_type_name, runtime_type_field_offsets
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.memorypack import named_native_records as named


def _program(image: Any, window: dict, rows: Any, expected: list[bytes], *, label: str,
             fail: Callable[..., None]) -> None:
    if (not isinstance(rows, list) or len(rows) != len(expected)
            or any(not isinstance(r, list) or len(r) != 2 or type(r[0]) is not int for r in rows)):
        fail("struct-program-shape", len(expected), rows)
    for row, raw in zip(rows, expected, strict=True):
        if row[1] != raw.hex().upper() or not window["startRva"] <= row[0] < row[0]+len(raw) <= window["endRva"]:
            fail("struct-program-instruction", raw.hex().upper(), row)
    if any(a[0]+len(bytes.fromhex(a[1])) != b[0] for a,b in zip(rows, rows[1:])):
        fail("struct-program-contiguity", "complete normal program", rows)
    image.check_instruction_windows(rows, label=label)


def _branch(rows: list, index: int, prefix: str, fail: Callable[..., None]) -> bytes:
    raw = bytes.fromhex(rows[index][1])
    expected = bytes.fromhex(prefix)
    if len(raw) != len(expected)+4 or not raw.startswith(expected):
        fail("struct-program-branch", prefix+" rel32", rows[index])
    return raw


def _call(image: Any, call: dict, *, label: str, fail: Callable[..., None]) -> bytes:
    named.check_call(image, call, label=label, fail=fail)
    return image.pe.bytes_at_va(image.pe.image_base+call["rva"],5)


def _getter(image: Any, proof: dict, record: dict, *, label: str, fail: Callable[..., None]) -> bytes:
    method=proof.get("getterMethod");call=proof.get("getterCall") or {}
    if (not isinstance(method,list) or len(method)!=4 or method[1]!=record["wrapperTypeName"]
            or method[2]!="get___instance" or method[3]!=call.get("targetRva")):
        fail("struct-wrapper-getter", "selected exact wrapper instance getter", proof)
    image.validate_method_row(method,label=label)
    definition=image.metadata.methods[method[0]]
    pointer=image.pe.u64_at_va(int(image.registration["types"],16)+definition.return_type*8)
    raw=image.pe.bytes_at_va(pointer,16)
    if (definition.flags&0x10 or definition.parameter_count!=0 or len(raw)!=16 or raw[10:12]!=b"\x12\0"
            or runtime_type_name(image.pe,image.metadata,pointer)!=record["runtimeTypeName"]):
        fail("struct-getter-return", "instance no-argument getter returns exact reference Data", raw.hex())
    return _call(image,call,label=label,fail=fail)


def check_reader_ref_wrapper_abi(image: Any, record: dict, *, fail: Callable[..., None]) -> None:
    """Establish the two incoming pointer arguments without a hidden result."""
    method=image.metadata.methods[record["readerMethod"][0]]
    table=int(image.registration["types"],16)
    parameters=list(image.metadata.parameters_for(method))
    raw=[image.pe.bytes_at_va(image.pe.u64_at_va(table+p.type_index*8),16) for p in parameters]
    result=image.pe.bytes_at_va(image.pe.u64_at_va(table+method.return_type*8),16)
    if (not method.flags&0x10 or len(raw)!=2 or len(result)!=16 or result[10]!=1 or result[11]&0x7f
            or any(len(t)!=16 or t[11]&0x7f!=0x20 for t in raw)
            or raw[0][10]!=0x11 or raw[1][10]!=0x12
            or int.from_bytes(raw[1][:8],"little")!=record["wrapperTypeDefinition"]
            or runtime_type_name(image.pe,image.metadata,image.pe.u64_at_va(table+parameters[0].type_index*8))!="MemoryPack.MemoryPackReader"):
        fail("struct-parent-abi", "static void reader with exact two ref parameters", [r.hex() for r in raw])


def _check_pointer_aliases(image: Any, normal: dict, rows: list, *, label: str,
                           aliases: dict[str, str] | None = None,
                           fail: Callable[..., None]) -> None:
    _program(image,normal,rows,[bytes.fromhex(r[1]) for r in rows],label=label,fail=fail)
    aliases=aliases or {"rbx":"488BD9","rdi":"488BFA"};seen=set()
    for at,value in rows:
        raw=bytes.fromhex(value)
        instructions=image.mapper.decode_x64_subset(raw,image.pe.image_base+at,stop_offset=len(raw))
        if len(instructions)!=1 or instructions[0]["text"].startswith("db"):
            fail("struct-parent-instruction", "one understood instruction", [at,value,instructions])
        write=instructions[0].get("write") or {};register=write.get("register")
        if register in {"rbx","ebx","bx","bl","bh","rdi","edi","di","dil"}:
            if register not in aliases or register in seen or value!=aliases[register]:
                fail("struct-parent-argument-clobber",aliases,[at,value,write])
            seen.add(register)
        if raw[:1]==b"\xe8" and seen!=set(aliases):
            fail("struct-parent-late-alias",sorted(aliases),sorted(seen))
    if seen!=set(aliases):fail("struct-parent-missing-alias",sorted(aliases),sorted(seen))


def check_unmanaged8(image: Any, source: dict, member: dict, record: dict, sizes: dict,
                     normal: dict, previous: int, *, label: str, fail: Callable[..., None]) -> None:
    """Prove two raw Float32 words return in RAX and reach one eight-byte field.

    This is an explicit normal-path program, not a width-based extension of
    ReadUnmanaged<int>. The selected direct and registered entries are proved
    independently. External slow and error paths and live calls stay outside
    this claim.
    """
    proof=member.get("unmanagedOutputSource") or {};assignment=member["assignment"]
    context=next((c for c in source["nestedContexts"] if c["instructionRva"]==member.get("sourceContextInstructionRva")),None)
    if (proof.get("mode")!="unmanaged-return64-float-pair" or member["kind"]!="raw8"
            or sizes.get(member["declaredType"])!=8 or proof.get("width")!=8
            or context is None or context.get("typeKind")!=17 or assignment["kind"]!="setter"):
        fail("struct-unmanaged8-type","closed eight-byte value with explicit paired-word return",proof)
    definition=image.metadata.methods[context["methodSpec"][0]]
    identity=[definition.index,image.type_name(definition.declaring_type),image.metadata.string(definition.name_index)]
    section=image.metadata.sections["genericContainers"];at=section.offset+definition.generic_container_index*16
    if definition.generic_container_index<0 or not section.offset<=at<=section.offset+section.size-16:
        fail("struct-unmanaged8-container","bounded method generic container",definition.generic_container_index)
    container=struct.unpack_from("<iiii",image.metadata.buf,at)
    table=int(image.registration["types"],16)
    ret=image.pe.bytes_at_va(image.pe.u64_at_va(table+definition.return_type*8),16)
    if (identity!=proof.get("sourceDefinition") or identity[1:]!=["MemoryPack.MemoryPackReader","ReadUnmanaged"]
            or definition.flags&0x10 or definition.parameter_count!=0 or container[:3]!=(definition.index,1,1)
            or len(ret)!=16 or ret[10:12]!=b"\x1e\0" or int.from_bytes(ret[:8],"little")!=container[3]):
        fail("struct-unmanaged8-definition","instance ReadUnmanaged<T>() returns its sole undecorated MVAR",identity)
    direct=proof["directReader"];dw=direct["window"];dr=direct["instructions"]
    if (member["sourceCall"]["targetRva"]!=dw["startRva"]
            or not any(w["startRva"]==dw["startRva"] and w["endRva"]==dw["endRva"] and w["sha256"]==dw["sha256"] for w in source["codeWindows"])):
        fail("struct-unmanaged8-direct-window","actual helper and authenticated source window",dw)
    registered=proof["registeredReader"];rw=registered["window"];rr=registered["instructions"]
    entry=GenericEntries(image).resolve(context["methodSpec"][0],[],[member["declaredType"]])
    if entry["methodSpecIndex"]!=context["methodSpecIndex"] or entry["pointer"]!=image.pe.image_base+rw["startRva"]:
        fail("struct-unmanaged8-registration","same closed MethodSpec and selected registered entry",entry)
    setter=proof["setter"];sw=setter["window"];sr=setter["instructions"];gw=setter["getterWindow"];gr=setter["getterInstructions"]
    aw=registered["advanceWindow"];ar=registered["advanceInstructions"]
    image.check_windows([dw,rw,aw,sw,gw],label=label)
    _program(image,dw,dr,[bytes.fromhex(h) for h in ["48895C2408","57","4883EC40","83793008","488BD9","0F29742430","0F297C2420"]]
        +[_branch(dr,7,"0F8C",fail)]+[bytes.fromhex(h) for h in ["488B4350","F30F1030","F30F107804","8B7B30","83EF08"]]
        +[_branch(dr,13,"0F88",fail)]+[bytes.fromhex(h) for h in ["4883435008","83434008","83434408","897B30","488B5C2450",
            "0F28C6","0F28742430","0F14C7","0F287C2420","66480F7EC0","4883C440","5F","C3"]],label=label,fail=fail)
    for rows,window,index in ((dr,dw,7),(dr,dw,13),(ar,aw,10)):
        raw=bytes.fromhex(rows[index][1])
        if len(raw)!=6 or window["startRva"]<=rows[index][0]+6+struct.unpack("<i",raw[2:])[0]<window["endRva"]:
            fail("struct-unmanaged8-slow-branch","failure branch leaves the proved normal helper",rows[index])
    branch=bytes.fromhex(rr[6][1])
    if len(branch)!=2 or branch[0]!=0x7d or rr[6][0]+2+struct.unpack("b",branch[1:])[0]!=rr[10][0]:
        fail("struct-unmanaged8-registered-branch","JGE skips only ensure-input call",rr[6])
    ensure=_call(image,registered["ensureCall"],label=label,fail=fail)
    advance=_call(image,registered["advanceCall"],label=label,fail=fail)
    _program(image,rw,rr,[bytes.fromhex(h) for h in ["4053","4883EC40","83793008","488BD9","0F29742430","0F297C2420"]]
        +[branch]+[bytes.fromhex("4533C0"),bytes.fromhex("BA08000000"),ensure]
        +[bytes.fromhex(h) for h in ["488B4350","BA08000000","488BCB","F30F1030","F30F107804"]]+[advance]
        +[bytes.fromhex(h) for h in ["0F14F7","0F287C2420","66480F7EF0","0F28742430","4883C440","5B","C3"]],label=label,fail=fail)
    _program(image,aw,ar,[bytes.fromhex(h) for h in ["85D2","743C","48895C2410","57","4883EC20","4863FA","488BD9","4889742430","8B7130","2BF7"]]
        +[_branch(ar,10,"0F88",fail)]+[bytes.fromhex(h) for h in ["48017B50","017B40","017B44","897330","488B742430","488B5C2438","4883C420","5F","C3"]],label=label,fail=fail)
    if (rr[9][0]!=registered["ensureCall"]["rva"] or rr[15][0]!=registered["advanceCall"]["rva"]
            or registered["advanceCall"]["targetRva"]!=aw["startRva"]):
        fail("struct-unmanaged8-registered-calls","actual ensure and cursor calls at proved program positions",registered)
    # The source's two incoming refs are preserved by nonvolatile aliases.
    check_reader_ref_wrapper_abi(image,record,fail=fail)
    prefix=proof["parentProgram"]
    if not prefix or prefix[0][0]!=normal["startRva"] or prefix[-1][0]+5!=assignment["rva"]+5:
        fail("struct-unmanaged8-parent-program","complete parent prefix through setter call",prefix)
    _check_pointer_aliases(image,normal,prefix,label=label,aliases={"rbx":"488BDA","rdi":"488BF9"},fail=fail)
    args=proof["argumentInstructions"];bridge=proof["bridgeInstructions"]
    _program(image,normal,args,[bytes.fromhex(context["instructionHex"]),bytes.fromhex("488BCF"),bytes.fromhex("488B33")],label=label,fail=fail)
    _program(image,normal,bridge,[bytes.fromhex("4885F6"),_branch(bridge,1,"0F84",fail),
        bytes.fromhex("4533C0"),bytes.fromhex("488BD0"),bytes.fromhex("488BCE"),_call(image,assignment,label=label,fail=fail)],label=label,fail=fail)
    if (not previous<=args[0][0]==context["instructionRva"] or args[-1][0]+3!=member["sourceCall"]["rva"]
            or member["sourceCall"]["rva"]+5!=bridge[0][0] or bridge[-1][0]!=assignment["rva"]
            or assignment["targetRva"]!=sw["startRva"]):
        fail("struct-unmanaged8-parent-transfer","reader RDI -> return RAX -> full argument RDX -> same wrapper setter",proof)
    method=image.metadata.methods[member["setterMethodIndex"]];params=list(image.metadata.parameters_for(method))
    pointer=image.pe.u64_at_va(table+params[0].type_index*8) if len(params)==1 else 0
    parameter=image.pe.bytes_at_va(pointer,16) if pointer else b""
    if (method.flags&0x10 or len(params)!=1 or len(parameter)!=16 or parameter[10]!=0x11 or parameter[11]&0x7f
            or runtime_type_name(image.pe,image.metadata,pointer)!=member["declaredType"]):
        fail("struct-unmanaged8-setter-abi","instance setter with sole undecorated exact value argument",parameter.hex())
    getter=_getter(image,setter,record,label=label,fail=fail);offset=setter["fieldOffset"]
    offsets=runtime_type_field_offsets(image.metadata,image.pe,image.registration,record["runtimeTypeDefinition"])
    if offsets.get(member["fieldName"])!=offset or type(offset) is not int or not 0<=offset<=123:
        fail("struct-unmanaged8-field-offset","actual owned field with two bounded disp8 stores",offsets)
    null=bytes.fromhex(sr[5][1])
    if len(null)!=2 or null[0]!=0x74 or sr[5][0]+2+struct.unpack("b",null[1:])[0]!=sr[12][0]:
        fail("struct-unmanaged8-setter-null","null return jumps only to error call",sr[5])
    _program(image,sw,sr,[bytes.fromhex(h) for h in ["4883EC28","4889542448","33D2"]]+[getter,bytes.fromhex("4885C0"),null]
        +[bytes.fromhex("F30F10442448"),bytes.fromhex("F30F104C244C"),bytes.fromhex("F30F1140")+bytes([offset]),
          bytes.fromhex("F30F1148")+bytes([offset+4]),bytes.fromhex("4883C428"),bytes.fromhex("C3"),bytes.fromhex(sr[12][1]),bytes.fromhex("CC")],label=label,fail=fail)
    if sr[3][0]!=setter["getterCall"]["rva"] or len(bytes.fromhex(sr[12][1]))!=5 or not sr[12][1].startswith("E8"):
        fail("struct-unmanaged8-getter-call","proved getter and bounded error call",setter)
    # The normal getter checks and returns its own typed __realInstance,
    # after comparing it to the inherited object reference.
    instance_fields=[f for f in image.metadata.fields_for(image.metadata.types[record["wrapperTypeDefinition"]]) if image.metadata.string(f.name_index)=="__realInstance"]
    raw=image.pe.bytes_at_va(image.pe.u64_at_va(table+instance_fields[0].type_index*8),16) if len(instance_fields)==1 else b""
    wo=runtime_type_field_offsets(image.metadata,image.pe,image.registration,record["wrapperTypeDefinition"])
    if (len(raw)!=16 or raw[10:12]!=b"\x12\0" or int.from_bytes(raw[8:10],"little")&0x10
            or int.from_bytes(raw[:8],"little")!=record["runtimeTypeDefinition"] or wo.get("__realInstance")!=24):
        fail("struct-unmanaged8-wrapper-instance","typed own __realInstance at selected getter return load",raw.hex())
    global_test=bytes.fromhex(gr[2][1]);init_branch=bytes.fromhex(gr[4][1])
    if len(global_test)!=7 or not global_test.startswith(bytes.fromhex("803D")) or global_test[-1]!=0 or len(init_branch)!=2 or init_branch[0]!=0x74:
        fail("struct-unmanaged8-getter-initialization","complete static-byte guard and JE initialization branch",gr[:5])
    _program(image,gw,gr,[bytes.fromhex("4053"),bytes.fromhex("4883EC20"),global_test,bytes.fromhex("488BD9"),init_branch,
        bytes.fromhex("48837B1800"),_branch(gr,6,"0F84",fail),bytes.fromhex("488B4310"),bytes.fromhex("48394318"),
        _branch(gr,9,"0F85",fail),bytes.fromhex("488B4318"),bytes.fromhex("4883C420"),bytes.fromhex("5B"),bytes.fromhex("C3")],label=label,fail=fail)
    for window,rows in ((dw,dr),(rw,rr),(aw,ar),(sw,sr)):
        if rows[0][0]!=window["startRva"] or rows[-1][0]+len(bytes.fromhex(rows[-1][1]))!=window["endRva"]:
            fail("struct-unmanaged8-program-extent","complete selected helper",window)
    if gr[0][0]!=gw["startRva"]:
        fail("struct-unmanaged8-getter-entry","normal getter starts at selected method entry",gr[0])


def check_parent_argument_roles(image: Any, record: dict, normal: dict, *, label: str,
                                 fail: Callable[..., None]) -> None:
    """Follow source reader and ref-wrapper arguments through the normal body."""
    proof=record.get("sourceArgumentRoles") or {};rows=proof.get("normalProgram")
    if (proof.get("mode")!="reader-rbx-wrapper-ref-rdi" or not isinstance(rows,list) or not rows
            or rows[0][0]!=normal["startRva"]):
        fail("struct-parent-roles", "complete normal prefix with exact ABI aliases", proof)
    check_reader_ref_wrapper_abi(image,record,fail=fail)
    selected=[m for m in record["members"] if m.get("unmanagedOutputSource") is not None
              or (m.get("inlineSource") or {}).get("mode") in {"inline-cursor-struct16", "inline-cursor-struct12"}]
    if not selected:fail("struct-parent-prefix-scope","reached struct source fields",[])
    end=max(max([m["assignment"]["rva"]+len(bytes.fromhex(m["assignment"]["rawHex"]))]
                +[t["rva"]+len(bytes.fromhex(t["rawHex"])) for t in m["assignment"].get("tailStores",[])])
            for m in selected)
    _check_pointer_aliases(image,normal,rows,label=label,fail=fail)
    if rows[-1][0]+len(bytes.fromhex(rows[-1][1]))!=end:
        fail("struct-parent-prefix-end",end,rows[-1])


def check_unmanaged12(image: Any, source: dict, member: dict, record: dict, sizes: dict,
                       normal: dict, previous: int, *, label: str, fail: Callable[..., None]) -> None:
    proof=member.get("unmanagedOutputSource") or {};assignment=member["assignment"]
    context=next((c for c in source["nestedContexts"] if c["instructionRva"]==member.get("sourceContextInstructionRva")),None)
    if (proof.get("mode")!="unmanaged-output12" or member["kind"]!="raw12"
            or sizes.get(member["declaredType"])!=12 or proof.get("width")!=12
            or record.get("sourceArgumentRoles", {}).get("mode")!="reader-rbx-wrapper-ref-rdi"
            or context is None or context.get("typeKind")!=17 or assignment["kind"]!="direct-store"):
        fail("struct-unmanaged-type", "closed unmanaged twelve-byte field and explicit source", proof)
    method=image.metadata.methods[context["methodSpec"][0]]
    identity=[method.index,image.type_name(method.declaring_type),image.metadata.string(method.name_index)]
    section=image.metadata.sections["genericContainers"];at=section.offset+method.generic_container_index*16
    if method.generic_container_index<0 or not section.offset<=at<=section.offset+section.size-16:
        fail("struct-unmanaged-generic-container", "bounded method container",method.generic_container_index)
    container=struct.unpack_from("<iiii",image.metadata.buf,at)
    ret=image.pe.bytes_at_va(image.pe.u64_at_va(int(image.registration["types"],16)+method.return_type*8),16)
    if (identity!=proof.get("sourceDefinition") or identity[1:]!=["MemoryPack.MemoryPackReader","ReadUnmanaged"]
            or method.flags&0x10 or method.parameter_count!=0 or container[:3]!=(method.index,1,1)
            or len(ret)!=16 or ret[10:12]!=b"\x1e\0" or int.from_bytes(ret[:8],"little")!=container[3]):
        fail("struct-unmanaged-return-abi", "instance ReadUnmanaged<T>() sole undecorated MVAR",identity)
    direct=proof["directReader"];window=next((w for w in source["codeWindows"] if w["startRva"]==direct["windowStartRva"]),None)
    if window is None or member["sourceCall"]["targetRva"]!=window["startRva"]:
        fail("struct-unmanaged-source-window","actual source call enters reviewed raw12 helper",window)
    rows=direct["instructions"]
    _program(image,window,rows,[bytes.fromhex(h) for h in [
        "48895C2408","4889742410","57","4883EC20","837A300C","488BDA","488BF9"]]+
        [_branch(rows,7,"0F8C",fail)]+[bytes.fromhex(h) for h in [
        "488B4350","F20F1000","8B4008","F20F1107","894708","8B7330","83EE0C"]]+
        [_branch(rows,15,"0F88",fail)]+[bytes.fromhex(h) for h in [
        "488343500C","8343400C","8343440C","897330","488B5C2430","488BC7","488B742438","4883C420","5F","C3"]],label=label,fail=fail)
    if rows[0][0]!=window["startRva"] or rows[-1][0]+1!=window["endRva"]:
        fail("struct-unmanaged-window-extent",window,rows[-1])
    entry=GenericEntries(image).resolve(context["methodSpec"][0],[],[member["declaredType"]])
    registered=proof["registeredReader"];rw=registered["window"];advance=registered["advanceWindow"];rcall=registered["advanceCall"]
    if entry["methodSpecIndex"]!=context["methodSpecIndex"] or entry["pointer"]!=image.pe.image_base+rw["startRva"]:
        fail("struct-unmanaged-registration","same closed MethodSpec and independent entry",entry)
    image.check_windows([rw,advance],label=label)
    rr=registered["instructions"]
    branch=bytes.fromhex(rr[6][1])
    if len(branch)!=2 or branch[:1]!=b"\x7d":fail("struct-registered-branch","JGE short",rr[6])
    ensure=_call(image,registered["ensureCall"],label=label,fail=fail)
    cursor=_call(image,rcall,label=label,fail=fail)
    _program(image,rw,rr,[bytes.fromhex(h) for h in ["48895C2408","57","4883EC20","837A300C","488BDA","488BF9"]]
        +[branch]+[bytes.fromhex(h) for h in ["4533C0","BA0C000000","488BCB"]]+[ensure]
        +[bytes.fromhex(h) for h in ["488B4350","BA0C000000","488BCB","F20F1000","8B4008","F20F1107","894708"]]
        +[cursor]+[bytes.fromhex(h) for h in ["488B5C2430","488BC7","4883C420","5F","C3"]],label=label,fail=fail)
    if (rr[0][0]!=rw["startRva"] or rr[-1][0]+1!=rw["endRva"] or rcall["targetRva"]!=advance["startRva"]
            or rr[10][0]!=registered["ensureCall"]["rva"] or rr[18][0]!=rcall["rva"]):
        fail("struct-registered-program-extent", "full registered program and its cursor helper",registered)
    ar=registered["advanceInstructions"]
    _program(image,advance,ar,[bytes.fromhex(h) for h in ["85D2","743C","48895C2410","57","4883EC20","4863FA","488BD9","4889742430","8B7130","2BF7"]]
        +[_branch(ar,10,"0F88",fail)]+[bytes.fromhex(h) for h in ["48017B50","017B40","017B44","897330","488B742430","488B5C2438","4883C420","5F","C3"]],label=label,fail=fail)
    if ar[0][0]!=advance["startRva"] or ar[-1][0]+1!=advance["endRva"]:
        fail("struct-cursor-program-extent",advance,ar[-1])
    arguments=proof["argumentInstructions"]
    _program(image,normal,arguments,[bytes.fromhex(context["instructionHex"]),bytes.fromhex("488D4C2420"),
        bytes.fromhex("488B37"),bytes.fromhex("488BD3")],label=label,fail=fail)
    if proof.get("destinationMode") == "direct-wrapper-instance-rcx":
        _check_direct_unmanaged12_destination(image, member, record, normal, label=label, fail=fail)
        bridge=proof["bridgeInstructions"]
        if (not previous<=arguments[0][0]==context["instructionRva"]
                or arguments[-1][0]+3!=member["sourceCall"]["rva"]
                or member["sourceCall"]["rva"]+5!=bridge[0][0]):
            fail("struct-unmanaged-transfer", "source output stack20 -> typed wrapper instance -> full field", proof)
        return
    if proof.get("destinationMode", "wrapper-getter-rax") != "wrapper-getter-rax":
        fail("struct-unmanaged-destination-mode", "explicit supported destination program", proof.get("destinationMode"))
    bridge=proof["bridgeInstructions"];getter=_getter(image,proof,record,label=label,fail=fail)
    offset=assignment["fieldOffset"];tail=assignment.get("tailStores")
    if not 0<=offset<=119 or tail!=proof.get("tailStores") or len(tail or [])!=1:
        fail("struct-unmanaged-destination", "complete disp8 eight-plus-four store",assignment)
    store=bytes.fromhex("F20F1140")+bytes([offset]);tail_store=bytes.fromhex("8948")+bytes([offset+8])
    _program(image,normal,bridge,[bytes.fromhex("4885F6"),_branch(bridge,1,"0F84",fail),
        bytes.fromhex("33D2"),bytes.fromhex("488BCE"),getter,bytes.fromhex("4885C0"),_branch(bridge,6,"0F84",fail),
        bytes.fromhex("F20F10442420"),bytes.fromhex("8B4C2428"),store,tail_store],label=label,fail=fail)
    if (not previous<=arguments[0][0]==context["instructionRva"] or arguments[-1][0]+3!=member["sourceCall"]["rva"]
            or member["sourceCall"]["rva"]+5!=bridge[0][0] or bridge[4][0]!=proof["getterCall"]["rva"]
            or bridge[9][0]!=assignment["rva"] or assignment["rawHex"]!=store.hex().upper()
            or assignment["baseRegister"]!=0 or tail[0]!={"rva":bridge[10][0],"rawHex":tail_store.hex().upper(),"offsetDelta":8}):
        fail("struct-unmanaged-transfer", "source output stack20 -> exact getter -> full field",proof)


def _check_direct_unmanaged12_destination(image: Any, member: dict, record: dict, normal: dict,
                                         *, label: str, fail: Callable[..., None]) -> None:
    """Authenticate an explicit wrapper-field load and the complete 8+4 copy.

    This profile has no getter call: RSI holds the dereferenced incoming
    wrapper, its typed __instance loads into RCX, and stack20/28 supply the
    original twelve-byte output. It is selected only by a reviewed declaration.
    """
    proof=member["unmanagedOutputSource"];assignment=member["assignment"]
    bridge=proof.get("bridgeInstructions",[]);offset=assignment["fieldOffset"]
    if (proof.get("destinationMode")!="direct-wrapper-instance-rcx" or len(bridge)!=9
            or type(offset) is not int or not 0<=offset<=119
            or assignment.get("baseRegister")!=1
            or "getterCall" in proof or "getterMethod" in proof):
        fail("struct-unmanaged-direct-destination", "typed RCX destination with two complete disp8 stores", proof)
    fields=[f for f in image.metadata.fields_for(image.metadata.types[record["wrapperTypeDefinition"]])
            if image.metadata.string(f.name_index)=="__instance"]
    table=int(image.registration["types"],16)
    raw=image.pe.bytes_at_va(image.pe.u64_at_va(table+fields[0].type_index*8),16) if len(fields)==1 else b""
    offsets=runtime_type_field_offsets(image.metadata,image.pe,image.registration,record["wrapperTypeDefinition"])
    if (len(raw)!=16 or raw[10:12]!=b"\x12\0" or int.from_bytes(raw[8:10],"little")&0x10
            or int.from_bytes(raw[:8],"little")!=record["runtimeTypeDefinition"] or offsets.get("__instance")!=16):
        fail("struct-unmanaged-direct-instance", "own exact reference Data at wrapper offset sixteen", raw.hex())
    store=bytes.fromhex("F20F1141")+bytes([offset]);tail=bytes.fromhex("8941")+bytes([offset+8])
    _program(image,normal,bridge,[bytes.fromhex("4885F6"),_branch(bridge,1,"0F84",fail),
        bytes.fromhex("488B4E10"),bytes.fromhex("4885C9"),_branch(bridge,4,"0F84",fail),
        bytes.fromhex("F20F10442420"),bytes.fromhex("8B442428"),store,tail],label=label,fail=fail)
    if (bridge[7][0]!=assignment["rva"] or assignment["rawHex"]!=store.hex().upper()
            or assignment.get("tailStores")!=proof.get("tailStores")
            or assignment.get("tailStores")!=[{"rva":bridge[8][0],"rawHex":tail.hex().upper(),"offsetDelta":8}]):
        fail("struct-unmanaged-direct-transfer", "stack20 eight bytes plus stack28 four bytes to one exact field", assignment)
    for index in (1,4):
        row=bridge[index];target=row[0]+6+struct.unpack_from("<i",bytes.fromhex(row[1]),2)[0]
        if bridge[0][0]<=target<bridge[-1][0]+len(tail):
            fail("struct-unmanaged-direct-null-branch", "null guard leaves the complete destination copy", target)


def check_inline16(image: Any, member: dict, record: dict, sizes: dict, normal: dict,
                    previous: int, *, label: str, fail: Callable[..., None]) -> None:
    proof=member["inlineSource"];assignment=member["assignment"];rows=proof["instructions"]
    if (proof.get("mode")!="inline-cursor-struct16" or member["kind"]!="raw16" or sizes.get(member["declaredType"])!=16
            or record.get("sourceArgumentRoles", {}).get("mode")!="reader-rbx-wrapper-ref-rdi"
            or member.get("sourceContextInstructionRva") is not None or assignment["kind"]!="direct-store"
            or proof.get("width")!=16 or assignment["baseRegister"]!=0):
        fail("struct-inline-type","explicit inline sixteen-byte copy",proof)
    getter=_getter(image,proof,record,label=label,fail=fail)
    offset=assignment["fieldOffset"];displacement_width=proof.get("destinationDisplacementBytes",4)
    if (type(offset) is not int or not 0<=offset<=0x7fffffff or type(displacement_width) is not int or displacement_width not in (1,4)
            or displacement_width==1 and offset>127):
        fail("struct-inline16-displacement","bounded disp8/disp32 destination",proof)
    store=(b"\x0f\x11\x40"+bytes([offset]) if displacement_width==1 else b"\x0f\x11\x80"+struct.pack("<i",offset))
    _program(image,normal,rows,[bytes.fromhex(h) for h in ["837B3010","488B2F"]]
        +[_branch(rows,2,"0F8C",fail)]+[bytes.fromhex(h) for h in ["488B4350","0F1000","0F11442420","8B7330","83EE10"]]
        +[_branch(rows,8,"0F88",fail)]+[bytes.fromhex(h) for h in ["4883435010","83434010","83434410","897330","4885ED"]]
        +[_branch(rows,14,"0F84",fail)]+[bytes.fromhex(h) for h in ["33D2","488BCD"]]+[getter,bytes.fromhex("4885C0")]
        +[_branch(rows,19,"0F84",fail)]+[bytes.fromhex("0F10442420"),bytes.fromhex("488BCB"),store],label=label,fail=fail)
    if (rows[0][0]<previous or rows[17][0]!=proof["getterCall"]["rva"] or rows[-1][0]!=assignment["rva"]
            or assignment["rawHex"]!=store.hex().upper()):
        fail("struct-inline-transfer","buffer16 -> cursor16 -> same stack20 -> entire runtime field",proof)


def check_inline12(image: Any, member: dict, record: dict, sizes: dict, normal: dict,
                   previous: int, *, label: str, fail: Callable[..., None]) -> None:
    proof=member["inlineSource"];assignment=member["assignment"];rows=proof.get("instructions",[])
    profiles={
        "wrapper-rsi-remaining-ebp": ["488B37","8B6B30","83ED0C","896B30","4885F6","488BCE"],
        "wrapper-rbp-remaining-esi": ["488B2F","8B7330","83EE0C","897330","4885ED","488BCD"]}
    profile=proof.get("registerProfile","wrapper-rsi-remaining-ebp")
    restore=proof.get("restoresReaderArgument",True)
    temporary=proof.get("temporaryStackOffset",0x48)
    if (proof.get("mode")!="inline-cursor-struct12" or member["kind"]!="raw12"
            or sizes.get(member["declaredType"])!=12 or proof.get("width")!=12
            or record.get("sourceArgumentRoles",{}).get("mode")!="reader-rbx-wrapper-ref-rdi"
            or member.get("sourceContextInstructionRva") is not None
            or assignment["kind"]!="direct-store" or assignment["baseRegister"]!=0
            or profile not in profiles or type(restore) is not bool
            or type(temporary) is not int or not 0<=temporary<=127
            or len(rows)!=24+int(restore)):
        fail("struct-inline12-type","explicit twelve-byte field, register profile and argument roles",proof)
    getter=_getter(image,proof,record,label=label,fail=fail)
    offset=assignment["fieldOffset"]
    if type(offset) is not int or not 0<=offset<=(1<<31)-9:
        fail("struct-inline12-offset","bounded complete disp8/disp32 field stores",offset)
    def displacement(value: int, short: str, wide: str) -> bytes:
        return bytes.fromhex(short)+bytes([value]) if value<=127 else bytes.fromhex(wide)+value.to_bytes(4,'little',signed=True)
    store=displacement(offset,"F20F1140","F20F1180")
    tail_store=displacement(offset+8,"448970","4489B0")
    wrapper,remaining,subtract,publish,test,receiver=(bytes.fromhex(h) for h in profiles[profile])
    _program(image,normal,rows,[bytes.fromhex("837B300C"),wrapper]
        +[_branch(rows,2,"0F8C",fail)]+[bytes.fromhex(h) for h in [
            "488B4350","F20F1000","448B7008"]]+[bytes.fromhex("F20F114424")+bytes([temporary])]+[remaining,subtract]
        +[_branch(rows,9,"0F88",fail)]+[bytes.fromhex(h) for h in [
            "488343500C","8343400C","8343440C"]]+[publish,test]
        +[_branch(rows,15,"0F84",fail)]+[bytes.fromhex("33D2"),receiver,getter,
            bytes.fromhex("4885C0"),_branch(rows,20,"0F84",fail),bytes.fromhex("F20F104424")+bytes([temporary])]
        +([bytes.fromhex("488BCB")] if restore else [])+[store,tail_store],label=label,fail=fail)
    if (rows[0][0]<previous or rows[18][0]!=proof["getterCall"]["rva"]
            or rows[-2][0]!=assignment["rva"] or assignment["rawHex"]!=store.hex().upper()
            or assignment.get("tailStores")!=[{"rva":rows[-1][0],"rawHex":tail_store.hex().upper(),"offsetDelta":8}]):
        fail("struct-inline12-transfer","buffer12 -> cursor12 -> same reviewed stack slot and r14d -> complete field",proof)


def check_provider32(image: Any, source: dict, member: dict, record: dict, normal: dict,
                     previous: int, *, label: str, fail: Callable[..., None]) -> None:
    """Join a typed variable-wire value to a complete 32-byte runtime copy.

    The helper zeroes and forwards a result buffer to provider dispatch. Its
    output width does not assert a wire width or a live formatter selection.
    """
    proof=member.get("providerOutputSource") or {};assignment=member["assignment"]
    context=next((c for c in source["nestedContexts"] if c["instructionRva"]==member.get("sourceContextInstructionRva")),None)
    if (proof.get("mode")!="provider-output32" or proof.get("runtimeValueBytes")!=32
            or context is None or context.get("typeKind")!=17 or assignment["kind"]!="direct-store"
            or context["typeDefinition"]!=proof.get("runtimeValueTypeDefinition")):
        fail("struct-provider32-type","typed value and explicit complete buffer proof",proof)
    runtime=image.metadata.types[context["typeDefinition"]]
    sizes=int(image.registration["typeDefinitionsSizes"],16)
    extent=image.pe.u32_at_va(image.pe.u64_at_va(sizes+runtime.index*8))-16
    if (extent!=32 or image.metadata.metadata_type_name(runtime.parent_index)!="System.ValueType"
            or image.type_name(runtime.index)!=member["declaredType"]):
        fail("struct-provider32-runtime","selected thirty-two-byte value",extent)
    definition=image.metadata.methods[context["methodSpec"][0]]
    identity=[definition.index,image.type_name(definition.declaring_type),image.metadata.string(definition.name_index)]
    section=image.metadata.sections["genericContainers"];at=section.offset+definition.generic_container_index*16
    if definition.generic_container_index<0 or not section.offset<=at<=section.offset+section.size-16:
        fail("struct-provider32-container","bounded method generic container",definition.generic_container_index)
    container=struct.unpack_from("<iiii",image.metadata.buf,at)
    table=int(image.registration["types"],16)
    result=image.pe.bytes_at_va(image.pe.u64_at_va(table+definition.return_type*8),16)
    if (identity!=proof.get("sourceDefinition") or identity[1:]!=["MemoryPack.MemoryPackReader","ReadValue"]
            or definition.flags&0x10 or definition.parameter_count!=0 or container[:3]!=(definition.index,1,1)
            or len(result)!=16 or result[10:12]!=b"\x1e\0" or int.from_bytes(result[:8],"little")!=container[3]):
        fail("struct-provider32-return","instance ReadValue<T>() sole undecorated MVAR",identity)
    check_reader_ref_wrapper_abi(image,record,fail=fail)
    arguments=proof.get("argumentInstructions",[]);prefix=proof.get("normalPrefix",[])
    if (not prefix or prefix[0][0]!=normal["startRva"] or not arguments
            or prefix[-1][0]+len(bytes.fromhex(prefix[-1][1]))!=arguments[-1][0]):
        fail("struct-provider32-prefix","incoming reader/ref wrapper survive to final dereference",prefix)
    _check_pointer_aliases(image,normal,prefix,label=label,fail=fail)
    _program(image,normal,arguments,[bytes.fromhex("488BD3"),bytes.fromhex(context["instructionHex"]),
        bytes.fromhex("488D4C2420"),bytes.fromhex("488B3F")],label=label,fail=fail)
    helper=proof["helper"];window=next((w for w in source["codeWindows"] if w["startRva"]==helper["windowStartRva"]),None)
    if window is None or member["sourceCall"]["targetRva"]!=window["startRva"]:
        fail("struct-provider32-helper","actual selected source helper",helper)
    rows=helper["normalInstructions"]
    short=[]
    for index in (8,14,19):
        raw=bytes.fromhex(rows[index][1])
        if len(raw)!=2 or raw[0]!=0x74:fail("struct-provider32-branch","JE rel8",rows[index])
        short.append(raw)
    carrier=bytes.fromhex(rows[12][1])
    if len(carrier)!=7 or not carrier.startswith(bytes.fromhex("488B0D")):
        fail("struct-provider32-carrier","selected rip-relative carrier load",rows[12])
    provider=_call(image,helper["providerCall"],label=label,fail=fail)
    dispatch=_call(image,helper["dispatchCall"],label=label,fail=fail)
    _program(image,window,rows,[bytes.fromhex(h) for h in ["48895C2408","4889742410","57","4883EC20",
        "4983783800","498BF8","488BF2","488BD9"]]+[short[0]]
        +[bytes.fromhex("0F57C0"),bytes.fromhex("0F1103"),bytes.fromhex("0F114310"),carrier,
          bytes.fromhex("83B9E000000000"),short[1]]
        +[bytes.fromhex("488B4738"),bytes.fromhex("488B08"),provider,bytes.fromhex("4885C0"),short[2]]
        +[bytes.fromhex("4C8BCB"),bytes.fromhex("4C8BC6"),bytes.fromhex("488BD0"),dispatch]
        +[bytes.fromhex(h) for h in ["488BC3","488B5C2430","488B742438","4883C420","5F","C3"]],label=label,fail=fail)
    if (rows[0][0]!=window["startRva"] or rows[17][0]!=helper["providerCall"]["rva"]
            or rows[23][0]!=helper["dispatchCall"]["rva"]
            or rows[19][0]+2+struct.unpack("b",short[2][1:])[0]!=rows[24][0]):
        fail("struct-provider32-helper-flow","output32 and original reader reach dispatch then common return",helper)
    # The parent's wrapper holds an exact reference Data, separate from the
    # returned inline value. Its field offset is authenticated independently.
    fields=[f for f in image.metadata.fields_for(image.metadata.types[record["wrapperTypeDefinition"]])
            if image.metadata.string(f.name_index)=="__instance"]
    raw=image.pe.bytes_at_va(image.pe.u64_at_va(table+fields[0].type_index*8),16) if len(fields)==1 else b""
    offsets=runtime_type_field_offsets(image.metadata,image.pe,image.registration,record["wrapperTypeDefinition"])
    if (len(raw)!=16 or raw[10:12]!=b"\x12\0" or int.from_bytes(raw[8:10],"little")&0x10
            or int.from_bytes(raw[:8],"little")!=record["runtimeTypeDefinition"] or offsets.get("__instance")!=16):
        fail("struct-provider32-parent-instance","exact reference Data at wrapper offset sixteen",raw.hex())
    bridge=proof["bridgeInstructions"];offset=assignment["fieldOffset"]
    if not 0<=offset<=111:fail("struct-provider32-offset","two complete disp8 stores",offset)
    store=bytes.fromhex("0F1141")+bytes([offset]);tail=bytes.fromhex("0F1149")+bytes([offset+16])
    _program(image,normal,bridge,[bytes.fromhex("4885FF"),_branch(bridge,1,"0F84",fail),
        bytes.fromhex("488B4F10"),bytes.fromhex("4885C9"),_branch(bridge,4,"0F84",fail),
        bytes.fromhex("0F10442420"),bytes.fromhex("0F104C2430"),store,tail],label=label,fail=fail)
    if (not previous<=arguments[0][0] or arguments[1][0]!=context["instructionRva"]
            or arguments[-1][0]+3!=member["sourceCall"]["rva"]
            or member["sourceCall"]["rva"]+5!=bridge[0][0] or assignment["rva"]!=bridge[7][0]
            or assignment["baseRegister"]!=1 or assignment["rawHex"]!=store.hex().upper()
            or assignment.get("tailStores")!=[{"rva":bridge[8][0],"rawHex":tail.hex().upper(),"offsetDelta":16}]):
        fail("struct-provider32-transfer","typed output stack20/30 -> exact wrapper Data -> full field",proof)


def _check_scalar_type(image,member,fail):
    if member['declaredType']=='int':return
    types=[t for t in image.metadata.types if image.type_name(t.index)==member['declaredType']]
    if len(types)!=1 or image.metadata.metadata_type_name(types[0].parent_index)!='System.Enum':
        fail('inline-scalar32-type','Int32 or an independently typed Int32 enum',member['declaredType'])
    fields=[f for f in image.metadata.fields_for(types[0]) if image.metadata.string(f.name_index)=='value__']
    table=int(image.registration['types'],16)
    raw=image.pe.bytes_at_va(image.pe.u64_at_va(table+fields[0].type_index*8),16) if len(fields)==1 else b''
    if len(raw)!=16 or raw[10]!=8 or raw[11]&0x7f or int.from_bytes(raw[8:10],'little')&0x10:
        fail('inline-scalar32-enum','nonstatic undecorated Int32 underlying value',raw.hex())

def check_inline_scalar32(image: Any, member: dict, record: dict, normal: dict, previous: int,
                          *, label: str, fail: Callable[..., None]) -> None:
    """Prove a buffered Int32 read and complete store through the typed wrapper.

    The enum underlying type, incoming ref ABI, retained pointer aliases and
    actual ancestor field are checked independently. Bounds/null branches
    leave this normal program; cold/refill behavior remains outside it.
    """
    p=member.get('inlineSource') or {};a=member['assignment'];rows=p.get('instructions',[]);prefix=p.get('parentPrefix',[])
    if (p.get('mode')!='inline-cursor-scalar32' or p.get('width')!=4 or member['kind']!='scalar32'
            or a['kind']!='direct-store' or a['baseRegister']!=0
            or member.get('sourceCall') is not None or member.get('sourceContextInstructionRva') is not None
            or len(rows)!=18 or not prefix or prefix[0][0]!=normal['startRva']
            or prefix[-1][0]+len(bytes.fromhex(prefix[-1][1]))!=rows[0][0]
            or rows[0][0]<previous):
        fail('inline-scalar32-shape','explicit int32 read without invented source call',p)
    check_reader_ref_wrapper_abi(image,record,fail=fail)
    _check_scalar_type(image,member,fail)
    _program(image,normal,prefix,[bytes.fromhex(r[1]) for r in prefix],label=label,fail=fail)
    seen=set();aliases={'rbx':'488BD9','rsi':'488BF2'}
    for at,h in prefix:
        raw=bytes.fromhex(h);ins=image.mapper.decode_x64_subset(raw,image.pe.image_base+at,stop_offset=len(raw))
        if len(ins)!=1 or ins[0]['text'].startswith('db'):fail('inline-scalar32-prefix-instruction','complete decoded instruction',[at,h])
        write=ins[0].get('write') or {};reg=write.get('register')
        if reg in {'rbx','ebx','bx','bl','bh','rsi','esi','si','sil'}:
            if reg not in aliases or reg in seen or h!=aliases[reg]:fail('inline-scalar32-alias-clobber',aliases,[at,h,write])
            seen.add(reg)
        if raw[:1]==b'\xe8' and seen!=set(aliases):fail('inline-scalar32-late-alias',set(aliases),seen)
    if seen!=set(aliases):fail('inline-scalar32-missing-alias',set(aliases),seen)
    owner=a['fieldOwnerTypeDefinition'];runtime=image.metadata.types[record['runtimeTypeDefinition']]
    if owner!=runtime.index and image.metadata.metadata_type_name(runtime.parent_index)!=image.type_name(owner):
        fail('inline-scalar32-instance-owner','runtime Data or its exact immediate parent',owner)
    types={image.type_name(t.index):t for t in image.metadata.types}
    instance=p.get('wrapperInstanceField') or {}
    if (not isinstance(instance.get('fieldName'),str) or not instance['fieldName']
            or instance.get('referenceTypeDefinition')!=owner or instance.get('offset')!=16):
        fail('inline-scalar32-instance-declaration','selected named ancestor reference field',instance)
    td=image.metadata.types[record['wrapperTypeDefinition']];fields=[]
    while True:
        if td.index==instance.get('declaringTypeDefinition'):
            fields.extend((td,f) for f in image.metadata.fields_for(td) if image.metadata.string(f.name_index)==instance['fieldName'])
        parent=image.metadata.metadata_type_name(td.parent_index)
        if parent=='System.Object':break
        if parent not in types:fail('inline-scalar32-wrapper-ancestry','bounded named wrapper ancestry',parent)
        td=types[parent]
    table=int(image.registration['types'],16)
    raw=image.pe.bytes_at_va(image.pe.u64_at_va(table+fields[0][1].type_index*8),16) if len(fields)==1 else b''
    offsets=runtime_type_field_offsets(image.metadata,image.pe,image.registration,fields[0][0].index) if len(fields)==1 else {}
    if (len(raw)!=16 or raw[10:12]!=b'\x12\0' or int.from_bytes(raw[8:10],'little')&0x10
            or int.from_bytes(raw[:8],'little')!=owner or offsets.get(instance['fieldName'])!=16):
        fail('inline-scalar32-wrapper-instance','typed Data owner reference at wrapper offset sixteen',raw.hex())
    offset=a['fieldOffset']
    real=runtime_type_field_offsets(image.metadata,image.pe,image.registration,owner)
    if real.get(member['fieldName'])!=offset or type(offset) is not int or not 0<=offset<=127:
        fail('inline-scalar32-field-offset','actual bounded owned field',real)
    store=bytes.fromhex('448970')+bytes([offset])
    _program(image,normal,rows,[bytes.fromhex('837B3004'),bytes.fromhex('488B2E'),_branch(rows,2,'0F8C',fail)]
        +[bytes.fromhex(h) for h in ['488B4350','448B30','8B7B30','83EF04']]+[_branch(rows,7,'0F88',fail)]
        +[bytes.fromhex(h) for h in ['4883435004','83434004','83434404','897B30','4885ED']]+[_branch(rows,13,'0F84',fail)]
        +[bytes.fromhex('488B4510'),bytes.fromhex('4885C0'),_branch(rows,16,'0F84',fail),store],label=label,fail=fail)
    if rows[-1][0]!=a['rva'] or a['rawHex']!=store.hex().upper():fail('inline-scalar32-transfer','source DWORD -> r14d -> full exact field',a)
    for index in (2,7,13,16):
        at,h=rows[index];target=at+6+struct.unpack_from('<i',bytes.fromhex(h),2)[0]
        if rows[0][0]<=target<rows[-1][0]+len(store):fail('inline-scalar32-bounds-branch','bounds/null failure leaves the copy',target)
