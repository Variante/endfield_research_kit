"""Bounded Center refresh/clear and physical machine-source initialization facts.

No local-store inventory establishes a full writer census or a persistent live
blackboard identity. The bitmap helper is proved only to preserve the refresh
carriers; complete GC semantics and arbitrary opaque-callee effects are excluded.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import struct

from scripts.common import check_installed_native_inputs
from scripts.repo_paths import REPO_ROOT
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext,validate_reference_ancestor_chain
from scripts.game_data.skill_timing_runtime_native import _require,_validate_fields
from scripts.game_data.skill_pending_storage_native import _match
from scripts.game_data import skill_center_fsm_native as fsm_native
from scripts.game_data import skill_blackboard_getter_native as getter_native
from scripts.game_data import skill_blackboard_consumer_native as consumer_native

SCHEMA='endfield.skill-center-lifecycle-native-contract.v1'
AUDIT_SCHEMA='endfield.skill-center-lifecycle-native-audit.v1'
CONTRACT_PATH=CONTRACTS_DIR/'skill_center_lifecycle_native.json'


def _rules():
    return dict(originalPathOnly=True,normalWin64CallsRequired=True,barrierPreservesR10R11=True,
        refreshWritesAiBeforeNullTest=True,refreshNullAiRequestsOpaqueFailure=True,
        refreshNullAiLeavesEntityUnwritten=True,refreshNonNullAiEntityReadAfterAiWriteBarrier=True,
        refreshStoresNullEntityValue=True,refreshEndsWithEntityBarrierTail=True,
        refreshHasNoDirectBlackboardFieldStore=True,machineSlotInitializedFromOriginalArgument=True,
        machineSlotEqualsGetterPhysicalSlot=True,machineSlotClosedNominalFieldProved=False,
        stopAndClearDisposeBeforeZero88=True,blackboardClearAllOriginalNoOp=True,
        completeFieldWriterCensusProved=False,crossCallBlackboardStabilityProved=False,
        lifetimeProved=False,runtimeBlackboardIdentityProved=False)


def _same(a,b):return json.dumps(a,sort_keys=True,allow_nan=False)==json.dumps(b,sort_keys=True,allow_nan=False)


def _programs(c):
    fields={r['id']:r for r in c['fields']};off={key:r['offset']for key,r in fields.items()};spans={r['id']:r for r in c['spans']};op=c['operands']
    required={'refreshPrefix','refreshBody','refreshReplacement','barrier','machinePrefix','machineFirstMap','machineSecondMap','machineSourceTail','machineCold1','machineCold2'}
    _require(set(spans)==required and len(spans)==len(c['spans']),'lifecycle-program-coverage',sorted(required),sorted(spans))
    _require(all(type(v)is int for v in op.values()),'lifecycle-operand-types','ordinary integer operands',op)
    h=bytes.fromhex;F=lambda key,width=1:('field',key,width);O=lambda key,width=1:('operand',key,width);R=lambda key,width=4:('relative',key,width)
    targets={**op,'barrierEnabledRelativeEnd':op['barrierEnabledCell']-1}
    def check(key,parts):
        row=spans[key];raw=bytes.fromhex(row['hex']);_require(_match(raw,row['rva'],parts,off,op,targets),'lifecycle-finite-program',key,raw.hex())
    check('refreshPrefix',[h('4883ec'),O('refreshFrame'),h('488b05'),R('refreshTypeInfoCell'),h('4c8bd14c8bda488b48'),O('refreshDispatchOffset'),h('4885c90f85'),R('refreshReplacementRva')])
    check('refreshBody',[h('498d4a'),F('ai'),h('4d895a'),F('ai'),h('e8'),R('barrierRva'),h('4d85db74'),R('refreshNullRva',1),h('498b43'),F('aiEntity'),h('498d4a'),F('entity'),h('498942'),F('entity'),h('4883c4'),O('refreshFrame'),h('e9'),R('barrierRva'),h('4883c4'),O('refreshFrame'),h('c3e8'),R('nullHelperRva'),h('cc')])
    check('refreshReplacement',[h('488b81'),O('replacementFunctionOffset',4),h('4885c00f84'),R('refreshOrdinaryRva'),h('488b89'),O('replacementContextOffset',4),h('4d8bc84d8bc3498bd2ffd090e9'),R('refreshReturnRva')])
    # Complete closed leaf. No instruction writes R10/R11 and there are no
    # calls. The CAS backedge and enabled-flag branch remain inside this span.
    check('barrier',[h('833d'),R('barrierEnabledRelativeEnd'),h('004c8bc174'),R('barrierRetRva',1),h('49c1e8'),O('barrierAddressShift'),h('488d0d'),R('barrierBitmapBase'),h('4181e0'),O('barrierIndexMask',4),h('418bc048c1e8'),O('barrierWordShift'),h('4183e0'),O('barrierBitMask'),h('488d14c10f0d0a488b02488bc84c0fabc1f0480fb10a75'),R('barrierLoopRva',1),h('c3')])
    check('machinePrefix',[h('48895c24'),O('machineSaveRbx'),h('48896c24'),O('machineSaveRbp'),h('48897424'),O('machineSaveRsi'),h('574883ec'),O('machineFrame'),h('488bf9488bea498b48'),O('methodInfoClassOffset'),h('ba'),O('firstResolverSlot',4),h('498bd8488b89'),O('classContextOffset',4),h('e8'),R('physicalResolverRva'),h('488bc8e8'),R('physicalAllocatorRva'),h('488bf04885c00f84'),R('machineNullRva')])
    check('machineFirstMap',[h('4c8b43'),O('methodInfoClassOffset'),h('498b90'),O('classContextOffset',4),h('488b4a'),O('firstCtorContextOffset'),h('488379'),O('classInitFlagOffset'),h('000f84'),R('machineCold1Rva'),h('488b43'),O('methodInfoClassOffset'),h('488bce488b90'),O('classContextOffset',4),h('488b52'),O('firstCtorContextOffset'),h('e8'),R('physicalMapCtorRva'),h('488d4f'),O('machineMapField1'),h('488977'),O('machineMapField1'),h('e8'),R('barrierRva')])
    check('machineSecondMap',[h('488b4b'),O('methodInfoClassOffset'),h('ba'),O('secondResolverSlot',4),h('488b89'),O('classContextOffset',4),h('e8'),R('physicalResolverRva'),h('488bc8e8'),R('physicalAllocatorRva'),h('488bf04885c074'),R('machineNullRva',1),h('488b4b'),O('methodInfoClassOffset'),h('488b91'),O('classContextOffset',4),h('488b4a'),O('secondCtorContextOffset'),h('488379'),O('classInitFlagOffset'),h('000f84'),R('machineCold2Rva'),h('488b43'),O('methodInfoClassOffset'),h('488bce488b90'),O('classContextOffset',4),h('488b52'),O('secondCtorContextOffset'),h('e8'),R('physicalMapCtorRva'),h('488d4f'),O('machineMapField2'),h('488977'),O('machineMapField2'),h('e8'),R('barrierRva')])
    # Source RDX was saved to nonvolatile RBP. Every intervening local GP
    # destination above excludes RBP/RDI; opaque normal calls use Win64 ABI.
    # _match operands have explicit names; computed restore offsets are kept
    # separate from native field declarations.
    derived={**op,**{key+'Restore':op['machineFrame']+8+op[key]for key in('machineSaveRbx','machineSaveRbp','machineSaveRsi')}}
    tail=[h('488d4f'),O('machineSourceOffset'),h('48896f'),O('machineSourceOffset'),h('488b5c24'),O('machineSaveRbxRestore'),h('488b6c24'),O('machineSaveRbpRestore'),h('488b7424'),O('machineSaveRsiRestore'),h('4883c4'),O('machineFrame'),h('5fe9'),R('barrierRva'),h('e8'),R('nullHelperRva'),h('cc')]
    r=spans['machineSourceTail'];_require(_match(bytes.fromhex(r['hex']),r['rva'],tail,off,derived,derived),'lifecycle-source-tail','saved original argument store then barrier tail',r)
    check('machineCold1',[h('ff1190e9'),R('machineMap1ResumeRva')])
    check('machineCold2',[h('488b4b'),O('methodInfoClassOffset'),h('488b91'),O('classContextOffset',4),h('488b4a'),O('secondCtorContextOffset'),h('ff1190e9'),R('machineMap2ResumeRva')])
    end=lambda key:spans[key]['rva']+len(bytes.fromhex(spans[key]['hex']))
    _require(spans['refreshPrefix']['rva']==c['method']['identity'][3]and end('refreshPrefix')==spans['refreshBody']['rva']==op['refreshOrdinaryRva']and spans['refreshReplacement']['rva']==op['refreshReplacementRva'],'lifecycle-refresh-joins','entry and original/replacement entries',spans)
    _require(spans['barrier']['rva']==op['barrierRva']and op['barrierRetRva']==end('barrier')-1 and op['barrierLoopRva']==end('barrier')-18,'lifecycle-barrier-closed-cfg','terminal RET and CAS retry beginning',op)
    for left,right in [('machinePrefix','machineFirstMap'),('machineFirstMap','machineSecondMap'),('machineSecondMap','machineSourceTail')]:_require(end(left)==spans[right]['rva'],'lifecycle-machine-continuity',left,right)
    _require(spans['machinePrefix']['rva']==op['machineEntryRva']and spans['machineCold1']['rva']==op['machineCold1Rva']and spans['machineCold2']['rva']==op['machineCold2Rva'],'lifecycle-machine-entry-cold','same selected physical program',spans)
    for key in('ai','entity'):_require(off[key]>=off['bb']+8 or off[key]+8<=off['bb'],'lifecycle-no-bb-store-overlap','AI/entity writes disjoint from BB reference field',off)
    _require(_same(c['rules'],_rules()),'lifecycle-rules',_rules(),c['rules'])
    return dict(refreshEntryRva=c['method']['identity'][3],physicalMachineEntryRva=op['machineEntryRva'],physicalSourceOffset=op['machineSourceOffset'],barrierEntryRva=op['barrierRva'])


def _validate(image,c,deps):
    cx=NativeReferenceContext(image)
    validate_reference_ancestor_chain(cx,'Beyond.Gameplay.AI.CharacterAIComponent',['Beyond.Gameplay.AI.AIComponent','Beyond.Gameplay.Core.TickComponent','Beyond.Gameplay.Core.BaseComponent'],'Beyond.Gameplay.Core.BaseComponent')
    fields=_validate_fields(image,c['fields']);_require(_same(c['fields'],deps['fsm']['fields']),'lifecycle-field-dependency','same independently typed state fields',c['fields'])
    props={}
    for key,r in fields.items():
        td=image.named_types[r['type']];f=next(f for f in image.metadata.fields_for(td)if image.metadata.string(f.name_index)==r['name']);attrs=cx.field_attributes(f.type_index);props[key]=dict(attributes=attrs,initOnly=bool(attrs&32),static=bool(attrs&16))
    _require(_same(props,c['fieldProperties'])and props['bb']['initOnly']is False,'lifecycle-field-attributes','metadata properties; state BB is not readonly',props)
    row=c['method'];index=image.validate_method_row(row['identity'],label='skillCenterLifecycle');method=image.metadata.methods[index]
    _require(row['identity'][1:3]==['Beyond.Gameplay.AI.CharacterMainCtrlSystem+CenterStateBase','RefreshData']and cx.type_name(method.return_type)=='void'and not method.flags&16 and [dict(name=image.metadata.string(p.name_index),type=cx.type_name(p.type_index))for p in image.metadata.parameters_for(method)]==row['parameters'],'lifecycle-refresh-signature','named instance RefreshData',row)
    image.check_windows(c['codeWindows'],label='skillCenterLifecycle')
    for owner,start in [('refresh',row['identity'][3]),('machine',c['operands']['machineEntryRva'])]:
        actual=sorted(r['runtimeTriple'][:2]for r in image.unwind_index.family(start)['ranges']);declared=sorted([r['startRva'],r['endRva']]for r in c['codeWindows']if r['owner']==owner)
        _require(actual==declared,'lifecycle-complete-family',actual,declared)
    for owner in ('refresh','machine','barrier'):
        spans=sorted((r['rva'],r['rva']+len(bytes.fromhex(r['hex'])),r)for r in c['spans']if r['owner']==owner);used=set()
        for w in sorted((r for r in c['codeWindows']if r['owner']==owner),key=lambda r:r['startRva']):
            at=w['startRva']
            for a,b,r in spans:
                if at<=a<w['endRva']:
                    _require(a==at and b<=w['endRva']and image.pe.bytes_at_va(image.pe.image_base+a,b-a)==bytes.fromhex(r['hex']),'lifecycle-complete-span-bytes',r,w);at=b;used.add(r['id'])
            _require(at==w['endRva'],'lifecycle-complete-span-coverage',w,at)
        _require(used=={r['id']for r in c['spans']if r['owner']==owner},'lifecycle-owned-spans',owner,used)
    fsm_rules,_=fsm_native._validate(image,deps['fsm'])
    consumer_rules=consumer_native._validate(image,deps['consumer'])
    image.check_windows(deps['getter']['codeWindows'],label='skillCenterLifecycleGetter');getter_facts=getter_native._programs(deps['getter'])
    _require(c['operands']['machineEntryRva']==deps['fsm']['operands']['physicalMachineBaseCtorRva']and c['operands']['machineSourceOffset']==getter_facts['sourceSlotOffset'],'lifecycle-physical-slot-join','supplied physical constructor and getter source-offset equality',getter_facts)
    _require(consumer_rules['stopAndClearDisposeBeforeDirectZero88']is True and consumer_rules['blackboardClearAllOriginalNoOp']is True,'lifecycle-clear-dependency','selected typed BB clear programs',consumer_rules)
    return dict(rules=_rules(),localProgram=_programs(c),fieldProperties=props,dependencyBoundaries=dict(fsm=fsm_rules,getterSourceNamedFieldProved=False,consumerSameLiveBBProved=consumer_rules['sameWriterConsumerLiveBlackboardProved']))


def load_skill_center_lifecycle(*,gameassembly,metadata,contract_path=CONTRACT_PATH):
    path=Path(contract_path);audit=dict(schema=AUDIT_SCHEMA,status='validation_failed',rules={},rows=[],nativeInputs={},failures=[])
    try:
        c,digest=read_reviewed_contract(path,schema=SCHEMA,status='reviewed',label='skillCenterLifecycle');saved=[(path,digest)];deps={};names=dict(fsm='skill_center_fsm_native.json',getter='skill_blackboard_getter_native.json',consumer='skill_blackboard_consumer_native.json')
        _require(c['dependencies']==names,'lifecycle-dependency-names',names,c['dependencies'])
        for key,module in [('fsm',fsm_native),('getter',getter_native),('consumer',consumer_native)]:
            dep=CONTRACTS_DIR/names[key];value,sha=read_reviewed_contract(dep,schema=module.SCHEMA,status='reviewed',label='skillCenterLifecycle');_require(_same(value['nativeInputs'],c['nativeInputs']),'lifecycle-dependency-native-inputs','same selected build',key);deps[key]=value;saved.append((dep,sha))
        pins=c['nativeInputs'];gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata);audit.update(status=gate.status,detail=gate.detail)
        if gate.status!='validated':return audit
        result=_validate(open_native_image(gate.gameassembly,gate.metadata),c,deps);after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
        _require(after.status=='validated'and all(hashlib.sha256(p.read_bytes()).hexdigest().upper()==sha for p,sha in saved),'lifecycle-input-bookends','native inputs and all consumed declarations unchanged',after.status)
        audit.update(status='validated-conditional-lifecycle',detail='',nativeInputs=pins,evidenceBoundary=c['evidenceBoundary'],**result);audit['rows']=[dict(id='centerLifecycleLocalEffects',evidence='conditional',rules=result['rules'])]
    except(OSError,ValueError,KeyError,IndexError,TypeError,RuntimeError,struct.error,OverflowError)as error:audit.update(status='validation_failed',detail=str(error)[:1600],rules={},rows=[],nativeInputs={},failures=[dict(check=str(error).split(':',1)[0],detail=str(error)[:1600])])
    return audit


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    for key in('gameassembly','metadata'):parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--contract',type=Path,default=CONTRACT_PATH);parser.add_argument('--output',type=Path,default=REPO_ROOT/'reports/game_data/skill_center_lifecycle_native.json');args=parser.parse_args(argv)
    _require(args.output.resolve().is_relative_to((REPO_ROOT/'reports').resolve()),'lifecycle-output-root','reports/',args.output)
    result=load_skill_center_lifecycle(gameassembly=args.gameassembly,metadata=args.metadata,contract_path=args.contract)
    if result['status']=='validated-conditional-lifecycle':args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result));return 0 if result['status']=='validated-conditional-lifecycle'else 2


if __name__=='__main__':raise SystemExit(main())
