"""Prove a bounded second-name and view-target carrier into CanCastSkill."""
from __future__ import annotations
import argparse,hashlib,json,struct
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.blackboard_vector_transfers import decode_blackboard_vectors
from scripts.game_data.skill_timing_runtime_native import _require,_validate_fields
from scripts.game_data.skill_ai_dispatch_native import _strict

CONTRACT_PATH=CONTRACTS_DIR/'skill_request_transfer_native.json'
SCHEMA='endfield.skill-request-transfer-native-contract.v1'
CORE='Beyond.Gameplay.Core.'


def _rules():
    return dict(originalPathOnly=True,lookupOutputUse='typed-skillType-guard',secondSkillIdReadRequired=True,
        admissionSkillArgument='second-name-in-RBX',admissionUsesLookupSkillPointer=False,
        separatelyReturnedViewRequired=True,lookupSlotOverwrittenByViewEndWord=True,
        interFragmentCarrierContinuityRequired=True,viewCopySourceContinuityRequired=False,
        opaqueProvidersNormalReturnRequired=True,viewTargetArgumentBindingProved=True,
        blackboardDestinationOwnershipProved=False,pendingDeliveryProved=False,actualCastProved=False,
        nameCarrierContinuityProved=True,normalWin64CalleeSavedRegistersRequired=True,
        coherentLocalStackRequired=True,firstLookupOutputForwardedToAdmission=False)


def _declarations(image,c):
    ctx=NativeReferenceContext(image);md=image.metadata
    nominal={'owner':('Beyond.Gameplay.AI.CharacterMainCtrlSystem+CenterStateMachine','_ToSkill'),
        'getter':(CORE+'AbilitySystem+ComboController','get_nextSkillId'),
        'wrapper':(CORE+'AbilitySystem','GetNextSkillId'),'view':(CORE+'AbilitySystem','GetNextSkillCastInputView'),
        'canCast':(CORE+'AbilitySystem','CanCastSkill'),'interrupt':(CORE+'AbilitySystem','CheckCanInterruptCurSkill')}
    _require(set(c['methods'])==set(nominal),'transfer-method-coverage',nominal,c['methods'])
    for role,row in c['methods'].items():
        _require(tuple(row['identity'][1:3])==nominal[role],'transfer-nominal-role',nominal[role],row)
        m=md.methods[image.validate_method_row(row['identity'],label='skillRequestTransfer')];params=list(md.parameters_for(m))
        actual=dict(returnType=ctx.type_name(m.return_type),parameters=[dict(name=md.string(p.name_index),type=ctx.type_name(p.type_index))for p in params],slot=m.slot,isStatic=bool(m.flags&16))
        _require(_strict(actual,{k:row[k]for k in actual}),'transfer-signature',row,actual)
        abi=[]
        for p in params:
            raw=image.pe.bytes_at_va(ctx.type_pointer(p.type_index),16);abi.append(dict(name=md.string(p.name_index),rawTypeHex=raw.hex(),byref=bool(raw[11]&0x20)))
        _require(_strict(abi,row['parameterAbi']),'transfer-native-ABI',row['parameterAbi'],abi)
    _validate_fields(image,list(c['fields'].values()))
    size=c['viewTypeSize'];td=image.named_types[size['type']];ptr=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+td.index*8);raw=image.pe.bytes_at_va(ptr,16)
    _require(size['type']==CORE+'SkillCastInputView'and raw.hex()==size['hex']and ctx.is_value_type(size['type'])and int.from_bytes(raw[:4],'little')-c['inputHeaderBytes']==c['operands']['viewEndSource']+8,'transfer-view-extent','typed value end word',size)
    expected={'skillType':(CORE+'Skill','<skillType>k__BackingField','Beyond.Gameplay.SkillType'),
        'target':(CORE+'SkillCastInputView','targetHandleView',CORE+'TargetHandleView')}
    _require(set(c['fields'])==set(expected),'transfer-field-coverage',expected,c['fields'])
    for role,(owner,name,value)in expected.items():
        f=c['fields'][role];_require((f['type'],f['name'],f['valueType'])==(owner,name,value),'transfer-field-nominal',expected[role],f)


def _branch(raw,at):
    if len(raw)==2 and (raw[0]==0xeb or 0x70<=raw[0]<=0x7f):return at+2+int.from_bytes(raw[1:],'little',signed=True)
    if len(raw)==6 and raw[0]==0x0f and 0x80<=raw[1]<=0x8f:return at+6+int.from_bytes(raw[2:],'little',signed=True)
    if len(raw)==5 and raw[0]==0xe9:return at+5+int.from_bytes(raw[1:],'little',signed=True)
    return None


def _carrier(image,c,w):
    rows=[]
    for role in ('nameCarrier','carrierCold'):
        window=w[role];raw=bytes.fromhex(window['hex']);decoded=decode_blackboard_vectors(image.mapper,raw,image.pe.image_base+window['startRva'])
        _require(sum(len(bytes.fromhex(x['bytes']))for x in decoded)==len(raw),'transfer-decoder-complete',role,decoded)
        rows.extend(decoded)
    by={int(r['va'],16)-image.pe.image_base:r for r in rows};start=w['nameCarrier']['startRva'];end=w['nameCarrier']['endRva'];flow=c['flow'];sites=c['sites'];d=c['operands']
    _require(by[start]['text']=='mov rbx, rax','transfer-second-name-save','RBX=second getter result',by[start])
    calls={sites['providerCall']:flow['providerTarget'],sites['viewCall']:c['methods']['view']['identity'][3],
        sites['interruptCall']:c['methods']['interrupt']['identity'][3],sites['admissionCall']:c['methods']['canCast']['identity'][3]}
    observed_calls={};head=d['viewArgumentCopyStack'];target=d['targetArgumentSlot'];rbp_minus_rsp=d['frameBytes']+d['rbpLeaDisplacement']
    _require(target-head==c['fields']['target']['offset']-c['inputHeaderBytes'],'transfer-view-target-geometry','unboxed typed target within first copied vector',(head,target))
    reached=set();todo=[start];edges=[]
    allowed={'mov','movups','movaps','movsd','movdqa','psrldq','movd','movzx','test','cmp','xor','lea','call','jcc','je','jne','jmp','shr'}
    while todo:
        at=todo.pop()
        if at in reached or at in (end,flow['falseReturn'],flow['nullThrow']):continue
        _require(at in by,'transfer-CFG-target','decoded node or declared false/throw exit',at);reached.add(at);r=by[at];raw=bytes.fromhex(r['bytes']);next_at=at+len(raw)
        _require(r['text'].split()[0]in allowed,'transfer-supported-instruction','finite reviewed instruction families',r)
        register=(r.get('write')or{}).get('register')
        _require(at==start or register not in ('rbx','ebx','bx','bl','bh'),'transfer-name-register-preservation','no later RBX alias write',r)
        _require(register not in ('rsp','esp','sp','spl','rbp','ebp','bp','bpl'),'transfer-stack-base-preservation','stable frame',r)
        if raw[0]==0xe8:
            observed_calls[at]=at+5+struct.unpack('<i',raw[1:])[0]
            _require(at in calls and observed_calls[at]==calls[at],'transfer-call-target',calls,r)
        memory=r.get('memoryOperation')or{}
        if memory.get('direction')=='store':
            address=memory['address'];base=address.get('base')
            _require(base in ('rsp','rbp')and address.get('index')is None,'transfer-local-store-address','fixed stack local store',r)
            disp=address['displacement']+(rbp_minus_rsp if base=='rbp'else 0);size=memory['memoryBytes']
            overlaps=disp<head+16 and head<disp+size
            _require(not overlaps or at==sites['viewHeadStore']and disp==head and size==16,'transfer-target-stack-preservation','only selected view-head store overlaps target bytes',r)
        destination=_branch(raw,at)
        if destination is not None:
            edges.append([at,destination]);todo.append(destination)
            if raw[0]not in (0xe9,0xeb):todo.append(next_at)
        else:todo.append(next_at)
    _require(observed_calls==calls and sites['admissionCall']in reached,'transfer-reachable-calls',calls,observed_calls)
    _require(set(by)==reached,'transfer-all-fragment-instructions-reachable','all declared fragment nodes',set(by)-reached)
    # The returned view reference RAX remains intact until the selected vector load.
    for at,r in by.items():
        if flow['viewReturn']<=at<w['viewHeadCopy']['startRva']:
            _require((r.get('write')or{}).get('register')not in ('rax','eax','ax','al','ah')and not r['text'].startswith('call '),'transfer-view-result-preservation','same RAX view result',r)
    return dict(decodedInstructions=len(rows),cfgEdges=edges,normalWin64CallsRequired=True,coherentLocalStackRequired=True)


def _validate(image,c):
    _declarations(image,c);w={x['role']:x for x in c['codeWindows']};required={'lookupGuard','rereadName','viewCall','admission','overwrittenOutSlot','falseReturn','nameCarrier','carrierCold','viewHeadCopy','prologue'}
    _require(set(w)==required and len(w)==len(c['codeWindows']),'transfer-window-coverage',required,w);image.check_windows(c['codeWindows'],label='skillRequestTransfer')
    family=image.unwind_index.family(c['methods']['owner']['identity'][3]);raws={}
    for role,row in w.items():
        raw=bytes.fromhex(row['hex']);_require(len(raw)==row['endRva']-row['startRva']and any(x['runtimeTriple'][0]<=row['startRva']<row['endRva']<=x['runtimeTriple'][1]for x in family['ranges'])and image.pe.bytes_at_va(image.pe.image_base+row['startRva'],len(raw))==raw,'transfer-owned-bytes',role,row);raws[role]=raw
    d=c['operands'];sites=c['sites'];flow=c['flow'];pack=lambda value:struct.pack('<i',value)
    first=sites['firstGetterReturnRva'];callraw=image.pe.bytes_at_va(image.pe.image_base+first-5,5)
    _require(callraw[0]==0xe8 and first+struct.unpack('<i',callraw[1:])[0]==c['methods']['getter']['identity'][3]
        and any(x['runtimeTriple'][0]<=first-5<first<=x['runtimeTriple'][1]for x in family['ranges']),
        'transfer-first-getter-site','owned direct getter call',sites)
    _require(sites['secondGetterReturnRva']==sites['wrapperCall']+5 and sites['canCastReturnRva']==sites['admissionCall']+5,
        'transfer-return-site-links','exact selected call returns',sites)
    _require(all(type(v)is int for v in d.values()),'transfer-operands','ordinary integers',d)
    def call(role,target):return b'\xe8'+pack(c['methods'][target]['identity'][3]-sites[role]-5)
    _require(raws['prologue']==bytes.fromhex('405556488dac24')+pack(d['rbpLeaDisplacement'])+bytes.fromhex('4881ec')+pack(d['frameBytes']),'transfer-frame-geometry','frame bases from prologue',raws['prologue'].hex())
    guard=raws['lookupGuard'];prefix=bytes.fromhex('488b85')+pack(d['lookupOutSlot'])+bytes.fromhex('4885c074')+bytes([d['guardNullDisp']])+bytes.fromhex('39b8')+pack(c['fields']['skillType']['offset'])+bytes.fromhex('0f86')
    _require(guard[:-6]==prefix and _branch(guard[-8:-2],w['lookupGuard']['endRva']-8)==flow['falseReturn'],'transfer-lookup-guard','typed SkillType unsigned comparison; EDI explicit upstream operand',guard.hex())
    _require(raws['rereadName'][:7]==bytes.fromhex('33d2')+call('wrapperCall','wrapper')and raws['rereadName'][7:10]==bytes.fromhex('488bd8'),'transfer-reread-name','separate getter result saved RBX',raws['rereadName'].hex())
    _require(raws['viewCall']==bytes.fromhex('4533c0488d4d')+d['viewResultStack'].to_bytes(1,'little',signed=True)+bytes.fromhex('498bd64c8be0')+call('viewCall','view'),'transfer-view-call','independent hidden output buffer and provider R12',raws['viewCall'].hex())
    _require(raws['viewHeadCopy']==bytes.fromhex('0f10000f2955')+d['viewHeadCopyOtherStack'].to_bytes(1,'little',signed=True)+bytes.fromhex('0f294424')+bytes([d['viewArgumentCopyStack']]),'transfer-view-head-copy','returned view first16 -> selected stack16',raws['viewHeadCopy'].hex())
    expected=bytes.fromhex('4c8b4424')+bytes([d['targetArgumentSlot']])+bytes.fromhex('41b10148897c24')+bytes([d['outgoingMethodInfo']])+bytes.fromhex('488bd344887c24')+bytes([d['outgoingSkipInterrupt']])+bytes.fromhex('498bcec64424')+bytes([d['outgoingSkipDistance']])+bytes.fromhex('00')+call('admissionCall','canCast')
    _require(raws['admission']==expected,'transfer-admission-ABI','second name RDX and copied view target R8',raws['admission'].hex())
    _require(raws['overwrittenOutSlot']==bytes.fromhex('f20f1040')+bytes([d['viewEndSource']])+bytes.fromhex('f20f1185')+pack(d['lookupOutSlot']),'transfer-old-output-overwritten','view tail bytes replace previous lookup local',raws['overwrittenOutSlot'].hex())
    carrier=_carrier(image,c,w);_require(_strict(c['rules'],_rules()),'transfer-rules-boundary',_rules(),c['rules'])
    return dict(rules=_rules(),carrier=carrier,callSites=sites,evidenceBoundary=c['evidenceBoundary'],guardComparison='unsigned SkillType <= explicit upstream EDI returns false; no signed-positive interpretation')


def load_skill_request_transfer(*,gameassembly,metadata,contract_path=CONTRACT_PATH):
    path=Path(contract_path);audit=dict(schema='endfield.skill-request-transfer-native-audit.v1',status='validation_failed',rules={},failures=[])
    try:
        c,digest=read_reviewed_contract(path,schema=SCHEMA,status='reviewed',label='skillRequestTransfer');pins=c['nativeInputs'];g=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata);audit.update(status=g.status,detail=g.detail)
        if g.status!='validated':return audit
        result=_validate(open_native_image(g.gameassembly,g.metadata),c);after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
        _require(after.status=='validated'and hashlib.sha256(path.read_bytes()).hexdigest().upper()==digest,'transfer-bookend','unchanged selected inputs',after.status);audit.update(result,status='validated-conditional-carriers',nativeInputs=pins)
    except(OSError,ValueError,KeyError,IndexError,TypeError,RuntimeError,struct.error,OverflowError)as error:audit.update(status='validation_failed',rules={},failures=[dict(check=str(error)[:1000],source=str(path))])
    return audit


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('gameassembly','metadata','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();r=load_skill_request_transfer(gameassembly=a.gameassembly,metadata=a.metadata)
    from scripts.repo_paths import REPO_ROOT
    _require(any(a.output.resolve().is_relative_to(REPO_ROOT/x)for x in ('reports','scratch','tmp')),'transfer-output-root','ignored',a.output)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));return 0 if r['status']=='validated-conditional-carriers'else 1


if __name__=='__main__':raise SystemExit(main())
