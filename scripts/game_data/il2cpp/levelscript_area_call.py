"""Typed current area call component; optimized callee semantics are separate."""
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.consumer_rva_switches import partition_consumer_rva_switches,ordinary_entry_program
from scripts.game_data.il2cpp.consumer_reference_origins import check_reference_origins
from scripts.game_data.il2cpp.levelscript_area_call_program import check_area_call_program


def prove_levelscript_area_call(image):
    context=NativeReferenceContext(image);index=image.body_index;metadata=image.metadata;base=image.pe.image_base
    owner='Beyond.Gameplay.Core.LevelScriptRuntime';fields={}
    if context.is_value_type(owner):raise ValueError('levelscriptAreaCall.reference-owner')
    for role,name,wanted,kind in [('within','withinActiveArea','bool',2),('enter','activeShapeList','System.Collections.Generic.List`1<Beyond.Gameplay.Core.LevelScriptShape>',0x15),('exit','activeShapeOutsideList','System.Collections.Generic.List`1<Beyond.Gameplay.Core.LevelScriptShape>',0x15)]:
        declaring,actual,offset=context.field(owner+'::'+name)
        if declaring!=owner or actual!=wanted:raise ValueError('levelscriptAreaCall.typed-field:'+name)
        declarations=[f for f in metadata.fields_for(index.types[owner]) if metadata.string(f.name_index)==name]
        if len(declarations)!=1:raise ValueError('levelscriptAreaCall.unique-field:'+name)
        context.require_ordinary_kind(declarations[0].type_index,kind);fields[role]=offset
    bodies={}
    for name in ('UpdateWithinActiveArea','get_activeRangeSensitive'):
        body=index.body(owner,name,parameters=[]);aliases=[r for r in index.names_by_pointer[body.pointer] if r['type']==owner and r['method']==name]
        if len(aliases)!=1:raise ValueError('levelscriptAreaCall.unique-method:'+name)
        method=metadata.methods[aliases[0]['methodIndex']]
        if method.flags&16 or method.generic_container_index>=0 or context.type_name(method.return_type)!='bool':raise ValueError('levelscriptAreaCall.ordinary-bool-instance:'+name)
        context.require_ordinary_kind(method.return_type,2);bodies[name]=body
    body=bodies['UpdateWithinActiveArea'];parts=image.unwind_index.family(body.pointer-base)['ranges']
    spans=sorted((base+p['runtimeTriple'][0],base+p['runtimeTriple'][1]) for p in parts)
    start,end=spans[0][0],spans[-1][1]
    if start!=body.pointer or any(left[1]!=right[0] for left,right in zip(spans,spans[1:])):raise ValueError('levelscriptAreaCall.contiguous-owned-caller')
    part=partition_consumer_rva_switches(image.mapper,image.pe.bytes_at_va(start,end-start),entry=start,image_base=base)
    tails={int(r['va'],16):dict(register='rax') for r in part['rows'] if r['bytes']=='48 ff e0'}
    program=ordinary_entry_program(part,entry=start,tail_exits=tails)
    literals={table['baseLoad']:(table['baseRegister'],base) for table in part['tables'] if table['baseLoad'] is not None}
    refs=check_reference_origins(program['rows'],entry=start,owned_ranges=program['ranges'],incoming_registers={'rcx':'this'},incoming_stack_slots={},selected_call_returns={},computed_jump_targets=program['computedJumpTargets'],selected_literal_registers=literals,tail_exits=program['tailExits'])
    proof=check_area_call_program(program,refs,entry=start,fields=fields,sensitive_pointer=bodies['get_activeRangeSensitive'].pointer)
    return dict(proof,fieldOffsets=fields,ordinaryEntryProof=dict(scope='ordinary-entry-with-separate-nonentry-code',completeOwnedBytePartition=True,computedGuardsProved=True,selectedBasesProved=True,incomingReceiverProved=True,exceptionalOrResumptionPathsProved=False,tables=part['tables'],nonEntryCode=program['nonEntryCode'],tailExits=program['tailExits']))
