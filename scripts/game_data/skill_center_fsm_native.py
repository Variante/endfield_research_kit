"""Conditional Center FSM construction and state registration fragments.

The cast helper's source/null identity is proved without claiming its class
predicate. Generic scheduling/selection and live writer-reader ownership remain
unresolved; nominal vtable membership does not prove a runtime dispatch.
"""
from __future__ import annotations
import hashlib,json,struct
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext,validate_reference_ancestor_chain
from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context,_vtable
from scripts.game_data.skill_timing_runtime_native import _require,_validate_fields
from scripts.game_data.skill_pending_storage_native import _match
SCHEMA='endfield.skill-center-fsm-native-contract.v1'
AUDIT_SCHEMA='endfield.skill-center-fsm-native-audit.v1'
CONTRACT_PATH=CONTRACTS_DIR/'skill_center_fsm_native.json'
AI='Beyond.Gameplay.AI.CharacterMainCtrlSystem+';BB=AI+'CenterBlackboard';STATE=AI+'CenterState';MACHINE=AI+'CenterStateMachine';BASE=AI+'CenterStateBase';SKILL=AI+'CenterSkillState'
METHODS={'base':(BASE,'.ctor'),'machine':(MACHINE,'.ctor'),'enter':(SKILL,'OnEnter'),'fixed':('Beyond.Gameplay.AI.CharacterMainCtrlSystem','OnFixedTick')}

def _rules():return dict(originalPathOnly=True,normalWin64CallsRequired=True,constructorSavedCarrierContinuityRequired=True,castResultIsOriginalSourceOrNull=True,castNullSourceReturnsNull=True,classifierSemanticsProved=False,firstCastResultStoredBeforeSecondCast=True,secondCastResultUnused=True,nullableFirstCastStored=True,nullAiComPreservesOldFields=True,nonNullAiComStorePrecedesEntityRead=True,entityNullValueStored=True,providedCastType=BB,sourceArgumentSharedWithSkillStateConstruction=True,skillStateAllocationTypeRequestProved=True,allocatorReturnedTypeProved=False,addStateRequestUsesSameConstructedToken=True,collectionRegistrationEffectsProved=False,skillStateOnEnterNominalVtableSlotProved=True,compiledGenericHelperIdentityProved=False,fullFSMDispatchProved=False,sameLiveWriterConsumerBlackboardProved=False,completeFieldWriterCensusProved=False,lifetimeProved=False,currentSessionFSMConstructionProved=False)

def _same(a,b):return json.dumps(a,sort_keys=True,allow_nan=False)==json.dumps(b,sort_keys=True,allow_nan=False)

def _validate(image,c):
    cx=NativeReferenceContext(image);validate_reference_ancestor_chain(cx,'Beyond.Gameplay.AI.CharacterAIComponent',['Beyond.Gameplay.AI.AIComponent','Beyond.Gameplay.Core.TickComponent','Beyond.Gameplay.Core.BaseComponent'],'Beyond.Gameplay.Core.BaseComponent');fields=_validate_fields(image,c['fields']);off={k:r['offset']for k,r in fields.items()};expected={'bb':(BASE,'m_blackboard',BB,18),'ai':(BASE,'m_aiCom','Beyond.Gameplay.AI.CharacterAIComponent',18),'entity':(BASE,'m_entity','Beyond.Gameplay.Core.Entity',18),'aiEntity':('Beyond.Gameplay.Core.BaseComponent','<entity>k__BackingField','Beyond.Gameplay.Core.Entity',18)}
    _require(set(fields)==set(expected),'fsm-field-coverage',sorted(expected),sorted(fields));properties={}
    for key,(owner,name,ty,kind)in expected.items():
        r=fields[key];_require((r['type'],r['name'],r['valueType'])==(owner,name,ty)and type(r['ordinaryKind'])is int and r['ordinaryKind']==kind and type(r['offset'])is int,'fsm-field-nominal',expected[key],r)
        td=image.named_types[owner];f=next(f for f in image.metadata.fields_for(td)if image.metadata.string(f.name_index)==name);attrs=cx.field_attributes(f.type_index);properties[key]=dict(attributes=attrs,initOnly=bool(attrs&32),static=bool(attrs&16))
    methods={}
    for r in c['methods']:
        role=r['id'];_require(role in METHODS and role not in methods and r['identity'][1:3]==list(METHODS[role]),'fsm-method-role',METHODS.get(role),r);idx=image.validate_method_row(r['identity'],label='skillCenterFSM');m=image.metadata.methods[idx]
        actual=dict(returnType=cx.type_name(m.return_type),parameters=[dict(name=image.metadata.string(p.name_index),type=cx.type_name(p.type_index))for p in image.metadata.parameters_for(m)],slot=m.slot)
        _require(not m.flags&16 and _same(actual,{k:r[k]for k in actual}),'fsm-method-signature',r,actual);methods[role]=r
    _require(set(methods)==set(METHODS),'fsm-method-coverage',sorted(METHODS),sorted(methods));image.check_windows(c['codeWindows'],label='skillCenterFSM')
    for role,r in methods.items():_require([[w['startRva'],w['endRva']]for w in c['codeWindows']if w['owner']==role]==[x['runtimeTriple'][:2]for x in image.unwind_index.family(r['identity'][3])['ranges']],'fsm-window-owner','complete named family',role)
    helper=c['physicalCast'];_require([[w['startRva'],w['endRva']]for w in c['codeWindows']if w['owner']=='castHelper']==[x['runtimeTriple'][:2]for x in image.unwind_index.family(helper['entryRva'])['ranges']],'fsm-helper-owner','complete selected physical helper',helper)
    spans={r['id']:r for r in c['spans']};raws={}
    for key,r in spans.items():
        raw=bytes.fromhex(r['hex']);cursor=r['rva']
        for a,b in sorted((w['startRva'],w['endRva'])for w in c['codeWindows']if w['owner']==r['owner']):
            if a<=cursor<b:cursor=min(b,r['rva']+len(raw))
        _require(raw and cursor==r['rva']+len(raw)and image.pe.bytes_at_va(image.pe.image_base+r['rva'],len(raw))==raw,'fsm-native-span',key,r);raws[key]=raw
    required={'baseCapture','baseInvoke','baseStore','baseAiGuard','baseAiWrite','castHelper','machineCapture','machineBaseInvoke','skillRegister','fixedVirtualTick','baseReturn'}
    _require(set(spans)==required,'fsm-program-coverage',sorted(required),sorted(spans));op=c['operands'];_require(all(type(v)is int for v in op.values()),'fsm-operands','ordinary integers',op);targets={**op,**{k:r['rva']for k,r in spans.items()},**{k:r['identity'][3]for k,r in methods.items()}}
    h=bytes.fromhex;F=lambda k,w=1:('field',k,w);O=lambda k,w=1:('operand',k,w);R=lambda k,w=4:('relative',k,w)
    def check(key,parts):_require(_match(raws[key],spans[key]['rva'],parts,off,op,targets),'fsm-semantic-program',key,raws[key].hex())
    check('baseCapture',[h('48895c24'),O('saveRbx'),h('48896c24'),O('saveRbp'),h('48897424'),O('saveRsi'),h('574883ec'),O('baseFrame'),h('803d'),O('baseInitFlagDisp',4),h('00498bf1498bf88bea488bd974'),R('baseMetadataInitRva',1)])
    check('baseInvoke',[h('4c8b0d'),R('stateBaseCtorContextCell'),h('4c8bc78bd5488bcbe8'),R('physicalStateBaseCtorRva')])
    check('baseStore',[h('488b15'),R('castTypeCell'),h('488bcfe8'),R('castHelperRva'),h('488943'),F('bb'),h('488bcf488b15'),R('castTypeCell'),h('e8'),R('castHelperRva'),h('488d4b'),F('bb'),h('e8'),R('barrierRva')])
    check('baseAiGuard',[h('4885f60f85'),R('baseAiWrite')])
    check('baseAiWrite',[h('488d4b'),F('ai'),h('488973'),F('ai'),h('e8'),R('barrierRva'),h('4c8b4e'),F('aiEntity'),h('488d4b'),F('entity'),h('4c894b'),F('entity'),h('e8'),R('barrierRva'),h('90e9'),R('baseReturnRva')])
    check('baseReturn',[h('488b5c24'),O('restoreRbx'),h('488b6c24'),O('restoreRbp'),h('488b7424'),O('restoreRsi'),h('4883c4'),O('baseFrame'),h('5fc3')])
    check('castHelper',[h('40534883ec'),O('castFrame'),h('488bd94885c974'),R('castNullReturnRva',1),h('488b09e8'),R('classifierRva'),h('33c984c0480f44d9488bc34883c4'),O('castFrame'),h('5bc333c04883c4'),O('castFrame'),h('5bc3')])
    _require(spans['castHelper']['rva']==helper['entryRva']==op['castHelperRva']and op['castNullReturnRva']==spans['castHelper']['rva']+len(raws['castHelper'])-8,'fsm-cast-null-edge','null branch reaches independent zero return',helper)
    check('machineCapture',[h('48895c24'),O('machineSaveRbx'),h('48896c24'),O('machineSaveRbp'),h('48897424'),O('machineSaveRsi'),h('574883ec'),O('machineFrame'),h('803d'),O('machineInitFlagDisp',4),h('00498bf8488bf2488bd90f85'),R('machineBaseInvoke')])
    check('machineBaseInvoke',[h('4c8b05'),R('machineBaseCtorContextCell'),h('488bd6488bcbe8'),R('physicalMachineBaseCtorRva')])
    check('skillRegister',[h('488b0d'),R('skillAllocationTypeCell'),h('488b6b'),O('machineAiPhysicalOffset'),h('e8'),R('allocatorRva'),h('488bf84885c00f84'),R('machineNullRva'),h('4c8bcd4c897424'),O('machineMethodInfoStack'),h('4c8bc6ba'),O('skillStateId',4),h('488bc8e8'),R('base'),h('4c8b05'),R('addStateContextCell'),h('488bd7488bcbe8'),R('physicalAddStateRva')])
    check('fixedVirtualTick',[h('b9'),O('tickSlot',4),h('0f28d6488bd0e8'),R('virtualTickHelperRva')])
    for left,right in [('baseCapture','baseInvoke'),('baseInvoke','baseStore'),('baseStore','baseAiGuard')]:_require(spans[left]['rva']+len(raws[left])==spans[right]['rva'],'fsm-contiguous-edge',left,right)
    _require(spans['baseCapture']['rva']==methods['base']['identity'][3]and spans['machineCapture']['rva']==methods['machine']['identity'][3]and spans['baseAiGuard']['rva']+len(raws['baseAiGuard'])==spans['baseReturn']['rva']==op['baseReturnRva'],'fsm-entry-return-boundary','captured entry and lazy null-ai return',spans)
    expected_contexts={'cast1':(BB,None,None),'cast2':(BB,None,None),'base':('Beyond.Gameplay.FSMState`1','.ctor',[STATE]),'machine':('Beyond.Gameplay.StateMachine`2','.ctor',[STATE,BB]),'allocation':(SKILL,None,None),'add':('Beyond.Gameplay.StateMachine`2','AddState',[STATE,BB])}
    _require(set(c['typedContexts'])==set(expected_contexts),'fsm-context-coverage',sorted(expected_contexts),sorted(c['typedContexts']))
    sites={'cast1':spans['baseStore']['rva'],'cast2':spans['baseStore']['rva']+22,'base':spans['baseInvoke']['rva'],'machine':spans['machineBaseInvoke']['rva'],'allocation':spans['skillRegister']['rva'],'add':spans['skillRegister']['rva']+52}
    for role,(ty,name,args)in expected_contexts.items():
        row=c['typedContexts'][role];actual=derive_typed_usage_context(image,row['instructionRva'],label='skillCenterFSM')
        _require(row['instructionRva']==sites[role]and _same(actual,row)and actual['typeName']==ty and(name is None or actual.get('methodName')==name and actual.get('classArguments')==args),'fsm-nominal-consumer-context',expected_contexts[role],actual)
    _require(c['typedContexts']['cast1']['usageCellRva']==c['typedContexts']['cast2']['usageCellRva']==op['castTypeCell']and op['skillStateId']==c['skillStateId'],'fsm-shared-cast-context','same BB type on both casts',op)
    onenter=image.metadata.methods[methods['enter']['identity'][0]];_require(onenter.slot==c['onEnterSlot']and type(c['onEnterSlot'])is int,'fsm-onenter-slot','nominal override slot',c['onEnterSlot']);_vtable(image,image.named_types[SKILL].index,c['onEnterSlot'],onenter.index,'skillCenterFSM')
    _require(_same(c['rules'],_rules()),'fsm-rules',_rules(),c['rules']);return _rules(),properties

def load_skill_center_fsm(contract_path=CONTRACT_PATH,*,gameassembly=None,metadata=None):
    path=Path(contract_path);a=dict(schema=AUDIT_SCHEMA,status='validation_failed',rules={},nativeInputs={},rows=[],failures=[])
    try:
        c,digest=read_reviewed_contract(path,schema=SCHEMA,status='reviewed',label='skillCenterFSM');pins=c['nativeInputs'];g=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata);a.update(status=g.status,detail=g.detail)
        if g.status!='validated':return a
        rules,props=_validate(open_native_image(g.gameassembly,g.metadata),c);after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=g.gameassembly,metadata=g.metadata)
        _require(after.status=='validated'and hashlib.sha256(path.read_bytes()).hexdigest().upper()==digest,'fsm-input-bookend','unchanged selected inputs',after.detail)
        a.update(status='validated-conditional-fragments',detail='',nativeInputs=dict(pins),rules=rules,rows=[dict(id='centerStateInitialization',evidence='conditional',rules=rules)],fieldProperties=props,registration=c['registration'],unresolvedDispatch=c['unresolvedDispatch'],boundaries=c['boundaries'])
    except(OSError,ValueError,KeyError,TypeError,IndexError,RuntimeError,struct.error)as e:a.update(status='validation_failed',detail=str(e)[:1200],rules={},nativeInputs={},rows=[],failures=[dict(check=str(e).split(':',1)[0],detail=str(e)[:1200])])
    return a
