"""Exact legacy MOVSD memory fragments and low-byte output projections.

Register/register, VEX/EVEX and arithmetic forms supply no claim. The legacy
memory load clears bits 64..127 while leaving higher vector bits unchanged;
the byte projection below uses only the independently transferred low bytes.
"""
from __future__ import annotations
import copy
from .integer_addressing import _address,_required
from .memory_moves import _finish_address,decode_memory_move
from .byte_copy_programs import prove_byte_copy_moves


def decode_scalar_memory_move(data,offset,start_va):
    if not 0<=offset<len(data) or data[offset]!=0xf2:return None
    at=offset+1;rex=0
    if at<len(data) and 0x40<=data[at]<=0x4f:rex=data[at];at+=1
    if data[at:at+2] not in (b'\x0f\x10',b'\x0f\x11'):return None
    opcode=data[at+1];at+=2;modrm=_required(data,at,1,offset,'scalar-memory-move')[0];at+=1
    if modrm>>6==3:return None
    number=((modrm>>3)&7)|((rex&4)<<1)
    address,end=_address(data,at,modrm,rex,offset,'scalar-memory-move')
    text_address=_finish_address(address,end,start_va);load=opcode==0x10;register=f'xmm{number}'
    operands=f'{register}, [{text_address}]' if load else f'[{text_address}], {register}'
    return {'offset':offset,'va':hex(start_va+offset),'bytes':data[offset:end].hex(' '),'text':f'movsd {operands}',
        'memoryOperation':{'direction':'load' if load else 'store','register':register,'backingRegister':f'vector{number}',
            'registerBits':64,'registerBitOffset':0,'memoryBytes':8,'address':address,'valueExtension':None,
            'upperRegisterEffect':'zero bits 64 through 127; preserve bits above 127' if load else 'preserved',
            'requiredAlignmentBytes':1,'nonTemporalHint':False,'writesFlags':False}},end


def decode_fragment_instruction(raw,at,*,label):
    result=decode_scalar_memory_move(raw,0,at) or decode_memory_move(raw,0,at)
    if result is None or result[1]!=len(raw):
        raise ValueError(f'{label}.fragment-encoding: expected=one complete scalar/GP memory transfer actual={raw.hex()}')
    return result[0]['memoryOperation']


def prove_indexed_value_fragments(operations,*,source_base,source_index,index_scale,data_offset,output_base,output_bytes,label='indexed-value-fragments'):
    def fail(check,expected,actual):
        raise ValueError(f'{label}.{check}: expected={str(expected)[:256]} actual={str(actual)[:384]}')
    if (type(index_scale) is not int or index_scale not in (1,2,4,8) or type(data_offset) is not int
            or data_offset<0 or type(output_bytes) is not int or output_bytes<=0):
        fail('domain','positive exact index scale and output extent',(index_scale,data_offset,output_bytes))
    projected=copy.deepcopy(operations);clobbered=set()
    for op in projected:
        address=op.get('address',{});direction=op.get('direction')
        if type(address.get('displacement')) is not int:fail('displacement','signed integer',address)
        if direction=='load':
            if address.get('base')!=source_base or address.get('index')!=source_index or address.get('scale')!=index_scale:
                fail('source-affine-address','same source base and symbolic scaled index',op)
            if source_index in clobbered:fail('symbolic-index-preservation','unchanged common element index',source_index)
            address['displacement']-=data_offset;address['index']=None;address['scale']=1
            clobbered.add(op.get('backingRegister'))
        elif direction=='store':
            if address.get('base')!=output_base or address.get('index') is not None:fail('output-address','same unindexed output buffer',op)
        else:fail('direction','load or store',direction)
        if op.get('backingRegister','').startswith('vector'):
            if op.get('registerBits')!=64 or op.get('memoryBytes')!=8 or op.get('registerBitOffset')!=0:
                fail('vector-fragment','only transferred low qword',op)
            expected='zero bits 64 through 127; preserve bits above 127' if direction=='load' else 'preserved'
            if op.get('upperRegisterEffect')!=expected:fail('legacy-upper-effect',expected,op)
            # Only low transferred bytes participate. Upper vector state is
            # unconsumed by this proof and is never claimed to be preserved.
            op['upperRegisterEffect']='preserved'
    proof=prove_byte_copy_moves(projected,length=output_bytes,pointers={source_base:'source',output_base:'destination'},
        overlap='arbitrary',label=label+'.bytes')
    return {'allOutputBytesEqualSelectedSourceElementProved':True,'outputBytes':output_bytes,
        'sourceElementBaseEquation':f'{source_base}+{data_offset}+{source_index}*{index_scale}',
        'byteProof':proof,'unconsumedUpperVectorStateProjectedOut':True,'floatArithmeticOrConversionPerformed':False,
        'sourcePublicationVisibilityProved':False,'runtimeExecutionObserved':False}
