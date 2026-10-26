"""Conditional halving request and selected call-free publication effects.

The request is guarded capacity halving, not a bootstrap initializer.
Nonzero threshold, unsigned stored-count-minus-auxiliary-count below threshold,
and initial capacity above cutoff precede halving. Later FP comparisons may halve
again; cutoff ends iteration without proving a minimum for arbitrary inputs.
Guard exits yield zero AL. Selected replacement/publication/cleanup with normal
saved-register-preserving returns yields one AL. Every normal return clears
request byte. AL records path, not allocation/migration/cleanup success.

descriptor_cache_publication_control checks a call-free bidirectional byte/
DWORD/QWORD transfer of selected temporary/global fields, including capacity,
marker/triple and entries. Two packed blocks initially exchange, then threshold
calculations overwrite leading QWORDs and both request bytes clear: no whole-
object swap. Returned packed control has only one byte and one DWORD traced to
old global through scratch vector; remaining bytes are unmodelled entry stack,
not padding/known fields. Separate scalar QWORD transfer is exact. Separate
reads/writes are not atomic. FP numeric policy, effects, pointer history,
concurrent visibility and live descriptor/list/root admission remain open.
"""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.unwind_chains import UnwindChainIndex,read_exception_directory
from scripts.game_data.il2cpp.owned_partition import checked_rows
from scripts.game_data.il2cpp.descriptor_cache_insertion_control import decode_insertion_instructions
from scripts.game_data.il2cpp.descriptor_cache_publication_control import validate_descriptor_cache_publication_control
from scripts.game_data.il2cpp.descriptor_cache_rebuild_request_control import validate_descriptor_cache_rebuild_request
from . import buff_camera_descriptor_cache_insertion as parent_owner

CONTRACT_PATH=CONTRACTS_DIR/'buff_camera_descriptor_cache_rebuild_request_native.json'
SCHEMA='endfield.buff-camera-descriptor-cache-rebuild-request-native-contract.v1'
PUBLICATION_SCHEMA='endfield.buff-camera-descriptor-cache-publication-native-contract.v1'
LABEL='buffCameraDescriptorCacheRebuild'


def _skip(status,detail,pins):
    return {'status':status,'detail':detail,'nativeInputs':pins,'runtimeExecutionKnown':False,
        'actualDescriptorOrColdTargetSelected':False,'positiveListGrammarProved':False,'wholeRootAdmitted':False}


def _validate_image(image,c):
    def fail(check,expected,actual):
        raise ValueError(json.dumps({'validator':LABEL,'source':CONTRACT_PATH.as_posix(),
            'check':check,'expected':str(expected)[:1000],'actual':str(actual)[:1000]}))
    parent,_=read_reviewed_contract(CONTRACTS_DIR/c['parentContract'],schema=parent_owner.SCHEMA,status='exact-current-build',label=LABEL)
    publication,_=read_reviewed_contract(CONTRACTS_DIR/c['publicationContract'],schema=PUBLICATION_SCHEMA,status='exact-current-build',label=LABEL)
    if parent['nativeInputs']!=c['nativeInputs'] or publication['nativeInputs']!=c['nativeInputs']:
        fail('dependency-build',c['nativeInputs'],[parent['nativeInputs'],publication['nativeInputs']])
    if publication['parentContract']!=c['parentContract']:fail('same-insertion-owner',c['parentContract'],publication['parentContract'])
    joined=parent_owner._validate_image(image,parent);base=image.pe.image_base
    if parent['calls']['initializationCandidate']!=c['function']['entryRva'] or parent['calls']['publishCandidate']!=publication['function']['entryRva']:
        fail('actual-insertion-child-targets',[c['function']['entryRva'],publication['function']['entryRva']],parent['calls'])
    if c['calls']['publication']!=publication['function']['entryRva'] or c['calls']['replacement']!=parent['calls']['replacementCandidate']:
        fail('actual-request-call-joins',publication['function']['entryRva'],c['calls'])
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
    f=publication['function'];published=validate_descriptor_cache_publication_control(rows_for(f),image_base=base,
        function={**f,'ownedWindows':f['codeWindows']},labels=publication['labels'],globals=publication['globals'])
    f=c['function'];request=validate_descriptor_cache_rebuild_request(rows_for(f),image_base=base,
        function={**f,'ownedWindows':f['codeWindows']},labels=c['labels'],globals=c['globals'],calls=c['calls'])
    if publication['globals']['objectBase']!=parent['globals']['table'] or c['globals']['capacity']!=parent['globals']['capacity']:
        fail('same-selected-container-globals',parent['globals'],[publication['globals'],c['globals']])
    return {'publicationControl':published,'rebuildRequestControl':request,'priorInsertion':joined,
        'legacyInitializationCandidateIsSemanticInitProof':False,'successfulRebuildProved':False,
        'wholeObjectExactSwapProved':False,'atomicPublicationProved':False,'runtimeSelectionKnown':False,
        'publicationEvidenceBoundary':publication['evidenceBoundary']}


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
        'evidenceBoundary':{'request':c['evidenceBoundary'],'publication':summary['publicationEvidenceBoundary']}}
