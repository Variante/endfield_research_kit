"""Selected canonical entry and complete generic call argument projections.

The fourth registration word is retained without following an adjustor table.
This deliberately proves no full entry, invoker, runtime MethodInfo or closed
receiver layout. An absent exact MethodSpec row is refused, never replaced by
an Object instantiation on a shared method pointer.
"""
from __future__ import annotations

import struct

from .context import relative_branch_target, rip_qword_load_target
from .integer_addressing import decode_lea_address


def project_generic_canonical_entry(records: bytes, pointers: bytes, *,
                                    record_count: int, pointer_count: int,
                                    spec_count: int, selected_spec: int,
                                    invoker_count: int) -> dict:
    """Check the exact selected MethodSpec -> canonical pointer projection."""
    for count in (record_count, pointer_count, spec_count, invoker_count):
        if type(count) is not int or not 0 <= count <= 1_000_000:
            raise ValueError('generic-call-projection.count: bounded integer counts required')
    if (not isinstance(records, bytes) or len(records) != record_count*16
            or not isinstance(pointers, bytes) or len(pointers) != pointer_count*8):
        raise ValueError('generic-call-projection.framing: exact declared arrays required')
    if type(selected_spec) is not int or not 0 <= selected_spec < spec_count:
        raise ValueError('generic-call-projection.selection: bounded exact MethodSpec required')
    selected = []
    for index, words in enumerate(struct.iter_unpack('<iiii', records)):
        spec, slot, invoker, fourth = words
        if not 0 <= spec < spec_count:
            raise ValueError('generic-call-projection.spec-key: table key outside MethodSpec array')
        if spec != selected_spec:
            continue
        if not 0 <= slot < pointer_count or not 0 <= invoker < invoker_count:
            raise ValueError('generic-call-projection.selected-index: pointer or invoker index outside declared array')
        pointer = struct.unpack_from('<Q', pointers, slot*8)[0]
        if not pointer:
            raise ValueError('generic-call-projection.pointer: selected canonical pointer is null')
        selected.append({'tableIndex':index,'methodSpecIndex':spec,'canonicalPointerSlot':slot,
            'canonicalPointerVa':pointer,'invokerIndex':invoker,
            'uninterpretedFourthWord':fourth,'recordHex':records[index*16:(index+1)*16].hex().upper(),
            'canonicalPointerHex':pointers[slot*8:(slot+1)*8].hex().upper()})
    if len(selected) != 1:
        raise ValueError(f'generic-call-projection.exact-row: expected=1,actual={len(selected)}')
    return {'status':'exact-selected-canonical-pointer-projection-validated',**selected[0],
            'adjustorTableExtentOrEntryProved':False,'completeGenericEntryProved':False,
            'runtimeMethodInfoOrReceiverLayoutProved':False}


def prove_context_receiver_call(raw: bytes, *, entry_va: int,
                                expected_usage_cell_va: int,
                                expected_callee_va: int,
                                allow_retained_rsi_read: bool = False) -> dict:
    """Check the complete context/receiver/CALL block and an opted-in RSI read.

    The optional qword read from RAX into RSI preserves RCX and RDX. Its source
    address and value remain separate conditions; no object field is named.
    """
    if (not isinstance(raw, bytes) or not 0 < len(raw) <= 32
            or type(allow_retained_rsi_read) is not bool
            or any(type(v) is not int or not 0 < v < 1<<64 for v in
                   (entry_va,expected_usage_cell_va,expected_callee_va))
            or entry_va+len(raw) >= 1<<64):
        raise ValueError('generic-call-projection.program: bounded original block and addresses required')
    if raw[:3] != b'\x48\x8b\x15':
        raise ValueError('generic-call-projection.context-register: complete RIP load into RDX required')
    cell = rip_qword_load_target(raw[:7],entry_va,source='generic call block')
    if cell != expected_usage_cell_va:
        raise ValueError('generic-call-projection.usage-cell: selected RIP target differs')
    decoded = decode_lea_address(raw,7,entry_va)
    if decoded is None:
        raise ValueError('generic-call-projection.receiver: complete receiver LEA required')
    row,end = decoded
    fact = row['addressOperation']
    if (fact['destination'] != 'rcx' or fact['destinationBits'] != 64
            or fact['base'] != 'rbx' or fact['index'] is not None or fact['ripRelative']
            or not 0 <= fact['displacement'] <= 1<<20):
        raise ValueError('generic-call-projection.receiver: full-width affine RBX receiver required')
    retained = None
    if allow_retained_rsi_read:
        if raw[end:end+3] != b'\x48\x8b\xb0' or len(raw) != end+12:
            raise ValueError('generic-call-projection.retained-read: exact qword RAX-to-RSI memory read required')
        displacement = struct.unpack_from('<i',raw,end+3)[0]
        if not 0 <= displacement <= 1<<20:
            raise ValueError('generic-call-projection.retained-read: bounded nonnegative memory displacement required')
        retained = {'baseRegister':'rax','destinationRegister':'rsi',
            'displacement':displacement,'bytes':8,'preservesCallArguments':['rcx','rdx'],
            'fieldOwnershipProved':False}
        end += 7
    if len(raw) != end+5 or raw[end] != 0xe8:
        raise ValueError('generic-call-projection.call: exact terminal direct CALL required')
    target = relative_branch_target(raw[end:],entry_va+end,source='generic call block')
    if target != expected_callee_va:
        raise ValueError('generic-call-projection.call-target: selected callee differs')
    return {'status':'complete-context-and-receiver-call-block-validated',
            'checkedProgramBytes':len(raw),'usageCellVa':cell,
            'contextArgumentRegister':'rdx','receiverArgumentRegister':'rcx',
            'receiverBaseRegister':'rbx','receiverDisplacement':fact['displacement'],
            'calleeVa':target,'explicitDataStores':0,'retainedRead':retained,
            'conditions':'Selected entry, valid nonwrapping RBX receiver, usage-cell read and any opted-in RAX memory range; register ownership, call frame and live MethodInfo resolution are separate obligations.',
            'runtimeMethodInfoOrReceiverLayoutProved':False,'calleeEffectsProved':False}
