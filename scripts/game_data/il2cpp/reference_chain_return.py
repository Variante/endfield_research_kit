"""Conditional two-field reference return after a named false Boolean call."""
import re
from scripts.game_data.il2cpp.consumer_reference_origins import check_reference_origins
from scripts.game_data.il2cpp.initializer_control import control_transfer
from scripts.game_data.il2cpp.memory_moves import decode_memory_move
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.type_data_initialization_instructions import decode_type_data_initialization_instructions


def check_reference_chain_return(index, body, spec):
    if (not isinstance(spec,dict) or set(spec)!={'guard','fields'} or not isinstance(spec['guard'],str) or not spec['guard']
            or not isinstance(spec['fields'],list) or len(spec['fields'])!=2 or any(not isinstance(f,str) or not f for f in spec['fields'])):
        raise ValueError('referenceChainReturn.two-fields-and-guard')
    image=index.image; metadata=image.metadata; selected=NativeReferenceContext(image)
    def method_at(pointer,symbol,kind):
        declarations=[r for r in index.names_by_pointer.get(pointer,[]) if r['type']+'.'+r['method']==symbol]
        if len(declarations)!=1:raise ValueError('referenceChainReturn.unique-method')
        method=metadata.methods[declarations[0]['methodIndex']]; owner=metadata.types[method.declaring_type]
        if (metadata.type_full_name(owner)+'.'+metadata.string(method.name_index)!=symbol
                or method.generic_container_index>=0 or owner.generic_container_index>=0
                or image.method_pointer_va(method)!=pointer):
            raise ValueError('referenceChainReturn.method-identity-or-generics')
        raw=image.pe.bytes_at_va(selected.type_pointer(method.return_type),16)
        if len(raw)!=16 or raw[10]!=kind or raw[11]&0x7f:
            raise ValueError('referenceChainReturn.return-abi')
        return method,metadata.type_full_name(owner)
    caller,owner=method_at(body.pointer,body.symbol,0x12)
    if caller.flags&0x10 or list(metadata.parameters_for(caller)) or selected.is_value_type(owner):
        raise ValueError('referenceChainReturn.reference-instance-getter')
    fields=[selected.field(name) for name in spec['fields']]
    if fields[0][0]!=owner or fields[1][0]!=fields[0][1] or selected.type_name(caller.return_type)!=fields[1][1]:
        raise ValueError('referenceChainReturn.typed-owner-chain')
    for field in fields:
        if len(image.named_type_definitions.get(field[0],()))!=1 or len(image.named_type_definitions.get(field[1],()))!=1:
            raise ValueError('referenceChainReturn.ambiguous-field-type')
        td=selected.index.types.get(field[1])
        if td is None or td.generic_container_index>=0 or selected.is_value_type(field[1]):
            raise ValueError('referenceChainReturn.nongeneric-reference-fields')
    base=image.pe.image_base; family=image.unwind_index.family(body.pointer-base)
    ranges=[(base+r['runtimeTriple'][0],base+r['runtimeTriple'][1]) for r in family['ranges']]
    rows=[]
    for start,end in sorted(ranges):
        rows+=decode_type_data_initialization_instructions(image.mapper,image.pe.bytes_at_va(start,end-start),start)
    proof=check_reference_origins(rows,entry=body.pointer,owned_ranges=ranges,
        incoming_registers={'rcx':'this'},incoming_stack_slots={},selected_call_returns={})
    by_at={int(r['va'],16):r for r in rows}
    def next_at(row):return int(row['va'],16)+len(bytes.fromhex(row['bytes']))
    def load(row,offset,base_register):
        decoded=decode_memory_move(bytes.fromhex(row['bytes']),0,int(row['va'],16))
        if not decoded or decoded[1]!=len(bytes.fromhex(row['bytes'])):return False
        operation=decoded[0]['memoryOperation']; address=operation['address']
        return (operation['direction'],operation['memoryBytes'],operation['registerBits'],operation['backingRegister'],
                address.get('base'),address.get('index'),address.get('ripRelative'),address.get('displacement')) == (
                    'load',8,64,'rax',base_register,None,False,offset)
    def exit_without_rax_write(at):
        seen=set()
        while at in by_at and at not in seen:
            seen.add(at); row=by_at[at]; flow=control_transfer(row); text=row['text']
            if flow['kind']=='return':return True
            if flow['kind']=='jump':at=flow['target'];continue
            if flow['kind']!='next' or text.startswith('pop rax'):
                return False
            # Only the native frame-restoration subset may follow the result.
            if not (re.fullmatch(r'mov (?:rbx|rbp|rsi|rdi|r1[2-5]), \[rsp(?:\+0x[0-9a-f]+)?\]',text)
                    or re.fullmatch(r'add rsp, 0x[0-9a-f]+',text)
                    or re.fullmatch(r'pop (?:rbx|rbp|rsi|rdi|r1[2-5])',text) or text=='nop'):
                return False
            at=next_at(row)
        return False
    candidates=[]
    for call in rows:
        flow=control_transfer(call)
        if flow['kind']!='call' or spec['guard'] not in index.names_of(flow['target']):continue
        method_at(flow['target'],spec['guard'],2)
        test=by_at.get(next_at(call),{}); branch=by_at.get(next_at(test),{}) if test else {}
        if test.get('bytes')!='84 c0' or not branch:continue
        transfer=control_transfer(branch)
        raw=bytes.fromhex(branch['bytes'])
        if transfer['kind']!='conditional' or not (raw[:1]==b'\x75' or raw[:2]==b'\x0f\x85'):continue
        first=by_at.get(next_at(branch),{})
        if not first:continue
        origins=proof['registerOrigins'][int(first['va'],16)]
        receivers=[register for register,values in origins.items() if values==['this']]
        if not any(load(first,fields[0][2],register) for register in receivers):continue
        null_test=by_at.get(next_at(first),{}); nonnull=by_at.get(next_at(null_test),{}) if null_test else {}
        if null_test.get('bytes')!='48 85 c0' or not nonnull:continue
        edge=control_transfer(nonnull); encoded=bytes.fromhex(nonnull['bytes'])
        if edge['kind']!='conditional' or not (encoded[:1]==b'\x75' or encoded[:2]==b'\x0f\x85'):continue
        null_call=by_at.get(next_at(nonnull),{})
        if not null_call or control_transfer(null_call)['kind']!='call':continue
        trap=by_at.get(next_at(null_call),{})
        if trap.get('bytes')!='cc':continue
        second=by_at.get(edge['target'],{})
        if not second or not load(second,fields[1][2],'rax') or not exit_without_rax_write(next_at(second)):continue
        null_return=by_at.get(transfer['target'],{})
        if null_return.get('bytes')!='33 c0' or not exit_without_rax_write(next_at(null_return)):continue
        candidates.append(dict(guard=call,firstFieldRead=first,secondFieldRead=second,nullReturn=null_return))
    if len(candidates)!=1:raise ValueError('referenceChainReturn.unique-owned-return-profile')
    return dict(profile=candidates[0],fields=fields,referenceControl=proof,evidenceBoundary='conditional',
        condition='The checked named Boolean guard returns ordinarily: false returns the current two-field reference chain; true returns null. Original fallback paths and ordinary native frame restoration only; IFix replacement results and runtime execution remain separate.')
