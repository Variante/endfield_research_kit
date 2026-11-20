"""Authenticate a bounded getter-result to skill-lookup argument bridge."""
from __future__ import annotations
import argparse,hashlib,json,struct
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.skill_timing_runtime_native import _require,_validate_fields
from scripts.game_data.skill_ai_dispatch_native import _strict

CONTRACT_PATH=CONTRACTS_DIR/'skill_request_delivery_native.json'
SCHEMA='endfield.skill-request-delivery-native-contract.v1'
ABILITY='Beyond.Gameplay.Core.AbilitySystem'
COMBO=ABILITY+'+ComboController'


def _rules():
    return dict(originalPathOnly=True,upstreamAbilityReceiverRequired=True,normalNonNullFallthroughRequired=True,
        getterResultForwardedAsSkillId=True,lookupOutParameterByref=True,lookupFalseReturnsFalse=True,
        lookupInternalsProved=False,completeReceiverContinuityProved=False,beforeCastLinkProved=False,
        actualCastProved=False,runtimeSelectionProved=False)


def _declarations(image,c):
    ctx=NativeReferenceContext(image);md=image.metadata
    expected={'owner':('Beyond.Gameplay.AI.CharacterMainCtrlSystem+CenterStateMachine','_ToSkill'),
        'getter':(COMBO,'get_nextSkillId'),'lookup':(ABILITY,'_TryGetSkill'),'wrapper':(ABILITY,'GetNextSkillId'),
        'attackQuery':(ABILITY,'GetNextAttackId'),'hasAttack':(ABILITY,'HasNextAttackRequest')}
    _require(set(c['methods'])==set(expected),'delivery-method-coverage',expected,c['methods'])
    for role,row in c['methods'].items():
        identity=row['identity'];_require(tuple(identity[1:3])==expected[role],'delivery-nominal-role',expected[role],identity)
        index=image.validate_method_row(identity,label='skillRequestDelivery');m=md.methods[index];params=list(md.parameters_for(m))
        actual={'returnType':ctx.type_name(m.return_type),'parameters':[{'name':md.string(p.name_index),'type':ctx.type_name(p.type_index)}for p in params],
            'slot':m.slot,'isStatic':bool(m.flags&16)}
        _require(_strict(actual,{k:row[k]for k in actual}),'delivery-method-signature',row,actual)
        abi=[]
        for p in params:
            raw=image.pe.bytes_at_va(ctx.type_pointer(p.type_index),16)
            abi.append({'name':md.string(p.name_index),'rawTypeHex':raw.hex(),'byref':bool(raw[11]&0x20)})
        _require(_strict(abi,row['parameterAbi']),'delivery-parameter-ABI',row['parameterAbi'],abi)
    lookup=c['methods']['lookup']
    _require(lookup['returnType']=='bool'and _strict(lookup['parameters'],[{'name':'skillId','type':'string'},{'name':'skill','type':'Beyond.Gameplay.Core.Skill'}])
        and [x['byref']for x in lookup['parameterAbi']]==[False,True],'delivery-lookup-ABI','Bool(String,ref Skill)',lookup)
    _validate_fields(image,[c['comboField']])
    f=c['comboField'];_require(f['id']==ABILITY+'::m_comboController'and f['valueType']==COMBO and f['static']is False,'delivery-combo-field',COMBO,f)


def _validate(image,c):
    _declarations(image,c);windows={r['role']:r for r in c['codeWindows']};methods=c['methods']
    _require(set(windows)=={'transfer','falseReturn','wrapper'}and len(windows)==len(c['codeWindows']),'delivery-window-coverage','three',windows)
    image.check_windows(c['codeWindows'],label='skillRequestDelivery');raws={}
    for role,w in windows.items():
        expected_owner='wrapper'if role=='wrapper'else'owner';_require(w['methodRole']==expected_owner,'delivery-window-role',expected_owner,w)
        family=image.unwind_index.family(methods[expected_owner]['identity'][3]);raw=bytes.fromhex(w['hex'])
        _require(len(raw)==w['endRva']-w['startRva']and any(r['runtimeTriple'][0]<=w['startRva']<w['endRva']<=r['runtimeTriple'][1]for r in family['ranges'])
            and image.pe.bytes_at_va(image.pe.image_base+w['startRva'],len(raw))==raw,'delivery-window-ownership-bytes',role,w);raws[role]=raw
    sites=c['sites'];field=c['comboField'];d=c['operands'];disp=struct.pack('<i',field['offset'])
    def call(at,target):return b'\xe8'+struct.pack('<i',target-at-5)
    transfer=raws['transfer'];start=windows['transfer']['startRva']
    prefix=bytes.fromhex('488b8b')+disp+bytes.fromhex('4885c974')
    _require(transfer.startswith(prefix),'delivery-receiver-read','RBX combo field -> RCX null test',transfer.hex())
    getter=sites['getterCall'];lookup=sites['lookupCall'];branch=sites['falseBranch']
    middle=bytes.fromhex('33d2')+call(getter,methods['getter']['identity'][3])+bytes.fromhex('4533c94c8d85')+struct.pack('<i',d['outSlotRbpDisplacement'])+bytes.fromhex('488bd0488bcb')+call(lookup,methods['lookup']['identity'][3])+bytes.fromhex('84c00f84')
    _require(start+len(prefix)+1+2==getter and getter+5+len(bytes.fromhex('4533c94c8d85'))+4+6==lookup
        and transfer[len(prefix)+1:-4]==middle and branch==lookup+7,'delivery-result-argument-program','RAX getter -> RDX lookup; RBX -> RCX; R8 stack address',transfer.hex())
    _require(branch+6+struct.unpack('<i',transfer[-4:])[0]==windows['falseReturn']['startRva']and raws['falseReturn']==bytes.fromhex('32c0'),
        'delivery-false-result-edge','lookup false -> AL zero',transfer.hex())
    wrapper=raws['wrapper'];tail=sites['wrapperTail'];release=d['wrapperStackRelease']
    _require(wrapper[:-4]==bytes.fromhex('488b89')+disp+bytes.fromhex('4885c9741033d24883c4')+bytes([release])+b'\xe9'
        and tail+5==windows['wrapper']['endRva']and tail+5+struct.unpack('<i',wrapper[-4:])[0]==methods['getter']['identity'][3],
        'delivery-wrapper-tail','normal nonnull field receiver tail-jumps named getter',wrapper.hex())
    bindings=[]
    for row in c['recordedCallerSites']:
        method=next((m for m in methods.values()if m['identity'][3]==row['familyEntry']),None)
        _require(method is not None,'delivery-caller-nominal-owner','declared owner',row)
        family=image.unwind_index.family(row['familyEntry'])
        _require(any(r['runtimeTriple']==row['runtimeTriple']and row['runtimeTriple'][0]<=row['returnRva']<row['runtimeTriple'][1]for r in family['ranges']),
            'delivery-caller-owned-range','selected unwind family',row)
        at=row['returnRva']-5;raw=image.pe.bytes_at_va(image.pe.image_base+at,5)
        _require(raw[0]==0xe8,'delivery-recorded-caller-call','direct E8 call before captured return',raw.hex())
        target=at+5+struct.unpack('<i',raw[1:])[0]
        _require(target in (methods['getter']['identity'][3],methods['wrapper']['identity'][3]),'delivery-recorded-call-target','getter or reviewed tail wrapper',target)
        bindings.append(dict(returnRva=row['returnRva'],owner=method['identity'],ownerRole=next(role for role,m in methods.items()if m is method),targetRole='getter'if target==methods['getter']['identity'][3]else'wrapper',category='lookup-for-transition'if method is methods['owner']else'query-only',
            getterAlias='direct'if target==methods['getter']['identity'][3]else'AbilitySystem.GetNextSkillId-tail',
            categoryBoundary='Bounded lookup/query caller classification; no transition completion or cast inferred.',actualCastProved=False))
    _require(_strict(c['rules'],_rules()),'delivery-rules-boundary',_rules(),c['rules'])
    return dict(rules=_rules(),callSites=sites,recordedCallerSites=c['recordedCallerSites'],callerBindings=bindings,evidenceBoundary=c['evidenceBoundary'])


def load_skill_request_delivery(*,gameassembly,metadata,contract_path=CONTRACT_PATH):
    path=Path(contract_path);audit={'schema':'endfield.skill-request-delivery-native-audit.v1','status':'validation_failed','rules':{},'failures':[]}
    try:
        c,digest=read_reviewed_contract(path,schema=SCHEMA,status='reviewed',label='skillRequestDelivery');pins=c['nativeInputs']
        gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
        audit.update(status=gate.status,detail=gate.detail)
        if gate.status!='validated':return audit
        result=_validate(open_native_image(gate.gameassembly,gate.metadata),c)
        after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
        _require(after.status=='validated','delivery-native-after','validated',after.status)
        _require(hashlib.sha256(path.read_bytes()).hexdigest().upper()==digest,'delivery-contract-after','unchanged',str(path))
        audit.update(result,status='validated-conditional-fragments',nativeInputs=pins)
    except(OSError,ValueError,KeyError,IndexError,TypeError,RuntimeError,struct.error,OverflowError)as error:
        audit.update(status='validation_failed',rules={},failures=[{'check':str(error)[:1000],'source':str(path)}])
    return audit


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('gameassembly','metadata','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();r=load_skill_request_delivery(gameassembly=a.gameassembly,metadata=a.metadata)
    from scripts.repo_paths import REPO_ROOT
    _require(any(a.output.resolve().is_relative_to(REPO_ROOT/x)for x in ('reports','scratch','tmp')),'delivery-output-root','ignored',a.output)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));return 0 if r['status']=='validated-conditional-fragments'else 1


if __name__=='__main__':raise SystemExit(main())

