"""Explicit-build metadata-loader result/cache initialization evidence.

The complete initializer joins the source resolver's actual global cells.
The selected metadata layout proves the allocation quotient only under a
matching fresh header read. It does not authenticate a live mapped file,
resolve the allocator target, establish capacity or preserve later globals.
"""
from __future__ import annotations
import struct
from pathlib import Path
from types import SimpleNamespace
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import NATIVE_MAPPER_PATH,METADATA_HELPER_PATH,read_reviewed_contract
from scripts.game_data.il2cpp.protocol import load_native_mapper,load_metadata_helper
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.il2cpp.metadata_initialization_control import validate_metadata_initialization_control
from scripts.game_data.memorypack import buff_formatter_receiver_resolution as parent_owner
from scripts.game_data.memorypack.corpus_gate import _fingerprint
from scripts.game_data.memorypack.native_owner import fail,proof_sources,validate_owner

LABEL='buffFormatterMetadataInitialization'
SCOPE='complete-owned-metadata-initialization-control-selected-header-base-cache-stores-and-conditional-size-only'
PATH=CONTRACTS_DIR/'buff_formatter_metadata_initialization_native.json'


def _fail(check,expected,actual,*,native_inputs=None):
    fail(LABEL,SCOPE,PATH,check,expected,actual,native_inputs=native_inputs)


def _contract():
    c,_=read_reviewed_contract(PATH,schema='endfield.buff-formatter-metadata-initialization-native-contract.v1',status='exact-current-build',label=LABEL)
    if (c.get('scope'),c.get('parentContract'))!=(SCOPE,parent_owner.PATH.name):
        _fail('contract-shape','reviewed scope and parent resolver',c.get('scope'),native_inputs=c.get('nativeInputs'))
    return c


def _proof_sources():
    return proof_sources(__file__,PATH,parent_owner._proof_sources(),NATIVE_MAPPER_PATH)


def _metadata_section(c,metadata):
    section=metadata.sections['typeDefinitions'];field=c['recordLayout']['headerTypeDefinitionsOffsetField']
    offset,size=struct.unpack_from('<ii',metadata.buf,field)
    count=len(metadata.types)
    if (offset,size,metadata.type_record_size)!=(section.offset,section.size,c['recordLayout']['recordBytes']):
        raise ValueError(LABEL+'.current-metadata-section-layout')
    if offset<0 or size<0 or offset+size>len(metadata.buf) or size!=count*metadata.type_record_size:
        raise ValueError(LABEL+'.current-metadata-section-range')
    return size,count


def _validate_selected(gameassembly,c,*,metadata_path):
    p=parent_owner._contract()
    if p['nativeInputs']!=c['nativeInputs']:_fail('parent-build','same selected native inputs','parent differs',native_inputs=c['nativeInputs'])
    for key in ('metadataSource','cacheCellRva','recordLayout'):
        if c[key]!=p[key]:_fail('actual-resolver-'+key,p[key],c[key],native_inputs=c['nativeInputs'])
    parent=parent_owner._validate_selected(gameassembly,p,metadata_path=Path(metadata_path))
    catalog=load_metadata_helper(METADATA_HELPER_PATH);metadata=catalog.Metadata(Path(metadata_path))
    size,count=_metadata_section(c,metadata)
    if count!=parent['checkedCurrentNamedMetadataCountRows']:
        _fail('current-parent-record-count',parent['checkedCurrentNamedMetadataCountRows'],count,native_inputs=c['nativeInputs'])
    mapper=load_native_mapper(NATIVE_MAPPER_PATH);pe=mapper.PeImage(Path(gameassembly));index=BodyIndex(SimpleNamespace(mapper=mapper,pe=pe,metadata=None))
    return {**validate_metadata_initialization_control(index,c,section_bytes=size,record_count=count),
        'actualSourceResolverAndMetadataConstructorParentProofRechecked':True,
        'checkedParentReceiverResolutionInstructions':parent['checkedInstructions'],
        'currentNamedMetadataSectionSizeAndRecordCountChecked':True,'conditions':c['conditions']}


def validate_current_native_contract(*,gameassembly,metadata):
    def selected_body(selected_ga,c):return _validate_selected(selected_ga,c,metadata_path=Path(metadata))
    owner=SimpleNamespace(_contract=_contract,_proof_sources=_proof_sources,_fail=_fail,_fingerprint=_fingerprint,
        SCOPE=SCOPE,check_installed_native_inputs=check_installed_native_inputs,_validate_selected=selected_body)
    return validate_owner(owner,gameassembly=gameassembly,metadata=metadata,
        open_claims={'actualLoadedMetadataSourceIdentityProved':False,'liveHeaderAndCacheGlobalStabilityProved':False,
            'actualAllocatorTargetAndAllocationOutcomeProved':False,'actualCacheAllocationCapacityProved':False,
            'allChildAliasEffectsProved':False,'actualReturnedClassCountEqualsSelectedMetadataWordProved':False,
            'positiveListAdmitted':False,'wholeRootAdmitted':False},
        check='native-metadata-initialization-control',expected='complete owned initializer and actual resolver cells, current metadata size/count, conditional quotient and allocator-result/cache stores',phase='metadata initialization')
