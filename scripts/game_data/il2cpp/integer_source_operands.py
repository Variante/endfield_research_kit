"""Selected complete ADD/AND, IMUL-immediate and byte-memory TEST operands.

Preserve original spans, memory read widths and immediate sign extension.
These instruction facts do not identify native class fields or helper meaning.
"""
from __future__ import annotations
from typing import Any
from scripts.game_data.il2cpp.integer_addressing import _address, _prefix, _reg, _required
from scripts.game_data.il2cpp.integer_widths import decode_width_aware_integer_instructions


def is_unknown_instruction(row: dict) -> bool:
    """A hex address containing 'db' is not an unknown-instruction directive."""
    return row['text'].lstrip().startswith('db ')


def _operand(data, at, modrm, rex, offset, label, bits):
    if modrm >> 6 == 3:
        return {'register':_reg((modrm&7)|((rex&1)<<3),bits),'address':None},at
    address,at=_address(data,at,modrm,rex,offset,label)
    return {'register':None,'address':address},at


def _operand_text(source, stop, start_va, bits):
    if source['register'] is not None: return source['register']
    address=source['address']
    if address['ripRelative']:
        address.update(ripBase=start_va+stop,absoluteAddress=start_va+stop+address['displacement'])
        term=f'rip => {hex(address["absoluteAddress"])}'
    else:
        term=address['base'] or ''
        if address['index'] is not None: term+=('+' if term else '')+f'{address["index"]}*{address["scale"]}'
        displacement=address['displacement']
        if displacement or not term: term+=('+' if term and displacement>=0 else '-' if displacement<0 else '')+hex(abs(displacement))
    return f'{ {8:"byte",32:"dword",64:"qword"}[bits]} [{term}]'


def _row(data, offset, stop, start_va, text, **facts):
    return {'offset':offset,'va':hex(start_va+offset),'bytes':data[offset:stop].hex(' '),'text':text,**facts},stop


def decode_source_register_arithmetic(data: bytes, offset: int, start_va: int):
    if not 0<=offset<len(data): return None
    at,rex=_prefix(data,offset)
    operation={b'\x03':'add',b'\x23':'and'}.get(data[at:at+1])
    if operation is None: return None
    at+=1;modrm=_required(data,at,1,offset,'source-register-arithmetic')[0];at+=1
    bits=64 if rex&8 else 32;destination=_reg(((modrm>>3)&7)|((rex&4)<<1),bits)
    source,at=_operand(data,at,modrm,rex,offset,'source-register-arithmetic',bits)
    operand=_operand_text(source,at,start_va,bits)
    flags={'writesFlags':['CF','OF','SF','ZF','AF','PF']} if operation=='add' else {
        'clearsFlags':['CF','OF'],'resultFlags':['SF','ZF','PF'],'undefinedFlags':['AF']}
    return _row(data,offset,at,start_va,f'{operation} {destination}, {operand}',
        write={'register':destination,'value':f'previous destination {operation} source, low {bits} bits'},
        sourceArithmeticOperation={'operation':operation,'destinationRegister':destination,
            'sourceRegister':source['register'],'sourceAddress':source['address'],'bits':bits,
            'memoryReadBytes':bits//8 if source['address'] else 0,'writesMemory':False,
            'zeroExtendsTo64':bits==32,'wrapsModulo':1<<bits,**flags})


def decode_immediate_multiply(data: bytes, offset: int, start_va: int):
    if not 0<=offset<len(data): return None
    at,rex=_prefix(data,offset)
    if data[at:at+1] not in (b'\x69',b'\x6b'): return None
    opcode=data[at];at+=1;modrm=_required(data,at,1,offset,'immediate-multiply')[0];at+=1
    bits=64 if rex&8 else 32;destination=_reg(((modrm>>3)&7)|((rex&4)<<1),bits)
    source,at=_operand(data,at,modrm,rex,offset,'immediate-multiply',bits)
    size=1 if opcode==0x6b else 4
    immediate=int.from_bytes(_required(data,at,size,offset,'immediate-multiply'),'little',signed=True);at+=size
    operand=_operand_text(source,at,start_va,bits)
    return _row(data,offset,at,start_va,f'imul {destination}, {operand}, {hex(immediate)}',
        write={'register':destination,'value':f'low {bits} bits of signed source times sign-extended immediate'},
        immediateMultiplyOperation={'destinationRegister':destination,'sourceRegister':source['register'],
            'sourceAddress':source['address'],'bits':bits,'memoryReadBytes':bits//8 if source['address'] else 0,
            'encodedImmediateBits':size*8,'immediateSignedValue':immediate,
            'immediateWord':immediate&((1<<bits)-1),'zeroExtendsTo64':bits==32,'writesMemory':False,
            'overflowFlags':['CF','OF'],'overflowCondition':'full signed product differs from sign extension of the truncated result',
            'undefinedFlags':['SF','ZF','AF','PF']})


def decode_byte_memory_test(data: bytes, offset: int, start_va: int):
    if not 0<=offset<len(data): return None
    at,rex=_prefix(data,offset)
    if data[at:at+1]!=b'\xf6': return None
    at+=1;modrm=_required(data,at,1,offset,'byte-memory-test')[0];at+=1
    if modrm>>6==3 or (modrm>>3)&7: return None
    source,at=_operand(data,at,modrm,rex,offset,'byte-memory-test',8)
    immediate=_required(data,at,1,offset,'byte-memory-test')[0];at+=1
    operand=_operand_text(source,at,start_va,8)
    return _row(data,offset,at,start_va,f'test {operand}, {hex(immediate)}',write=None,
        byteMemoryTestOperation={'sourceAddress':source['address'],'bits':8,'memoryReadBytes':1,
            'immediateWord':immediate,'writesMemory':False,'preservesRegisters':True,
            'zeroFlagCondition':'(stored byte AND immediate byte) equals zero',
            'clearsFlags':['CF','OF'],'resultFlags':['SF','ZF','PF'],'undefinedFlags':['AF']})


def decode_al_immediate_test(data: bytes, offset: int, start_va: int):
    if not 0<=offset<len(data): return None
    at,_=_prefix(data,offset)
    if data[at:at+1]!=b'\xa8': return None
    at+=1;immediate=_required(data,at,1,offset,'al-immediate-test')[0];at+=1
    return _row(data,offset,at,start_va,f'test al, {hex(immediate)}',write=None,
        alImmediateTestOperation={'sourceRegister':'al','bits':8,'immediateWord':immediate,
            'preservesRegisters':True,'zeroFlagCondition':'(AL AND immediate byte) equals zero',
            'clearsFlags':['CF','OF'],'resultFlags':['SF','ZF','PF'],'undefinedFlags':['AF']})


def decode_byte_memory_zero_extension(data: bytes, offset: int, start_va: int):
    if not 0<=offset<len(data): return None
    at,rex=_prefix(data,offset)
    if data[at:at+2]!=b'\x0f\xb6': return None
    at+=2;modrm=_required(data,at,1,offset,'byte-memory-zero-extension')[0];at+=1
    if modrm>>6==3: return None
    bits=64 if rex&8 else 32;destination=_reg(((modrm>>3)&7)|((rex&4)<<1),bits)
    source,at=_operand(data,at,modrm,rex,offset,'byte-memory-zero-extension',8)
    operand=_operand_text(source,at,start_va,8)
    return _row(data,offset,at,start_va,f'movzx {destination}, {operand}',
        write={'register':destination,'value':'zero extension of stored unsigned byte'},
        byteMemoryZeroExtensionOperation={'destinationRegister':destination,'destinationBits':bits,
            'sourceAddress':source['address'],'sourceBits':8,'memoryReadBytes':1,
            'zeroExtendsTo64':bits==32,'writesMemory':False,'writesFlags':False})


def decode_source_operand_integer_instructions(mapper: Any, data: bytes, start_va: int) -> list[dict]:
    class Fallback:
        def decode_one_x64(self, raw, offset, at):
            for decoder in (decode_source_register_arithmetic,decode_immediate_multiply,decode_byte_memory_test,
                            decode_al_immediate_test,decode_byte_memory_zero_extension):
                result=decoder(raw,offset,at)
                if result is not None: return result
            return mapper.decode_one_x64(raw,offset,at)
    return decode_width_aware_integer_instructions(Fallback(),data,start_va)
