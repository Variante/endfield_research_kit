"""Validate selected MoveTo runtime defaults and existing-wrapper callbacks."""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.context import type_parameter_owner
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract,NATIVE_MAPPER_PATH,METADATA_HELPER_PATH
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError,_fingerprint,_package_import_closure
from scripts.game_data.memorypack import runtime_constructor_sources as constructors
from scripts.game_data.memorypack import inherited_reference_sources as ancestry
from scripts.game_data.memorypack.buffered_reference_wrappers import validate_fast_reference_barrier
from scripts.game_data.memorypack.buffered_wrapper_lifecycle_sources import _profile,_branch

LABEL='buffMoveToRuntimeDefaults'
SCHEMA='endfield.buff-move-to-runtime-defaults-native-contract.v1'
CONTRACT_PATH=CONTRACTS_DIR/'buff_move_to_runtime_defaults_native.json'
DEPENDENCY_SCHEMAS={'lifecycle':'endfield.buff-move-to-lifecycle-native-contract.v1',
    'blackboardData':'endfield.memorypack-blackboard-double-data-native-contract.v1',
    'barrier':'endfield.buff-timeline-source-wrappers-native-contract.v1'}


def _fail(check: str,expected: Any,actual: Any,**scope: Any) -> None:
    error=CensusGateError(f'{LABEL}.{check}',source=CONTRACT_PATH.as_posix(),expected=str(expected)[:1800],actual=str(actual)[:2200])
    error.diagnostic.update(validator=LABEL,check=check,scope=scope)
    error.args=(json.dumps(error.diagnostic,sort_keys=True),);raise error


def _contract() -> dict:
    c,_=read_reviewed_contract(CONTRACT_PATH,schema=SCHEMA,status='exact-current-build',label=LABEL)
    if (set(c.get('dependencies',{}))!=set(DEPENDENCY_SCHEMAS) or
        any(not isinstance(n,str) or Path(n).name!=n or '/' in n or '\\' in n or not n.endswith('_native.json') for n in c['dependencies'].values()) or
        set(c.get('records',{}))!={'moveTo','subSpeed','blackboardZero','blackboardSingle','target','vector','curve','preparation'}):
        _fail('contract-scope','named dependencies and all selected constructor/callback records',list(c.get('records',{})))
    return c


def _closed_float_cell(image: Any,c: dict,dependency: dict) -> dict:
    p=dependency['closedScalarFields'];runtime=ancestry._ancestry(image,p['runtimeTypeDefinition'])
    wrappers=ancestry._ancestry(image,dependency['record']['wrapperTypeDefinition'])
    ancestry._ancestry_matches(runtime,p['runtimeAncestry'],_fail)
    ancestry._ancestry_matches(wrappers,p['wrapperAncestry'],_fail)
    closed=[r['parent'] for r in runtime if r['parent'] and r['parent']['kind']==0x15]
    slots=[(r,f) for r in wrappers for f in r['fields'] if f['type']['kind']==0x15]
    if len(closed)!=1 or len(slots)!=1:_fail('closed-float-carriers',[1,1],[len(closed),len(slots)])
    closed=closed[0];owner,slot=slots[0]
    if any(closed[k]!=slot['type'][k] for k in ('definition','instanceIndex','arguments')):
        _fail('closed-float-same-instance',closed,slot['type'])
    value=[f for r in runtime for f in r['fields'] if f['name']=='value']
    if len(value)!=1 or value[0]['type']['kind']!=0x13:_fail('closed-float-declared-value','one owned VAR value',value)
    identity=type_parameter_owner(image.metadata.buf,int.from_bytes(bytes.fromhex(value[0]['type']['rawHex'])[:8],'little'),
        [td.generic_container_index for td in image.metadata.types],source=LABEL)
    if (identity!=p['valueParameterOwner'] or identity['ordinal']!=0 or identity['typeIndex']!=closed['definition'] or
            [r['name'] for r in closed['arguments']]!=['float','double']):
        _fail('closed-float-variable-owner',p['valueParameterOwner'],identity)
    setter=p['setters']['value'];method=setter['method'];image.validate_method_row(method,label=LABEL)
    parameters=list(image.metadata.parameters_for(image.metadata.methods[method[0]]))
    if len(parameters)!=1 or ancestry._type_row(image,parameters[0].type_index)['pointerRva']!=closed['arguments'][0]['pointerRva']:
        _fail('closed-float-setter-parameter','same closed Float32 argument',method)
    offset=setter['destinationOffset'];instance_offset=owner['offsets'][slot['name']]
    if (c['blackboardFloatCell']!={'runtimeTypeDefinition':p['runtimeTypeDefinition'],'valueOffset':offset,'typeName':'float',
                                'meaning':'same concrete cell as the reviewed closed value setter'} or
            not 0<=offset<128 or not 0<=instance_offset<128):
        _fail('closed-float-cell','same owned setter cell with bounded displacement',c['blackboardFloatCell'])
    proof={'program':setter['program'],'codeWindows':[setter['window']]}
    rr=_profile(image,proof,['4883EC28',f'488B41{instance_offset:02X}','4885C0',None,
        f'F30F1148{offset:02X}','4883C428','C3'],fail=_fail)
    _branch(rr,3,b'\x74',False,fail=_fail)
    return {'offset':offset,'typeName':'float','carrier':closed['name'],'openGenericOffsetsUsed':False}


def _validate_image(image: Any,c: dict,deps: dict) -> dict:
    selected=NativeReferenceContext(image);records=c['records'];life=deps['lifecycle']
    for key,r in records.items():
        method=r['method'];image.validate_method_row(method,label=LABEL)
        md=image.metadata.methods[method[0]];parameters=[selected.type_name(p.type_index) for p in image.metadata.parameters_for(md)]
        expected=['float']*3 if key=='vector' else ['float'] if key=='blackboardSingle' else []
        if md.flags&0x10 or parameters!=expected or ancestry._type_row(image,md.return_type)['name']!='void':
            _fail('constructor-method-signature',{'parameters':expected,'instanceVoid':True},method)
        if method[2]!=('OnDeserialized' if key=='preparation' else '.ctor'):
            _fail('constructor-method-kind',key,method)
        for field in r.get('fields',[]):
            if list(selected.field(field['qualified']))!=field['field']:_fail('constructor-field-layout',field,selected.field(field['qualified']))
        for proof in r.get('proofs',{}).values() if key=='preparation' else [r['proof']]:
            if proof['program'][0][0]!=method[3]:_fail('constructor-program-entry',method,proof['program'][0])
    for field in c['directionFields']:
        if list(selected.field(field['qualified']))!=field['field']:_fail('constructor-direction-layout',field,selected.field(field['qualified']))
    for kind in ('moveTo','subSpeed'):
        if records[kind]['method']!=life['records'][kind]['runtimeConstructorMethod']:
            _fail('current-wrapper-runtime-constructor',life['records'][kind]['runtimeConstructorMethod'],records[kind]['method'])
    if (records['preparation']['method'][3]!=life['calls']['prepareExistingWrapper'] or
            records['preparation']['method'][1]!=life['records']['moveTo']['readerMethod'][1] or
            c['calls']['allocation']!=life['calls']['allocation'] or c['calls']['getterCast']!=life['calls']['getterCast']):
        _fail('current-lifecycle-call-joins','same current wrapper preparation, allocation and cast calls',c['calls'])
    cell=_closed_float_cell(image,c,deps['blackboardData'])
    bb_name=image.type_name(c['blackboardFloatCell']['runtimeTypeDefinition'])
    if any(records[k]['method'][1]!=bb_name for k in ('blackboardZero','blackboardSingle')):
        _fail('constructor-closed-blackboard-type',bb_name,[records[k]['method'] for k in ('blackboardZero','blackboardSingle')])
    barrier=deps['barrier']['barrierProgram'];fast=validate_fast_reference_barrier(image,barrier,fail=_fail)
    if fast['entryRva']!=c['calls']['barrier']:_fail('constructor-common-barrier',fast['entryRva'],c['calls']['barrier'])
    scalar=constructors.scalar_constructors(image,records,value_offset=cell['offset'],carrier=cell['carrier'],fail=_fail)
    class_ready=constructors.class_initializer_ready(image,c['classInitializerReady'],c['calls']['classInitializer'],fail=_fail)
    curve=constructors.curve_constructor(image,records['curve'],fail=_fail)
    target=constructors.target_constructor(image,records['target'],c['directionFields'],c['calls'],fast['disabledFlagRva'],fail=_fail)
    vector=constructors.vector_constructor(image,records['vector'],c['calls'],fast['disabledFlagRva'],cell['offset'],cell['carrier'],fail=_fail)
    sub=constructors.sub_speed_constructor(image,records['subSpeed'],curve,c['calls'],barrier,cell['offset'],cell['carrier'],fail=_fail)
    parent=constructors.parent_constructor(image,records['moveTo'],records,c['calls'],fail=_fail)
    prep=constructors.preparation(image,records['preparation'],c['calls'],records['moveTo']['method'][1],fail=_fail)
    nested_allocations=parent['directAllocationCalls'];native_factory_calls=0
    nested={'target':target,'vector':vector,'subSpeed':sub,'curve':curve,'blackboardZero':{'allocationCalls':0,'opaqueFactoryCalls':0},
            'blackboardSingle':{'allocationCalls':0,'opaqueFactoryCalls':0}}
    for field in parent['referenceDefaults']:
        nested_allocations+=nested[field['constructor']]['allocationCalls']
        native_factory_calls+=nested[field['constructor']]['opaqueFactoryCalls']
    key=c['curveResolverKey'];raw=bytes.fromhex(key['instructionHex'])
    image.check_instruction_windows([[key['instructionRva'],key['instructionHex']]],label=LABEL)
    if (len(raw)!=7 or raw[:3]!=b'\x48\x8d\x0d' or
            key['instructionRva']+7+int.from_bytes(raw[3:],'little',signed=True)!=key['dataRva'] or
            image.pe.bytes_at_va(image.pe.image_base+key['dataRva'],len(bytes.fromhex(key['rawHex']))).hex().upper()!=key['rawHex'] or
            bytes.fromhex(key['rawHex'])!=key['text'].encode('ascii')+b'\0'):
        _fail('curve-resolver-literal','same actual RIP resolver string argument',key)
    return {'closedFloatCell':cell,'scalarConstructors':scalar,'curveConstructor':curve,'targetConstructor':target,
            'classInitializerReady':class_ready,'curveResolverKey':key['text'],
            'vectorConstructor':vector,'subSpeedConstructor':sub,'parentConstructor':parent,'preparation':prep,
            'selectedParentNestedAllocationCalls':nested_allocations,'selectedParentOpaqueCurveFactoryCalls':native_factory_calls,
            'countsDescribeConditionalStaticPaths':True,'allocationAndFactoryEffectsProved':False,
            'finalAccumulatedInstanceStateProved':False,'wholeActionAdmitted':False,'wholeRootAdmitted':False}


def validate_current_native_contract(*,gameassembly: Path|None=None,metadata: Path|None=None) -> dict:
    c=_contract();pins=c['nativeInputs']
    gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
    if gate.status!='validated':return {'status':gate.status,'detail':gate.detail,'nativeInputs':pins}
    unity=Path(gate.gameassembly).parent/'UnityPlayer.dll'
    def unity_matches():return unity.is_file() and hashlib.sha256(unity.read_bytes()).hexdigest().upper()==pins['UnityPlayer.dll']
    if not unity_matches():return {'status':'mismatched' if unity.is_file() else 'missing','detail':'UnityPlayer.dll missing or mismatched','nativeInputs':pins}
    deps={key:read_reviewed_contract(CONTRACTS_DIR/name,schema=DEPENDENCY_SCHEMAS[key],status='exact-current-build',label=LABEL)[0]
          for key,name in c['dependencies'].items()}
    if any(d['nativeInputs']!=pins for d in deps.values()):_fail('dependency-build',pins,{k:d['nativeInputs'] for k,d in deps.items()})
    paths={CONTRACT_PATH,*(CONTRACTS_DIR/n for n in c['dependencies'].values()),*_package_import_closure(Path(__file__)),
           NATIVE_MAPPER_PATH,METADATA_HELPER_PATH,Path(gate.gameassembly),Path(gate.metadata),unity}
    sources=[_fingerprint(p) for p in sorted(paths)]
    try:summary=_validate_image(open_native_image(gate.gameassembly,gate.metadata),c,deps)
    except ValueError as error:
        if isinstance(error,CensusGateError):raise
        _fail('native-constructor-composition','complete selected programs and owned fields',str(error))
    for row in sources:
        now=_fingerprint(Path(row['path']))
        if now!=row:_fail('source-drift',row,now)
    after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
    if after.status!='validated' or not unity_matches():
        return {'status':after.status if after.status!='validated' else 'mismatched','detail':'native inputs changed during validation','nativeInputs':pins}
    return {'status':'validated','nativeInputs':pins,'proofSources':sources,'summary':summary,'evidenceBoundary':c['evidenceBoundary'],
            'wholeActionAdmitted':False,'wholeRootAdmitted':False,'runtimeExecutionKnown':False}


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gameassembly',type=Path,required=True);parser.add_argument('--metadata',type=Path,required=True)
    parser.add_argument('--report',type=Path,required=True);args=parser.parse_args();report=args.report.resolve()
    if not report.is_relative_to(Path(__file__).resolve().parents[3]/'reports'):parser.error('--report must be inside the repository reports directory')
    result=validate_current_native_contract(gameassembly=args.gameassembly,metadata=args.metadata)
    if result['status']!='validated':
        print(json.dumps({'status':result['status'],'detail':result.get('detail'),'reportPreserved':report.as_posix()}),flush=True);raise SystemExit(1)
    result.update(schema='endfield.buff-move-to-runtime-defaults-validation.v1',checkedAtUtc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    report.parent.mkdir(parents=True,exist_ok=True);report.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':result['status'],'report':report.as_posix(),'nestedAllocations':result['summary']['selectedParentNestedAllocationCalls'],
                      'opaqueFactories':result['summary']['selectedParentOpaqueCurveFactoryCalls']}),flush=True)


if __name__=='__main__':main()
