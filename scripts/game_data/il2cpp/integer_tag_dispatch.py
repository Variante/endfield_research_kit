"""Signed byte tags, word memory comparisons and register increment widths.

These facts preserve original x64 operands; runtime tag/field meaning is not
inferred from an address, the instruction mnemonic or an indexed code table.
Sign extension follows the Intel SDM MOVSX/MOVSXD entries.
"""
from __future__ import annotations
from typing import Any
from scripts.game_data.il2cpp.integer_addressing import _address,_prefix,_reg,_required
from scripts.game_data.il2cpp.integer_widths import _byte,_word
from scripts.game_data.il2cpp.integer_source_operands import decode_source_operand_integer_instructions


def _memory_text(address,stop,start_va,bits):
    if address['ripRelative']:
        address.update(ripBase=start_va+stop,absoluteAddress=start_va+stop+address['displacement'])
        term=f'rip => {hex(address["absoluteAddress"])}'
    else:
        term=address['base'] or ''
        if address['index'] is not None:term+=('+' if term else '')+f'{address["index"]}*{address["scale"]}'
        d=address['displacement']
        if d or not term:term+=('+' if term and d>=0 else '-' if d<0 else '')+hex(abs(d))
    return f'{ {8:"byte",16:"word",32:"dword",64:"qword"}[bits]} [{term}]'


def _row(data,offset,stop,start_va,text,**facts):
    return {'offset':offset,'va':hex(start_va+offset),'bytes':data[offset:stop].hex(' '),'text':text,**facts},stop


def decode_signed_byte_extension(data:bytes,offset:int,start_va:int):
    if not 0<=offset<len(data):return None
    at,rex=_prefix(data,offset)
    if data[at:at+2]!=b'\x0f\xbe':return None
    at+=2;modrm=_required(data,at,1,offset,'signed-byte-extension')[0];at+=1
    bits=64 if rex&8 else 32;destination=_reg(((modrm>>3)&7)|((rex&4)<<1),bits)
    source_register=None;address=None
    if modrm>>6==3:source_register=_byte((modrm&7)|((rex&1)<<3),rex);operand=source_register
    else:
        address,at=_address(data,at,modrm,rex,offset,'signed-byte-extension')
        operand=_memory_text(address,at,start_va,8)
    return _row(data,offset,at,start_va,f'movsx {destination}, {operand}',
        write={'register':destination,'value':f'sign extend byte to {bits} destination bits'},
        signedByteExtensionOperation={'sourceRegister':source_register,'sourceAddress':address,
            'sourceBits':8,'destinationBits':bits,'destinationRegister':destination,
            'memoryReadBytes':1 if address else 0,'zeroExtendsDestinationTo64':bits==32,
            'writesFlags':False,'signedSourceRange':[-128,127]})


def decode_word_memory_compare(data:bytes,offset:int,start_va:int):
    if not 0<=offset<len(data) or data[offset]!=0x66:return None
    at,rex=_prefix(data,offset+1)
    if rex&8 or data[at:at+1] not in (b'\x39',b'\x3b'):return None
    opcode=data[at];at+=1;modrm=_required(data,at,1,offset,'word-memory-compare')[0];at+=1
    if modrm>>6==3:return None
    register=_word(((modrm>>3)&7)|((rex&4)<<1))
    address,at=_address(data,at,modrm,rex,offset,'word-memory-compare');memory=_memory_text(address,at,start_va,16)
    left,right=(register,memory) if opcode==0x3b else (memory,register)
    return _row(data,offset,at,start_va,f'cmp {left}, {right}',write=None,
        wordMemoryComparisonOperation={'bits':16,'register':register,'sourceAddress':address,
            'memoryReadBytes':2,'registerIsLeftOperand':opcode==0x3b,'preservesRegisters':True,
            'writesMemory':False,'flags':'16-bit left-minus-right flags; CF unsigned borrow, ZF equality, SF bit15 and OF signed overflow'})


def decode_dword_sign_extension(data:bytes,offset:int,start_va:int):
    if not 0<=offset<len(data):return None
    at,rex=_prefix(data,offset)
    if not rex&8 or data[at:at+1]!=b'\x63':return None
    at+=1;modrm=_required(data,at,1,offset,'dword-sign-extension')[0];at+=1
    destination=_reg(((modrm>>3)&7)|((rex&4)<<1),64);register=None;address=None
    if modrm>>6==3:register=_reg((modrm&7)|((rex&1)<<3),32);operand=register
    else:
        address,at=_address(data,at,modrm,rex,offset,'dword-sign-extension');operand=_memory_text(address,at,start_va,32)
    return _row(data,offset,at,start_va,f'movsxd {destination}, {operand}',
        write={'register':destination,'value':'sign extend dword to full 64-bit destination'},
        dwordSignExtensionOperation={'destinationRegister':destination,'destinationBits':64,
            'sourceRegister':register,'sourceAddress':address,'sourceBits':32,
            'memoryReadBytes':4 if address else 0,'writesFlags':False})


def decode_register_increment(data:bytes,offset:int,start_va:int):
    if not 0<=offset<len(data):return None
    at,rex=_prefix(data,offset)
    if data[at:at+1]!=b'\xff':return None
    at+=1;modrm=_required(data,at,1,offset,'register-increment')[0];at+=1
    if modrm>>6!=3 or (modrm>>3)&7 or rex&4:return None
    bits=64 if rex&8 else 32;destination=_reg((modrm&7)|((rex&1)<<3),bits)
    return _row(data,offset,at,start_va,f'inc {destination}',
        write={'register':destination,'value':f'previous low {bits} bits plus one modulo 2^{bits}'},
        registerIncrementOperation={'bits':bits,'destinationRegister':destination,
            'zeroExtendsTo64':bits==32,'preservesCarryFlag':True,'writesFlags':['OF','SF','ZF','AF','PF']})


def decode_memory_immediate_compare(data:bytes,offset:int,start_va:int):
    if not 0<=offset<len(data):return None
    at,rex=_prefix(data,offset)
    if data[at:at+1] not in (b'\x80',b'\x83'):return None
    opcode=data[at];at+=1;modrm=_required(data,at,1,offset,'memory-immediate-compare')[0];at+=1
    if modrm>>6==3 or (modrm>>3)&7!=7 or rex&4:return None
    bits=8 if opcode==0x80 else 64 if rex&8 else 32
    address,at=_address(data,at,modrm,rex,offset,'memory-immediate-compare')
    raw_immediate=_required(data,at,1,offset,'memory-immediate-compare')[0];at+=1
    immediate=raw_immediate if bits==8 else raw_immediate-256 if raw_immediate>=128 else raw_immediate
    memory=_memory_text(address,at,start_va,bits)
    return _row(data,offset,at,start_va,f'cmp {memory}, {hex(immediate)}',write=None,
        memoryImmediateComparisonOperation={'bits':bits,'sourceAddress':address,'memoryReadBytes':bits//8,
            'encodedImmediateBits':8,'immediateValue':immediate,'immediateWord':immediate&((1<<bits)-1),
            'preservesRegisters':True,'writesMemory':False,'flags':f'{bits}-bit stored operand minus immediate flags'})


def decode_tag_dispatch_instructions(mapper:Any,data:bytes,start_va:int)->list[dict]:
    class Fallback:
        def decode_one_x64(self,raw,offset,at):
            for decoder in (decode_signed_byte_extension,decode_word_memory_compare,decode_dword_sign_extension,
                            decode_register_increment,decode_memory_immediate_compare):
                result=decoder(raw,offset,at)
                if result is not None:return result
            return mapper.decode_one_x64(raw,offset,at)
    return decode_source_operand_integer_instructions(Fallback(),data,start_va)
