"""Optional REX.W D3 /1 register ROR-by-CL, without changing older readers.

Count is sampled from the old CL and masked to six bits. Only the destination
register and conditional CF/OF are affected; no pointer meaning is inferred.
"""
from __future__ import annotations
from .integer_addressing import _prefix,_reg,_required
from .integer_tag_dispatch import _row
from .word_immediate_stores import decode_word_store_instructions


def rotate_right64(word,cl):
    if type(word) is not int or not 0<=word<1<<64 or type(cl) is not int or not 0<=cl<256:
        raise ValueError('x64.register-rotate.value-domain')
    count=cl&63
    return word if count==0 else ((word>>count)|(word<<(64-count)))&((1<<64)-1)


def decode_register_rotate(data,offset,start_va):
    if not 0<=offset<len(data):return None
    at,rex=_prefix(data,offset)
    if not rex&8 or data[at:at+1]!=b'\xd3':return None
    at+=1;modrm=_required(data,at,1,offset,'register-rotate')[0];at+=1
    if rex&4 or modrm>>6!=3 or (modrm>>3)&7!=1:return None
    destination=_reg((modrm&7)|((rex&1)<<3),64)
    return _row(data,offset,at,start_va,f'ror {destination}, cl',
        write={'register':destination,'value':'rotate previous QWORD right by pre-instruction CL modulo 64'},
        registerRotateOperation={'operation':'ror','destinationRegister':destination,'bits':64,
            'countRegister':'cl','countMask':63,'countUsesPreInstructionRegister':True,
            'preservesCountRegister':destination!='rcx','readsMemory':False,'writesMemory':False,
            'zeroCountPreservesDestinationAndFlags':True,'cfWhenCountNonzero':'most significant result bit',
            'ofWhenCountOne':'XOR of two most significant result bits','ofWhenCountAboveOne':'undefined',
            'preservesFlags':['SF','ZF','AF','PF'],'runtimeExecutionObserved':False})


def decode_rotate_instructions(mapper,data,start_va):
    class Fallback:
        def decode_one_x64(self,raw,offset,at):
            result=decode_register_rotate(raw,offset,at)
            return result if result is not None else mapper.decode_one_x64(raw,offset,at)
    return decode_word_store_instructions(Fallback(),data,start_va)
