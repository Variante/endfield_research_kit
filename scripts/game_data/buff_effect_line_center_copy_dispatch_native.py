"""Combine complete copy programs with the actual selected bulk dispatch.

All unsigned size/mode/option/alignment domains and actual entry/fallthrough
joins are checked. Resulting store values retain per-program memory/CPU/DF
conditions; store visibility, live array stride and resize lifetime are not
inferred from complete static dispatch coverage.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.rep_string_moves import decode_rep_selection_instructions
from scripts.game_data.il2cpp.memory_moves import decode_memory_move_instructions
from scripts.game_data.il2cpp.copy_dispatch_domains import prove_copy_dispatch_domains
from scripts.game_data import buff_effect_line_center_copy_non_temporal_native as nt_owner
from scripts.game_data import buff_effect_line_center_copy_backward_native as backward_owner

loop_owner = nt_owner.loop_owner
small_owner = loop_owner.small_owner
rep_owner = small_owner.rep_owner
SCHEMA = 'endfield.buff-effect-line-center-copy-dispatch-native-contract.v1'
LABEL = 'buffEffectLineCenterCopyDispatch'
CONTRACT_PATH = CONTRACTS_DIR / 'buff_effect_line_center_copy_dispatch_native.json'
PARENT_OWNERS = {'rep': rep_owner, 'small': small_owner, 'loops': loop_owner,
    'nonTemporal': nt_owner, 'backward': backward_owner}


def _fail(check, expected, actual):
    raise ValueError(f'{LABEL}.{check}: source={CONTRACT_PATH.as_posix()} expected={str(expected)[:384]} actual={str(actual)[:512]}')


def _contract():
    contract, _ = read_reviewed_contract(CONTRACT_PATH, schema=SCHEMA, status='exact-current-build', label=LABEL)
    if (contract.get('scope') != 'conditional-complete-bulk-dispatch-and-store-value-coverage'
            or contract.get('operandDomains') != {'countBits': 64, 'pointerBits': 64, 'modeBits': 32, 'optionBits': 8}
            or contract.get('parentContracts') != {role: owner.CONTRACT_PATH.name for role, owner in PARENT_OWNERS.items()}):
        _fail('contract-shape', 'complete same-image parent programs and decoded unsigned operand domains', contract.get('scope'))
    return contract


def _dispatch(image, parents, bulk):
    base = image.pe.image_base
    rep, small, loops, nt, backward = (parents[key] for key in ('rep', 'small', 'loops', 'nonTemporal', 'backward'))
    def rows(window, decoder):
        if not any(w['startRva'] <= window['startRva'] < window['endRva'] <= w['endRva'] for w in bulk['windows']):
            _fail('owned-dispatch-window', bulk['windows'], window)
        return decoder(image.mapper, image.window_bytes(window), base + window['startRva'])
    constants = rep['selectionConstants']
    selected = {role: getattr(rep_owner, '_' + role)(rows(rep['blocks'][role], decode_rep_selection_instructions), constants)
        for role in ('entry', 'medium', 'common', 'low')}
    small_dispatch = small_owner._small_dispatch(rows(small['blocks']['smallDispatch'], decode_memory_move_instructions),
        small_limit=constants['smallLimit'], table=small['tables']['small'], image_base=base)
    joins = []
    def edge(name, source, target_rva):
        if source['target'] != base + target_rva:
            _fail('actual-edge:' + name, base + target_rva, source)
        joins.append({'name': name, 'kind': 'decoded-branch', 'sourceVA': source['va'], 'targetRva': target_rva})
    def contiguous(name, source_end, target_start):
        if source_end != target_start:
            _fail('actual-fallthrough:' + name, target_start, source_end)
        joins.append({'name': name, 'kind': 'contiguous-fallthrough', 'targetRva': target_start})
    if rep['blocks']['entry']['startRva'] != bulk['entryRva'] or small['blocks']['smallDispatch']['startRva'] != bulk['entryRva']:
        _fail('actual-bulk-start', bulk['entryRva'], (rep['blocks']['entry'], small['blocks']['smallDispatch']))
    edge('entryToMedium', selected['entry']['mediumEntryEdge'], rep['blocks']['medium']['startRva'])
    edge('smallToMedium', small_dispatch['largeEntryEdge'], rep['blocks']['medium']['startRva'])
    edge('mediumToCommon', selected['medium']['commonEntryEdge'], rep['blocks']['common']['startRva'])
    contiguous('mediumToSnapshot', rep['blocks']['medium']['endRva'], small['blocks']['snapshot']['startRva'])
    edge('commonToBackward', selected['common']['backwardOverlapEdge'], backward['blocks']['backward']['startRva'])
    edge('commonToLowMode', selected['common']['lowModeEntryEdge'], rep['blocks']['low']['startRva'])
    for role in ('high', 'low'):
        source = selected['common'] if role == 'high' else selected['low']
        edge(role + 'ToRep', source['repEntryEdge'], rep['leafWindow']['startRva'])
        edge(role + 'ToVector', source[role + 'VectorEntryEdge'], small['blocks'][role + 'Prefix']['startRva'])
        # A false option test does not branch: the complete block must end
        # exactly at the same vector prefix, including the final JNE bytes.
        contiguous(role + 'OptionFalseToVector', rep['blocks']['common' if role == 'high' else 'low']['endRva'],
            small['blocks'][role + 'Prefix']['startRva'])
        width = small['vectors'][role]['widthBytes']; chunk = small['vectors'][role]['lengthMaximum']
        prefix = small_owner._vector_prefix(rows(small['blocks'][role + 'Prefix'], decode_memory_move_instructions), width=width, limit=chunk)
        alignment = loop_owner._alignment(rows(loops['blocks'][role + 'Alignment'], decode_memory_move_instructions),
            width=width, chunk=chunk, non_temporal_threshold=loops['selectionConstants']['highNonTemporalThreshold'] if role == 'high' else None)
        edge(role + 'BoundedToTail', prefix['tailEntryEdge'], small['blocks'][role + 'Tail']['startRva'])
        contiguous(role + 'LargeToAlignment', small['blocks'][role + 'Prefix']['endRva'], loops['blocks'][role + 'Alignment']['startRva'])
        edge(role + 'AlignedToTail', alignment['tailEntryEdge'], small['blocks'][role + 'Tail']['startRva'])
        contiguous(role + 'AlignedToPadding', loops['blocks'][role + 'Alignment']['endRva'], loops['blocks'][role + 'Padding']['startRva'])
        contiguous(role + 'PaddingToTemporalLoop', loops['blocks'][role + 'Padding']['endRva'], loops['blocks'][role + 'Loop']['startRva'])
        contiguous(role + 'TemporalLoopToTail', loops['blocks'][role + 'Loop']['endRva'], small['blocks'][role + 'Tail']['startRva'])
        if role == 'high':
            edge('highAlignedToNonTemporal', alignment['nonTemporalEntryEdge'], nt['blocks']['loop']['startRva'])
    contiguous('nonTemporalLoopToTail', nt['blocks']['loop']['endRva'], nt['blocks']['tail']['startRva'])
    if selected['common']['optionByteInstruction']['byteTestOperation'] != selected['low']['optionByteInstruction']['byteTestOperation']:
        _fail('same-option-byte', selected['common']['optionByteInstruction'], selected['low']['optionByteInstruction'])
    return {'joins': joins, 'selectionConstants': constants,
        'bothFalseOptionFallthroughsCheckedProved': True,
        'nonTemporalThresholdIsRemainingAfterAlignmentProved': True}


def _validate_image(image, contract):
    parents = {role: owner._contract() for role, owner in PARENT_OWNERS.items()}
    arguments = rep_owner.argument_owner._contract(); bulk = arguments['programs']['bulk']
    for role, parent in {**parents, 'arguments': arguments}.items():
        if parent['nativeInputs'] != contract['nativeInputs']:
            _fail('same-parent-build:' + role, contract['nativeInputs'], parent['nativeInputs'])
        if role != 'arguments' and parent['bulkEntryRva'] != bulk['entryRva']:
            _fail('same-called-bulk:' + role, bulk['entryRva'], parent['bulkEntryRva'])
    if contract['bulkEntryRva'] != bulk['entryRva']:
        _fail('same-called-bulk:combined', bulk['entryRva'], contract['bulkEntryRva'])
    # The non-temporal owner recursively revalidates loops, small/snapshot,
    # REP and full arguments on this image. Backward independently revalidates
    # REP/arguments and its complete payload. Original proofs remain owned there.
    streaming = nt_owner._validate_image(image, parents['nonTemporal'])
    backward = backward_owner._validate_image(image, parents['backward'])
    if (not streaming['conditionalNonTemporalStoreByteCoverageProved']
            or not streaming['temporalAndParentProofRevalidated']
            or not backward['conditionalCompleteBackwardByteCopyProved']
            or not backward['actualBackwardOverlapEntryJoinProved']):
        _fail('required-complete-payload-proofs', 'same-image checked forward and backward chains', (streaming, backward))
    dispatch = _dispatch(image, parents, bulk)
    domains = prove_copy_dispatch_domains(dispatch['selectionConstants'], parents['small']['vectors'],
        parents['loops']['selectionConstants']['highNonTemporalThreshold'], label=LABEL + '.domains')
    return {'sameImageAllCopyProgramProofsRevalidated': True, 'dispatch': dispatch, 'domains': domains,
        'allActualBulkEntryAndFallthroughJoinsProved': True,
        'completeActualDispatchDomainCoverageProved': True,
        'conditionalCompleteSelectedBulkStoreValuesProved': True,
        'conditionalCopySelection': 'Actual selected same-element and normal-return helper; valid stable supported compatible ordinary source/destination memory and non-wrapping endpoints, no interfering writes, disjoint caller frame and optional bitset, successful optional bitset retry. The actual program selected by count/overlap/mode/option must have supported CPU/vector state; REP alone additionally requires DF=0. Complete checked stores carry every corresponding initial-source byte; non-temporal store visibility retains its explicit fence/publication/read conditions.',
        'directionFlagRequiredOnlyWhenRepSelected': True,
        'nonTemporalVisibilityRemainsConditional': True,
        'runtimeModeOptionCPUOrOverlapSelectionProved': False, 'runtimeStrideProved': False,
        'directionFlagClearProved': False, 'allPayloadStoresGloballyVisibleAtReturnProved': False,
        'actualPublicationVisibilityAtReadProved': False, 'allocationFreshnessProved': False,
        'sourceTemporaryNonaliasingLifetimeProved': False, 'bulkCopyImplementationProved': False,
        'existingValuesPreservedAcrossResizeProved': False, 'runtimeExecutionObserved': False}


def validate_current_native_contract(*, gameassembly: Path | None = None, metadata: Path | None = None):
    contract = _contract(); pins = contract['nativeInputs']
    gate = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'], gameassembly=gameassembly, metadata=metadata)
    if gate.status != 'validated':
        return {'status': gate.status, 'detail': gate.detail, 'nativeInputs': pins}
    unity = Path(gate.gameassembly).parent / 'UnityPlayer.dll'
    def matches():
        if not unity.is_file(): return False
        with unity.open('rb') as stream:
            return hashlib.file_digest(stream, 'sha256').hexdigest().upper() == pins['UnityPlayer.dll']
    if not matches():
        return {'status': 'mismatched', 'detail': 'Selected UnityPlayer missing or different', 'nativeInputs': pins}
    result = _validate_image(open_native_image(gate.gameassembly, gate.metadata), contract)
    after = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'], gameassembly=gate.gameassembly, metadata=gate.metadata)
    if after.status != 'validated' or not matches():
        return {'status': 'mismatched', 'detail': 'Selected native inputs changed during combined dispatch proof', 'nativeInputs': pins}
    return {'status': 'validated', 'nativeInputs': pins, **result, 'evidenceBoundary': contract['evidenceBoundary']}
