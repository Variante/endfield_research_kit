"""Selected pending-request storage/read fragments, composed with maintained consumers.

A request record carries an id and other input fields, including a nested origin
Skill reference. It does not retain the precheck's selected execution Skill.
Collection/object-pool effects, all writers, lifetime and live delivery stay open.
"""
from __future__ import annotations
import hashlib,json,struct
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
from scripts.game_data.skill_timing_runtime_native import _require,_validate_fields
from scripts.game_data import skill_pending_cast_native as pending
from scripts.game_data import skill_player_command_native as player
from scripts.game_data.memorypack.pooled_source_helper import check_unity_input
SCHEMA='endfield.skill-pending-storage-native-contract.v1'
AUDIT_SCHEMA='endfield.skill-pending-storage-native-audit.v1'
CONTRACT_PATH=CONTRACTS_DIR/'skill_pending_storage_native.json'
AI='Beyond.Gameplay.AI.';CORE='Beyond.Gameplay.Core.'
DEPS={'pending':('skill_pending_cast_native.json',pending.SCHEMA),'player':('skill_player_command_native.json',player.SCHEMA)}
METHODS={'cast':(AI+'CharacterSkillSystem','CastComboSkill'),'get':(AI+'CharacterSkillSystem','GetComboSkillData'),'clear':(AI+'CharacterSkillSystem+SkillData','ClearAll'),'dispose':(CORE+'SkillCastInputData','Dispose'),'release':(AI+'CharacterSkillSystem','OnRelease'),'exit':(AI+'CharacterSkillSystem','OnExitSystem'),'getList':(AI+'CharacterSkillSystem','get_pendingComboSkills'),'plunge':(AI+'CharacterSkillSystem','CastPlungingAttack')}

def _rules():return dict(originalPathOnly=True,coherentCollectionRequired=True,localCarrierPremises=['CastComboSkill RSI is selected system and RDI is entity','GetComboSkillData RDI is selected system and RSI is entity','ClearAll RBX is selected request record'],inputDataPayloadBytes=88,recordDirectSkillFieldPresent=False,nestedOriginSkillReferencePresent=True,writeSelection='forward-first-resolved-entity-match',readSelection='reverse-last-resolved-entity-match',selectionFiltersCasting=False,selectionFiltersCastType=False,reachedNullEntryNormalMissProved=False,nullListNormalMissProved=False,exceptionalNullExitRequired=True,writerRefetchNullRequestsPool=True,readRefetchNullReturnsNull=True,readMissReturnsNull=True,selectedIndexRefetched=True,collectionEffectsProved=False,poolEffectsProved=False,completeWriterSetProved=False,mutablePendingListReferenceExposed=True,disposeDirectlyClearsTargetOnly=True,disposeOtherDirectStoresProvedAbsent=True,disposeIndirectSideEffectsProved=False,clearAllRequestsWholeInputZero=True,zeroHelperEffectsProved=False,behaviorStoresRequestRecordReference=True,consumerPrechecksByCurrentRecordSkillId=True,consumerCallsTryCastByReloadedRecordSkillId=True,precheckSkillPointerPassedToTryCast=False,recordReloadedAfterTryCast=True,stableRecordIdentityRequired=True,upstreamSkillInstanceContinuityProved=False,currentSessionPendingExecutionProved=False)

def _equal(a,b):return json.dumps(a,sort_keys=True,allow_nan=False)==json.dumps(b,sort_keys=True,allow_nan=False)

def _match(raw,rva,parts,fields,operands,targets):
    cursor=0
    for part in parts:
        if isinstance(part,bytes):want=part
        else:
            kind,key,width=part
            if kind=='field':value=fields[key]
            elif kind=='operand':value=operands[key]
            elif kind=='relative':value=targets[key]-(rva+cursor+width)
            else:raise ValueError('pending-storage unknown grammar operand')
            _require(type(value)is int,'storage-operand-type','ordinary integer',part);want=value.to_bytes(width,'little',signed=True)
        if raw[cursor:cursor+len(want)]!=want:return False
        cursor+=len(want)
    return cursor==len(raw)

def _validate(image,c,dependencies):
    cx=NativeReferenceContext(image);dep_pending=pending._validate(image,dependencies['pending']);dep_player=player._validate(image,dependencies['player'])
    _require(dep_player['status']=='validated'and dep_pending['recordReloadedAfterTryCast']is True,'storage-dependency-validation','maintained selected consumer proofs',(dep_pending,dep_player.get('status')))
    # Enumerate all declared instance fields of record, bases and stored value
    # carriers. A nested originSkill is retained explicitly, not erased by a
    # misleading claim that the whole record contains no Skill references.
    sets={}
    for row in c['completeFieldSets']:
        name=row['type'];td=image.named_types['System.Object'if name=='object'else name];actual=[]
        for f in image.metadata.fields_for(td):
            attrs=cx.field_attributes(f.type_index)
            if attrs&16:continue
            cx.require_ordinary_kind(f.type_index,image.pe.bytes_at_va(cx.type_pointer(f.type_index),16)[10])
            actual.append(dict(name=image.metadata.string(f.name_index),valueType=cx.type_name(f.type_index),ordinaryKind=image.pe.bytes_at_va(cx.type_pointer(f.type_index),16)[10]))
        _require(cx.parent(name)==row['parent']and _equal(actual,row['fields']),'storage-complete-field-set',row,actual);sets[name]=row
    required={AI+'CharacterSkillSystem+SkillData','Beyond.Gameplay.AIClassPool','object',CORE+'SkillCastInputData',CORE+'Skill+SkillCastInfo'}
    _require(set(sets)==required and sets[AI+'CharacterSkillSystem+SkillData']['parent']=='Beyond.Gameplay.AIClassPool'and sets['Beyond.Gameplay.AIClassPool']['parent']=='object','storage-record-ancestry',sorted(required),sorted(sets))
    _require([r['name']for r in sets[AI+'CharacterSkillSystem+SkillData']['fields']]==['castType','entity','inputData','casting']and not any(r['valueType']==CORE+'Skill'for name in(AI+'CharacterSkillSystem+SkillData','Beyond.Gameplay.AIClassPool','object')for r in sets[name]['fields'])and any(r['name']=='originSkill'and r['valueType']==CORE+'Skill'for r in sets[CORE+'Skill+SkillCastInfo']['fields']),'storage-direct-versus-nested-skill','no direct Skill; nested originSkill present',sets)
    fields=_validate_fields(image,c['fields']);off={k:r['offset']for k,r in fields.items()};methods={}
    expected={'list':(AI+'CharacterSkillSystem','m_pendingComboSkills','System.Collections.Generic.List`1<'+AI+'CharacterSkillSystem+SkillData>',21),'castType':(AI+'CharacterSkillSystem+SkillData','castType',AI+'CharacterSkillSystem+SkillData+CastType',17),'entity':(AI+'CharacterSkillSystem+SkillData','entity','Beyond.ObjectPtr`1<'+CORE+'Entity>',21),'input':(AI+'CharacterSkillSystem+SkillData','inputData',CORE+'SkillCastInputData',17),'casting':(AI+'CharacterSkillSystem+SkillData','casting','bool',2),'target':(CORE+'SkillCastInputData','targetHandle',CORE+'TargetHandle',18)}
    _require(set(fields)==set(expected),'storage-field-coverage',sorted(expected),sorted(fields))
    for key,(owner,name,ty,kind)in expected.items():
        row=fields[key];_require((row['type'],row['name'],row['valueType'])==(owner,name,ty)and type(row['ordinaryKind'])is int and row['ordinaryKind']==kind and type(row['offset'])is int,'storage-field-nominal',expected[key],row)
    for row in c['methods']:
        role=row['id'];_require(role in METHODS and role not in methods and row['identity'][1:3]==list(METHODS[role]),'storage-method-role',METHODS.get(role),row)
        index=image.validate_method_row(row['identity'],label='skillPendingStorage');m=image.metadata.methods[index]
        actual=dict(returnType=cx.type_name(m.return_type),parameters=[dict(name=image.metadata.string(p.name_index),type=cx.type_name(p.type_index))for p in image.metadata.parameters_for(m)])
        _require(not m.flags&16 and _equal(actual,{k:row[k]for k in actual}),'storage-method-signature',row,actual);methods[role]=row
    _require(set(methods)==set(METHODS),'storage-method-coverage',list(METHODS),list(methods));image.check_windows(c['codeWindows'],label='skillPendingStorage')
    for role in methods:
        entry=methods[role]['identity'][3]
        actual=[r['runtimeTriple'][:2]for r in image.unwind_index.family(entry)['ranges']]
        _require(actual==[[w['startRva'],w['endRva']]for w in c['codeWindows']if w['owner']==role],'storage-window-owner','complete selected family',role)
    spans={s['id']:s for s in c['spans']};raws={}
    for key,row in spans.items():
        raw=bytes.fromhex(row['hex']);cursor=row['rva']
        for a,b in sorted((w['startRva'],w['endRva'])for w in c['codeWindows']if w['owner']==row['owner']):
            if a<=cursor<b:cursor=min(b,row['rva']+len(raw))
        _require(raw and cursor==row['rva']+len(raw)and image.pe.bytes_at_va(image.pe.image_base+row['rva'],len(raw))==raw,'storage-native-span',key,row);raws[key]=raw
    op=c['operands'];_require(all(type(v)is int for v in op.values()),'storage-operands','ordinary integers',op);targets={**{k:v['identity'][3]for k,v in methods.items()},**{k:v['rva']for k,v in spans.items()},**op}
    _require(set(spans)=={'writeStart','writeIteration','writeCompare','writeRefetch','readStart','readIteration','readCompare','readStep','readRefetch','disposeBody','disposeClear','clearAll','getList','getListCapture','disposePrefix'},'storage-span-coverage','finite selected programs',sorted(spans))
    h=bytes.fromhex;F=lambda n,w=1:('field',n,w);O=lambda n,w=1:('operand',n,w);R=lambda n,w=4:('relative',n,w)
    def check(key,parts):_require(_match(raws[key],spans[key]['rva'],parts,off,op,targets),'storage-semantic-program',key,raws[key].hex())
    check('writeStart',[h('488b46'),F('list'),h('33db4885c00f84'),R('writeNullRva'),h('448b70'),O('listCountOffset'),h('4585f67e'),R('writeNewRva',1)])
    check('writeIteration',[h('488b4e'),F('list'),h('4885c90f84'),R('writeNullRva'),h('4c8b05'),R('listItemContextCell'),h('8bd3e8'),R('listGetRva'),h('4885c00f84'),R('writeNullRva')])
    check('writeRefetch',[h('488b4e'),F('list'),h('4885c90f84'),R('writeNullRva'),h('4c8b05'),R('listItemContextCell'),h('8bd3e8'),R('listGetRva'),h('488bd84885c075'),R('writeStoreRva',1)])
    check('readStart',[h('488b5f'),F('list'),h('4885db74'),R('readNullRva',1),h('8b5b'),O('listCountOffset'),h('eb'),R('readStep',1)])
    check('readIteration',[h('488b4f'),F('list'),h('4885c974'),R('readNullRva',1),h('4c8b05'),R('listItemContextCell'),h('8bd3e8'),R('listGetRva'),h('4885c074'),R('readNullRva',1)])
    check('readRefetch',[h('488b4f'),F('list'),h('4885c974'),R('readNullRva',1),h('4c8b05'),R('listItemContextCell'),h('8bd3e8'),R('listGetRva'),h('eb'),R('readReturnRva',1)])
    check('disposePrefix',[h('40534883ec'),O('disposeFrameBytes'),h('488b05'),R('disposeTypeInfoCell'),h('488bd9488b48'),O('dispatchOffset'),h('4885c90f85'),R('disposeReplacementRva')])
    _require(spans['disposePrefix']['rva']==methods['dispose']['identity'][3]and spans['disposePrefix']['rva']+len(raws['disposePrefix'])==spans['disposeBody']['rva'],'storage-dispose-entry','RCX this to RBX before original body',spans['disposePrefix'])
    check('disposeBody',[h('488b4b'),O('inputTargetPayloadOffset'),h('4885c975'),R('disposeReleaseRva',1),h('488d4b'),O('inputTargetPayloadOffset'),h('48c743'),O('inputTargetPayloadOffset'),h('000000004883c4'),O('disposeFrameBytes'),h('5be9'),R('writeBarrierRva'),h('4883c4'),O('disposeFrameBytes'),h('5bc333d2e8'),R('targetReleaseRva'),h('eb'),R('disposeClear',1)])
    check('writeCompare',[h('488b15'),R('objectPtrContextCell'),h('488d48'),F('entity'),h('e8'),R('objectPtrResolveRva'),h('483bc774'),R('writeRefetch',1),h('ffc3413bde7c'),R('writeLoopRva',1),h('eb'),R('writeNewRva',1)])
    check('readCompare',[h('488b15'),R('objectPtrContextCell'),h('488d48'),F('entity'),h('e8'),R('objectPtrResolveRva'),h('483bc674'),R('readRefetch',1)])
    check('readStep',[h('83eb0179'),R('readLoopRva',1),h('33c0eb'),R('readReturnRva',1)])
    check('disposeClear',[h('488d4b'),O('inputTargetPayloadOffset'),h('48c743'),O('inputTargetPayloadOffset'),h('000000004883c4'),O('disposeFrameBytes'),h('5be9'),R('writeBarrierRva')])
    check('clearAll',[h('33d2c743'),F('castType'),h('00000000488d4c24'),O('clearEntityTemp'),h('e8'),R('objectPtrFromEntityRva'),h('488d4b'),F('entity'),h('0f1000f30f7f43'),F('entity'),h('e8'),R('writeBarrierRva'),h('488d4b'),F('input'),h('33d2e8'),R('dispose'),h('33d2488d4b'),F('input'),h('448d42'),O('inputBytes'),h('e8'),R('zeroInputRva'),h('c683'),F('casting',4),h('00')])
    check('getList',[h('498b41'),F('list'),h('4883c4'),O('getListFrame'),h('c3')])
    check('getListCapture',[h('4883ec'),O('getListFrame'),h('488b05'),R('getListTypeInfoCell'),h('4c8bc9488b48'),O('getListDispatchOffset'),h('4885c974'),R('getList',1)])
    _require(spans['getListCapture']['rva']==methods['getList']['identity'][3],'storage-list-getter-entry','entry RCX captured to R9 before original field load',spans['getListCapture'])
    for left,right in [('writeStart','writeIteration'),('writeIteration','writeCompare'),('writeCompare','writeRefetch'),('readStart','readIteration'),('readIteration','readCompare'),('readCompare','readStep'),('readStep','readRefetch')]:
        _require(spans[left]['rva']+len(raws[left])==spans[right]['rva'],'storage-contiguous-selection',left,right)
    _require(op['writeLoopRva']==spans['writeIteration']['rva']and op['readLoopRva']==spans['readIteration']['rva']and spans['writeRefetch']['rva']+len(raws['writeRefetch'])==op['writeNewRva']and spans['readRefetch']['rva']+len(raws['readRefetch'])==op['readNullRva'],'storage-loop-edges','selected loops/refetch fallback edges',op)
    _require(any(r['name']=='skillCastInfo'and r['valueType']==CORE+'Skill+SkillCastInfo'for r in sets[CORE+'SkillCastInputData']['fields']),'storage-nested-origin-chain','record.inputData.skillCastInfo.originSkill',sets[CORE+'SkillCastInputData'])
    expected_contexts={(spans[role]['rva']+delta,spans[role]['rva']+delta+9)for role,delta in [('writeIteration',13),('writeRefetch',13),('readIteration',9),('readRefetch',9)]}
    _require(len(c['typedContexts'])==4 and {(r['rva'],r['callSiteRva'])for r in c['typedContexts']}==expected_contexts,'storage-context-coverage','four actual get_Item consumer sites',c['typedContexts'])
    for role,key in [('cast','writeNullRva'),('get','readNullRva')]:
        rva=op[key];raw=image.pe.bytes_at_va(image.pe.image_base+rva,6)
        _require(raw[:1]==b'\xe8'and raw[5:]==b'\xcc'and rva+5+struct.unpack_from('<i',raw,1)[0]==op['nullExitHelperRva']and any(w['owner']==role and w['startRva']<=rva<rva+6<=w['endRva']for w in c['codeWindows']),'storage-exceptional-null-exit','selected helper call followed by INT3; helper semantic name not promoted',(role,raw.hex()))
    # Bind the two List.get_Item calls to their actual typed method contexts;
    # ObjectPtr resolution itself remains an explicit normal helper outcome.
    for row in c['typedContexts']:
        actual=derive_typed_usage_context(image,row['rva'],label='skillPendingStorage')
        _require(_equal(actual,row['result'])and actual.get('typeName')=='System.Collections.Generic.List`1'and actual.get('classArguments')==[AI+'CharacterSkillSystem+SkillData']and actual.get('methodName')=='get_Item','storage-list-context',row,actual)
        raw=image.pe.bytes_at_va(image.pe.image_base+row['rva'],row['callSiteRva']+5-row['rva']);_require(raw[:3]==h('4c8b05')and raw[7:9]==h('8bd3')and raw[9:10]==b'\xe8'and row['rva']+14==row['callSiteRva']+5 and row['callSiteRva']+5+struct.unpack_from('<i',raw,10)[0]==op['listGetRva'],'storage-context-consumer','R8 context + EDX index reaches actual call',row)
    _require(op['inputBytes']==c['inputDataPayloadBytes']==88 and off['target']-c['boxedHeaderBytes']==op['inputTargetPayloadOffset'],'storage-payload-width','selected 88-byte input and target slot',op)
    size=c['inputSize'];td=image.named_types[CORE+'SkillCastInputData'];addr=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+td.index*8);actual=image.pe.bytes_at_va(addr,16)
    _require(actual.hex()==size['hex']and int.from_bytes(actual[:4],'little')-c['boxedHeaderBytes']==op['inputBytes'],'storage-input-size','concrete boxed-size witness',size)
    _require([r['role']for r in c['writerInventory']]==['cast','plunge','clear','release','exit'],'storage-writer-inventory','bounded selected candidates',c['writerInventory'])
    _require(_equal(c['rules'],_rules()),'storage-rules',_rules(),c['rules']);return _rules()

def load_skill_pending_storage(contract_path=CONTRACT_PATH,*,gameassembly=None,metadata=None):
    path=Path(contract_path);audit=dict(schema=AUDIT_SCHEMA,status='validation_failed',nativeInputs={},rows=[],rules={},sourceContracts=[],dependencyNativeInputs={},failures=[])
    try:
        c,digest=read_reviewed_contract(path,schema=SCHEMA,status='reviewed',label='skillPendingStorage');pins=c['nativeInputs'];gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata);audit.update(status=gate.status,detail=gate.detail)
        if gate.status!='validated':return audit
        dependencies={};bookends={path:digest}
        _require(c['dependencies']=={k:v[0]for k,v in DEPS.items()},'storage-dependency-declarations','selected maintained contracts',c['dependencies'])
        for role,(filename,schema)in DEPS.items():
            source=CONTRACTS_DIR/filename;dep,sha=read_reviewed_contract(source,schema=schema,status='reviewed',label='skillPendingStorage');_require(all(dep['nativeInputs'][name].upper()==value.upper()for name,value in pins.items()),'storage-dependency-inputs','same selected native inputs',source);dependencies[role]=dep;bookends[source]=sha
        if failure:=check_unity_input(gate.gameassembly,dependencies['player']['nativeInputs']):audit.update(status=failure.get('status','validation_failed'),detail='storage-unity-input:'+str(failure));return audit
        rules=_validate(open_native_image(gate.gameassembly,gate.metadata),c,dependencies)
        after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata);_require(after.status=='validated','storage-native-after','unchanged',after.detail)
        if failure:=check_unity_input(gate.gameassembly,dependencies['player']['nativeInputs']):audit.update(status=failure.get('status','validation_failed'),detail='storage-unity-after:'+str(failure));return audit
        _require(all(hashlib.sha256(p.read_bytes()).hexdigest().upper()==sha for p,sha in bookends.items()),'storage-source-bookend','all selected contracts unchanged','changed')
        audit.update(status='validated-conditional-fragments',detail='',nativeInputs=dict(pins),rules=rules,rows=[dict(id='pendingStorage',evidence='conditional',rules=rules)],sourceContracts=[dict(path=str(p),sha256=sha)for p,sha in bookends.items()],dependencyNativeInputs={role:dep['nativeInputs']for role,dep in dependencies.items()},writerInventory=[dict(**row,method=next(m['identity']for m in c['methods']if m['id']==row['role']))for row in c['writerInventory']],boundaries=c['boundaries'])
    except(OSError,ValueError,KeyError,TypeError,IndexError,RuntimeError,struct.error)as e:audit.update(status='validation_failed',detail=str(e)[:1200],nativeInputs={},rows=[],rules={},failures=[dict(check=str(e).split(':',1)[0],detail=str(e)[:1200])])
    return audit
