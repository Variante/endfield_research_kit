"""Selected legacy MOVSD memory transfers, below vector/field meaning.

Only the low QWORD transfer is described. Register-only encodings, alternate
address-size prefixes and upper vector-lane effects are outside this reader.
"""
from __future__ import annotations
from .integer_addressing import _address,_prefix,_required
from .integer_tag_dispatch import _row
from .memory_moves import _finish_address


def decode_scalar_double_memory_move(data,offset,start_va):
    if not 0<=offset<len(data) or data[offset]!=0xf2:return None
    at,rex=_prefix(data,offset+1)
    opcode=data[at:at+2]
    if opcode not in (b'\x0f\x10',b'\x0f\x11'):return None
    at+=2;modrm=_required(data,at,1,offset,'scalar-double-memory')[0];at+=1
    if modrm>>6==3:return None
    number=((modrm>>3)&7)|((rex&4)<<1)
    address,at=_address(data,at,modrm,rex,offset,'scalar-double-memory')
    term=_finish_address(address,at,start_va);register=f'xmm{number}';load=opcode[-1]==0x10
    operands=f'{register}, [{term}]' if load else f'[{term}], {register}'
    return _row(data,offset,at,start_va,'movsd '+operands,
        memoryOperation={'direction':'load' if load else 'store','register':register,'backingRegister':f'vector{number}',
            'registerBits':128,'registerBitOffset':0,'memoryBytes':8,'address':address,
            'valueExtension':None,'upperRegisterEffect':'not asserted by this low-QWORD reader',
            'requiredAlignmentBytes':1,'nonTemporalHint':False,'rexWSelectsTransferWidth':False},
        scalarDoubleMemoryTransfer={'lowQwordBitsTransferred':64,'upperVectorLaneEffectsProved':False,
            'numericConversionPerformed':False,'wholeFieldOrFunctionMeaningProved':False})
