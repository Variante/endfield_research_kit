"""Current conditional positive instance transfer, with explicit creation gap.

This gate authenticates the instance's own complete entry/return paths and
additional adapter/provider/Activator contexts. It proves argument and slot
ownership under the selected compatible RuntimeType/cache/provider results
and normal calls. The concrete wrappers' metadata mask selects the creation
branch if returned runtime attributes describe those same classes. Neither
the attribute/class bridge nor Activator construction/global effects is
observed, and this lane is kept outside stored list/root admission.
"""
from __future__ import annotations

import hashlib,json
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.formatter_composition import validate_registered_formatter_composition,validate_generic_contexts,_vtable
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError
from scripts.game_data.memorypack.reference_nullable_sources import validate_reference_adapter_abi
from scripts.game_data.memorypack.reference_conversion_sources import validate_conversion_context,validate_formatter_dispatch,validate_interface_conversion
from scripts.game_data.memorypack.reference_instance_sources import (
    validate_type_key_byref_liveness,validate_instance_context,
    validate_type_flags_dispatch,validate_positive_instance_transfer)

LABEL='buffTimelineInstance'
SCHEMA='endfield.buff-timeline-instance-native-contract.v1'
SCOPE='buffered-positive-instance-owned-transfer-only'
CONTRACT_PATH=CONTRACTS_DIR/'buff_timeline_instance_native.json'


def _fail(check: str,expected: Any,actual: Any) -> None:
    error=CensusGateError(f'{LABEL}.{check}',source=CONTRACT_PATH.as_posix(),expected=str(expected)[:1024],actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL,scope=SCOPE);error.args=(json.dumps(error.diagnostic,sort_keys=True),);raise error


def _contract() -> dict:
    c,_=read_reviewed_contract(CONTRACT_PATH,schema=SCHEMA,status='exact-current-build',label=LABEL)
    if c.get('scope')!=SCOPE or set(c['programs'])!={'nonnull','nullWrapperOutput'}:
        _fail('instance-scope','two complete selected positive instance output paths',c.get('scope'))
    return c


def _validate_image(image: Any,c: dict) -> dict:
    schemas={'reference':'endfield.buff-timeline-reference-native-contract.v2',
        'static':'endfield.buff-timeline-static-composition-native-contract.v1',
        'source':'endfield.buff-timeline-element-sources-native-contract.v1'}
    deps={k:read_reviewed_contract(CONTRACTS_DIR/c['dependencies'][k],schema=s,status='exact-current-build',label=LABEL)[0]for k,s in schemas.items()}
    if any(d['nativeInputs']!=c['nativeInputs']for d in deps.values()):_fail('instance-dependency-build',c['nativeInputs'],deps)
    reference,static,source=(deps[k]for k in ('reference','static','source'))
    validate_registered_formatter_composition(image,static['composition'],label=LABEL)
    validate_generic_contexts(image,c['methodContexts'],label=LABEL)
    selected=NativeReferenceContext(image);entries=GenericEntries(image)
    adapter=next(r for r in reference['sharedEntries']if not r['nonnull'])
    helper=next(r for r in reference['sharedEntries']if r['nonnull'])
    actual=entries.resolve(adapter['method'][0],adapter['classArguments'],adapter['methodArguments'])
    if json.loads(json.dumps(actual))!=adapter['registration']:_fail('instance-physical-registration',adapter['registration'],actual)
    validate_reference_adapter_abi(image,adapter['method'],nonnull=False,fail=_fail)
    entry=actual['pointer']-image.pe.image_base
    if any(p['codeWindows'][0]['startRva']!=entry for p in c['programs'].values()):_fail('instance-physical-entry',entry,c['programs'])
    context=next(r for r in static['composition']['genericContexts']if r['typeName']==adapter['method'][1]and not r['isMethod'])
    conversion_context=validate_conversion_context(image,context,entries,fail=_fail)
    method_context=validate_instance_context(image,context,c['methodContexts'],entries,helper['method'][0],fail=_fail)
    activation=c['activatorEntry'];slot=next(r for r in context['entries']if r['relativeSlot']==11)
    if activation['method'][0]!=slot['methodSpec'][0]or activation['classArguments']!=[]or activation['methodArguments']!=['object']:
        _fail('instance-activator-declaration','same owned CreateInstance with independent Object physical selection',activation)
    image.validate_method_row(activation['method'],label=LABEL)
    result=entries.resolve(activation['method'][0],activation['classArguments'],activation['methodArguments'])
    if json.loads(json.dumps(result))!=activation['registration']or result['pointer']-image.pe.image_base!=c['calls']['activator']:
        _fail('instance-actual-activator-target','actual call equals independently owned shared Object entry',result)
    getter=c['typeFlagsGetter'];image.validate_method_row(getter['method'],label=LABEL)
    m=image.metadata.methods[getter['method'][0]];td=selected.index.types[getter['method'][1]]
    if m.slot!=66 or selected.type_name(m.return_type)!='System.Reflection.TypeAttributes':
        _fail('instance-type-attributes-declaration','owned RuntimeType TypeAttributes slot 66',getter)
    _vtable(image,td.index,66,m.index,LABEL)
    flags=validate_type_flags_dispatch(image,c['typeFlagsDispatch'],getter['method'][3],fail=_fail)
    if flags['calls']['typeKey']!=c['calls']['typeKey']or c['typeFlagsDispatch']['program'][0][0]!=c['calls']['typeFlags']:
        _fail('instance-type-key-call-join','same actual type-key/flags helpers',flags)
    liveness=validate_type_key_byref_liveness(image,c['typeKeyByrefLiveness'],fail=_fail)
    if liveness['entryRva']!=c['calls']['typeKey']:_fail('instance-live-type-key-entry',c['calls']['typeKey'],liveness)
    wrappers={r['wrapperType']:r for r in static['composition']['registrations']}
    if len(c['wrapperMetadataFlags'])!=2 or {r['wrapperType']for r in c['wrapperMetadataFlags']}!=set(wrappers):
        _fail('instance-wrapper-flags-bijection','two independently registered concrete wrappers',c['wrapperMetadataFlags'])
    for row in c['wrapperMetadataFlags']:
        actual=selected.index.types[row['wrapperType']]
        if actual.index!=row['definition']or actual.flags!=row['flags']or actual.flags&0x80 or selected.is_value_type(row['wrapperType']):
            _fail('instance-concrete-wrapper-mask','reference wrappers with bit 0x80 clear',row)
    dispatch=validate_formatter_dispatch(image,reference['conversionPrograms']['formatterDispatch'],[r['formatterMethod'][3]for r in static['wrapperConversions']],fail=_fail)
    conversion=validate_interface_conversion(image,reference['conversionPrograms']['interfaceConversion'],[r['getterMethod'][3]for r in static['wrapperConversions']],fail=_fail)
    if any(c['calls'][k]!=reference['conversionCalls'][k]for k in ('formatterResult','formatterDispatch','interfaceConversion')):
        _fail('instance-conversion-helper-join','same independently proved concrete dispatch/getter helpers',c['calls'])
    offsets=source['readerFieldsUnboxedOffsets']
    if offsets!={n:selected.field('MemoryPack.MemoryPackReader::'+n)[2]-16 for n in offsets}:
        _fail('instance-reader-layout','source-owned actual unboxed Reader fields',offsets)
    transfers={k:validate_positive_instance_transfer(image,p,c['calls'],offsets,null_wrapper=k=='nullWrapperOutput',fail=_fail)for k,p in c['programs'].items()}
    return {'ownedConversionContext':conversion_context,'additionalMethodContexts':method_context,
        'conditionalTypeFlags':flags,'typeKeyByrefLivenessPrefix':liveness,
        'wrapperMetadataMaskClear':True,'actualActivatorEntryMatched':True,
        'formatterDispatch':dispatch,'interfaceConversion':conversion,'positiveInstanceTransfers':transfers,
        'activatorConstructionEffects':'unresolved','runtimeTypeFlagsMetadataBridge':'conditional'}


def validate_current_native_contract(*,gameassembly: Path | None=None,metadata: Path | None=None) -> dict:
    c=_contract();pins=c['nativeInputs']
    gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
    if gate.status!='validated':return {'status':gate.status,'detail':gate.detail,'nativeInputs':pins,'scope':SCOPE}
    unity=Path(gate.gameassembly).parent/'UnityPlayer.dll'
    def unity_matches():return unity.is_file()and hashlib.sha256(unity.read_bytes()).hexdigest().upper()==pins['UnityPlayer.dll']
    if not unity_matches():return {'status':'mismatched'if unity.is_file()else 'missing','detail':'UnityPlayer.dll missing or mismatched','nativeInputs':pins,'scope':SCOPE}
    try:summary=_validate_image(open_native_image(gate.gameassembly,gate.metadata),c)
    except ValueError as error:
        if isinstance(error,CensusGateError):raise
        _fail('native-instance-transfer','current complete instance ABI/context/value paths',str(error))
    after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
    if after.status!='validated'or not unity_matches():return {'status':after.status if after.status!='validated'else 'mismatched','detail':'native inputs changed during instance validation','nativeInputs':pins,'scope':SCOPE}
    return {'status':'validated','scope':SCOPE,'nativeInputs':pins,'summary':summary,
        'positiveListAdmitted':False,'wholeRootAdmitted':False,'runtimeMeaningExact':False,'evidenceBoundary':c['evidenceBoundary']}
