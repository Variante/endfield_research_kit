"""Gate source and child-program joins for the Buff condition context fallback."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract, NATIVE_MAPPER_PATH, METADATA_HELPER_PATH
from scripts.game_data.il2cpp.protocol import load_metadata_helper
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.class_creation_instructions import decode_class_creation_instructions
from scripts.game_data.il2cpp.class_dispatch_sources import metadata_dispatch_count_columns, prove_creation_dispatch_sources, static_interface_context_bindings
from scripts.game_data.il2cpp.context_dispatch_joins import join_context_dispatch_programs
from scripts.game_data.il2cpp.dispatch_fallback_control import validate_dispatch_fallback_control
from scripts.game_data.memorypack import buff_condition_context_adapter as parent_owner
from scripts.game_data.memorypack import buff_formatter_dispatch_fallback as dispatch_owner
from scripts.game_data.memorypack import buff_formatter_resolver_scan as scan_owner
from scripts.game_data.memorypack import buff_formatter_class_creation as creation_owner
from scripts.game_data.memorypack.corpus_gate import _fingerprint
from scripts.game_data.memorypack.native_owner import fail, proof_sources, validate_owner

LABEL = 'buffConditionContextDispatch'
SCHEMA = 'endfield.buff-condition-context-dispatch-native-contract.v1'
SCOPE = 'context-fallback-actual-child-programs-allocated-self-interface-count-and-static-getter-pairs'
PATH = CONTRACTS_DIR/'buff_condition_context_dispatch_native.json'


def _fail(check, expected, actual, *, native_inputs=None):
    fail(LABEL, SCOPE, PATH, check, expected, actual, native_inputs=native_inputs)


def _contract():
    c, _ = read_reviewed_contract(PATH, schema=SCHEMA, status='exact-current-build', label=LABEL)
    if c.get('scope') != SCOPE or c.get('parentContract') != parent_owner.PATH.name or c.get('childContracts') != {
        'dispatch': dispatch_owner.PATH.name, 'scan': scan_owner.PATH.name, 'creation': creation_owner.PATH.name}:
        _fail('contract-shape', 'reviewed context parent and actual dispatch/scan/creation children', c.get('scope'))
    return c


def _proof_sources():
    return proof_sources(__file__, PATH, parent_owner._proof_sources()+scan_owner._proof_sources(), NATIVE_MAPPER_PATH)


def _validate_selected(gameassembly, c, *, metadata_path):
    parent, dc, rc, creation = [owner._contract() for owner in (parent_owner, dispatch_owner, scan_owner, creation_owner)]
    if any(contract['nativeInputs'] != c['nativeInputs'] for contract in (parent, dc, rc, creation)):
        raise ValueError(LABEL + '.parent-child-native-build-differs')
    context = parent_owner._validate_selected(gameassembly, parent, metadata_path=metadata_path)
    # The maintained scan owner rechecks its complete dispatch parent and
    # actual preparation/search targets; no helper implementation is copied.
    scan = scan_owner._validate_selected(gameassembly, rc)
    image = open_native_image(Path(gameassembly), Path(metadata_path)); index = BodyIndex(image)
    dispatch = validate_dispatch_fallback_control(index, dc)
    columns = metadata_dispatch_count_columns(load_metadata_helper(METADATA_HELPER_PATH), image.metadata)
    if columns != c['metadataColumns']:
        raise ValueError(LABEL + '.named-metadata-dispatch-count-columns-differ')
    creation_block = {**creation['function'], 'ownedWindows': creation['function']['codeWindows']}
    rows = parent_owner._owned_rows(image, index, creation_block, decode_class_creation_instructions)
    sources = prove_creation_dispatch_sources(rows, image.pe.image_base, creation,
        dc['layout']['prepareArgumentPointer'], context['fallback']['freshWordCountLoad']['receiverByteOffset'], columns)
    if sources != c['creationDispatchSources']:
        raise ValueError(LABEL + '.allocation-self-and-record-count-sources-differ')
    bindings = static_interface_context_bindings(image, NativeReferenceContext(image, index=index), parent, sources)
    if bindings != c['staticInterfaceBindings']:
        raise ValueError(LABEL + '.five-static-context-getter-bindings-differ')
    joined = join_context_dispatch_programs(context['fallback'], dc, rc, sources, dispatch, scan)
    return {'creationDispatchSources': sources, 'metadataRowsChecked': columns['rowsChecked'],
        'staticInterfaceBindings': bindings, 'contextDispatchJoin': joined,
        'checkedParentAdapterInstructions': context['adapter']['checkedInstructions'],
        'checkedParentFallbackInstructions': context['fallback']['checkedInstructions'],
        'checkedPrepareAndResolverInstructions': dispatch['checkedInstructions'],
        'checkedDirectSearchAndIndexLeafInstructions': scan['checkedInstructions'],
        'directSearchCodeDataPartition': {k: scan[k] for k in ('ownedBytes', 'codeBytes', 'tableBytes', 'paddingBytes')},
        'conditions': c['conditions']}


def validate_current_native_contract(*, gameassembly, metadata):
    def body(selected_ga, c): return _validate_selected(selected_ga, c, metadata_path=Path(metadata))
    owner = SimpleNamespace(_contract=_contract, _proof_sources=_proof_sources, _fail=_fail, _fingerprint=_fingerprint,
        SCOPE=SCOPE, check_installed_native_inputs=check_installed_native_inputs, _validate_selected=body)
    return validate_owner(owner, gameassembly=gameassembly, metadata=metadata,
        open_claims={'runtimePreparedClassInterfaceArrayPairIdentityProved': False,
            'actualAllocationCapacityOrOutcomeProved': False, 'preparationOrResolverEffectsAndTerminationProved': False,
            'wholeConditionExecutionProved': False, 'wholeRootAdmitted': False},
        check='native-context-dispatch-sources', expected='actual complete child programs and allocated self/interface-count/static-getter pair source joins',
        phase='Buff context fallback dispatch sources')
