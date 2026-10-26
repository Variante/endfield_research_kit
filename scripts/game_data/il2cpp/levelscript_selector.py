"""Typed ordinary runtime activation selection, without live/IFix claims."""
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.consumer_rva_switches import partition_consumer_rva_switches,ordinary_entry_program
from scripts.game_data.il2cpp.consumer_reference_origins import check_reference_origins
from scripts.game_data.il2cpp.original_field_return import check_original_field_return
from scripts.game_data.il2cpp.levelscript_selector_program import check_levelscript_selector_program
from scripts.game_data.il2cpp import protocol


def prove_levelscript_selector(image):
    label='levelscriptSelector';index=image.body_index;metadata=image.metadata;context=NativeReferenceContext(image)
    owner='Beyond.Gameplay.Core.LevelScriptRuntime';brief='Beyond.Gameplay.LevelScriptBriefData'
    types=dict(state='Beyond.GEnums.LevelScriptState',runtime=owner+'+RuntimeState',type='Beyond.GEnums.LevelScriptType')
    for name in (owner,brief,*types.values(),'Beyond.Gameplay.Core.ScriptEndReason'):
        if len(image.named_type_definitions.get(name,()))!=1:raise ValueError(label+'.unique-type:'+name)
        if name in (*types.values(),'Beyond.Gameplay.Core.ScriptEndReason'):
            if not context.is_enum(name) or context.field(name+'::value__')[1]!='int':raise ValueError(label+'.int32-enum:'+name)
            members=[f for f in metadata.fields_for(index.types[name]) if metadata.string(f.name_index)=='value__']
            if len(members)!=1:raise ValueError(label+'.unique-enum-underlying:'+name)
            context.require_ordinary_kind(members[0].type_index,8)
    bodies={};pointers={};methods={}
    for name,args,returns,kind in [('UpdateRuntimeState',['Beyond.Gameplay.Core.ScriptEndReason'],'void',1),
            ('set_runtimeState',[types['runtime']],'void',1),('get_levelScriptType',[],types['type'],0x11),
            ('UpdateWithinActiveArea',[],'bool',2),('_SendLevelScriptSetActive',['System.Boolean'],'void',1)]:
        body=index.body(owner,name,parameters=args);aliases=[r for r in index.names_by_pointer[body.pointer] if r['type']+'.'+r['method']==body.symbol]
        if len(aliases)!=1:raise ValueError(label+'.unique-method:'+name)
        method=metadata.methods[aliases[0]['methodIndex']];td=metadata.types[method.declaring_type]
        if (method.flags&0x10 or method.generic_container_index>=0 or td.generic_container_index>=0 or context.is_value_type(owner)
                or image.method_pointer_va(method)!=body.pointer or context.type_name(method.return_type)!=returns):raise ValueError(label+'.ordinary-method:'+name)
        context.require_ordinary_kind(method.return_type,kind);params=list(metadata.parameters_for(method))
        if len(params)!=len(args):raise ValueError(label+'.parameter-count:'+name)
        for param,wanted in zip(params,args):
            expected='bool' if wanted=='System.Boolean' else wanted
            if context.type_name(param.type_index)!=expected:raise ValueError(label+'.parameter-type:'+name)
            context.require_ordinary_kind(param.type_index,2 if expected=='bool' else 0x11)
        bodies[name]=body;pointers[name]=body.pointer;methods[name]=dict(methodIndex=method.index,token=body.token,pointer=hex(body.pointer))
    fields={}
    for role,qualified,wanted,kind in [('state',owner+'::m_state',types['state'],0x11),('runtimeState',owner+'::m_runtimeState',types['runtime'],0x11),
            ('brief',owner+'::<briefData>k__BackingField',brief,0x12),('type',brief+'::levelScriptType',types['type'],0x11)]:
        declaring,actual,offset=context.field(qualified)
        if actual!=wanted or type(offset) is not int or offset<16:raise ValueError(label+'.typed-field:'+qualified)
        members=[f for f in metadata.fields_for(index.types[declaring]) if metadata.string(f.name_index)==qualified.partition('::')[2]]
        if len(members)!=1:raise ValueError(label+'.unique-field:'+qualified)
        context.require_ordinary_kind(members[0].type_index,kind);fields[role]=offset
    getter=check_original_field_return(index,bodies['get_levelScriptType'],fields['type'],4,data_offset=fields['brief'])
    body=bodies['UpdateRuntimeState'];base=image.pe.image_base;ranges=image.unwind_index.family(body.pointer-base)['ranges']
    if len(ranges)!=1:raise ValueError(label+'.single-owned-runtime-program')
    start,end=[base+n for n in ranges[0]['runtimeTriple'][:2]]
    if start!=body.pointer:raise ValueError(label+'.owned-entry')
    part=partition_consumer_rva_switches(image.mapper,image.pe.bytes_at_va(start,end-start),entry=start,image_base=base)
    program=ordinary_entry_program(part,entry=start);literals={int(r['va'],16):('rbx',0) for r in program['rows'] if r['bytes']=='33 db'}
    literals.update({t['baseLoad']:(t['baseRegister'],base) for t in part['tables'] if t['baseLoad'] is not None})
    refs=check_reference_origins(program['rows'],entry=start,owned_ranges=program['ranges'],incoming_registers={'rcx':'this'},incoming_stack_slots={},
        selected_call_returns={},computed_jump_targets=program['computedJumpTargets'],selected_literal_registers=literals)
    enums={role:{r['name']:r['id'] for r in protocol.enum_members(metadata,index.enum_defaults,name)} for role,name in types.items()}
    proof=check_levelscript_selector_program(part,program,refs,entry=start,image_base=base,fields=fields,enums=enums,pointers=pointers)
    return dict(proof,methods=methods,fieldOffsets=fields,enumValues={types[role]:values for role,values in enums.items()},getterProof=getter,
        ordinaryEntryProof=dict(scope='ordinary-entry-with-separate-nonentry-code',completeOwnedBytePartition=True,computedGuardsProved=True,
            selectedBasesProved=True,incomingReceiverProved=True,originalGetterFieldReturnProved=True,exceptionalOrResumptionPathsProved=False,
            codeInstructions=len(part['rows']),ordinaryInstructions=len(program['rows']),tables=part['tables'],padding=part['padding'],nonEntryCode=program['nonEntryCode']))
