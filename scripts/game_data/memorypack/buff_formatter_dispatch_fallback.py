"""Authenticate anonymous preparation/fallback control on the selected build."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.il2cpp.native_image import NATIVE_MAPPER_PATH,read_reviewed_contract
from scripts.game_data.il2cpp.protocol import load_native_mapper
from scripts.game_data.il2cpp.dispatch_fallback_control import validate_dispatch_fallback_control
from scripts.game_data.memorypack import buff_formatter_comparer_dispatch as parent_owner
from scripts.game_data.memorypack.corpus_gate import CensusGateError,_fingerprint,_parser_source_snapshots

LABEL='buffFormatterDispatchFallback'
SCOPE='anonymous-prepare-byte-gates-and-resolver-result-transfer-only'
PATH=CONTRACTS_DIR/'buff_formatter_dispatch_fallback_native.json'

def _fail(check,expected,actual):
    error=CensusGateError(f'{LABEL}.{check}',source=PATH.as_posix(),expected=str(expected)[:1024],actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL,scope=SCOPE);error.args=(json.dumps(error.diagnostic,sort_keys=True),);raise error

def _contract():
    c,_=read_reviewed_contract(PATH,schema='endfield.buff-formatter-dispatch-fallback-native-contract.v1',status='exact-current-build',label=LABEL)
    if (c.get('schema'),c.get('scope'),c.get('parentContract'))!=(
        'endfield.buff-formatter-dispatch-fallback-native-contract.v1',SCOPE,'buff_formatter_comparer_dispatch_native.json'):
        _fail('contract-shape','reviewed schema, scope and parent',c.get('schema'))
    return c

def _proof_sources():
    rows=_parser_source_snapshots(Path(__file__))+[_fingerprint(PATH),_fingerprint(NATIVE_MAPPER_PATH)]+parent_owner._proof_sources()
    return sorted({r['path']:r for r in rows}.values(),key=lambda r:r['path'])

def _validate_selected(gameassembly,c):
    parent=parent_owner._contract()
    if parent['nativeInputs']!=c['nativeInputs']:_fail('parent-build',c['nativeInputs'],parent['nativeInputs'])
    if parent['calls']['prepareClass']!=c['prepareEntryTransfer']['entryRva'] or parent['calls']['resolveSlot']!=c['programs']['resolver']['entryRva']:
        _fail('actual-parent-callees','parent prepare and resolver entries',c['programs'])
    parent_owner._validate_selected(gameassembly,parent)
    mapper=load_native_mapper(NATIVE_MAPPER_PATH);pe=mapper.PeImage(Path(gameassembly))
    index=BodyIndex(SimpleNamespace(mapper=mapper,pe=pe,metadata=None))
    return {**validate_dispatch_fallback_control(index,c),'actualParentDispatchAndCallerTransfersRechecked':True}

def validate_current_native_contract(*,gameassembly=None,metadata=None):
    c=_contract();pins=c['nativeInputs'];sources=_proof_sources()
    gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
    result={'status':gate.status,'scope':SCOPE,'nativeInputs':pins,'provenance':{'inputs':sources},
        'evidenceBoundary':c['evidenceBoundary'],'childEffectsOrInitializationMeaningProved':False,
        'actualRuntimeTargetSelected':False,'callbackCursorEqualityProved':False,'positiveListAdmitted':False,'wholeRootAdmitted':False}
    if gate.status!='validated':return {**result,'detail':gate.detail}
    unity=Path(gate.gameassembly).parent/'UnityPlayer.dll'
    def unity_hash():
        if not unity.is_file():return None
        with unity.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest().upper()
    current=unity_hash()
    if current!=pins['UnityPlayer.dll']:
        return {**result,'status':'missing' if current is None else 'mismatched','detail':'UnityPlayer.dll missing or mismatched'}
    try:summary=_validate_selected(gate.gameassembly,c)
    except (ValueError,KeyError,IndexError,TypeError,OverflowError) as error:
        if isinstance(error,CensusGateError):raise
        _fail('native-control','complete owned prepare/resolver control and actual parent calls',str(error))
    after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
    current=unity_hash()
    if after.status!='validated' or current!=pins['UnityPlayer.dll']:
        return {**result,'status':after.status if after.status!='validated' else 'missing' if current is None else 'mismatched',
            'detail':'native inputs changed during fallback validation'}
    drift=[r['path'] for r in sources if _fingerprint(Path(r['path']))!=r]
    if drift:_fail('proof-source-drift','unchanged source/contract closure',drift)
    return {**result,'status':'validated','summary':summary}
