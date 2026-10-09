"""Decode selected dword register addition without changing the shared mapper.

The fallback adapter composes with the maintained lane decoder. Unsupported
forms remain outside this narrow subset and cannot prove an integer operation.
"""
from __future__ import annotations
from typing import Any
from .sse_lanes import decode_lane_transfer_instructions


def decode_register_add(data:bytes,offset:int,start_va:int)->tuple[dict,int]|None:
    if not 0<=offset<len(data):return None
    at=offset;rex=0
    if 0x40<=data[at]<=0x4f:rex=data[at];at+=1
    if rex&8 or data[at:at+1]!=b'\x03':return None
    at+=1
    if at>=len(data):
        raise ValueError(f'x64.integer-register-add.truncated: offset={offset} requiredEnd={at+1} bytes={len(data)}')
    modrm=data[at];at+=1
    if modrm>>6!=3:return None
    def register(number):
        return ('eax','ecx','edx','ebx','esp','ebp','esi','edi')[number] if number<8 else f'r{number}d'
    destination=register(((modrm>>3)&7)|((rex&4)<<1))
    source=register((modrm&7)|((rex&1)<<3))
    return {'offset':offset,'va':hex(start_va+offset),'bytes':data[offset:at].hex(' '),
        'text':f'add {destination}, {source}',
        'write':{'register':destination,'value':f'uint32_add_wrap(previous({destination}), {source}); zero extend to 64 bits'},
        'integerOperation':{'operation':'add','destination':destination,'source':source,'bits':32,
            'wrapsModulo':1<<32,'zeroExtendsTo64':True,'writesArithmeticFlags':True}},at


def decode_integer_register_instructions(mapper:Any,data:bytes,start_va:int)->list[dict]:
    class Fallback:
        def decode_one_x64(self,raw,offset,at):
            result=decode_register_add(raw,offset,at)
            return result if result is not None else mapper.decode_one_x64(raw,offset,at)
    return decode_lane_transfer_instructions(Fallback(),data,start_va)
