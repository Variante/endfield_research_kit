"""Authenticate all closed children of the selected saved-cookie caller."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.register_rotates import decode_rotate_instructions
from scripts.game_data.il2cpp.unwind_chains import UnwindChainIndex,read_exception_directory
from scripts.game_data.il2cpp.owned_partition import checked_rows
from scripts.game_data.il2cpp.name_cache_handler_sibling_stores_control import validate_handler_sibling_stores
from .core import CONTRACTS_DIR

LABEL='buffNameCacheHandlerSiblingStores';SCHEMA='endfield.buff-name-cache-handler-sibling-stores-native-contract.v1'
SCOPE='all-direct-cookie-argument-stores-and-conditional-return-state'
CONTRACT_PATH=CONTRACTS_DIR/'buff_name_cache_handler_sibling_stores_native.json'


def _skip(status,detail,pins):
    return {'status':status,'detail':detail,'scope':SCOPE,'nativeInputs':pins,
        'wholeRootAdmitted':False,'runtimeExecutionKnown':False,'actualCallerInvocationOrStartupOrderProved':False}


def _validate(image,c):
    direct,_=read_reviewed_contract(CONTRACTS_DIR/'buff_name_cache_handler_direct_init_native.json',schema='endfield.buff-name-cache-handler-direct-init-native-contract.v1',status='exact-current-build',label=LABEL)
    getter,_=read_reviewed_contract(CONTRACTS_DIR/'buff_name_cache_handler_getter_native.json',schema='endfield.buff-name-cache-handler-getter-native-contract.v1',status='exact-current-build',label=LABEL)
    if c['nativeInputs']!=getter['nativeInputs'] or (c['cookieRva'],c['encodedHandlerRva'])!=(getter['globals']['cookie'],getter['globals']['encodedHandler']):raise ValueError(LABEL+'.getter-storage-build-join')
    base=image.pe.image_base;directory,size,raw=read_exception_directory(image.pe)
    unwind=UnwindChainIndex(raw,lambda at,n:image.pe.bytes_at_va(base+at,n),table_rva=directory,image_size=size);programs={}
    for role,f in c['functions'].items():
        windows=f['codeWindows']
        if f['ownershipKind']=='exceptionFamily':
            family=json.loads(json.dumps(unwind.family(f['entryRva'])))
            if role!='caller' or family!=f['unwindFamily'] or [[w['startRva'],w['endRva']] for w in windows]!=[r['runtimeTriple'][:2] for r in family['ranges']]:raise ValueError(LABEL+'.owned-caller')
        elif f['ownershipKind']=='closedNoCallProgram':
            if len(windows)!=1 or windows[0]['startRva']!=f['entryRva'] or any(a<w['endRva'] and w['startRva']<b for a,b,_ in unwind.entries.values() for w in windows):raise ValueError(LABEL+'.closed-child-range:'+role)
        else:raise ValueError(LABEL+'.ownership-kind')
        image.check_windows(windows,label=LABEL+'.'+role);rows=[]
        for w in windows:
            data=image.pe.bytes_at_va(base+w['startRva'],w['endRva']-w['startRva'])
            rows.extend(checked_rows(decode_rotate_instructions(image.mapper,data,base+w['startRva']),data,LABEL+'.'+role))
        programs[role]=rows
    for call in c['calls']:
        raw=image.pe.bytes_at_va(base+call['siteRva'],5)
        if raw!=bytes.fromhex(call['instructionHex']) or raw[0]!=0xe8 or call['siteRva']+5+int.from_bytes(raw[1:],'little',signed=True)!=call['targetRva']:raise ValueError(LABEL+'.actual-parent-call')
    for store in c['stores']:
        rva=store['destinationRva']
        owners=[s for s in image.pe.sections if s['virtualAddress']<=rva and rva+8<=s['virtualAddress']+s['virtualSize']]
        if len(owners)!=1:raise ValueError(LABEL+'.declared-global-extent')
    return validate_handler_sibling_stores(programs,image_base=base,contract=c,direct_contract=direct)


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
        'wholeRootAdmitted':False,'runtimeExecutionKnown':False,'actualCallerInvocationOrStartupOrderProved':False}
