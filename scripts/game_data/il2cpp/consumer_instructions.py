"""Optional named-consumer ANDPS and word-store instruction framing."""
from scripts.game_data.il2cpp.integer_addressing import _prefix, _address, _required
from scripts.game_data.il2cpp.integer_tag_dispatch import _row
from scripts.game_data.il2cpp.memory_moves import _finish_address
from scripts.game_data.il2cpp.word_immediate_stores import decode_word_immediate_store
from scripts.game_data.il2cpp.type_data_initialization_instructions import decode_type_data_initialization_instructions


def decode_packed_single_and(data,offset,start):
    if not 0<=offset<len(data):return None
    at,rex=_prefix(data,offset)
    if data[at:at+2]!=b'\x0f\x54':return None
    at+=2;modrm=_required(data,at,1,offset,'packed-single-and')[0];at+=1
    destination=f'xmm{((modrm>>3)&7)|((rex&4)<<1)}';address=None;source=None
    if modrm>>6==3:source=f'xmm{(modrm&7)|((rex&1)<<3)}';operand=source
    else:
        address,at=_address(data,at,modrm,rex,offset,'packed-single-and');operand='['+_finish_address(address,at,start)+']'
    return _row(data,offset,at,start,f'andps {destination}, {operand}',write={'register':destination,'value':'bitwise AND of low 128 bits'},
        packedSingleAndOperation=dict(destination=destination,sourceRegister=source,sourceAddress=address,bits=128,
            memoryReadBytes=16 if address else 0,memoryWriteBytes=0,writesFlags=False,writesGeneralRegisters=False,preservesVectorBitsAbove127=True))


def decode_consumer_instructions(mapper,data,start):
    class Fallback:
        def decode_one_x64(self,raw,offset,at):
            for decoder in (decode_packed_single_and,decode_word_immediate_store):
                result=decoder(raw,offset,at)
                if result is not None:return result
            return mapper.decode_one_x64(raw,offset,at)
    return decode_type_data_initialization_instructions(Fallback(),data,start)
