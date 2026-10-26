"""Authenticate cache allocator wrapper control and static import declarations."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.word_immediate_stores import decode_word_store_instructions
from scripts.game_data.il2cpp.name_cache_allocator_control import validate_name_cache_allocator
from scripts.game_data.il2cpp.owned_partition import checked_rows
from scripts.game_data.il2cpp.unwind_chains import UnwindChainIndex,read_exception_directory
from scripts.game_data.il2cpp.pe_imports import resolve_named_import_slots
from .core import CONTRACTS_DIR

LABEL='buffNameCacheAllocator';SCHEMA='endfield.buff-name-cache-allocator-native-contract.v1'
SCOPE='complete-conditional-allocator-wrapper-and-helper-control'
CONTRACT_PATH=CONTRACTS_DIR/'buff_name_cache_allocator_native.json'


def _skip(status,detail,pins):
    return {'status':status,'detail':detail,'scope':SCOPE,'nativeInputs':pins,'wholeRootAdmitted':False,'runtimeExecutionKnown':False,'cacheNoninterferenceProved':False}


def _validate(image,c):
    base=image.pe.image_base;directory,size,raw=read_exception_directory(image.pe)
    unwind=UnwindChainIndex(raw,lambda at,n:image.pe.bytes_at_va(base+at,n),table_rva=directory,image_size=size)
    parent,_=read_reviewed_contract(CONTRACTS_DIR/'buff_name_cache_constructor_native.json',
        schema='endfield.buff-name-cache-constructor-native-contract.v1',status='exact-current-build',label=LABEL)
    if parent['nativeInputs']!=c['nativeInputs']:raise ValueError(LABEL+'.constructor-build')
    if parent['externalCalls']['allocator']!=c['functions']['allocatorProxy']['entryRva']:raise ValueError(LABEL+'.constructor-selected-allocator')
    parent_windows=parent['functions']['constructor']['codeWindows']+[w for f in c['functions'].values() for w in f['codeWindows']]
    programs={}
    for role,f in c['functions'].items():
        windows=f['codeWindows'];owned=f['ownedWindows']
        if f['ownershipKind']=='exceptionFamily':
            family=json.loads(json.dumps(unwind.family(f['entryRva'])))
            if family!=f['unwindFamily'] or owned!=windows or [[w['startRva'],w['endRva']] for w in owned]!=[p['runtimeTriple'][:2] for p in family['ranges']]:
                raise ValueError(LABEL+'.whole-owned-code:'+role)
        elif f['ownershipKind'] in ('closedNoCallProgram','directTailProgram'):
            if owned or f['unwindFamily'] is not None or len(windows)!=1 or windows[0]['startRva']!=f['entryRva'] or any(a<w['endRva'] and w['startRva']<b for a,b,_ in unwind.entries.values() for w in windows):
                raise ValueError(LABEL+'.closed-program-range:'+role)
        else:raise ValueError(LABEL+'.ownership-kind:'+role)
        is_tail='actualParentTail' in f;join=f['actualParentTail'] if is_tail else f['actualParentCall']
        if not isinstance(join,dict):raise ValueError(LABEL+'.missing-parent-join:'+role)
        raw=image.pe.bytes_at_va(base+join['siteRva'],5)
        if raw[0]!=(0xe9 if is_tail else 0xe8) or join['siteRva']+5+int.from_bytes(raw[1:],'little',signed=True)!=f['entryRva'] or join['targetRva']!=f['entryRva']:
            raise ValueError(LABEL+'.actual-parent-join:'+role)
        if 'instructionHex' in join and raw!=bytes.fromhex(join['instructionHex']):raise ValueError(LABEL+'.join-bytes:'+role)
        containing=[w for w in parent_windows if w['startRva']<=join['siteRva'] and join['siteRva']+5<=w['endRva']]
        if not containing:raise ValueError(LABEL+'.parent-window:'+role)
        image.check_windows(containing,label=LABEL+'.parent-'+role);image.check_windows(windows,label=LABEL+'.'+role)
        rows=[]
        for w in windows:
            raw=image.pe.bytes_at_va(base+w['startRva'],w['endRva']-w['startRva'])
            rows.extend(checked_rows(decode_word_store_instructions(image.mapper,raw,base+w['startRva']),raw,LABEL+'.'+role))
        programs[role]=rows
    imports=resolve_named_import_slots(image.pe,[c['heapImport']['slotRva']])
    if imports['selectedImports']!=[c['heapImport']]:raise ValueError(LABEL+'.heap-import-declaration')
    for role,site in c['externalCallSites'].items():
        raw=image.pe.bytes_at_va(base+site['siteRva'],5)
        if raw!=bytes.fromhex(site['instructionHex']) or raw[0]!=0xe8 or site['siteRva']+5+int.from_bytes(raw[1:],'little',signed=True)!=c['externalCalls'][role] or site['targetRva']!=c['externalCalls'][role]:
            raise ValueError(LABEL+'.external-call:'+role)
        if not any(w['startRva']<=site['siteRva'] and site['siteRva']+5<=w['endRva'] for f in c['functions'].values() for w in f['codeWindows']):
            raise ValueError(LABEL+'.external-call-ownership:'+role)
    return validate_name_cache_allocator(programs,image_base=base,contract=c)


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
        'wholeRootAdmitted':False,'runtimeExecutionKnown':False,'cacheNoninterferenceProved':False}
