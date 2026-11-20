"""Authenticate bounded original authored action timing consumers.

No BodyIndex, disassembler, capture or full Skill family validation is used.
Exact pinned windows carry reviewed paths, while declarations and explicit ABI
operand checks guard the narrow facts admitted below.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp import protocol
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext, single_reference_generic_field
from scripts.game_data.skill_timing_runtime_native import _require, _validate_fields

SCHEMA='endfield.skill-action-timing-consumers-native-contract.v1'
AUDIT_SCHEMA='endfield.skill-action-timing-consumers-native-audit.v1'
CONTRACT_PATH=CONTRACTS_DIR/'skill_action_timing_consumers_native.json'
LABEL='skillActionTimingConsumers'


def _validate(image, contract):
    context=NativeReferenceContext(image)
    methods={}
    for row in contract['methods']:
        index=image.validate_method_row(row['identity'],label=LABEL)
        method=image.metadata.methods[index]
        actual={'returnType':context.type_name(method.return_type),
                'parameters':[{'name':image.metadata.string(p.name_index),'type':context.type_name(p.type_index)}
                              for p in image.metadata.parameters_for(method)]}
        _require(actual=={key:row[key]for key in actual} and not method.flags&0x10,
                 'action-method-signature',row,actual)
        _require(row['id'] not in methods,'action-method-duplicate','unique id',row['id'])
        nominal=row['identity'][1].removeprefix('Beyond.Gameplay.Core.')+'.'+row['identity'][2]
        _require(row['id']==nominal,'action-method-nominal',nominal,row['id'])
        methods[row['id']]=row
    windows=contract['codeWindows']
    _require(len({w['owner']for w in windows})==len(windows),'action-window-owner','unique owners',windows)
    for window in windows:
        if window['owner'] in methods:
            _require(window['startRva']==methods[window['owner']]['identity'][3],
                     'action-window-entry',methods[window['owner']]['identity'][3],window['startRva'])
    image.check_windows(windows,label=LABEL)
    fields=_validate_fields(image,contract['fields'])
    for field in fields.values():
        context.field(field['type']+'::'+field['name'])  # Reject static or duplicate declarations.
    layouts={}
    for row in contract['closedData']:
        proof=single_reference_generic_field(context,owner=row['owner'],field=row['field'],
            witness=row['witness'],concrete_instance_suffix=row['concreteInstanceSuffix'])
        _require(proof['fieldOffset']==row['expectedOffset'],'action-closed-data-offset',row['expectedOffset'],proof['fieldOffset'])
        layouts[row['witness']]=proof

    def checked(row):
        raw=bytes.fromhex(row['hex']);rva=row['rva']
        owners=[w for w in windows if w['owner']==row['owner']]
        _require(len(owners)==1,'action-operand-owner',row['owner'],len(owners))
        window=owners[0]
        _require(window['startRva']<=rva and rva+len(raw)<=window['endRva'],
                 'action-operand-window',window['owner'],rva)
        actual=image.pe.bytes_at_va(image.pe.image_base+rva,len(raw))
        _require(actual==raw,'action-operand-bytes',raw.hex(),actual.hex())
        return raw

    operands={}
    expected_fields={'duration':'duration','curveKey':'curveKey','useDirectCurve':'useDirectCurve',
                     'directCurve':'directCurve','affectType':'affectType','priorityTag':'timeDilationPriority'}
    for row in contract['fieldOperands']:
        raw=checked(row);field=fields[row['field']]
        _require(row['role'] in expected_fields and field['type']=='Beyond.Gameplay.Core.HitStopAction+Data'
                 and field['name']==expected_fields[row['role']], 'action-field-binding',expected_fields,row)
        at,size=row['displacementOffset'],row['displacementSize']
        _require(size==1 and 0<=at<len(raw) and raw[at]==field['offset'],
                 'action-field-operand',field['offset'],raw.hex())
        _require(row['role'] not in operands,'action-operand-duplicate','unique role',row['role'])
        operands[row['role']]=row
    _require(set(operands)==set(expected_fields),'action-field-coverage',expected_fields,operands)
    spans={row['role']:row for row in contract['flowSpans']}
    _require(len(spans)==len(contract['flowSpans']),'action-flow-duplicate','unique roles',contract['flowSpans'])
    raw_spans={role:checked(row)for role,row in spans.items()}
    calls={}
    expected_calls={
        'hitStopRequest':('HitStopAction.ExecuteInternal','TimeDilationManager.StartHitStop'),
        'entityTimeDilationRequest':('TimeDilationManager.StartHitStop','TimeDilationManager.StartEntityTimeDilation'),
        'allowPackAdd':('AllowNextSkillAction.ExecuteInternal','AbilitySystem+ComboController.AddAllowedNextSkillPack'),
        'allowPackRemove':('AllowNextSkillAction.OnEnd.removeHelper','AbilitySystem+ComboController.RemoveAllowedNextSkillPack'),
        'mappingAdd':('ComboCacheAction.ExecuteInternal','AbilitySystem+ComboController.AddMappingModifier')}
    for row in contract['directCalls']:
        _require(row['role'] in expected_calls,'action-call-role',list(expected_calls),row['role'])
        owner,target_method=expected_calls[row['role']]
        _require(row['owner']==owner,'action-call-owner',owner,row['owner'])
        _require(row['target']==methods[target_method]['identity'],'action-call-method-join',
                 methods[target_method]['identity'],row['target'])
        raw=checked(row)
        _require(len(raw)==5 and raw[0]==(0xe8 if row['opcode']=='call' else 0xe9),
                 'action-call-opcode',row['opcode'],raw.hex())
        image.validate_method_row(row['target'],label=LABEL)
        target=row['rva']+5+struct.unpack_from('<i',raw,1)[0]
        _require(target==row['target'][3],'action-call-target',row['target'][3],target)
        _require(row['role'] not in calls,'action-call-duplicate','unique role',row['role'])
        calls[row['role']]=row
    _require(set(calls)==set(expected_calls),'action-call-role-coverage',list(expected_calls),list(calls))
    _require(len(contract['localEdges'])==1,'action-local-edge-coverage',1,len(contract['localEdges']))
    for row in contract['localEdges']:
        _require((row['role'],row['owner'],row['targetOwner'])==(
            'allowOnEndToRemovalHelper','AllowNextSkillAction.OnEnd','AllowNextSkillAction.OnEnd.removeHelper'),
            'action-local-edge-role','named OnEnd to selected removal helper',row)
        raw=checked(row)
        targets=[window for window in windows if window['owner']==row['targetOwner']]
        _require(len(raw)==5 and raw[0]==0xe8 and len(targets)==1,
                 'action-local-edge','CALL rel32 to selected reviewed helper',row)
        target=row['rva']+5+struct.unpack_from('<i',raw,1)[0]
        _require(target==targets[0]['startRva'],'action-local-edge-target',targets[0]['startRva'],target)
    # This is the supported reviewed Win64 encoding: incoming this is saved in
    # nonvolatile R14, then the proved closed Data slot is loaded through R14.
    _require(raw_spans['ownedThisSave']==bytes.fromhex('4c8bf1'),
             'action-owned-this','MOV R14,RCX',raw_spans['ownedThisSave'].hex())
    load=raw_spans['ownedDataLoad']
    slot=layouts['Beyond.Gameplay.Core.HitStopAction']['fieldOffset']
    _require(len(load)==4 and load[:3]==bytes.fromhex('498b46') and load[3]==slot,
             'action-owned-data','MOV RAX,[R14+proved closed Data slot]',load.hex())
    forwarding=contract['durationForwarding']
    _require(forwarding['requestMethod']=='TimeDilationManager.StartHitStop'
             and forwarding['entityMethod']=='TimeDilationManager.StartEntityTimeDilation'
             and calls['hitStopRequest']['target']==methods[forwarding['requestMethod']]['identity']
             and calls['entityTimeDilationRequest']['target']==methods[forwarding['entityMethod']]['identity'],
             'action-forwarding-method-join','duration ABI declarations and actual named targets are identical',forwarding)
    field=fields[forwarding['sourceField']]
    _require(field['name']=='duration' and field['ordinaryKind']==12 and field['valueType']=='float',
             'action-duration-type','ordinary Single duration',field)
    source=checked(operands['duration'])
    _require(source[:4]==bytes.fromhex('f30f1040'),'action-duration-load','MOVSS XMM0,[RAX+duration]',source.hex())
    outgoing=raw_spans['durationOutgoingStack']
    outgoing_offset=forwarding['callerOutgoingStackOffset']
    _require(len(outgoing)==6 and outgoing[:5]==bytes.fromhex('f30f114424') and outgoing[5]==outgoing_offset,
             'action-duration-outgoing','MOVSS [RSP+argument],XMM0',outgoing.hex())
    request=methods[forwarding['requestMethod']]
    ordinal=forwarding['requestParameterIndex']
    _require(request['parameters'][ordinal]=={'name':forwarding['requestParameter'],'type':'float'}
             and ordinal>=3 and outgoing_offset==0x20+(ordinal-3)*8
             and forwarding['calleeEntryStackOffset']==outgoing_offset+8,
             'action-duration-request-abi','named Single in correct Win64 stack argument',forwarding)
    block=spans['requestArgumentBlock'];call=calls['hitStopRequest']
    _require(block['rva']==spans['ownedDataLoad']['rva']
             and block['rva']<=operands['duration']['rva']<spans['durationOutgoingStack']['rva']
             and spans['durationOutgoingStack']['rva']+len(outgoing)==call['rva']
             and block['rva']+len(raw_spans['requestArgumentBlock'])==call['rva']+5,
             'action-duration-request-path','reviewed contiguous Data load through outgoing store/call',block)
    prologue=raw_spans['calleePrologue']
    _require(len(prologue)==21 and prologue[:10]==bytes.fromhex('4c894c24204889542410')
             and prologue[10:17]==bytes.fromhex('415441554881ec'),
             'action-duration-prologue','two pushes and SUB RSP imm32',prologue.hex())
    stack=16+struct.unpack_from('<I',prologue,17)[0]
    _require(stack==forwarding['calleePrologueStackBytes']
             and stack+forwarding['calleeEntryStackOffset']==forwarding['calleeDurationLoadOffset'],
             'action-duration-stack-binding','entry duration slot after selected prologue',forwarding)
    incoming=raw_spans['sinkDurationIncoming']
    _require(len(incoming)==9 and incoming[:5]==bytes.fromhex('f30f109c24')
             and struct.unpack_from('<I',incoming,5)[0]==forwarding['calleeDurationLoadOffset'],
             'action-duration-incoming','MOVSS XMM3,[RSP+bound incoming duration]',incoming.hex())
    entity=methods[forwarding['entityMethod']]
    _require(entity['parameters'][forwarding['entityParameterIndex']]=={'name':forwarding['entityParameter'],'type':'float'}
             and forwarding['entityParameterIndex']==2 and forwarding['entityRegister']=='xmm3',
             'action-duration-entity-abi','third explicit Single parameter in XMM3',entity)
    entity_call=calls['entityTimeDilationRequest'];block=spans['entityRequestBlock']
    _require(block['rva']==spans['sinkDurationIncoming']['rva']
             and block['rva']+len(raw_spans['entityRequestBlock'])==entity_call['rva']+5,
             'action-duration-entity-path','reviewed contiguous incoming Single to named sink',block)
    enum=contract['affectEnum']
    actual=[{key:row[key]for key in ('id','name')}for row in protocol.native_enum_members(
        image.metadata,protocol.field_defaults(image.metadata),image.pe,image.registration,enum['type'])]
    _require(actual==enum['members'],'action-affect-enum',enum['members'],actual)
    _require(forwarding['originalPathOnly'] is True and forwarding['calleeKeyCurvePathOnly'] is True
             and forwarding['actualFrozenDurationProved'] is False
             and contract['rules']['completeControlRecoveryProved'] is False
             and contract['rules']['effectiveCacheDurationProved'] is False
             and contract['rules']['simultaneousBothFreezeProved'] is False
             and contract['rules']['affectSelectionCompiledProved'] is False
             and forwarding['intermediateCalleeStackPreservationProved'] is False
             and forwarding['requiresUnchangedIncomingDurationStack'] is True
             and forwarding['originalIfixSelectionObserved'] is False,
             'action-rule-boundary','original selected request arguments only',contract['rules'])
    def joined_edge(role):
        owner,target_method=expected_calls[role]
        source_identity=methods[owner]['identity'] if owner in methods else None
        return {'role':role,'sourceOwner':owner,'sourceIdentity':source_identity,
                'targetMethod':target_method,'targetIdentity':list(calls[role]['target'])}
    return {'durationForwarding':dict(forwarding),'affectEnum':actual,'rules':dict(contract['rules']),
            'rows':[{'id':'hitStopDurationRequest','evidence':'direct','sourceField':forwarding['sourceField'],
                     'edges':[joined_edge('hitStopRequest')],
                     'originalPathOnly':True,'actualFrozenDurationProved':False},
                    {'id':'hitStopDurationEntityRequest','evidence':'conditional',
                     'edges':[joined_edge('entityTimeDilationRequest')],
                     'requiresUnchangedIncomingDurationStack':True,
                     'intermediateCalleeStackPreservationProved':False,'originalIfixSelectionObserved':False,
                     'actualFrozenDurationProved':False},
                    {'id':'allowNextSkillSinks','evidence':'conditional','storedOperandsBoundToCall':False,
                     'edges':[joined_edge('allowPackAdd'),joined_edge('allowPackRemove')],
                     'removalSourceIdentity':list(methods['AllowNextSkillAction.OnEnd']['identity']),
                     'removalLocalEdgeRole':contract['localEdges'][0]['role']},
                    {'id':'comboCacheSink','evidence':'conditional','effectiveCacheDurationProved':False,
                     'edges':[joined_edge('mappingAdd')]}]}



def load_action_timing_consumers(contract_path:Path=CONTRACT_PATH,*,gameassembly:Path,metadata:Path):
    path=Path(contract_path)
    audit={'schema':AUDIT_SCHEMA,'status':'validation_failed','rows':[],'rules':{},'durationForwarding':{},
           'affectEnum':[],'nativeInputs':{},'failures':[],'contract':str(path)}
    try:
        contract,digest=read_reviewed_contract(path,schema=SCHEMA,status='reviewed',label=LABEL)
        audit.update(contractSha256=digest,evidenceBoundary=contract['evidenceBoundary'])
        pins=contract['nativeInputs'];gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],
            gameassembly=gameassembly,metadata=metadata)
        audit.update(status=gate.status,detail=gate.detail)
        if gate.status!='validated':return audit
        result=_validate(open_native_image(gate.gameassembly,gate.metadata),contract)
        after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],
            gameassembly=gate.gameassembly,metadata=gate.metadata)
        _require(after.status=='validated','action-native-after','same selected native pair',after.detail)
        _require(hashlib.sha256(path.read_bytes()).hexdigest().upper()==digest,
                 'action-contract-after','unchanged contract bytes','changed')
        audit.update(result,status='validated',detail='',nativeInputs=dict(pins))
    except (OSError,ValueError,KeyError,IndexError,TypeError,RuntimeError,struct.error)as error:
        audit.update(status='validation_failed',detail=str(error)[:800],rows=[],rules={},durationForwarding={},affectEnum=[],nativeInputs={})
        audit['failures'].append({'validator':LABEL,'check':str(error).split(':',1)[0], 'source':str(path),'detail':str(error)[:800]})
    return audit


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--contract',type=Path,default=CONTRACT_PATH)
    parser.add_argument('--gameassembly',type=Path,required=True);parser.add_argument('--metadata',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args(argv)
    from scripts.repo_paths import REPO_ROOT
    if not any(args.output.resolve().is_relative_to(REPO_ROOT/root)for root in ('scratch','tmp','reports')):
        parser.error('--output must stay under scratch/, tmp/ or reports/')
    audit=load_action_timing_consumers(args.contract,gameassembly=args.gameassembly,metadata=args.metadata)
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(audit,indent=2)+'\n')
    print(json.dumps({key:audit[key]for key in ('status','detail','failures')},indent=2))
    return 0 if audit['status']=='validated'else 1


if __name__=='__main__':raise SystemExit(main())
