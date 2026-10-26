"""Typed current NPC proxy dialog selection under original ordinary code."""
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.consumer_entry_program import read_ordinary_consumer_entry
from scripts.game_data.il2cpp.consumer_reference_origins import check_reference_origins
from scripts.game_data.il2cpp.initializer_control import control_transfer
from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
from scripts.game_data.il2cpp.list_item_program import check_list_item_program
from scripts.game_data.il2cpp.nullable_cast_program import check_nullable_cast_program
from scripts.game_data.il2cpp.original_field_return import check_original_field_return
from scripts.game_data.il2cpp.npc_proxy_selection_program import check_npc_proxy_selection_program


def check_npc_proxy_selection(index,body,spec):
    label='npcProxySelection';image=index.image;md=image.metadata;ctx=NativeReferenceContext(image);base=image.pe.image_base
    keys={'proxyIndex','dataField','rowsField','dialogField','lookup','npcIdGetter','indexGetter'}
    if not isinstance(spec,dict) or set(spec)!=keys or any(not isinstance(v,str) or not v for v in spec.values()):raise ValueError(label+'.named-profile')
    fields={role:ctx.field(spec[key]) for role,key in [('index','proxyIndex'),('data','dataField'),('rows','rowsField'),('dialog','dialogField')]}
    proxy=fields['index'][0];owner=fields['data'][0];data_type=fields['rows'][0];item_type=fields['dialog'][0];list_type='System.Collections.Generic.List`1<'+item_type+'>'
    if fields['index'][1]!='int' or fields['dialog'][1]!='string' or fields['rows'][1]!=list_type or ctx.parent(data_type)!=fields['data'][1]:raise ValueError(label+'.typed-field-chain')
    for name in (proxy,owner,data_type,item_type):
        if len(image.named_type_definitions.get(name,()))!=1 or ctx.is_value_type(name) or index.types[name].generic_container_index>=0:raise ValueError(label+'.unique-reference-owner:'+name)
    for role,key,kind in [('index','proxyIndex',8),('data','dataField',0x12),('rows','rowsField',0x15),('dialog','dialogField',0x0e)]:
        declaration_name=spec[key].partition('::')[2];members=[f for f in md.fields_for(index.types[fields[role][0]]) if md.string(f.name_index)==declaration_name]
        if len(members)!=1:raise ValueError(label+'.unique-field:'+role)
        ctx.require_ordinary_kind(members[0].type_index,kind)
    def declaration(pointer,symbol,result,kinds):
        matches=[r for r in index.names_by_pointer[pointer] if r['type']+'.'+r['method']==symbol]
        if len(matches)!=1:raise ValueError(label+'.unique-method:'+symbol)
        method=md.methods[matches[0]['methodIndex']];td=md.types[method.declaring_type];params=list(md.parameters_for(method))
        if method.flags&16 or method.generic_container_index>=0 or td.generic_container_index>=0 or ctx.type_name(method.return_type)!=result or len(params)!=len(kinds):raise ValueError(label+'.method-ABI:'+symbol)
        ctx.require_ordinary_kind(method.return_type,2 if result=='bool' else 8 if result=='int' else 0x0e)
        for parameter,(name,kind,byref) in zip(params,kinds):
            raw=image.pe.bytes_at_va(ctx.type_pointer(parameter.type_index),16)
            if ctx.type_name(parameter.type_index)!=name or len(raw)!=16 or raw[10]!=kind or raw[11]&0x7f!=(0x20 if byref else 0):raise ValueError(label+'.parameter-ABI:'+symbol)
        return method
    declaration(body.pointer,body.symbol,'bool',[('string',0x0e,True)])
    if body.symbol.rpartition('.')[0]!=owner:raise ValueError(label+'.caller-owner')
    pointers={}
    for role,key,result,kinds in [('lookup','lookup','bool',[('string',0x0e,False),(proxy,0x12,True)]),('npcId','npcIdGetter','string',[]),('indexGetter','indexGetter','int',[])]:
        values=index.pointers_by_name.get(spec[key],set())
        if len(values)!=1:raise ValueError(label+'.unique-pointer:'+role)
        pointer=next(iter(values));method=declaration(pointer,spec[key],result,kinds);pointers[role]=pointer
        if role=='npcId' and md.type_full_name(md.types[method.declaring_type])!=owner:raise ValueError(label+'.id-getter-owner')
        if role=='indexGetter' and md.type_full_name(md.types[method.declaring_type])!=proxy:raise ValueError(label+'.index-getter-owner')
    getter=index.body(proxy,spec['indexGetter'].rsplit('.',1)[1],parameters=[])
    original_getter=check_original_field_return(index,getter,fields['index'][2],4)
    program=read_ordinary_consumer_entry(image,body);rows=program['rows'];calls=[(i,r) for i,r in enumerate(rows) if control_transfer(r)['kind']=='call']
    lookups=[i for i,r in calls if control_transfer(r)['target']==pointers['lookup']]
    items=[(i,r) for i,r in calls if 'System.Collections.Generic.List`1.get_Item' in index.names_of(control_transfer(r)['target'])]
    if len(lookups)!=1 or len(items)!=1:raise ValueError(label+'.unique-lookup-and-item')
    cast_load=rows[lookups[0]+3];cast_call=rows[lookups[0]+5];cast_context=derive_typed_usage_context(image,int(cast_load['va'],16)-base,label=label)
    if cast_context['tag']!=1 or cast_context['typeName']!=data_type:raise ValueError(label+'.cast-target-context')
    position,item_call=items[0];item_context=derive_typed_usage_context(image,int(rows[position-2]['va'],16)-base,label=label)
    if item_context.get('tag')!=6 or item_context.get('typeName')!='System.Collections.Generic.List`1' or item_context.get('methodName')!='get_Item' or item_context.get('classArguments')!=[item_type] or item_context.get('methodArguments')!=[]:raise ValueError(label+'.typed-list-item-context')
    generic=GenericEntries(image);definition=item_context['methodSpec'][0];method=md.methods[definition];parameters=list(md.parameters_for(method))
    returned=ContextSymbols(image).type(ctx.type_pointer(method.return_type));parameter_owner=returned.get('parameterOwner',{})
    return_raw=bytes.fromhex(returned['rawHex'])
    if method.flags&16 or method.generic_container_index>=0 or len(parameters)!=1 or ctx.type_name(parameters[0].type_index)!='int' or return_raw[10]!=0x13 or return_raw[11]&0x7f or parameter_owner.get('typeIndex')!=method.declaring_type or parameter_owner.get('ordinal')!=0:raise ValueError(label+'.list-item-ABI')
    ctx.require_ordinary_kind(parameters[0].type_index,8)
    registration=generic.resolve(definition,['object'],[]);pointers['item']=control_transfer(item_call)['target'];pointers['cast']=control_transfer(cast_call)['target']
    if registration['pointer']!=pointers['item'] or registration['registration']['indices'][-1]!=-1:raise ValueError(label+'.ordinary-reference-shared-item-entry')
    def owned(pointer):
        from scripts.game_data.il2cpp.type_data_initialization_instructions import decode_type_data_initialization_instructions
        ranges=[(base+p['runtimeTriple'][0],base+p['runtimeTriple'][1]) for p in image.unwind_index.family(pointer-base)['ranges']];code=[]
        for a,b in ranges:code+=decode_type_data_initialization_instructions(image.mapper,image.pe.bytes_at_va(a,b-a),a)
        return dict(rows=code,entry=pointer,owned_ranges=ranges)
    item_proof=check_list_item_program(**owned(pointers['item']),element_kind='reference');cast_proof=check_nullable_cast_program(**owned(pointers['cast']))
    counts=[m for m in md.methods_for(md.types[method.declaring_type]) if md.string(m.name_index)=='get_Count' and m.parameter_count==0]
    if len(counts)!=1 or ctx.type_name(counts[0].return_type)!='int' or counts[0].flags&16:raise ValueError(label+'.list-count-ABI')
    ctx.require_ordinary_kind(counts[0].return_type,8);count_entries=generic.observe(counts[0].index,['object'],[])
    if len(count_entries)!=1 or not count_entries[0]['pointer'] or count_entries[0]['registration']['indices'][-1]!=-1:raise ValueError(label+'.list-count-registration')
    count_raw=image.pe.bytes_at_va(count_entries[0]['pointer'],4);offset=item_proof['boundFieldOffset']
    if not 16<=offset<=127 or count_raw!=bytes.fromhex('8b41')+bytes((offset,0xc3)):raise ValueError(label+'.list-count-field-return')
    literals={int(r['va'],16):('rsi',0) for r in rows if r['bytes']=='33 f6'}
    refs=check_reference_origins(rows,entry=body.pointer,owned_ranges=program['ranges'],incoming_registers={'rcx':'this','rdx':'dialog-output'},incoming_stack_slots={},selected_call_returns={},selected_literal_registers=literals)
    proof=check_npc_proxy_selection_program(program,refs,entry=body.pointer,fields={role:row[2] for role,row in fields.items()},pointers=pointers,count_offset=offset)
    return dict(proof,originalIndexGetter=original_getter,castContext=cast_context,itemContext=item_context,itemProof=item_proof,castProof=cast_proof,
        countRegistration=count_entries[0],ordinaryEntryProof=dict(scope='ordinary-entry-with-separate-nonentry-code',completeOwnedBytePartition=True,ordinaryInstructions=len(rows),unenteredOwnedByteCandidates=program['unenteredOwnedByteCandidates'],exceptionalOrResumptionPathsProved=False))
