"""Gate creation count origins against explicit native and metadata inputs."""
from __future__ import annotations
import struct
from pathlib import Path
from types import SimpleNamespace
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import NATIVE_MAPPER_PATH,METADATA_HELPER_PATH,read_reviewed_contract
from scripts.game_data.il2cpp.protocol import load_native_mapper,load_metadata_helper
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.il2cpp.class_creation_control import validate_class_creation_control
from scripts.game_data.memorypack import buff_formatter_field_setup as parent_owner
from scripts.game_data.memorypack.corpus_gate import _fingerprint
from scripts.game_data.memorypack.native_owner import fail,proof_sources,validate_owner

LABEL='buffFormatterClassCreation'
SCOPE='complete-owned-metadata-record-creation-control-selected-count-source-allocation-and-return-only'
PATH=CONTRACTS_DIR/'buff_formatter_class_creation_native.json'


def _fail(check,expected,actual,*,native_inputs=None):
    fail(LABEL,SCOPE,PATH,check,expected,actual,native_inputs=native_inputs)


def _contract():
    c,_=read_reviewed_contract(PATH,schema='endfield.buff-formatter-class-creation-native-contract.v1',status='exact-current-build',label=LABEL)
    if (c.get('scope'),c.get('parentContract'))!=(SCOPE,parent_owner.PATH.name):_fail('contract-shape','reviewed scope and parent',c.get('scope'),native_inputs=c.get('nativeInputs'))
    return c


def _proof_sources():
    return proof_sources(__file__,PATH,parent_owner._proof_sources()+[_fingerprint(METADATA_HELPER_PATH)],NATIVE_MAPPER_PATH)


def _metadata_record_layout(catalog,metadata):
    section=metadata.sections['typeDefinitions'];stride=metadata.type_record_size
    if not metadata.types:raise ValueError(LABEL+'.empty-type-definitions')
    next_at=catalog.parse_type_reference_prefix(metadata.buf,section.offset,stride)[-1]
    tail=catalog.parse_type_layout_tail(metadata.buf,next_at,stride)
    if tail[-1]-section.offset!=stride:raise ValueError(LABEL+'.metadata-record-size')
    count_start=tail[-1]-section.offset-24
    layout={'recordBytes':stride,'fieldCountWordOffset':count_start+4,'vtableCountWordOffset':count_start+10,
        'headerTypeDefinitionsOffsetField':8+8*list(metadata.sections).index('typeDefinitions')}
    header=struct.unpack_from('<i',metadata.buf,layout['headerTypeDefinitionsOffsetField'])[0]
    if header!=section.offset:raise ValueError(LABEL+'.metadata-header-section-offset')
    for t in metadata.types:
        at=section.offset+t.index*stride
        values=struct.unpack_from('<H',metadata.buf,at+layout['fieldCountWordOffset'])[0],struct.unpack_from('<H',metadata.buf,at+layout['vtableCountWordOffset'])[0]
        if values!=(t.field_count,t.vtable_count):raise ValueError(LABEL+'.metadata-count-word:'+str(t.index))
    return layout,len(metadata.types)


def _validate_selected(gameassembly,c,*,metadata_path):
    p=parent_owner._contract()
    if p['nativeInputs']!=c['nativeInputs']:_fail('parent-build','same selected native inputs','parent differs',native_inputs=c['nativeInputs'])
    if c['classFieldCount']!=p['classFields']['fieldCount'] or c['allocatorEntryJoin']!=p['allocatorEntryJoin']:_fail('named-count-and-allocator-provenance',(p['classFields']['fieldCount'],p['allocatorEntryJoin']),(c['classFieldCount'],c['allocatorEntryJoin']),native_inputs=c['nativeInputs'])
    catalog=load_metadata_helper(METADATA_HELPER_PATH);metadata=catalog.Metadata(Path(metadata_path))
    layout,count=_metadata_record_layout(catalog,metadata)
    if layout!=c['recordLayout']:_fail('current-metadata-record-layout',c['recordLayout'],layout,native_inputs=c['nativeInputs'])
    parent_summary=parent_owner._validate_selected(gameassembly,p)
    mapper=load_native_mapper(NATIVE_MAPPER_PATH);pe=mapper.PeImage(Path(gameassembly));index=BodyIndex(SimpleNamespace(mapper=mapper,pe=pe,metadata=None))
    return {**validate_class_creation_control(index,c),'actualNamedCountAndAllocatorParentProofRechecked':True,
        'checkedParentFieldSetupInstructions':parent_summary['checkedInstructions'],'metadataCountRowsChecked':count,
        'metadataRecordLayout':layout,'currentNamedMetadataFieldAndVtableCountWordsChecked':True,
        'metadataLayoutDoesNotProveLiveGlobalPointerIdentity':True,'conditions':c['conditions']}


def validate_current_native_contract(*,gameassembly,metadata):
    # This adapter feeds the same explicit metadata path to the body reader
    # and the standard before/after native gate, without reselecting it as an
    # additional library or modifying the shared owners' established API.
    def selected_body(selected_ga,c):return _validate_selected(selected_ga,c,metadata_path=Path(metadata))
    owner=SimpleNamespace(_contract=_contract,_proof_sources=_proof_sources,_fail=_fail,_fingerprint=_fingerprint,
        SCOPE=SCOPE,check_installed_native_inputs=check_installed_native_inputs,_validate_selected=selected_body)
    return validate_owner(owner,gameassembly=gameassembly,metadata=metadata,
        open_claims={'completeTypedCreationEffectsProved':False,'actualGlobalMetadataHeaderAndTablePointersProved':False,
            'actualAllocatedClassCacheAndPreparationReceiverIdentityProved':False,'creationCountEqualsLaterPreparationCountProved':False,
            'countUnchangedByChildOrAliasEffectsProved':False,'allocationCapacityAndInitializationOutcomeProved':False,
            'positiveListAdmitted':False,'wholeRootAdmitted':False},
        check='native-class-creation-control',expected='complete owned creation control/stores/frames, current named metadata counts and selected count/source/allocation/return projections',phase='metadata class creation')
