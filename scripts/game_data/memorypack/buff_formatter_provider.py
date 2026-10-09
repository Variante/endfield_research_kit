"""Actual Buff list/adapter formatter helper; typed normal return, effects open."""
from __future__ import annotations

import hashlib,json
from pathlib import Path
from typing import Any
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.formatter_composition import validate_registered_formatter_composition,validate_generic_contexts
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError
from scripts.game_data.memorypack.reference_conversion_sources import validate_conversion_context
from scripts.game_data.memorypack.reference_instance_sources import validate_instance_context
from scripts.game_data.memorypack.formatter_provider_sources import validate_provider_transfer

LABEL='buffFormatterProvider'
SCHEMA='endfield.buff-formatter-provider-native-contract.v1'
SCOPE='selected-physical-formatter-provider-context-and-return-only'
CONTRACT_PATH=CONTRACTS_DIR/'buff_formatter_provider_native.json'


def _fail(check: str,expected: Any,actual: Any) -> None:
    error=CensusGateError(f'{LABEL}.{check}',source=CONTRACT_PATH.as_posix(),expected=str(expected)[:1024],actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL,scope=SCOPE);error.args=(json.dumps(error.diagnostic,sort_keys=True),);raise error


def _contract() -> dict:
    c,_=read_reviewed_contract(CONTRACT_PATH,schema=SCHEMA,status='exact-current-build',label=LABEL)
    if c.get('scope')!=SCOPE or set(c['dependencies'])!={'instance','static'}:
        _fail('provider-scope','complete physical return plus independently owned context dependencies',c.get('scope'))
    return c


def _validate_image(image: Any,c: dict) -> dict:
    schemas={'instance':'endfield.buff-timeline-instance-native-contract.v1',
        'static':'endfield.buff-timeline-static-composition-native-contract.v1'}
    deps={k:read_reviewed_contract(CONTRACTS_DIR/c['dependencies'][k],schema=s,status='exact-current-build',label=LABEL)[0]for k,s in schemas.items()}
    if any(d['nativeInputs']!=c['nativeInputs']for d in deps.values()):_fail('dependency-build','same selected native inputs',c['nativeInputs'])
    composition=deps['static']['composition'];validate_registered_formatter_composition(image,composition,label=LABEL)
    method_contexts=deps['instance']['methodContexts'];validate_generic_contexts(image,method_contexts,label=LABEL)
    context=next(r for r in composition['genericContexts']if not r['isMethod']and r['typeName']=='Beyond.MemoryPack.GenericMemoryPackFormatter`2')
    entries=GenericEntries(image);owned=validate_conversion_context(image,context,entries,fail=_fail)
    helper=next(r for r in context['entries']if r['relativeSlot']==3)['methodSpec'][0]
    method_owned=validate_instance_context(image,context,method_contexts,entries,helper,fail=_fail)
    provider=next(r for r in method_contexts if r['typeName']=='MemoryPack.MemoryPackFormatterProvider')
    if provider!=c['providerContext']:_fail('provider-context-join','same complete owned GetFormatter context',c['providerContext'])
    m=image.metadata.methods[provider['definition']]
    if c['declaration']!=[m.index,image.type_name(m.declaring_type),image.metadata.string(m.name_index)]:
        _fail('provider-declaration','same named metadata declaration without physical body identity promotion',c['declaration'])
    actual=entries.resolve(m.index,[],['object'])
    if json.loads(json.dumps(actual))!=c['independentObjectRegistration']:_fail('independent-registration',c['independentObjectRegistration'],actual)
    matched=actual['pointer']-image.pe.image_base==c['calledEntryRva']
    if matched!=c['physicalEntryMatchedIndependentObject']:_fail('independent-physical-comparison',c['physicalEntryMatchedIndependentObject'],matched)
    if c['proof']['program'][0][0]!=c['calledEntryRva']:_fail('physical-program-entry',c['calledEntryRva'],c['proof']['program'][0])
    if any(c['calls'][k]!=deps['instance']['calls'][k]for k in('typeKey','formatterResult','formatterClassPredicate')):
        _fail('owned-physical-helper-join','same current type/result/predicate callees',c['calls'])
    transfer=validate_provider_transfer(image,c['proof'],c['calls'],fail=_fail)
    return {'ownedAdapterContext':owned,'ownedProviderMethodContexts':method_owned,'providerTransfer':transfer,
        'physicalEntryMatchedIndependentObject':matched,'physicalBodyIdentity':'unresolved',
        'runtimeContextAndCandidateSelection':'conditional','cacheMissAllocationAndGlobalEffects':'unresolved'}


def validate_current_native_contract(*,gameassembly: Path|None=None,metadata: Path|None=None) -> dict:
    c=_contract();pins=c['nativeInputs']
    gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
    if gate.status!='validated':return {'status':gate.status,'detail':gate.detail,'scope':SCOPE,'nativeInputs':pins}
    unity=Path(gate.gameassembly).parent/'UnityPlayer.dll'
    def unity_matches():return unity.is_file()and hashlib.sha256(unity.read_bytes()).hexdigest().upper()==pins['UnityPlayer.dll']
    if not unity_matches():return {'status':'mismatched'if unity.is_file()else 'missing','detail':'UnityPlayer.dll missing or mismatched','scope':SCOPE,'nativeInputs':pins}
    try:summary=_validate_image(open_native_image(gate.gameassembly,gate.metadata),c)
    except ValueError as error:
        if isinstance(error,CensusGateError):raise
        _fail('native-provider-transfer','current complete context/ABI/return proof',str(error))
    after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
    if after.status!='validated'or not unity_matches():return {'status':after.status if after.status!='validated'else 'mismatched','detail':'native inputs changed during provider validation','scope':SCOPE,'nativeInputs':pins}
    return {'status':'validated','scope':SCOPE,'nativeInputs':pins,'summary':summary,
        'childSchemaAdmitted':False,'positiveListAdmitted':False,'wholeRootAdmitted':False,'runtimeMeaningExact':False,'evidenceBoundary':c['evidenceBoundary']}
