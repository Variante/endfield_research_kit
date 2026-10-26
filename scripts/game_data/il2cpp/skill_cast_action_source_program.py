"""Close anonymous action-source copies and the caller's low-DWORD projection."""
from .consumer_control import check_consumer_control
from .owned_partition import BranchGrammar
from .initializer_control import control_transfer

LABEL = 'skillCastActionSourceProgram'


class _HelperGrammar(BranchGrammar):
    """Retain real addresses across ranges already closed by the full CFG."""
    def __init__(self, rows, *, owned_ranges):
        parts = [[r for r in rows if start <= int(r['va'], 16) < end]
                 for start, end in sorted(owned_ranges)]
        if not parts or any(not part for part in parts) or [r for part in parts for r in part] != rows:
            raise ValueError(LABEL + '.owned-range-row-membership')
        super().__init__(parts[0], label=LABEL)
        for part in parts[1:]: BranchGrammar(part, label=LABEL + '.range')
        self.rows = rows


def _decoded(rows, mapper):
    for row in rows:
        raw = bytes.fromhex(row['bytes']); at = int(row['va'], 16)
        actual, end = mapper.decode_one_x64(raw, 0, at)
        if end != len(raw) or actual['text'] != row['text'] or actual['text'].startswith('db'):
            raise ValueError(LABEL + '.original-byte-decoding:' + row['va'])


def check_action_source_helper(rows, *, entry, owned_ranges, mapper, contract, environment_offset, calls):
    _decoded(rows, mapper)
    control = check_consumer_control(rows, entry=entry, owned_ranges=owned_ranges)
    if set(calls) != set(contract['namedCalls']) | {'trapHelper', 'fallbackHelper'}:
        raise ValueError(LABEL + '.call-membership')
    if contract['copiedValueBytes'] != 24 or contract['rawEnvironmentSource']['bytes'] != 24:
        raise ValueError(LABEL + '.copy-shape')
    word = contract['classWord']; raw = contract['rawEnvironmentSource']
    values = {'environmentOffset': environment_offset, 'classWordOffset': word['offset'],
        'fillValue': word['fillValue'], 'rawValue': word['rawValue'], 'zeroSubtraction': word['zeroSubtraction'],
        'rawSourceOffset': raw['offset'], 'rawTailOffset': raw['offset'] + 16}
    if any(type(v) != int or not 0 <= v < 2**32 for v in values.values()):
        raise ValueError(LABEL + '.unsigned-declarations')
    grammar = _HelperGrammar(rows, owned_ranges=owned_ranges)
    for step in contract['helperProgram']:
        if len(step) != 1:
            raise ValueError(LABEL + '.instruction-declaration')
        operation, value = next(iter(step.items()))
        if operation == 'take':
            for key, number in values.items(): value = value.replace('{' + key + '}', hex(number))
            grammar.take(value)
        elif operation == 'pattern': grammar.pattern(value)
        elif operation == 'mark': grammar.mark(value)
        elif operation == 'branch': grammar.branch(*value)
        elif operation == 'call': grammar.call(calls[value])
        else: raise ValueError(LABEL + '.unknown-program-operation:' + operation)
    grammar.finish()
    first_zero = (word['rawValue'] + word['zeroSubtraction']) & 0xffffffff
    zeros = [(first_zero + n) & 0xffffffff for n in range(3)]
    if len(set(zeros)) != 3 or set(zeros) & {word['rawValue'], word['fillValue']}:
        raise ValueError(LABEL + '.class-case-overlap')
    return {'status': 'complete-action-source-copy-and-zero-cases-proved',
        'instructionsChecked': control['instructionsChecked'], 'ownedRangesChecked': control['ownedRangesChecked'],
        'environmentFieldOffset': environment_offset, 'classWordOffsetStructuralOnly': word['offset'],
        'fillCaseRawClassWord': word['fillValue'], 'rawCopyCaseRawClassWord': word['rawValue'],
        'zeroOutputRawClassWords': zeros, 'zeroOutputBytes': 24,
        'rawEnvironmentCopy': {'sourceOffset': raw['offset'], 'bytes': 24, 'namedMeaningKnown': False},
        'returnsIncomingOutputPointerOnCheckedReturn': True,
        'classDiscriminatorMeaningKnown': False, 'selectedReceiverClassKnown': False,
        'fallbackValueKnown': False, 'patchedValueKnown': False, 'runtimeExecutionKnown': False,
        'evidenceBoundary': 'conditional',
        'conditions': ['valid readable action/environment/class and writable output/frame storage',
            'ordinary returning Win64 callees and disjoint source/output/frame storage',
            'the selected compiled path reaches its return'],
        'fillCompositionCondition': 'the environment is a valid Ability and the checked Fill normal unpatched path returns'}


def check_action_source_caller(rows, *, entry, owned_ranges, mapper, action_test_site,
        helper_pointer, fallback_start, fallback_rejoin_site, clear_start):
    _decoded(rows, mapper)
    control = check_consumer_control(rows, entry=entry, owned_ranges=owned_ranges)
    positions = [i for i, r in enumerate(rows) if int(r['va'], 16) == action_test_site]
    if len(positions) != 1: raise ValueError(LABEL + '.unique-action-test')
    block = rows[positions[0]:positions[0]+10]
    grammar = BranchGrammar(block, label=LABEL + '.caller')
    grammar.labels.update(fallback=fallback_start, clear=clear_start)
    grammar.take('test rdx, rdx'); grammar.branch('je', 'fallback')
    grammar.pattern(r'lea rcx, \[rsp\+0x[0-9a-f]+\]'); grammar.call(helper_pointer)
    grammar.take('movups xmm1, [rax]', 'movsd xmm0, [rax+0x10]', 'movd ebp, xmm1')
    grammar.pattern(r'movsd \[rsp\+0x[0-9a-f]+\], xmm0')
    grammar.take('test ebp, ebp'); grammar.branch('je', 'clear')
    grammar.finish()
    checked = block[:grammar.cursor]
    inside = {int(r['va'], 16) for r in checked}
    interior = {int(r['va'], 16) for r in checked[1:]}
    expected_test = int(checked[-2]['va'], 16)
    by_site = {int(r['va'], 16): r for r in rows}
    fallback_flow = control_transfer(by_site[fallback_rejoin_site])
    if fallback_flow.get('kind') != 'jump' or fallback_flow.get('target') != expected_test:
        raise ValueError(LABEL + '.authenticated-fallback-rejoin')
    for site, targets in control['edges'].items():
        if site in inside or not targets & interior: continue
        if site == fallback_rejoin_site and targets & interior == {expected_test}: continue
        raise ValueError(LABEL + '.caller-projection-entry-bypass')
    return {'status': 'non-null-action-helper-low-dword-to-clear-selection-proved',
        'instructionsChecked': len(checked), 'helperPointer': helper_pointer,
        'lowDwordCopiedWithoutConversion': True, 'zeroDwordSelectsClearPath': True,
        'clearPathIsUnconditionalCall': False, 'runtimeExecutionKnown': False,
        'evidenceBoundary': 'conditional',
        'condition': 'ordinary helper return and readable returned output reference; the independent named caller proof owns the fallback rejoin'}
