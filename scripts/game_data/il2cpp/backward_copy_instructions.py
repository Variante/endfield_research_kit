"""Exact legacy MOVUPS/MOVAPS and byte TEST forms for backward programs.

Legacy moves transfer bits without float conversion and preserve vector bits
above 127. Aligned memory operands require sixteen-byte alignment. Other
prefixes, arithmetic, VEX/EVEX and memory TEST forms supply no added claim.
"""
from __future__ import annotations
from .integer_addressing import _address,_required,decode_address_integer_instructions
from .memory_moves import _finish_address,_register,decode_copy_padding


def decode_legacy_vector_move(data,offset,start_va):
    if not 0<=offset<len(data):return None
    at=offset;rex=0
    if 0x40<=data[at]<=0x4f:rex=data[at];at+=1
    if data[at:at+2] not in (b'\x0f\x10',b'\x0f\x11',b'\x0f\x28',b'\x0f\x29'):return None
    opcode=data[at+1];at+=2;modrm=_required(data,at,1,offset,'legacy-vector-move')[0];at+=1
    number=((modrm>>3)&7)|((rex&4)<<1);register=f'xmm{number}'
    load=opcode in (0x10,0x28);aligned=opcode in (0x28,0x29);mnemonic='movaps' if aligned else 'movups'
    row={'offset':offset,'va':hex(start_va+offset)}
    if modrm>>6==3:
        other=(modrm&7)|((rex&1)<<3);destination,source=(number,other) if load else (other,number)
        row.update(bytes=data[offset:at].hex(' '),text=f'{mnemonic} xmm{destination}, xmm{source}',
            vectorRegisterOperation={'source':f'vector{source}','destination':f'vector{destination}',
                'bits':128,'bitOffset':0,'upperRegisterEffect':'preserved','writesFlags':False,'readsMemory':False,'writesMemory':False})
        return row,at
    address,end=_address(data,at,modrm,rex,offset,'legacy-vector-move')
    text_address=_finish_address(address,end,start_va)
    operands=f'{register}, [{text_address}]' if load else f'[{text_address}], {register}'
    row.update(bytes=data[offset:end].hex(' '),text=f'{mnemonic} {operands}',
        memoryOperation={'direction':'load' if load else 'store','register':register,'backingRegister':f'vector{number}',
            'registerBits':128,'registerBitOffset':0,'memoryBytes':16,'address':address,'valueExtension':None,
            'upperRegisterEffect':'preserved','requiredAlignmentBytes':16 if aligned else 1,'nonTemporalHint':False,'writesFlags':False})
    return row,end


def decode_register_byte_test(data,offset,start_va):
    if not 0<=offset<len(data):return None
    at=offset;rex=0
    if 0x40<=data[at]<=0x4f:rex=data[at];at+=1
    if data[at:at+1]!=b'\xf6':return None
    modrm=_required(data,at+1,1,offset,'register-byte-test')[0]
    if modrm>>6!=3 or (modrm>>3)&7:return None
    mask=_required(data,at+2,1,offset,'register-byte-test')[0];end=at+3
    register,backing,bit_offset=_register((modrm&7)|((rex&1)<<3),8,bool(rex))
    return {'offset':offset,'va':hex(start_va+offset),'bytes':data[offset:end].hex(' '),
        'text':f'test {register}, 0x{mask:x}','byteTestOperation':{'register':register,'backingRegister':backing,
            'bits':8,'bitOffset':bit_offset,'mask':mask,'writesRegister':False,'writesMemory':False,
            'zeroFlagExpression':'(selected byte & mask) == 0','changesDirectionFlag':False}},end


def decode_backward_copy_instructions(mapper,data,start_va):
    class Fallback:
        def decode_one_x64(self,raw,offset,at):
            for decoder in (decode_legacy_vector_move,decode_register_byte_test,decode_copy_padding):
                result=decoder(raw,offset,at)
                if result is not None:return result
            return mapper.decode_one_x64(raw,offset,at)
    return decode_address_integer_instructions(Fallback(),data,start_va)
