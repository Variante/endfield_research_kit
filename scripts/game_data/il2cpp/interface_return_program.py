"""Complete selected interface-return adapter and its exact-width arithmetic.

The reviewed byte program is versioned data. Call relocations are independently
decoded; no raw address, hash or native program block is embedded in Python.
"""
LABEL = 'interfaceReturnProgram'


def interface_pair_address(class_pointer, offset_dword_bits, incoming_slot, *, vtable_index_bias, invoke_data_stride_bytes):
    if any(type(v) != int for v in (class_pointer, offset_dword_bits, incoming_slot)):
        raise ValueError(LABEL + '.integer-domain')
    if not 0 <= class_pointer < 2**64 or not 0 <= offset_dword_bits < 2**32 or not 0 <= incoming_slot < 2**64:
        raise ValueError(LABEL + '.unsigned-domain')
    slot = incoming_slot & 0xffff
    total = (offset_dword_bits + slot) & 0xffffffff
    signed = total if total < 2**31 else total - 2**32
    if (type(vtable_index_bias) != int or type(invoke_data_stride_bytes) != int
            or invoke_data_stride_bytes <= 0):
        raise ValueError(LABEL + '.address-geometry-domain')
    return (class_pointer + (signed + vtable_index_bias) * invoke_data_stride_bytes) & ((1 << 64) - 1)


def interface_search_iterations(count_word, match_index=None):
    if type(count_word) != int or not 0 <= count_word <= 0xffff:
        raise ValueError(LABEL + '.word-count-domain')
    if match_index is None: return count_word
    if type(match_index) != int or not 0 <= match_index < count_word:
        raise ValueError(LABEL + '.match-index-domain')
    return match_index + 1


def check_interface_return_program(raw, *, pointer, specification):
    expected = bytes.fromhex(specification['programHex'])
    if len(raw) != len(expected): raise ValueError(LABEL + '.complete-byte-length')
    roles = set(); variable = set(); calls = []
    for declaration in specification['relocationCalls']:
        offset, role = declaration['offset'], declaration['role']
        if role in roles or type(offset) != int or offset < 0 or offset+5 > len(raw):
            raise ValueError(LABEL + '.call-declaration')
        if expected[offset] != 0xe8 or raw[offset] != 0xe8:
            raise ValueError(LABEL + '.actual-direct-call')
        operands = set(range(offset+1, offset+5))
        if variable & operands: raise ValueError(LABEL + '.overlapping-relocations')
        variable |= operands; roles.add(role)
        target = pointer+offset+5+int.from_bytes(raw[offset+1:offset+5], 'little', signed=True)
        if pointer <= target < pointer+len(raw): raise ValueError(LABEL + '.call-into-owned-body')
        calls.append({'role': role, 'site': pointer+offset, 'target': target})
    if roles != {'classPreparation', 'lookup'}: raise ValueError(LABEL + '.call-membership')
    for offset, (actual, wanted) in enumerate(zip(raw, expected, strict=True)):
        if offset not in variable and actual != wanted:
            raise ValueError(f'{LABEL}.program-byte: offset={offset} expected={wanted:02X} actual={actual:02X}')
    def operand(prefix, size, signed=False):
        prefix = bytes.fromhex(prefix)
        positions = [i for i in range(len(raw)) if raw[i:i+len(prefix)] == prefix]
        if len(positions) != 1 or positions[0]+len(prefix)+size > len(raw):
            raise ValueError(LABEL + '.unique-operand-source:' + prefix.hex())
        start = positions[0]+len(prefix)
        return int.from_bytes(raw[start:start+size], 'little', signed=signed)
    for opcode in ('440FB7F2', '6641FFC2', '4103C6', '4898', '41FFD1', '4803D2', '483934C1'):
        if raw.count(bytes.fromhex(opcode)) != 1:
            raise ValueError(LABEL + '.selected-width-or-transfer:' + opcode)
    if raw.count(bytes.fromhex('66443BD2')) != 2:
        raise ValueError(LABEL + '.two-word-count-comparisons')
    geometry = {'interfaceCountWordOffset': operand('0FB793', 4, True),
        'interfaceTablePointerOffset': operand('488B8B', 4, True),
        'entryStrideBytes': 2 * (1 << (bytes.fromhex('D1')[0] >> 6)),
        'entryOffsetDwordOffset': operand('8B44D1', 1, True),
        'vtableIndexBias': operand('4883C0', 1, True),
        'invokeDataStrideBytes': 1 << operand('48C1E0', 1),
        'copiedReturnBytes': operand('F20F1048', 1, True) + 8}
    if specification['matchedReturnControl'] != geometry:
        raise ValueError(LABEL + '.reviewed-operand-layout')
    frame_bytes = operand('4883EC', 1)
    local_offset = operand('488D4C24', 1)
    copy_bytes = geometry['copiedReturnBytes']
    if local_offset < 32 or local_offset+copy_bytes > frame_bytes or frame_bytes % 16:
        raise ValueError(LABEL + '.frame-home-buffer-geometry')
    return {'status': 'complete-selected-interface-return-adapter-proved', 'bytesChecked': len(raw),
        'calls': calls, 'incomingSlotBitsUsed': 16, 'interfaceCountBits': 16, 'counterBits': 16,
        'searchIterationsAtMostCountWord': True, 'firstComparedMatchSelected': True,
        'offsetAndSlotAdditionBits': 32, 'sumSignExtendedToBits': 64,
        'invokeDataGeometry': geometry, 'invokeDataPairBytes': 16, 'calleeRegister': 'r9', 'calleeThisRegister': 'rdx',
        'calleeMethodInfoRegister': 'r8', 'calleeReturnBufferRegister': 'rcx',
        'copiedReturnBytes': copy_bytes, 'copiedFromCalleeReturnedReference': True,
        'returnsIncomingOutputPointer': True, 'frame': {'stackAllocationBytes': frame_bytes, 'pushBytes': 8,
            'calleeHomeBytes': 32, 'localReturnBufferOffset': local_offset, 'localReturnBufferBytes': copy_bytes,
            'alignedCallsUnderWin64EntryConvention': True},
        'actualImplementationKnown': False, 'lookupResultKnown': False, 'runtimeExecutionKnown': False,
        'evidenceBoundary': 'conditional',
        'conditions': ['ordinary returning Win64 callees preserve nonvolatile references',
            'readable compatible class/table/InvokeData and callee-return reference storage',
            'writable disjoint output/frame storage',
            'the supplied runtime interface pointer is correctly initialized for its declared type'],
        'unresolved': ['runtime interface pointer and method target', 'class preparation and lookup effects',
                       'lookup pair contents', 'callee values/effects', 'actual invocation']}


def check_default_interface_return(raw, *, expected_program, copied_value_bytes):
    if raw != bytes.fromhex(expected_program): raise ValueError(LABEL + '.complete-default-program')
    if copied_value_bytes != 24: raise ValueError(LABEL + '.default-value-shape')
    return {'status': 'complete-default-interface-zero-return-proved', 'bytesChecked': len(raw),
        'outputBytesZeroed': copied_value_bytes, 'returnsIncomingOutputPointer': True,
        'receiverFieldsRead': False, 'callsMade': False, 'runtimeExecutionKnown': False,
        'evidenceBoundary': 'conditional',
        'condition': 'this named compiled body is invoked with a valid writable hidden output buffer'}
