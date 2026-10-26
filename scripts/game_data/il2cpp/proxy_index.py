"""Typed external Int32 index normalization in the original proxy method."""
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.consumer_entry_program import read_ordinary_consumer_entry
from scripts.game_data.il2cpp.consumer_reference_origins import check_reference_origins
from scripts.game_data.il2cpp.proxy_index_program import check_proxy_index_program


def check_proxy_index_normalization(index,body,spec):
    if not isinstance(spec,dict) or set(spec)!={'field','callback'} or any(not isinstance(v,str) or not v for v in spec.values()):raise ValueError('proxyIndex.named-profile')
    image=index.image;md=image.metadata;ctx=NativeReferenceContext(image);owner,kind,offset=ctx.field(spec['field'])
    if kind!='int' or body.symbol.rpartition('.')[0]!=owner or ctx.is_value_type(owner) or len(image.named_type_definitions.get(owner,()))!=1:raise ValueError('proxyIndex.typed-reference-and-int32-field')
    fields=[f for f in md.fields_for(index.types[owner]) if md.string(f.name_index)==spec['field'].partition('::')[2]]
    if len(fields)!=1:raise ValueError('proxyIndex.unique-field')
    ctx.require_ordinary_kind(fields[0].type_index,8)
    targets=index.pointers_by_name.get(spec['callback'],set())
    if len(targets)!=1:raise ValueError('proxyIndex.unique-callback')
    target=next(iter(targets))
    for pointer,symbol,count in [(body.pointer,body.symbol,1),(target,spec['callback'],2)]:
        matches=[r for r in index.names_by_pointer[pointer] if r['type']+'.'+r['method']==symbol]
        if len(matches)!=1:raise ValueError('proxyIndex.unique-method')
        method=md.methods[matches[0]['methodIndex']];td=md.types[method.declaring_type];parameters=list(md.parameters_for(method))
        if md.type_full_name(td)!=owner or td.generic_container_index>=0 or method.flags&16 or method.generic_container_index>=0 or ctx.type_name(method.return_type)!='void' or len(parameters)!=count:raise ValueError('proxyIndex.ordinary-instance-void-ABI')
        ctx.require_ordinary_kind(method.return_type,1)
        for parameter in parameters:
            if ctx.type_name(parameter.type_index)!='int':raise ValueError('proxyIndex.int32-parameters')
            ctx.require_ordinary_kind(parameter.type_index,8)
    program=read_ordinary_consumer_entry(image,body,tail_targets=(target,))
    refs=check_reference_origins(program['rows'],entry=body.pointer,owned_ranges=program['ranges'],incoming_registers={'rcx':'this','rdx':'incoming-index'},incoming_stack_slots={},selected_call_returns={},tail_exits=program['tailExits'])
    proof=check_proxy_index_program(program,refs,field_offset=offset,callback=target)
    if refs['registerOrigins'][int(proof['readVa'],16)]['rdx']!=['incoming-index']:raise ValueError('proxyIndex.incoming-index-preservation')
    return dict(proof,ordinaryEntryProof=dict(scope='ordinary-entry-with-separate-nonentry-code',completeOwnedBytePartition=True,ordinaryInstructions=len(program['rows']),unenteredOwnedByteCandidates=program['unenteredOwnedByteCandidates'],tailExits=program['tailExits'],exceptionalOrResumptionPathsProved=False))
