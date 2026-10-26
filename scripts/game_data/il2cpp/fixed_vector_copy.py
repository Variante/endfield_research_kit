"""Prove bounded fixed-size vector copies from complete selected x64 bytes.

Input address identities and source/destination regions are caller obligations.
Only literal counters, full-width LEA, legacy unaligned vector moves, scalar
SUB and local JNE are admitted. Distinct symbolic regions model disjoint input
storage; this proves byte transfer under that selection, never live execution.
"""
from __future__ import annotations

from .backward_copy_instructions import decode_legacy_vector_move
from .integer_addressing import _reg, _required, decode_lea_address


def prove_fixed_vector_copy(raw: bytes, *, initial_pointers: dict,
                            source: tuple[str, int, int],
                            destination: tuple[str, int, int],
                            maximum_steps: int = 4096) -> dict:
    """Return exact symbolic byte coverage and final register addresses.

    Regions are ``(identity, offset, byte_count)``; initial pointer registers
    hold ``(identity, offset)``. Identities must differ, and callers must prove
    this disjoint-storage selection and the selected incoming register values.
    """
    def fail(check, actual):
        raise ValueError(f'fixed-vector-copy.{check}: {str(actual)[:384]}')

    if not isinstance(raw, bytes) or not raw:
        fail('program', 'nonempty original instruction bytes required')
    if (not isinstance(source, tuple) or not isinstance(destination, tuple)
            or len(source) != 3 or len(destination) != 3
            or any(not isinstance(r[0], str) or not r[0]
                   or type(r[1]) is not int or type(r[2]) is not int
                   or not 0 < r[2] <= 1024 * 1024 for r in (source, destination))
            or source[0] == destination[0] or source[2] != destination[2]
            or type(maximum_steps) is not int or not 0 < maximum_steps <= 1000000):
        fail('selection', (source, destination, maximum_steps))
    registers = {}
    valid_registers = {_reg(n) for n in range(16)}
    for name, pointer in initial_pointers.items():
        if (name not in valid_registers or not isinstance(pointer, tuple)
                or len(pointer) != 2 or not isinstance(pointer[0], str)
                or type(pointer[1]) is not int):
            fail('initial-pointer', (name, pointer))
        registers[name] = pointer

    instructions = {}
    at = 0
    while at < len(raw):
        begin = at
        decoded = decode_lea_address(raw, at, 0)
        if decoded is not None:
            row, at = decoded
            operation = row['addressOperation']
            if operation['destinationBits'] != 64:
                fail('lea-width', row)
            instruction = ('lea', operation, at)
        else:
            decoded = decode_legacy_vector_move(raw, at, 0)
            if decoded is not None:
                row, at = decoded
                operation = row.get('memoryOperation')
                if operation is None or operation['requiredAlignmentBytes'] != 1:
                    fail('vector-form', row)
                instruction = ('move', operation, at)
            else:
                prefix_at = at
                rex = 0
                if 0x40 <= raw[prefix_at] <= 0x4f:
                    rex = raw[prefix_at]
                    prefix_at += 1
                opcode = _required(raw, prefix_at, 1, begin, 'fixed-copy-opcode')[0]
                if 0xb8 <= opcode <= 0xbf:
                    if rex & 6:
                        fail('immediate-prefix', rex)
                    size = 8 if rex & 8 else 4
                    value = int.from_bytes(_required(raw, prefix_at + 1, size, begin, 'fixed-copy-immediate'), 'little')
                    at = prefix_at + 1 + size
                    instruction = ('literal', (_reg((opcode - 0xb8) | ((rex & 1) << 3)), value), at)
                elif opcode in (0x81, 0x83):
                    modrm = _required(raw, prefix_at + 1, 1, begin, 'fixed-copy-sub')[0]
                    if rex not in (0x48, 0x49) or modrm >> 6 != 3 or (modrm >> 3) & 7 != 5:
                        fail('sub-form', (rex, modrm))
                    size = 1 if opcode == 0x83 else 4
                    value = int.from_bytes(_required(raw, prefix_at + 2, size, begin, 'fixed-copy-sub-immediate'), 'little', signed=True)
                    at = prefix_at + 2 + size
                    instruction = ('sub', (_reg((modrm & 7) | ((rex & 1) << 3)), value), at)
                elif rex == 0 and (opcode == 0x75 or raw[prefix_at:prefix_at + 2] == b'\x0f\x85'):
                    size = 1 if opcode == 0x75 else 4
                    head = 1 if size == 1 else 2
                    displacement = int.from_bytes(_required(raw, prefix_at + head, size, begin, 'fixed-copy-jne'), 'little', signed=True)
                    at = prefix_at + head + size
                    instruction = ('jne', at + displacement, at)
                else:
                    fail('unsupported-instruction', {'offset': begin, 'remaining': raw[begin:begin + 12].hex()})
        if at <= begin:
            fail('decoder-boundary', (begin, at))
        instructions[begin] = instruction
    for begin, (kind, operation, _end) in instructions.items():
        if kind == 'jne' and operation not in instructions:
            fail('branch-target', (begin, operation))

    def address(operand):
        if operand['ripRelative'] or operand['addressBits'] != 64:
            fail('address-width', operand)
        base = registers.get(operand['base'])
        if not isinstance(base, tuple):
            fail('address-base', operand)
        offset = base[1] + operand['displacement']
        if operand['index'] is not None:
            value = registers.get(operand['index'])
            if type(value) is not int:
                fail('address-index', operand)
            offset += value * operand['scale']
        return base[0], offset

    vectors = {}
    output = {}
    visited = set()
    zero = None
    at = steps = loads = stores = taken = 0
    while at != len(raw):
        if steps >= maximum_steps:
            fail('step-limit', {'maximum': maximum_steps, 'offset': at})
        if at not in instructions:
            fail('execution-boundary', at)
        visited.add(at)
        kind, operation, end = instructions[at]
        next_at = end
        if kind == 'lea':
            registers[operation['destination']] = address(operation)
        elif kind == 'literal':
            name, value = operation
            registers[name] = value
        elif kind == 'sub':
            name, value = operation
            prior = registers.get(name)
            if type(prior) is not int:
                fail('scalar-counter', (name, prior))
            registers[name] = (prior - value) % (1 << 64)
            zero = registers[name] == 0
        elif kind == 'jne':
            if zero is None:
                fail('branch-flags', at)
            if not zero:
                next_at = operation
                taken += 1
        elif kind == 'move':
            identity, offset = address(operation['address'])
            region = source if operation['direction'] == 'load' else destination
            width = operation['memoryBytes']
            if identity != region[0] or not region[1] <= offset <= offset + width <= region[1] + region[2]:
                fail('payload-range', (operation['direction'], identity, offset, width, region))
            selected = offset - region[1]
            vector = operation['backingRegister']
            if operation['direction'] == 'load':
                vectors[vector] = tuple(range(selected, selected + width))
                loads += 1
            else:
                expected = tuple(range(selected, selected + width))
                if vectors.get(vector) != expected:
                    fail('stored-byte-identity', (selected, vectors.get(vector), expected))
                for byte in expected:
                    output[byte] = byte
                stores += 1
        at = next_at
        steps += 1
    if visited != set(instructions):
        fail('unexecuted-instruction', sorted(set(instructions) - visited))
    if set(output) != set(range(source[2])):
        fail('complete-byte-coverage', {'expected': source[2], 'actual': len(output)})
    return {'status': 'proved', 'byteCount': source[2], 'instructionBytes': len(raw),
            'instructionCount': len(instructions), 'steps': steps,
            'loads': loads, 'stores': stores, 'takenBackEdges': taken,
            'allDestinationBytesEqualInitialSource': True,
            'finalPointerRegisters': {name: {'identity': value[0], 'offset': value[1]}
                                      for name, value in registers.items() if isinstance(value, tuple)},
            'conditionalSelection': 'Supplied incoming register addresses, distinct disjoint source/destination storage regions, and nonwrapping affine address arithmetic.',
            'runtimeExecutionObserved': False}
