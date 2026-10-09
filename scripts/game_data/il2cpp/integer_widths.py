"""Selected x64 integer widths that the legacy display does not preserve.

Own complete accumulator extension, word MOVZX/CMP/INC and register-byte XOR
encodings. Unsupported prefix/address forms remain outside this subset.
"""
from __future__ import annotations
from typing import Any
from scripts.game_data.il2cpp.integer_addressing import _address, _prefix, _reg, _required
from scripts.game_data.il2cpp.signed_division import decode_signed_integer_instructions

_WORD = ('ax','cx','dx','bx','sp','bp','si','di')
_BYTE = ('al','cl','dl','bl','ah','ch','dh','bh')
_REX_BYTE = ('al','cl','dl','bl','spl','bpl','sil','dil')


def _word(number): return _WORD[number] if number < 8 else f'r{number}w'
def _byte(number, rex): return (_REX_BYTE if rex else _BYTE)[number] if number < 8 else f'r{number}b'
def _row(data, offset, stop, start_va, text, **facts):
    return {'offset':offset,'va':hex(start_va+offset),'bytes':data[offset:stop].hex(' '),'text':text,**facts},stop


def decode_accumulator_extension(data: bytes, offset: int, start_va: int):
    if not 0 <= offset < len(data): return None
    at=offset; word=data[at]==0x66
    if word: at+=1
    at,rex=_prefix(data,at)
    if data[at:at+1]!=b'\x98': return None
    at+=1; bits=64 if rex&8 else 16 if word else 32
    source={16:'al',32:'ax',64:'eax'}[bits];destination={16:'ax',32:'eax',64:'rax'}[bits]
    return _row(data,offset,at,start_va,{16:'cbw',32:'cwde',64:'cdqe'}[bits],
        write={'register':destination,'value':f'sign_extend_{bits}({source})'},
        accumulatorExtensionOperation={'sourceRegister':source,'destinationRegister':destination,
            'sourceBits':bits//2,'destinationBits':bits,'writesFlags':False,
            'preservesBitsAboveDestination':bits==16,'zeroExtendsDestinationTo64':bits==32})


def decode_word_zero_extension(data: bytes, offset: int, start_va: int):
    if not 0 <= offset < len(data): return None
    at,rex=_prefix(data,offset)
    if data[at:at+2]!=b'\x0f\xb7': return None
    at+=2;modrm=_required(data,at,1,offset,'word-zero-extension')[0];at+=1
    bits=64 if rex&8 else 32;destination=_reg(((modrm>>3)&7)|((rex&4)<<1),bits)
    address=None;source=None
    if modrm>>6==3:
        source=_word((modrm&7)|((rex&1)<<3));operand=source
    else:
        address,at=_address(data,at,modrm,rex,offset,'word-zero-extension')
        if address['ripRelative']:
            address.update(ripBase=start_va+at,absoluteAddress=start_va+at+address['displacement'])
            term=f'rip => {hex(address["absoluteAddress"])}'
        else:
            term=address['base'] or ''
            if address['index'] is not None: term+=('+' if term else '')+f'{address["index"]}*{address["scale"]}'
            displacement=address['displacement']
            if displacement or not term: term+=('+' if term and displacement>=0 else '-' if displacement<0 else '')+hex(abs(displacement))
        operand=f'word [{term}]'
    return _row(data,offset,at,start_va,f'movzx {destination}, {operand}',
        write={'register':destination,'value':'zero extend unsigned 16-bit source'},
        wordZeroExtensionOperation={'destinationRegister':destination,'destinationBits':bits,'sourceRegister':source,
            'sourceAddress':address,'sourceBits':16,'memoryReadBytes':2 if address else 0,
            'zeroExtendsDestinationTo64':bits==32,'writesFlags':False})


def decode_word_compare_registers(data: bytes, offset: int, start_va: int):
    if not 0 <= offset < len(data) or data[offset]!=0x66: return None
    at,rex=_prefix(data,offset+1)
    if rex&8 or data[at:at+1] not in (b'\x39',b'\x3b'): return None
    opcode=data[at];at+=1;modrm=_required(data,at,1,offset,'word-compare')[0];at+=1
    if modrm>>6!=3: return None
    register=_word(((modrm>>3)&7)|((rex&4)<<1));operand=_word((modrm&7)|((rex&1)<<3))
    left,right=(register,operand) if opcode==0x3b else (operand,register)
    return _row(data,offset,at,start_va,f'cmp {left}, {right}',write=None,
        wordComparisonOperation={'bits':16,'leftRegister':left,'rightRegister':right,'preservesRegisters':True,
            'flags':'16-bit left-minus-right: CF unsigned borrow; ZF equality; OF signed overflow; SF bit15; AF borrow bit4; PF low-byte parity'})


def decode_word_increment_register(data: bytes, offset: int, start_va: int):
    if not 0 <= offset < len(data) or data[offset]!=0x66: return None
    at,rex=_prefix(data,offset+1)
    if rex&0x0c or data[at:at+1]!=b'\xff': return None
    at+=1;modrm=_required(data,at,1,offset,'word-increment')[0];at+=1
    if modrm>>6!=3 or (modrm>>3)&7: return None
    register=_word((modrm&7)|((rex&1)<<3))
    return _row(data,offset,at,start_va,f'inc {register}',
        write={'register':register,'value':'previous low word plus 1 modulo 2^16; preserve upper register bits'},
        wordIncrementOperation={'register':register,'bits':16,'wrapsModulo':65536,
            'preservesBitsAboveDestination':True,'preservesCarryFlag':True,
            'writesFlags':['OF','SF','ZF','AF','PF']})


def decode_byte_register_xor(data: bytes, offset: int, start_va: int):
    if not 0 <= offset < len(data): return None
    at,rex=_prefix(data,offset)
    if data[at:at+1] not in (b'\x30',b'\x32'): return None
    opcode=data[at];at+=1;modrm=_required(data,at,1,offset,'byte-register-xor')[0];at+=1
    if modrm>>6!=3: return None
    register=_byte(((modrm>>3)&7)|((rex&4)<<1),rex);operand=_byte((modrm&7)|((rex&1)<<3),rex)
    destination,source=(register,operand) if opcode==0x32 else (operand,register)
    low_bit=8 if destination in ('ah','ch','dh','bh') else 0
    return _row(data,offset,at,start_va,f'xor {destination}, {source}',
        write={'register':destination,'value':f'previous({destination}) XOR {source}; preserve other register bits'},
        byteXorOperation={'destinationRegister':destination,'sourceRegister':source,'bits':8,
            'destinationLowBit':low_bit,'preservesBitsOutsideDestination':True,'zeroExtendsTo64':False,
            'resultZeroWhenSameRegister':destination==source,'clearsFlags':['CF','OF'],
            'resultFlags':['SF','ZF','PF'],'undefinedFlags':['AF']})


def decode_width_aware_integer_instructions(mapper: Any, data: bytes, start_va: int) -> list[dict]:
    class Fallback:
        def decode_one_x64(self, raw, offset, at):
            for decoder in (decode_accumulator_extension,decode_word_zero_extension,decode_word_compare_registers,
                            decode_word_increment_register,decode_byte_register_xor):
                result=decoder(raw,offset,at)
                if result is not None: return result
            return mapper.decode_one_x64(raw,offset,at)
    return decode_signed_integer_instructions(Fallback(),data,start_va)
