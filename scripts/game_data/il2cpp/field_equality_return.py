"""A typed reference argument's Int32 enum read becomes an equality index."""
import re
from scripts.game_data.il2cpp.consumer_control import check_consumer_control
from scripts.game_data.il2cpp.consumer_reference_origins import check_reference_origins
from scripts.game_data.il2cpp.initializer_control import control_transfer
from scripts.game_data.il2cpp.memory_moves import decode_memory_move
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.type_data_initialization_instructions import decode_type_data_initialization_instructions


def check_field_equality_program(mapper, rows, *, entry, owned_ranges, field_offset, true_value, activation):
    control = check_consumer_control(rows, entry=entry, owned_ranges=owned_ranges)
    refs = check_reference_origins(rows, entry=entry, owned_ranges=owned_ranges,
        incoming_registers={'rcx':'this','rdx':'selected-argument'}, incoming_stack_slots={}, selected_call_returns={})
    if min(int(row['va'],16) for row in rows) != entry or not 0 <= true_value < 128:
        raise ValueError('fieldEqualityReturn.entry-or-small-enum')
    rows = [dict(row,offset=int(row['va'],16)-entry) for row in rows]
    states = mapper._instruction_origin_states(rows,entry,{'rcx':'this','rdx':'selected-argument'},
        {at-entry:frame[0] for at,frame in control['frames'].items()}, {})
    by_at = {int(row['va'],16):row for row in rows}
    def following(row):return int(row['va'],16)+len(bytes.fromhex(row['bytes']))
    def epilogue(at):
        seen=set()
        while at in by_at and at not in seen:
            seen.add(at); row=by_at[at]; flow=control_transfer(row)
            if flow['kind']=='return':return True
            if flow['kind']=='jump':at=flow['target'];continue
            if flow['kind']!='next' or not (row['text']=='nop'
                    or re.fullmatch(r'mov (?:rbx|rbp|rsi|rdi|r1[2-5]), \[rsp(?:\+0x[0-9a-f]+)?\]',row['text'])
                    or re.fullmatch(r'add rsp, 0x[0-9a-f]+',row['text'])
                    or re.fullmatch(r'pop (?:rbx|rbp|rsi|rdi|r1[2-5])',row['text'])):return False
            at=following(row)
        return False
    calls=[call['site'] for call in control['calls'] if call['kind']=='call' and call['target']==activation
           and refs['registerOrigins'][call['site']]['rcx']==['selected-argument']]
    candidates=[]
    for row in rows:
        at=int(row['va'],16); raw=bytes.fromhex(row['bytes'])
        decoded=decode_memory_move(raw,0,at)
        if not decoded or decoded[1]!=len(raw):continue
        op=decoded[0]['memoryOperation']; address=op['address']
        if ((op['direction'],op['memoryBytes'],op['registerBits'],op['backingRegister'],address.get('index'),address.get('ripRelative'),address.get('displacement'))
                !=('load',4,32,'rbx',None,False,field_offset)
                or refs['registerOrigins'][at].get(address.get('base'))!=['selected-argument']):continue
        # Removing the activation instruction must disconnect this read from entry.
        dominated=[]
        for call in calls:
            reached=set(); pending=[entry]
            while pending:
                current=pending.pop()
                if current in reached or current==call:continue
                reached.add(current); pending.extend(control['edges'][current]-reached)
            if at not in reached:dominated.append(call)
        if len(dominated)!=1:continue
        cursor=following(row)
        for _ in range(12):
            current=by_at.get(cursor)
            if current is None:break
            if bytes.fromhex(current['bytes'])==bytes((0x83,0xfb,true_value)):
                predicate=by_at.get(following(current),{}); result=by_at.get(following(predicate),{}) if predicate else {}
                origins=states.get(int(predicate.get('va','0'),16)-entry,({},{}))[0]
                if (predicate.get('bytes')=='40 0f 94 c6' and result.get('bytes')=='8b c6'
                        and origins.get('rsi') in ('0','0x0') and epilogue(following(result))):
                    candidates.append(dict(read=row,activation=dominated[0],comparison=current,predicate=predicate,result=result))
                break
            flow=control_transfer(current)
            if flow['kind']=='call':pass  # RBX and RSI are nonvolatile in the ordinary Win64 ABI.
            elif flow['kind']!='next' or not re.fullmatch(r'mov (?:ecx|edx|r8d|r9d|rcx|rdx|r8|r9), (?:0x[0-9a-f]+|rbx|rbp|rsi|rdi)',current['text']):break
            cursor=following(current)
    if len(candidates)!=1:raise ValueError('fieldEqualityReturn.unique-dominated-read-equality-return')
    return dict(profile=candidates[0],control=control,referenceOrigins=refs,evidenceBoundary='conditional',
        condition='After the checked activation returns normally, the selected argument field read returns index one exactly for the selected enum value, otherwise zero. Ordinary Win64 callee preservation and frame restoration only; IFix replacement paths and runtime execution remain separate.')


def check_field_equality_return(index, body, spec):
    if (not isinstance(spec,dict) or set(spec)!={'parameter','field','enumMember','activation'}
            or any(not isinstance(value,str) or not value for value in spec.values())):
        raise ValueError('fieldEqualityReturn.named-profile')
    image=index.image; metadata=image.metadata; selected=NativeReferenceContext(image)
    declarations=[row for row in index.names_by_pointer.get(body.pointer,[]) if row['type']+'.'+row['method']==body.symbol]
    if len(declarations)!=1:raise ValueError('fieldEqualityReturn.unique-caller')
    method=metadata.methods[declarations[0]['methodIndex']]; owner=metadata.types[method.declaring_type]
    params=list(metadata.parameters_for(method))
    if (method.flags&0x10 or method.generic_container_index>=0 or owner.generic_container_index>=0
            or selected.is_value_type(metadata.type_full_name(owner)) or selected.type_name(method.return_type)!='int'
            or len(params)!=1 or metadata.string(params[0].name_index)!=spec['parameter']):
        raise ValueError('fieldEqualityReturn.instance-int32-single-parameter')
    selected.require_ordinary_kind(method.return_type,0x08)
    selected.require_ordinary_kind(params[0].type_index,0x12)
    field_owner,kind,offset=selected.field(spec['field'])
    if (selected.type_name(params[0].type_index)!=field_owner or selected.is_value_type(field_owner)
            or not selected.is_enum(kind) or selected.field(kind+'::value__')[1]!='int'
            or any(len(image.named_type_definitions.get(name,()))!=1 for name in (metadata.type_full_name(owner),field_owner,kind))):
        raise ValueError('fieldEqualityReturn.typed-reference-and-enum')
    true_value=index.enum_member_id(kind,spec['enumMember'])
    pointers=index.pointers_by_name.get(spec['activation'],set())
    if len(pointers)!=1:raise ValueError('fieldEqualityReturn.unique-activation')
    activation=next(iter(pointers))
    targets=[row for row in index.names_by_pointer.get(activation,[]) if row['type']+'.'+row['method']==spec['activation']]
    if len(targets)!=1:raise ValueError('fieldEqualityReturn.unique-activation-declaration')
    target=metadata.methods[targets[0]['methodIndex']]
    if (target.flags&0x10 or target.generic_container_index>=0 or metadata.types[target.declaring_type].generic_container_index>=0
            or metadata.type_full_name(metadata.types[target.declaring_type])!=field_owner or selected.type_name(target.return_type)!='void'):
        raise ValueError('fieldEqualityReturn.activation-reference-instance-void-abi')
    selected.require_ordinary_kind(target.return_type,0x01)
    rows=[]; base=image.pe.image_base
    ranges=[(base+row['runtimeTriple'][0],base+row['runtimeTriple'][1]) for row in image.unwind_index.family(body.pointer-base)['ranges']]
    for a,b in sorted(ranges):rows+=decode_type_data_initialization_instructions(image.mapper,image.pe.bytes_at_va(a,b-a),a)
    return check_field_equality_program(image.mapper,rows,entry=body.pointer,owned_ranges=ranges,
        field_offset=offset,true_value=true_value,activation=activation)
