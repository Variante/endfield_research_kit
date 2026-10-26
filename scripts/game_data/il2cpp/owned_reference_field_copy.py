"""Fresh typed field-to-field reference copy on an owned original method path.

This proves a selected stored-reference transfer, not its branch outcome,
callee effects, persistence, callback dispatch, or runtime execution.
"""
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext,closed_generic_reference_extent
from scripts.game_data.il2cpp.type_data_initialization_instructions import decode_type_data_initialization_instructions
from scripts.game_data.il2cpp.consumer_reference_origins import check_reference_origins
from scripts.game_data.il2cpp.consumer_control import check_consumer_control
from scripts.game_data.il2cpp.memory_moves import decode_memory_move
from scripts.game_data.il2cpp.integer_addressing import decode_lea_address


def derive_reference_field_copy(image,spec):
    ctx=NativeReferenceContext(image);md=image.metadata;pe=image.pe
    def need(ok,gate):
        if not ok:raise ValueError('ownedReferenceFieldCopy.'+gate)
    need(set(spec)=={'type','method','sourceField','destinationField','fieldType','parameters','returnType'},'claim-shape')
    owner=spec['type'];td=ctx.index.types.get(owner);need(td is not None and not ctx.is_value_type(owner)and td.generic_container_index<0,'ordinary-owner')
    methods=[m for m in md.methods_for(td)if md.string(m.name_index)==spec['method']]
    need(len(methods)==1,'unique-method');method=methods[0]
    need(not method.flags&0x10 and ctx.type_name(method.return_type)==spec['returnType']and [ctx.type_name(p.type_index)for p in md.parameters_for(method)]==spec['parameters'],'method-abi')
    for p in [method.return_type,*[p.type_index for p in md.parameters_for(method)]]:
        need(not pe.bytes_at_va(ctx.type_pointer(p),16)[11]&0x7f,'ordinary-method-types')
    chain=[owner]
    while chain[-1]in ctx.index.types and len(chain)<32:
        parent=ctx.parent(chain[-1])
        if not parent:break
        need(parent not in chain,'acyclic-inheritance');chain.append(parent)
    fields=[]
    for qualified in(spec['sourceField'],spec['destinationField']):
        declaring,kind,offset=ctx.field(qualified);need(declaring in chain and kind==spec['fieldType'],'owned-matching-field-types')
        definition=ctx.index.types[declaring];field,=[f for f in md.fields_for(definition)if md.string(f.name_index)==qualified.partition('::')[2]]
        extent=closed_generic_reference_extent(ctx,field.type_index);need(extent['type']==kind and extent['bytes']==8,'full-reference-storage')
        fields.append(dict(field=qualified,type=kind,offset=offset,storage=extent))
    need(fields[0]['offset']!=fields[1]['offset'],'distinct-storage')
    entry=image.method_pointer_va(method);family=image.unwind_index.family(entry-pe.image_base)
    ranges=[(pe.image_base+r['runtimeTriple'][0],pe.image_base+r['runtimeTriple'][1])for r in family['ranges']]
    rows=[dict(r,offset=int(r['va'],16)-entry)for start,end in sorted(ranges)for r in decode_type_data_initialization_instructions(image.mapper,pe.bytes_at_va(start,end-start),start)]
    control=check_consumer_control(rows,entry=entry,owned_ranges=ranges)
    origins=check_reference_origins(rows,entry=entry,owned_ranges=ranges,incoming_registers={'rcx':'this'},incoming_stack_slots={},selected_call_returns={})['registerOrigins']
    def memory(row):
        raw=bytes.fromhex(row['bytes']);value=decode_memory_move(raw,0,int(row['va'],16))
        return value[0]['memoryOperation']if value and value[1]==len(raw)else None
    def own(fact,row,direction,offset):
        a=fact.get('address',{})if fact else{}
        return bool(fact and(fact['direction'],fact['registerBits'],fact['memoryBytes'],a.get('index'),a.get('ripRelative'),a.get('displacement'))==(direction,64,8,None,False,offset)and origins[int(row['va'],16)].get(a.get('base'))==['this'])
    by_at={int(r['va'],16):r for r in rows};copies=[]
    for store in rows:
        sf=memory(store)
        if not own(sf,store,'store',fields[1]['offset']):continue
        previous=[at for at,edges in control['edges'].items()if int(store['va'],16)in edges]
        need(len(previous)==1,'store-unique-predecessor');lea=by_at[previous[0]];raw=bytes.fromhex(lea['bytes']);address=decode_lea_address(raw,0,previous[0]);need(address is not None and address[1]==len(raw),'address-only-bridge')
        a=address[0]['addressOperation'];need(a['destination']=='rcx'and a['destinationBits']==64 and a.get('index')is None and not a.get('ripRelative')and a['displacement']==fields[1]['offset']and origins[previous[0]].get(a.get('base'))==['this'],'owned-destination-address')
        before=[at for at,edges in control['edges'].items()if previous[0]in edges];need(len(before)==1,'load-unique-predecessor');load=by_at[before[0]];lf=memory(load)
        need(own(lf,load,'load',fields[0]['offset'])and lf['backingRegister']==sf['backingRegister']=='rax','unchanged-reference-transfer')
        need(before[0]+len(bytes.fromhex(load['bytes']))==previous[0]and previous[0]+len(raw)==int(store['va'],16),'contiguous-copy')
        copies.append(dict(load=load,address=lea,store=store))
    need(len(copies)==1,'unique-owned-copy')
    return dict(method=[method.index,owner,spec['method'],entry-pe.image_base],fields=fields,ancestorChain=chain,copy=copies[0],ownedRanges=ranges,instructionsChecked=len(rows),originalThisToOwnedWaitFieldCopyProved=True,callbackContinuationProved=False,evidenceBoundary='direct',condition='Selected original/IFix-bypass path reaches the checked store; ordinary Win64 returning callees and valid stable disjoint heap. Later helper effects, wait-list consumption, callback selection and execution are not proved.')
