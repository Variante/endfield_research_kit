"""Authenticate lifecycle and selected setter definitions without invocation claims."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.register_rotates import decode_rotate_instructions
from scripts.game_data.il2cpp.owned_partition import checked_rows
from scripts.game_data.il2cpp.unwind_chains import UnwindChainIndex,read_exception_directory
from scripts.game_data.il2cpp.pe_imports import resolve_named_import_slots
from scripts.game_data.il2cpp.name_cache_handler_lifecycle_control import validate_handler_lifecycle
from scripts.game_data.il2cpp.name_cache_handler_setter_control import validate_handler_setter
from .core import CONTRACTS_DIR

LABEL='buffNameCacheHandlerState';SCOPE='selected-handler-lifecycle-and-setter-definitions'


def _read(name):
    return read_reviewed_contract(CONTRACTS_DIR/('buff_name_cache_handler_'+name+'_native.json'),
        schema='endfield.buff-name-cache-handler-'+name+'-native-contract.v1',status='exact-current-build',label=LABEL)[0]


def _skip(status,detail,pins):return {'status':status,'detail':detail,'scope':SCOPE,'nativeInputs':pins,'wholeRootAdmitted':False,'runtimeExecutionKnown':False,'actualInitializationOrderProved':False}


def _validate(image,life,setter):
    base=image.pe.image_base;directory,size,raw=read_exception_directory(image.pe)
    unwind=UnwindChainIndex(raw,lambda at,n:image.pe.bytes_at_va(base+at,n),table_rva=directory,image_size=size)
    getter=_read('getter');guard=_read('guard')
    if not all(c['nativeInputs']==life['nativeInputs'] for c in (setter,getter,guard)):raise ValueError(LABEL+'.selected-build-consistency')
    if life['arrayBaseRva']!=guard['arrayBaseRva'] or setter['globals']!={k:getter['globals'][k] for k in ('cookie','encodedHandler')}:raise ValueError(LABEL+'.shared-storage-joins')
    def rows(f,label):
        windows=f['codeWindows']
        if f['ownershipKind']=='exceptionFamily':
            family=json.loads(json.dumps(unwind.family(f['entryRva'])))
            if family!=f['unwindFamily'] or [[w['startRva'],w['endRva']] for w in windows]!=[p['runtimeTriple'][:2] for p in family['ranges']]:raise ValueError(LABEL+'.whole-owned-code:'+label)
        elif f['ownershipKind']=='closedIndirectTailProgram':
            if len(windows)!=1 or windows[0]['startRva']!=f['entryRva'] or any(a<w['endRva'] and w['startRva']<b for a,b,_ in unwind.entries.values() for w in windows):raise ValueError(LABEL+'.closed-tail-range:'+label)
        else:raise ValueError(LABEL+'.ownership-kind:'+label)
        image.check_windows(windows,label=LABEL+'.'+label);rr=[]
        for w in windows:
            raw=image.pe.bytes_at_va(base+w['startRva'],w['endRva']-w['startRva'])
            rr.extend(checked_rows(decode_rotate_instructions(image.mapper,raw,base+w['startRva']),raw,LABEL+'.'+label))
        return rr
    p={role:rows(f,role) for role,f in life['functions'].items()}
    for role in ('cleanup','initProxy'):
        f=life['functions'][role];call=f['actualParentCall'];raw=image.pe.bytes_at_va(base+call['siteRva'],5)
        if raw!=bytes.fromhex(call['instructionHex']) or raw[0]!=0xe8 or call['siteRva']+5+int.from_bytes(raw[1:],'little',signed=True)!=f['entryRva']:raise ValueError(LABEL+'.actual-child-call:'+role)
        if not any(w['startRva']<=call['siteRva'] and call['siteRva']+5<=w['endRva'] for w in life['functions']['initializer']['codeWindows']):raise ValueError(LABEL+'.child-call-ownership:'+role)
    decl=resolve_named_import_slots(image.pe,[life['initImportSlotRva'],life['deleteImportSlotRva']])
    if decl!=life['importDeclaration']:raise ValueError(LABEL+'.lifecycle-import-declarations')
    lifecycle=validate_handler_lifecycle(p,image_base=base,contract=life)
    sr=rows(setter['function'],'setter')
    for role,call in zip(('guardEnter','guardLeave'),setter['guardCalls']):
        raw=image.pe.bytes_at_va(base+call['siteRva'],5)
        if raw!=bytes.fromhex(call['instructionHex']) or raw[0]!=0xe8 or call['siteRva']+5+int.from_bytes(raw[1:],'little',signed=True)!=guard['functions'][role]['entryRva'] or call['targetRva']!=guard['functions'][role]['entryRva']:raise ValueError(LABEL+'.setter-guard-call:'+role)
        if not any(w['startRva']<=call['siteRva'] and call['siteRva']+5<=w['endRva'] for w in setter['function']['codeWindows']):raise ValueError(LABEL+'.setter-call-ownership:'+role)
    replace=validate_handler_setter(sr,entry_va=base+setter['function']['entryRva'],cookie_va=base+setter['globals']['cookie'],encoded_va=base+setter['globals']['encodedHandler'],
        guard_enter_va=base+guard['functions']['guardEnter']['entryRva'],guard_leave_va=base+guard['functions']['guardLeave']['entryRva'])
    return {'lifecycle':lifecycle,'setter':replace,'codeInstructions':lifecycle['codeInstructions']+replace['codeInstructions'],
        'definitionsOnly':True,'actualInitializationOrderProved':False,'allHandlerWritersGuardedProved':False,'wholeRootAdmitted':False,'runtimeExecutionKnown':False}


def validate_current_native_contract(*,gameassembly:Path,metadata:Path):
    life,setter=_read('lifecycle'),_read('setter');pins=life['nativeInputs']
    if pins!=setter['nativeInputs']:raise ValueError(LABEL+'.contract-build-consistency')
    before=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
    if before.status!='validated':return _skip(before.status,before.detail,pins)
    unity=Path(before.gameassembly).parent/'UnityPlayer.dll'
    def valid_unity():
        if not unity.is_file():return False
        with unity.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest().upper()==pins['UnityPlayer.dll']
    if not valid_unity():return _skip('mismatched' if unity.is_file() else 'missing','Selected UnityPlayer.dll missing or mismatched',pins)
    summary=_validate(open_native_image(before.gameassembly,before.metadata),life,setter)
    after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=before.gameassembly,metadata=before.metadata)
    if after.status!='validated' or not valid_unity():return _skip(after.status if after.status!='validated' else 'mismatched','Selected native inputs changed',pins)
    return {'status':'validated','scope':SCOPE,'nativeInputs':pins,'summary':summary,'evidenceBoundary':{'lifecycle':life['evidenceBoundary'],'setter':setter['evidenceBoundary']},
        'wholeRootAdmitted':False,'runtimeExecutionKnown':False,'actualInitializationOrderProved':False}
