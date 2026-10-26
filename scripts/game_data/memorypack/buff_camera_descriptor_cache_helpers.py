"""Comparator effects and conditional empty-iterator stores on selected bytes.

The comparator has no exception entry: closed_leaf_entry checks its complete
reachable bounded call-free CFG, refusing escaping/interior branches, without
claiming unused bytes or physical extent. Unequal DWORD wrapper markers return
zero AL; equal nonzero markers return one without triple reads; equal zeros
require all three QWORDs equal. Upper RAX is not the Boolean result. No memory
is written; only RAX/RCX/R8 change among general registers, preserving R9/R10/R11.
Actual caller bytes join those effects to probe/iterator state.

The iterator stores table/current/end at distinct QWORD offsets and returns
original output; equal initial current/end skips scanning. Otherwise scanning
uses entry stride and the comparator, without termination proof; R11 is preserved.
The empty helper supplies output, two separately computed ends and fifth stack
argument. Ends sample one capacity but separate begin-global reads. Equal reads
and valid storage give current=end, no scan, and original output via R11.
Together with zero-flag probe/caller proof, coherent key/current/end globals
exclude an empty-output false hit conditionally. Concurrent history, opaque-call
key changes, later globals/contents and runtime selection remain open; no root.
"""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.unwind_chains import UnwindChainIndex,read_exception_directory
from scripts.game_data.il2cpp.register_rotates import decode_rotate_instructions
from scripts.game_data.il2cpp.owned_partition import checked_rows
from scripts.game_data.il2cpp.closed_leaf_entry import decode_closed_leaf_entry
from scripts.game_data.il2cpp.descriptor_cache_helper_control import (
    validate_probe_leaf,validate_iterator_constructor,validate_empty_output_bridge)
from . import buff_camera_descriptor_cache_lookup as parent_owner

CONTRACT_PATH=CONTRACTS_DIR/'buff_camera_descriptor_cache_helpers_native.json'
SCHEMA='endfield.buff-camera-descriptor-cache-helpers-native-contract.v1'
LABEL='buffCameraDescriptorCacheHelpers'


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
    calls=joined['lookupControl']['calls']
    expected=[c['emptyOutput']['entryRva'],c['probe']['entryRva']]
    if [r['target']-base for r in calls]!=expected:fail('actual-lookup-child-call-targets',expected,calls)
    p=c['probe'];image.check_windows([p['codeWindow']],label=LABEL)
    if p['codeWindow']['startRva']!=p['entryRva']:fail('probe-entry-window',p['entryRva'],p['codeWindow'])
    raw=image.pe.bytes_at_va(base+p['entryRva'],p['codeWindow']['endRva']-p['entryRva'])
    program=decode_closed_leaf_entry(image.mapper,raw,base+p['entryRva'])
    if b''.join(bytes.fromhex(r['bytes']) for r in program['rows'])!=raw:
        fail('closed-reachable-byte-partition','all selected bytes reached without overlap',program['rows'])
    probe=validate_probe_leaf(program,entry_va=base+p['entryRva'],labels=p['labels'])
    if len(program['rows'])!=p['checkedInstructionCount']:fail('probe-instruction-count',p['checkedInstructionCount'],len(program['rows']))
    directory,size,table=read_exception_directory(image.pe)
    unwind=UnwindChainIndex(table,lambda at,n:image.pe.bytes_at_va(base+at,n),table_rva=directory,image_size=size)
    def rows_for(f):
        family=json.loads(json.dumps(unwind.family(f['entryRva'])))
        if family!=f['unwindFamily']:fail('complete-exception-family',f['unwindFamily'],family)
        if [(w['startRva'],w['endRva']) for w in f['codeWindows']]!=[tuple(r['runtimeTriple'][:2]) for r in family['ranges']]:
            fail('complete-range-membership',family['ranges'],f['codeWindows'])
        image.check_windows(f['codeWindows'],label=LABEL);rows=[]
        for w in f['codeWindows']:
            data=image.pe.bytes_at_va(base+w['startRva'],w['endRva']-w['startRva'])
            rows.extend(checked_rows(decode_rotate_instructions(image.mapper,data,base+w['startRva']),data,LABEL))
        if len(rows)!=f['checkedInstructionCount']:fail('instruction-count',f['checkedInstructionCount'],len(rows))
        return rows
    constructor=validate_iterator_constructor(rows_for(c['constructor']),image_base=base,function=c['constructor'],
        segments=c['constructorSegments'],labels=c['constructorLabels'],globals=c['globals'],probe_rva=p['entryRva'],probe=probe)
    empty=validate_empty_output_bridge(rows_for(c['emptyOutput']),image_base=base,entry_rva=c['emptyOutput']['entryRva'],
        globals=c['globals'],constructor_rva=c['constructor']['entryRva'],constructor=constructor)
    if not joined['lookupControl']['zeroFlagExplicitProbeHitRequiresThreeQwordEquality'] or joined['callerArgumentBridge']['lookupWrapperFlag']!=0:
        fail('zero-flag-caller-and-explicit-hit-join',True,joined)
    if c['globals']['capacity']!=parent['globals']['capacity'] or c['globals']['begin']!=parent['globals']['begin']:
        fail('same-caller-lookup-end-globals',parent['globals'],c['globals'])
    return {'probeControl':probe,'iteratorConstructorControl':constructor,'emptyOutputControl':empty,'priorLookup':joined,
        'probeLoopRegistersR9R10R11Preserved':True,'conditionalEmptyCurrentEqualsEnd':True,
        'callerHitTripleEqualityConditionalOnCoherentZeroFlagKeyAndGlobals':True,
        'unconditionalCallerHitTripleEqualityProved':False,'insertionAndLaterPointeeEffectsProved':False,
        'conditions':'Coherent zero-flag local query key, stable compatible table/current/end globals, readable operands and disjoint writable output/frame storage. This proves sampled native field flow, not runtime selection or concurrent cache history.'}


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
