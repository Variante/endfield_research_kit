"""Stored valid UTF8 BlackboardDouble keys from the actual inline source.

The original child reader independently establishes the named key span. This
owner proves its length/null/empty/ReadUtf8 result program and decodes that
span. Closed generic Data layout, replacement decoding, provider choice and
evaluated blackboard values remain open.
"""
from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path
from typing import Any
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import (
    METADATA_HELPER_PATH,NATIVE_MAPPER_PATH,open_native_image,read_reviewed_contract)
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError,_fingerprint,_package_import_closure
from scripts.game_data.memorypack import buff_adding_cooldown as scalar
from scripts.game_data.memorypack import inline_utf8_sources as inline
from scripts.game_data.memorypack import utf8_source_helper as strings

LABEL='buffBlackboardDoubleKey'
CONTRACT_PATH=CONTRACTS_DIR/'memorypack_blackboard_double_key_native.json'


def _contract() -> dict[str,Any]:
    c,_=read_reviewed_contract(CONTRACT_PATH,
        schema='endfield.memorypack-blackboard-double-key-native-contract.v1',status='exact-current-build',label=LABEL)
    if (c.get('wireEncoding')!='nullable-int32-byte-length-valid-utf8'
            or c.get('fieldName')!='blackboardKey' or c.get('fieldOrdinal')!=0
            or (c.get('record',{}).get('inlineStringSource') or {}).get('mode')!=inline.MODE):
        raise ValueError(f'{LABEL}.contract:scope')
    return c


def _fail(check: str,expected: Any,actual: Any) -> None:
    c=_contract();error=CensusGateError(f'{LABEL}.{check}',source=scalar.CHILD_CONTRACT_PATH.as_posix(),
        expected=str(expected)[:1024],actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL,field=c['fieldName'],nativeInputs=c['nativeInputs'])
    error.args=(json.dumps(error.diagnostic,sort_keys=True),);raise error


def _skip(status: str,detail: str,pins: dict) -> dict:
    return {'status':status,'detail':detail,'nativeInputs':pins,'childSchemaAdmitted':False,'wholeRootAdmitted':False}


def validate_current_native_contract(*,gameassembly: Path,metadata: Path) -> dict[str,Any]:
    c=_contract();pins=c['nativeInputs']
    gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
    if gate.status!='validated':return _skip(gate.status,gate.detail,pins)
    unity=Path(gate.gameassembly).parent/'UnityPlayer.dll'
    if not unity.is_file():return _skip('missing','UnityPlayer.dll missing beside selected GameAssembly.dll',pins)
    if _fingerprint(unity)['sha256']!=pins['UnityPlayer.dll']:return _skip('mismatched','Selected UnityPlayer.dll hash differs',pins)
    declaration_files=[scalar.DEFAULT_DUMMYDLL_ROOT/'generation.json',scalar.DEFAULT_DUMMYDLL_ROOT/'MemoryPack.Beyond.dll']
    if any(not p.is_file() for p in declaration_files):
        return _skip('missing','Current optional generated scalar declarations unavailable; no key labels published',pins)
    paths=set(_package_import_closure(Path(__file__)))|{
        CONTRACT_PATH,scalar.CONTRACT_PATH,scalar.ROOT_CONTRACT_PATH,scalar.CHILD_CONTRACT_PATH,
        strings.CONTRACT_PATH,scalar.DEFAULT_DUMMYDLL_ROOT/'generation.json',
        scalar.DEFAULT_DUMMYDLL_ROOT/'MemoryPack.Beyond.dll',NATIVE_MAPPER_PATH,METADATA_HELPER_PATH}
    inputs=sorted((_fingerprint(path) for path in paths),key=lambda r:r['path'])
    names=scalar.validate_current_native_contract(gameassembly=gate.gameassembly,metadata=gate.metadata)
    string_result=strings.validate_current_native_contract(gameassembly=gate.gameassembly,metadata=gate.metadata)
    if names.get('status')!='validated':return _skip(names.get('status','unresolved'),'Current scalar generated names unavailable',pins)
    if string_result.get('status')!='validated' or string_result.get('nativeInputs')!=pins:
        return _skip('mismatched' if string_result.get('status')=='validated' else string_result.get('status','unresolved'),
                     'UTF8 helper not validated for selected build',pins)
    if names.get('selectedReadOrder')!=c['selectedReadOrder']:
        _fail('current-member-order',c['selectedReadOrder'],names.get('selectedReadOrder'))
    if scalar._contract()['nativeInputs']!=pins or strings._contract()['nativeInputs']!=pins:
        _fail('dependency-build','Same selected native inputs',pins)
    image=open_native_image(gate.gameassembly,gate.metadata)
    source=json.loads(scalar.CHILD_CONTRACT_PATH.read_bytes())
    for method in source['methods']:image.validate_method_row(method,label=LABEL)
    image.check_windows(source['codeWindows'],label=LABEL)
    reader=c['record']['readerMethod'];image.validate_method_row(reader,label=LABEL)
    if (reader not in source['methods'] or reader[1]!=c['record']['wrapperTypeName']
            or image.type_name(c['record']['wrapperTypeDefinition'])!=reader[1]):
        _fail('child-source-method','Exact selected child reader and wrapper',reader)
    method=c['utf8Method'];image.validate_method_row(method,label=LABEL)
    definition=image.metadata.methods[method[0]];selected=NativeReferenceContext(image)
    if (method[1:3]!=['MemoryPack.MemoryPackReader','ReadUtf8'] or definition.flags&0x10
            or selected.type_name(definition.return_type)!='string'
            or [selected.type_name(p.type_index) for p in image.metadata.parameters_for(definition)]!=['int']):
        _fail('read-utf8-signature','Instance Reader.ReadUtf8(int) returns string',method)
    declared=next((r for r in strings._contract()['methods'] if r[2]=='ReadUtf8'),None)
    if declared!=method:_fail('read-utf8-helper-identity',declared,method)
    transfer=inline.validate_inline_utf8_source(image,source,c['record'],utf8_method=method,
        empty_literal_cell=strings._contract()['emptyLiteral']['usageCellRva'],fail=_fail)
    after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],
        gameassembly=gate.gameassembly,metadata=gate.metadata)
    if after.status!='validated':return _skip(after.status,after.detail,pins)
    if not unity.is_file() or _fingerprint(unity)['sha256']!=pins['UnityPlayer.dll']:
        return _skip('mismatched' if unity.is_file() else 'missing','Selected UnityPlayer.dll changed during validation',pins)
    for before in inputs:
        actual=_fingerprint(Path(before['path']))
        if before!=actual:_fail('source-drift',before,actual)
    return {'status':'validated','nativeInputs':pins,'fieldName':c['fieldName'],'fieldOrdinal':c['fieldOrdinal'],
        'selectedReadOrder':c['selectedReadOrder'],'wireEncoding':c['wireEncoding'],
        'utf8Method':method,'sourceTransfer':transfer,'provenance':{'inputs':inputs},
        'childSchemaAdmitted':False,'wholeActionAdmitted':False,'wholeRootAdmitted':False,
        'runtimeMeaningExact':False,'evidenceBoundary':c['evidenceBoundary']}


def decode_key(data: bytes,*,source: str,digest: str,child_start: int,child_end: int,
               native_validation: dict[str,Any],scalar_native_validation: dict[str,Any]) -> dict[str,Any]:
    c=_contract()
    if (native_validation.get('status')!='validated' or native_validation.get('nativeInputs')!=c['nativeInputs']
            or native_validation.get('fieldName')!=c['fieldName'] or native_validation.get('fieldOrdinal')!=0
            or native_validation.get('wireEncoding')!=c['wireEncoding'] or not isinstance(data,bytes)
            or not source or not isinstance(digest,str) or hashlib.sha256(data).hexdigest().upper()!=digest.upper()):
        raise ValueError(f'{LABEL}.decode:unvalidated-source')
    child=scalar.decode_adding_cooldown(data,child_start,child_end,native_validation=scalar_native_validation)
    if child.get('memberCount') is None:
        return {'schema':'endfield.blackboard-double-key-receipt.v1','source':source,'logicalSha256':digest.upper(),
            'childStart':child_start,'childEnd':child_end,'childNull':True,'keyPresent':False,'key':None,
            'wholeStoredKeySpanExact':False,'runtimeMeaningExact':False}
    field=child['fields'][0]
    if field.get('name')!=c['fieldName'] or field.get('declaredType')!='string':
        raise ValueError(f'{LABEL}.decode:child-key-identity')
    start,end=field['start'],field['end'];count=struct.unpack_from('<i',data,start)[0]
    if count < -1 or end!=start+4+max(count,0):raise ValueError(f'{LABEL}.decode:key-length')
    try:value=None if count==-1 else data[start+4:end].decode('utf-8','strict')
    except UnicodeDecodeError as error:raise ValueError(f'{LABEL}.decode:invalid-utf8') from error
    reencoded=struct.pack('<i',-1 if value is None else len(value.encode('utf-8')))+(b'' if value is None else value.encode('utf-8'))
    if reencoded!=data[start:end]:raise ValueError(f'{LABEL}.decode:key-reencode')
    return {'schema':'endfield.blackboard-double-key-receipt.v1','source':source,'logicalSha256':digest.upper(),
        'childStart':child_start,'childEnd':child_end,'childNull':False,'keyPresent':True,
        'key':{'fieldName':c['fieldName'],'start':start,'end':end,'byteLength':count,'value':value,
               'rawHex':data[start:end].hex().upper(),'storedStringValueExact':True},
        'wholeStoredKeySpanExact':True,'keyFieldReencodeExact':True,'runtimeMeaningExact':False,
        'wholeActionAdmitted':False,'wholeRootAdmitted':False}
