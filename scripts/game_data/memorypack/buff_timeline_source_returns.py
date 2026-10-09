"""Complete positive Timeline/ForceSync source returns, below child composition."""
from __future__ import annotations

import hashlib,json
from pathlib import Path
from typing import Any
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError
from scripts.game_data.memorypack import buff_timeline_element_sources as source
from scripts.game_data.memorypack.buffered_owned_sources import _program

LABEL='buffTimelineSourceReturns'
SCHEMA='endfield.buff-timeline-source-returns-native-contract.v1'
SCOPE='buffered-positive-source-through-complete-return-only'
CONTRACT_PATH=CONTRACTS_DIR/'buff_timeline_source_returns_native.json'


def _fail(check: str,expected: Any,actual: Any) -> None:
    error=CensusGateError(f'{LABEL}.{check}',source=CONTRACT_PATH.as_posix(),
        expected=str(expected)[:1024],actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL,scope=SCOPE)
    error.args=(json.dumps(error.diagnostic,sort_keys=True),);raise error


def _contract() -> dict:
    c,_=read_reviewed_contract(CONTRACT_PATH,schema=SCHEMA,status='exact-current-build',label=LABEL)
    if c.get('scope')!=SCOPE or set(c['records'])!={'timeline','forceSync'} or set(c['dependencies'])!={'source'}:
        _fail('source-return-scope','two complete positive source paths and one independent field-source dependency',c.get('scope'))
    return c


def _validate_suffix(image: Any,key: str,proof: dict,record: dict) -> dict:
    """Join the proved last field store to an exact no-call/no-write epilogue."""
    program=proof['program'];prefix=record['positiveProgram'];window=record['sourceWindow']
    image.check_windows([window],label=LABEL)
    if program[:len(prefix)]!=prefix or not prefix or prefix[-1][0]!=record['members'][-1]['storeRva']:
        _fail('source-prefix-and-final-store','same complete independently proved positive field program',program[:len(prefix)])
    _program(image,window,program,_fail)
    suffix=program[len(prefix):];codes=[r[1]for r in suffix]
    if key=='timeline':
        expected=['7448','4C8B742448','4C8B7C2450','488B5C2458','4883C420','5F','5E','5D','C3']
        if [r[1]for r in prefix[:5]]!=['48895C2420','55','56','57','4883EC20']:
            _fail('source-entry-frame','three pushes and a thirty-two-byte local frame',prefix[:5])
        for saved in ('4C89742448','4C897C2450'):
            if sum(raw==saved for _,raw in prefix)!=1:
                _fail('source-nonvolatile-save','one exact caller-home save for each restored nonvolatile',saved)
        flag_at,flag_hex=prefix[-2];raw=bytes.fromhex(flag_hex)
        if len(raw)!=7 or raw[:2]!=b'\x83\x3d' or raw[-1]!=0:
            _fail('source-disabled-barrier-guard','RIP Int32 comparison against zero immediately before final reference store',prefix[-2])
        flag=flag_at+7+int.from_bytes(raw[2:6],'little',signed=True)
        condition='final reference-store barrier flag is zero; prior source-path conditions remain required'
    elif key=='forceSync':
        expected=['488B5C2448','488B6C2450','488B742458','4883C430','5F','C3']
        if [r[1]for r in prefix[:5]]!=['48895C2410','48896C2418','4889742420','57','4883EC30']:
            _fail('source-entry-frame','one push and a forty-eight-byte local frame',prefix[:5])
        if (sum(raw=='0F29742420'for _,raw in prefix)!=1
                or len(prefix)<2 or prefix[-2][1]!='0F28742420'):
            _fail('source-vector-restore','one XMM6 save and restoration immediately before the last scalar store',prefix[-2:])
        flag=None;condition='prior source-path conditions remain required'
    else:
        _fail('source-record-selection','timeline or forceSync',key)
    if codes!=expected:
        _fail('source-complete-epilogue',expected,codes)
    return {'completeReturn':True,'selectedInstructionCount':len(program),
        'sourceFrameBytesBelowEntry':56,'suffixCalls':0,'suffixReaderWrites':0,
        'suffixObjectWrites':0,'disabledFinalBarrierFlagRva':flag,'condition':condition,
        'originalChildCursorComposition':'unresolved','positiveListAdmitted':False,'wholeRootAdmitted':False}


def _validate_image(image: Any,c: dict) -> dict:
    dependency,_=read_reviewed_contract(CONTRACTS_DIR/c['dependencies']['source'],
        schema=source.SCHEMA,status='exact-current-build',label=LABEL)
    if dependency['nativeInputs']!=c['nativeInputs']:
        _fail('dependency-build','same selected native inputs',dependency['nativeInputs'])
    fields=source._validate_image(image,dependency)
    return {'positiveSourceFields':fields,'completeSourceReturns':{
        key:_validate_suffix(image,key,c['records'][key],record)
        for key,record in dependency['records'].items()},
        'nullableOriginalChildComposition':'unresolved','runtimeSelectionObserved':False}


def validate_current_native_contract(*,gameassembly: Path|None=None,metadata: Path|None=None) -> dict:
    c=_contract();pins=c['nativeInputs']
    gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
    if gate.status!='validated':return {'status':gate.status,'detail':gate.detail,'scope':SCOPE,'nativeInputs':pins}
    unity=Path(gate.gameassembly).parent/'UnityPlayer.dll'
    def unity_matches():return unity.is_file()and hashlib.sha256(unity.read_bytes()).hexdigest().upper()==pins['UnityPlayer.dll']
    if not unity_matches():return {'status':'mismatched'if unity.is_file()else'missing','detail':'UnityPlayer.dll missing or mismatched','scope':SCOPE,'nativeInputs':pins}
    try:summary=_validate_image(open_native_image(gate.gameassembly,gate.metadata),c)
    except ValueError as error:
        if isinstance(error,CensusGateError):raise
        _fail('native-source-return','current complete positive source paths through RET',str(error))
    after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
    if after.status!='validated'or not unity_matches():return {'status':after.status if after.status!='validated'else'mismatched','detail':'native inputs changed during source return validation','scope':SCOPE,'nativeInputs':pins}
    return {'status':'validated','scope':SCOPE,'nativeInputs':pins,'summary':summary,
        'childSchemaAdmitted':False,'positiveListAdmitted':False,'wholeRootAdmitted':False,
        'runtimeMeaningExact':False,'evidenceBoundary':c['evidenceBoundary']}
