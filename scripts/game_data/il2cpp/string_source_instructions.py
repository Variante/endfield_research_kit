"""Optional memory updates for complete string-source program checking.

Other validators retain their narrower instruction lane: these forms need an
explicit memory-effect proof before a control analysis can accept them.
"""
from __future__ import annotations
from .integer_addressing import _address,_prefix,_reg,_required
from .integer_tag_dispatch import _memory_text,_row
from .word_immediate_stores import decode_word_immediate_store
from .type_data_initialization_instructions import decode_type_data_initialization_instructions
from .integer_widths import _word

def decode_memory_register_add(data,offset,start_va):
    if not 0<=offset<len(data):return None
    at,rex=_prefix(data,offset)
    if data[at:at+1]!=b'\x01':return None
    at+=1;modrm=_required(data,at,1,offset,'memory-register-add')[0];at+=1
    if modrm>>6==3:return None
    bits=64 if rex&8 else 32;source=_reg(((modrm>>3)&7)|((rex&4)<<1),bits)
    address,at=_address(data,at,modrm,rex,offset,'memory-register-add')
    return _row(data,offset,at,start_va,f'add {_memory_text(address,at,start_va,bits)}, {source}',write=None,
        memoryRegisterAddOperation={'bits':bits,'sourceRegister':source,'destinationAddress':address,
            'memoryReadBytes':bits//8,'memoryWriteBytes':bits//8,'wrapsModulo':1<<bits,
            'preservesRegisters':True,'writesFlags':['CF','OF','SF','ZF','AF','PF']})


def decode_locked_memory_or(data,offset,start_va):
    if not 0<=offset<len(data) or data[offset]!=0xf0:return None
    at,rex=_prefix(data,offset+1)
    if rex&4 or data[at:at+1] not in (b'\x81',b'\x83'):return None
    opcode=data[at];at+=1;modrm=_required(data,at,1,offset,'locked-memory-or')[0];at+=1
    if modrm>>6==3 or (modrm>>3)&7!=1:return None
    bits=64 if rex&8 else 32;address,at=_address(data,at,modrm,rex,offset,'locked-memory-or')
    size=1 if opcode==0x83 else 4;immediate=int.from_bytes(_required(data,at,size,offset,'locked-memory-or'),'little',signed=True);at+=size
    return _row(data,offset,at,start_va,f'lock or {_memory_text(address,at,start_va,bits)}, {hex(immediate)}',write=None,
        lockedMemoryOrOperation={'bits':bits,'destinationAddress':address,'signedImmediate':immediate,
            'encodedImmediateBits':size*8,'effectiveImmediate':immediate&((1<<bits)-1),
            'memoryReadBytes':bits//8,'memoryWriteBytes':bits//8,'lockedReadModifyWrite':True,
            'preservesRegisters':True,'writesFlags':['SF','ZF','PF'],'clearsFlags':['CF','OF'],'undefinedFlags':['AF']})


def decode_string_source_instructions(mapper,data,start_va):
    class Fallback:
        def decode_one_x64(self,raw,offset,at):
            for decoder in (decode_memory_register_add,decode_locked_memory_or,decode_word_immediate_store):
                result=decoder(raw,offset,at)
                if result is not None:return result
            return mapper.decode_one_x64(raw,offset,at)
    return decode_type_data_initialization_instructions(Fallback(),data,start_va)


def decode_register_immediate_test(data,offset,start_va):
    if not 0<=offset<len(data):return None
    at,rex=_prefix(data,offset)
    if rex&4 or data[at:at+1]!=b'\xf7':return None
    at+=1;modrm=_required(data,at,1,offset,'register-immediate-test')[0];at+=1
    if modrm>>6!=3 or (modrm>>3)&7:return None
    encoded=int.from_bytes(_required(data,at,4,offset,'register-immediate-test'),'little');at+=4
    bits=64 if rex&8 else 32;source=_reg((modrm&7)|((rex&1)<<3),bits)
    immediate=(encoded if bits==32 or encoded<1<<31 else encoded-(1<<32))&((1<<bits)-1)
    return _row(data,offset,at,start_va,f'test {source}, {hex(immediate)}',write=None,
        registerImmediateTestOperation={'bits':bits,'sourceRegister':source,'encodedImmediateBits':32,
            'encodedImmediate':encoded,'effectiveImmediate':immediate,'immediateSignExtendedTo64':bits==64,
            'preservesRegisters':True,'memoryReadBytes':0,'memoryWriteBytes':0,
            'clearsFlags':['CF','OF'],'undefinedFlags':['AF'],'resultFlags':['SF','ZF','PF']})


def decode_utf8_word_arithmetic(data,offset,start_va):
    if not 0<=offset<len(data) or data[offset]!=0x66:return None
    at,rex=_prefix(data,offset+1)
    if rex&8 or data[at:at+1] not in (b'\x83',b'\x23',b'\x2b'):return None
    opcode=data[at];at+=1;modrm=_required(data,at,1,offset,'utf8-word-arithmetic')[0];at+=1
    if modrm>>6!=3:return None
    source=None;immediate=None
    if opcode==0x83:
        if rex&4 or (modrm>>3)&7!=4:return None
        destination=_word((modrm&7)|((rex&1)<<3))
        immediate=int.from_bytes(_required(data,at,1,offset,'utf8-word-arithmetic'),'little',signed=True);at+=1
        operand=hex(immediate&0xffff)
    else:
        destination=_word(((modrm>>3)&7)|((rex&4)<<1));source=_word((modrm&7)|((rex&1)<<3));operand=source
    operation='sub' if opcode==0x2b else 'and'
    flags={'writesFlags':['CF','OF','SF','ZF','AF','PF']} if operation=='sub' else {
        'clearsFlags':['CF','OF'],'resultFlags':['SF','ZF','PF'],'undefinedFlags':['AF']}
    return _row(data,offset,at,start_va,f'{operation} {destination}, {operand}',
        write={'register':destination,'value':f'low WORD {operation}; upper 48 bits preserved'},
        wordRegisterArithmeticOperation={'operation':operation,'bits':16,'destinationRegister':destination,
            'sourceRegister':source,'signedImmediate':immediate,'encodedImmediateBits':8 if source is None else None,
            'effectiveImmediate':immediate&0xffff if source is None else None,'preservesBits16Through63':True,
            'zeroExtendsTo64':False,'memoryReadBytes':0,'memoryWriteBytes':0,**flags})


def decode_al_immediate_compare(data,offset,start_va):
    if not 0<=offset<len(data) or data[offset]!=0x3c:return None
    immediate=_required(data,offset+1,1,offset,'al-immediate-compare')[0]
    return _row(data,offset,offset+2,start_va,f'cmp al, {hex(immediate)}',write=None,
        accumulatorByteComparisonOperation={'bits':8,'sourceRegister':'al','immediate':immediate,
            'preservesRegisters':True,'memoryReadBytes':0,'memoryWriteBytes':0,
            'flags':'8-bit AL minus immediate; CF unsigned borrow, ZF equality, SF bit7, OF signed overflow, AF bit4 borrow, PF low-byte parity'})


def decode_utf8_decoder_instructions(mapper,data,start_va):
    class Fallback:
        def decode_one_x64(self,raw,offset,at):
            for decoder in (decode_register_immediate_test,decode_utf8_word_arithmetic,decode_al_immediate_compare):
                result=decoder(raw,offset,at)
                if result is not None:return result
            return mapper.decode_one_x64(raw,offset,at)
    return decode_string_source_instructions(Fallback(),data,start_va)
