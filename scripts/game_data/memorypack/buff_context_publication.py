"""Authenticate the complete second context physical publication program."""
from __future__ import annotations
from pathlib import Path
from types import SimpleNamespace
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.il2cpp.native_image import (
    open_native_image, read_reviewed_contract, METADATA_HELPER_PATH, NATIVE_MAPPER_PATH,
)
from scripts.game_data.il2cpp.protocol import load_metadata_helper
from scripts.game_data.il2cpp.class_creation_instructions import decode_class_creation_instructions
from scripts.game_data.il2cpp.class_creation_control import validate_class_creation_control
from scripts.game_data.il2cpp.context_publication_sources import (
    metadata_publication_columns, prove_creation_publication_sources, validate_context_publication_program,
)
from scripts.game_data.il2cpp.context_setup_control import validate_context_setup_control
from scripts.game_data.il2cpp.dispatch_fallback_control import validate_dispatch_fallback_control
from scripts.game_data.il2cpp.owned_partition import owned_windows, checked_rows, check_byte_partition
from scripts.game_data.memorypack import buff_formatter_context_setup as setup_owner
from scripts.game_data.memorypack import buff_formatter_class_creation as creation_owner
from scripts.game_data.memorypack import buff_formatter_dispatch_fallback as dispatch_owner
from scripts.game_data.memorypack import buff_condition_context_adapter as adapter_owner
from scripts.game_data.memorypack.corpus_gate import _fingerprint
from scripts.game_data.memorypack.native_owner import fail, proof_sources, validate_owner

LABEL = 'buffContextPublication'
SCHEMA = 'endfield.buff-context-publication-native-contract.v2'
SCOPE = 'complete-second-context-physical-field-call-and-publication-program'
PATH = CONTRACTS_DIR/'buff_context_publication_native.json'


def _fail(check, expected, actual, *, native_inputs=None):
    fail(LABEL, SCOPE, PATH, check, expected, actual, native_inputs=native_inputs)


def _contract():
    c, _ = read_reviewed_contract(PATH, schema=SCHEMA, status='exact-current-build', label=LABEL)
    if c.get('scope') != SCOPE or c.get('parentContracts') != {
        'setup':setup_owner.PATH.name,'creation':creation_owner.PATH.name,'dispatch':dispatch_owner.PATH.name,
        'adapter':adapter_owner.PATH.name}:
        _fail('contract-shape','reviewed scope and actual parent declarations',c.get('scope'))
    return c


def _proof_sources():
    return proof_sources(__file__,PATH,setup_owner._proof_sources()+creation_owner._proof_sources()+
        dispatch_owner._proof_sources()+adapter_owner._proof_sources()+[_fingerprint(METADATA_HELPER_PATH)],NATIVE_MAPPER_PATH)


def _validate_selected(gameassembly, c, *, metadata_path):
    context, creation, dispatch, adapter = [owner._contract() for owner in (setup_owner,creation_owner,dispatch_owner,adapter_owner)]
    if any(parent['nativeInputs']!=c['nativeInputs'] for parent in (context,creation,dispatch,adapter)):
        raise ValueError(LABEL+'.parent-native-build-differs')
    l=c['layout'];f=next(f for f in context['functions'] if f['role']=='second')
    if (dispatch['calls']['prepareSecond']!=f['entryRva'] or l['selfPointer']!=dispatch['layout']['prepareArgumentPointer']
        or l['linkedPointer']!=f['addressHandoff']['linkedReceiver']):
        raise ValueError(LABEL+'.actual-prepare-child-and-physical-layout-join')
    image=open_native_image(Path(gameassembly),Path(metadata_path));index=BodyIndex(image)
    # Existing full CFG/ownership/frame algorithms remain the source of truth.
    # Selected new value-flow grammars extend them without widening root readers.
    setup_summary=validate_context_setup_control(index,context)
    creation_summary=validate_class_creation_control(index,creation)
    dispatch_summary=validate_dispatch_fallback_control(index,dispatch)
    columns=metadata_publication_columns(load_metadata_helper(METADATA_HELPER_PATH),image.metadata)
    if columns!=c['metadataColumns']:raise ValueError(LABEL+'.named-metadata-publication-columns')
    owned,pieces,windows=owned_windows(index,creation['function'],LABEL);rows=[]
    for category,_,start,raw in windows:
        if category!='codeWindows':raise ValueError(LABEL+'.unreviewed-creation-piece')
        rows+=checked_rows(decode_class_creation_instructions(image.mapper,raw,start),raw,LABEL)
    check_byte_partition(owned,pieces,LABEL);rows.sort(key=lambda r:int(r['va'],16))
    sources=prove_creation_publication_sources(rows,image.pe.image_base,creation,l,columns)
    if sources!=c['creationPublicationSources']:raise ValueError(LABEL+'.creation-publication-sources')
    globals_=c['program']['globals'];prefix=creation['function']['sourceAllocationPrefix']
    for key in ('headerPointerCellRva','metadataBaseCellRva','registrationCellRva','allocatorContextCellRva'):
        if globals_[key]!=prefix[key]:raise ValueError(LABEL+'.creation-and-writer-global-cell-join:'+key)
    program=validate_context_publication_program(index,context,c)
    adapter_summary=adapter_owner._validate_selected(gameassembly,adapter,metadata_path=metadata_path)
    reads=adapter_summary['adapter']['unconditionalInputReads']
    if len(reads)!=2 or reads[1]['memoryBytes']!=4 or reads[1]['byteOffset']!=l['selectorDword']:
        raise ValueError(LABEL+'.actual-adapter-selector-read-and-repair-store-join')
    return {'creationPublicationSources':sources,'metadataColumns':columns,'publicationProgram':program,
        'actualPreparationSecondChildJoinChecked':True,
        'actualAdapterSelectorReadAndPostCreationRepairDwordOffsetJoined':True,
        'checkedRelatedAdapterInstructions':adapter_summary['adapter']['checkedInstructions'],
        'checkedRelatedFallbackInstructions':adapter_summary['fallback']['checkedInstructions'],
        'checkedFullSetupInstructions':setup_summary['checkedInstructions'],
        'checkedFullCreationInstructions':creation_summary['checkedInstructions'],
        'checkedFullPreparationAndResolverInstructions':dispatch_summary['checkedInstructions'],
        'conditions':c['conditions']}


def validate_current_native_contract(*, gameassembly, metadata):
    def body(selected_ga,c):return _validate_selected(selected_ga,c,metadata_path=Path(metadata))
    owner=SimpleNamespace(_contract=_contract,_proof_sources=_proof_sources,_fail=_fail,_fingerprint=_fingerprint,
        SCOPE=SCOPE,check_installed_native_inputs=check_installed_native_inputs,_validate_selected=body)
    return validate_owner(owner,gameassembly=gameassembly,metadata=metadata,
        open_claims={'runtimePreparedReceiverMetadataInterfaceOrPairIdentityProved':False,
            'actualAllocationCapacityOrLookupOutcomeProved':False,
            'lookupInflationAndSpecialChildrenIdentitiesEffectsAndTerminationProved':False,
            'wholeConditionExecutionProved':False,'wholeRootAdmitted':False},
        check='native-context-publication-program',expected='current creation sources and complete second physical field/argument/pair/selector/special program',
        phase='Buff context publication')
