"""Authenticate cache key construction and selected same-node record copies."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.enum_underlying_instructions import decode_enum_underlying_instructions
from scripts.game_data.il2cpp.name_cache_key_record_control import validate_name_cache_key_record
from scripts.game_data.il2cpp.owned_partition import checked_rows
from scripts.game_data.il2cpp.unwind_chains import UnwindChainIndex,read_exception_directory
from .core import CONTRACTS_DIR
LABEL='buffNameCacheKeyRecord';SCHEMA='endfield.buff-name-cache-key-record-native-contract.v2';SCOPE='complete-cache-construction-control-and-selected-key-record-node-copy';CONTRACT_PATH=CONTRACTS_DIR/'buff_name_cache_key_record_native.json'
def _skip(status,detail,pins):return {'status':status,'detail':detail,'scope':SCOPE,'nativeInputs':pins,'wholeRootAdmitted':False,'runtimeExecutionKnown':False,'lookupReturnedSystemInt32ClassProved':False}
def _check_string_section(image,c):
    section=image.metadata.sections['string'];offset=c['layout']['stringSectionHeader']
    raw=image.metadata.buf[offset:offset+4]
    if len(raw)!=4 or int.from_bytes(raw,'little',signed=True)!=section.offset:
        raise ValueError(LABEL+'.string-section-header')

def _validate(image,c):
    base=image.pe.image_base;directory,size,raw=read_exception_directory(image.pe);unwind=UnwindChainIndex(raw,lambda at,n:image.pe.bytes_at_va(base+at,n),table_rva=directory,image_size=size);programs={}
    for role,f in c['functions'].items():
        family=json.loads(json.dumps(unwind.family(f['entryRva'])))
        if family!=f['unwindFamily'] or [[w['startRva'],w['endRva']] for w in f['codeWindows']]!=[p['runtimeTriple'][:2] for p in family['ranges']]:raise ValueError(LABEL+'.whole-owned-code:'+role)
        image.check_windows(f['codeWindows'],label=LABEL+'.'+role);rows=[]
        for w in f['codeWindows']:
            b=image.pe.bytes_at_va(base+w['startRva'],w['endRva']-w['startRva']);rows.extend(checked_rows(decode_enum_underlying_instructions(image.mapper,b,base+w['startRva']),b,LABEL+'.'+role))
        programs[role]=rows
    old,_=read_reviewed_contract(CONTRACTS_DIR/'buff_class_name_lookup_native.json',schema='endfield.buff-class-name-lookup-native-contract.v1',status='exact-current-build',label=LABEL)
    if old['nativeInputs']!=c['nativeInputs'] or c['functions']['caller']['entryRva']!=old['functions']['cacheInsert']['entryRva'] or c['globals']!={k:old['globals'][k] for k in ('metadataHeader','metadataBase')}:raise ValueError(LABEL+'.same-caller-and-metadata')
    _check_string_section(image,c)
    if (c['layout']['namespace'],c['layout']['name'],c['layout']['record'],1<<c['layout']['nodeShift'])!=(old['layout']['keyNamespace'],old['layout']['keyName'],old['layout']['nodeRecord'],1<<old['layout']['nodeShift']):raise ValueError(LABEL+'.same-key-node-layout')
    return validate_name_cache_key_record(programs,image_base=base,contract=c)
def validate_current_native_contract(*,gameassembly:Path,metadata:Path):
    c,_=read_reviewed_contract(CONTRACT_PATH,schema=SCHEMA,status='exact-current-build',label=LABEL)
    if c.get('scope')!=SCOPE:raise ValueError(LABEL+'.scope')
    pins=c['nativeInputs'];before=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
    if before.status!='validated':return _skip(before.status,before.detail,pins)
    unity=Path(before.gameassembly).parent/'UnityPlayer.dll'
    def valid_unity():return unity.is_file() and hashlib.sha256(unity.read_bytes()).hexdigest().upper()==pins['UnityPlayer.dll']
    if not valid_unity():return _skip('mismatched' if unity.is_file() else 'missing','Selected UnityPlayer.dll missing or mismatched',pins)
    summary=_validate(open_native_image(before.gameassembly,before.metadata),c)
    after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=before.gameassembly,metadata=before.metadata)
    if after.status!='validated' or not valid_unity():return _skip(after.status if after.status!='validated' else 'mismatched','Selected native inputs changed',pins)
    return {'status':'validated','scope':SCOPE,'nativeInputs':pins,'summary':summary,'evidenceBoundary':c['evidenceBoundary'],'wholeRootAdmitted':False,'runtimeExecutionKnown':False,'lookupReturnedSystemInt32ClassProved':False}
