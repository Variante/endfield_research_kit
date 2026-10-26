"""Complete class-context CFG and conditional slot publication geometry."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.unwind_chains import UnwindChainIndex,read_exception_directory
from scripts.game_data.il2cpp.register_rotates import decode_rotate_instructions
from scripts.game_data.il2cpp.owned_partition import checked_rows
from scripts.game_data.il2cpp.context_slot_initializer_control import (validate_closed_initializer_graph,
    validate_slot_loop_geometry,validate_method_slot_argument_flow,validate_definition_range_prefix)
from . import buff_camera_base_constructor as base_owner

CONTRACT_PATH=CONTRACTS_DIR/'buff_camera_context_slot_publication_native.json'
SCHEMA='endfield.buff-camera-context-slot-publication-native-contract.v1'
LABEL='buffCameraContextSlotPublication'
def _skip(status,detail,pins):
    return {'status':status,'detail':detail,'nativeInputs':pins,'runtimeSlot7Observed':False,
        'actualColdTargetMatchesEntryProved':False,'positiveListGrammarProved':False,'wholeRootAdmitted':False,'runtimeExecutionKnown':False}


def _validate_image(image,c):
    def fail(check,expected,actual):
        raise ValueError(json.dumps({'validator':LABEL,'source':CONTRACT_PATH.as_posix(),'check':check,
            'expected':str(expected)[:1000],'actual':str(actual)[:1000]}))
    base_contract,_=read_reviewed_contract(CONTRACTS_DIR/c['baseConstructorContract'],schema=base_owner.SCHEMA,status='exact-current-build',label=LABEL)
    if base_contract['nativeInputs']!=c['nativeInputs']:fail('dependency-build',c['nativeInputs'],base_contract['nativeInputs'])
    base_join=base_owner._validate_image(image,base_contract)
    base=image.pe.image_base;directory,size,raw=read_exception_directory(image.pe)
    unwind=UnwindChainIndex(raw,lambda at,n:image.pe.bytes_at_va(base+at,n),table_rva=directory,image_size=size)
    f=c['function'];family=json.loads(json.dumps(unwind.family(f['entryRva'])))
    if family!=f['unwindFamily']:fail('complete-exception-family',f['unwindFamily'],family)
    windows=f['codeWindows']
    if [(w['startRva'],w['endRva']) for w in windows]!=[tuple(r['runtimeTriple'][:2]) for r in family['ranges']]:
        fail('complete-byte-range-membership',family['ranges'],windows)
    image.check_windows(windows,label=LABEL);rows=[]
    for w in windows:
        data=image.pe.bytes_at_va(base+w['startRva'],w['endRva']-w['startRva'])
        rows.extend(checked_rows(decode_rotate_instructions(image.mapper,data,base+w['startRva']),data,LABEL))
    graph=validate_closed_initializer_graph(rows,entry_va=base+f['entryRva'])
    if graph['instructionsChecked']!=f['instructionsChecked']:fail('complete-instruction-count',f['instructionsChecked'],graph['instructionsChecked'])
    sites={k:base+v for k,v in c['sites'].items()}
    geometry=validate_slot_loop_geometry(rows,loop_va=sites['loop'],suffix_va=sites['suffix'],publication_va=sites['publication'])
    method=validate_method_slot_argument_flow(rows,dispatch_va=sites['loop'],producer_va=sites['methodProducer'],key_va=sites['methodKey'],return_store_va=sites['methodReturnStore'])
    prefix=validate_definition_range_prefix(rows,range_va=sites['rangeResult'],selected_count_va=sites['selectedCount'],loop_setup_va=sites['loopSetup'])
    context=base_contract['classContext'];slot=next(r for r in context['entries'] if r['relativeSlot']==base_join['staticBaseContext']['inheritedConstructorSlot'])
    if slot['kind']!=method['selectedDefinitionKind']:fail('inherited-constructor-kind',method['selectedDefinitionKind'],slot['kind'])
    slot_offset=slot['relativeSlot']*geometry['outputSlotStrideBytes']
    if slot_offset!=c['consumer']['slotByteOffset'] or geometry['classPublicationOffset']!=c['consumer']['classContextOffset']:
        fail('constructor-consumer-slot-geometry',c['consumer'],[slot_offset,geometry['classPublicationOffset']])
    return {'completeInitializerGraph':graph,'rangePrefix':prefix,'slotLoopGeometry':geometry,
        'methodSlotArgumentFlow':method,'priorBaseConstructorJoins':base_join,
        'conditionalInheritedConstructorSlotByteOffset':slot_offset,'inheritedConstructorSlot':slot['relativeSlot'],
        'runtimeSlot7Observed':False,'actualColdTargetMatchesEntryProved':False,
        'condition':'The runtime class and module are compatible with the authenticated declared context; lookup selects its declared range, allocation/fill returns a valid array, and valid disjoint frame/definition/output storage and normal ABI-preserving callees hold. Actual slot values and resolver/cache selections remain unobserved.'}


def validate_current_native_contract(*,gameassembly:Path,metadata:Path):
    c,_=read_reviewed_contract(CONTRACT_PATH,schema=SCHEMA,status='exact-current-build',label=LABEL);pins=c['nativeInputs']
    gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
    if gate.status!='validated':return _skip(gate.status,gate.detail,pins)
    unity=Path(gate.gameassembly).parent/'UnityPlayer.dll'
    def unity_matches():
        if not unity.is_file():return False
        with unity.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest().upper()==pins['UnityPlayer.dll']
    if not unity_matches():return _skip('mismatched' if unity.is_file() else 'missing','Selected UnityPlayer.dll missing or mismatched',pins)
    summary=_validate_image(open_native_image(gate.gameassembly,gate.metadata),c)
    after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
    if after.status!='validated' or not unity_matches():return _skip(after.status if after.status!='validated' else 'mismatched','Selected native inputs changed',pins)
    return {'status':'validated','nativeInputs':pins,'summary':summary,'runtimeSlot7Observed':False,
        'actualColdTargetMatchesEntryProved':False,'positiveListGrammarProved':False,'wholeRootAdmitted':False,'runtimeExecutionKnown':False,
        'evidenceBoundary':c['evidenceBoundary']}
