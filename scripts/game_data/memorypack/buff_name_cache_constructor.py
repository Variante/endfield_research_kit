"""Authenticate complete conditional name-cache constructor defaults."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.word_immediate_stores import decode_word_store_instructions
from scripts.game_data.il2cpp.name_cache_constructor_control import validate_name_cache_constructor
from scripts.game_data.il2cpp.owned_partition import checked_rows, check_byte_partition
from scripts.game_data.il2cpp.unwind_chains import UnwindChainIndex, read_exception_directory
from .core import CONTRACTS_DIR

LABEL='buffNameCacheConstructor'
SCHEMA='endfield.buff-name-cache-constructor-native-contract.v1'
SCOPE='complete-conditional-cache-constructor-defaults'
CONTRACT_PATH=CONTRACTS_DIR/'buff_name_cache_constructor_native.json'


def _skip(status, detail, pins):
    return {'status':status,'detail':detail,'scope':SCOPE,'nativeInputs':pins,
        'wholeRootAdmitted':False,'runtimeExecutionKnown':False,'lookupReturnedSystemInt32ClassProved':False}


def _validate(image,c):
    base=image.pe.image_base;directory,size,raw=read_exception_directory(image.pe)
    unwind=UnwindChainIndex(raw,lambda at,n:image.pe.bytes_at_va(base+at,n),table_rva=directory,image_size=size)
    parent,_=read_reviewed_contract(CONTRACTS_DIR/'buff_class_name_lookup_native.json',
        schema='endfield.buff-class-name-lookup-native-contract.v1',status='exact-current-build',label=LABEL)
    if parent['nativeInputs']!=c['nativeInputs']:raise ValueError(LABEL+'.parent-build')
    parent_windows=parent['functions']['lookup']['ownedWindows']
    programs={}
    for role,f in c['functions'].items():
        windows=f['codeWindows'];owned=f['ownedWindows'];padding=f['paddingWindows']
        if f['ownershipKind']=='exceptionFamily':
            family=json.loads(json.dumps(unwind.family(f['entryRva'])))
            if family!=f['unwindFamily'] or [[w['startRva'],w['endRva']] for w in owned]!=[p['runtimeTriple'][:2] for p in family['ranges']]:
                raise ValueError(LABEL+'.whole-owned-code:'+role)
            check_byte_partition([(w['startRva'],w['endRva']) for w in owned],
                [(w['startRva'],w['endRva'],kind) for kind,ww in (('code',windows),('padding',padding)) for w in ww],LABEL+'.'+role)
            image.check_windows(owned,label=LABEL+'.owned-'+role)
            image.check_windows(padding,label=LABEL+'.padding-'+role)
            for w in padding:
                if image.pe.bytes_at_va(base+w['startRva'],w['endRva']-w['startRva'])!=b'\xcc':
                    raise ValueError(LABEL+'.padding-form')
        elif f['ownershipKind']=='closedNoCallProgram':
            if owned or padding or f['unwindFamily'] is not None or len(windows)!=1 or windows[0]['startRva']!=f['entryRva'] or any(a<w['endRva'] and w['startRva']<b for a,b,_ in unwind.entries.values() for w in windows):
                raise ValueError(LABEL+'.closed-program-range:'+role)
        else:raise ValueError(LABEL+'.ownership-kind:'+role)
        call=f['actualParentCall'];raw=image.pe.bytes_at_va(base+call['siteRva'],5)
        if raw[0]!=0xe8 or call['siteRva']+5+int.from_bytes(raw[1:],'little',signed=True)!=f['entryRva'] or call['targetRva']!=f['entryRva']:
            raise ValueError(LABEL+'.actual-parent-call:'+role)
        if 'instructionHex' in call and raw!=bytes.fromhex(call['instructionHex']):raise ValueError(LABEL+'.call-bytes:'+role)
        all_parent_windows=parent_windows+[w for p in c['functions'].values() for w in p['codeWindows']]
        containing=[w for w in all_parent_windows if w['startRva']<=call['siteRva'] and call['siteRva']+5<=w['endRva']]
        if not containing:raise ValueError(LABEL+'.parent-call-ownership:'+role)
        image.check_windows(containing,label=LABEL+'.parent-'+role)
        image.check_windows(windows,label=LABEL+'.'+role);rows=[]
        for w in windows:
            raw=image.pe.bytes_at_va(base+w['startRva'],w['endRva']-w['startRva'])
            rows.extend(checked_rows(decode_word_store_instructions(image.mapper,raw,base+w['startRva']),raw,LABEL+'.'+role))
        programs[role]=rows
    constant=c['thresholdConstant'];raw=image.pe.bytes_at_va(base+constant['rva'],4)
    if raw.hex().upper()!=constant['rawHex'] or hashlib.sha256(raw).hexdigest().upper()!=constant['sha256']:
        raise ValueError(LABEL+'.threshold-constant-bytes')
    return validate_name_cache_constructor(programs,raw,image_base=base,contract=c)


def validate_current_native_contract(*,gameassembly:Path,metadata:Path):
    c,_=read_reviewed_contract(CONTRACT_PATH,schema=SCHEMA,status='exact-current-build',label=LABEL)
    if c.get('scope')!=SCOPE:raise ValueError(LABEL+'.scope')
    pins=c['nativeInputs'];before=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
    if before.status!='validated':return _skip(before.status,before.detail,pins)
    unity=Path(before.gameassembly).parent/'UnityPlayer.dll'
    def unity_valid():
        if not unity.is_file():return False
        with unity.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest().upper()==pins['UnityPlayer.dll']
    if not unity_valid():return _skip('mismatched' if unity.is_file() else 'missing','Selected UnityPlayer.dll missing or mismatched',pins)
    summary=_validate(open_native_image(before.gameassembly,before.metadata),c)
    after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=before.gameassembly,metadata=before.metadata)
    if after.status!='validated' or not unity_valid():return _skip(after.status if after.status!='validated' else 'mismatched','Selected native inputs changed',pins)
    return {'status':'validated','scope':SCOPE,'nativeInputs':pins,'summary':summary,
        'evidenceBoundary':c['evidenceBoundary'],'wholeRootAdmitted':False,'runtimeExecutionKnown':False,'lookupReturnedSystemInt32ClassProved':False}
