"""Exact lazy-usage-cell and numeric forms in runtime data construction.

These are instruction facts, not a statement that a lazy initializer ran or
that its chosen pointer identifies a live object. MUL declares both implicit
outputs; callers must not treat it as a single-register write.
"""
from __future__ import annotations
from .integer_addressing import _prefix,_address,_reg,_required
from .memory_moves import _finish_address
from .integer_widths import _byte
from .integer_context_memory import decode_accumulator_and
from .field_setup_instructions import decode_single_bit_register_shift
from .blackboard_vector_transfers import decode_blackboard_vectors
from .scalar_conversions import decode_scalar_signed_conversion


def _row(data,offset,end,start,text,**facts):
    return {'offset':offset,'va':hex(start+offset),'bytes':data[offset:end].hex(' '),'text':text,**facts},end


def decode_usage_atomic(data,offset,start):
    if not 0<=offset<len(data):return None
    locked=data[offset]==0xf0;at,rex=_prefix(data,offset+int(locked))
    xadd=data[at:at+2]==b'\x0f\xc1';xchg=data[at:at+1]==b'\x87'
    if not (xadd and locked or xchg):return None
    at+=2 if xadd else 1;modrm=_required(data,at,1,offset,'usage-atomic')[0];at+=1
    if modrm>>6==3:return None
    bits=64 if rex&8 else 32;register=_reg(((modrm>>3)&7)|((rex&4)<<1),bits)
    address,end=_address(data,at,modrm,rex,offset,'usage-atomic');operand=_finish_address(address,end,start)
    return _row(data,offset,end,start,('lock xadd' if xadd else 'xchg')+f' [{operand}], {register}',
        write={'register':register,'value':'old memory operand'},
        atomicMemoryOperation={'operation':'xadd' if xadd else 'xchg','address':address,'register':register,
            'bits':bits,'memoryReadBytes':bits//8,'memoryWriteBytes':bits//8,'locked':True,
            'zeroExtendsRegisterTo64':bits==32,'memoryResult':'old memory plus source, modulo width' if xadd else 'previous source register',
            'writesArithmeticFlags':xadd,'preservesFlags':not xadd})


def decode_register_byte_test(data,offset,start):
    if not 0<=offset<len(data):return None
    at,rex=_prefix(data,offset)
    if rex&4 or data[at:at+1]!=b'\xf6':return None
    at+=1;modrm=_required(data,at,1,offset,'register-byte-test')[0];at+=1
    if modrm>>6!=3 or (modrm>>3)&7:return None
    value=_required(data,at,1,offset,'register-byte-test')[0];at+=1
    register=_byte((modrm&7)|((rex&1)<<3),rex)
    return _row(data,offset,at,start,f'test {register}, {hex(value)}',write=None,
        byteTestOperation={'register':register,'immediate':value,'preservesRegisters':True,
            'clearsFlags':['CF','OF'],'resultFlags':['SF','ZF','PF'],'undefinedFlags':['AF']})


def decode_unsigned_register_multiply(data,offset,start):
    if not 0<=offset<len(data):return None
    at,rex=_prefix(data,offset)
    if rex&4 or data[at:at+1]!=b'\xf7':return None
    at+=1;modrm=_required(data,at,1,offset,'unsigned-register-multiply')[0];at+=1
    if modrm>>6!=3 or (modrm>>3)&7!=4:return None
    bits=64 if rex&8 else 32;source=_reg((modrm&7)|((rex&1)<<3),bits);low=_reg(0,bits);high=_reg(2,bits)
    return _row(data,offset,at,start,f'mul {source}',write=None,
        implicitRegisterWrites=[low,high],
        unsignedMultiplyOperation={'bits':bits,'source':source,'accumulator':low,'lowOutput':low,'highOutput':high,
            'zeroExtendsOutputsTo64':bits==32,'setsCarryAndOverflowIfHighNonzero':True,'otherArithmeticFlagsUndefined':True})


def decode_memory_source_subtract(data,offset,start):
    if not 0<=offset<len(data):return None
    at,rex=_prefix(data,offset)
    if data[at:at+1]!=b'\x2b':return None
    at+=1;modrm=_required(data,at,1,offset,'memory-source-subtract')[0];at+=1
    if modrm>>6==3:return None
    bits=64 if rex&8 else 32;destination=_reg(((modrm>>3)&7)|((rex&4)<<1),bits)
    address,end=_address(data,at,modrm,rex,offset,'memory-source-subtract');operand=_finish_address(address,end,start)
    return _row(data,offset,end,start,f'sub {destination}, [{operand}]',
        write={'register':destination,'value':f'previous destination minus memory, modulo {bits} bits'},
        memorySubtractOperation={'bits':bits,'destination':destination,'sourceAddress':address,'memoryReadBytes':bits//8,
            'writesMemory':False,'zeroExtendsTo64':bits==32,'writesArithmeticFlags':True})


def decode_packed_single_to_double(data,offset,start):
    if not 0<=offset<len(data):return None
    at,rex=_prefix(data,offset)
    if data[at:at+2]!=b'\x0f\x5a':return None
    at+=2;modrm=_required(data,at,1,offset,'packed-single-to-double')[0];at+=1
    if modrm>>6!=3:return None
    destination=f'xmm{((modrm>>3)&7)|((rex&4)<<1)}';source=f'xmm{(modrm&7)|((rex&1)<<3)}'
    return _row(data,offset,at,start,f'cvtps2pd {destination}, {source}',
        write={'register':destination,'value':'two Double lanes converted from previous source low two Single lanes'},
        packedConversion={'source':source,'destination':destination,'sourceLaneBits':32,'destinationLaneBits':64,
            'laneCount':2,'preservesBitsAbove127':True,'writesArithmeticFlags':False})


def decode_packed_double_to_single(data,offset,start):
    if not 0<=offset<len(data) or data[offset]!=0x66:return None
    at,rex=_prefix(data,offset+1)
    if data[at:at+2]!=b'\x0f\x5a':return None
    at+=2;modrm=_required(data,at,1,offset,'packed-double-to-single')[0];at+=1
    if modrm>>6!=3:return None
    destination=f'xmm{((modrm>>3)&7)|((rex&4)<<1)}';source=f'xmm{(modrm&7)|((rex&1)<<3)}'
    return _row(data,offset,at,start,f'cvtpd2ps {destination}, {source}',
        write={'register':destination,'value':'low64=two Single lanes converted from previous source Double lanes; bits64..127=zero'},
        packedConversion={'source':source,'destination':destination,'sourceLaneBits':64,'destinationLaneBits':32,
            'laneCount':2,'zeroesBits64Through127':True,'preservesBitsAbove127':True,
            'writesArithmeticFlags':False,'rounding':'MXCSR rounding control','mxcsrExceptionBehaviorRequired':True})


def decode_runtime_data(mapper,raw,start):
    class Adapter:
        def decode_one_x64(self,data,offset,at):
            for decoder in (decode_usage_atomic,decode_register_byte_test,decode_unsigned_register_multiply,
                            decode_memory_source_subtract,decode_packed_single_to_double,decode_packed_double_to_single,
                            decode_accumulator_and,decode_single_bit_register_shift,decode_scalar_signed_conversion):
                result=decoder(data,offset,at)
                if result is not None:return result
            return mapper.decode_one_x64(data,offset,at)
    return decode_blackboard_vectors(Adapter(),raw,start)
