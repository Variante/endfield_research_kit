"""Original cast-id assignment and selected Skill/Ability carrier links.

IDs may be supplied/copied and a zero input consumes a wrapping, unsynchronized
counter. No global uniqueness, live object lifetime or cross-tick cause follows.
"""
from __future__ import annotations
import hashlib,json,struct
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
from scripts.game_data.il2cpp import protocol
from scripts.game_data.skill_input_execution_native import _program as _identity_program,_entry_bridge as _identity_entry_bridge
from scripts.game_data.skill_timing_runtime_native import _require,_validate_fields
SCHEMA='endfield.skill-cast-identity-native-contract.v1'
AUDIT_SCHEMA='endfield.skill-cast-identity-native-audit.v1'
CONTRACT_PATH=CONTRACTS_DIR/'skill_cast_identity_native.json'
PREFIX='Beyond.Gameplay.Core.'
METHODS={'assign':('Ability','AssignSkillCastInfo',['Skill+SkillCastInfo']),'skillInit':('Skill','_Init',[]),'refresh':('Skill','_DoRefreshRuntimeData',['bool']),'abilityInit':('Ability','Init',['Skill','ActionGroupData','@Beyond.ActionBlackboard']),'before':('Ability','BeforeCast',['TargetHandleView']),'tryCast':('AbilitySystem','TryCastSkill',['@string','TargetHandleView','@System.Action`2<Beyond.Gameplay.Core.Skill+FinishType,int>','@System.Nullable`1<Beyond.Gameplay.Core.Skill+CastSkillOptions>','@System.Action`1<Beyond.Gameplay.Core.Skill>','@System.Action`1<Beyond.Gameplay.Core.Skill>','Skill+SkillCastInfo','bool']), 'abilityCtor':('Ability','.ctor',[])}

def assignment_effect(*,input_id,input_origin,input_cost_bits,source_skill,counter,counter_for_increment):
    """Pure conditional direct-store model, with all reached values explicit.

The caller supplies normal-return original-path premises and each separate counter read; this is
not a replay of a captured request. Cost is copied as 32 uninterpreted bits.
"""
    _require(type(input_id)is int and 0<=input_id<2**32,'identity-input-id','uint32',input_id)
    if input_id:
        _require(type(input_origin)is int and 0<=input_origin<2**64 and type(input_cost_bits)is int and 0<=input_cost_bits<2**32,'identity-copy-input','reference carrier/uint32 bits',(input_origin,input_cost_bits))
        return dict(skillCastId=input_id,castOriginSkill=input_origin,nonReturnedAtbCostBits=input_cost_bits,counterWriteRequested=False)
    _require(type(counter)is int and 0<=counter<2**32 and type(source_skill)is int and 0<=source_skill<2**64 and type(counter_for_increment)is int and 0<=counter_for_increment<2**32,'identity-zero-input','uint32 counter/source reference',(counter,source_skill))
    return dict(skillCastId=counter,castOriginSkill=source_skill,nonReturnedAtbCostBits=0,counterWriteRequested=True,nextCounter=(counter_for_increment+1)%(2**32))

def _rules():
    return dict(originalPathOnly=True,nonzeroInputIdCopiesIdOriginAndCostBits=True,zeroInputIdReadsCounterThenRequestsWrappingIncrement=True,zeroInputOriginUsesSourceSkill=True,zeroInputCostBits=0,counterBits=32,counterIndependentlyReloadedForIncrement=True,nominalCounterFieldProved=True,writeBarrierPreservesR10OnNormalReturn=True,counterAtomicIncrementProved=False,globalCastIdUniquenessProved=False,abilityPointerOrUidIsCastOccurrence=False,skillAbilityAndSourceSkillConditionalBacklink=False,abilityInitStoresSourceSkill=True,carrierContinuityRequired=['Skill RBX at allocation/store fragment','Skill RBX at fresh-refresh fragment','selected Skill RDI and preserved RBX between TryCast fragments'],freshRefreshPathOnly=True,beforeCastCallerIsSelectedTryCastSkill=True,requestDeliveryProved=False,unobservedCallerAboveTryCastSkillProved=False,objectLifetimeProved=False)

def _equal(a,b):return json.dumps(a,sort_keys=True,allow_nan=False)==json.dumps(b,sort_keys=True,allow_nan=False)

def _validate(image,c):
    cx=NativeReferenceContext(image);fields=_validate_fields(image,c['fields']);off={k:v['offset']for k,v in fields.items()};expected={'ability':('Skill','m_ability','Ability',18),'source':('Ability','<sourceSkill>k__BackingField','Skill',18),'id':('Ability','skillCastId','uint',9),'origin':('Ability','castOriginSkill','Skill',18),'cost':('Ability','nonReturnedAtbCost','float',12),'inputId':('Skill+SkillCastInfo','skillCastId','uint',9),'inputOrigin':('Skill+SkillCastInfo','originSkill','Skill',18),'inputCost':('Skill+SkillCastInfo','nonReturnedAtbCost','float',12)}
    _require(set(fields)==set(expected),'identity-field-coverage',list(expected),list(fields))
    for key,(owner,name,value,kind)in expected.items():
        row=fields[key];_require(row['type']==PREFIX+owner and row['name']==name and row['valueType']==(value if value in('uint','float')else PREFIX+value)and type(row['ordinaryKind'])is int and row['ordinaryKind']==kind and type(row['offset'])is int,'identity-field-nominal',expected[key],row)
    header=c['inputHeaderBytes'];_require(type(header)is int and header>0 and off['inputId']==header and off['inputOrigin']-header==8 and off['inputCost']-header==16,'identity-input-layout','selected uint/reference/float fields',off)
    methods={}
    for row in c['methods']:
        role=row['id'];_require(role in METHODS and role not in methods,'identity-method-role','unique selected role',role);owner,name,params=METHODS[role];index=image.validate_method_row(row['identity'],label='skillCastIdentity');m=image.metadata.methods[index]
        actual=[cx.type_name(p.type_index)for p in image.metadata.parameters_for(m)]
        _require(row['identity'][1:3]==[PREFIX+owner,name] and not m.flags&0x10 and cx.type_name(m.return_type)==('bool'if role=='tryCast'else 'void') and (params is None or actual==[p[1:]if p.startswith('@')else p if p=='bool'else PREFIX+p for p in params]),'identity-method-nominal',(owner,name,params),row)
        methods[role]=row
    _require(set(methods)==set(METHODS),'identity-method-coverage',list(METHODS),list(methods));image.check_windows(c['codeWindows'],label='skillCastIdentity')
    for role in methods:
        bounds=[r['runtimeTriple'][:2]for r in image.unwind_index.family(methods[role]['identity'][3])['ranges']]
        _require([[w['startRva'],w['endRva']]for w in c['codeWindows']if w['owner']==role]==bounds,'identity-window-owner','complete selected family',role)
    spans={r['id']:r for r in c['spans']};required={'assignCapture','assignGuard','zero','copy','zeroInit','skillAbilityStore','refreshReceiver','abilitySourceStore','beforeReceiver','abilityCapture','barrier','assignReceiver'}
    _require(set(spans)==required,'identity-span-coverage',sorted(required),sorted(spans));raws={}
    for key,row in spans.items():
        raw=bytes.fromhex(row['hex']);rva=row['rva'];bounds=sorted((w['startRva'],w['endRva'])for w in c['codeWindows']if w['owner']==row['owner']);cursor=rva
        for a,b in bounds:
            if a<=cursor<b:cursor=min(b,rva+len(raw))
        _require(raw and cursor==rva+len(raw)and image.pe.bytes_at_va(image.pe.image_base+rva,len(raw))==raw,'identity-native-span',key,row);raws[key]=raw
    op=c['operands'];_require(all(type(v)is int for v in op.values()),'identity-operand-types','ordinary integers',op)
    def template(key,parts):
        row=spans[key];raw=raws[key];cursor=0
        for part in parts:
            if isinstance(part,bytes):wanted=part
            else:
                kind,name,width=part;value=(off[name]-header if kind=='input'else off[name])if kind in('field','input')else op[name]if kind=='operand'else None
                if kind in('field','input','operand'):wanted=value.to_bytes(width,'little',signed=True)
                elif kind in('branch','call'):
                    target=spans[name]['rva']if kind=='branch'else methods[name]['identity'][3]if name in methods else op[name];wanted=struct.pack('<i',target-(row['rva']+cursor+width))
                elif kind in('rip','rip1'):wanted=struct.pack('<i',op[name]-(row['rva']+cursor+width+(1 if kind=='rip1'else 0)))
                else:raise ValueError('identity unknown template operand')
            _require(raw[cursor:cursor+len(wanted)]==wanted,'identity-semantic-instruction',key,raw.hex());cursor+=len(wanted)
        _require(cursor==len(raw),'identity-program-extent',key,len(raw))
    h=bytes.fromhex;F=lambda n,w=1:('field',n,w);I=lambda n,w=1:('input',n,w);O=lambda n,w=1:('operand',n,w);B=lambda n:('branch',n,4);C=lambda n:('call',n,4);R=lambda n:('rip',n,4)
    entry=methods['assign']['identity'][3];prefix=image.pe.bytes_at_va(image.pe.image_base+entry,spans['assignCapture']['rva']-entry)
    _require(len(prefix)==13 and prefix[:5]==h('40534883ec') and prefix[5]==op['assignFrameBytes'] and prefix[6:9]==h('488b05'),'identity-assign-entry-carriers','entry RCX/RDX unchanged by stack/RAX-only prologue',prefix.hex())
    template('assignCapture',[h('488bd94c8bd2488b48'),O('dispatchOffset'),h('4885c90f85'),('call','assignReplacementRva',4)])
    template('assignGuard',[h('833a0075'),O('nonzeroBranchDisp')])
    _require(spans['assignGuard']['rva']+5+op['nonzeroBranchDisp']==spans['copy']['rva']and spans['assignCapture']['rva']+len(raws['assignCapture'])==spans['assignGuard']['rva'],'identity-nonzero-edge','contiguous original uint !=0 branch',spans)
    template('zero',[h('488b05'),R('counterInfoCellRva'),h('83b8'),O('classInitFlagOffset',4),h('0074'),O('classInitBranchDisp'),h('488b80'),O('staticFieldsOffset',4),h('8b08'+'894b'),F('id'),h('488b15'),R('counterInfoCellRva'),h('488b82'),O('staticFieldsOffset',4),h('8b08ffc18908488d4b'),F('origin'),h('488b43'),F('source'),h('488943'),F('origin'),h('e8'),C('writeBarrierRva'),h('c743'),F('cost'),h('000000004883c4'),O('assignFrameBytes'),h('5bc3')])
    _require(spans['assignGuard']['rva']+len(raws['assignGuard'])==spans['zero']['rva']and spans['zero']['rva']+16+op['classInitBranchDisp']==spans['zeroInit']['rva'],'identity-zero-edges','false input branch and class-init edge',spans)
    template('copy',[h('8b02488d4b'),F('origin'),h('8943'),F('id'),h('488b42'),I('inputOrigin'),h('488943'),F('origin'),h('e8'),C('writeBarrierRva'),h('458b4a'),I('inputCost'),h('44894b'),F('cost'),h('4883c4'),O('assignFrameBytes'),h('5bc3')])
    template('zeroInit',[h('488bc8e8'),C('classInitRva'),h('488b05'),R('counterInfoCellRva'),h('eb'),O('classInitReturnDisp')])
    _require(spans['zeroInit']['rva']+len(raws['zeroInit'])+op['classInitReturnDisp']==spans['zero']['rva']+16,'identity-classinit-return','return to same static counter load',spans)
    template('skillAbilityStore',[h('488bf84885c00f84'),('call','skillNullThrowRva',4),h('33d2488bc8e8'),C('abilityCtor'),h('488d4b'),F('ability'),h('48897b'),F('ability'),h('e8'),C('writeBarrierRva')])
    template('refreshReceiver',[h('488b43'),O('skillDataOffset'),h('488b4b'),F('ability'),h('4885c00f84'),('call','refreshNullThrowRva',4),h('4885c90f84'),('call','refreshNullThrowRva',4),h('4c8b8b'),O('skillBlackboardOffset',4),h('488bd34c8b80'),O('actionGroupOffset',4),h('48c74424'),O('methodInfoStackOffset'),h('00000000e8'),C('abilityInit')])
    template('abilitySourceStore',[h('488d4b'),F('source'),h('48897c24'),O('abilityInitSpillOffset'),h('4c8953'),F('source'),h('e8'),C('writeBarrierRva')])
    template('assignReceiver',[h('488b4f'),F('ability'),h('4885c90f84'),('call','tryCastEarlyNullThrowRva',4),h('488b55'),O('skillCastInfoStackDisp'),h('4533c0e8'),C('assign')])
    template('beforeReceiver',[h('4885db0f84'),('call','tryCastNullThrowRva',4),h('4533c0488bd0488bcbe8'),C('before')])
    # The selected receiver was loaded from RDI Skill.m_ability; the intervening
    # reviewed target-handle branch preserves RBX (no assignment to it).
    load=c['beforeAbilityLoad'];raw=bytes.fromhex(load['hex']);_require(raw==h('488b5f')+off['ability'].to_bytes(1,'little')and image.pe.bytes_at_va(image.pe.image_base+load['rva'],len(raw))==raw and any(w['owner']=='tryCast'and w['startRva']<=load['rva']<load['rva']+len(raw)<=w['endRva']for w in c['codeWindows'])and load['rva']<spans['beforeReceiver']['rva'],'identity-before-receiver-load','RBX=selected RDI Skill.ability',load)
    # Actual helper body is a closed leaf: both exits converge on RET; its
    # retry loop changes only RAX/RCX/RDX/R8. Thus R10 survives the cost load.
    template('barrier',[h('833d'),('rip1','barrierFlagRva',4),h('004c8bc174'),O('barrierExitDisp'),h('49c1e8'),O('barrierPageShift'),h('488d0d'),R('barrierTableRva'),h('4181e0'),O('barrierMask',4),h('418bc048c1e8'),O('barrierWordShift'),h('4183e0'),O('barrierBitMask'),h('488d14c10f0d0a488b02488bc84c0fabc1f0480fb10a75'),O('barrierRetryDisp'),h('c3')])
    _require(spans['barrier']['rva']==op['writeBarrierRva'] and spans['barrier']['rva']+12+op['barrierExitDisp']==spans['barrier']['rva']+len(raws['barrier'])-1 and spans['barrier']['rva']+len(raws['barrier'])-1+op['barrierRetryDisp']==op['barrierLoopRva'],'identity-barrier-control','closed retry/ret paths; no R10 assignment',op)
    capture=spans['abilityCapture'];prefix=image.pe.bytes_at_va(image.pe.image_base+methods['abilityInit']['identity'][3],capture['rva']-methods['abilityInit']['identity'][3]);operands=dict(dispatchTableOffset=op['dispatchOffset'],savedRdiStackOffset=op['abilityInitSpillOffset'])
    _require(_identity_entry_bridge('init',prefix,operands) and _identity_program('init',raws['abilityCapture'],dict(sourceSkill=off['source']),operands) and capture['rva']+len(raws['abilityCapture'])==spans['abilitySourceStore']['rva']+len(raws['abilitySourceStore'])-5,'identity-ability-init-carriers','RCX/RDX preserved to sourceSkill store',capture)
    for role,expected_name in [('counter',PREFIX+'Ability'),('allocation',PREFIX+'Ability')]:
        row=c['typedContexts'][role];actual=derive_typed_usage_context(image,row['instructionRva'],label='skillCastIdentity')
        _require(_equal(actual,row)and actual['typeName']==expected_name,'identity-typed-context',expected_name,actual)
    _require(c['typedContexts']['counter']['usageCellRva']==op['counterInfoCellRva'],'identity-counter-context','Ability class context feeds static-table loads',op)
    static=c['counterField'];td=image.named_types[PREFIX+'Ability'];decl=[f for f in image.metadata.fields_for(td)if image.metadata.string(f.name_index)=='s_skillCastId']
    _require(len(decl)==1 and static['name']=='s_skillCastId'and static['type']==PREFIX+'Ability'and static['valueType']=='uint'and type(static['offset'])is int and static['offset']==0,'identity-static-field-declaration','selected nonliteral UInt32 counter',static)
    f=decl[0];attrs=cx.field_attributes(f.type_index);cx.require_ordinary_kind(f.type_index,9)
    _require(attrs&0x10 and not attrs&0x40 and cx.type_name(f.type_index)=='uint'and protocol.runtime_type_field_offsets(image.metadata,image.pe,image.registration,td.index).get('s_skillCastId')==static['offset'],'identity-static-field','actual nonliteral static UInt32 offset0',attrs)
    bindings=c['callerBindings'];_require({b['role']for b in bindings}=={'abilityInit','beforeCast','assignCastInfo'}and len(bindings)==3,'identity-caller-coverage','selected three callers',bindings)
    for binding in bindings:
        expected={'abilityInit':('refresh','abilityInit','refreshReceiver'),'beforeCast':('tryCast','before','beforeReceiver'),'assignCastInfo':('tryCast','assign','assignReceiver')}[binding['role']]
        _require((binding['ownerRole'],binding['targetRole'])==expected[:2]and binding['callSiteRva']==spans[expected[2]]['rva']+len(raws[expected[2]])-5,'identity-caller-role','nominal role and consumed forwarding span',binding)
        site=binding['callSiteRva'];owner=binding['ownerRole'];target=binding['targetRole'];raw=image.pe.bytes_at_va(image.pe.image_base+site,5)
        _require(binding['returnRva']==site+5 and raw[:1]==b'\xe8' and site+5+struct.unpack_from('<i',raw,1)[0]==methods[target]['identity'][3]and any(w['owner']==owner and w['startRva']<=site<site+5<=w['endRva']for w in c['codeWindows']),'identity-caller-binding','actual E8 in selected owner family',binding)
    _require(_equal(c['rules'],_rules()),'identity-rules',_rules(),c['rules']);return _rules()

def load_skill_cast_identity(contract_path=CONTRACT_PATH,*,gameassembly=None,metadata=None):
    p=Path(contract_path);a=dict(schema=AUDIT_SCHEMA,status='validation_failed',rows=[],rules={},nativeInputs={},callerBindings=[],failures=[])
    try:
        c,digest=read_reviewed_contract(p,schema=SCHEMA,status='reviewed',label='skillCastIdentity');pins=c['nativeInputs'];g=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata);a.update(status=g.status,detail=g.detail)
        if g.status!='validated':return a
        rules=_validate(open_native_image(g.gameassembly,g.metadata),c);after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=g.gameassembly,metadata=g.metadata)
        _require(after.status=='validated'and hashlib.sha256(p.read_bytes()).hexdigest().upper()==digest,'identity-bookend','unchanged selected inputs',after.detail);a.update(status='validated-conditional-fragments',detail='',callerBindings=[dict(role=b['role'],returnRva=b['returnRva'],callSiteRva=b['callSiteRva'],owner=next(m['identity']for m in c['methods']if m['id']==b['ownerRole']),target=next(m['identity']for m in c['methods']if m['id']==b['targetRole']))for b in c['callerBindings']],rows=[dict(id='originalCastIdentityStores',evidence='conditional',rules=rules)],rules=rules,nativeInputs=dict(pins),evidenceBoundary=c['evidenceBoundary'])
    except(OSError,ValueError,KeyError,TypeError,IndexError,RuntimeError,struct.error)as e:a.update(status='validation_failed',detail=str(e)[:1200],rows=[],rules={},nativeInputs={},callerBindings=[],failures=[dict(check=str(e).split(':',1)[0],detail=str(e)[:1200])])
    return a

