"""Current reference-list control and physical reset; no stored admission.

The actual helper index write/version increment is distinct from its anonymous
span callee's unresolved writes and independently registered managed identity.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.formatter_composition import (
    validate_registered_formatter_composition, validate_source_list_formatter_registration)
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError
from scripts.game_data.memorypack.named_native_records import check_typed_context
from scripts.game_data.memorypack.list_reference_sources import (
    validate_list_element_context, validate_buffered_reference_list)
from scripts.game_data.memorypack.list_context_helpers import validate_physical_list_reset
from scripts.game_data.memorypack import buff_formatter_provider as formatter_provider

LABEL = 'buffTimelineListControl'
CONTRACT_PATH = CONTRACTS_DIR / 'buff_timeline_list_control_native.json'
SCHEMA = 'endfield.buff-timeline-list-control-native-contract.v4'
SCOPE = 'buffered-existing-reference-list-control-only'


def _fail(check: str, expected: Any, actual: Any) -> None:
    error = CensusGateError(f'{LABEL}.{check}', source=CONTRACT_PATH.as_posix(),
        expected=str(expected)[:1024], actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL,scope=SCOPE)
    error.args=(json.dumps(error.diagnostic,sort_keys=True),)
    raise error


def _contract() -> dict:
    contract,_=read_reviewed_contract(CONTRACT_PATH,schema=SCHEMA,status='exact-current-build',label=LABEL)
    row=contract['sharedEntry']
    if (contract.get('scope')!=SCOPE or set(contract['dependencies'])!={'staticComposition','rootList','readerLayout','formatterProvider'}
            or row['classArguments']!=['object'] or row['methodArguments']!=[]
            or row['method'][1:]!=['MemoryPack.Formatters.ListFormatter`1','Deserialize']):
        _fail('shared-list-scope','independent Object physical entry and separate requested element',row)
    return contract


def _validate_image(image: Any, contract: dict) -> dict:
    schemas={'staticComposition':'endfield.buff-timeline-static-composition-native-contract.v1',
        'rootList':'endfield.buff-timeline-empty-native-contract.v1',
        'readerLayout':'endfield.buff-timeline-element-sources-native-contract.v1',
        'formatterProvider':formatter_provider.SCHEMA}
    dependencies={key:read_reviewed_contract(CONTRACTS_DIR/contract['dependencies'][key],
        schema=schema,status='exact-current-build',label=LABEL)[0] for key,schema in schemas.items()}
    if any(c['nativeInputs']!=contract['nativeInputs'] for c in dependencies.values()):
        _fail('dependency-build',contract['nativeInputs'],[c['nativeInputs'] for c in dependencies.values()])
    static,root,source=(dependencies[k] for k in ('staticComposition','rootList','readerLayout'))
    validate_registered_formatter_composition(image,static['composition'],label=LABEL)
    selected=NativeReferenceContext(image);row=contract['sharedEntry'];entries=GenericEntries(image)
    actual=entries.resolve(row['method'][0],row['classArguments'],row['methodArguments'])
    if json.loads(json.dumps(actual))!=row['registration']:
        _fail('shared-list-registration',row['registration'],actual)
    image.validate_method_row(row['method'],label=LABEL)
    flow=dict(static['sourceListRegistration'],sourceContext=root['listSourceContext'])
    if row['requestedElementType']!=flow['elementType'] or selected.is_value_type(flow['elementType']):
        _fail('source-reference-element',flow['elementType'],row['requestedElementType'])
    check_typed_context(image,flow['sourceContext'],root['timelineFieldType'],label=LABEL,fail=_fail)
    validate_source_list_formatter_registration(image,flow,label=LABEL)
    contexts=[r for r in static['composition']['genericContexts'] if r['typeName']==row['method'][1] and not r['isMethod']]
    if len(contexts)!=1 or image.metadata.methods[row['method'][0]].declaring_type!=contexts[0]['definition']:
        _fail('list-owned-context','one exact ListFormatter context owner',contexts)
    context=validate_list_element_context(image,contexts[0],entries,fail=_fail)
    method=image.metadata.methods[row['method'][0]];parameters=image.metadata.parameters_for(method)
    if method.flags&0x10 or selected.type_name(method.return_type)!='void' or len(parameters)!=2:
        _fail('list-reference-abi','instance void with two byrefs',row['method'])
    for ordinal,p in enumerate(parameters):
        raw=image.pe.bytes_at_va(selected.type_pointer(p.type_index),16)
        if raw[11]!=0x20 or (ordinal==0 and selected.type_name(p.type_index)!='MemoryPack.MemoryPackReader'):
            _fail('list-reference-parameter','Reader and List references',[ordinal,raw.hex()])
        if ordinal==1:
            list_row=next(r for r in contexts[0]['entries'] if r['relativeSlot']==0)
            list_raw=image.pe.bytes_at_va(selected.type_pointer(list_row['index']),16)
            if raw[10]!=0x15 or raw[:8]!=list_raw[:8]:
                _fail('list-output-parameter','same owned List instantiation by reference',raw.hex())
    offsets=contract['readerFieldsUnboxedOffsets']
    if (set(offsets)!={'currentPtr','bufferLength','advancedCount','consumed','totalLength'}
            or {n:v for n,v in offsets.items() if n!='totalLength'}!=source['readerFieldsUnboxedOffsets']
            or offsets!={n:selected.field('MemoryPack.MemoryPackReader::'+n)[2]-16 for n in offsets}):
        _fail('list-reader-layout','five metadata-owned unboxed fields',offsets)
    entry=actual['pointer']-image.pe.image_base
    if any(p['codeWindows'][0]['startRva']!=entry for p in contract['programs'].values()):
        _fail('list-program-entry',entry,contract['programs'])
    loop=validate_buffered_reference_list(image,contract['programs']['singleElement'],
        contract['programs']['twoElements'],offsets,fail=_fail)
    provider=formatter_provider._validate_image(image,dependencies['formatterProvider'])
    if provider['providerTransfer']['entryRva']!=loop['elementContextCallRva']:
        _fail('physical-element-provider','same actual helper with independently proved typed return',provider)
    gaps=_context_entry_gaps(image,entries,contract['independentContextEntries'],contexts[0],loop)
    reset=contract['physicalListReset']
    reset_summary=validate_physical_list_reset(image,reset['programs'],reset['observedSlots'],
        loop['listStorageOffsets'],loop['existingListContextCallRva'],fail=_fail)
    return {'selectedReferenceElement':row['requestedElementType'],'staticElementContext':context,
        'bufferedReferenceLoop':loop,'physicalContextHelperIdentityGaps':gaps,
        'physicalListReset':reset_summary,'physicalFormatterProvider':provider}


def _context_entry_gaps(image: Any, entries: Any, rows: list, context: dict, loop: dict) -> list:
    """Authenticate independently selected managed entries without naming clones."""
    slots={r['relativeSlot']:r for r in context['entries']}
    if (len(rows)!=2 or {r['relativeContextSlot'] for r in rows}!={2,3}
            or {r['physicalCallField'] for r in rows}!={'existingListContextCallRva','elementContextCallRva'}):
        _fail('independent-context-entry-scope','separate Clear/provider physical entries',rows)
    gaps=[]
    for row in rows:
        slot=row['relativeContextSlot'];method=row['method']
        if (method[0]!=slots[slot]['methodSpec'][0]
                or row['classArguments']!=(['object'] if slot==2 else [])
                or row['methodArguments']!=([] if slot==2 else ['object'])
                or row['physicalCallField']!=('existingListContextCallRva' if slot==2 else 'elementContextCallRva')):
            _fail('independent-context-entry-owner','same static declaration with independent Object selection',row)
        image.validate_method_row(method,label=LABEL)
        actual=entries.resolve(method[0],row['classArguments'],row['methodArguments'])
        if json.loads(json.dumps(actual))!=row['registration']:
            _fail('independent-context-entry-registration',row['registration'],actual)
        managed=actual['pointer']-image.pe.image_base;physical=loop[row['physicalCallField']]
        if managed==physical:
            _fail('independent-context-helper-gap','observed distinct physical helper and registered entry',[managed,physical])
        gaps.append({'relativeContextSlot':slot,'physicalHelperRva':physical,'registeredObjectEntryRva':managed,
            'helperBodyIdentity':'unresolved','runtimeSelectionObserved':False})
    return gaps


def validate_current_native_contract(*,gameassembly: Path | None=None,metadata: Path | None=None) -> dict:
    contract=_contract();pins=contract['nativeInputs']
    gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
    if gate.status!='validated':return {'status':gate.status,'detail':gate.detail,'nativeInputs':pins,'scope':SCOPE}
    unity=Path(gate.gameassembly).parent/'UnityPlayer.dll'
    def unity_matches():return unity.is_file() and hashlib.sha256(unity.read_bytes()).hexdigest().upper()==pins['UnityPlayer.dll']
    if not unity_matches():return {'status':'mismatched' if unity.is_file() else 'missing',
        'detail':'UnityPlayer.dll missing or mismatched','nativeInputs':pins,'scope':SCOPE}
    try:summary=_validate_image(open_native_image(gate.gameassembly,gate.metadata),contract)
    except ValueError as error:
        if isinstance(error,CensusGateError):raise
        _fail('native-list-control','current typed header and complete selected loop',str(error))
    after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
    if after.status!='validated' or not unity_matches():return {'status':after.status if after.status!='validated' else 'mismatched',
        'detail':'native inputs changed during validation','nativeInputs':pins,'scope':SCOPE}
    return {'status':'validated','scope':SCOPE,'nativeInputs':pins,'summary':summary,
        'positiveListAdmitted':False,'wholeRootAdmitted':False,'runtimeMeaningExact':False,
        'evidenceBoundary':contract['evidenceBoundary']}
