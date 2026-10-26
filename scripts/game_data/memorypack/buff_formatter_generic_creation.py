"""Explicit-build generic creation control/count/cache evidence owner.

Authenticates the parent named count, allocator and shared receiver getter,
then checks the complete creation code/table partition and selected physical
flows. This is conditional native evidence, with no storage/root admission.
"""
from __future__ import annotations
from pathlib import Path
from types import SimpleNamespace
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import NATIVE_MAPPER_PATH,read_reviewed_contract
from scripts.game_data.il2cpp.protocol import load_native_mapper
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.il2cpp.generic_creation_control import validate_generic_creation_control
from scripts.game_data.memorypack import buff_formatter_class_creation as parent_owner
from scripts.game_data.memorypack import buff_formatter_field_construction as receiver_owner
from scripts.game_data.memorypack.corpus_gate import _fingerprint
from scripts.game_data.memorypack.native_owner import fail,proof_sources,validate_owner

LABEL='buffFormatterGenericCreation'
SCOPE='complete-owned-generic-creation-code-data-control-selected-count-cache-and-return-only'
PATH=CONTRACTS_DIR/'buff_formatter_generic_creation_native.json'


def _fail(check,expected,actual,*,native_inputs=None):
    fail(LABEL,SCOPE,PATH,check,expected,actual,native_inputs=native_inputs)


def _contract():
    c,_=read_reviewed_contract(PATH,schema='endfield.buff-formatter-generic-creation-native-contract.v1',status='exact-current-build',label=LABEL)
    if (c.get('scope'),c.get('parentContract'),c.get('receiverContract'))!=(SCOPE,parent_owner.PATH.name,receiver_owner.PATH.name):
        _fail('contract-shape','reviewed scope and parent/receiver owners',c.get('scope'),native_inputs=c.get('nativeInputs'))
    return c


def _proof_sources():
    return proof_sources(__file__,PATH,parent_owner._proof_sources()+receiver_owner._proof_sources(),NATIVE_MAPPER_PATH)


def _validate_selected(gameassembly,c,*,metadata_path):
    p=parent_owner._contract();receiver=receiver_owner._contract()
    if p['nativeInputs']!=c['nativeInputs'] or receiver['nativeInputs']!=c['nativeInputs']:
        _fail('parent-build','same selected native inputs','parent/receiver differs',native_inputs=c['nativeInputs'])
    if c['classFieldCount']!=p['classFieldCount'] or c['allocatorEntryJoin']!=p['allocatorEntryJoin']:
        _fail('named-count-and-allocator-provenance',(p['classFieldCount'],p['allocatorEntryJoin']),(c['classFieldCount'],c['allocatorEntryJoin']),native_inputs=c['nativeInputs'])
    if c['genericReceiver']!=receiver['genericReceiver'] or c['classGenericLink']!=receiver['classFields']['genericLink']:
        _fail('receiver-and-link-provenance','parent shared receiver getter and named generic link','selection differs',native_inputs=c['nativeInputs'])
    parent_summary=parent_owner._validate_selected(gameassembly,p,metadata_path=Path(metadata_path))
    mapper=load_native_mapper(NATIVE_MAPPER_PATH);pe=mapper.PeImage(Path(gameassembly));index=BodyIndex(SimpleNamespace(mapper=mapper,pe=pe,metadata=None))
    return {**validate_generic_creation_control(index,c),'actualNamedCountAllocatorAndReceiverParentProofRechecked':True,
        'checkedParentCreationInstructions':parent_summary['checkedInstructions'],
        'checkedParentMetadataCountRows':parent_summary['metadataCountRowsChecked'],'conditions':c['conditions']}


def validate_current_native_contract(*,gameassembly,metadata):
    def selected_body(selected_ga,c):return _validate_selected(selected_ga,c,metadata_path=Path(metadata))
    owner=SimpleNamespace(_contract=_contract,_proof_sources=_proof_sources,_fail=_fail,_fingerprint=_fingerprint,
        SCOPE=SCOPE,check_installed_native_inputs=check_installed_native_inputs,_validate_selected=selected_body)
    return validate_owner(owner,gameassembly=gameassembly,metadata=metadata,
        open_claims={'completeTypedCreationEffectsProved':False,'cacheReloadEqualsPublishedOrAllocatedPointerProved':False,
            'actualAllocatedClassCacheAndPreparationReceiverIdentityProved':False,'creationCountEqualsLaterPreparationCountProved':False,
            'countUnchangedByChildOrAliasEffectsProved':False,'actualSynchronizationAndCacheOutcomeProved':False,
            'recursiveTerminationProved':False,'allocationCapacityAndInitializationOutcomeProved':False,
            'positiveListAdmitted':False,'wholeRootAdmitted':False},
        check='native-generic-creation-control',expected='complete owned code/table control, stores and normal frame; actual count/receiver/allocator/cache/return projections',phase='generic class creation')
