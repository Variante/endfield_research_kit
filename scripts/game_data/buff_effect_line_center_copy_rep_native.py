"""Prove conditional forward byte copying on the selected REP bulk branch.

Full bulk-copy semantics and runtime array stride/selection remain separate.
The checked native branch rules, valid-memory/no-wrap/frame conditions and
DF=0 qualify the REP proof; an ABI expectation is not an observed flag value.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.program_grammar import ProgramGrammar
from scripts.game_data.il2cpp.rep_string_moves import decode_rep_selection_instructions
from scripts.game_data import buff_effect_line_center_copy_arguments_native as argument_owner

SCHEMA = 'endfield.buff-effect-line-center-copy-rep-native-contract.v1'
LABEL = 'buffEffectLineCenterCopyRep'
CONTRACT_PATH = CONTRACTS_DIR / 'buff_effect_line_center_copy_rep_native.json'


def _fail(check, expected, actual):
    raise ValueError(f'{LABEL}.{check}: source={CONTRACT_PATH.as_posix()} expected={str(expected)[:384]} actual={str(actual)[:512]}')


def _below(g):
    row = g.row(); raw = bytes.fromhex(row['bytes']); at = int(row['va'], 16)
    if len(raw) == 2 and raw[0] == 0x72: relative = raw[1:]
    elif len(raw) == 6 and raw[:2] == b'\x0f\x82': relative = raw[2:]
    else: g.fail('unsigned-below', 'JB', row)
    target = at + len(raw) + int.from_bytes(relative, 'little', signed=True)
    if row['text'] not in (f'jb 0x{target:x}', f'jcc 0x{target:x}'):
        g.fail('unsigned-below-decoding', hex(target), row)
    return {**row, 'target': target}


def _entry(rows, constants):
    g = ProgramGrammar(rows, label=LABEL + '.entry')
    g.take('mov rax, rcx')
    origin = g.pattern(r'lea r10, \[rip[+-]0x[0-9a-f]+ => 0x[0-9a-f]+\]')
    g.take(f'cmp r8, 0x{constants["smallLimit"]:x}'); large = g.branch('ja'); g.finish()
    return {'returnDestinationOriginProved': True, 'imageBaseInstruction': origin, 'mediumEntryEdge': large}


def _medium(rows, constants):
    g = ProgramGrammar(rows, label=LABEL + '.medium')
    g.take(f'cmp r8, 0x{constants["mediumLimit"]:x}'); large = g.branch('ja'); g.finish()
    return {'commonEntryEdge': large, 'snapshotVectorFallthroughProved': False}


def _option(g, mask):
    row = g.pattern(r'test byte \[rip[+-]0x[0-9a-f]+ => 0x[0-9a-f]+\], 0x[0-9a-f]+')
    operation = row.get('byteTestOperation', {})
    if operation.get('bits') != 8 or operation.get('mask') != mask or operation.get('writesMemory') is not False:
        g.fail('option-byte-operation', {'bits': 8, 'mask': mask, 'writesMemory': False}, operation)
    return row


def _common(rows, constants):
    g = ProgramGrammar(rows, label=LABEL + '.common')
    g.take('lea r9, [rdx+r8*1]', 'cmp rcx, rdx', 'cmovbe r9, rcx', 'cmp rcx, r9')
    backwards = _below(g)
    mode = g.pattern(r'cmp \[rip[+-]0x[0-9a-f]+ => 0x[0-9a-f]+\], 0x[0-9a-f]+')
    raw = bytes.fromhex(mode['bytes'])
    if len(raw) != 7 or raw[:2] != b'\x83\x3d' or raw[-1] != constants['modeThreshold']:
        g.fail('mode-comparison-width', 'dword comparison with reviewed threshold', mode)
    low = _below(g)
    g.take(f'cmp r8, 0x{constants["highRepMinimum"]:x}'); short_vector = g.branch('jbe')
    g.take(f'cmp r8, 0x{constants["highRepMaximum"]:x}'); long_vector = g.branch('ja')
    option = _option(g, constants['optionMask']); rep = g.branch('jne'); g.finish()
    if short_vector['target'] != long_vector['target']:
        g.fail('one-high-vector-entry', short_vector['target'], long_vector['target'])
    return {'completeSelectedCommonBlockChecked': True, 'backwardOverlapEdge': backwards,
        'modeWordInstruction': mode, 'lowModeEntryEdge': low, 'highVectorEntryEdge': short_vector,
        'optionByteInstruction': option, 'repEntryEdge': rep,
        'forwardOverlapSelection': 'destination <= source OR destination >= source + length, without pointer wrap',
        'runtimeModeOrOptionValuesProved': False, 'modeOrOptionNativeNamesProved': False}


def _low(rows, constants):
    g = ProgramGrammar(rows, label=LABEL + '.lowMode')
    g.take(f'cmp r8, 0x{constants["lowRepMinimum"]:x}'); vector = g.branch('jbe')
    option = _option(g, constants['optionMask']); rep = g.branch('jne'); g.finish()
    return {'completeSelectedLowModeBlockChecked': True, 'lowVectorEntryEdge': vector,
        'optionByteInstruction': option, 'repEntryEdge': rep, 'runtimeOptionValueProved': False}


def _leaf(rows):
    g = ProgramGrammar(rows, label=LABEL + '.repLeaf')
    g.take('push rdi', 'push rsi', 'mov rdi, rcx', 'mov rsi, rdx', 'mov rcx, r8')
    move = g.take('rep movsb'); operation = move.get('stringOperation', {})
    expected = {'operation': 'rep-movsb', 'elementBytes': 1, 'addressBits': 64,
        'sourceRegister': 'rsi', 'destinationRegister': 'rdi', 'countRegister': 'rcx', 'countBits': 64,
        'directionFlagControlsStep': True, 'terminatesOnCountZero': True,
        'zeroFlagControlsTermination': False, 'modifiesRegisters': ['rcx', 'rsi', 'rdi'],
        'writesArithmeticFlags': False, 'changesDirectionFlag': False}
    if bytes.fromhex(move['bytes']) != b'\xf3\xa4' or operation != expected:
        g.fail('rep-default-address-operation', expected, move)
    g.take('pop rsi', 'pop rdi', 'ret'); g.finish()
    return {'completeSelectedLeafEntryToReturnChecked': True,
        'copyArguments': {'destination': 'incoming RCX', 'source': 'incoming RDX', 'byteCount': 'incoming R8'},
        'countBits': 64, 'returnsIncomingRAXUnchanged': True, 'restoresRSIAndRDI': True,
        'preservesParentNonvolatileRegisters': ['rbx', 'r12', 'r14'], 'preservesDirectionFlag': True,
        'directionFlagClearProved': False, 'conditionalForwardByteCopyProved': True,
        'copySelection': 'DF=0; normal complete operation over valid non-wrapping memory, stable source, caller frame disjoint from payloads, and destination <= source OR destination >= source + byteCount',
        'loopInvariant': 'before byte i: previous destination bytes equal the initial source prefix, RCX = incoming count - i, RSI = source + i, RDI = destination + i; selected forward overlap cannot overwrite any future unread source byte',
        'runtimeExecutionObserved': False}


def evaluate_rep_selection(*, length, source, destination, mode, option, constants):
    values = (length, source, destination, mode, option)
    bounds = ((1 << 64), (1 << 64), (1 << 64), (1 << 32), (1 << 8))
    if any(type(value) is not int or not 0 <= value < bound for value, bound in zip(values, bounds)):
        return {'status': 'refused', 'reason': 'unsigned operand domain'}
    if source + length >= 1 << 64 or destination + length >= 1 << 64:
        return {'status': 'refused', 'reason': 'pointer endpoint wrap'}
    if length <= constants['mediumLimit']:
        return {'status': 'selected-other-path', 'path': 'small or snapshot vector'}
    if source < destination < source + length:
        return {'status': 'selected-other-path', 'path': 'backward overlap'}
    if mode < constants['modeThreshold']:
        selected = length > constants['lowRepMinimum'] and bool(option & constants['optionMask'])
        path = 'low-mode REP' if selected else 'low-mode vector'
    else:
        selected = constants['highRepMinimum'] < length <= constants['highRepMaximum'] and bool(option & constants['optionMask'])
        path = 'high-mode REP' if selected else 'high-mode vector'
    return {'status': 'rep-selected' if selected else 'selected-other-path', 'path': path, 'runtimeOutcomeObserved': False}


def _contract():
    contract, _ = read_reviewed_contract(CONTRACT_PATH, schema=SCHEMA, status='exact-current-build', label=LABEL)
    if (contract.get('scope') != 'conditional-forward-copy-via-selected-rep-bulk-branches'
            or set(contract.get('blocks', {})) != {'entry', 'medium', 'common', 'low'}
            or set(contract.get('selectionConstants', {})) != {'smallLimit', 'mediumLimit', 'modeThreshold',
                'highRepMinimum', 'highRepMaximum', 'lowRepMinimum', 'optionMask'}):
        _fail('contract-shape', 'four bulk blocks, leaf entry and selected constants', contract.get('scope'))
    return contract


def _validate_image(image, contract):
    parent = argument_owner._contract(); base = image.pe.image_base
    if parent['nativeInputs'] != contract['nativeInputs']:
        _fail('same-parent-build', parent['nativeInputs'], contract['nativeInputs'])
    argument_proof = argument_owner._validate_image(image, parent)
    bulk = parent['programs']['bulk']
    if bulk['entryRva'] != contract['bulkEntryRva']:
        _fail('actual-called-bulk-entry', bulk['entryRva'], contract['bulkEntryRva'])
    rows = {}
    for role, block in contract['blocks'].items():
        if not any(w['startRva'] <= block['startRva'] < block['endRva'] <= w['endRva'] for w in bulk['windows']):
            _fail('owned-bulk-block:' + role, bulk['windows'], block)
        rows[role] = decode_rep_selection_instructions(image.mapper, image.window_bytes(block), base + block['startRva'])
    leaf_window = contract['leafWindow']; image.check_windows([leaf_window], label=LABEL)
    leaf_rows = decode_rep_selection_instructions(image.mapper, image.window_bytes(leaf_window), base + leaf_window['startRva'])
    constants = contract['selectionConstants']
    entry = _entry(rows['entry'], constants); medium = _medium(rows['medium'], constants)
    common = _common(rows['common'], constants); low = _low(rows['low'], constants); leaf = _leaf(leaf_rows)
    joins = [(entry['mediumEntryEdge'], contract['blocks']['medium']['startRva']),
        (medium['commonEntryEdge'], contract['blocks']['common']['startRva']),
        (common['lowModeEntryEdge'], contract['blocks']['low']['startRva']),
        (common['repEntryEdge'], leaf_window['startRva']), (low['repEntryEdge'], leaf_window['startRva'])]
    for edge, rva in joins:
        if edge['target'] != base + rva: _fail('selected-branch-join', rva, edge)
    if contract['blocks']['entry']['startRva'] != bulk['entryRva']:
        _fail('actual-entry-prefix', bulk['entryRva'], contract['blocks']['entry'])
    if entry['imageBaseInstruction'].get('addressOperation', {}).get('absoluteAddress') != base:
        _fail('actual-image-base-lea', base, entry['imageBaseInstruction'])
    if (common['highVectorEntryEdge']['target'] != base + contract['blocks']['common']['endRva']
            or low['lowVectorEntryEdge']['target'] != base + contract['blocks']['low']['endRva']):
        _fail('unselected-vector-fallthroughs', 'checked block ends', {'common': common, 'low': low})
    high_option = common['optionByteInstruction']['byteTestOperation']; low_option = low['optionByteInstruction']['byteTestOperation']
    if high_option != low_option: _fail('shared-byte-option', high_option, low_option)
    return {'bulkArgumentProofRevalidated': True, 'entry': entry, 'medium': medium, 'common': common,
        'low': low, 'leaf': leaf, 'selectionConstants': constants,
        'conditionalForwardBulkByteCopyViaRepProved': True,
        'repLeafNonvolatilePreservationProved': True, 'repBranchReturnsOriginalDestinationProved': True,
        'conditionalOldPointPreservationViaRepBranchProved': True,
        'conditionalOldPointPreservationSelection': 'all parent same-element and normal-return selections; initialized class stride equals the separately checked Vector3 twelve-byte width; current REP length/mode/option selection; DF=0; valid stable non-wrapping arrays, caller frame disjoint from payloads and optional static bitset disjoint from them; successful optional bitset retry; selected new-array reference then current twelve-byte append',
        'runtimeModeOrOptionSelectionProved': False, 'runtimeStrideProved': False,
        'directionFlagClearProved': False, 'bulkCopyImplementationProved': False,
        'existingValuesPreservedAcrossResizeProved': False, 'runtimeExecutionObserved': False}


def validate_current_native_contract(*, gameassembly: Path | None = None, metadata: Path | None = None):
    contract = _contract(); pins = contract['nativeInputs']
    gate = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'], gameassembly=gameassembly, metadata=metadata)
    if gate.status != 'validated': return {'status': gate.status, 'detail': gate.detail, 'nativeInputs': pins}
    unity = Path(gate.gameassembly).parent / 'UnityPlayer.dll'
    def matches():
        if not unity.is_file(): return False
        with unity.open('rb') as stream:
            return hashlib.file_digest(stream, 'sha256').hexdigest().upper() == pins['UnityPlayer.dll']
    if not matches(): return {'status': 'mismatched', 'detail': 'Selected UnityPlayer missing or different', 'nativeInputs': pins}
    result = _validate_image(open_native_image(gate.gameassembly, gate.metadata), contract)
    after = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'], gameassembly=gate.gameassembly, metadata=gate.metadata)
    if after.status != 'validated' or not matches():
        return {'status': 'mismatched', 'detail': 'Selected native inputs changed during REP copy validation', 'nativeInputs': pins}
    return {'status': 'validated', 'nativeInputs': pins, **result, 'evidenceBoundary': contract['evidenceBoundary']}
