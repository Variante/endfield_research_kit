"""Current physical normalization proof; no concrete formatter or root admission."""
from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.normalization_control import validate_normalization
from scripts.game_data.il2cpp.normalization_instructions import decode_normalization_instructions
from scripts.game_data.il2cpp.owned_partition import check_byte_partition, checked_rows
from scripts.game_data.il2cpp.unwind_chains import UnwindChainIndex, read_exception_directory
from .core import CONTRACTS_DIR

LABEL='buffGenericNormalization'
SCHEMA='endfield.buff-generic-normalization-native-contract.v1'
SCOPE='complete-physical-normalization-and-proved-stack-probe-register-preservation'
CONTRACT_PATH=CONTRACTS_DIR/'buff_generic_normalization_native.json'


def _contract():
    c,_=read_reviewed_contract(CONTRACT_PATH,schema=SCHEMA,status='exact-current-build',label=LABEL)
    if c.get('scope')!=SCOPE or set(c['functions'])!={'first','second','probe'}:
        raise ValueError(LABEL+'.scope-or-functions')
    return c


def _skip(status,detail,pins):
    return {'status':status,'detail':detail,'nativeInputs':pins,'scope':SCOPE,
            'concreteGenericSharingSelected':False,'positiveStoredGrammarAdmitted':False,
            'wholeRootAdmitted':False,'runtimeExecutionKnown':False}


def _validate_image(image,c):
    base=image.pe.image_base
    directory,size,raw=read_exception_directory(image.pe)
    unwind=UnwindChainIndex(raw,lambda at,n:image.pe.bytes_at_va(base+at,n),table_rva=directory,image_size=size)
    programs={};families={}
    for key,f in c['functions'].items():
        family=json.loads(json.dumps(unwind.family(f['entryRva'])))
        if family!=f['unwindFamily']:raise ValueError(LABEL+'.unwind-parent-triples:'+key)
        owned=[(w['startRva'],w['endRva']) for w in f['ownedWindows']]
        if len(owned)!=len(family['ranges']) or set(owned)!={tuple(r['runtimeTriple'][:2]) for r in family['ranges']}:
            raise ValueError(LABEL+'.owned-window-membership:'+key)
        image.check_windows(f['ownedWindows'],label=LABEL)
        pieces=[(w['startRva'],w['endRva'],role) for role in ('codeWindows','dataWindows') for w in f[role]]
        check_byte_partition(owned,pieces,LABEL+'.'+key)
        rows=[]
        for w in f['codeWindows']:
            image.check_windows([w],label=LABEL)
            data=image.pe.bytes_at_va(base+w['startRva'],w['endRva']-w['startRva'])
            rows.extend(checked_rows(decode_normalization_instructions(image.mapper,data,base+w['startRva']),data,LABEL))
        image.check_windows(f['dataWindows'],label=LABEL)
        if [[int(r['va'],16)-base,bytes.fromhex(r['bytes']).hex().upper()] for r in rows]!=f['program']:
            raise ValueError(LABEL+'.complete-code-bytes:'+key)
        programs[key]=rows;families[key]=family
    table=c['table']
    windows=c['functions']['first']['dataWindows']
    if len(windows)!=1 or (windows[0]['startRva'],windows[0]['endRva'])!=(table['startRva'],table['endRva']):
        raise ValueError(LABEL+'.table-membership')
    data=image.pe.bytes_at_va(base+table['startRva'],table['endRva']-table['startRva'])
    targets=[x[0] for x in struct.iter_unpack('<I',data)]
    if targets!=table['targetsRva'] or set(targets)!={r['entryRva'] for r in table['casesInCodeOrder']}:
        raise ValueError(LABEL+'.table-targets')
    caller=c['callerPhysicalSource']
    if json.loads(json.dumps(unwind.family(caller['entryRva'])))!=caller['unwindFamily']:
        raise ValueError(LABEL+'.caller-parent-triples')
    image.check_windows(caller['codeWindows'],label=LABEL)
    ranges=[tuple(r['runtimeTriple'][:2]) for r in caller['unwindFamily']['ranges']]
    if len(caller['codeWindows'])!=len(ranges) or {(w['startRva'],w['endRva']) for w in caller['codeWindows']}!=set(ranges):
        raise ValueError(LABEL+'.caller-owned-membership')
    for edge in c['actualParentCalls']:
        at=edge['siteRva'];data=image.pe.bytes_at_va(base+at,5)
        if (data[0]!=0xe8 or data.hex().upper()!=edge['instructionHex'] or
                at+5+int.from_bytes(data[1:],'little',signed=True)!=edge['targetRva'] or
                not any(a<=at and at+5<=b for a,b in ranges)):
            raise ValueError(LABEL+'.actual-parent-call')
    summary=validate_normalization(programs,image_base=base,contract=c)
    summary['unwindFamilies']=families
    summary['actualParentCalls']=c['actualParentCalls']
    summary['callerFullCacheOrProviderSemanticsProved']=False
    return summary


def validate_current_native_contract(*,gameassembly:Path,metadata:Path):
    c=_contract();pins=c['nativeInputs']
    before=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
    if before.status!='validated':return _skip(before.status,before.detail,pins)
    unity=Path(before.gameassembly).parent/'UnityPlayer.dll'
    def unity_matches():return unity.is_file() and hashlib.sha256(unity.read_bytes()).hexdigest().upper()==pins['UnityPlayer.dll']
    if not unity_matches():return _skip('mismatched' if unity.is_file() else 'missing','Selected UnityPlayer.dll missing or mismatched',pins)
    summary=_validate_image(open_native_image(before.gameassembly,before.metadata),c)
    after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=before.gameassembly,metadata=before.metadata)
    if after.status!='validated' or not unity_matches():
        return _skip(after.status if after.status!='validated' else 'mismatched','Selected native inputs changed during normalization proof',pins)
    return {'status':'validated','nativeInputs':pins,'scope':SCOPE,'summary':summary,
            'concreteGenericSharingSelected':False,'positiveStoredGrammarAdmitted':False,
            'wholeRootAdmitted':False,'runtimeExecutionKnown':False,'evidenceBoundary':c['evidenceBoundary']}
