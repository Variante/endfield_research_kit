"""Current insertion control and conditional entry/output stores."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.unwind_chains import UnwindChainIndex,read_exception_directory
from scripts.game_data.il2cpp.owned_partition import checked_rows
from scripts.game_data.il2cpp.descriptor_cache_insertion_control import decode_insertion_instructions,validate_descriptor_cache_insertion_control
from . import buff_camera_descriptor_cache_helpers as parent_owner

CONTRACT_PATH=CONTRACTS_DIR/'buff_camera_descriptor_cache_insertion_native.json'
SCHEMA='endfield.buff-camera-descriptor-cache-insertion-native-contract.v1'
LABEL='buffCameraDescriptorCacheInsertion'


def _skip(status,detail,pins):
    return {'status':status,'detail':detail,'nativeInputs':pins,'runtimeExecutionKnown':False,
        'actualDescriptorOrColdTargetSelected':False,'positiveListGrammarProved':False,'wholeRootAdmitted':False}


def _validate_image(image,c):
    def fail(check,expected,actual):
        raise ValueError(json.dumps({'validator':LABEL,'source':CONTRACT_PATH.as_posix(),
            'check':check,'expected':str(expected)[:1000],'actual':str(actual)[:1000]}))
    parent,_=read_reviewed_contract(CONTRACTS_DIR/c['parentContract'],schema=parent_owner.SCHEMA,status='exact-current-build',label=LABEL)
    if parent['nativeInputs']!=c['nativeInputs']:fail('dependency-build',c['nativeInputs'],parent['nativeInputs'])
    joined=parent_owner._validate_image(image,parent);base=image.pe.image_base
    composition=joined['priorLookup']['priorComposition']['compositionControl']
    direct=[r for r in composition['calls'] if r['kind']=='call']
    if len(direct)!=3 or direct[2]['target']-base!=c['function']['entryRva']:
        fail('actual-composition-insertion-call',c['function']['entryRva'],direct)
    if parent['probe']['entryRva']!=c['calls']['probe']:fail('same-proved-probe',parent['probe']['entryRva'],c['calls']['probe'])
    directory,size,raw=read_exception_directory(image.pe)
    unwind=UnwindChainIndex(raw,lambda at,n:image.pe.bytes_at_va(base+at,n),table_rva=directory,image_size=size)
    f=c['function'];family=json.loads(json.dumps(unwind.family(f['entryRva'])))
    if family!=f['unwindFamily']:fail('complete-exception-family',f['unwindFamily'],family)
    if [(w['startRva'],w['endRva']) for w in f['codeWindows']]!=[tuple(r['runtimeTriple'][:2]) for r in family['ranges']]:
        fail('complete-range-membership',family['ranges'],f['codeWindows'])
    image.check_windows(f['codeWindows'],label=LABEL);rows=[]
    for w in f['codeWindows']:
        data=image.pe.bytes_at_va(base+w['startRva'],w['endRva']-w['startRva'])
        rows.extend(checked_rows(decode_insertion_instructions(image.mapper,data,base+w['startRva']),data,LABEL))
    control=validate_descriptor_cache_insertion_control(rows,image_base=base,function={**f,'ownedWindows':f['codeWindows']},
        segments=c['segments'],labels=c['labels'],globals=c['globals'],calls=c['calls'],probe=joined['probeControl'])
    if len(rows)!=f['checkedInstructionCount']:fail('instruction-count',f['checkedInstructionCount'],len(rows))
    if c['globals']['capacity']!=parent['globals']['capacity'] or c['globals']['begin']!=parent['globals']['begin'] or c['globals']['table']!=parent['globals']['table']:
        fail('shared-container-globals',parent['globals'],c['globals'])
    return {'insertionControl':control,'priorCacheHelpers':joined,
        'allocationPointerRetainedByCompositionConditionally':True,
        'insertionResultPointerReplacesSavedAllocationProved':False,
        'insertionAndLaterPointeeEffectsFullyProved':False,'runtimeSelectionKnown':False}


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
