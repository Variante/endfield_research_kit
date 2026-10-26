"""Optional register MUL facts for metadata initialization programs.

The unsigned full product writes both implicit result registers. These facts
do not establish a runtime operand value, allocation outcome or live target.
Existing instruction readers and their authenticated receipts are unchanged.
"""
from __future__ import annotations
from scripts.game_data.il2cpp.integer_addressing import _prefix,_reg,_required
from scripts.game_data.il2cpp.integer_tag_dispatch import _row
from scripts.game_data.il2cpp.generic_creation_instructions import decode_generic_creation_instructions


def decode_unsigned_register_multiply(data,offset,start_va):
    if not 0<=offset<len(data):return None
    at,rex=_prefix(data,offset)
    if rex&4 or data[at:at+1]!=b'\xf7':return None
    at+=1;modrm=_required(data,at,1,offset,'unsigned-register-multiply')[0];at+=1
    if modrm>>6!=3 or (modrm>>3)&7!=4:return None
    bits=64 if rex&8 else 32;source=_reg((modrm&7)|((rex&1)<<3),bits)
    low,high=('rax','rdx') if bits==64 else ('eax','edx')
    return _row(data,offset,at,start_va,f'mul {source}',
        implicitUnsignedMultiplyOperation={'bits':bits,'sourceRegister':source,
            'accumulatorRegister':low,'lowResultRegister':low,'highResultRegister':high,
            'fullProductBits':2*bits,'unsignedOperands':True,'writesMemory':False,
            'resultWritesZeroExtendTo64':bits==32,'sourcePreservedUnlessImplicitResult':source not in (low,high),
            'overflowFlags':['CF','OF'],'overflowCondition':'high result word is nonzero',
            'undefinedFlags':['SF','ZF','AF','PF']})


def decode_metadata_initialization_instructions(mapper,data,start_va):
    class Fallback:
        def decode_one_x64(self,raw,offset,at):
            result=decode_unsigned_register_multiply(raw,offset,at)
            return result if result is not None else mapper.decode_one_x64(raw,offset,at)
    return decode_generic_creation_instructions(Fallback(),data,start_va)
