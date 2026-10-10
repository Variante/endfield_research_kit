"""Selected FF /1 register DEC widths, wrap and flag preservation.

Per the Intel SDM DEC entry: FF /1 decrements a register at its encoded width,
wraps at that width, preserves CF, and a DWORD destination zero-extends into
the full 64-bit register.
"""
from __future__ import annotations
from scripts.game_data.il2cpp.integer_addressing import _prefix,_reg,_required
from scripts.game_data.il2cpp.integer_tag_dispatch import decode_tag_dispatch_instructions


def decode_register_decrement(data:bytes,offset:int,start_va:int):
    if not 0<=offset<len(data):return None
    at,rex=_prefix(data,offset)
    if data[at:at+1]!=b'\xff':return None
    at+=1;modrm=_required(data,at,1,offset,'register-decrement')[0];at+=1
    if modrm>>6!=3 or (modrm>>3)&7!=1 or rex&4:return None
    bits=64 if rex&8 else 32;register=_reg((modrm&7)|((rex&1)<<3),bits)
    return {'offset':offset,'va':hex(start_va+offset),'bytes':data[offset:at].hex(' '),'text':f'dec {register}',
        'write':{'register':register,'value':f'previous low {bits} bits minus one modulo 2^{bits}'},
        'registerDecrementOperation':{'bits':bits,'destinationRegister':register,'wrapsModulo':1<<bits,
            'zeroExtendsTo64':bits==32,'preservesCarryFlag':True,'writesFlags':['OF','SF','ZF','AF','PF']}},at


def decode_decrement_instructions(mapper,data:bytes,start_va:int):
    class Fallback:
        def decode_one_x64(self,raw,offset,at):
            result=decode_register_decrement(raw,offset,at)
            return result if result is not None else mapper.decode_one_x64(raw,offset,at)
    return decode_tag_dispatch_instructions(Fallback(),data,start_va)
