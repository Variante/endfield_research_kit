"""Reviewed generated-record source calls and unchanged return/field transfers.

The caller authenticates the opened image and owns the wire grammar, selected
provider conditions and whole-source admission. These helpers never select a
game root or infer a serialized grammar from a field name.
"""
from __future__ import annotations

from scripts.game_data.il2cpp import protocol
from scripts.game_data.il2cpp.body_claims import _writes_register
from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
from scripts.game_data.il2cpp.reference_field_programs import preserved_argument


def normal_source_rows(rows):
    """Elide only a null failure ending in INT3 and explicitly bypassed by JNE."""
    omitted = set()
    for i in range(3,len(rows)-1):
        guard,branch,call,trap = rows[i-3:i+1]
        if (trap["text"] == "int3" and guard["text"] == "test rsi, rsi"
                and branch["text"] == f"jne {int(rows[i+1]['va'],16):#x}"
                and call["text"].startswith("call ")):
            omitted.update((i-1,i))
    return [row for i,row in enumerate(rows) if i not in omitted]


def typed_source_context(image, setup, *, field, method, argument):
    loads = [i for i,row in enumerate(setup) if bytes.fromhex(row["bytes"])[:3] == b"\x48\x8b\x15"]
    if len(loads) != 1 or any(_writes_register(row,"rdx") for row in setup[loads[0]+1:]):
        raise ValueError(f"recordSource.contextLoad:{field}:expected=one-unclobbered-RDX-load:actual={len(loads)}")
    context = derive_typed_usage_context(image,int(setup[loads[0]]["va"],16)-image.pe.image_base,label="recordSource")
    if (context.get("tag") != 6 or context.get("typeName") != "MemoryPack.MemoryPackReader"
            or context.get("methodName") != method or context.get("classArguments") != []
            or [protocol.canonical_type_name(arg) for arg in context.get("methodArguments",[])] != [protocol.canonical_type_name(argument)]):
        raise ValueError(f"recordSource.typedSource:{field}:expected={method}<{argument}>:actual={context}")
    declaration = image.metadata.methods[context["methodSpec"][0]]
    if declaration.parameter_count != 0 or declaration.flags & 16:
        raise ValueError(f"recordSource.readerABI:{field}:expected=instance/no-formal-arguments")
    return context


def ordered_record(build, reviewed):
    from scripts.game_data.buff_frontiers_regenerate import _method_row
    from scripts.game_data.il2cpp.type_data_initialization_instructions import decode_type_data_initialization_instructions
    from scripts.game_data.levelscript_family_regenerate import select_calls
    from scripts.game_data.levelscript_two_routes_native import _window
    from scripts.game_data.skill_custom_root_motion_regenerate import prove_primitive
    image = build.image
    base = image.pe.image_base
    wrapper = build.wrappers[reviewed["wrapperName"]]
    fields = [[m.name,protocol.canonical_type_name(m.declared_type)] for m in wrapper.members]
    expected = [[name,protocol.canonical_type_name(kind)] for name,kind in reviewed["fields"]]
    if wrapper.wrapped_type != reviewed["typeName"] or fields != expected:
        raise ValueError(f"recordSource.declarations:{reviewed['typeName']}")
    body = image.body_index.body(wrapper.name,"Deserialize")
    rows = decode_type_data_initialization_instructions(image.mapper,image.pe.bytes_at_va(body.pointer,body.size),body.pointer)
    setters = [_method_row(image,[0,m.declaring_wrapper,f"set___{m.name}__",0]) for m in wrapper.members]
    header,reads,writes,setups = select_calls(normal_source_rows(rows),len(fields),[base+s[3] for s in setters])
    plan = []
    for member,read,write,setter,setup in zip(wrapper.members,reads,writes,setters,setups,strict=True):
        target = int(read["text"].split()[1],16)
        proof = "ordered-source-call"
        if member.kind == "string":
            build.prove_pooled_string_target(target)
            proof = "signed-pool-index-helper"
        elif member.kind == "bool":
            prove_primitive(image,target,"bool-byte")
            proof = "buffered-byte-normalized-Boolean"
        context = None
        if member.kind in ("list","object","enum"):
            method = "ReadUnmanaged" if member.kind == "enum" else "ReadPackable" if member.kind == "list" or member.declared_type.startswith("System.Collections.Generic.Dictionary`2<") else "ReadValue"
            context = typed_source_context(image,setup,field=member.name,method=method,argument=member.declared_type)
        plan.append({"field":member.name,"readRva":int(read["va"],16)-base,"targetRva":target-base,
                     "setter":setter,"transferRva":int(write["va"],16)-base,"proof":proof,"typedContext":context})
    windows = {(body.pointer,body.pointer+body.size)}
    windows.update((start,start+size) for start,size in image.body_index.chained_fragments.get(body.pointer,()))
    return {"typeName":reviewed["typeName"],"wrapperName":wrapper.name,"fields":reviewed["fields"],
            "method":_method_row(image,[0,wrapper.name,"Deserialize",0]),
            "memberCountInstruction":[int(header["va"],16)-base,header["bytes"]],"orderedReads":plan,
            "codeWindows":[_window(image,start,end,"complete owned reader coverage") for start,end in sorted(windows)]}


def return_field_source(image, rows, field, offset, *, value_register="rax"):
    """Prove preserved entry arguments and a guarded unchanged return store."""
    if value_register not in ("al","rax"):
        raise ValueError(f"recordSource.returnRegister:{field}:{value_register}")
    stores = [i for i,row in enumerate(rows) if row["text"] in (
        f"mov [r8+0x{offset:x}], {value_register}",f"mov [rcx+0x{offset:x}], {value_register}")]
    if len(stores) != 1:
        raise ValueError(f"recordSource.fieldStore:{field}:expected=1:actual={len(stores)}")
    store = stores[0]
    instance = rows[store]["text"].split("[",1)[1].split("+",1)[0]
    candidates = []
    for call in (store-6,store-7):
        if call < 0 or not rows[call]["text"].startswith("call 0x"):continue
        flow = rows[call+1:store]
        if len(flow) == 6 and flow[-1]["text"].startswith("cmp dword [rip"):
            flow = flow[:-1]
        if len(flow) != 5:continue
        wrapper = flow[0]["text"].split(" ",1)[-1].split(",",1)[0]
        expected = [f"test {wrapper}, {wrapper}",None,f"mov {instance}, [{wrapper}+0x10]",f"test {instance}, {instance}",None]
        if all(wanted is None or row["text"] == wanted for row,wanted in zip(flow,expected)):
            candidates.append((call,wrapper,flow))
    if len(candidates) != 1:
        raise ValueError(f"recordSource.returnTransfer:{field}:expected=one-complete-guarded-transfer:actual={len(candidates)}")
    call,wrapper,flow = candidates[0]
    reader,holder = (preserved_argument(rows[:call],register) for register in ("rcx","rdx"))
    setup = rows[max(0,call-4):call]
    moves = [i for i,row in enumerate(setup) if row["text"] == f"mov rcx, {reader}"]
    if (len(moves) != 1 or any(_writes_register(row,"rcx") for row in setup[moves[0]+1:])
            or not any(row["text"] == f"mov {wrapper}, [{holder}]" for row in setup)):
        raise ValueError(f"recordSource.entryArguments:{field}:reader={reader}:holder={holder}")
    for row in (flow[1],flow[4]):
        raw = bytes.fromhex(row["bytes"])
        if not (len(raw) == 2 and raw[0] == 0x74 or len(raw) == 6 and raw[:2] == b"\x0f\x84"):
            raise ValueError(f"recordSource.nullGuard:{field}:expected=JE:actual={raw.hex()}")
    return {"field":field,"fieldOffset":offset,"readerArgument":reader,"wrapperArgument":holder,
            "callRva":int(rows[call]["va"],16)-image.pe.image_base,
            "targetRva":int(rows[call]["text"].split()[1],16)-image.pe.image_base,
            "storeRva":int(rows[store]["va"],16)-image.pe.image_base}

def reference_field_source(image, rows, field, offset, *, pooled=False):
    result = return_field_source(image,rows,field,offset)
    if not pooled:
        call = next(i for i,row in enumerate(rows) if int(row["va"],16)-image.pe.image_base == result["callRva"])
        result["typedContext"] = typed_source_context(image,rows[max(0,call-4):call],field=field,
                                                    method="ReadPackable",argument="System.Collections.Generic.List`1<ulong>")
    return result


def prove_reference_setter_rows(rows, *, slot, field):
    """Prove the unchanged incoming reference store; barrier behavior is separate."""
    expected = ['sub rsp, 0x28',f'mov rcx, [rcx+0x{slot:x}]','test rcx, rcx',None,
                f'mov [rcx+0x{field:x}], rdx',f'add rcx, 0x{field:x}',
                'add rsp, 0x28',None,None,'int3']
    if len(rows) != len(expected) or any(wanted is not None and row['text'] != wanted
                                        for row,wanted in zip(rows,expected)):
        raise ValueError('recordSource.referenceSetter:complete-program-differs')
    branch,tail,trap = (rows[i] for i in (3,7,8))
    raw = bytes.fromhex(branch['bytes'])
    if (raw[:1] != b'\x74' or len(raw) != 2
            or int(branch['va'],16)+2+int.from_bytes(raw[1:],'little',signed=True) != int(trap['va'],16)
            or not tail['text'].startswith('jmp 0x') or not trap['text'].startswith('call 0x')):
        raise ValueError('recordSource.referenceSetter:null-or-tail-branch-differs')


def setter_reference_source(build, rows, member):
    from scripts.game_data.il2cpp.reference_field_programs import _setter_metadata,reader_setup
    from scripts.game_data.il2cpp.type_data_initialization_instructions import decode_type_data_initialization_instructions
    from scripts.game_data.levelscript_two_routes_native import _window
    from scripts.game_data.buff_frontiers_regenerate import _method_row
    image=build.image;base=image.pe.image_base
    context,wrapper,field,target,offset,method=_setter_metadata(image,build.wrappers,member)
    if member.kind != 'string' or context.field(wrapper.name+'::__instance') != (wrapper.name,wrapper.wrapped_type,16):
        raise ValueError(f'recordSource.referenceSetter:{member.name}:typed-reference-holder-differs')
    pointer=image.method_pointer_va(method)
    calls=[i for i,row in enumerate(rows) if row['text']==f'call {pointer:#x}']
    if len(calls)!=1 or calls[0]<6:
        raise ValueError(f'recordSource.setterCall:{member.name}:expected=1:actual={len(calls)}')
    setter=calls[0];call=setter-6
    if not rows[call]['text'].startswith('call 0x'):
        raise ValueError(f'recordSource.setterReturn:{member.name}:missing-source-call')
    _,reader,holder,receiver=reader_setup(rows,rows[call])
    flow=rows[call+1:setter]
    guard=bytes.fromhex(flow[1]['bytes'])
    if ([row['text'] for row in flow] != [f'test {receiver}, {receiver}',flow[1]['text'],
            'xor r8d, r8d','mov rdx, rax',f'mov rcx, {receiver}']
            or not (len(guard)==2 and guard[0]==0x74 or len(guard)==6 and guard[:2]==b'\x0f\x84')):
        raise ValueError(f'recordSource.setterTransfer:{member.name}:unchanged-return-or-null-guard-differs')
    slot=context.field(wrapper.name+'::__instance')[2]
    body=image.body_index.body(wrapper.name,image.metadata.string(method.name_index))
    if body.pointer!=pointer or image.body_index.chained_fragments.get(pointer):
        raise ValueError(f'recordSource.referenceSetter:{member.name}:owned-body-differs')
    setter_rows=decode_type_data_initialization_instructions(image.mapper,image.pe.bytes_at_va(pointer,body.size),pointer)
    prove_reference_setter_rows(setter_rows,slot=slot,field=offset)
    return {'field':member.name,'fieldOffset':offset,'readerArgument':reader,'wrapperArgument':holder,
            'callRva':int(rows[call]['va'],16)-base,'targetRva':int(rows[call]['text'].split()[1],16)-base,
            'setter':_method_row(image,[0,wrapper.name,image.metadata.string(method.name_index),0]),
            'setterCallRva':int(rows[setter]['va'],16)-base,
            'setterWindows':[_window(image,pointer,pointer+body.size,'complete reference setter; collector behavior is separate')]}



def bounded_reference_record(build, reviewed):
    """Prove reviewed declarations/count and selected reference-return sources only."""
    from scripts.game_data.buff_frontiers_regenerate import _type_definition, _method_row
    from scripts.game_data.il2cpp.type_data_initialization_instructions import decode_type_data_initialization_instructions
    from scripts.game_data.levelscript_two_routes_native import _window
    image = build.image
    wrapper = build.wrappers[reviewed["wrapperName"]]
    fields = [[m.name,protocol.canonical_type_name(m.declared_type)] for m in wrapper.members]
    expected = [[name,protocol.canonical_type_name(kind)] for name,kind in reviewed["fields"]]
    if wrapper.wrapped_type != reviewed["typeName"] or fields != expected:
        raise ValueError(f"recordSource.declarations:{reviewed['typeName']}")
    body = image.body_index.body(wrapper.name,"Deserialize")
    rows = decode_type_data_initialization_instructions(image.mapper,image.pe.bytes_at_va(body.pointer,body.size),body.pointer)
    headers = [row for row in rows if row["text"].startswith("cmp ") and row["text"].endswith(f", {len(fields):#x}") and len(bytes.fromhex(row["bytes"])) in (4,5)]
    if len(headers) != 1:
        raise ValueError(f"recordSource.memberCount:{reviewed['typeName']}:expected=1:actual={len(headers)}")
    offsets = protocol.runtime_type_field_offsets(image.metadata,image.pe,image.registration,_type_definition(image,wrapper.wrapped_type))
    holder_offsets = protocol.runtime_type_field_offsets(image.metadata,image.pe,image.registration,wrapper.type_definition)
    if holder_offsets.get("__instance") != 16:
        raise ValueError(f"recordSource.wrapperHolder:{wrapper.name}:expected=16:actual={holder_offsets.get('__instance')}")
    sources = []
    for field,kind in reviewed["sourceFields"]:
        if kind not in ("uint64-list","pooled-string","pooled-string-setter"):
            raise ValueError(f"recordSource.sourceKind:{field}:{kind}")
        source = (setter_reference_source(build,rows,next(m for m in wrapper.members if m.name==field))
                  if kind == "pooled-string-setter" else reference_field_source(image,rows,field,offsets[field],pooled=kind=="pooled-string"))
        if kind.startswith("pooled-string"):
            build.prove_pooled_string_target(image.pe.image_base+source["targetRva"])
        sources.append(source)
    lists = [source for source in sources if "typedContext" in source]
    if len({(source["targetRva"],source["typedContext"]["usageCellRva"]) for source in lists}) > 1:
        raise ValueError(f"recordSource.listSourceIdentity:{reviewed['typeName']}")
    spans = {(body.pointer,body.pointer+body.size)}|{(p,p+s) for p,s in image.body_index.chained_fragments.get(body.pointer,())}
    return {"typeName":reviewed["typeName"],"wrapperName":wrapper.name,"fields":reviewed["fields"],"sourceFields":reviewed["sourceFields"],
                    "method":_method_row(image,[0,wrapper.name,"Deserialize",0]),
                    "memberCountInstruction":[int(headers[0]["va"],16)-image.pe.image_base,headers[0]["bytes"]],
                    "fieldSources":sources,"codeWindows":[_window(image,start,end,"complete owned reader coverage") for start,end in sorted(spans)]}
