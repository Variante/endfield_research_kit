"""Current ordinary-entry packet and runtime state call-lane proofs."""
from scripts.game_data.il2cpp.consumer_entry_program import read_ordinary_consumer_entry
from scripts.game_data.il2cpp.initializer_control import control_transfer
from scripts.game_data.il2cpp.summary_instructions import decode_summary_instructions
from scripts.game_data.il2cpp.int32_enum_transfer import check_int32_enum_transfer
from scripts.game_data.il2cpp.native_image import METADATA_HELPER_PATH
from scripts.game_data.il2cpp import protocol


def prove_levelscript_state_transfers(image):
    index=image.body_index;metadata=image.metadata;helper=protocol.load_metadata_helper(METADATA_HELPER_PATH);out={}
    runtime='Beyond.Gameplay.Core.LevelScriptRuntime';manager='Beyond.Gameplay.Core.LevelScriptManager'
    for role,owner,name,args,target_owner,target_name,target_args,lane,parameter,field in [
            ('incrementalState','Beyond.Gameplay.GameplayNetwork','_Handle_SceneLevelScriptStateNotify',['Proto.SC_SCENE_LEVEL_SCRIPT_STATE_NOTIFY'],
             manager,'ServerSyncLevelScriptState',['Beyond.Gameplay.Core.LevelScriptPtr','System.String','Beyond.GEnums.LevelScriptState',
                 'Beyond.Gameplay.Core.ScriptEndReason','System.Boolean'],'r9','msg','Proto.SC_SCENE_LEVEL_SCRIPT_STATE_NOTIFY::<State>k__BackingField'),
            ('snapshotState',runtime,'ServerSync',None,runtime,'set_state',['Beyond.GEnums.LevelScriptState'],'rdx','state',None)]:
        body=index.body(owner,name,parameters=args);target=index.body(target_owner,target_name,parameters=target_args)
        declarations=[r for r in index.names_by_pointer[body.pointer] if r['type']==owner and r['method']==name]
        if len(declarations)!=1:raise ValueError('levelscriptStateTransfers.unique-source:'+role)
        source_index=declarations[0]['methodIndex'];method=metadata.methods[source_index];td=metadata.types[method.declaring_type]
        info=helper.method_row(metadata,method)
        source=dict(type=metadata.type_full_name(td),method=info['name'],methodIndex=source_index,token=info['token'],
            returnTypeName=info['returnTypeName'],parameters=info['parameters'],parameterDetails=info['parameterDetails'],flags=info['flags'])
        program=read_ordinary_consumer_entry(image,body);summary=[]
        for a,b in program['ranges']:
            summary += [dict(r,offset=int(r['va'],16)-body.pointer) for r in decode_summary_instructions(image.mapper,image.pe.bytes_at_va(a,b-a),a)]
        states=image.mapper._instruction_origin_states(summary,body.pointer,image.mapper.param_origin_registers(source),
            {at-body.pointer:frame[0] for at,frame in program['control']['frames'].items()},index.names_by_pointer)
        calls=[r for r in program['rows'] if control_transfer(r)['kind']=='call' and control_transfer(r)['target']==target.pointer]
        if len(calls)!=1:raise ValueError('levelscriptStateTransfers.unique-call:'+role)
        call=calls[0];at=int(call['va'],16);values=dict(resolved=index.names_by_pointer[target.pointer],argumentOrigins=states[at-body.pointer][0])
        proof=check_int32_enum_transfer(metadata,image.pe,image.registration,source_index,values,lane,parameter,target_owner,target_name,source_field=field)
        if proof['status']!='validated':raise ValueError('levelscriptStateTransfers.enum-transfer:'+role+':'+proof.get('detail',''))
        out[role]=dict(proof,sourceMethod=body.symbol,targetMethod=target.symbol,callOffset=at-body.pointer,
            ordinaryEntryProof=dict(scope='ordinary-entry-with-separate-nonentry-code',completeOwnedBytePartition=True,
                ordinaryInstructions=len(program['rows']),unenteredOwnedByteCandidates=program['unenteredOwnedByteCandidates'],
                exceptionalOrResumptionPathsProved=False))
    return out
