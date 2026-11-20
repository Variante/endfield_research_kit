"""Typed Center transition construction requests, without live delegate claims."""
from __future__ import annotations
import hashlib
import json
import struct
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.context import unresolved_usage_index
from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.skill_timing_runtime_native import _require

SCHEMA='endfield.skill-center-transition-construction-native-contract.v1'
AUDIT_SCHEMA='endfield.skill-center-transition-construction-native-audit.v1'
CONTRACT_PATH=CONTRACTS_DIR/'skill_center_transition_construction_native.json'

def _rules():
    return dict(originalPathOnly=True,normalWin64ReturnsRequired=True,
        entryRaxEqualsSavedRdiDelegateTokenRequired=True,entryRbxMachineRequired=True,
        methodDefUsageRequestProved=True,sameMachineDelegateTargetRequestProved=True,
        sameDelegateTokenPassedAsConditionProved=True,typedTransitionRequestArgumentsProved=True,
        argumentsReportedAsUnsignedBits32=True,
        compiledDelegateInitializerIdentityProved=False,compiledTransitionAdderIdentityProved=False,
        initializedMethodInfoIdentityProved=False,delegateStoredDispatchTargetProved=False,
        transitionCollectionEffectsProved=False,liveSelectedTransitionProved=False)

def _rip(image,at):
    raw=image.pe.bytes_at_va(image.pe.image_base+at,7)
    return at+7+struct.unpack_from('<i',raw,3)[0]

def _arguments(raw,start):
    """Finite straight-line suffix: exact supported instructions, no opaque writes."""
    registers={'rbx':'machine','rdi':'delegate','rcx':'transitionMethodInfo'}
    stack={};at=0
    while at<len(raw):
        tail=raw[at:];size=0
        for prefix,reg in [(b'\xba','edx'),(b'\x41\xb8','r8d'),(b'\x41\xb9','r9d')]:
            if tail.startswith(prefix) and len(tail)>=len(prefix)+4:
                size=len(prefix)+4;registers[reg]=int.from_bytes(tail[len(prefix):size],'little');break
        if size:at+=size;continue
        actions={bytes.fromhex('33d2'):('edx',0),bytes.fromhex('4533c9'):('r9d',0),
            bytes.fromhex('458bc1'):('r8d','r9d'),bytes.fromhex('448bca'):('r9d','edx'),
            bytes.fromhex('448bc2'):('r8d','edx'),bytes.fromhex('488bcb'):('rcx','rbx')}
        found=False
        for code,(dest,source) in actions.items():
            if tail.startswith(code):
                _require(type(source)is int or source in registers,'centerTransition.argument-source','defined register',source)
                registers[dest]=source if type(source)is int else registers[source];at+=len(code);found=True;break
        if found:continue
        for code,offset,source in [(bytes.fromhex('48894c2428'),40,'rcx'),(bytes.fromhex('48897c2420'),32,'rdi')]:
            if tail.startswith(code):stack[offset]=registers[source];at+=len(code);found=True;break
        if found:continue
        raise ValueError(f'centerTransition.argument-instruction: rva={start+at:#x} bytes={tail[:8].hex()}')
    _require(registers.get('rcx')=='machine' and stack=={40:'transitionMethodInfo',32:'delegate'},
        'centerTransition.argument-carriers','machine plus same delegate and MethodInfo stack arguments',dict(registers=registers,stack=stack))
    return {key:registers[key] for key in ('edx','r8d','r9d')}

def _validate(image,c):
    image.validate_method_row(c['owner'],label='centerTransition.constructor')
    image.validate_method_row(c['predicate'],label='centerTransition.predicate')
    _require(c['owner'][1:3]==['Beyond.Gameplay.AI.CharacterMainCtrlSystem+CenterStateMachine','.ctor'] and
        c['predicate'][1:3]==[c['owner'][1],'_ToSkill'],'centerTransition.named-methods','Center constructor and _ToSkill',c['owner'])
    image.check_windows(c['codeWindows'],label='centerTransition')
    family=image.unwind_index.family(c['owner'][3])['ranges'];results=[]
    _require(len(c['requests'])==4 and len({r['id']for r in c['requests']})==4 and
        len({r['startRva']for r in c['requests']})==4,
        'centerTransition.request-count','four distinct reviewed requests',len(c['requests']))
    for r in c['requests']:
        start=r['startRva'];raw=bytes.fromhex(r['hex']);end=start+len(raw)
        _require(any(a['runtimeTriple'][0]<=start and end<=a['runtimeTriple'][1] for a in family),
            'centerTransition.constructor-ownership','one constructor family interval',r['id'])
        _require(image.pe.bytes_at_va(image.pe.image_base+start,len(raw))==raw,'centerTransition.request-bytes',r['id'],raw.hex())
        _require(raw[:3]==bytes.fromhex('4c8b05') and raw[7:17]==bytes.fromhex('4533c9488bd3488bc8e8'),
            'centerTransition.delegate-arguments','R8 usage; R9=0; RDX=RBX; RCX=RAX; direct call',r['id'])
        cell=_rip(image,start);usage=image.pe.bytes_at_va(image.pe.image_base+cell,8)
        mi=unresolved_usage_index(usage,len(image.metadata.methods),tag=3,source='centerTransition',offset=cell)
        _require(mi==c['predicate'][0],'centerTransition.predicate-usage',c['predicate'][0],mi)
        call=start+16
        _require(raw[16]==0xe8 and call+5+struct.unpack_from('<i',raw,17)[0]==c['delegateInitializerRva'],
            'centerTransition.delegate-call','selected physical initializer call; effects opaque',r['id'])
        context_at=start+21
        context=derive_typed_usage_context(image,context_at,label='centerTransition.addContext')
        _require(context['typeName']=='Beyond.Gameplay.StateMachine`2' and context['methodName']=='AddTransition' and
            context['classArguments']==['Beyond.Gameplay.AI.CharacterMainCtrlSystem+CenterState','Beyond.Gameplay.AI.CharacterMainCtrlSystem+CenterBlackboard'],
            'centerTransition.typed-transition','closed Center AddTransition',context)
        _require(raw[21:24]==bytes.fromhex('488b0d') and raw[-5]==0xe8 and
            end+struct.unpack_from('<i',raw,len(raw)-4)[0]==c['transitionAdderRva'],
            'centerTransition.transition-call','typed context and selected direct AddTransition',r['id'])
        args=_arguments(raw[28:-5],start+28)
        actual=dict(fromState=args['edx'],toState=args['r8d'],priority=args['r9d'])
        _require(actual==r['arguments'],'centerTransition.request-arguments',r['arguments'],actual)
        results.append(dict(id=r['id'],**actual,predicateUsageCellRva=cell,predicateMethodIndex=mi,
            initializerCallRva=call,transitionCallRva=end-5,evidence='conditional'))
    _require(set(c['evidenceBoundary'])=={'exact','conditional','unresolved'} and
        all(isinstance(v,list) and v and all(isinstance(s,str) and s for s in v) for v in c['evidenceBoundary'].values()),
        'centerTransition.evidence-boundary','nonempty exact/conditional/unresolved descriptions',c['evidenceBoundary'])
    _require(json.dumps(c['rules'],sort_keys=True)==json.dumps(_rules(),sort_keys=True),
        'centerTransition.rules',_rules(),c['rules'])
    return results

def load_skill_center_transition_construction(contract_path=CONTRACT_PATH,*,gameassembly=None,metadata=None):
    path=Path(contract_path);audit=dict(schema=AUDIT_SCHEMA,status='validation_failed',rules={},rows=[],nativeInputs={},failures=[])
    try:
        c,digest=read_reviewed_contract(path,schema=SCHEMA,status='reviewed',label='centerTransition')
        pins=c['nativeInputs'];gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
        audit.update(status=gate.status,detail=gate.detail)
        if gate.status!='validated':return audit
        image=open_native_image(gate.gameassembly,gate.metadata);rows=_validate(image,c)
        after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
        _require(after.status=='validated' and hashlib.sha256(path.read_bytes()).hexdigest().upper()==digest,
            'centerTransition.input-bookend','unchanged selected native and contract',after.detail)
        audit.update(status='validated-conditional-requests',detail='',rules=_rules(),rows=rows,nativeInputs=pins,evidenceBoundary=c['evidenceBoundary'])
    except (OSError,ValueError,KeyError,TypeError,IndexError,RuntimeError,struct.error) as exc:
        audit.update(status='validation_failed',detail=str(exc)[:1200],rules={},rows=[],nativeInputs={},failures=[dict(check=str(exc).split(':',1)[0],detail=str(exc)[:1200])])
    return audit

def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gameassembly',type=Path,required=True)
    parser.add_argument('--metadata',type=Path,required=True)
    parser.add_argument('--output',type=Path,default=Path('reports/skill_center_transition_construction.json'))
    args=parser.parse_args()
    reports=(Path(__file__).resolve().parents[2]/'reports').resolve()
    output=args.output.resolve()
    if not output.is_relative_to(reports):parser.error('--output must remain under repository reports/')
    audit=load_skill_center_transition_construction(gameassembly=args.gameassembly,metadata=args.metadata)
    if audit['status']!='validated-conditional-requests':
        print(f"{audit['status']}: publication skipped; existing report untouched")
        if audit.get('detail'):print(audit['detail'])
        return 1
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f"{audit['status']}: rows={len(audit['rows'])} output={output}")
    if audit.get('detail'):print(audit['detail'])
    return 0

if __name__=='__main__':raise SystemExit(main())
