"""Selected register BTR-immediate, CDQ/CQO and dword/qword IDIV facts.

The decoder composes with existing address/lane readers and retains complete
instruction boundaries. It does not assume a nonzero divisor or a fitting
quotient; divide faults and valid memory remain separate program conditions.
"""
from __future__ import annotations
from typing import Any
from scripts.game_data.il2cpp.integer_addressing import (
    _address, _prefix, _reg, _required, decode_address_integer_instructions,
)


def decode_bit_reset(data: bytes, offset: int, start_va: int):
    if not 0 <= offset < len(data): return None
    at,rex=_prefix(data,offset)
    if data[at:at+2]!=b'\x0f\xba':return None
    at+=2;modrm=_required(data,at,1,offset,'bit-reset')[0];at+=1
    if modrm>>6!=3 or (modrm>>3)&7!=6 or rex&4:return None
    immediate=_required(data,at,1,offset,'bit-reset')[0];at+=1
    bits=64 if rex&8 else 32;register=_reg((modrm&7)|((rex&1)<<3),bits);bit=immediate%bits
    return {'offset':offset,'va':hex(start_va+offset),'bytes':data[offset:at].hex(' '),
        'text':f'btr {register}, {hex(immediate)}',
        'write':{'register':register,'value':f'previous({register}) AND {hex(((1<<bits)-1) ^ (1<<bit))}'},
        'bitResetOperation':{'register':register,'bits':bits,'encodedBitIndex':immediate,'selectedBit':bit,
            'zeroExtendsTo64':bits==32,'carryFromPreviousSelectedBit':True,'preservesZeroFlag':True,
            'undefinedFlags':['OF','SF','AF','PF']}},at


def decode_dividend_extension(data: bytes, offset: int, start_va: int):
    if not 0<=offset<len(data):return None
    at,rex=_prefix(data,offset)
    if data[at:at+1]!=b'\x99':return None
    at+=1;bits=64 if rex&8 else 32;low='rax' if bits==64 else 'eax';high='rdx' if bits==64 else 'edx'
    return {'offset':offset,'va':hex(start_va+offset),'bytes':data[offset:at].hex(' '),
        'text':'cqo' if bits==64 else 'cdq',
        'write':{'register':high,'value':f'all {bits} bits copy sign bit of {low}'},
        'dividendExtensionOperation':{'bits':bits,'lowRegister':low,'highRegister':high,
            'preservesLowRegister':True,'zeroExtendsHighTo64':bits==32,'writesFlags':False}},at


def decode_signed_divide(data: bytes, offset: int, start_va: int):
    if not 0<=offset<len(data):return None
    at,rex=_prefix(data,offset)
    if data[at:at+1]!=b'\xf7':return None
    at+=1;modrm=_required(data,at,1,offset,'signed-divide')[0];at+=1
    if (modrm>>3)&7!=7 or rex&4:return None
    bits=64 if rex&8 else 32;address=None;source_register=None
    if modrm>>6==3:
        source_register=_reg((modrm&7)|((rex&1)<<3),bits);operand=source_register
    else:
        address,at=_address(data,at,modrm,rex,offset,'signed-divide')
        if address['ripRelative']:
            address.update(ripBase=start_va+at,absoluteAddress=start_va+at+address['displacement'])
            term=f'rip => {hex(address["absoluteAddress"])}'
        else:
            term=address['base'] or ''
            if address['index'] is not None:term+=('+' if term else '')+f'{address["index"]}*{address["scale"]}'
            d=address['displacement']
            if d or not term:term+=('+' if term and d>=0 else '-' if d<0 else '')+hex(abs(d))
        operand=f'{"qword" if bits==64 else "dword"} [{term}]'
    low='rax' if bits==64 else 'eax';high='rdx' if bits==64 else 'edx'
    return {'offset':offset,'va':hex(start_va+offset),'bytes':data[offset:at].hex(' '),
        'text':f'idiv {operand}',
        'signedDivisionOperation':{'bits':bits,'dividendHighRegister':high,'dividendLowRegister':low,
            'quotientRegister':low,'remainderRegister':high,'divisorRegister':source_register,'divisorAddress':address,
            'rounding':'toward-zero','remainderSign':'same as dividend or zero','zeroExtendsResultsTo64':bits==32,
            'faults':['zero-divisor','quotient-outside-signed-result-width'],
            'undefinedFlags':['CF','OF','SF','ZF','AF','PF']}},at


def evaluate_idiv_words(*, high: int, low: int, divisor: int, bits: int=32) -> dict:
    """Exact mathematical normal-result model for raw operand-width words."""
    if type(bits) is not int or bits not in (32,64) or any(type(v) is not int or not 0<=v<1<<bits for v in (high,low,divisor)):
        raise ValueError('signed division requires dword/qword raw operand words')
    dividend=(high<<bits)|low
    if dividend & (1<<(bits*2-1)):dividend-=1<<(bits*2)
    signed_divisor=divisor-(1<<bits) if divisor & (1<<(bits-1)) else divisor
    if signed_divisor==0:raise ZeroDivisionError('idiv divide error: zero divisor')
    quotient=abs(dividend)//abs(signed_divisor)
    if (dividend<0)!=(signed_divisor<0):quotient=-quotient
    if not -(1<<(bits-1))<=quotient<1<<(bits-1):raise OverflowError('idiv divide error: quotient overflow')
    remainder=dividend-quotient*signed_divisor;mask=(1<<bits)-1
    return {'quotient':quotient,'remainder':remainder,'quotientWord':quotient&mask,'remainderWord':remainder&mask}


def decode_signed_integer_instructions(mapper:Any,data:bytes,start_va:int)->list[dict]:
    class Fallback:
        def decode_one_x64(self,raw,offset,at):
            for decoder in (decode_bit_reset,decode_dividend_extension,decode_signed_divide):
                result=decoder(raw,offset,at)
                if result is not None:return result
            return mapper.decode_one_x64(raw,offset,at)
    return decode_address_integer_instructions(Fallback(),data,start_va)
