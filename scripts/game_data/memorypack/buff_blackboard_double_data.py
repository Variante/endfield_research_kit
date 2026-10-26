"""Closed BlackboardDouble scalar cells from named setters and reader programs.

VAR ownership and current closed arguments establish the Float32 declaration.
Actual emitted stores establish the physical cells; open generic offsets do
not. Original bytes can be joined to the conditional normal Boolean and raw
Float32 transfer without claiming lookup, provider or runtime execution.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import (
    METADATA_HELPER_PATH,NATIVE_MAPPER_PATH,open_native_image,read_reviewed_contract)
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError,_fingerprint,_package_import_closure
from scripts.game_data.memorypack import buff_blackboard_double_key as keys
from scripts.game_data.memorypack import closed_scalar_wrapper_fields as cells
from scripts.game_data.memorypack import buffered_reference_wrappers as barriers

LABEL='buffBlackboardDoubleData'
CONTRACT_PATH=CONTRACTS_DIR/'memorypack_blackboard_double_data_native.json'
BARRIER_CONTRACT_PATH=CONTRACTS_DIR/'buff_timeline_source_wrappers_native.json'


def _contract() -> dict[str,Any]:
    c,_=read_reviewed_contract(CONTRACT_PATH,
        schema='endfield.memorypack-blackboard-double-data-native-contract.v1',status='exact-current-build',label=LABEL)
    if (c.get('selectedReadOrder')!=['blackboardKey','useBlackboardKey','value']
            or c.get('closedScalarFields',{}).get('mode')!=cells.MODE):
        raise ValueError(f'{LABEL}.contract:scope')
    return c


def _fail(check: str,expected: Any,actual: Any) -> None:
    c=_contract();error=CensusGateError(f'{LABEL}.{check}',source=CONTRACT_PATH.as_posix(),
        expected=str(expected)[:1024],actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL,record=c['record']['wrapperTypeName'],nativeInputs=c['nativeInputs'])
    error.args=(json.dumps(error.diagnostic,sort_keys=True),);raise error


def _skip(status: str,detail: str,pins: dict,gate=None) -> dict:
    row={'status':status,'detail':detail,'nativeInputs':pins,
            'childSchemaAdmitted':False,'wholeActionAdmitted':False,'wholeRootAdmitted':False}
    if gate is not None:
        row['nativeGate']={'status':gate.status,'detail':gate.detail,
            'gameAssembly':{'path':str(gate.gameassembly),'sha256':gate.gameassembly_sha256},
            'metadata':{'path':str(gate.metadata),'sha256':gate.metadata_sha256}}
    return row


def validate_current_native_contract(*,gameassembly: Path,metadata: Path) -> dict[str,Any]:
    c=_contract();pins=c['nativeInputs']
    gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
    if gate.status!='validated':return _skip(gate.status,gate.detail,pins,gate)
    unity=Path(gate.gameassembly).parent/'UnityPlayer.dll'
    if not unity.is_file():return _skip('missing','UnityPlayer.dll missing beside selected GameAssembly.dll',pins)
    if _fingerprint(unity)['sha256']!=pins['UnityPlayer.dll']:return _skip('mismatched','Selected UnityPlayer.dll hash differs',pins)
    paths=set(_package_import_closure(Path(__file__)))|{
        CONTRACT_PATH,BARRIER_CONTRACT_PATH,keys.CONTRACT_PATH,keys.scalar.CHILD_CONTRACT_PATH,
        NATIVE_MAPPER_PATH,METADATA_HELPER_PATH}
    inputs={r['path']:r for r in (_fingerprint(p) for p in paths)}
    key_result=keys.validate_current_native_contract(gameassembly=gate.gameassembly,metadata=gate.metadata)
    if key_result.get('status')!='validated' or key_result.get('nativeInputs')!=pins:
        return _skip('mismatched' if key_result.get('status')=='validated' else key_result.get('status','unresolved'),
                     'Independent inline key source unavailable for selected native build',pins)
    key_contract=keys._contract()
    if (key_contract['nativeInputs']!=pins or key_contract['selectedReadOrder']!=c['selectedReadOrder']
            or any(key_contract['record'][k]!=v for k,v in c['record'].items())
            or not key_result.get('sourceTransfer',{}).get('nullEmptyPositiveProgramsProved')):
        _fail('key-source-identity','Same actual child reader, current key programs and member order',key_contract['record'])
    for before in key_result['provenance']['inputs']:
        if before['path'] in inputs and inputs[before['path']]!=before:_fail('dependency-drift',inputs[before['path']],before)
        inputs[before['path']]=before
    barrier=json.loads(BARRIER_CONTRACT_PATH.read_bytes())
    if barrier.get('nativeInputs')!=pins:_fail('barrier-build',pins,barrier.get('nativeInputs'))
    image=open_native_image(gate.gameassembly,gate.metadata)
    source=json.loads(keys.scalar.CHILD_CONTRACT_PATH.read_bytes())
    for method in source['methods']:image.validate_method_row(method,label=LABEL)
    image.check_windows(source['codeWindows'],label=LABEL)
    reader=c['record']['readerMethod'];image.validate_method_row(reader,label=LABEL)
    if reader not in source['methods'] or image.type_name(c['record']['wrapperTypeDefinition'])!=c['record']['wrapperTypeName']:
        _fail('reader-identity','Current exact child reader and wrapper',reader)
    fast=barriers.validate_fast_reference_barrier(image,barrier['barrierProgram'],fail=_fail)
    transfer=cells.validate_closed_scalar_fields(image,source,c['record'],c['closedScalarFields'],
        key_result_join=key_contract['record']['inlineStringSource']['resultJoinRva'],
        barrier_flag=fast['disabledFlagRva'],fail=_fail)
    after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],
        gameassembly=gate.gameassembly,metadata=gate.metadata)
    if after.status!='validated':return _skip(after.status,after.detail,pins)
    if not unity.is_file() or _fingerprint(unity)['sha256']!=pins['UnityPlayer.dll']:
        return _skip('mismatched' if unity.is_file() else 'missing','Selected UnityPlayer.dll changed during validation',pins)
    for before in inputs.values():
        actual=_fingerprint(Path(before['path']))
        if before!=actual:_fail('source-drift',before,actual)
    return {'status':'validated','nativeInputs':pins,'selectedReadOrder':c['selectedReadOrder'],
        'sourceTransfer':transfer,'keyNativeValidation':key_result,
        'barrierDisabledPath':fast,'provenance':{'inputs':sorted(inputs.values(),key=lambda r:r['path'])},
        'childSchemaAdmitted':False,'wholeActionAdmitted':False,'wholeRootAdmitted':False,
        'runtimeExecutionKnown':False,'evidenceBoundary':c['evidenceBoundary']}


def decode_data(data: bytes,*,source: str,digest: str,child_start: int,child_end: int,
                native_validation: dict[str,Any],scalar_native_validation: dict[str,Any]) -> dict[str,Any]:
    c=_contract();transfer=native_validation.get('sourceTransfer',{})
    if (native_validation.get('status')!='validated' or native_validation.get('nativeInputs')!=c['nativeInputs']
            or not transfer.get('sourceMatchesActualNamedSetterCells') or not transfer.get('normalBooleanNormalizationProved')
            or not transfer.get('rawFloat32CopyProved') or transfer.get('runtimeGenericTemplateOffsetsUsed') is not False
            or transfer.get('closedArguments')!=['float','double'] or not isinstance(data,bytes)
            or not source or not isinstance(digest,str) or hashlib.sha256(data).hexdigest().upper()!=digest.upper()):
        raise ValueError(f'{LABEL}.decode:unvalidated-source')
    expected=[(name,block['destinationOffset']) for name,block in c['closedScalarFields']['setters'].items()]
    actual=[(row.get('fieldName'),row.get('destinationOffset')) for row in transfer.get('fields',[])]
    if sorted(actual)!=sorted(expected) or len(actual)!=3:
        raise ValueError(f'{LABEL}.decode:unvalidated-destinations')
    child=keys.scalar.decode_adding_cooldown(data,child_start,child_end,native_validation=scalar_native_validation)
    key=keys.decode_key(data,source=source,digest=digest,child_start=child_start,child_end=child_end,
        native_validation=native_validation['keyNativeValidation'],scalar_native_validation=scalar_native_validation)
    result={'schema':'endfield.blackboard-double-data-receipt.v1','source':source,'logicalSha256':digest.upper(),
        'childStart':child_start,'childEnd':child_end,'childNull':child['memberCount'] is None,
        'wireValueExact':child['wholeValueExact'],'keyReceipt':key,'closedArguments':['float','double'],
        'runtimeGenericTemplateOffsetsUsed':False,'runtimeExecutionKnown':False,
        'providerSelectionProved':False,'runtimeConsumerReadsProved':False,
        'childSchemaAdmitted':False,'wholeActionAdmitted':False,'wholeRootAdmitted':False}
    if result['childNull']:
        result.update(fields=[],conditionalNormalScalarStateProved=False,wholeStoredChildReencodeExact=data[child_start:child_end]==b'\xff')
        return result
    positions={r['fieldName']:r['destinationOffset'] for r in transfer['fields']}
    flag,value=child['fields'][1:];raw=data[flag['start']];bits=data[value['start']:value['end']]
    if (flag['name']!='useBlackboardKey' or flag['end']-flag['start']!=1 or value['name']!='value'
            or value['end']-value['start']!=4 or flag['rawByte']!=raw or value['rawBitsHex']!=bits.hex().upper()):
        raise ValueError(f'{LABEL}.decode:scalar-field-identity')
    reencoded=b'\x03'+bytes.fromhex(key['key']['rawHex'])+bytes((raw,))+bits
    if reencoded!=data[child_start:child_end]:raise ValueError(f'{LABEL}.decode:whole-child-reencode')
    result.update(fields=[{'fieldName':'blackboardKey','destinationOffset':positions['blackboardKey'],
            'start':key['key']['start'],'end':key['key']['end'],'storedValue':key['key']['value'],'representation':'reference'},
        {'fieldName':'useBlackboardKey','destinationOffset':positions['useBlackboardKey'],
            'start':flag['start'],'end':flag['end'],'wireRawByte':raw,'conditionalStoredByte':int(raw!=0),
            'conditionalStoredBoolean':raw!=0,'representation':'normalized-bool'},
        {'fieldName':'value','destinationOffset':positions['value'],'start':value['start'],'end':value['end'],
            'rawBitsHex':bits.hex().upper(),'representation':'raw-float32','storedWidth':4}],
        wholeStoredChildReencodeExact=True,conditionalNormalScalarStateProved=True,
        evidenceBoundary='conditional: independently proved buffered normal source programs and coherent declared references; no lookup/provider/execution observation')
    return result
