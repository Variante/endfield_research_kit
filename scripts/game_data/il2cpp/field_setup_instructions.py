"""Optional integer/Single forms used by complete field setup programs.

Original readers remain unchanged. Unknown encodings retain their refusal;
instruction facts establish no class layout, lock, capacity or runtime value.
"""
from __future__ import annotations
from .integer_addressing import _address,_prefix,_reg,_required
from .integer_byte_operations import _destination
from .integer_tag_dispatch import _row,_memory_text
from .integer_byte_shifts import decode_byte_shift_instructions
from .scalar_conversions import decode_scalar_signed_conversion


def decode_single_bit_register_shift(data,offset,start_va):
    if not 0<=offset<len(data):return None
    at,rex=_prefix(data,offset)
    if rex&4 or data[at:at+1]!=b'\xd1':return None
    at+=1;modrm=_required(data,at,1,offset,'single-bit-register-shift')[0];at+=1
    if modrm>>6!=3 or (modrm>>3)&7!=5:return None
    bits=64 if rex&8 else 32;register=_reg((modrm&7)|((rex&1)<<3),bits)
    return _row(data,offset,at,start_va,f'shr {register}, 0x1',
        write={'register':register,'value':'logical right shift one bit'},
        singleBitRegisterShiftOperation={'operation':'shr','register':register,'bits':bits,
            'count':1,'logicalZeroFill':True,'zeroExtendsTo64':bits==32,'memoryReadBytes':0,'memoryWriteBytes':0,'flagsProved':False})


def decode_register_or(data,offset,start_va):
    if not 0<=offset<len(data):return None
    at,rex=_prefix(data,offset)
    if data[at:at+1]!=b'\x0b':return None
    at+=1;modrm=_required(data,at,1,offset,'register-or')[0];at+=1
    if modrm>>6!=3:return None
    bits=64 if rex&8 else 32;dest=_reg(((modrm>>3)&7)|((rex&4)<<1),bits);source=_reg((modrm&7)|((rex&1)<<3),bits)
    return _row(data,offset,at,start_va,f'or {dest}, {source}',
        write={'register':dest,'value':'previous destination OR source'},
        registerOrOperation={'destinationRegister':dest,'sourceRegister':source,'bits':bits,'zeroExtendsTo64':bits==32,
            'memoryReadBytes':0,'memoryWriteBytes':0,'clearsFlags':['CF','OF'],'undefinedFlags':['AF'],'writesResultFlags':['SF','ZF','PF']})


def decode_accumulator_test(data,offset,start_va):
    if not 0<=offset<len(data):return None
    at,rex=_prefix(data,offset)
    if rex&7 or data[at:at+1]!=b'\xa9':return None
    at+=1;encoded=_required(data,at,4,offset,'accumulator-test');at+=4
    bits=64 if rex&8 else 32;register=_reg(0,bits)
    signed=int.from_bytes(encoded,'little',signed=bits==64);mask=signed&((1<<bits)-1)
    return _row(data,offset,at,start_va,f'test {register}, {hex(signed)}',write=None,
        accumulatorTestOperation={'register':register,'bits':bits,'encodedImmediateBits':32,'immediateWord':mask,
            'signExtendsImmediateTo64':bits==64,'preservesRegisters':True,'memoryReadBytes':0,'memoryWriteBytes':0,
            'clearsFlags':['CF','OF'],'undefinedFlags':['AF'],'writesResultFlags':['SF','ZF','PF']})


def decode_register_bit_test(data,offset,start_va):
    if not 0<=offset<len(data):return None
    at,rex=_prefix(data,offset)
    if rex&4 or data[at:at+2]!=b'\x0f\xba':return None
    at+=2;modrm=_required(data,at,1,offset,'register-bit-test')[0];at+=1
    if modrm>>6!=3 or (modrm>>3)&7!=4:return None
    index=_required(data,at,1,offset,'register-bit-test')[0];at+=1
    bits=64 if rex&8 else 32;register=_reg((modrm&7)|((rex&1)<<3),bits)
    return _row(data,offset,at,start_va,f'bt {register}, {hex(index)}',write=None,
        registerBitTestOperation={'register':register,'bits':bits,'encodedBitIndex':index,'effectiveBitIndex':index&(bits-1),
            'preservesRegisters':True,'memoryReadBytes':0,'memoryWriteBytes':0,'writesCarryFlagFromSelectedBit':True,'otherFlagsProved':False})


def decode_byte_memory_or(data,offset,start_va):
    if not 0<=offset<len(data):return None
    at,rex=_prefix(data,offset)
    if data[at:at+1]!=b'\x0a':return None
    at+=1;modrm=_required(data,at,1,offset,'byte-memory-or')[0];at+=1
    if modrm>>6==3:return None
    address,at=_address(data,at,modrm,rex,offset,'byte-memory-or')
    operand=_memory_text(address,at,start_va,8);facts=_destination(((modrm>>3)&7)|((rex&4)<<1),rex)
    facts.update(operation='or',sourceAddress=address,memoryReadBytes=1,memoryWriteBytes=0,
                 clearsFlags=['CF','OF'],undefinedFlags=['AF'],writesResultFlags=['SF','ZF','PF'])
    return _row(data,offset,at,start_va,f'or {facts["destinationRegister"]}, {operand}',
        write={'register':facts['destinationRegister'],'value':'previous destination byte OR memory byte'},byteMemoryOrOperation=facts)


def decode_locked_memory_add(data,offset,start_va):
    if not 0<=offset<len(data) or data[offset]!=0xf0:return None
    at,rex=_prefix(data,offset+1)
    if data[at:at+1]!=b'\x01':return None
    at+=1;modrm=_required(data,at,1,offset,'locked-memory-add')[0];at+=1
    if modrm>>6==3:return None
    address,at=_address(data,at,modrm,rex,offset,'locked-memory-add');bits=64 if rex&8 else 32
    source=_reg(((modrm>>3)&7)|((rex&4)<<1),bits);operand=_memory_text(address,at,start_va,bits)
    return _row(data,offset,at,start_va,f'lock add {operand}, {source}',
        lockedMemoryAddOperation={'operation':'add','bits':bits,'sourceRegister':source,'sourceRegisterPreserved':True,
            'destinationAddress':address,'memoryReadBytes':bits//8,'memoryWriteBytes':bits//8,'locked':True,
            'memoryResult':f'previous memory plus source modulo 2^{bits}','writesFlags':['CF','OF','SF','ZF','AF','PF']})


def decode_field_setup_instructions(mapper,data,start_va):
    class Fallback:
        def decode_one_x64(self,raw,offset,at):
            for decoder in (decode_scalar_signed_conversion,decode_single_bit_register_shift,decode_register_or,
                            decode_accumulator_test,decode_register_bit_test,decode_byte_memory_or,decode_locked_memory_add):
                result=decoder(raw,offset,at)
                if result is not None:return result
            return mapper.decode_one_x64(raw,offset,at)
    return decode_byte_shift_instructions(Fallback(),data,start_va)
