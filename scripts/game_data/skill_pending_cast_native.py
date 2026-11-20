"""Authenticate the selected pending-record consumer through its cast attempt.

These are conditional original callbacks. Mode configuration/dispatch selection,
collection helper effects and eventual cast success are separate claims.
"""
from __future__ import annotations
import argparse, hashlib, json, struct
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext, validate_reference_ancestor_chain
from scripts.game_data.skill_timing_runtime_native import _require, _validate_fields

SCHEMA='endfield.skill-pending-cast-native-contract.v3'
AUDIT_SCHEMA='endfield.skill-pending-cast-native-audit.v3'
CONTRACT_PATH=CONTRACTS_DIR/'skill_pending_cast_native.json'
LABEL='skillPendingCast'
# Every instruction in these contiguous normal-return transfers is consumed.
# @ identifies a relative call or branch whose target is a reviewed named node.
PROGRAMS={'brainForwarding': '498b51{operand1:s1} 4533c0 4883c4{operand2:u1} @brainForward',
 'enterAcquire': '488b43{operand3:s1} c743{operand4:s1}{operand5:u4} '
                 'c643{operand6:s1}{operand5:u1} 4885c0 @enterEntityNull 488b88{operand7:s4} '
                 '4885c9 @enterAINull 488b89{operand8:s4} 4885c9 @enterBrainNull',
 'tickAcquire': '488b47{operand3:s1} 4885c0 @tickEntityNull 488b88{operand7:s4} 4885c9 @tickAINull '
                '488b89{operand8:s4} 4885c9 @tickBrainNull 33d2 @tickGet',
 'enterStore': '33d2 @brainGet 488d4b{operand9:s1} 488943{operand9:s1} @enterBarrier 33d2 488bcb '
               '4883c4{operand10:u1} 5b @enterTry',
 'tickStore': '488d4f{operand9:s1} c647{operand6:s1}{operand5:u1} c747{operand4:s1}{operand5:u4} '
              '488947{operand9:s1} @tickBarrier',
 'directArguments': '488b4e{operand9:s1} 4885c9 @directDataNull 33d2 @onEnd 4c8be0 '
                    '488b4e{operand3:s1} 4885c9 @directEntityNull 4c8bb1{operand11:s4} '
                    '488b4e{operand9:s1} 4885c9 @idDataNull 33d2 @skillId 4c8bf8 '
                    '488b4e{operand9:s1} 4885c9 @targetDataNull 33d2 @targetHandle 488bc8 '
                    '@targetView 488bd8 488b4e{operand9:s1} 4885c9 @callbackDataNull 4533ed 33d2 '
                    '@afterStart 0f57c0 33c9 0f118424{operand12:s4} 48898c24{operand13:s4} 4d85f6 '
                    '@abilityNull 0f298424{operand14:s4} 4489ac24{operand15:s4} '
                    '48897c24{operand16:s1} 40887c24{operand17:s1} 488d8c24{operand12:s4} '
                    '48894c24{operand18:s1} 48894424{operand19:s1} 48897c24{operand20:s1} '
                    '488d8424{operand14:s4} 48894424{operand21:s1} 4d8bcc 4c8bc3 498bd7 498bce '
                    '@cast',
 'castCommit': '8846{operand6:s1} 84c0 @castFalse 48397e{operand9:s1} @commitDataNull '
               '488b46{operand9:s1} c680{operand22:s4}{operand23:u1} @commitReturn',
 'tryLookup': '488b98{operand24:s4} 33d2 488b4e{operand9:s1} @lookupSkillId 4885db '
              '@lookupAbilityNull 4533c9 4c8d8424{operand25:s4} 488bd0 488bcb @tryGet 84c0 '
              '@lookupFalse',
 'tickRetry': 'f30f5877{operand4:s1} 33d2 488bcf f30f1177{operand4:s1} @tickTry',
 'tickPendingGuard': '4885c0 @tickNoPending 80b8{operand22:s4}{operand5:u1} @tickAlreadyCasting',
 'directLane': '4038b9{operand26:s4} @noSwitch 488b4e{operand3:s1} 4885c9 @switchEntityNull '
               'ba{operand27:u4} @entityModeHelper 84c0 @entityModeDirect',
 'afterAirCheck': '84c0 @airDirect',
 'afterSwitch': '84c0 @switchSucceeded 488d4c24{operand28:s1} @releaseTemp @switchFailedDirect',
 'tryNoData': '48397e{operand9:s1} @tryDataNull',
 'lookupFailure': '40887e{operand6:s1} @lookupFailureReturn',
 'getSkillId': '498b41{operand29:s1}',
 'getTargetHandle': '498b41{operand30:s1}',
 'getOnEnd': '498b41{operand31:s1}',
 'getAfterStart': '498b41{operand32:s1}',
 'targetViewCopy': '48895424{operand33:s1} 4883ec{operand34:u1} 488bd1 '
                   '48c74424{operand18:s1}{operand5:u4} 488d4c24{operand18:s1} @copyReference '
                   '488b4424{operand18:s1} 4883c4{operand34:u1} c3'}
PROGRAM_BINDINGS={'operand1': {'kind': 'field', 'field': 'brainEntity'},
 'operand2': {'kind': 'opaqueLiteral', 'role': 'brainForwarding'},
 'operand3': {'kind': 'field', 'field': 'behaviorEntity'},
 'operand4': {'kind': 'field', 'field': 'timer'},
 'operand5': {'kind': 'zero'},
 'operand6': {'kind': 'field', 'field': 'success'},
 'operand7': {'kind': 'field', 'field': 'entityAI'},
 'operand8': {'kind': 'field', 'field': 'aiBrain'},
 'operand9': {'kind': 'field', 'field': 'record'},
 'operand10': {'kind': 'opaqueLiteral', 'role': 'enterStore'},
 'operand11': {'kind': 'contextOffset', 'role': 'directArguments'},
 'operand12': {'kind': 'stackSlot', 'base': 'rsp'},
 'operand13': {'kind': 'stackSlot', 'base': 'rsp'},
 'operand14': {'kind': 'stackSlot', 'base': 'rsp'},
 'operand15': {'kind': 'stackSlot', 'base': 'rsp'},
 'operand16': {'kind': 'stackSlot', 'base': 'rsp'},
 'operand17': {'kind': 'stackSlot', 'base': 'rsp'},
 'operand18': {'kind': 'stackSlot', 'base': 'rsp'},
 'operand19': {'kind': 'stackSlot', 'base': 'rsp'},
 'operand20': {'kind': 'stackSlot', 'base': 'rsp'},
 'operand21': {'kind': 'stackSlot', 'base': 'rsp'},
 'operand22': {'kind': 'field', 'field': 'casting'},
 'operand23': {'kind': 'one'},
 'operand24': {'kind': 'contextOffset', 'role': 'tryLookup'},
 'operand25': {'kind': 'stackSlot', 'base': 'rsp'},
 'operand26': {'kind': 'field', 'field': 'switchBefore'},
 'operand27': {'kind': 'opaqueLiteral', 'role': 'directLane'},
 'operand28': {'kind': 'stackSlot', 'base': 'rsp'},
 'operand29': {'kind': 'inputField', 'base': 'input', 'field': 'inputId'},
 'operand30': {'kind': 'inputField', 'base': 'input', 'field': 'inputTarget'},
 'operand31': {'kind': 'inputField', 'base': 'input', 'field': 'inputEnd'},
 'operand32': {'kind': 'inputField', 'base': 'input', 'field': 'inputAfter'},
 'operand33': {'kind': 'stackSlot', 'base': 'rsp'},
 'operand34': {'kind': 'opaqueLiteral', 'role': 'targetViewCopy'}}
METHODS={
 'enter':('CharacterCastSkillBehavior','OnEnter'), 'tick':('CharacterCastSkillBehavior','OnTick'),
 'try':('CharacterCastSkillBehavior','_TryCastSkill'), 'rotate':('CharacterCastSkillBehavior','_RotateToTarget'),
 'brain':('CharacterAIBrain','GetComboSkillData'), 'pending':('CharacterSkillSystem','GetComboSkillData'),
 'id':('CharacterSkillSystem+SkillData','get_skillId'), 'target':('CharacterSkillSystem+SkillData','get_targetHandle'),
 'end':('CharacterSkillSystem+SkillData','get_onCastEnd'), 'after':('CharacterSkillSystem+SkillData','get_afterCastStartCallback'),
 'cast':('Beyond.Gameplay.Core.AbilitySystem','TryCastSkill'), 'lookup':('Beyond.Gameplay.Core.AbilitySystem','TryGetSkill'),
 'switch':('Beyond.Gameplay.Core.AbilitySystem','SwitchCenterBySkill'),
 'air':('Beyond.Gameplay.Core.MovementComponent','get_isInAir'),
 'playerCast':('Beyond.Gameplay.Core.PlayerController','CastSkill'),
 'mode':('CharacterAIBrain','SwitchAIMode')}
CALLS={
 'brainGet':('enter','brain','e8'),'tickGet':('tick','brain','e8'),
 'enterTry':('enter','try','e9'),'tickTry':('tick','try','e8'),
 'lookupSkillId':('try','id','e8'),'tryGet':('try','lookup','e8'),
 'onEnd':('try','end','e8'),'skillId':('try','id','e8'),'targetHandle':('try','target','e8'),
 'afterStart':('try','after','e8'),'cast':('try','cast','e8'),
 'rotate':('try','rotate','e8'),'switch':('try','switch','e8'),
 'air':('try','air','e8'),'playerCast':('try','playerCast','e8'),
 'brainForward':('brain','pending','e9')}


def _program_operands(contract,fields,bindings):
    declared=contract['operandBindings']
    _require(set(declared)==set(bindings),'program-operand-coverage',list(bindings),list(declared))
    result={}
    for name,expected in bindings.items():
        row=declared[name]
        _require({k:v for k,v in row.items()if k!='value'}==expected,'program-operand-binding-'+name,expected,row)
        value=row['value']
        _require(type(value)is int,'program-operand-integer',name,value)
        if expected['kind']=='field':actual=fields[expected['field']]['offset']
        elif expected['kind']=='inputField':actual=fields[expected['base']]['offset']+fields[expected['field']]['offset']-contract['inputDataHeaderBytes']
        elif expected['kind']=='viewField':actual=fields[expected['field']]['offset']-contract['inputViewHeaderBytes']
        elif expected['kind']=='zero':actual=0
        elif expected['kind']=='one':actual=1
        else:
            _require(expected['kind']in('stackSlot','contextOffset','opaqueLiteral','conditionalEntityOffset'),
                'program-operand-kind','bounded reviewed declaration',expected)
            actual=value
        _require(value==actual,'program-operand-field-'+name,actual,value);result[name]=value
    return result


def _render_program(shape,operands):
    import re
    def encode(match):
        value=operands[match[1]];signed=match[2]=='s';width=int(match[3])
        try:return value.to_bytes(width,'little',signed=signed).hex()
        except OverflowError as error:raise ValueError('program-operand-range:'+match[1])from error
    return re.sub(r'\{([A-Za-z0-9_]+):([su])([1248])\}',encode,shape)



def _relative(raw,rva):
    if len(raw)==5 and raw[0]in(0xe8,0xe9):return rva+5+struct.unpack_from('<i',raw,1)[0]
    if len(raw)==2 and raw[0]in(0x74,0x75,0xeb,0x79):return rva+2+int.from_bytes(raw[1:],'little',signed=True)
    if len(raw)==6 and raw[:2]in(b'\x0f\x84',b'\x0f\x85'):return rva+6+struct.unpack_from('<i',raw,2)[0]
    raise ValueError('pending-relative-encoding')


def _scope(contract):
    rules=contract['rules']
    expected=dict(originalPathOnly=True,normalHelperReturnRequired=True,runtimeBehaviorSelectionProved=False,
      collectionEffectsProved=False,completePlayerInputAcceptanceProved=False,
      recordReloadedAfterTryCast=True,stableRecordIdentityRequiredForSameRecordClaim=True,behaviorEntityFieldLayoutProved=True,tryCastResultStored=True,castingSetOnlyOnTrue=True,
      missingPendingReturns=True,tryGetFalseStoresSuccessFalse=True,
      directLaneOrder=['pendingNonnull','TryGetSkill','switchToCenterBeforeCast','entityModeHelper','isInAir','SwitchCenterBySkill','rotate','pendingGetters','TryCastSkill','storeSuccess','conditionalCastingCommit'],
      specialLaneRequest='PlayerController.CastSkill',distanceAndAngleReevaluatedHere=False)
    _require(json.dumps(rules,sort_keys=True,separators=(',',':'))==json.dumps(expected,sort_keys=True,separators=(',',':')),'pending-rule-scope',expected,rules)
    _require({r['id']for r in contract['facts']}=={'pendingAcquire','pendingRetry','pendingCastAttempt','pendingCastCommit'}and
        len(contract['facts'])==4 and all(r['evidence']=='conditional'and r['rules']==rules and r['boundary']for r in contract['facts']),
        'pending-facts','four conditional bound facts',contract['facts'])
    return rules


def _validate(image,contract):
    rules=_scope(contract);context=NativeReferenceContext(image);methods={}
    for row in contract['methods']:
        role=row['id'];index=image.validate_method_row(row['identity'],label=LABEL);method=image.metadata.methods[index]
        actual=dict(returnType=context.type_name(method.return_type),parameters=[dict(name=image.metadata.string(p.name_index),type=context.type_name(p.type_index))for p in image.metadata.parameters_for(method)])
        _require(actual=={k:row[k]for k in actual}and not method.flags&0x10,'pending-signature',row,actual)
        owner,name=METHODS[role];owner=owner if owner.startswith('Beyond.')else'Beyond.Gameplay.AI.'+owner
        _require(row['identity'][1:3]==[owner,name]and role not in methods,'pending-method-nominal',[owner,name],row)
        methods[role]=row
    _require(set(methods)==set(METHODS),'pending-method-coverage',list(METHODS),list(methods))
    windows=contract['codeWindows'];image.check_windows(windows,label=LABEL);owners={r['owner']:r for r in windows}
    _require(len(owners)==len(windows),'pending-window-unique','unique',windows)
    for role in('enter','tick','try','brain','pending','id','target','end','after'):
        _require(owners[role]['startRva']==methods[role]['identity'][3],'pending-window-entry',methods[role]['identity'][3],owners[role])
    fields=_validate_fields(image,contract['fields'])
    entity=fields['behaviorEntity']
    _require((entity['type'],entity['name'],entity['valueType'],entity['ordinaryKind'])==
        ('Beyond.Gameplay.AI.AIBehavior','m_entity','Beyond.Gameplay.Core.Entity',18),
        'pending-inherited-entity-declaration','AIBehavior.m_entity: ordinary Entity reference',entity)
    owner=methods['enter']['identity'][1]
    expected_chain=[
        'Beyond.Gameplay.AI.CharacterAIBehavior`1<Beyond.Gameplay.AI.CharacterCastSkillBehavior+CharacterCastSkillBehaviorData>',
        'Beyond.Gameplay.AI.CharacterAIBehavior','Beyond.Gameplay.AI.AIBehavior']
    _require(contract['behaviorEntityAncestors']==expected_chain,
        'pending-inherited-entity-chain',expected_chain,contract['behaviorEntityAncestors'])
    validate_reference_ancestor_chain(context,owner,contract['behaviorEntityAncestors'],entity['type'])
    def checked(row):
        raw=bytes.fromhex(row['hex']);w=owners[row['owner']];rva=row['rva']
        _require(raw and w['startRva']<=rva<rva+len(raw)<=w['endRva'],'pending-owner-span',w,row)
        _require(image.pe.bytes_at_va(image.pe.image_base+rva,len(raw))==raw,'pending-span-bytes',row,'native differs');return raw
    nodes={r['id']:r for r in contract['nodes']}
    _require(len(nodes)==len(contract['nodes']),'pending-node-distinct','unique',nodes)
    for row in nodes.values():checked(row)
    for role,(owner,target,opcode)in CALLS.items():
        row=nodes[role];raw=checked(row)
        _require(row['owner']==owner and raw[:1].hex()==opcode and _relative(raw,row['rva'])==methods[target]['identity'][3],
            'pending-nominal-call-'+role,(owner,target,opcode),row)
    programs={r['id']:r for r in contract['programs']}
    _require(set(programs)==set(PROGRAMS),'pending-program-coverage',list(PROGRAMS),list(programs))
    operands=_program_operands(contract,fields,PROGRAM_BINDINGS)
    _require(set(contract['reviewedPrograms'])==set(PROGRAMS),'pending-reviewed-program-coverage',list(PROGRAMS),list(contract['reviewedPrograms']))
    for role,grammar in PROGRAMS.items():
        shape=_render_program(grammar,operands)
        _require(contract['reviewedPrograms'][role]==shape,'pending-reviewed-program-declaration',shape,contract['reviewedPrograms'][role])
        row=programs[role];raw=checked(row);at=0
        for token in shape.split():
            if token.startswith('@'):
                name=token[1:];node=nodes[name];part=checked(node)
                _require(node['owner']==row['owner']and node['rva']==row['rva']+at,'pending-program-node-'+name,'contiguous selected site',node)
            else:part=bytes.fromhex(token)
            _require(raw[at:at+len(part)]==part,'pending-program-operation-'+role,token,raw[at:at+len(part)].hex());at+=len(part)
        _require(at==len(raw),'pending-program-length',at,len(raw))
    edges={r['source']:r for r in contract['edges']}
    expected={'directDataNull':('exception','0f84'),'directEntityNull':('exception','0f84'),
      'idDataNull':('exception','0f84'),'targetDataNull':('exception','0f84'),'callbackDataNull':('exception','0f84'),
      'abilityNull':('exception','74'),'castFalse':('tryReturn','0f84'),'commitDataNull':('tryReturn','0f84'),
      'commitReturn':('tryReturn','e9'),'lookupAbilityNull':('exception','0f84'),
      'lookupFalse':('lookupFailure','0f84'),'lookupFailureReturn':('tryReturn','e9'),
      'tickNoPending':('tickSuccessCheck','74'),'tickAlreadyCasting':('tickSuccessCheck','75'),
      'noSwitch':('directStart','0f84'),'switchEntityNull':('exception','0f84'),
      'entityModeDirect':('directStart','0f85'),'airDirect':('directStart','0f85'),
      'switchSucceeded':('specialStart','75'),'switchFailedDirect':('directStart','e9'),
      'tryDataNull':('tryReturn','74'),
      'enterEntityNull':('enterException','74'),'enterAINull':('enterException','74'),
      'enterBrainNull':('enterException','74'),'tickEntityNull':('tickException','0f84'),
      'tickAINull':('tickException','0f84'),'tickBrainNull':('tickException','0f84')}
    _require(len(edges)==len(contract['edges'])and{r:(v['target'],v['opcode'])for r,v in edges.items()}==expected,
        'pending-edge-coverage',expected,contract['edges'])
    for source,edge in edges.items():
        row=nodes[source];raw=checked(row)
        _require(raw.hex().startswith(edge['opcode'])and _relative(raw,row['rva'])==nodes[edge['target']]['rva'],
            'pending-edge-'+source,edge,raw.hex())
    for name,window in [('targetView','targetView'),('copyReference','copyRef')]:
        row=nodes[name];raw=checked(row)
        _require(raw[0]==0xe8 and _relative(raw,row['rva'])==owners[window]['startRva'],
            'pending-target-carrier-copy',window,row)
    copy=owners['copyRef'];raw=image.pe.bytes_at_va(image.pe.image_base+copy['startRva'],13)
    _require(raw[:2]==b'\x83\x3d'and raw[6:]==bytes.fromhex('004c8bc1488911'),
        'pending-target-carrier-store','MOV [RCX],RDX before barrier-only branch',raw.hex())
    # Nominal layout joins for the stored reference and its boolean commit.
    _require(fields['record']['valueType']=='Beyond.Gameplay.AI.CharacterSkillSystem+SkillData'
      and fields['input']['valueType']=='Beyond.Gameplay.Core.SkillCastInputData'
      and fields['casting']['valueType']=='bool','pending-carrier-types','typed record/input/casting',fields)
    for getter,field in [('getSkillId','inputId'),('getTargetHandle','inputTarget'),('getOnEnd','inputEnd'),('getAfterStart','inputAfter')]:
        offset=checked(programs[getter])[-1]
        _require(offset==fields['input']['offset']+fields[field]['offset']-contract['inputDataHeaderBytes'],
            'pending-input-getter-'+getter,'runtime boxed value offset minus explicit header16',offset)
    _require(type(contract['inputDataHeaderBytes'])is int and contract['inputDataHeaderBytes']==fields['inputId']['offset'] and contract['inputDataHeaderBytes']>0,'pending-input-header','selected first input field starts after the declared header',contract['inputDataHeaderBytes'])
    return dict(rules)


def load_skill_pending_cast(contract_path=CONTRACT_PATH,*,gameassembly=None,metadata=None):
    path=Path(contract_path);audit=dict(schema=AUDIT_SCHEMA,status='validation_failed',nativeInputs={},rows=[],rules={},failures=[],contract=str(path))
    try:
        contract,digest=read_reviewed_contract(path,schema=SCHEMA,status='reviewed',label=LABEL)
        audit.update(contractSha256=digest,evidenceBoundary=contract['evidenceBoundary'])
        pins=contract['nativeInputs'];gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
        audit.update(status=gate.status,detail=gate.detail)
        if gate.status!='validated':return audit
        rules=_validate(open_native_image(gate.gameassembly,gate.metadata),contract)
        after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
        _require(after.status=='validated','pending-native-after','validated',after.detail)
        _require(hashlib.sha256(path.read_bytes()).hexdigest().upper()==digest,'pending-contract-after','unchanged','changed')
        audit.update(status='validated',detail='',nativeInputs=dict(pins),rows=contract['facts'],rules=rules)
    except(OSError,ValueError,KeyError,TypeError,IndexError,RuntimeError,struct.error)as error:
        audit.update(status='validation_failed',detail=str(error)[:1200],nativeInputs={},rows=[],rules={})
        audit['failures'].append(dict(validator=LABEL,source=str(path),check=str(error).split(':',1)[0],detail=str(error)[:1200]))
    return audit


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--gameassembly',type=Path);parser.add_argument('--metadata',type=Path);parser.add_argument('--output',type=Path)
    args=parser.parse_args(argv);audit=load_skill_pending_cast(gameassembly=args.gameassembly,metadata=args.metadata)
    if args.output:
        from scripts.repo_paths import REPO_ROOT
        if not any(args.output.resolve().is_relative_to(REPO_ROOT/root)for root in('reports','scratch','tmp')):parser.error('output must be reports/scratch/tmp')
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(audit,indent=2)+'\n')
    print(json.dumps({k:audit[k]for k in('status','detail','failures')},indent=2));return int(audit['status']!='validated')
if __name__=='__main__':raise SystemExit(main())
