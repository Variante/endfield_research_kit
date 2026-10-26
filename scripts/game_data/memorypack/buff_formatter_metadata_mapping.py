"""Explicit-build mapping-slot and registration-return source evidence."""
from __future__ import annotations
from pathlib import Path
from types import SimpleNamespace
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import NATIVE_MAPPER_PATH, read_reviewed_contract
from scripts.game_data.il2cpp.protocol import load_native_mapper
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.il2cpp.metadata_mapping_control import validate_metadata_mapping_control
from scripts.game_data.memorypack import buff_formatter_metadata_loader as parent_owner
from scripts.game_data.memorypack.corpus_gate import _fingerprint
from scripts.game_data.memorypack.native_owner import fail, proof_sources, validate_owner

LABEL = 'buffFormatterMetadataMapping'
SCOPE = 'complete-owned-metadata-mapping-control-arguments-registration-slots-and-return-source-only'
PATH = CONTRACTS_DIR / 'buff_formatter_metadata_mapping_native.json'


def _fail(check, expected, actual, *, native_inputs=None):
    fail(LABEL, SCOPE, PATH, check, expected, actual, native_inputs=native_inputs)


def _contract():
    c, _ = read_reviewed_contract(PATH, schema='endfield.buff-formatter-metadata-mapping-native-contract.v1',
                                 status='exact-current-build', label=LABEL)
    if (c.get('scope'), c.get('parentContract')) != (SCOPE, parent_owner.PATH.name):
        _fail('contract-shape', 'reviewed scope and actual loader parent', c.get('scope'), native_inputs=c.get('nativeInputs'))
    return c


def _proof_sources():
    return proof_sources(__file__, PATH, parent_owner._proof_sources(), NATIVE_MAPPER_PATH)


def _validate_selected(gameassembly, c, *, metadata_path):
    p = parent_owner._contract()
    if p['nativeInputs'] != c['nativeInputs']:
        _fail('parent-build', 'same selected native inputs', 'parent differs', native_inputs=c['nativeInputs'])
    if p['mappingThunk']['targetEntryRva'] != c['mapping']['entryRva']:
        _fail('actual-mapping-parent', 'actual loader mapping thunk tail target', 'selection differs', native_inputs=c['nativeInputs'])
    parent = parent_owner._validate_selected(gameassembly, p, metadata_path=Path(metadata_path))
    mapper = load_native_mapper(NATIVE_MAPPER_PATH)
    pe = mapper.PeImage(Path(gameassembly))
    index = BodyIndex(SimpleNamespace(mapper=mapper, pe=pe, metadata=None))
    return {**validate_metadata_mapping_control(index, c), 'actualLoaderAndMappingThunkParentProofRechecked': True,
            'checkedParentLoaderInstructions': parent['checkedInstructions'], 'conditions': c['conditions']}


def validate_current_native_contract(*, gameassembly, metadata):
    def selected_body(selected_ga, c):
        return _validate_selected(selected_ga, c, metadata_path=Path(metadata))
    owner = SimpleNamespace(_contract=_contract, _proof_sources=_proof_sources, _fail=_fail, _fingerprint=_fingerprint,
        SCOPE=SCOPE, check_installed_native_inputs=check_installed_native_inputs, _validate_selected=selected_body)
    return validate_owner(owner, gameassembly=gameassembly, metadata=metadata,
        open_claims={'normalReturnEqualsOriginalViewResultProved': False, 'finalReturnNonnullOrValidProved': False,
            'childAliasesOrSlotNoninterferenceProved': False, 'actualMappedFileIdentityProved': False,
            'liveIatCalleeOrSynchronizationOutcomeProved': False, 'retryTerminationProved': False,
            'positiveListAdmitted': False, 'wholeRootAdmitted': False},
        check='native-metadata-mapping-control', expected='complete owned mapping control/frame, actual child arguments, mutable registration slots and fresh return', phase='metadata mapping')
