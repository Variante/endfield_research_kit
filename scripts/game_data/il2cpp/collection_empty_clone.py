"""Selected generic collection-empty program, context and exit-list argument."""
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.context import usage_method_spec
from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
from scripts.game_data.il2cpp.consumer_entry_program import read_ordinary_consumer_entry
from scripts.game_data.il2cpp.consumer_reference_origins import check_reference_origins
from scripts.game_data.il2cpp.owned_consumer_instructions import read_owned_consumer_instructions
from scripts.game_data.il2cpp.collection_empty_clone_program import check_collection_empty_clone,check_true_result_returns_false,_target
from scripts.game_data.il2cpp.type_data_initialization_instructions import decode_type_data_initialization_instructions


def prove_collection_empty_clone(image,body,*,argument_type):
    index=image.body_index;md=image.metadata;ctx=NativeReferenceContext(image);base=image.pe.image_base;generic=GenericEntries(image)
    aliases=[r for r in index.names_by_pointer[body.pointer] if r['type']+'.'+r['method']==body.symbol]
    if len(aliases)!=1:raise ValueError('collectionEmpty.unique-caller')
    declaration=md.methods[aliases[0]['methodIndex']];parameters=list(md.parameters_for(declaration));list_type='System.Collections.Generic.List`1<'+argument_type+'>'
    if not declaration.flags&16 or declaration.generic_container_index>=0 or md.types[declaration.declaring_type].generic_container_index>=0 or ctx.type_name(declaration.return_type)!='bool' or len(parameters)!=5:raise ValueError('collectionEmpty.static-caller-ABI')
    ctx.require_ordinary_kind(declaration.return_type,2)
    for parameter,wanted,kind in zip(parameters[:3],('bool',list_type,list_type),(2,0x15,0x15)):
        if ctx.type_name(parameter.type_index)!=wanted:raise ValueError('collectionEmpty.exit-argument-type')
        ctx.require_ordinary_kind(parameter.type_index,kind)
    program=read_ordinary_consumer_entry(image,body);rows=program['rows'];reg=image.registration;table=int(reg['methodSpecs'],16);matches=[]
    refs=check_reference_origins(rows,entry=body.pointer,owned_ranges=program['ranges'],incoming_registers={'r8':'exit-shapes'},incoming_stack_slots={},selected_call_returns={})
    def owned(pointer):return read_owned_consumer_instructions(image.mapper,image.pe,pointer)[0]
    for i,row in enumerate(rows):
        raw=bytes.fromhex(row['bytes'])
        if len(raw)!=5 or raw[0]!=0xe8 or i<2:continue
        load=rows[i-2];load_raw=bytes.fromhex(load['bytes'])
        if len(load_raw)!=7 or load_raw[:3]!=b'\x48\x8b\x15':continue
        cell=int(load['va'],16)+7+int.from_bytes(load_raw[3:],'little',signed=True)
        selected=usage_method_spec(image.pe.bytes_at_va(cell,8),image.pe.bytes_at_va(table,reg['methodSpecsCount']*12),len(md.methods),reg['genericInstsCount'],source=str(image.gameassembly),usage_offset=cell,records_offset=table)
        method=md.methods[selected['definition']]
        if md.type_full_name(md.types[method.declaring_type])!='Beyond.CollectionExtensions' or md.string(method.name_index)!='IsNullOrEmpty':continue
        if generic.arguments(selected['classInstantiationIndex'])[0]!=[] or generic.arguments(selected['methodInstantiationIndex'])[0]!=[argument_type]:raise ValueError('collectionEmpty.selected-context')
        if not method.flags&16 or ctx.type_name(method.return_type)!='bool' or method.parameter_count!=1:raise ValueError('collectionEmpty.method-ABI')
        ctx.require_ordinary_kind(method.return_type,2);ctx.require_ordinary_kind(list(md.parameters_for(method))[0].type_index,0x15)
        symbols=ContextSymbols(image).context(method.index,is_method=True);entries=symbols['entries']
        if len(entries)!=2 or entries[0]['kind']!=2 or entries[0]['relativeSlot']!=0 or entries[0]['type']['definition']['name']!='System.Collections.Generic.ICollection`1':raise ValueError('collectionEmpty.context-type')
        arg=entries[0]['type']['classArguments'];count=entries[1]
        if len(arg)!=1 or arg[0].get('parameterOwner',{}).get('methodIndex')!=method.index or arg[0]['parameterOwner']['ordinal']!=0:raise ValueError('collectionEmpty.parameter-owner')
        if count['kind']!=3 or count['typeName']!='System.Collections.Generic.ICollection`1' or count['methodName']!='get_Count' or count['classArguments']!=arg or count['methodArguments']!=[]:raise ValueError('collectionEmpty.count-context')
        getter=md.methods[count['methodSpec'][0]]
        if getter.slot!=0 or getter.parameter_count!=0 or getter.flags&16 or getter.generic_container_index>=0 or ctx.type_name(getter.return_type)!='int':raise ValueError('collectionEmpty.count-ABI')
        ctx.require_ordinary_kind(getter.return_type,8)
        for earlier,later in zip(rows[i-2:i],rows[i-1:i+1]):
            if {source for source,targets in program['control']['edges'].items() if int(later['va'],16) in targets}!={int(earlier['va'],16)}:raise ValueError('collectionEmpty.context-load-bypass')
        if refs['registerOrigins'][int(row['va'],16)]['rcx']!=['exit-shapes']:raise ValueError('collectionEmpty.exit-argument-bits')
        registrations=generic.observe(method.index,[],['object'])
        if len(registrations)!=1 or not registrations[0]['pointer'] or registrations[0]['registration']['indices'][-1]!=-1:raise ValueError('collectionEmpty.selected-ordinary-canonical-registration')
        canonical=registrations[0];clone_rows=owned(_target(row,0xe8));leaf=_target(clone_rows[11],0xe8)
        leaf_rows=decode_type_data_initialization_instructions(image.mapper,image.pe.bytes_at_va(leaf,15),leaf)
        proof=check_collection_empty_clone(owned(canonical['pointer']),clone_rows,leaf_rows)
        false_return=check_true_result_returns_false(rows,int(row['va'],16))
        matches.append(dict(proof,**false_return,callSiteVa=row['va'],selectedContext=selected,contextSymbols=symbols,selectedExitArgumentBitsProved=True,
            selectedCanonicalRegistration=canonical,uniquePhysicalMethodIdentityClaimed=False))
    if len(matches)!=1:raise ValueError('collectionEmpty.unique-selected-call:'+str(len(matches)))
    return matches[0]
