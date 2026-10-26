"""Optional register bit-set and byte arithmetic for class creation bodies.

Physical widths and partial writes establish no class or metadata identity.
The previous field-setup and frozen storage readers remain unchanged.
"""
from __future__ import annotations
from .integer_addressing import _prefix,_reg,_required
from .integer_byte_operations import _destination
from .integer_widths import _byte
from .integer_tag_dispatch import _row
from .field_setup_instructions import decode_field_setup_instructions


def decode_register_bit_set(data,offset,start_va):
    if not 0<=offset<len(data):return None
    at,rex=_prefix(data,offset)
    if rex&4 or data[at:at+2]!=b'\x0f\xba':return None
    at+=2;modrm=_required(data,at,1,offset,'register-bit-set')[0];at+=1
    if modrm>>6!=3 or (modrm>>3)&7!=5:return None
    bit=_required(data,at,1,offset,'register-bit-set')[0];at+=1
    bits=64 if rex&8 else 32;register=_reg((modrm&7)|((rex&1)<<3),bits)
    return _row(data,offset,at,start_va,f'bts {register}, {hex(bit)}',
        write={'register':register,'value':'set selected bit in previous operand'},
        registerBitSetOperation={'register':register,'bits':bits,'encodedBitIndex':bit,'effectiveBitIndex':bit&(bits-1),
            'preservesOtherBitsWithinOperandWidth':True,'zeroExtendsTo64':bits==32,
            'memoryReadBytes':0,'memoryWriteBytes':0,'writesCarryFlagFromPreviousSelectedBit':True,'otherFlagsProved':False})


def decode_byte_left_shift(data,offset,start_va):
    if not 0<=offset<len(data):return None
    at,rex=_prefix(data,offset)
    if rex&4 or data[at:at+1]!=b'\xc0':return None
    at+=1;modrm=_required(data,at,1,offset,'byte-left-shift')[0];at+=1
    if modrm>>6!=3 or (modrm>>3)&7!=4:return None
    count=_required(data,at,1,offset,'byte-left-shift')[0];at+=1
    facts=_destination((modrm&7)|((rex&1)<<3),rex)
    facts.update(operation='shl',encodedCount=count,effectiveCount=count&31,countMask=31,
        result='previous byte shifted left by effective count modulo 256',flagsProved=False)
    return _row(data,offset,at,start_va,f'shl {facts["destinationRegister"]}, {hex(count)}',
        write={'register':facts['destinationRegister'],'value':'logical left shift of previous byte'},byteLeftShiftOperation=facts)


def decode_byte_not(data,offset,start_va):
    if not 0<=offset<len(data):return None
    at,rex=_prefix(data,offset)
    if rex&4 or data[at:at+1]!=b'\xf6':return None
    at+=1;modrm=_required(data,at,1,offset,'byte-not')[0];at+=1
    if modrm>>6!=3 or (modrm>>3)&7!=2:return None
    facts=_destination((modrm&7)|((rex&1)<<3),rex)
    facts.update(operation='not',result='previous byte XOR 255',writesFlags=False)
    return _row(data,offset,at,start_va,f'not {facts["destinationRegister"]}',
        write={'register':facts['destinationRegister'],'value':'bitwise complement of previous byte'},byteNotOperation=facts)


def decode_byte_register_add(data,offset,start_va):
    if not 0<=offset<len(data):return None
    at,rex=_prefix(data,offset)
    if data[at:at+1]!=b'\x02':return None
    at+=1;modrm=_required(data,at,1,offset,'byte-register-add')[0];at+=1
    if modrm>>6!=3:return None
    facts=_destination(((modrm>>3)&7)|((rex&4)<<1),rex)
    source=_byte((modrm&7)|((rex&1)<<3),rex)
    facts.update(operation='add',sourceRegister=source,sourceRegisterPreserved=source!=facts['destinationRegister'],
        result='previous destination byte plus source byte modulo 256',writesFlags=['CF','OF','SF','ZF','AF','PF'])
    return _row(data,offset,at,start_va,f'add {facts["destinationRegister"]}, {source}',
        write={'register':facts['destinationRegister'],'value':'byte sum'},byteRegisterAddOperation=facts)


def decode_class_creation_instructions(mapper,data,start_va):
    class Fallback:
        def decode_one_x64(self,raw,offset,at):
            for decoder in (decode_register_bit_set,decode_byte_left_shift,decode_byte_not,decode_byte_register_add):
                result=decoder(raw,offset,at)
                if result is not None:return result
            return mapper.decode_one_x64(raw,offset,at)
    return decode_field_setup_instructions(Fallback(),data,start_va)
