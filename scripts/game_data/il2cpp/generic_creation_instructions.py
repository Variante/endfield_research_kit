"""Optional memory logical forms and implicitly locked XCHG for creation.

The memory form of XCHG overwrites both operands, even without LOCK. Its
instruction facts prove neither a successful cache publication nor a later
load's equality with the value written. Existing readers remain unchanged.
"""
from __future__ import annotations
from .integer_addressing import _address,_prefix,_reg,_required
from .integer_tag_dispatch import _row,_memory_text
from .class_creation_instructions import decode_class_creation_instructions


def _memory_operand(data,offset,start_va,opcode,label):
    if not 0<=offset<len(data):return None
    at,rex=_prefix(data,offset)
    if data[at:at+1]!=bytes((opcode,)):return None
    at+=1;modrm=_required(data,at,1,offset,label)[0];at+=1
    if modrm>>6==3:return None
    address,at=_address(data,at,modrm,rex,offset,label)
    bits=64 if rex&8 else 32
    register=_reg(((modrm>>3)&7)|((rex&4)<<1),bits)
    operand=_memory_text(address,at,start_va,bits)
    return at,bits,register,address,operand


def decode_memory_source_xor(data,offset,start_va):
    result=_memory_operand(data,offset,start_va,0x33,'memory-source-xor')
    if result is None:return None
    at,bits,register,address,operand=result
    return _row(data,offset,at,start_va,f'xor {register}, {operand}',
        write={'register':register,'value':f'previous register XOR memory modulo 2^{bits}'},
        memoryXorOperation={'destinationRegister':register,'bits':bits,'sourceAddress':address,
            'memoryReadBytes':bits//8,'memoryWriteBytes':0,'zeroExtendsTo64':bits==32,
            'clearsFlags':['CF','OF'],'undefinedFlags':['AF'],'writesResultFlags':['SF','ZF','PF']})


def decode_implicit_memory_exchange(data,offset,start_va):
    result=_memory_operand(data,offset,start_va,0x87,'implicit-memory-exchange')
    if result is None:return None
    at,bits,register,address,operand=result
    return _row(data,offset,at,start_va,f'xchg {operand}, {register}',
        write={'register':register,'value':f'previous memory value; '+('zero upper 32 bits' if bits==32 else 'full register')},
        implicitMemoryExchangeOperation={'register':register,'bits':bits,'address':address,
            'memoryReadBytes':bits//8,'memoryWriteBytes':bits//8,'implicitlyLocked':True,
            'memoryResult':'previous register value','registerResult':'previous memory value',
            'registerPreserved':False,'zeroExtendsTo64':bits==32,'writesFlags':False})


def decode_memory_immediate_or(data,offset,start_va):
    if not 0<=offset<len(data):return None
    at,rex=_prefix(data,offset)
    if rex&4 or data[at:at+1]!=b'\x81':return None
    at+=1;modrm=_required(data,at,1,offset,'memory-immediate-or')[0];at+=1
    if modrm>>6==3 or (modrm>>3)&7!=1:return None
    address,at=_address(data,at,modrm,rex,offset,'memory-immediate-or')
    encoded=int.from_bytes(_required(data,at,4,offset,'memory-immediate-or'),'little');at+=4
    bits=64 if rex&8 else 32
    value=(encoded if encoded<1<<31 else encoded-(1<<32))&((1<<bits)-1)
    operand=_memory_text(address,at,start_va,bits)
    return _row(data,offset,at,start_va,f'or {operand}, {hex(value)}',
        memoryImmediateOrOperation={'bits':bits,'destinationAddress':address,'encodedImmediate':encoded,
            'effectiveImmediate':value,'immediateSignExtendedTo64':bits==64,
            'memoryReadBytes':bits//8,'memoryWriteBytes':bits//8,'preservesRegisters':True,
            'clearsFlags':['CF','OF'],'undefinedFlags':['AF'],'writesResultFlags':['SF','ZF','PF']})


def decode_generic_creation_instructions(mapper,data,start_va):
    class Fallback:
        def decode_one_x64(self,raw,offset,at):
            for decoder in (decode_memory_source_xor,decode_implicit_memory_exchange,decode_memory_immediate_or):
                result=decoder(raw,offset,at)
                if result is not None:return result
            return mapper.decode_one_x64(raw,offset,at)
    return decode_class_creation_instructions(Fallback(),data,start_va)
