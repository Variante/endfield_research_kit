"""Optional ADD/AND-immediate memory facts for native metadata initialization."""
from __future__ import annotations
from .integer_addressing import _address,_prefix,_required
from .integer_tag_dispatch import _memory_text,_row
from .enum_underlying_instructions import decode_enum_underlying_instructions
from .metadata_initialization_instructions import decode_unsigned_register_multiply

def decode_initialization_memory_update(data,offset,start_va):
    if not 0<=offset<len(data):return None
    at,rex=_prefix(data,offset)
    if rex&4 or data[at:at+1] not in (b'\x81',b'\x83'):return None
    opcode=data[at];at+=1;modrm=_required(data,at,1,offset,'initialization-memory-add')[0];at+=1
    group=(modrm>>3)&7
    if modrm>>6==3 or group not in (0,4):return None
    operation='add' if group==0 else 'and'
    bits=64 if rex&8 else 32;address,at=_address(data,at,modrm,rex,offset,'initialization-memory-add')
    size=1 if opcode==0x83 else 4;raw=_required(data,at,size,offset,'initialization-memory-add');at+=size
    immediate=int.from_bytes(raw,'little',signed=True);operand=_memory_text(address,at,start_va,bits)
    value=hex(immediate) if immediate>=0 else '-'+hex(-immediate)
    return _row(data,offset,at,start_va,f'{operation} {operand}, {value}',
        initializationMemoryUpdateOperation={'operation':operation,'bits':bits,'destinationAddress':address,'encodedImmediateBits':size*8,
            'signedImmediate':immediate,'effectiveImmediate':immediate&((1<<bits)-1),
            'memoryReadBytes':bits//8,'memoryWriteBytes':bits//8,'wrapsModulo':1<<bits,
            'preservesRegisters':True,'writesFlags':['CF','OF','SF','ZF','AF','PF'] if operation=='add' else ['SF','ZF','PF'],
            'clearsCarryAndOverflow':operation=='and','undefinedFlags':[] if operation=='add' else ['AF']})

def decode_type_data_initialization_instructions(mapper,data,start_va):
    class Fallback:
        def decode_one_x64(self,raw,offset,at):
            for decoder in (decode_initialization_memory_update,decode_unsigned_register_multiply):
                result=decoder(raw,offset,at)
                if result is not None:return result
            return mapper.decode_one_x64(raw,offset,at)
    return decode_enum_underlying_instructions(Fallback(),data,start_va)
