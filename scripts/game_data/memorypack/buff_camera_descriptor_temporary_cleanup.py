"""Selected old-array handoff, release thunk/body and ordinary import names."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.unwind_chains import UnwindChainIndex,read_exception_directory
from scripts.game_data.il2cpp.owned_partition import checked_rows
from scripts.game_data.il2cpp.descriptor_cache_insertion_control import decode_insertion_instructions
from scripts.game_data.il2cpp.descriptor_temporary_cleanup_control import validate_descriptor_temporary_cleanup
from scripts.game_data.il2cpp.descriptor_release_control import validate_release_tail,validate_descriptor_release_control
from scripts.game_data.il2cpp.pe_imports import resolve_named_import_slots
from . import buff_camera_descriptor_cache_rebuild as parent_owner

CONTRACT_PATH=CONTRACTS_DIR/'buff_camera_descriptor_temporary_cleanup_native.json'
SCHEMA='endfield.buff-camera-descriptor-temporary-cleanup-native-contract.v2'
LABEL='buffCameraDescriptorTemporaryCleanup'


def _skip(status,detail,pins):
    return {'status':status,'detail':detail,'nativeInputs':pins,'runtimeExecutionKnown':False,
        'actualDescriptorOrColdTargetSelected':False,'positiveListGrammarProved':False,'wholeRootAdmitted':False}


def _validate_image(image,c):
    def fail(check,expected,actual):
        raise ValueError(json.dumps({'validator':LABEL,'source':CONTRACT_PATH.as_posix(),
            'check':check,'expected':str(expected)[:1000],'actual':str(actual)[:1000]}))
    parent,_=read_reviewed_contract(CONTRACTS_DIR/c['parentContract'],schema=parent_owner.SCHEMA,status='exact-current-build',label=LABEL)
    if parent['nativeInputs']!=c['nativeInputs'] or parent['publicationContract']!=c['publicationContract']:
        fail('same-selected-parent-publication',c['nativeInputs'],parent)
    joined=parent_owner._validate_image(image,parent);base=image.pe.image_base
    if parent['calls']['cleanup']!=c['cleanup']['entryRva']:fail('actual-request-cleanup-call',c['cleanup']['entryRva'],parent['calls']['cleanup'])
    publication=joined['publicationControl']
    if {'offset':96,'bytes':8} not in publication['selectedBidirectionalFields']:
        fail('old-array-pointer-publication-field',(96,8),publication['selectedBidirectionalFields'])
    directory,size,raw=read_exception_directory(image.pe)
    unwind=UnwindChainIndex(raw,lambda at,n:image.pe.bytes_at_va(base+at,n),table_rva=directory,image_size=size)
    def rows_for(f):
        family=json.loads(json.dumps(unwind.family(f['entryRva'])))
        if family!=f['unwindFamily']:fail('complete-exception-family',f['unwindFamily'],family)
        if [(w['startRva'],w['endRva']) for w in f['codeWindows']]!=[tuple(r['runtimeTriple'][:2]) for r in family['ranges']]:
            fail('complete-range-membership',family['ranges'],f['codeWindows'])
        image.check_windows(f['codeWindows'],label=LABEL);rows=[]
        for w in f['codeWindows']:
            data=image.pe.bytes_at_va(base+w['startRva'],w['endRva']-w['startRva'])
            rows.extend(checked_rows(decode_insertion_instructions(image.mapper,data,base+w['startRva']),data,LABEL))
        if len(rows)!=f['checkedInstructionCount']:fail('instruction-count',f['checkedInstructionCount'],len(rows))
        return rows
    tail=c['releaseTail'];image.check_windows([tail['codeWindow']],label=LABEL)
    if tail['codeWindow']['startRva']!=tail['entryRva']:fail('tail-entry-window',tail['entryRva'],tail['codeWindow'])
    data=image.pe.bytes_at_va(base+tail['entryRva'],tail['codeWindow']['endRva']-tail['entryRva'])
    tail_rows=checked_rows(decode_insertion_instructions(image.mapper,data,base+tail['entryRva']),data,LABEL)
    tail_control=validate_release_tail(tail_rows,entry_va=base+tail['entryRva'],target_va=base+c['releaseBody']['entryRva'])
    if tail['targetRva']!=c['releaseBody']['entryRva']:fail('same-tail-release-body',c['releaseBody']['entryRva'],tail['targetRva'])
    cleanup=validate_descriptor_temporary_cleanup(rows_for(c['cleanup']),entry_va=base+c['cleanup']['entryRva'],release_va=base+tail['entryRva'])
    resolution=resolve_named_import_slots(image.pe,[r['iatCellRva'] for r in c['imports'].values()]);matched=[]
    for role,expected in c['imports'].items():
        actual=[r for r in resolution['selectedImports'] if r['slotRva']==expected['iatCellRva']]
        declaration=expected['declaration']
        if actual!=[declaration]:fail('exact-import-declaration:'+role,declaration,actual)
        matched.append({'iatCellRva':actual[0]['slotRva'],'name':actual[0]['symbolName'],'dll':actual[0]['libraryName'],
            'liveIatValueOrCalleeSelected':False})
    release=validate_descriptor_release_control(rows_for(c['releaseBody']),image_base=base,
        function={**c['releaseBody'],'ownedWindows':c['releaseBody']['codeWindows']},labels=c['labels'],
        globals=c['globals'],calls=c['calls'],imports=c['imports'])
    return {'cleanupControl':cleanup,'tailControl':tail_control,'releaseControl':release,'importDeclarations':matched,
        'importResolution':resolution,
        'priorRebuild':joined,'oldArrayFieldHandoffConditionallyJoined':True,
        'releaseSucceededProved':False,'runtimeIatBindingsObserved':False,'inputHeapOwnershipProved':False}


def validate_current_native_contract(*,gameassembly:Path,metadata:Path):
    c,_=read_reviewed_contract(CONTRACT_PATH,schema=SCHEMA,status='exact-current-build',label=LABEL);pins=c['nativeInputs']
    before=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
    if before.status!='validated':return _skip(before.status,before.detail,pins)
    unity=Path(before.gameassembly).parent/'UnityPlayer.dll'
    def unity_matches():
        if not unity.is_file():return False
        with unity.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest().upper()==pins['UnityPlayer.dll']
    if not unity_matches():return _skip('mismatched' if unity.is_file() else 'missing','Selected UnityPlayer.dll missing or mismatched',pins)
    summary=_validate_image(open_native_image(before.gameassembly,before.metadata),c)
    after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=before.gameassembly,metadata=before.metadata)
    if after.status!='validated' or not unity_matches():
        return _skip(after.status if after.status!='validated' else 'mismatched','Selected native inputs changed',pins)
    return {'status':'validated','nativeInputs':pins,'summary':summary,'runtimeExecutionKnown':False,
        'actualDescriptorOrColdTargetSelected':False,'positiveListGrammarProved':False,'wholeRootAdmitted':False,
        'evidenceBoundary':c['evidenceBoundary']}
