"""Current actual-entry byte fill, independent of any typed caller contract.

The current owned main body supplies every dispatch table and anonymous global.
Only the pure complete instruction grammars and symbolic range/value algorithms
are shared with the reviewed fill domain. Runtime CPU flags, writable capacity,
DF and memory visibility remain conditions of a normal return.
"""
from __future__ import annotations

import hashlib

from .byte_fill_control import _main_program, _rep_program
from .fill_geometry import prove_byte_replication, prove_fill_geometry
from .fill_instructions import decode_fill_instructions
from .owned_partition import checked_rows
from .relation_control import transfer

LABEL = 'byteFillSource'


def need(check, condition, detail=None):
    if not condition:
        raise ValueError(LABEL + '.' + check + ':' + str(detail)[:600])


def structure(rows, image_base):
    """Discover operands; the complete grammar independently checks their use."""
    tables = []; comparisons = []; vector_modes = []; rep_modes = []; rep_entries = []
    for i, row in enumerate(rows):
        raw = bytes.fromhex(row['bytes']); at = int(row['va'], 16)
        op = row.get('memoryOperation', {}); address = op.get('address', {})
        if (op.get('direction') == 'load' and op.get('memoryBytes') == 4 and
                address.get('base') == 'r10' and address.get('scale') == 4):
            need('four-table-loads', len(tables) < 4 and i + 2 < len(rows))
            role = ('short', 'temporal32', 'nonTemporal32', 'fallback16')[len(tables)]
            rva = address.get('displacement')
            need('table-positive-rva', type(rva) is int and 0 <= rva < 1 << 32)
            tables.append(dict(role=role, siteRva=at-image_base,
                jumpSiteRva=int(rows[i+2]['va'], 16)-image_base,
                startRva=rva, endRva=rva+(16 if role == 'short' else 9)*4))
        if len(raw) == 7 and raw[:2] == b'\x83\x3d' and raw[-1] == 3:
            vector_modes.append(at+7+int.from_bytes(raw[2:6], 'little', signed=True)-image_base)
        if len(raw) == 7 and raw[:3] == b'\x4c\x3b\x05':
            comparisons.append(at+7+int.from_bytes(raw[3:], 'little', signed=True)-image_base)
        if 'byteTestOperation' in row:
            facts = row['byteTestOperation']; rep_modes.append(facts.get('address', -1)-image_base)
            need('rep-test-mask-and-following-branch', facts.get('mask') == 2 and
                 facts.get('bits') == 8 and i+1 < len(rows))
            edge = transfer(rows[i+1])
            need('rep-jne', edge.get('kind') == 'conditional' and edge.get('conditionCode') == 5, edge)
            rep_entries.append(edge['target']-image_base)
    need('four-distinct-tables', len(tables) == 4 and len({t['startRva'] for t in tables}) == 4)
    need('same-current-global-use-sites', len(vector_modes) == 1 and len(comparisons) == 4 and
         comparisons[0] == comparisons[3] and comparisons[1] == comparisons[2] and
         len(rep_modes) == 2 and rep_modes[0] == rep_modes[1] and
         len(rep_entries) == 2 and rep_entries[0] == rep_entries[1])
    globals_ = dict(vectorModeRva=vector_modes[0], lowerThresholdRva=comparisons[0],
                    upperThresholdRva=comparisons[1], repModeRva=rep_modes[0])
    need('positive-global-and-rep-rvas', all(type(v) is int and 0 <= v < 1 << 32
         for v in [*globals_.values(), rep_entries[0]]))
    ranges = sorted((t['startRva'], t['endRva']) for t in tables)
    need('nonoverlapping-tables', all(b <= a2 for (_, b), (a2, _) in zip(ranges, ranges[1:])))
    return dict(tables=tables, globals=globals_, repEntryRva=rep_entries[0])


def prove(regions, entry, *, rows, table_bytes, rep_regions, rep_rows, image_base, max_bytes):
    need('finite-own-domain', type(max_bytes) is int and 0 < max_bytes < 1 << 31)
    need('actual-entry-is-first-owned-instruction', rows and int(rows[0]['va'], 16) == entry)
    all_rows = []
    for pieces, decoded in ((regions, rows), (rep_regions, rep_rows)):
        used = set()
        for start, raw in pieces:
            selected = [r for r in decoded if start <= int(r['va'], 16) < start+len(raw)]
            need('complete-current-owned-instructions', selected and int(selected[0]['va'], 16) == start)
            all_rows += checked_rows(selected, raw, LABEL)
            used.update(int(r['va'], 16) for r in selected)
        need('all-decoded-instructions-owned', used == {int(r['va'], 16) for r in decoded})
    shape = structure(rows, image_base)
    need('exact-rep-prefix-entry', rep_rows and
         int(rep_rows[0]['va'], 16) == image_base+shape['repEntryRva'])
    need('exact-current-table-set', set(table_bytes) == {t['startRva'] for t in shape['tables']})
    for table in shape['tables']:
        raw = table_bytes[table['startRva']]
        need('complete-current-table-bytes', isinstance(raw, bytes) and len(raw) == table['endRva']-table['startRva'])
        table['targetRvas'] = [int.from_bytes(raw[i:i+4], 'little') for i in range(0, len(raw), 4)]
    _main_program(rows, image_base, shape); _rep_program(rep_rows)
    starts = {int(r['va'], 16): r for r in all_rows}
    need('unique-main-and-rep-instructions', len(starts) == len(all_rows))
    jumps = {image_base+t['jumpSiteRva']: [image_base+r for r in t['targetRvas']] for t in shape['tables']}
    edges = {}; branches = []; stores = []; returns = []
    for at, row in starts.items():
        if 'fillJumpOperation' in row:
            need('only-owned-table-indirect-jumps', at in jumps); successors = jumps[at]
        else:
            edge = transfer(row); kind = edge['kind']; successors = []
            if kind == 'return': returns.append(at-image_base)
            elif kind in ('jump', 'conditional'):
                successors.append(edge['target'])
                branches.append(dict(siteRva=at-image_base, kind=kind, targetRva=edge['target']-image_base))
            else: need('no-unproved-call-or-transfer', kind == 'next', edge)
            if kind in ('next', 'conditional'): successors.append(at+len(bytes.fromhex(row['bytes'])))
        need('all-edges-owned-instruction-boundaries', all(target in starts for target in successors), hex(at))
        edges[at] = successors
        if row.get('memoryOperation', {}).get('direction') == 'store' or 'fillStringOperation' in row:
            stores.append(at-image_base)
    reached = set(); pending = [entry]
    while pending:
        at = pending.pop()
        if at not in reached: reached.add(at); pending += edges[at]
    need('no-unreachable-nonpadding', all(starts[a]['text'] == 'nop' for a in set(starts)-reached))
    for count in range(16, 33):
        need('bounded-vector-coverage', set(range(16)) | set(range(count-16, count)) == set(range(count)))
    return dict(structure=shape, maxBytes=max_bytes, checkedInstructions=len(all_rows),
        tableEntries=sum(len(t['targetRvas']) for t in shape['tables']), branches=branches,
        returnRvas=returns, payloadStoreSiteRvas=stores, reachableInstructions=len(reached),
        byteReplication=prove_byte_replication(), vectorGeometry=[prove_fill_geometry(width=w, chunk=8*w) for w in (16, 32)],
        completeOwnedFillAndRepProgramsChecked=True, normalReturnEqualsIncomingDestinationProved=True,
        allRequestedBytesEqualLowIncomingValueByteConditionallyProved=True,
        repPreservesRdiAndRestoresFrameProved=True, nonTemporalStoresHaveFollowingSfenceProved=True,
        payloadReadsRequired=False, directionFlagClearRequired=True, validWritableExtentRequired=True,
        compatibleCpuAndSimdStateRequired=True, nonWrappingEndpointAndControlStorageNoninterferenceRequired=True,
        compatibleCallFrameAndNormalReturnRequired=True, allStoresGloballyVisibleAtReturnProved=False,
        liveModeFlagsObserved=False, allocationSuccessOrValidCapacityProved=False, typedCallerDomainImported=False)


def derive(image, pins, *, entry, max_bytes):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    _publication_gate(image, pins); base = image.pe.image_base
    need('actual-entry', type(entry) is int and 0 <= entry-base < 1 << 32)
    family = image.unwind_index.family(entry-base); regions = []; rows = []; windows = []
    for piece in family['ranges']:
        a, b = piece['runtimeTriple'][:2]; raw = image.pe.bytes_at_va(base+a, b-a)
        regions.append((base+a, raw)); rows += decode_fill_instructions(image.mapper, raw, base+a)
        windows.append(dict(startRva=a, endRva=b, sha256=hashlib.sha256(raw).hexdigest().upper()))
    shape = structure(rows, base); tables = {}; table_windows = []
    for table in shape['tables']:
        a, b = table['startRva'], table['endRva']; raw = image.pe.bytes_at_va(base+a, b-a); tables[a] = raw
        table_windows.append(dict(startRva=a, endRva=b, rawHex=raw.hex(), sha256=hashlib.sha256(raw).hexdigest().upper()))
    at = base+shape['repEntryRva']; raw = image.pe.bytes_at_va(at, 16)
    rep_regions = [(at, raw)]; rep_rows = decode_fill_instructions(image.mapper, raw, at)
    proof = prove(regions, entry, rows=rows, table_bytes=tables, rep_regions=rep_regions,
                  rep_rows=rep_rows, image_base=base, max_bytes=max_bytes)
    _publication_gate(image, pins)
    return dict(schema='endfield.byte-fill-source.v1', status='proved-conditional-byte-fill-source',
        nativeInputs=pins, entryRva=entry-base, maxBytes=max_bytes,
        proof=dict(family=family, sourceWindows=windows, sourceRegions=[[a, raw.hex()] for a, raw in regions],
            tables=table_windows, repReachablePrefix=dict(startRva=at-base, endRva=at-base+len(raw),
                rawHex=raw.hex(), sha256=hashlib.sha256(raw).hexdigest().upper(), physicalExtentProved=False), program=proof),
        wholeOwnerAdmitted=False, runtimeExecutionObserved=False)
