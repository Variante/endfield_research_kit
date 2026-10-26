"""Typed current action dispatch proof, including the selected Int32 list body."""
import struct
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext, closed_generic_reference_extent, validate_reference_ancestor_chain
from scripts.game_data.il2cpp.context import usage_method_spec
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.memory_moves import decode_memory_move
from scripts.game_data.il2cpp.owned_consumer_instructions import read_owned_consumer_instructions
from scripts.game_data.il2cpp.initializer_control import control_transfer
from scripts.game_data.il2cpp.list_item_program import check_list_item_program
from scripts.game_data.il2cpp.action_branch_program import check_action_branch_program


def check_action_branch_flow(index,body,spec):
    label='actionBranchFlow'
    if (not isinstance(spec,dict) or set(spec)!={'fields','ancestors'} or not isinstance(spec['fields'],dict)
            or set(spec['fields'])!={'list','index','id','reserved','next'}
            or any(not isinstance(value,str) or not value for value in spec['fields'].values())):
        raise ValueError(label+'.named-fields-and-ancestors')
    image=index.image;metadata=image.metadata;context=NativeReferenceContext(image)
    declarations=[r for r in index.names_by_pointer.get(body.pointer,()) if r['type']+'.'+r['method']==body.symbol]
    if len(declarations)!=1:raise ValueError(label+'.unique-caller')
    method=metadata.methods[declarations[0]['methodIndex']];td=metadata.types[method.declaring_type];owner=metadata.type_full_name(td)
    if (owner+'.'+metadata.string(method.name_index)!=body.symbol
            or method.flags&0x10 or method.generic_container_index>=0 or td.generic_container_index>=0
            or context.is_value_type(owner) or image.method_pointer_va(method)!=body.pointer):
        raise ValueError(label+'.ordinary-reference-instance')
    context.require_ordinary_kind(method.return_type,1)
    ancestors=spec['ancestors']
    if not isinstance(ancestors,list) or not ancestors:raise ValueError(label+'.ancestors')
    validate_reference_ancestor_chain(context,owner,ancestors,ancestors[-1])
    chain=[owner,*ancestors];fields={};list_type=None
    if any(len(image.named_type_definitions.get(name,()))!=1 for name in chain):raise ValueError(label+'.unique-owners')
    for role,qualified in spec['fields'].items():
        declaring,kind,offset=context.field(qualified)
        if type(offset) is not int or offset<16:raise ValueError(label+'.instance-field-offset')
        if declaring not in chain or role in ('list','index') and declaring!=owner:raise ValueError(label+'.field-owner')
        members=[f for f in metadata.fields_for(index.types[declaring]) if metadata.string(f.name_index)==qualified.partition('::')[2]]
        if len(members)!=1:raise ValueError(label+'.unique-field')
        if role=='list':
            list_type=closed_generic_reference_extent(context,members[0].type_index)
            if list_type['type']!='System.Collections.Generic.List`1<int>':raise ValueError(label+'.closed-int32-list')
            carrier=int.from_bytes(bytes.fromhex(list_type['declaredTypeRecordHex'])[:8],'little')
            inst=image.instantiations.resolve_pointer(image.pe.u64_at_va(carrier+8))
            if len(inst.arguments)!=1:raise ValueError(label+'.list-argument-count')
            argument=image.pe.bytes_at_va(inst.arguments[0].type_pointer_va,16)
            if len(argument)!=16 or argument[10]!=8 or argument[11]&0x7f:raise ValueError(label+'.ordinary-list-int32-argument')
        else:
            context.require_ordinary_kind(members[0].type_index,8)
            if kind!='int':raise ValueError(label+'.int32-fields')
        fields[role]=offset
    spans=sorted((offset,offset+(8 if role=='list' else 4)) for role,offset in fields.items())
    if any(b>c for (a,b),(c,d) in zip(spans,spans[1:])):raise ValueError(label+'.field-overlap')
    rows,ranges,_=read_owned_consumer_instructions(image.mapper,image.pe,body.pointer)
    calls=[r for r in rows if 'System.Collections.Generic.List`1.get_Item' in index.names_of(control_transfer(r).get('target',0))]
    if len(calls)!=1:raise ValueError(label+'.unique-item-call')
    call=calls[0];pointer=control_transfer(call)['target'];position=rows.index(call)
    if position<2:raise ValueError(label+'.item-context-load')
    load=rows[position-2];decoded=decode_memory_move(bytes.fromhex(load['bytes']),0,int(load['va'],16))
    if decoded is None or decoded[1]!=len(bytes.fromhex(load['bytes'])):raise ValueError(label+'.context-move')
    op=decoded[0]['memoryOperation'];address=op['address']
    if (op['direction'],op['register'],op['memoryBytes'],op['registerBits'],address.get('ripRelative'))!=('load','r8',8,64,True):
        raise ValueError(label+'.context-rip-reference')
    cell=address['absoluteAddress'];reg=image.registration;table=int(reg['methodSpecs'],16)
    selected=usage_method_spec(image.pe.bytes_at_va(cell,8),image.pe.bytes_at_va(table,reg['methodSpecsCount']*12),
        len(metadata.methods),reg['genericInstsCount'],source=str(image.gameassembly),usage_offset=cell,records_offset=table)
    target=metadata.methods[selected['definition']]
    if (target.declaring_type!=list_type['definitionTypeIndex'] or metadata.string(target.name_index)!='get_Item'
            or target.flags&0x10 or target.generic_container_index>=0 or selected['methodInstantiationIndex']!=-1):
        raise ValueError(label+'.declared-item-context')
    generic=GenericEntries(image);args,argument_proof=generic.arguments(selected['classInstantiationIndex'])
    if args!=['int']:raise ValueError(label+'.int32-context')
    raw=bytes.fromhex(argument_proof['arguments'][0]['raw_type_record_hex'])
    if len(raw)!=16 or raw[10]!=8 or raw[11]&0x7f:raise ValueError(label+'.ordinary-int32-context')
    registered=generic.resolve(target.index,['int'],[])
    if registered['pointer']!=pointer or registered['registration']['indices'][-1]!=-1:
        raise ValueError(label+'.ordinary-registered-item-target')
    params=list(metadata.parameters_for(target))
    if len(params)!=1:raise ValueError(label+'.item-index-parameter')
    context.require_ordinary_kind(params[0].type_index,8)
    ret=image.pe.bytes_at_va(context.type_pointer(target.return_type),16)
    section=metadata.sections['genericContainers'];at=section.offset+metadata.types[target.declaring_type].generic_container_index*16
    if not section.offset<=at<=section.offset+section.size-16:raise ValueError(label+'.generic-container-range')
    declaration,count,is_method,parameter=struct.unpack_from('<iiii',metadata.buf,at)
    if (declaration,count,is_method)!=(target.declaring_type,1,0) or len(ret)!=16 or ret[10]!=0x13 or ret[11]&0x7f or int.from_bytes(ret[:8],'little')!=parameter:
        raise ValueError(label+'.item-returns-selected-type-parameter')
    item_rows,item_ranges,_=read_owned_consumer_instructions(image.mapper,image.pe,pointer)
    item=check_list_item_program(item_rows,entry=pointer,owned_ranges=item_ranges,element_kind='int32')
    program=check_action_branch_program(rows,entry=body.pointer,owned_ranges=ranges,fields=fields,count_offset=item['boundFieldOffset'],item_pointer=pointer)
    return dict(program=program,itemProgram=item,selectedContext=selected,registeredEntry=registered,
        evidenceBoundary='conditional',condition=program['condition']+' Static declared context and matching AOT registration only; live MethodInfo selection remains conditional.')
