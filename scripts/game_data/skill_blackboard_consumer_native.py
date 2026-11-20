"""Selected typed CenterBlackboard consumer and post-cast cleanup fragments.

This is the direct CenterSkillState -> TryCastSkill route, not the separate
cache-tick -> pending route. Actual FSM selection and same live BB instance
between writer/consumer are not established here.
"""
from __future__ import annotations
import hashlib,json,struct
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext,validate_reference_ancestor_chain
from scripts.game_data.skill_timing_runtime_native import _require,_validate_fields
from scripts.game_data.skill_pending_storage_native import _match
SCHEMA='endfield.skill-blackboard-consumer-native-contract.v1'
AUDIT_SCHEMA='endfield.skill-blackboard-consumer-native-audit.v1'
CONTRACT_PATH=CONTRACTS_DIR/'skill_blackboard_consumer_native.json'
AI='Beyond.Gameplay.AI.CharacterMainCtrlSystem+';CORE='Beyond.Gameplay.Core.'
METHODS={'enter':(AI+'CenterSkillState','OnEnter'),'cast':(AI+'CenterSkillState','_DoCastSkill'),'view':(CORE+'SkillCastInputView','.ctor'),'try':(CORE+'AbilitySystem','TryCastSkill'),'clearRequest':(CORE+'AbilitySystem','ClearSkillRequest'),'comboClear':(CORE+'AbilitySystem+ComboController','ClearSkillRequest'),'dispose':(CORE+'SkillCastInputData','Dispose'),'stop':(AI+'CenterBlackboard','Stop'),'clear':(AI+'CenterBlackboard','Clear'),'clearAll':(AI+'CenterBlackboard','ClearAll'),'perfect':(AI+'CenterSkillState','_ProcessPerfectDodge')}

def _rules():return dict(originalPathOnly=True,normalWin64HelperReturnRequired=True,stateReceiverContinuityPremiseRequired=True,blackboardInputPayloadBytes=88,typedNamedBlackboardFieldProved=True,sameWriterConsumerLiveBlackboardProved=False,runtimeFSMSelectionProved=False,blackboardToPendingJoinProved=False,directTryCastRouteProved=True,viewConstructorResultExplicitRequired=True,selectedOptionsCarrierExplicitRequired=True,tryCastBoolUsedForCleanupBranch=False,cleanupReloadsBlackboard=True,cleanupClearsSkillEndCallbackOnly=True,cleanupThenReloadsEntityThenAbility=True,nullCleanupCarrierRequiresExceptionalExit=True,clearRequestTailForwardsToComboClear=True,stopAndClearDisposeBeforeDirectZero88=True,blackboardClearAllOriginalNoOp=True,keepTrueClearsFlagAndSkipsCast=True,baseOnEnterEffectsExcludedFromKeepPrimitive=True,upstreamSkillInstanceContinuityProved=False,currentSessionBlackboardIdentityProved=False)

def _same(a,b):return json.dumps(a,sort_keys=True,allow_nan=False)==json.dumps(b,sort_keys=True,allow_nan=False)

def _validate(image,c):
    cx=NativeReferenceContext(image);validate_reference_ancestor_chain(cx,AI+'CenterSkillState',[AI+'CenterStateBase'],AI+'CenterStateBase')
    fields=_validate_fields(image,c['fields']);off={k:r['offset']for k,r in fields.items()}
    expected={'stateBB':(AI+'CenterStateBase','m_blackboard',AI+'CenterBlackboard',18),'stateEntity':(AI+'CenterStateBase','m_entity',CORE+'Entity',18),'keep':(AI+'CenterSkillState','keepSkillOnEnter','bool',2),'bbInput':(AI+'CenterBlackboard','skillInputData',CORE+'SkillCastInputData',17),'inputEnd':(CORE+'SkillCastInputData','skillEndCallback','System.Action`2<'+CORE+'Skill+FinishType,int>',21),'entityAbility':(CORE+'Entity','<abilityCom>k__BackingField',CORE+'AbilitySystem',18),'combo':(CORE+'AbilitySystem','m_comboController',CORE+'AbilitySystem+ComboController',18),'viewId':(CORE+'SkillCastInputView','skillId','string',14),'viewTarget':(CORE+'SkillCastInputView','targetHandleView',CORE+'TargetHandleView',17),'viewEnd':(CORE+'SkillCastInputView','skillEndCallback','System.Action`2<'+CORE+'Skill+FinishType,int>',21),'viewAfter':(CORE+'SkillCastInputView','afterCastStartCallback','System.Action`1<'+CORE+'Skill>',21),'viewExclusive':(CORE+'SkillCastInputView','onExclusiveTimeCallback','System.Action`1<'+CORE+'Skill>',21),'viewInfo':(CORE+'SkillCastInputView','skillCastInfo',CORE+'Skill+SkillCastInfo',17),'viewSkip':(CORE+'SkillCastInputView','skipApplyCost','bool',2)}
    _require(set(fields)==set(expected),'bb-field-coverage',sorted(expected),sorted(fields))
    for key,(owner,name,ty,kind)in expected.items():
        r=fields[key];_require((r['type'],r['name'],r['valueType'])==(owner,name,ty)and type(r['ordinaryKind'])is int and r['ordinaryKind']==kind and type(r['offset'])is int,'bb-field-nominal',expected[key],r)
    header=c['boxedHeaderBytes'];_require(type(header)is int and header>0,'bb-header','ordinary boxed header extent',header);off['postCallback']=off['bbInput']+off['inputEnd']-header
    methods={}
    for r in c['methods']:
        role=r['id'];_require(role in METHODS and role not in methods and r['identity'][1:3]==list(METHODS[role]),'bb-method-role',METHODS.get(role),r);index=image.validate_method_row(r['identity'],label='skillBlackboardConsumer');m=image.metadata.methods[index]
        actual=dict(returnType=cx.type_name(m.return_type),parameters=[dict(name=image.metadata.string(p.name_index),type=cx.type_name(p.type_index))for p in image.metadata.parameters_for(m)])
        _require(not m.flags&16 and _same(actual,{k:r[k]for k in actual}),'bb-method-signature',r,actual);methods[role]=r
    _require(set(methods)==set(METHODS),'bb-method-coverage',sorted(METHODS),sorted(methods));image.check_windows(c['codeWindows'],label='skillBlackboardConsumer')
    for role,r in methods.items():
        windows=[[w['startRva'],w['endRva']]for w in c['codeWindows']if w['owner']==role]
        if role=='clearAll':_require(windows==[[r['identity'][3],r['identity'][3]+c['clearAllLeafBytes']]],'bb-leaf-owner','complete reviewed leaf grammar',windows)
        else:_require(windows==[x['runtimeTriple'][:2]for x in image.unwind_index.family(r['identity'][3])['ranges']],'bb-window-owner','complete selected family',role)
    spans={r['id']:r for r in c['spans']};raws={};op=c['operands'];_require(all(type(v)is int for v in op.values()),'bb-operands','ordinary integers',op)
    for key,r in spans.items():
        raw=bytes.fromhex(r['hex']);cursor=r['rva']
        for a,b in sorted((w['startRva'],w['endRva'])for w in c['codeWindows']if w['owner']==r['owner']):
            if a<=cursor<b:cursor=min(b,r['rva']+len(raw))
        _require(raw and cursor==r['rva']+len(raw)and image.pe.bytes_at_va(image.pe.image_base+r['rva'],len(raw))==raw,'bb-native-span',key,r);raws[key]=raw
    required={'keepGuard','keepExit','enterInvoke','copyInput','tryReceiver','tryGuard','tryArgs','postCallback','postClear','clearForward','clearPrefix','stopBody','clearBody','stopPrefix','clearPrefixBB','clearAllLeaf'}
    _require(set(spans)==required,'bb-program-coverage',sorted(required),sorted(spans));targets={**{k:r['identity'][3]for k,r in methods.items()},**{k:r['rva']for k,r in spans.items()},**op}
    h=bytes.fromhex;F=lambda k,w=1:('field',k,w);O=lambda k,w=1:('operand',k,w);R=lambda k,w=4:('relative',k,w)
    def check(key,parts):_require(_match(raws[key],spans[key]['rva'],parts,off,op,targets),'bb-semantic-program',key,raws[key].hex())
    check('keepGuard',[h('807b'),F('keep'),h('000f85'),R('keepExit')]);check('keepExit',[h('c643'),F('keep'),h('00e9'),R('enterReturnRva')])
    check('enterInvoke',[h('33d2488bcbe8'),R('cast'),h('33d2488bcbe8'),R('perfect')])
    copy=[h('488b43'),F('stateBB'),h('0f57c00f114424'),O('defaultOptionsStack'),h('66c74424'),O('defaultOptionsStack'),O('fallbackOptionsWord',2),h('0f287424'),O('defaultOptionsStack'),h('4885c00f84'),R('castNullRva')]
    copy += [h('0f1040'),F('bbInput'),h('4533c0488d55'),O('inputTempRbp'),h('0f1048'),('operand','bbChunk1',1),h('488d4d'),O('viewTempRbp'),h('0f2945'),O('inputTempRbp')]
    for i in range(2,5):copy += [h('0f1040'if i%2==0 else '0f1048'),O('bbChunk'+str(i)),h('0f294d'if i%2==0 else '0f2945'),O('inputChunk'+str(i-1))]
    copy += [h('f20f1048'),O('bbChunk5'),h('0f2945'),O('inputChunk4'),h('f20f114d'),O('inputChunk5'),h('e8'),R('view')]
    check('copyInput',copy)
    _require(all(op[role+'Rbp']==op['viewTempRbp']+off[role]-header for role in ['viewId','viewTarget','viewEnd','viewAfter','viewExclusive','viewInfo','viewSkip']),'bb-view-argument-field-binding','named local-view fields to actual TryCast argument loads',op)
    _require(op['bbChunk0']==off['bbInput']and op['bbChunk1']==off['bbInput']+16 and all(op['bbChunk'+str(i)]==off['bbInput']+16*i for i in range(2,6))and all(op['inputChunk'+str(i)]==op['inputTempRbp']+16*i for i in range(1,6)),'bb-copy-chunk-layout','five16+eight bytes to constructor input',op)
    check('tryReceiver',[h('488b43'),F('stateEntity'),h('4885c00f84'),R('castNullRva'),h('4c8b90'),F('entityAbility',4),h('33ff66897c24'),O('nullablePadWordStack'),h('40887c24'),O('nullablePadByteStack'),h('c64424'),O('nullableOptionsStack'),h('010f117424'),O('nullableValueStack'),h('4d85d20f84'),R('castNullRva')])
    check('tryGuard',[h('488b05'),R('tryDispatchCell'),h('488b48'),O('dispatchOffset'),h('4885c90f85'),R('tryReplacementRva')])
    check('tryArgs',[h('0fb645'),O('viewSkipRbp'),h('498bca0f104424'),O('nullableOptionsStack'),h('4c8b4d'),O('viewEndRbp'),h('4c8b45'),O('viewTargetRbp'),h('488b55'),O('viewIdRbp'),h('48897c24'),O('methodInfoStack'),h('884424'),O('skipStack'),h('488d45'),O('viewInfoRbp'),h('48894424'),O('infoStack'),h('488b45'),O('viewAfterRbp'),h('48894424'),O('afterStack'),h('488b45'),O('viewExclusiveRbp'),h('48894424'),O('exclusiveStack'),h('488d4424'),O('nullableOptionsStack'),h('660f73de'),O('optionsTailShift'),h('48894424'),O('optionsStack'),h('0f294424'),O('nullableOptionsStack'),h('660f7e7424'),O('nullableTailStack'),h('e8'),R('try')])
    check('postCallback',[h('488b4b'),F('stateBB'),h('4885c974'),R('castNullRva',1),h('488979'),F('postCallback'),h('4883c1'),F('postCallback'),h('e8'),R('barrierRva')])
    check('postClear',[h('4c8b4b'),F('stateEntity'),h('4d85c974'),R('castNullRva',1),h('498b89'),F('entityAbility',4),h('4885c974'),R('castNullRva',1),h('33d2e8'),R('clearRequest')])
    check('clearPrefix',[h('4883ec'),O('clearFrame'),h('488b05'),R('clearTypeInfoCell'),h('4c8b48'),O('dispatchOffset'),h('4d85c90f85'),R('clearReplacementRva')])
    check('clearForward',[h('488b89'),F('combo',4),h('4885c974'),R('clearNullRva',1),h('33d24883c4'),O('clearFrame'),h('e9'),R('comboClear')])
    for role,body in [('stop','stopBody'),('clear','clearBody')]:
        prefix=role+'Prefix'if role=='stop'else 'clearPrefixBB';check(prefix,[h('40534883ec'),O('bbFrame'),h('488b05'),R('clearTypeInfoCellForBB'if role=='clear'else 'stopTypeInfoCell'),h('488bd9488b48'),O('bbDispatchOffset'),h('4885c90f85'),R('clearReplacementRvaForBB'if role=='clear'else 'stopReplacementRva')])
        zero=[h('488d4b'),F('bbInput'),h('33d2e8'),R('dispose'),h('0f57c033c0')]
        for i in range(5):zero += [h('0f1143'),O('bbChunk'+str(i))]
        zero += [h('488943'),O('bbChunk5')];check(body,zero)
        _require(spans[prefix]['rva']==methods[role]['identity'][3]and spans[prefix]['rva']+len(raws[prefix])==spans[body]['rva'],'bb-clear-entry-carrier','RCX captured to RBX before Dispose/zero',role)
    check('clearAllLeaf',[h('488b05'),R('clearAllTypeInfoCell'),h('4c8bc9488b48'),O('bbDispatchOffset'),h('4885c974'),R('clearAllRetRva',1),h('488b81'),O('clearAllFunctionOffset',4),h('4885c074'),R('clearAllRetRva',1),h('488b89'),O('clearAllContextOffset',4),h('4c8bc2498bd148ffe0c3')])
    for left,right in [('tryReceiver','tryGuard'),('tryGuard','tryArgs'),('tryArgs','postCallback'),('postCallback','postClear'),('clearPrefix','clearForward')]:_require(spans[left]['rva']+len(raws[left])==spans[right]['rva'],'bb-contiguous-edge',left,right)
    _require(spans['clearPrefix']['rva']==methods['clearRequest']['identity'][3]and spans['clearAllLeaf']['rva']==methods['clearAll']['identity'][3]and op['clearAllRetRva']==spans['clearAllLeaf']['rva']+len(raws['clearAllLeaf'])-1,'bb-method-entry','selected wrapper/leaf entries',spans)
    for role,key in [('cast','castNullRva'),('clearRequest','clearNullRva')]:
        at=op[key];raw=image.pe.bytes_at_va(image.pe.image_base+at,6);_require(raw[:1]==b'\xe8'and raw[5:]==b'\xcc'and at+5+struct.unpack_from('<i',raw,1)[0]==op['nullHelperRva']and any(w['owner']==role and w['startRva']<=at<at+6<=w['endRva']for w in c['codeWindows']),'bb-null-exit','selected exceptional helper + INT3',key)
    _require(_same(c['rules'],_rules()),'bb-rules',_rules(),c['rules']);return _rules()

def load_skill_blackboard_consumer(contract_path=CONTRACT_PATH,*,gameassembly=None,metadata=None):
    p=Path(contract_path);a=dict(schema=AUDIT_SCHEMA,status='validation_failed',nativeInputs={},rows=[],rules={},callerBindings=[],failures=[])
    try:
        c,digest=read_reviewed_contract(p,schema=SCHEMA,status='reviewed',label='skillBlackboardConsumer');pins=c['nativeInputs'];g=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata);a.update(status=g.status,detail=g.detail)
        if g.status!='validated':return a
        rules=_validate(open_native_image(g.gameassembly,g.metadata),c);after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=g.gameassembly,metadata=g.metadata)
        _require(after.status=='validated'and hashlib.sha256(p.read_bytes()).hexdigest().upper()==digest,'bb-input-bookend','unchanged selected inputs',after.detail)
        methods={r['id']:r['identity']for r in c['methods']};spans={r['id']:r for r in c['spans']};bindings=[]
        for role,target,span,tail in [('directTryCast','try','tryArgs',False),('postCastClearRequest','clearRequest','postClear',False),('clearRequestTailAlias','comboClear','clearForward',True)]:
            r=spans[span];site=r['rva']+len(bytes.fromhex(r['hex']))-5;bindings.append(dict(role=role,owner=methods[r['owner']],siteRva=site,target=methods[target],returnRva=None if tail else site+5,tailForwardPreservesCallerReturn=tail))
        a.update(status='validated-conditional-fragments',detail='',nativeInputs=dict(pins),rules=rules,rows=[dict(id='typedBlackboardConsumer',evidence='conditional',rules=rules)],callerBindings=bindings,fieldBindings=c['fields'],boundaries=c['boundaries'])
    except(OSError,ValueError,KeyError,TypeError,IndexError,RuntimeError,struct.error)as e:a.update(status='validation_failed',detail=str(e)[:1200],nativeInputs={},rows=[],rules={},callerBindings=[],failures=[dict(check=str(e).split(':',1)[0],detail=str(e)[:1200])])
    return a
