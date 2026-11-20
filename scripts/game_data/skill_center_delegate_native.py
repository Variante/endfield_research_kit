"""Selected physical delegate initializer and ConditionChecker slot join.

Each MethodInfo flag/heap read is an independent input. No initialized runtime
MethodInfo identity or live Center transition is inferred from this program.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.protocol import runtime_type_name
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext, validate_reference_ancestor_chain
from scripts.game_data.skill_pending_storage_native import _match
from scripts.game_data.skill_timing_runtime_native import _require, _validate_fields
from scripts.game_data import skill_center_dispatch_native as dispatch
from scripts.game_data import skill_center_lifecycle_native as lifecycle

SCHEMA='endfield.skill-center-delegate-native-contract.v1'
AUDIT_SCHEMA='endfield.skill-center-delegate-native-audit.v1'
CONTRACT_PATH=CONTRACTS_DIR/'skill_center_delegate_native.json'
DEPS={'dispatch':('skill_center_dispatch_native.json',dispatch.SCHEMA),
      'lifecycle':('skill_center_lifecycle_native.json',lifecycle.SCHEMA)}

def _same(a,b):return json.dumps(a,sort_keys=True,allow_nan=False)==json.dumps(b,sort_keys=True,allow_nan=False)

def _rules():
    return dict(originalPathOnly=True,normalReturnOnly=True,independentHeapReadsRequired=True,
        selectedNormalInitializerCfgProved=True,resolverPreservesArgumentCarriers=True,
        barrierPreservesArgumentCarriers=True,dispatchSlotsMatchConditionConsumer=True,
        canonicalEnumInitializerRegistrationProved=True,systemDelegateFieldOffsetsProved=True,
        runtimeMethodInfoIdentityProved=False,actualToSkillDelegateBindingProved=False,
        liveReceiverTypeIdentityProved=False,liveTransitionSelectionProved=False)

def _rows():
    # These describe raw physical flag predicates, not inferred CLR meanings.
    return [dict(id=key,condition=condition,dispatchTargetSource=target,
        dispatchFunctionSource=function,requiresTargetNonNull=nonnull,evidence='conditional')
        for key,condition,target,function,nonnull in [
        ('instanceTarget','(flag4c & 0x10) == 0 and supplied target nonnull','reread.targetSlot','reread.methodPointerSlot',True),
        ('staticSharedTarget','(flag4c & 0x10) != 0 and (flag54 & 0x10) == 0 and byte53 nonzero','reread.targetSlot','reread.methodPointerSlot',False),
        ('staticSelfThunk','(flag4c & 0x10) != 0 and (flag54 & 0x10) == 0 and byte53 zero','receiver','selfThunk',False),
        ('staticSpecialZero','(flag4c & 0x10) != 0 and (flag54 & 0x10) != 0 and byte53 zero','receiver','specialZeroThunk',False),
        ('staticSpecialNonzero','(flag4c & 0x10) != 0 and (flag54 & 0x10) != 0 and byte53 nonzero','receiver','specialNonzeroThunk',False)]]

def _semantic_parameters(c,offsets):
    """Publish authenticated numeric masks, never ambiguous bit ordinals."""
    op=c['operands']
    return dict(resolver=dict(flagByteOffset=op['flag54Offset'],flagMask=op['resolverFlagMask'],
        primaryCodeOffset=op['primaryCodeOffset'],alternateCodeOffset=op['alternateCodeOffset']),
        initializer=dict(byte53Offset=op['byte53Offset'],flag4cOffset=op['flag4cOffset'],
            flag54Offset=op['flag54Offset'],flagMask=op['flag10Mask']),
        delegateSlots=dict(offsets),conditionConsumerSlots=dict(function=offsets['invoke'],
            methodInfo=offsets['method'],target=offsets['dispatchTarget']))

def _programs(c,offsets):
    h=bytes.fromhex;O=lambda k,w=1:('operand',k,w);F=lambda k:('field',k,1);R=lambda k,w=4:('relative',k,w)
    p={
      'entry':[h('4883ec'),O('frame'),h('4c8bc94d8bd8498bc84c8bd2e8'),R('resolverRva'),
        h('498d49'),F('target'),h('498941'),F('pointer'),h('4d8941'),F('method'),
        h('498951'),F('target'),h('e8'),R('barrierRva')],
      'branch':[h('410fb643'),O('byte53Offset'),h('4d8949'),F('dispatchTarget'),
        h('41f643'),O('flag4cOffset'),O('flag10Mask'),h('0f85'),R('staticRva'),
        h('4d85d20f84'),R('nullRva')],
      'reload':[h('498b41'),F('target'),h('498b49'),F('pointer'),h('498941'),F('dispatchTarget')],
      'join':[h('b8'),O('invokeOffset',4),h('498bd148890c02488d05'),R('trampolineRva'),
        h('498941'),F('extra'),h('4883c4'),O('frame'),h('c3')],
      'static':[h('41f643'),O('flag54Offset'),O('flag10Mask'),h('74'),R('staticOtherRva',1),
        h('84c0488d0d'),R('specialZeroThunkRva'),h('488d15'),R('specialNonzeroThunkRva'),
        h('480f45cae9'),R('joinRva')],
      'staticOther':[h('84c00f85'),R('reloadRva'),h('488d0d'),R('selfThunkRva'),h('e9'),R('joinRva')],
      'null':[h('488d15'),R('nullMessageCell'),h('33c9e8'),R('nullCreateRva'),
        h('33d2488bc8e8'),R('nullRaiseRva'),h('cc')],
      'resolver':[h('f641'),O('flag54Offset'),O('resolverFlagMask'),h('75'),R('resolverAlternateTestRva',1),
        h('488b41'),O('primaryCodeOffset'),h('c348833d'),R('resolverGlobalRelativeEnd'),h('0074'),R('resolverPrimaryRva',1),
        h('488b41'),O('alternateCodeOffset'),h('c3')],
    }
    spans={s['id']:s for s in c['spans']};op=c['operands'];targets={**op,'resolverGlobalRelativeEnd':op['resolverGlobalCell']-1}
    _require(len(spans)==len(c['spans']) and set(spans)==set(p),'centerDelegate.program-coverage',sorted(p),sorted(spans))
    _require(all(type(v)is int for v in op.values()),'centerDelegate.operand-types','ordinary integer operands',op)
    _require(op['invokeOffset']==offsets['invoke'] and op['flag10Mask']==16 and op['resolverFlagMask']==2,
        'centerDelegate.mask-and-index','observed bit masks and invoke slot',op)
    for key,program in p.items():
        span=spans[key];raw=bytes.fromhex(span['hex'])
        _require(_match(raw,span['rva'],program,offsets,op,targets),
            'centerDelegate.semantic-program',key,raw.hex())
    end=lambda key:spans[key]['rva']+len(bytes.fromhex(spans[key]['hex']))
    for chain in [('entry','branch','reload','join'),('static','staticOther','null')]:
        for left,right in zip(chain,chain[1:]):_require(end(left)==spans[right]['rva'],
            'centerDelegate.contiguous-edge',left,right)
    for key in ('entry','reload','join','static','staticOther','null','resolver'):
        _require(spans[key]['rva']==op[key+'Rva'],'centerDelegate.branch-target',key,op[key+'Rva'])
    resolver=spans['resolver']['rva']
    _require(op['resolverPrimaryRva']==resolver+6 and op['resolverAlternateTestRva']==resolver+11,
        'centerDelegate.resolver-targets','primary load and alternate-condition entry',op)
    # The resolver grammar is a closed leaf writing only RAX/flags. In
    # particular RDX/R8/R9/R10/R11 are preserved by its instructions, not ABI.
    return spans

def _registration(image,c):
    row=c['registration'];reg=image.registration;pe=image.pe;md=image.metadata
    code=image.mapper.code_registration_summary(pe,image.code_registration)
    ti,si,pi=(row[k]for k in ('tableIndex','methodSpecIndex','pointerIndex'))
    _require(all(type(v)is int and v>=0 for v in (ti,si,pi)) and ti<reg['genericMethodTableCount'] and
        si<reg['methodSpecsCount'] and pi<code['genericMethodPointersCount'],
        'centerDelegate.registration-bounds','bounded registration indices',row)
    actual=struct.unpack('<iiii',pe.bytes_at_va(int(reg['genericMethodTable'],16)+ti*16,16))
    _require(actual[:2]==(si,pi),'centerDelegate.registration-row',(si,pi),actual)
    mi,ci,method_inst=struct.unpack('<iii',pe.bytes_at_va(int(reg['methodSpecs'],16)+si*12,12))
    owner=image.named_types['Beyond.Gameplay.FSMTransition`1+ConditionChecker']
    _require(owner.method_start<=mi<owner.method_start+owner.method_count and mi==row['methodIndex'] and
        md.string(md.methods[mi].name_index)=='.ctor' and ci>=0 and method_inst==-1,
        'centerDelegate.registration-method','ConditionChecker class-only constructor MethodSpec',(mi,ci,method_inst))
    args=[runtime_type_name(pe,md,a.type_pointer_va)for a in image.instantiations.resolve(ci).arguments]
    rva=pe.u64_at_va(int(code['genericMethodPointers'],16)+pi*8)-pe.image_base
    _require(args==row['classArguments']==['System.Int32Enum'] and rva==row['entryRva']==c['operands']['entryRva'],
        'centerDelegate.canonical-registration','canonical enum constructor physical helper',dict(args=args,rva=rva))

def _validate(image,c,deps):
    cx=NativeReferenceContext(image)
    validate_reference_ancestor_chain(cx,'Beyond.Gameplay.FSMTransition`1+ConditionChecker',
        ['System.MulticastDelegate','System.Delegate'],'System.Delegate')
    fields=_validate_fields(image,c['fields']);offsets={key:r['offset']for key,r in fields.items()}
    expected={'pointer':('method_ptr','nint'),'invoke':('invoke_impl','nint'),'target':('m_target','object'),
        'method':('method','nint'),'extra':('extra_arg','nint'),'dispatchTarget':('method_code','nint')}
    _require(set(fields)==set(expected),'centerDelegate.field-coverage',sorted(expected),sorted(fields))
    for key,(name,value_type)in expected.items():
        _require((fields[key]['type'],fields[key]['name'],fields[key]['valueType'])==('System.Delegate',name,value_type),
            'centerDelegate.nominal-field',expected[key],fields[key])
    _registration(image,c);spans=_programs(c,offsets)
    image.check_windows(c['codeWindows'],label='centerDelegate')
    family=[r['runtimeTriple'][:2]for r in image.unwind_index.family(c['operands']['entryRva'])['ranges']]
    owned=[[w['startRva'],w['endRva']]for w in c['codeWindows']if w['owner']=='initializer']
    _require(owned==family,'centerDelegate.complete-initializer-family',family,owned)
    for key,span in spans.items():
        raw=bytes.fromhex(span['hex']);a=span['rva'];b=a+len(raw)
        _require(image.pe.bytes_at_va(image.pe.image_base+a,len(raw))==raw and
            (key=='resolver' or any(lo<=a and b<=hi for lo,hi in family)),
            'centerDelegate.authenticated-span','actual owned bytes',key)
    _require(family==[[spans['entry']['rva'],spans['join']['rva']+len(bytes.fromhex(spans['join']['hex']))],
        [spans['static']['rva'],spans['null']['rva']+len(bytes.fromhex(spans['null']['hex']))]],
        'centerDelegate.complete-cfg','main and cold ranges fully consumed',family)
    # Lifecycle owns this barrier. Its exact closed grammar has only RAX,
    # RCX, RDX and R8 destinations, no calls and a bounded CAS retry edge.
    # Therefore R9/R10/R11 survive every normally returning barrier path.
    life=deps['lifecycle'];barrier=lifecycle._programs(life)
    _require(barrier['barrierEntryRva']==c['operands']['barrierRva'],
        'centerDelegate.barrier-target','same proved barrier',barrier)
    b=next(s for s in life['spans']if s['id']=='barrier');raw=bytes.fromhex(b['hex'])
    _require(image.pe.bytes_at_va(image.pe.image_base+b['rva'],len(raw))==raw,
        'centerDelegate.barrier-bytes','actual fully matched closed barrier',b['rva'])
    dispatch._validate(image,deps['dispatch']);dop=deps['dispatch']['operands']
    _require((dop['delegatePointerOffset'],dop['delegateMethodInfoOffset'],dop['delegateTargetOffset'])==
        (offsets['invoke'],offsets['method'],offsets['dispatchTarget']),
        'centerDelegate.condition-slots','initializer slots are ConditionChecker pointer/MethodInfo/target reads',dop)
    _require(_same(c['rules'],_rules()) and _same(c['rows'],_rows()),
        'centerDelegate.rules-and-paths',dict(rules=_rules(),rows=_rows()),dict(rules=c['rules'],rows=c['rows']))
    return dict(rows=_rows(),rules=_rules(),physicalSlots=offsets,
        semanticParameters=_semantic_parameters(c,offsets),
        resolverPreservedRegisters=['rdx','r8','r9','r10','r11'],barrierPreservedRegisters=['r9','r10','r11'])

def load_skill_center_delegate(contract_path=CONTRACT_PATH,*,gameassembly=None,metadata=None):
    path=Path(contract_path);audit=dict(schema=AUDIT_SCHEMA,status='validation_failed',rules={},rows=[],nativeInputs={},failures=[])
    try:
        c,digest=read_reviewed_contract(path,schema=SCHEMA,status='reviewed',label='centerDelegate');pins=c['nativeInputs']
        gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
        audit.update(status=gate.status,detail=gate.detail)
        if gate.status!='validated':return audit
        image=open_native_image(gate.gameassembly,gate.metadata);deps={};snapshots={path:digest}
        for key,(name,schema)in DEPS.items():
            dep_path=CONTRACTS_DIR/name;dep,dep_digest=read_reviewed_contract(dep_path,schema=schema,status='reviewed',label='centerDelegate.'+key)
            _require(_same(dep['nativeInputs'],pins),'centerDelegate.dependency-build',pins,dep['nativeInputs'])
            deps[key]=dep;snapshots[dep_path]=dep_digest
        result=_validate(image,c,deps)
        after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
        _require(after.status=='validated' and all(hashlib.sha256(p.read_bytes()).hexdigest().upper()==d for p,d in snapshots.items()),
            'centerDelegate.input-bookend','unchanged selected native and reviewed contracts',after.detail)
        audit.update(status='validated-conditional-delegate',detail='',nativeInputs=pins,evidenceBoundary=c['evidenceBoundary'],**result)
    except (OSError,ValueError,KeyError,TypeError,IndexError,RuntimeError,struct.error,StopIteration) as exc:
        audit.update(status='validation_failed',detail=str(exc)[:1200],rules={},rows=[],nativeInputs={},failures=[dict(check=str(exc).split(':',1)[0],detail=str(exc)[:1200])])
    return audit

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gameassembly',type=Path,required=True);parser.add_argument('--metadata',type=Path,required=True)
    parser.add_argument('--output',type=Path,default=Path('reports/skill_center_delegate_native.json'))
    args=parser.parse_args();output=args.output.resolve();reports=(Path(__file__).resolve().parents[2]/'reports').resolve()
    if not output.is_relative_to(reports):parser.error('--output must remain under repository reports/')
    audit=load_skill_center_delegate(gameassembly=args.gameassembly,metadata=args.metadata)
    if audit['status']!='validated-conditional-delegate':
        print(f"{audit['status']}: publication skipped; existing report untouched")
        if audit.get('detail'):print(audit['detail'])
        return 1
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f"{audit['status']}: rows={len(audit['rows'])} output={output}");return 0

if __name__=='__main__':raise SystemExit(main())
