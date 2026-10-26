"""Authenticate handler decoding and selected PE CFG storage/default joins."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.register_rotates import decode_rotate_instructions
from scripts.game_data.il2cpp.name_cache_handler_getter_control import validate_name_cache_handler_getter
from scripts.game_data.il2cpp.owned_partition import checked_rows
from scripts.game_data.il2cpp.unwind_chains import UnwindChainIndex,read_exception_directory
from scripts.game_data.il2cpp.pe_load_config import resolve_load_config_pointer_slots
from .core import CONTRACTS_DIR

LABEL='buffNameCacheHandlerGetter';SCHEMA='endfield.buff-name-cache-handler-getter-native-contract.v1'
SCOPE='conditional-handler-word-decoding-and-file-cfg-dispatch-joins'
CONTRACT_PATH=CONTRACTS_DIR/'buff_name_cache_handler_getter_native.json'


def _skip(status,detail,pins):
    return {'status':status,'detail':detail,'scope':SCOPE,'nativeInputs':pins,'wholeRootAdmitted':False,
        'runtimeExecutionKnown':False,'decodedWordIsValidCallbackProved':False,'liveCfgDispatchSelectionProved':False}


def _validate(image,c):
    base=image.pe.image_base;directory,size,raw=read_exception_directory(image.pe)
    unwind=UnwindChainIndex(raw,lambda at,n:image.pe.bytes_at_va(base+at,n),table_rva=directory,image_size=size)
    parent,_=read_reviewed_contract(CONTRACTS_DIR/'buff_name_cache_allocator_native.json',
        schema='endfield.buff-name-cache-allocator-native-contract.v1',status='exact-current-build',label=LABEL)
    if parent['nativeInputs']!=c['nativeInputs']:raise ValueError(LABEL+'.parent-build')
    joins=(('handlerGetter','handlerGetter'),('callbackDispatch','callbackDispatch'))
    for role,key in joins:
        if c['functions'][role]['actualParentCall']!=parent['externalCallSites'][key]:raise ValueError(LABEL+'.parent-call-record:'+role)
    selected=resolve_load_config_pointer_slots(image.pe,[c['globals']['cookie'],c['globals']['dispatchSlot']])
    if selected!=c['loadConfigDeclaration']:raise ValueError(LABEL+'.load-config-declaration')
    programs={}
    for role,f in c['functions'].items():
        family=json.loads(json.dumps(unwind.family(f['entryRva'])))
        windows=f['codeWindows']
        if f['ownershipKind']!='exceptionFamily' or family!=f['unwindFamily'] or [[w['startRva'],w['endRva']] for w in windows]!=[p['runtimeTriple'][:2] for p in family['ranges']]:
            raise ValueError(LABEL+'.whole-owned-code:'+role)
        if role!='fileDefaultDispatch':
            call=f['actualParentCall'];raw=image.pe.bytes_at_va(base+call['siteRva'],5)
            if raw!=bytes.fromhex(call['instructionHex']) or raw[0]!=0xe8 or call['siteRva']+5+int.from_bytes(raw[1:],'little',signed=True)!=f['entryRva']:
                raise ValueError(LABEL+'.actual-parent-call:'+role)
            containing=[w for p in parent['functions'].values() for w in p['codeWindows'] if w['startRva']<=call['siteRva'] and call['siteRva']+5<=w['endRva']]
            if not containing:raise ValueError(LABEL+'.parent-call-ownership:'+role)
            image.check_windows(containing,label=LABEL+'.parent-'+role)
        image.check_windows(windows,label=LABEL+'.'+role);rows=[]
        for w in windows:
            raw=image.pe.bytes_at_va(base+w['startRva'],w['endRva']-w['startRva'])
            rows.extend(checked_rows(decode_rotate_instructions(image.mapper,raw,base+w['startRva']),raw,LABEL+'.'+role))
        programs[role]=rows
    for role,call in c['externalCallSites'].items():
        raw=image.pe.bytes_at_va(base+call['siteRva'],5)
        if raw!=bytes.fromhex(call['instructionHex']) or raw[0]!=0xe8 or call['siteRva']+5+int.from_bytes(raw[1:],'little',signed=True)!=c['externalCalls'][role]:
            raise ValueError(LABEL+'.guard-helper-call:'+role)
        if not any(w['startRva']<=call['siteRva'] and call['siteRva']+5<=w['endRva'] for w in c['functions']['handlerGetter']['codeWindows']):
            raise ValueError(LABEL+'.guard-helper-call-ownership:'+role)
    return validate_name_cache_handler_getter(programs,image_base=base,contract=c)


def validate_current_native_contract(*,gameassembly:Path,metadata:Path):
    c,_=read_reviewed_contract(CONTRACT_PATH,schema=SCHEMA,status='exact-current-build',label=LABEL)
    if c.get('scope')!=SCOPE:raise ValueError(LABEL+'.scope')
    pins=c['nativeInputs'];before=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
    if before.status!='validated':return _skip(before.status,before.detail,pins)
    unity=Path(before.gameassembly).parent/'UnityPlayer.dll'
    def valid_unity():
        if not unity.is_file():return False
        with unity.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest().upper()==pins['UnityPlayer.dll']
    if not valid_unity():return _skip('mismatched' if unity.is_file() else 'missing','Selected UnityPlayer.dll missing or mismatched',pins)
    summary=_validate(open_native_image(before.gameassembly,before.metadata),c)
    after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=before.gameassembly,metadata=before.metadata)
    if after.status!='validated' or not valid_unity():return _skip(after.status if after.status!='validated' else 'mismatched','Selected native inputs changed',pins)
    return {'status':'validated','scope':SCOPE,'nativeInputs':pins,'summary':summary,'evidenceBoundary':c['evidenceBoundary'],
        'wholeRootAdmitted':False,'runtimeExecutionKnown':False,'decodedWordIsValidCallbackProved':False,'liveCfgDispatchSelectionProved':False}
