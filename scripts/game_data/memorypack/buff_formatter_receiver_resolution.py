"""Explicit-build source getter/index/cache/metadata-constructor evidence.

Closed leaf programs are distinct from complete owned resolver coverage.
The all-record arithmetic bound and constructor/cache joins are conditional;
fresh cache views, live class identity and actual count equality remain open.
"""
from __future__ import annotations
from pathlib import Path
from types import SimpleNamespace
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import NATIVE_MAPPER_PATH,read_reviewed_contract
from scripts.game_data.il2cpp.protocol import load_native_mapper
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.il2cpp.receiver_resolution_control import validate_receiver_resolution_control
from scripts.game_data.memorypack import buff_formatter_generic_creation as parent_owner
from scripts.game_data.memorypack import buff_formatter_class_creation as creation_owner
from scripts.game_data.memorypack.corpus_gate import _fingerprint
from scripts.game_data.memorypack.native_owner import fail,proof_sources,validate_owner

LABEL='buffFormatterReceiverResolution'
SCOPE='closed-receiver-leaves-complete-owned-cache-resolver-selected-metadata-index-and-result-flows-only'
PATH=CONTRACTS_DIR/'buff_formatter_receiver_resolution_native.json'


def _fail(check,expected,actual,*,native_inputs=None):
    fail(LABEL,SCOPE,PATH,check,expected,actual,native_inputs=native_inputs)


def _contract():
    c,_=read_reviewed_contract(PATH,schema='endfield.buff-formatter-receiver-resolution-native-contract.v1',status='exact-current-build',label=LABEL)
    if (c.get('scope'),c.get('parentContract'),c.get('creationContract'))!=(SCOPE,parent_owner.PATH.name,creation_owner.PATH.name):
        _fail('contract-shape','reviewed scope and parent/constructor owners',c.get('scope'),native_inputs=c.get('nativeInputs'))
    return c


def _proof_sources():
    return proof_sources(__file__,PATH,parent_owner._proof_sources()+creation_owner._proof_sources(),NATIVE_MAPPER_PATH)


def _validate_selected(gameassembly,c,*,metadata_path):
    p=parent_owner._contract();creation=creation_owner._contract()
    if p['nativeInputs']!=c['nativeInputs'] or creation['nativeInputs']!=c['nativeInputs']:
        _fail('parent-build','same selected native inputs','parent/constructor differs',native_inputs=c['nativeInputs'])
    if c['genericReceiver']!=p['genericReceiver'] or c['nullableLeaf']['window']['startRva']!=p['genericReceiver']['tailTargetRva']:
        _fail('actual-receiver-continuation','actual shared getter tail target','selection differs',native_inputs=c['nativeInputs'])
    source=creation['function']['sourceAllocationPrefix']
    cells={'headerCellRva':source['headerPointerCellRva'],'baseCellRva':source['metadataBaseCellRva']}
    if c['recordLayout']!=creation['recordLayout'] or c['metadataSource']!=cells or c['constructorEntryRva']!=creation['function']['entryRva']:
        _fail('metadata-constructor-provenance','current record layout, same header/base cells and actual constructor entry','selection differs',native_inputs=c['nativeInputs'])
    parent_summary=parent_owner._validate_selected(gameassembly,p,metadata_path=Path(metadata_path))
    mapper=load_native_mapper(NATIVE_MAPPER_PATH);pe=mapper.PeImage(Path(gameassembly));index=BodyIndex(SimpleNamespace(mapper=mapper,pe=pe,metadata=None))
    count=parent_summary['checkedParentMetadataCountRows']
    return {**validate_receiver_resolution_control(index,c,record_count=count),
        'actualGetterCreationAndMetadataParentProofRechecked':True,'checkedParentGenericCreationInstructions':parent_summary['checkedInstructions'],
        'checkedCurrentNamedMetadataCountRows':count,'conditions':c['conditions']}


def validate_current_native_contract(*,gameassembly,metadata):
    def selected_body(selected_ga,c):return _validate_selected(selected_ga,c,metadata_path=Path(metadata))
    owner=SimpleNamespace(_contract=_contract,_proof_sources=_proof_sources,_fail=_fail,_fingerprint=_fingerprint,
        SCOPE=SCOPE,check_installed_native_inputs=check_installed_native_inputs,_validate_selected=selected_body)
    return validate_owner(owner,gameassembly=gameassembly,metadata=metadata,
        open_claims={'liveSourceClassCachePreparationIdentityProved':False,'actualReturnedClassCountEqualsSelectedMetadataWordProved':False,
            'cacheCheckPublicationAndReturnViewsEqualProved':False,'actualCacheIndexBoundsAndStorageProved':False,
            'actualLiveMetadataPointerOrGlobalStabilityProved':False,'actualSynchronizationOutcomeProved':False,
            'childAliasEffectsAndLaterCountCoherenceProved':False,'completeTypedResolverEffectsProved':False,
            'positiveListAdmitted':False,'wholeRootAdmitted':False},
        check='native-receiver-resolution-control',expected='closed leaves, all-record index geometry, complete owned resolver control/frame and actual constructor/cache/return joins',phase='receiver resolution')
