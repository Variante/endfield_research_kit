"""Prove the selected ordinary LevelScript Active-case start policy."""
from scripts.game_data.il2cpp.original_field_return import check_original_field_return
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.consumer_reference_origins import check_reference_origins
from scripts.game_data.il2cpp.consumer_rva_switches import partition_consumer_rva_switches, ordinary_entry_program
from scripts.game_data.il2cpp.levelscript_start_program import check_levelscript_start_program
from scripts.game_data.il2cpp import protocol


RUNTIME='Beyond.Gameplay.Core.LevelScriptRuntime'
STATE='Beyond.GEnums.LevelScriptState'
START='Beyond.Gameplay.LevelScriptStartType'
RUNTIME_STATE=RUNTIME+'+RuntimeState'


def prove_levelscript_start_policy(image):
    index=image.body_index;metadata=image.metadata;context=NativeReferenceContext(image);label='levelscriptStartPolicy'
    enum_types={'state':STATE,'start':START,'runtime':RUNTIME_STATE}
    for name in (RUNTIME,'Beyond.Gameplay.LevelScriptData',*enum_types.values(),'Beyond.Gameplay.Core.ScriptEndReason'):
        if len(image.named_type_definitions.get(name,()))!=1:raise ValueError(label+'.unique-type:'+name)
        if name in enum_types.values() or name=='Beyond.Gameplay.Core.ScriptEndReason':
            if not context.is_enum(name) or context.field(name+'::value__')[1]!='int':raise ValueError(label+'.int32-enum:'+name)
            underlying=[field for field in metadata.fields_for(index.types[name]) if metadata.string(field.name_index)=='value__']
            if len(underlying)!=1:raise ValueError(label+'.unique-enum-underlying:'+name)
            context.require_ordinary_kind(underlying[0].type_index,8)
    bodies={};methods={};pointers={}
    for name,args,kind,returns in [('get_state',[],0x11,STATE),('get_isDone',[],2,'bool'),('get_startType',[],0x11,START),
            ('UpdateWithinStartArea',[],2,'bool'),('set_runtimeState',[RUNTIME_STATE],1,'void'),
            ('UpdateRuntimeState',['Beyond.Gameplay.Core.ScriptEndReason'],1,'void')]:
        body=index.body(RUNTIME,name,parameters=args)
        declarations=[row for row in index.names_by_pointer[body.pointer] if row['type']+'.'+row['method']==body.symbol]
        if len(declarations)!=1:raise ValueError(label+'.unique-method:'+name)
        method=metadata.methods[declarations[0]['methodIndex']];owner=metadata.types[method.declaring_type]
        if (metadata.type_full_name(owner)+'.'+metadata.string(method.name_index)!=body.symbol or method.flags&0x10
                or method.generic_container_index>=0 or owner.generic_container_index>=0 or context.is_value_type(RUNTIME)
                or image.method_pointer_va(method)!=body.pointer or context.type_name(method.return_type)!=returns):
            raise ValueError(label+'.method-identity-or-abi:'+name)
        context.require_ordinary_kind(method.return_type,kind)
        parameters=list(metadata.parameters_for(method))
        if len(parameters)!=len(args):raise ValueError(label+'.parameter-count:'+name)
        for parameter,wanted in zip(parameters,args):
            context.require_ordinary_kind(parameter.type_index,0x11)
            if context.type_name(parameter.type_index)!=wanted:raise ValueError(label+'.parameter-type:'+name)
        bodies[name]=body;pointers[name]=body.pointer
        methods[name]=dict(mappingStatus='mapped_unique',methodIndex=method.index,token=body.token,methodPointerVa=hex(body.pointer),
            parameterTypes=args,returnTypeName=returns)
    fields={}
    for role,qualified,wanted,kind in [('state',RUNTIME+'::m_state',STATE,0x11),('runtimeState',RUNTIME+'::m_runtimeState',RUNTIME_STATE,0x11),
            ('done',RUNTIME+'::m_isDone','bool',2),('manual',RUNTIME+'::m_manualStartTriggered','bool',2),
            ('data',RUNTIME+'::<data>k__BackingField','Beyond.Gameplay.LevelScriptData',0x12),
            ('start','Beyond.Gameplay.LevelScriptData::startType',START,0x11)]:
        owner,actual,offset=context.field(qualified)
        if actual!=wanted or type(offset) is not int or offset<16:raise ValueError(label+'.typed-field:'+qualified)
        members=[field for field in metadata.fields_for(index.types[owner]) if metadata.string(field.name_index)==qualified.partition('::')[2]]
        if len(members)!=1:raise ValueError(label+'.unique-field:'+qualified)
        context.require_ordinary_kind(members[0].type_index,kind);fields[role]=offset
    getters={name:check_original_field_return(index,bodies[name],fields[role],width,data_offset=fields['data'] if role=='start' else None)
        for name,role,width in [('get_state','state',4),('get_isDone','done',1),('get_startType','start',4)]}
    body=bodies['UpdateRuntimeState'];base=image.pe.image_base
    family=image.unwind_index.family(body.pointer-base)['ranges']
    if len(family)!=1:raise ValueError(label+'.single-owned-switch-program')
    start,end=(base+family[0]['runtimeTriple'][i] for i in (0,1))
    if start!=body.pointer:raise ValueError(label+'.owned-entry')
    part=partition_consumer_rva_switches(image.mapper,image.pe.bytes_at_va(start,end-start),entry=start,image_base=base)
    program=ordinary_entry_program(part,entry=start)
    literals={int(row['va'],16):('rbx',0) for row in program['rows'] if row['bytes']=='33 db'}
    literals.update({table['baseLoad']:('r15',base) for table in part['tables'] if table['baseLoad'] is not None})
    refs=check_reference_origins(program['rows'],entry=start,owned_ranges=program['ranges'],incoming_registers={'rcx':'this'},
        incoming_stack_slots={},selected_call_returns={},computed_jump_targets=program['computedJumpTargets'],selected_literal_registers=literals)
    enums={role:{row['name']:row['id'] for row in protocol.enum_members(metadata,index.enum_defaults,name)} for role,name in enum_types.items()}
    proof=check_levelscript_start_program(part,program,refs,entry=start,image_base=base,fields=fields,enums=enums,pointers=pointers)
    return dict(proof,methods=methods,enumValues={name:enums[role] for role,name in enum_types.items()},fieldOffsets=fields,getterProofs=getters,
        ordinaryEntryProof=dict(scope='ordinary-entry-with-separate-nonentry-code',completeOwnedBytePartition=True,computedGuardsProved=True,
            selectedBasesProved=True,incomingReceiverAndZeroProved=True,originalGetterFieldReturnsProved=True,exceptionalOrResumptionPathsProved=False,
            codeInstructions=len(part['rows']),ordinaryInstructions=len(program['rows']),tables=part['tables'],padding=part['padding'],
            nonEntryCode=program['nonEntryCode']))
