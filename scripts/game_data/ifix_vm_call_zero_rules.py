"""Prove the Call builder's forty-byte zero fill on its bounded native routes.

The wrapper forwards destination/count with fill byte zero. For this fixed
count the target bypasses scalar and large loops. Its SSE, AVX and repeat
routes all cover exactly the requested interval for every alignment. This
requires valid storage, no address wrap, ordinary clear direction flag and
normal supported instruction execution. CPU selection and execution are not
observed. The call opcode group continues to own the caller and copy order.
"""
from __future__ import annotations

import struct
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import NativeImage
from scripts.game_data.ifix_vm_reference_address_rules import _ref, _rva, _hash, _expect


class CallZeroRuleError(ValueError):
    """A bounded fill declaration lacks its native witness."""


def _need(ok: bool, detail: str) -> None:
    if not ok: raise CallZeroRuleError('call-zero.' + detail)


def validate_call_zero_rules(image: Any, spec: dict, contract: dict) -> dict:
    """Authenticate inside the parent's gated image, without executing it."""
    _need(all(type(spec.get(k)) is type(v) and spec.get(k)==v for k,v in _CLAIMS.items()), 'unsupported declaration')
    wrapper=_ref(contract,spec['wrapperRef']);at=_rva(wrapper['rva']);raw=image.pe.bytes_at_va(image.pe.image_base+at,wrapper['byteCount']);_hash(raw,wrapper,'zero wrapper')
    target=_rva(spec['target']['rva']);_need(target==_rva(contract['callOpcodeRules']['zeroMemoryTarget']), 'inherited target differs')
    _expect(raw,bytes.fromhex('4c8bc233d2e9')+(target-at-10).to_bytes(4,'little',signed=True),'zero wrapper')
    row=spec['target'];_need(type(row['bodyBytes'])is int and row['bodyBytes']==904,'target extent differs')
    body=image.pe.bytes_at_va(image.pe.image_base+target,row['bodyBytes']);_hash(body,row,'bounded fill',method=True)
    def block(offset,hex_bytes):
        expected=bytes.fromhex(hex_bytes);_expect(body[offset:offset+len(expected)],expected,'fill block '+hex(offset))
    def branch(offset,prefix,wanted):
        opcode=bytes.fromhex(prefix);_expect(body[offset:offset+len(opcode)],opcode,'fill branch')
        actual=target+offset+len(opcode)+4+struct.unpack_from('<i',body,offset+len(opcode))[0]
        _need(actual==wanted,'fill branch target differs')
    block(0,'488bc14c8bc94c8d15');_need(target+13+struct.unpack_from('<i',body,9)[0]==0,'image-base carrier differs')
    block(0xd,'0fb6d249bb01010101010101014c0fafda66490f6ec34983f80f0f87830000000f1f00')
    block(0xb0,'660f6cc04983f820770cf30f7f01f3420f7f4401f0c3833d')
    _need(body[0xcc]==3,'CPU comparison immediate differs');branch(0xcd,'0f82',target+0x2b0)
    block(0xd3,'4c3b05');block(0xda,'76164c3b05');block(0xe3,'770df605');_need(body[0xeb]==2,'AVX repeat mask differs')
    repeat=spec['repeat'];repeat_at=_rva(repeat['rva']);_need(type(repeat['bodyBytes'])is int and repeat['bodyBytes']==16,'repeat extent differs');branch(0xec,'0f85',repeat_at)
    repeated=image.pe.bytes_at_va(image.pe.image_base+repeat_at,16);_hash(repeated,repeat,'repeat',method=True);_expect(repeated,bytes.fromhex('578bc2488bf9498bc8f3aa498bc15fc3'),'repeat program')
    block(0xf2,'c4e37d18c0014c8bc94983e11f4983e920492bc9492bd14d03c14981f8000100007665')
    block(0x17a,'4d8d481f4983e1e04d8bd949c1eb05');block(0x191,'4d03da41ffe3')
    block(0x2b0,'4c3b05');block(0x2b7,'760df605');_need(body[0x2bf]==2,'SSE repeat mask differs');branch(0x2c0,'0f85',repeat_at)
    block(0x2c6,'4c8bc94983e10f4983e910492bc9492bd14d03c14981f880000000764b')
    block(0x32e,'4d8d480f4983e1f04d8bd949c1eb04');block(0x345,'4d03da41ffe3')
    _need(set(spec['tables'])=={'sse','avx'},'table set differs')
    for name,width,reference,prefix,first,tail,end_prefix,base_prefix,terminal in (
        ('sse',16,0x33d,'478b9c9a',0x34b,0x37c,'f3420f7f4401f0','f30f7f00','c3'),
        ('avx',32,0x189,'478b9c9a',0x197,0x1d4,'c4a17e7f4401e0','c5fe7f00','c5f877c3'),
    ):
        table=spec['tables'][name];_need(type(table['referenceBodyOffset'])is int and table['referenceBodyOffset']==reference,'table reference differs');block(reference,prefix)
        address=struct.unpack_from('<I',body,reference+4)[0];_need(address==_rva(table['rva']),'table address differs')
        entries=table['entryOffsets'];_need(isinstance(entries,list) and len(entries)==9 and all(type(x)is int for x in entries),'table entries differ')
        actual=list(struct.unpack('<9I',image.pe.bytes_at_va(image.pe.image_base+address,36)));_need(actual==[target+x for x in entries],'stored table differs')
        position=first;expected=[tail+len(bytes.fromhex(end_prefix)),tail]
        for distance in range(8*width,2*width-1,-width):
            expected.append(position)
            if name=='sse':encoded='f3420f7f4409'+struct.pack('<b',-distance).hex()
            elif distance>=160:encoded='c4a17e7f8409'+struct.pack('<i',-distance).hex()
            else:encoded='c4a17e7f4409'+struct.pack('<b',-distance).hex()
            block(position,encoded);position+=len(bytes.fromhex(encoded))
        _need(position==tail and entries==[expected[0],expected[1],*reversed(expected[2:])],'table tail partition differs')
        block(tail,end_prefix+base_prefix+terminal)
        for alignment in range(width):
            position=width-alignment;remaining=40-position;blocks=(remaining+width-1)//width
            _need(0<remaining<=128 and 0<blocks<len(entries),'fixed length could enter unsupported loop')
            intervals=[(0,width),(40-width,40)]+[(position+n*width,position+(n+1)*width)for n in range(blocks-1)]
            _need(all(0<=lo<=hi<=40 for lo,hi in intervals),'write outside requested forty bytes')
            covered=set().union(*(set(range(lo,hi))for lo,hi in intervals));_need(covered==set(range(40)),'incomplete forty-byte coverage')
    return dict(status='validated_conditional_call_zero_fill',evidenceBoundary='conditional',executionBoundary='unobserved',
                byteCount=40,fillByte=0,alignmentCases=48,normalFifthCallWord='zero-before-explicit-four-field-stores-and-five-word-copy',
                storageBoundary=spec['storageBoundary'],callerBoundary=spec['callerBoundary'],runtimeRoute='unobserved')


def validate_selected_call_zero_rules(contract: dict, *, gameassembly: Path|None, metadata: Path|None, spec: dict|None=None) -> dict:
    if gameassembly is None or metadata is None:return dict(status='missing',detail='explicit native paths required')
    n=contract['nativeInputs'];_need(bool(n.get('gameAssemblySha256'))and bool(n.get('globalMetadataSha256')),'native hashes required')
    gate=check_installed_native_inputs(n['gameAssemblySha256'],n['globalMetadataSha256'],gameassembly=Path(gameassembly),metadata=Path(metadata))
    if gate.status!='validated':return dict(status=gate.status,detail=gate.detail)
    image=NativeImage(gate.gameassembly,gate.metadata,label='ifix.call-zero')
    return validate_call_zero_rules(image,contract['callZeroRules']if spec is None else spec,contract)


_CLAIMS=dict(schema='endfield.ifix-vm-call-zero-rules.v1',evidenceBoundary='conditional',executionBoundary='unobserved',
    wrapperRef='callOpcodeRules.helpers.zeroMemory',byteCount=40,fillByte=0,
    storageBoundary='valid-forty-byte-destination-and-global-reads;no-address-wrap;clear-direction-flag;normal-supported-SSE-AVX-repeat-execution',
    callerBoundary='callOpcodeRules-owns-forty-byte-request-before-four-explicit-stores-and-five-word-copy;helper-mutation-after-return-unobserved')
