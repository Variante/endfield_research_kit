"""Optional F7 /0 memory TEST for complete enum-projection programs.

The immediate is sign-extended for a QWORD operand. TEST updates flags only;
its memory operand and all general registers are preserved. Other group forms,
legacy prefixes, register operands and opcode-extension REX.R are unsupported.
"""
from __future__ import annotations
from .integer_addressing import _address,_prefix,_required
from .integer_tag_dispatch import _row,_memory_text
from .normalization_instructions import decode_normalization_instructions


def decode_memory_immediate_test(data,offset,start_va):
    if not 0<=offset<len(data):return None
    at,rex=_prefix(data,offset)
    if rex&4 or data[at:at+1]!=b'\xf7':return None
    at+=1;modrm=_required(data,at,1,offset,'memory-immediate-test')[0];at+=1
    if modrm>>6==3 or (modrm>>3)&7:return None
    address,at=_address(data,at,modrm,rex,offset,'memory-immediate-test')
    encoded=int.from_bytes(_required(data,at,4,offset,'memory-immediate-test'),'little');at+=4
    bits=64 if rex&8 else 32
    immediate=(encoded if bits==32 or encoded<1<<31 else encoded-(1<<32))&((1<<bits)-1)
    operand=_memory_text(address,at,start_va,bits)
    return _row(data,offset,at,start_va,f'test {operand}, {hex(immediate)}',write=None,
        memoryImmediateTestOperation={'bits':bits,'sourceAddress':address,'encodedImmediateBits':32,
            'encodedImmediate':encoded,'effectiveImmediate':immediate,'immediateSignExtendedTo64':bits==64,
            'memoryReadBytes':bits//8,'memoryWriteBytes':0,'preservesRegisters':True,'writesResult':False,
            'clearsFlags':['CF','OF'],'undefinedFlags':['AF'],'writesResultFlags':['SF','ZF','PF']})


def decode_enum_underlying_instructions(mapper,data,start_va):
    class Fallback:
        def decode_one_x64(self,raw,offset,at):
            result=decode_memory_immediate_test(raw,offset,at)
            return result if result is not None else mapper.decode_one_x64(raw,offset,at)
    return decode_normalization_instructions(Fallback(),data,start_va)
