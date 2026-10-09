"""Root list ReadPackable and new-list selected native control, below admission."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from typing import Any
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.formatter_composition import validate_generic_contexts
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError
from scripts.game_data.memorypack import buff_timeline_empty_native as root
from scripts.game_data.memorypack import buff_timeline_list as lists
from scripts.game_data.memorypack import buff_timeline_read_value as read_value
from scripts.game_data.memorypack import buff_timeline_source_wrappers as wrappers
from scripts.game_data.memorypack.packable_reference_sources import (
    validate_packable_context,validate_packable_transfer,validate_root_list_field_transfer)
from scripts.game_data.memorypack.new_list_reference_sources import (
    validate_capacity_constructor_context,validate_capacity_constructor_programs,validate_new_reference_list)
from scripts.game_data.memorypack.reference_conversion_sources import validate_formatter_dispatch
from scripts.game_data.memorypack.buffered_reference_wrappers import validate_fast_reference_barrier

LABEL='buffTimelineRootList'
SCHEMA='endfield.buff-timeline-root-list-native-contract.v1'
SCOPE='root-local-readpackable-and-new-reference-list-control-only'
CONTRACT_PATH=CONTRACTS_DIR/'buff_timeline_root_list_native.json'


def _fail(check: str,expected: Any,actual: Any) -> None:
    error=CensusGateError(f'{LABEL}.{check}',source=CONTRACT_PATH.as_posix(),
        expected=str(expected)[:1024],actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL,scope=SCOPE)
    error.args=(json.dumps(error.diagnostic,sort_keys=True),);raise error


def _contract() -> dict:
    c,_=read_reviewed_contract(CONTRACT_PATH,schema=SCHEMA,status='exact-current-build',label=LABEL)
    if (c.get('scope')!=SCOPE or set(c['dependencies'])!={'root','existingList','readValue','sourceWrappers'}
            or set(c['newListPrograms'])!={'nullList','emptyNewList','singleElement','twoElements'}
            or set(c['constructorPrograms'])!={'zero','positive'}):
        _fail('root-list-scope','complete root helper, four list paths and two capacity constructor paths',c.get('scope'))
    return c


def _validate_image(image: Any,c: dict) -> dict:
    schemas={'root':root.SCHEMA,'existingList':lists.SCHEMA,'readValue':read_value.SCHEMA,'sourceWrappers':wrappers.SCHEMA}
    deps={k:read_reviewed_contract(CONTRACTS_DIR/c['dependencies'][k],schema=s,status='exact-current-build',label=LABEL)[0]
        for k,s in schemas.items()}
    if any(d['nativeInputs']!=c['nativeInputs']for d in deps.values()):
        _fail('dependency-build','all selected native dependencies describe the same build',c['nativeInputs'])
    list_result=lists._validate_image(image,deps['existingList'])
    value_result=read_value._validate_image(image,deps['readValue'])
    entries=GenericEntries(image);selected=NativeReferenceContext(image);source=deps['root']
    root._check_context(image,source['listSourceContext'])
    for m in source['methods']:image.validate_method_row(m,label=LABEL)
    field=selected.field(source['ownerType']+'::'+source['timelineField'])
    if field[:2]!=(source['ownerType'],source['timelineFieldType']):
        _fail('root-list-field-type','same concrete original timeline list field',field)
    validate_generic_contexts(image,[c['packableContext'],c['capacityClassContext']],label=LABEL)
    context=validate_packable_context(image,c['packableContext'],
        value_result['ownedReadValueContext']['readerMethodDefinition'],entries,fail=_fail)
    if source['listSourceContext']['methodSpec'][:2]!=[context['packableDefinition'],-1]:
        _fail('root-packable-context','same declared root method parameter binding',source['listSourceContext'])
    independent=c['independentPackableObjectEntry']
    actual=entries.resolve(context['packableDefinition'],[],['object'])
    if (json.loads(json.dumps(actual))!=independent['registration']
            or actual['pointer']-image.pe.image_base==source['listReadTargetRva']
            or independent['matchedActualRootCall']is not False):
        _fail('packable-independent-entry-gap','separately authenticated Object entry differs from actual root target',independent)
    packable=c['packableProgram']
    if packable['program'][0][0]!=source['listReadTargetRva']:
        _fail('actual-root-helper-entry',source['listReadTargetRva'],packable['program'][0])
    expected_calls={k:deps['readValue']['calls'][k]for k in
        ('typeKey','cacheHash','cacheCompare','formatterResult','formatterClassPredicate','formatterDispatch')}
    if c['packableCalls']!=expected_calls:_fail('packable-physical-dependencies',expected_calls,c['packableCalls'])
    transfer=validate_packable_transfer(image,packable,c['packableCalls'],fail=_fail)
    reference=read_reviewed_contract(CONTRACTS_DIR/deps['readValue']['dependencies']['reference'],
        schema='endfield.buff-timeline-reference-native-contract.v2',status='exact-current-build',label=LABEL)[0]
    if reference['nativeInputs']!=c['nativeInputs']:_fail('reference-build',c['nativeInputs'],reference['nativeInputs'])
    list_entry=deps['existingList']['programs']['singleElement']['program'][0][0]
    fallback=validate_formatter_dispatch(image,reference['conversionPrograms']['formatterDispatch'],[list_entry],fail=_fail)
    root_prefix=json.loads((CONTRACTS_DIR/root.ROOT_CONTRACT_PATH.name).read_bytes())
    if c['rootFieldTransfer']['window']!=root_prefix['codeWindows'][0]:
        _fail('root-local-window-owner','same independently authenticated named root source window',c['rootFieldTransfer']['window'])
    local=validate_root_list_field_transfer(image,c['rootFieldTransfer'],source['listSourceContext'],
        source['listReadTargetRva'],field[2],fail=_fail)
    static=read_reviewed_contract(CONTRACTS_DIR/deps['existingList']['dependencies']['staticComposition'],
        schema='endfield.buff-timeline-static-composition-native-contract.v1',status='exact-current-build',label=LABEL)[0]
    formatter_context=next(r for r in static['composition']['genericContexts']if r['typeName']=='MemoryPack.Formatters.ListFormatter`1')
    capacity_context=validate_capacity_constructor_context(image,formatter_context,c['capacityClassContext'],entries,fail=_fail)
    ctor=c['independentConstructorObjectEntry']
    actual=entries.resolve(capacity_context['constructorDefinition'],['object'],[])
    if (json.loads(json.dumps(actual))!=ctor['registration']or ctor['matchedActualCall']is not True
            or actual['pointer']-image.pe.image_base!=c['newListCalls']['capacityConstructor']):
        _fail('capacity-physical-body-owner','actual constructor equals separately registered shared List constructor',ctor)
    entry=c['newListCalls']['capacityConstructor']
    if any(p['program'][0][0]!=entry for p in c['constructorPrograms'].values()):
        _fail('capacity-entry-owner',entry,c['constructorPrograms'])
    capacity=validate_capacity_constructor_programs(image,c['constructorPrograms'],c['arrayAllocationCall'],fail=_fail)
    if any(p['codeWindows']!=deps['existingList']['programs']['singleElement']['codeWindows']for p in c['newListPrograms'].values()):
        _fail('new-list-physical-window-owner','same independently authenticated ListFormatter windows',c['newListPrograms'])
    new_list=validate_new_reference_list(image,c['newListPrograms'],deps['existingList']['programs']['singleElement'],c['newListCalls'],fail=_fail)
    barrier=validate_fast_reference_barrier(image,deps['sourceWrappers']['barrierProgram'],fail=_fail)
    if new_list['outputDisabledBarrierFlagRva']!=barrier['disabledFlagRva']:
        _fail('new-list-output-barrier','same independently proved disabled output barrier flag',new_list)
    if capacity['disabledBarrierFlagRva']!=barrier['disabledFlagRva']:
        _fail('capacity-output-barrier-join','same actual constructor/list/output disabled barrier flag',capacity)
    return {'rootListType':field[1],'ownedPackableContext':context,'actualPackableTransfer':transfer,
        'namedPackableBodyIdentity':'unresolved','listFormatterOrdinaryFallback':fallback,'localRootFieldTransfer':local,
        'capacityConstructorContext':capacity_context,'capacityConstructorReturns':capacity,
        'actualConstructorMatchesIndependentSharedEntry':True,'newReferenceListControl':new_list,
        'priorExistingListLoop':list_result['bufferedReferenceLoop'],
        'allocatedObjectInitialCountAndArrayCapacity':'conditional',
        'originalTimelineElementCursorComposition':'unresolved','wholeRootEntryAndTailComposition':'unresolved'}


def validate_current_native_contract(*,gameassembly: Path | None=None,metadata: Path | None=None) -> dict:
    c=_contract();pins=c['nativeInputs']
    gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
    if gate.status!='validated':return {'status':gate.status,'detail':gate.detail,'scope':SCOPE,'nativeInputs':pins}
    unity=Path(gate.gameassembly).parent/'UnityPlayer.dll'
    def unity_matches():return unity.is_file()and hashlib.sha256(unity.read_bytes()).hexdigest().upper()==pins['UnityPlayer.dll']
    if not unity_matches():return {'status':'mismatched'if unity.is_file()else'missing',
        'detail':'UnityPlayer.dll missing or mismatched','scope':SCOPE,'nativeInputs':pins}
    try:summary=_validate_image(open_native_image(gate.gameassembly,gate.metadata),c)
    except ValueError as error:
        if isinstance(error,CensusGateError):raise
        _fail('native-root-list-transfer','complete current owned contexts and selected source/helper/list/constructor programs',str(error))
    after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
    if after.status!='validated'or not unity_matches():return {'status':after.status if after.status!='validated'else'mismatched',
        'detail':'native inputs changed during root list validation','scope':SCOPE,'nativeInputs':pins}
    return {'status':'validated','scope':SCOPE,'nativeInputs':pins,'summary':summary,
        'childSchemaAdmitted':False,'positiveListAdmitted':False,'wholeRootAdmitted':False,'runtimeMeaningExact':False,
        'evidenceBoundary':c['evidenceBoundary']}
