"""Authenticate selected no-frame Enter/LeaveCriticalSection argument tails."""
from __future__ import annotations
import hashlib
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.word_immediate_stores import decode_word_store_instructions
from scripts.game_data.il2cpp.name_cache_handler_guard_control import validate_name_cache_handler_guards
from scripts.game_data.il2cpp.owned_partition import checked_rows
from scripts.game_data.il2cpp.unwind_chains import UnwindChainIndex,read_exception_directory
from scripts.game_data.il2cpp.pe_imports import resolve_named_import_slots
from .core import CONTRACTS_DIR

LABEL='buffNameCacheHandlerGuard';SCHEMA='endfield.buff-name-cache-handler-guard-native-contract.v1'
SCOPE='signed-index-shared-storage-and-static-guard-tail-control'
CONTRACT_PATH=CONTRACTS_DIR/'buff_name_cache_handler_guard_native.json'


def _skip(status,detail,pins):
    return {'status':status,'detail':detail,'scope':SCOPE,'nativeInputs':pins,'wholeRootAdmitted':False,'runtimeExecutionKnown':False,'criticalSectionInitializedProved':False}


def _validate(image,c):
    base=image.pe.image_base;directory,size,raw=read_exception_directory(image.pe)
    unwind=UnwindChainIndex(raw,lambda at,n:image.pe.bytes_at_va(base+at,n),table_rva=directory,image_size=size)
    parent,_=read_reviewed_contract(CONTRACTS_DIR/'buff_name_cache_handler_getter_native.json',schema='endfield.buff-name-cache-handler-getter-native-contract.v1',status='exact-current-build',label=LABEL)
    if parent['nativeInputs']!=c['nativeInputs']:raise ValueError(LABEL+'.parent-build')
    programs={}
    for role,f in c['functions'].items():
        if f['ownershipKind']!='closedIndirectTailProgram' or len(f['codeWindows'])!=1:raise ValueError(LABEL+'.tail-shape:'+role)
        w=f['codeWindows'][0]
        if w['startRva']!=f['entryRva'] or any(a<w['endRva'] and w['startRva']<b for a,b,_ in unwind.entries.values()):raise ValueError(LABEL+'.unowned-closed-tail-range:'+role)
        call=f['actualParentCall']
        if call!=parent['externalCallSites'][role] or call['targetRva']!=f['entryRva']:raise ValueError(LABEL+'.parent-call-record:'+role)
        raw=image.pe.bytes_at_va(base+call['siteRva'],5)
        if raw!=bytes.fromhex(call['instructionHex']) or raw[0]!=0xe8 or call['siteRva']+5+int.from_bytes(raw[1:],'little',signed=True)!=f['entryRva']:raise ValueError(LABEL+'.parent-call:'+role)
        pw=[w for w in parent['functions']['handlerGetter']['codeWindows'] if w['startRva']<=call['siteRva'] and call['siteRva']+5<=w['endRva']]
        if not pw:raise ValueError(LABEL+'.parent-call-ownership:'+role)
        image.check_windows(pw,label=LABEL+'.parent-'+role);image.check_windows(f['codeWindows'],label=LABEL+'.'+role)
        raw=image.pe.bytes_at_va(base+w['startRva'],w['endRva']-w['startRva'])
        programs[role]=checked_rows(decode_word_store_instructions(image.mapper,raw,base+w['startRva']),raw,LABEL+'.'+role)
    decl=resolve_named_import_slots(image.pe,[f['tailImportSlotRva'] for f in c['functions'].values()])
    if decl!=c['importDeclaration']:raise ValueError(LABEL+'.import-declarations')
    return validate_name_cache_handler_guards(programs,image_base=base,contract=c)


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
        'wholeRootAdmitted':False,'runtimeExecutionKnown':False,'criticalSectionInitializedProved':False}
