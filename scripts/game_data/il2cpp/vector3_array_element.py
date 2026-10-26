"""Complete bounds/copy program for a caller-authenticated twelve-byte array.

The unsigned check uses the low index DWORD; addressing uses the whole R8.
Typed array identity and valid index/memory conditions belong to the caller.
This proves the observed count/payload coordinates, not the object header,
array allocation, Count interface dispatch or error-helper effects.
"""
from __future__ import annotations

import hashlib
from .context import relative_branch_target
from .integer_addressing import decode_lea_address


def prove_vector3_array_element(raw: bytes, *, entry_va: int, error_helper_va: int,
                               count_offset: int = 24, payload_offset: int = 32) -> dict:
    if (not isinstance(raw, bytes) or any(type(v) is not int or not 0<v<1<<64
            for v in (entry_va,error_helper_va)) or entry_va+len(raw)>=1<<64):
        raise ValueError('vector3-array-element.input: original bytes and bounded addresses required')
    if any(type(v) is not int or not 0<v<120 for v in (count_offset,payload_offset)):
        raise ValueError('vector3-array-element.field: positive byte offsets with complete payload required')
    rows=[];offset=0
    def literal(hexed, meaning):
        nonlocal offset
        expected=bytes.fromhex(hexed);actual=raw[offset:offset+len(expected)]
        if actual!=expected:
            raise ValueError(f'vector3-array-element.instruction: offset={offset} expected={hexed} actual={actual.hex().upper()}')
        rows.append({'offset':offset,'rawHex':hexed,'operation':meaning});offset+=len(expected)
    literal('4883EC28','allocate forty-byte call frame')
    literal('443B41'+f'{count_offset:02X}','unsigned comparison: r8d against array count DWORD')
    literal('731D','JAE to error call at offset 39')
    decoded=decode_lea_address(raw,offset,entry_va)
    if decoded is None:
        raise ValueError('vector3-array-element.index: complete affine index LEA required')
    row,end=decoded;fact=row['addressOperation']
    if (end!=offset+4 or fact['destination']!='rax' or fact['destinationBits']!=64
            or fact['base']!='r8' or fact['index']!='r8' or fact['scale']!=2
            or fact['displacement']!=0 or fact['ripRelative']):
        raise ValueError('vector3-array-element.index: full R8 plus twice full R8 required')
    rows.append({'offset':offset,'rawHex':raw[offset:end].hex().upper(),
        'operation':'rax = r8 + 2*r8, full-width modular addressing','decodedAddress':fact});offset=end
    literal('F20F104481'+f'{payload_offset:02X}','load first eight element bytes before any output store')
    literal('8B4481'+f'{payload_offset+8:02X}','load remaining four element bytes')
    literal('F20F1102','store first eight bytes through rdx')
    literal('894208','store remaining four bytes through rdx+8')
    literal('488BC2','return output pointer in rax')
    literal('4883C428','restore forty-byte call frame')
    literal('C3','normal return')
    call=raw[offset:offset+5]
    if len(call)!=5 or call[0]!=0xe8 or relative_branch_target(call,entry_va+offset,source='array bounds error')!=error_helper_va:
        raise ValueError('vector3-array-element.error-call: complete selected CALL required')
    rows.append({'offset':offset,'rawHex':call.hex().upper(),'operation':'call opaque bounds-error helper','targetVa':error_helper_va});offset+=5
    literal('CC','INT3 after error helper')
    if offset!=len(raw):
        raise ValueError(f'vector3-array-element.terminal: expectedBytes={offset} actualBytes={len(raw)}')
    return {'status':'complete-vector3-array-element-bounds-and-copy-program-proved',
        'programBytes':len(raw),'programSha256':hashlib.sha256(raw).hexdigest().upper(),'program':rows,
        'arrayRegister':'rcx','outputRegister':'rdx','indexRegister':'r8',
        'countOffset':count_offset,'countReadBits':32,'indexComparisonBits':32,
        'boundsComparisonUnsigned':True,'addressIndexBits':64,'elementStrideBytes':12,
        'elementPayloadOffset':payload_offset,'valueBytesCopied':12,'returnedOutputRegister':'rax',
        'allElementReadsBeforeOutputStores':True,
        'sourceAddressExpression':f'rcx+{payload_offset}+12*r8 (modulo 2^64)',
        'fullIndexBoundsProvedForArbitraryHighBits':False,'fullArrayHeaderOrAllocationProved':False,
        'errorHelperEffectsProved':False,'runtimeExecutionKnown':False,
        'conditions':['Current selected caller authenticates this complete helper and its typed array/input aliases',
            'Valid nonnull count/element memory and writable output/frame; no incompatible indirect writes',
            'For an in-array element interpretation, full R8 equals the nonnegative bounded index represented by its low DWORD and address arithmetic does not wrap'],
        'evidenceBoundary':'Full helper bytes, low-DWORD unsigned check, independently decoded extended SIB index, twelve-byte copy and normal return. Stored coordinates do not prove a complete object header, allocation, interface Count result or actual execution.'}
