"""Current selected forward copy paths with temporal loop induction.

The entry comes from an actual caller. Every block/table is discovered from
that entry's current owned bytes. The legacy domain owners supply pure byte
algorithms only; none of their contracts, addresses or native validators is
read. Backward overlap and non-temporal paths remain outside this component.
"""
from __future__ import annotations

import hashlib

from .formatter_value_paths import BytesPath

LABEL = 'forwardCopySource'


def need(check, condition, detail=None):
    if not condition:
        raise ValueError(LABEL + '.' + check + ':' + str(detail)[:700])


def decode(mapper, raw, entry):
    from .memory_moves import decode_memory_move_instructions
    from .rep_string_moves import decode_rep_movsb, decode_rip_byte_test

    class RepFallback:
        def decode_one_x64(self, data, offset, start):
            for decoder in (decode_rep_movsb, decode_rip_byte_test):
                result = decoder(data, offset, start)
                if result is not None:
                    return result
            return mapper.decode_one_x64(data, offset, start)

    return decode_memory_move_instructions(RepFallback(), raw, entry)


def structure(regions, entry, *, rows, image_base):
    """Recover literal block boundaries and tables, without granting copying."""
    by_at = {int(row['va'], 16): row for row in rows}
    need('unique-instructions', len(by_at) == len(rows))
    g = BytesPath(regions, entry)
    blocks = {}
    tables = {}

    def instruction():
        row = by_at.get(g.at)
        need('instruction-boundary', row is not None, hex(g.at))
        raw = bytes.fromhex(row['bytes'])
        need('original-decoded-bytes', g.read(len(raw)) == raw)
        return row

    def cmp64():
        g.take('4981f8')
        value = int.from_bytes(g.read(4), 'little', signed=True)
        need('positive-qword-limit', value > 0, value)
        return value

    def table(role, destination, index, entries):
        row = instruction()
        op = row.get('memoryOperation', {})
        address = op.get('address', {})
        rva = address.get('displacement')
        need('table-load', op.get('direction') == 'load' and
             op.get('register') == destination + 'd' and
             op.get('registerBits') == 32 and op.get('memoryBytes') == 4 and
             address == dict(base='r10', index=index, scale=4, displacement=rva,
                             ripRelative=False, addressBits=64) and type(rva) is int)
        tables[role] = dict(startRva=rva, entriesCount=entries)
        g.take('4d03ca' if destination == 'r9' else '4d03da',
               '41ffe1' if destination == 'r9' else '41ffe3')

    def ret_end(start):
        cursor = start
        while True:
            row = by_at.get(cursor)
            need('complete-return-boundary', row is not None, hex(cursor))
            raw = bytes.fromhex(row['bytes'])
            cursor += len(raw)
            if raw == b'\xc3':
                return cursor

    def block(role, start, end):
        need('positive-owned-block', start < end and
             all(address in g.bytes for address in range(start, end)), role)
        blocks[role] = [start, end]

    g.take('488bc1')
    need('literal-image-base', g.relative('4c8d15') == image_base)
    g.take('4983f8'); small = int.from_bytes(g.read(1), 'little')
    medium_entry = g.relative('0f87')
    instruction()  # Pure padding algorithm checks this decoded operation.
    table('small', 'r9', 'r8', small + 1)
    block('smallDispatch', entry, g.at)

    g.at = medium_entry
    g.take('4983f8'); medium = int.from_bytes(g.read(1), 'little')
    common_entry = g.relative('77', 1)
    block('medium', medium_entry, g.at)
    block('snapshot', g.at, ret_end(g.at))

    g.at = common_entry
    g.take('4e8d0c02', '483bca', '4c0f46c9', '493bc9')
    backward = g.relative('0f82')
    mode_cell = g.relative('833d') + 1; mode = int.from_bytes(g.read(1), 'little')
    low_entry = g.relative('0f82')
    high_minimum = cmp64(); high_entry = g.relative('76', 1)
    high_maximum = cmp64(); need('high-size-rejoin', g.relative('77', 1) == high_entry)
    high_option = g.relative('f605') + 1
    option = int.from_bytes(g.read(1), 'little')
    rep_entry = g.relative('0f85')
    need('high-fallthrough', g.at == high_entry)
    block('common', common_entry, g.at)

    g.at = low_entry
    low_minimum = cmp64(); low_vector = g.relative('76', 1)
    low_option = g.relative('f605') + 1
    need('same-option-address-and-mask', low_option == high_option and
         int.from_bytes(g.read(1), 'little') == option)
    need('same-rep-entry', g.relative('0f85') == rep_entry)
    need('low-fallthrough', g.at == low_vector)
    block('low', low_entry, g.at)

    vectors = {}
    threshold = None
    for role, start, width, chunk in (('high', high_entry, 32, 256),
                                      ('low', low_vector, 16, 128)):
        g.at = start
        instruction(); instruction()
        need('vector-chunk-comparison', cmp64() == chunk)
        tail = g.relative('0f86')
        block(role + 'Prefix', start, g.at)
        alignment = g.at
        g.take('4c8bc9', '4983e1' + bytes((width - 1,)).hex(),
               '4983e9' + bytes((width,)).hex(), '492bc9', '492bd1', '4d03c1')
        need('aligned-chunk-comparison', cmp64() == chunk)
        need('aligned-tail-rejoin', g.relative('0f86' if role == 'high' else '76',
                                            4 if role == 'high' else 1) == tail)
        if role == 'high':
            threshold = cmp64()
            streaming = g.relative('0f87')
        block(role + 'Alignment', alignment, g.at)
        padding = g.at
        instruction()
        block(role + 'Padding', padding, g.at)
        loop = g.at
        for _ in range(16):
            need('loop-payload-is-memory-transfer', instruction().get('memoryOperation') is not None)
        c = chunk.to_bytes(4, 'little').hex()
        g.take('4881c1' + c, '4881c2' + c, '4981e8' + c, '4981f8' + c)
        need('loop-backedge', g.relative('0f83' if role == 'high' else '73',
                                       4 if role == 'high' else 1) == loop)
        need('loop-tail-fallthrough', g.at == tail)
        block(role + 'Loop', loop, g.at)
        g.take('4d8d48' + bytes((width - 1,)).hex(),
               '4983e1' + bytes((-width & 255,)).hex(), '4d8bd9',
               '49c1eb' + bytes((width.bit_length() - 1,)).hex())
        table(role, 'r11', 'r11', chunk // width + 1)
        block(role + 'Tail', tail, ret_end(g.at))
        vectors[role] = dict(widthBytes=width, lengthMaximum=chunk)

    need('supported-ordered-dispatch', 0 <= small < medium < 128 and
         medium < low_minimum < high_minimum < high_maximum and
         0 < mode < 128 and option > 0 and not option & (option - 1) and threshold > 256)
    return dict(blocks=blocks, tables=tables, vectors=vectors, repEntry=rep_entry,
                highNonTemporalEntry=streaming, highNonTemporalThreshold=threshold,
                backwardEntry=backward, modeCell=mode_cell,
                selectionConstants=dict(smallLimit=small, mediumLimit=medium, modeThreshold=mode,
                    highRepMinimum=high_minimum, highRepMaximum=high_maximum,
                    lowRepMinimum=low_minimum, optionMask=option))


def prove(regions, entry, *, rows, tables, rep_rows, image_base, max_bytes):
    """All bounded counts/modes/options, forward-safe overlap and DF=0."""
    # These functions are pure programs. In particular _contract and
    # _validate_image from the legacy native domains are never called.
    from scripts.game_data import buff_effect_line_center_copy_small_native as small
    from scripts.game_data import buff_effect_line_center_copy_loops_native as loops
    from scripts.game_data import buff_effect_line_center_copy_rep_native as rep
    from .copy_dispatch_domains import prove_copy_dispatch_domains, require_interval_partition

    shape = structure(regions, entry, rows=rows, image_base=image_base)
    constants = shape['selectionConstants']; blocks = shape['blocks']
    need('bounded-temporal-count-domain', type(max_bytes) is int and
         constants['mediumLimit'] < max_bytes <= shape['highNonTemporalThreshold'])
    by_at = {int(row['va'], 16): row for row in rows}

    def selected(start, end):
        result = []; cursor = start
        while cursor < end:
            row = by_at.get(cursor)
            need('whole-block-instructions', row is not None, hex(cursor))
            result.append(row); cursor += len(bytes.fromhex(row['bytes']))
        need('whole-block-end', cursor == end)
        return result

    def body(role):
        return selected(*blocks[role])

    current_tables = {}
    for role, descriptor in shape['tables'].items():
        raw = tables.get(descriptor['startRva'])
        need('current-complete-table', isinstance(raw, bytes) and
             len(raw) == descriptor['entriesCount'] * 4, role)
        current_tables[role] = dict(startRva=descriptor['startRva'],
            entries=[int.from_bytes(raw[i:i + 4], 'little') for i in range(0, len(raw), 4)])

    dispatch = small._small_dispatch(body('smallDispatch'), small_limit=constants['smallLimit'],
                                     table=current_tables['small'], image_base=image_base)
    small_proofs = []
    for length, target in enumerate(current_tables['small']['entries']):
        cursor = image_base + target
        payload = []
        while True:
            row = by_at.get(cursor); need('small-leaf-owned', row is not None, hex(cursor))
            payload.append(row); cursor += len(bytes.fromhex(row['bytes']))
            if bytes.fromhex(row['bytes']) == b'\xc3':
                break
        moves = small._payload(payload, label='currentSmall')['moves']
        small_proofs.append(small._prove_payload(moves, length=length, overlap='arbitrary', label='currentSmall'))
    snapshot = small._payload(body('snapshot'), label='currentSnapshot')['moves']
    snapshots = [small._prove_payload(snapshot, length=n, overlap='arbitrary', label='currentSnapshot')
                 for n in range(constants['smallLimit'] + 1, constants['mediumLimit'] + 1)]
    common = rep._common(body('common'), constants)
    low = rep._low(body('low'), constants)
    medium = rep._medium(body('medium'), constants)
    need('owned-entry-joins', dispatch['largeEntryEdge']['target'] == blocks['medium'][0] and
         medium['commonEntryEdge']['target'] == blocks['common'][0] and
         common['lowModeEntryEdge']['target'] == blocks['low'][0])
    need('exact-standalone-rep-entry', rep_rows and int(rep_rows[0]['va'], 16) == shape['repEntry'])
    leaf = rep._leaf(rep_rows)
    paths = {}
    for role in ('high', 'low'):
        width = shape['vectors'][role]['widthBytes']; chunk = shape['vectors'][role]['lengthMaximum']
        bounded = small._prove_vector(body(role + 'Prefix'), body(role + 'Tail'), width=width,
            limit=chunk, medium_limit=constants['mediumLimit'], table=current_tables[role], image_base=image_base)
        alignment = loops._alignment(body(role + 'Alignment'), width=width, chunk=chunk,
            non_temporal_threshold=shape['highNonTemporalThreshold'] if role == 'high' else None)
        padding = loops._padding(body(role + 'Padding'))
        loop = loops._loop(body(role + 'Loop'), width=width, chunk=chunk)
        tails = loops._tails(body(role + 'Tail'), width=width, chunk=chunk,
                             table=current_tables[role], image_base=image_base)
        need('all-vector-tail-joins', bounded['tailEntryEdge']['target'] == blocks[role + 'Tail'][0] and
             alignment['tailEntryEdge']['target'] == blocks[role + 'Tail'][0])
        current_entry = common['highVectorEntryEdge']['target'] if role == 'high' else low['lowVectorEntryEdge']['target']
        need('current-vector-entry-join', current_entry == blocks[role + 'Prefix'][0])
        paths[role] = dict(bounded=bounded, alignment=alignment, padding=padding, loop=loop, tails=tails)
    domains = prove_copy_dispatch_domains(constants, shape['vectors'], shape['highNonTemporalThreshold'])
    bounded_domains = []
    for mode in domains['forwardPartitions']:
        cells = [dict(minimum=cell['minimum'], maximum=min(max_bytes, cell['maximum']),
                      program=cell['program']) for cell in mode['cells'] if cell['minimum'] <= max_bytes]
        interval = require_interval_partition((constants['mediumLimit'] + 1, max_bytes), cells,
                                             label=LABEL + '.boundedDomains')
        bounded_domains.append(dict(mode=mode['mode'], optionBitSet=mode['optionBitSet'],
                                    partition=interval, cells=cells))
    return dict(maxBytes=max_bytes, structure=shape, small=small_proofs, snapshots=snapshots,
        common=common, low=low, rep=leaf, vectors=paths, boundedDomains=bounded_domains,
        allCountModeOptionAlignmentCasesProved=True, arbitraryTemporalLoopCountProved=True,
        allSelectedBytesEqualInitialSource=True, allSelectedPayloadRangesInBounds=True,
        returnsOriginalDestination=True, sourceAndDestinationDisjointRequired=False,
        forwardSafeOverlapRequired=True, directionFlagClearRequired=True,
        nonTemporalPathAdmitted=False, backwardPathAdmitted=False, runtimeSelectionObserved=False,
        condition='Valid stable nonwrapping payloads disjoint from the call frame; destination <= source or destination >= source+length; supported selected SIMD state; DF=0 for REP. Both current mode halves and both option-bit outcomes, all destination alignment residues and every integer byte count through maxBytes are covered. Runtime CPU/options and memory visibility are not observed.')


def derive(image, pins, *, entry, max_bytes):
    """Fresh actual-entry/full-family copy component, without a pinned catalog."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    _publication_gate(image, pins)
    base = image.pe.image_base
    need('selected-entry', type(entry) is int and 0 <= entry - base < 1 << 32)
    family = image.unwind_index.family(entry - base)
    regions = []; rows = []; windows = []
    for owned in family['ranges']:
        start, end = owned['runtimeTriple'][:2]
        raw = image.pe.bytes_at_va(base + start, end - start)
        decoded = decode(image.mapper, raw, base + start)
        need('whole-owned-byte-partition', b''.join(bytes.fromhex(row['bytes']) for row in decoded) == raw)
        regions.append((base + start, raw)); rows += decoded
        windows.append(dict(startRva=start, endRva=end,
                            sha256=hashlib.sha256(raw).hexdigest().upper()))
    shape = structure(regions, entry, rows=rows, image_base=base)
    table_bytes = {}; table_windows = []
    for descriptor in shape['tables'].values():
        rva = descriptor['startRva']; size = descriptor['entriesCount'] * 4
        raw = image.pe.bytes_at_va(base + rva, size); table_bytes[rva] = raw
        table_windows.append(dict(startRva=rva, endRva=rva + size,
                                 sha256=hashlib.sha256(raw).hexdigest().upper(), rawHex=raw.hex()))
    # The selected REP leaf may have no pdata. Its exact reachable 16-byte
    # program is a separate prefix claim; no physical method extent is made.
    leaf = image.pe.bytes_at_va(shape['repEntry'], 16)
    rep_rows = decode(image.mapper, leaf, shape['repEntry'])
    proof = prove(regions, entry, rows=rows, tables=table_bytes, rep_rows=rep_rows,
                  image_base=base, max_bytes=max_bytes)
    _publication_gate(image, pins)
    return dict(schema='endfield.forward-copy-source.v1', status='proved-conditional-forward-copy',
        nativeInputs=pins, entryRva=entry - base, maxBytes=max_bytes,
        proof=dict(family=family, windows=windows, tables=table_windows,
                   repReachablePrefix=dict(startRva=shape['repEntry'] - base,
                       endRva=shape['repEntry'] - base + len(leaf),
                       sha256=hashlib.sha256(leaf).hexdigest().upper(), physicalExtentProved=False),
                   program=proof), wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Current actual copy entry/full unwind family, typed-independent byte programs, current tables and reachable REP leaf; complete finite dispatch domains and temporal loop/tail induction.',
            conditional=proof['condition'], unresolved=['live CPU/options/DF and provider selection',
                'backward overlap', 'non-temporal or counts above bound', 'typed caller/array/field framing']))
