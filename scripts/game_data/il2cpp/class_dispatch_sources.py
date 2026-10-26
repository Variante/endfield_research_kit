"""Stored interface-count, allocated self pointer and static method-pair joins.

Callers authenticate the native image, full creation/control programs and
metadata before/after. Allocator capacity and live receiver/table identity are
never inferred from these source copies or static interface declarations.
"""
import struct
from .class_creation_control import _prefix, _dominators
from .field_setup_control import _graph, _frames
from .initializer_control import _ALIASES, control_transfer
from .memory_moves import decode_memory_move
from .integer_widths import decode_word_zero_extension
from .formatter_composition import _vtable

LABEL = 'classDispatchSources'


def metadata_dispatch_count_columns(catalog, metadata):
    section = metadata.sections['typeDefinitions']; stride = metadata.type_record_size
    if stride not in (88, 92) or not metadata.types or section.size != stride * len(metadata.types):
        raise ValueError(LABEL + '.metadata-count-framing')
    layout = None
    for ordinal, td in enumerate(metadata.types):
        if td.index != ordinal: raise ValueError(LABEL + '.metadata-type-index')
        start = section.offset + ordinal * stride
        prefix = catalog.parse_type_reference_prefix(metadata.buf, start, stride)
        tail = catalog.parse_type_layout_tail(metadata.buf, prefix[-1], stride)
        count_start = tail[-1] - 24
        if tail[-1] != start + stride or len(tail[3]) != 8:
            raise ValueError(LABEL + '.metadata-count-tail')
        offsets = {'recordBytes': stride, 'vtableCountWordOffset': count_start-start+5*2,
            'interfaceOffsetsCountWordOffset': count_start-start+7*2}
        if layout is not None and offsets != layout: raise ValueError(LABEL + '.metadata-count-offset-drift')
        layout = offsets
        actual = tuple(struct.unpack_from('<H', metadata.buf, start + layout[k])[0]
            for k in ('vtableCountWordOffset', 'interfaceOffsetsCountWordOffset'))
        if actual != (tail[3][5], tail[3][7]) or actual != (td.vtable_count, td.interface_offsets_count):
            raise ValueError(LABEL + '.named-metadata-count-source')
    return {**layout, 'rowsChecked': len(metadata.types), 'runtimeSourcePointerIdentityProved': False}


def _memory(row, direction, register, bits, receiver, offset):
    raw = bytes.fromhex(row['bytes']); decoded = decode_memory_move(raw, 0, int(row['va'], 16))
    if decoded is None or decoded[1] != len(raw): raise ValueError(LABEL + '.complete-memory-move')
    fact = decoded[0]['memoryOperation']; a = fact['address']
    if (fact['direction'], fact['register'], fact['registerBits'], fact['memoryBytes'],
        a['base'], a['index'], a['scale'], a['displacement'], a['ripRelative'], a['addressBits']) != (
        direction, register, bits, bits//8, receiver, None, 1, offset, False, 64) or row['text'] != decoded[0]['text']:
        raise ValueError(LABEL + '.selected-memory-operands')


def _preserved(rows, start, end, registers, *, only_next=False):
    readers = {'cmp', 'test', 'bt', 'nop', 'push'}
    writers = {'mov', 'movzx', 'movsx', 'movsxd', 'movups', 'lea', 'xor', 'and', 'or', 'add', 'sub',
        'imul', 'inc', 'dec', 'shl', 'shr', 'sar', 'neg', 'not', 'bts', 'cmovne', 'sete', 'pop'}
    for row in rows:
        if not start <= int(row['va'], 16) < end: continue
        kind = control_transfer(row)['kind']
        if kind != 'next':
            if only_next: raise ValueError(LABEL + '.fresh-allocation-local-transfer')
            continue
        head, _, rest = row['text'].partition(' ')
        if head in readers: continue
        if head not in writers: raise ValueError(LABEL + '.unknown-register-writer:' + head)
        if _ALIASES.get(rest.split(',')[0]) in registers:
            raise ValueError(LABEL + '.selected-register-overwritten')


def _overlaps(stores, receivers, offset, size):
    found = []
    for row in stores:
        fact = row['facts']; a = fact.get('address', fact.get('destinationAddress', {}))
        width = fact.get('memoryBytes', fact.get('memoryWriteBytes'))
        if a.get('base') in receivers and a.get('index') is None and not a.get('ripRelative'):
            if type(width) != int or width <= 0: raise ValueError(LABEL + '.unknown-direct-store-width')
            if a['displacement'] < offset+size and offset < a['displacement']+width: found.append(row['siteRva'])
    return found


def prove_creation_dispatch_sources(rows, base, contract, self_offset, count_offset, columns):
    function = contract['function']; prefix = function['sourceAllocationPrefix']
    edges, _, stores = _graph(rows, base, function); _frames(rows, edges, base, function)
    allocation = _prefix(rows, base, contract, function)
    dom = _dominators(edges, base+function['entryRva'])
    by_at = {int(r['va'], 16): r for r in rows}
    self_sites = _overlaps(stores, {'rax', 'rbx'}, self_offset, 8)
    count_sites = _overlaps(stores, {'rbx'}, count_offset, 2)
    if len(self_sites) != 1 or len(count_sites) != 1:
        raise ValueError(LABEL + '.unique-self-and-count-direct-stores')
    self_at, count_at = base+self_sites[0], base+count_sites[0]
    _memory(by_at[self_at], 'store', 'rax', 64, 'rax', self_offset)
    after_call = allocation + len(bytes.fromhex(by_at[allocation]['bytes']))
    if not after_call < self_at: raise ValueError(LABEL + '.self-store-before-allocation-return')
    _preserved(rows, after_call, self_at, {'rax'}, only_next=True)
    _memory(by_at[count_at], 'store', 'ax', 16, 'rbx', count_offset)
    position = rows.index(by_at[count_at])
    if not position: raise ValueError(LABEL + '.missing-count-source')
    load = rows[position-1]; load_at = int(load['va'], 16); raw = bytes.fromhex(load['bytes'])
    decoded = decode_word_zero_extension(raw, 0, load_at)
    if decoded is None or decoded[1] != len(raw) or load_at+len(raw) != count_at:
        raise ValueError(LABEL + '.adjacent-unsigned-count-load')
    fact = decoded[0]['wordZeroExtensionOperation']; a = fact['sourceAddress'] or {}
    if (fact['destinationRegister'], fact['destinationBits'], fact['sourceBits'], fact['memoryReadBytes'],
        a.get('base'), a.get('index'), a.get('scale'), a.get('displacement'), a.get('ripRelative')) != (
        'eax', 32, 16, 2, 'rdi', None, 1, columns['interfaceOffsetsCountWordOffset'], False) or load['text'] != decoded[0]['text']:
        raise ValueError(LABEL + '.named-interface-count-load-operands')
    bound = base+prefix['window']['endRva']
    if not bound <= load_at < count_at: raise ValueError(LABEL + '.count-source-before-allocation-prefix')
    _preserved(rows, bound, count_at, {'rdi', 'rbx'})
    if allocation not in dom[self_at] or allocation not in dom[load_at] or load_at not in dom[count_at]:
        raise ValueError(LABEL + '.allocation-source-store-dominance')
    if not function['returnRvas'] or any(self_at not in dom[base+r] or count_at not in dom[base+r] for r in function['returnRvas']):
        raise ValueError(LABEL + '.dispatch-stores-do-not-dominate-normal-returns')
    if columns['vtableCountWordOffset'] != contract['recordLayout']['vtableCountWordOffset']:
        raise ValueError(LABEL + '.named-allocation-vtable-count-source')
    return {'allocationCallRva': allocation-base,
        'selfPointer': {'siteRva': self_at-base, 'allocationByteOffset': self_offset,
            'freshAllocationRaxStoredIntoItsOwnQwordProved': True, 'directStoreUnique': True,
            'actualPreparedReceiverPointerEqualityProved': False},
        'interfaceRecordCount': {'loadRva': load_at-base, 'storeRva': count_at-base,
            'sourceRecordWordOffset': columns['interfaceOffsetsCountWordOffset'], 'allocationWordOffset': count_offset,
            'namedInterfaceOffsetsCountCopiedToAllocationProved': True, 'bits': 16, 'directStoreUnique': True,
            'unchangedByChildrenOrAliasesProved': False},
        'storesDominateEveryNormalLocalReturn': True,
        'allocationRequest': {'source': 'current stored metadata vtable_count WORD',
            'sourceRecordWordOffset': columns['vtableCountWordOffset'],
            'bias': prefix['allocationBias'], 'shift': prefix['allocationShift'],
            'formula': '(zero_extend_64(stored vtable_count WORD) + bias) << shift',
            'actualAllocationCapacityOrOutcomeProved': False},
        'runtimeMetadataClassOrArrayIdentityProved': False, 'wholeRootAdmitted': False}


def static_interface_context_bindings(image, selected, context_contract, sources):
    metadata = image.metadata; interface = context_contract['interfaceSlot']
    section = metadata.sections['interfaceOffsets']; slot = interface['interfaceMethod']['slot']
    request = sources['allocationRequest']; result = []
    for case in context_contract['cases']:
        td = metadata.types[case['uniqueCurrentMetadataType']['typeDefinition']]
        start = section.offset + td.interface_offsets_start*8; size = td.interface_offsets_count*8
        if not 0 <= td.interface_offsets_count or not section.offset <= start <= section.offset+section.size-size:
            raise ValueError(LABEL + '.interface-offset-record-range')
        pairs = list(struct.iter_unpack('<ii', metadata.buf[start:start+size]))
        found = [(i, t, offset) for i, (t, offset) in enumerate(pairs) if t == interface['registeredTypeIndex']]
        if len(found) != 1: raise ValueError(LABEL + '.unique-static-interface-record')
        ordinal, type_index, offset = found[0]
        if selected.type_name(type_index) != interface['typeName']:
            raise ValueError(LABEL + '.current-static-interface-type')
        effective = offset+slot
        if not 0 <= offset <= effective < td.vtable_count or effective >= 1 << 31:
            raise ValueError(LABEL + '.static-slot-within-vtable-count')
        method_index = case['namedGetter']['method'][0]
        _vtable(image, td.index, effective, method_index, LABEL)
        pair_end = ((effective+request['bias']) << request['shift'])+16
        requested = (td.vtable_count+request['bias']) << request['shift']
        if request['bias'] < 0 or request['shift'] != 4 or pair_end > requested:
            raise ValueError(LABEL + '.static-pair-within-allocation-request-formula')
        result.append({'type': metadata.type_full_name(td), 'typeDefinition': td.index,
            'interfaceRecordIndex': td.interface_offsets_start+ordinal,
            'interfaceOffsetsCount': td.interface_offsets_count, 'interfaceOffset': offset,
            'interfaceSlot': slot, 'effectiveVtableSlot': effective, 'vtableCount': td.vtable_count,
            'getContextMethodDefinition': method_index, 'currentStaticVtableGetterProved': True,
            'pairEndByteOffset': pair_end, 'recordedAllocationRequestBytes': requested,
            'staticPairWithinRecordedAllocationRequestProved': True,
            'runtimeInterfaceArrayPairOrCapacityProved': False})
    return result
