"""Optional exact legacy MOVHPD/PADDQ forms for initialization CFGs.

MOVHPD loads one QWORD into vector bits64..127 and preserves bits0..63 and
bits above127. The supported PADDQ register form adds two independent QWORD
lanes modulo2^64 and preserves vector bits above127. Neither writes EFLAGS or
general registers. Memory PADDQ, register MOVHPD, VEX/EVEX and alternate legacy
prefixes supply no added claim. Existing MOVSD memory semantics are reused.
"""
from scripts.game_data.il2cpp.integer_addressing import _prefix,_address,_required
from scripts.game_data.il2cpp.integer_tag_dispatch import _row
from scripts.game_data.il2cpp.memory_moves import _finish_address
from scripts.game_data.il2cpp.scalar_memory_moves import decode_scalar_memory_move
from scripts.game_data.il2cpp.enum_underlying_instructions import decode_enum_underlying_instructions


def decode_initialization_vector(data,offset,start_va):
    if not 0<=offset<len(data)or data[offset]!=0x66:return None
    at,rex=_prefix(data,offset+1)
    if rex&8:return None
    opcode=data[at:at+2]
    if opcode not in(b'\x0f\x16',b'\x0f\xd4'):return None
    at+=2;modrm=_required(data,at,1,offset,'initialization-vector')[0];at+=1
    number=((modrm>>3)&7)|((rex&4)<<1);destination='xmm'+str(number)
    if opcode==b'\x0f\xd4':
        if modrm>>6!=3:return None
        source='xmm'+str((modrm&7)|((rex&1)<<3))
        return _row(data,offset,at,start_va,f'paddq {destination}, {source}',
            write=dict(register=destination,value='two independent low128 QWORD sums modulo2^64'),
            packedQwordAddOperation=dict(destinationRegister=destination,sourceRegister=source,
                vectorBits=128,laneBits=64,lanes=2,wrapsModulo=1<<64,preservesBitsAbove127=True,
                memoryReadBytes=0,memoryWriteBytes=0,writesFlags=False,preservesGeneralRegisters=True))
    if modrm>>6==3:return None
    address,at=_address(data,at,modrm,rex,offset,'initialization-high-qword')
    term=_finish_address(address,at,start_va)
    return _row(data,offset,at,start_va,f'movhpd {destination}, [{term}]',
        memoryOperation=dict(direction='load',register=destination,backingRegister='vector'+str(number),
            registerBits=64,registerBitOffset=64,memoryBytes=8,address=address,valueExtension=None,
            upperRegisterEffect='preserve bits0..63 and bits above127',requiredAlignmentBytes=1,
            nonTemporalHint=False,writesFlags=False),
        highQwordMemoryTransfer=dict(destinationBits=[64,128],preservedBits=[[0,64],[128,None]],
            memoryReadBytes=8,memoryWriteBytes=0,writesFlags=False,preservesGeneralRegisters=True))


def decode_enum_initialization_instructions(mapper,data,start_va):
    class Fallback:
        def decode_one_x64(self,raw,offset,at):
            result=decode_initialization_vector(raw,offset,at)or decode_scalar_memory_move(raw,offset,at)
            return result if result is not None else mapper.decode_one_x64(raw,offset,at)
    return decode_enum_underlying_instructions(Fallback(),data,start_va)
