"""Exact selected GP/SSE/VEX memory moves with default 64-bit addressing.

Transfer widths, REX/VEX register extensions, SIB indices, alignment and
upper-register effects are instruction facts. Valid memory, CPU support,
overlap, ordering and whole-copy coverage belong to a consumer proof.
"""
from __future__ import annotations
from typing import Any
from .integer_addressing import _address, _required, decode_address_integer_instructions

_GP = ('rax','rcx','rdx','rbx','rsp','rbp','rsi','rdi')
_GP32 = ('eax','ecx','edx','ebx','esp','ebp','esi','edi')
_GP16 = ('ax','cx','dx','bx','sp','bp','si','di')
_GP8 = ('al','cl','dl','bl','spl','bpl','sil','dil')


def _register(number, bits, has_rex):
    if bits == 8 and not has_rex and 4 <= number < 8:
        return ('ah','ch','dh','bh')[number-4], _GP[number-4], 8
    backing = _GP[number] if number < 8 else f'r{number}'
    names = {64:_GP,32:_GP32,16:_GP16,8:_GP8}[bits]
    name = names[number] if number < 8 else f'r{number}' + {64:'',32:'d',16:'w',8:'b'}[bits]
    return name, backing, 0


def _finish_address(address, end, start_va):
    if address['ripRelative']:
        address['ripBase'] = start_va + end
        address['absoluteAddress'] = address['ripBase'] + address['displacement']
        d = address['displacement']
        return f"rip{'+' if d >= 0 else '-'}0x{abs(d):x} => 0x{address['absoluteAddress']:x}"
    text = address['base'] or ''
    if address['index'] is not None:
        text += ('+' if text else '') + f"{address['index']}*{address['scale']}"
    d = address['displacement']
    if d or not text: text += ('+' if text and d >= 0 else '-' if d < 0 else '') + f'0x{abs(d):x}'
    return text


def decode_memory_move(data: bytes, offset: int, start_va: int) -> tuple[dict,int] | None:
    if not 0 <= offset < len(data): return None
    at = offset; prefix = None; rex = 0; vex = False; vector = False
    if data[at] in (0x66,0xf3): prefix = data[at]; at += 1
    if at < len(data) and 0x40 <= data[at] <= 0x4f: rex = data[at]; at += 1
    if prefix is None and rex == 0 and data[at:at+1] in (b'\xc4',b'\xc5'):
        vex = vector = True
        if data[at] == 0xc5:
            encoded = _required(data,at+1,1,offset,'memory-move-vex')[0]; at += 2
            rex = ((~encoded >> 7) & 1) << 2
        else:
            first,encoded = _required(data,at+1,2,offset,'memory-move-vex'); at += 3
            if first & 31 != 1: return None
            rex = (((~first >> 7)&1)<<2) | (((~first >> 6)&1)<<1) | ((~first >> 5)&1)
        if encoded & 3 not in (1,2): return None
        prefix = 0x66 if encoded & 3 == 1 else 0xf3
        vector_bits = 256 if encoded & 4 else 128
        if data[at:at+1] not in (b'\x6f',b'\x7f',b'\xe7'): return None
        if (encoded >> 3) & 15 != 15:
            raise ValueError(f'x64.memory-move-vex.reserved-vvvv: offset={offset}')
        opcode = data[at]; at += 1
    elif prefix in (0x66,0xf3) and data[at:at+2] in (b'\x0f\x6f',b'\x0f\x7f',b'\x0f\xe7'):
        vector = True; vector_bits = 128; opcode = data[at+1]; at += 2
    else:
        if prefix == 0xf3: return None
        extension = None
        if data[at:at+2] in (b'\x0f\xb6',b'\x0f\xb7'):
            opcode = data[at+1]; extension = 'zero'; at += 2
        elif data[at:at+1] in (b'\x8a',b'\x88',b'\x8b',b'\x89'):
            opcode = data[at]; at += 1
        else: return None
        register_bits = 64 if rex & 8 else 16 if prefix == 0x66 else 32
        if opcode == 0xb7 and register_bits == 16: return None
        if opcode in (0x8a,0x88): register_bits = memory_bits = 8
        else: memory_bits = 8 if opcode == 0xb6 else 16 if opcode == 0xb7 else register_bits
    modrm = _required(data,at,1,offset,'memory-move')[0]; at += 1
    if modrm >> 6 == 3: return None
    number = ((modrm >> 3)&7) | ((rex & 4)<<1)
    address,end = _address(data,at,modrm,rex,offset,'memory-move')
    address_text = _finish_address(address,end,start_va)
    if vector:
        if opcode == 0xe7 and prefix != 0x66: return None
        load = opcode == 0x6f; register_bits = memory_bits = vector_bits
        register = ('ymm' if vector_bits == 256 else 'xmm') + str(number)
        backing = 'vector' + str(number); bit_offset = 0
        mnemonic = ('v' if vex else '') + ('movntdq' if opcode == 0xe7 else 'movdqa' if prefix == 0x66 else 'movdqu')
        upper = 'zero bits above transfer width up to maximum architectural vector width' if load and vex else 'preserved'
        extension = None; alignment = memory_bits//8 if prefix == 0x66 else 1
    else:
        load = opcode in (0x8a,0x8b,0xb6,0xb7)
        register,backing,bit_offset = _register(number,register_bits,bool(rex))
        mnemonic = 'movzx' if extension else 'mov'; alignment = 1
        upper = 'zero upper 32 bits' if load and register_bits == 32 else 'replaced full register' if load and register_bits == 64 else 'preserved'
    operation = {'direction':'load' if load else 'store','register':register,'backingRegister':backing,
        'registerBits':register_bits,'registerBitOffset':bit_offset,'memoryBytes':memory_bits//8,
        'address':address,'valueExtension':extension,'upperRegisterEffect':upper,
        'requiredAlignmentBytes':alignment,'nonTemporalHint':vector and opcode==0xe7,'writesFlags':False}
    operands = f'{register}, [{address_text}]' if load else f'[{address_text}], {register}'
    return {'offset':offset,'va':hex(start_va+offset),'bytes':data[offset:end].hex(' '),
        'text':f'{mnemonic} {operands}',
        'write':{'register':register,'value':'loaded memory bytes'} if load else None,
        'memoryOperation':operation},end


def decode_copy_padding(data: bytes, offset: int, start_va: int) -> tuple[dict,int] | None:
    if not 0 <= offset < len(data): return None
    at = offset
    while data[at:at+1] == b'\x66' and at-offset < 15: at += 1
    rex = 0
    if at < len(data) and 0x40 <= data[at] <= 0x4f: rex = data[at]; at += 1
    if data[at:at+2] != b'\x0f\x1f': return None
    at += 2; modrm = _required(data,at,1,offset,'copy-padding')[0]; at += 1
    if (modrm>>3)&7: return None
    if modrm>>6 != 3: _,at = _address(data,at,modrm,rex,offset,'copy-padding')
    if at-offset > 15: raise ValueError(f'x64.copy-padding.overlong: offset={offset} bytes={at-offset}')
    return {'offset':offset,'va':hex(start_va+offset),'bytes':data[offset:at].hex(' '),
        'text':'nop','write':None,'paddingOperation':{'readsMemory':False,'writesFlags':False}},at


def decode_memory_move_instructions(mapper: Any, data: bytes, start_va: int) -> list[dict]:
    class Fallback:
        def decode_one_x64(self,raw,offset,at):
            for decoder in (decode_memory_move,decode_copy_padding):
                result = decoder(raw,offset,at)
                if result is not None: return result
            if raw[offset:offset+3] == b'\xc5\xf8\x77':
                end=offset+3
                return {'offset':offset,'va':hex(at+offset),'bytes':raw[offset:end].hex(' '),
                    'text':'vzeroupper','write':None,
                    'vectorStateOperation':{'registerNumbers':list(range(16)),'preservesLow128Bits':True,
                        'zerosBits128Through255':True,'higherBitsAbove255Proved':False,
                        'writesMemory':False,'writesFlags':False}},end
            return mapper.decode_one_x64(raw,offset,at)
    return decode_address_integer_instructions(Fallback(),data,start_va)
