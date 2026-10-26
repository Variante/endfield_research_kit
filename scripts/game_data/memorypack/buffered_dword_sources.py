"""Complete physical DWORD reader path under an available-buffer condition.

The caller authenticates the selected image, reviewed code window and actual
source CALL. This transfer proves four wire bytes, not generic registration,
provider selection, a collection formatter or a cold refill/error path.
"""
from __future__ import annotations

from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext


def validate_buffered_dword_reader(image, window):
    """Check every normal-path instruction, branch, source read and store."""
    image.check_windows([window], label='bufferedDwordSource')
    start, end = window['startRva'], window['endRva']
    if type(start) is not int or type(end) is not int or end - start != 80:
        raise ValueError('bufferedDwordSource:complete-owned-window')
    layout = NativeReferenceContext(image)
    offsets = {name: layout.field('MemoryPack.MemoryPackReader::'+name)[2] - 16
               for name in ('currentPtr', 'bufferLength', 'advancedCount', 'consumed')}
    if (any(type(n) is not int or not 0 <= n < 128 for n in offsets.values())
            or len(set(offsets.values())) != 4):
        raise ValueError('bufferedDwordSource:metadata-reader-offsets')
    ptr, remaining, advanced, consumed = (offsets[name] for name in
        ('currentPtr', 'bufferLength', 'advancedCount', 'consumed'))
    expected = [b'\x48\x89\x5c\x24\x08', b'\x48\x89\x74\x24\x10', b'\x57',
        b'\x48\x83\xec\x20', bytes((0x83, 0x79, remaining, 4)), b'\x48\x8b\xd9',
        b'\x0f\x8c', bytes((0x48, 0x8b, 0x43, ptr)), b'\x8b\x30',
        bytes((0x8b, 0x7b, remaining)), b'\x83\xef\x04', b'\x0f\x88',
        bytes((0x48, 0x83, 0x43, ptr, 4)), bytes((0x83, 0x43, advanced, 4)),
        bytes((0x83, 0x43, consumed, 4)), bytes((0x89, 0x7b, remaining)),
        b'\x48\x8b\x5c\x24\x30', b'\x8b\xc6', b'\x48\x8b\x74\x24\x38',
        b'\x48\x83\xc4\x20', b'\x5f', b'\xc3']
    raw = image.pe.bytes_at_va(image.pe.image_base + start, end - start)
    if len(raw) != end - start:
        raise ValueError('bufferedDwordSource:truncated-window')
    at = 0; program = []; cold_edges = []
    for index, opcode in enumerate(expected):
        size = 6 if index in (6, 11) else len(opcode)
        instruction = raw[at:at+size]
        if len(instruction) != size or instruction[:len(opcode)] != opcode:
            raise ValueError(f'bufferedDwordSource:instruction={index}; rva={start+at}; '
                             f'expected={opcode.hex()}; actual={instruction.hex()}')
        program.append([start+at, instruction.hex().upper()])
        if index in (6, 11):
            target = start+at+size+int.from_bytes(instruction[2:], 'little', signed=True)
            if start <= target < end:
                raise ValueError('bufferedDwordSource:cold-edge-enters-normal-body')
            cold_edges.append({'instructionRva': start+at, 'targetRva': target,
                'condition': 'signed-buffer-length-less-than-four' if index == 6
                             else 'negative-length-after-subtract-four',
                'takenUnderAvailableBufferCondition': False, 'targetBodyProved': False})
        at += size
    if at != len(raw):
        raise ValueError('bufferedDwordSource:unowned-or-trailing-instructions')
    return {'scope': 'complete-buffered-normal-dword-path', 'entryRva': start,
        'returnRva': program[-1][0], 'program': program, 'readerFieldsUnboxedOffsets': offsets,
        'wireBytesRead': 4, 'returnedBits': 'EAX equals source DWORD, with its raw bits retained',
        'cursorUpdates': {'currentPtr': 4, 'bufferLength': -4, 'advancedCount': 4, 'consumed': 4},
        'coldEdges': cold_edges,
        'condition': 'Coherent readable reader storage and signed bufferLength >= 4 on entry; normal stack/return behavior.',
        'genericRegisteredEntryIdentityProved': False, 'collectionElementSelectionProved': False,
        'runtimeExecutionObserved': False}
