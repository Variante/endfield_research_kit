"""Exact integer-domain partitions for a checked size/overlap copy dispatch.

Intervals cover every unsigned count; finite alignment residues are complete
bit-mask cases, not sampled lengths. This module proves selection coverage,
not memory transfers, CPU availability or visibility of selected stores.
"""
from __future__ import annotations


def _fail(label, check, expected, actual):
    raise ValueError(f'{label}.{check}: expected={str(expected)[:320]} actual={str(actual)[:512]}')


def require_interval_partition(bounds, cells, *, label='copyDispatch'):
    """Prove a disjoint, gap-free closed integer interval union by adjacency."""
    lower, upper = bounds
    if type(lower) is not int or type(upper) is not int or lower > upper:
        _fail(label, 'interval-domain', 'nonempty integer interval', bounds)
    cursor = lower
    for cell in sorted(cells, key=lambda row: row['minimum']):
        start, end = cell['minimum'], cell['maximum']
        if type(start) is not int or type(end) is not int or start != cursor or not start <= end <= upper:
            _fail(label, 'interval-partition', {'nextMinimum': cursor, 'maximum': upper}, cell)
        cursor = end + 1
    if cursor != upper + 1:
        _fail(label, 'interval-partition', {'exclusiveEnd': upper + 1}, cursor)
    return {'minimum': lower, 'maximum': upper, 'completeDisjointIntegerUnionProved': True}


def _split(bounds, limit):
    lo, hi = bounds
    before = (lo, min(hi, limit)) if lo <= min(hi, limit) else None
    after = (max(lo, limit + 1), hi) if max(lo, limit + 1) <= hi else None
    return before, after


def _cell(bounds, program, **facts):
    return {'minimum': bounds[0], 'maximum': bounds[1], 'program': program, **facts}


def _vector_partition(bounds, *, role, width, chunk, nt_threshold, label):
    bounded, large = _split(bounds, chunk)
    cells = []
    if bounded:
        cells.append(_cell(bounded, role + 'BoundedVector'))
    if large:
        alignments = []
        for advance in range(1, width + 1):
            direct_tail, loop_range = _split(large, chunk + advance)
            leaves = []
            if direct_tail:
                leaves.append(_cell(direct_tail, role + 'RebasedTail'))
            if loop_range:
                if role == 'high':
                    temporal, streaming = _split(loop_range, nt_threshold + advance)
                    if temporal:
                        leaves.append(_cell(temporal, role + 'TemporalLoop'))
                    if streaming:
                        leaves.append(_cell(streaming, 'highNonTemporalLoop'))
                else:
                    leaves.append(_cell(loop_range, role + 'TemporalLoop'))
            union = require_interval_partition(large, leaves, label=label + '.alignment')
            for leaf in leaves:
                leaf['remainingMinimum'] = leaf['minimum'] - advance
                leaf['remainingMaximum'] = leaf['maximum'] - advance
                if leaf['remainingMinimum'] <= 0:
                    _fail(label, 'alignment-count-no-underflow', 'positive remaining', leaf)
                if leaf['program'].endswith('RebasedTail'):
                    if leaf['remainingMaximum'] > chunk:
                        _fail(label, 'direct-tail-bound', chunk, leaf)
                elif leaf['remainingMinimum'] <= chunk:
                    _fail(label, 'first-complete-chunk-guard', f'remaining > {chunk}', leaf)
                if leaf['program'] == 'highNonTemporalLoop' and leaf['remainingMinimum'] <= nt_threshold:
                    _fail(label, 'non-temporal-threshold', f'remaining > {nt_threshold}', leaf)
            alignments.append({'destinationResidue': width - advance, 'advance': advance,
                'partition': union, 'cells': leaves})
        cells.append(_cell(large, role + 'AlignedVector', widthBytes=width,
            alignmentCases=alignments, allMaskedDestinationResiduesCoveredProved=True))
    # Avoid using cardinality alone: each exact alignment residue has its own
    # checked complete interval partition, and width-(D & (width-1)) is bijective.
    return {'partition': require_interval_partition(bounds, cells, label=label + '.vector'), 'cells': cells}


def prove_copy_dispatch_domains(constants, vectors, nt_threshold, *, label='copyDispatch'):
    maximum = (1 << 64) - 1
    expected = {'smallLimit', 'mediumLimit', 'modeThreshold', 'highRepMinimum',
        'highRepMaximum', 'lowRepMinimum', 'optionMask'}
    if set(constants) != expected or set(vectors) != {'high', 'low'}:
        _fail(label, 'declaration-shape', 'complete checked constants and two vector paths', (constants, vectors))
    for key in expected:
        value = constants[key]
        bound = 1 << (32 if key == 'modeThreshold' else 8 if key == 'optionMask' else 64)
        if type(value) is not int or not 0 <= value < bound:
            _fail(label, 'unsigned-constant:' + key, f'0 <= integer < {bound}', value)
    small, medium = constants['smallLimit'], constants['mediumLimit']
    mode, mask = constants['modeThreshold'], constants['optionMask']
    if not 0 <= small < medium < maximum or not 0 < mode < (1 << 32) or not mask or mask & (mask - 1):
        _fail(label, 'ordered-domains', 'strict size bounds, nonempty mode halves and one option bit', constants)
    if not medium < constants['highRepMinimum'] < constants['highRepMaximum'] <= maximum:
        _fail(label, 'high-rep-domain', 'medium < minimum < maximum', constants)
    if not medium < constants['lowRepMinimum'] <= maximum:
        _fail(label, 'low-rep-domain', 'medium < low REP minimum', constants)
    if type(nt_threshold) is not int or not 0 <= nt_threshold <= maximum:
        _fail(label, 'non-temporal-domain', 'unsigned qword threshold', nt_threshold)
    for role, declaration in vectors.items():
        width, chunk = declaration['widthBytes'], declaration['lengthMaximum']
        if (type(width) is not int or type(chunk) is not int or width <= 0 or width & (width - 1)
                or not width <= medium < chunk <= maximum - (width - 1) or chunk % width
                or chunk > constants[role + 'RepMinimum'] or (role == 'high' and nt_threshold < chunk)):
            _fail(label, 'vector-and-loop-domain:' + role, 'valid saved vectors, whole chunk, bounded rounding and guarded first loop', declaration)
    size_cells = [_cell((0, small), 'small'), _cell((small + 1, medium), 'snapshot'),
        _cell((medium + 1, maximum), 'common')]
    mode_cells = [_cell((0, mode - 1), 'low'), _cell((mode, (1 << 32) - 1), 'high')]
    forward = []
    for role in ('low', 'high'):
        for enabled in (False, True):
            domain = (medium + 1, maximum)
            short, above_min = _split(domain, constants[role + 'RepMinimum'])
            selections = [_cell(short, role + 'Vector')]
            if role == 'high':
                eligible, above_max = _split(above_min, constants['highRepMaximum'])
                if eligible:
                    selections.append(_cell(eligible, 'rep' if enabled else role + 'Vector'))
                if above_max:
                    selections.append(_cell(above_max, role + 'Vector'))
            elif above_min:
                selections.append(_cell(above_min, 'rep' if enabled else role + 'Vector'))
            union = require_interval_partition(domain, selections, label=label + '.forward')
            for selection in selections:
                if selection['program'].endswith('Vector'):
                    selection['vector'] = _vector_partition((selection['minimum'], selection['maximum']),
                        role=role, width=vectors[role]['widthBytes'], chunk=vectors[role]['lengthMaximum'],
                        nt_threshold=nt_threshold, label=label + '.' + role)
            forward.append({'mode': role, 'optionBitSet': enabled, 'partition': union, 'cells': selections})
    return {'sizePartition': require_interval_partition((0, maximum), size_cells, label=label + '.size'),
        'sizeCells': size_cells,
        'modePartition': require_interval_partition((0, (1 << 32) - 1), mode_cells, label=label + '.mode'),
        'modeCells': mode_cells,
        'optionPartition': {'operandBits': 8, 'mask': mask,
            'conditions': ['(optionByte & mask) == 0', '(optionByte & mask) != 0'],
            'completeDisjointBooleanPartitionProved': True},
        'overlapPartition': {'domain': 'N > mediumLimit; E=S+N does not wrap, hence S<E',
            'cells': [{'condition': 'D<=S', 'program': 'forward'},
                {'condition': 'S<D<E', 'program': 'backward'}, {'condition': 'D>=E', 'program': 'forward'}],
            'proof': 'Since S<E, ordered integer trichotomy gives disjoint D<=S, S<D<E, D>=E. The checked CMOVBE changes E to D exactly when D<=S; the following unsigned D<E test selects exactly the middle case.',
            'completeDisjointOrderedPartitionProved': True},
        'forwardPartitions': forward,
        'allUnsignedCountModeOptionAndAlignmentDomainsCoveredProved': True,
        'countCoverageIsExactIntervalAlgebraNotSampledLengths': True,
        'memoryTransfersOrRuntimeSelectionsProved': False}
