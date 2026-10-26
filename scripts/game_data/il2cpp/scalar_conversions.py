"""Exact register-only legacy signed integer/Single conversions.

Record physical lanes, widths, extensions and MXCSR conditions. This reader
does not evaluate rounding, exception outcomes or runtime CPU execution.
"""
from __future__ import annotations
from .integer_addressing import _prefix,_reg,_required
from .integer_tag_dispatch import _row


def decode_scalar_signed_conversion(data,offset,start_va):
    if not 0<=offset<len(data) or data[offset]!=0xf3:return None
    at,rex=_prefix(data,offset+1);opcode=data[at:at+2]
    if opcode not in (b'\x0f\x2a',b'\x0f\x2c'):return None
    at+=2;modrm=_required(data,at,1,offset,'scalar-signed-conversion')[0];at+=1
    if modrm>>6!=3:return None
    reg=((modrm>>3)&7)|((rex&4)<<1);rm=(modrm&7)|((rex&1)<<3);bits=64 if rex&8 else 32
    to_single=opcode==b'\x0f\x2a';operation='cvtsi2ss' if to_single else 'cvttss2si'
    destination=f'xmm{reg}' if to_single else _reg(reg,bits)
    source=_reg(rm,bits) if to_single else f'xmm{rm}'
    facts={'operation':operation,'destinationRegister':destination,'sourceRegister':source,
           'signedIntegerBits':bits,'singleBits':32,'memoryReadBytes':0,'memoryWriteBytes':0,
           'writesEflags':False,'sourceRegisterPreserved':True,
           'destinationUpperVectorBitsPreserved':to_single,
           'integerDestinationZeroExtendsTo64':not to_single and bits==32,
           'rounding':'MXCSR rounding control' if to_single else 'truncate toward zero',
           'mxcsrExceptionBehaviorRequired':True,'concreteNumericResultProved':False,
           'runtimeExecutionObserved':False}
    if not to_single:facts['maskedInvalidIntegerResultBits']=1<<(bits-1)
    return _row(data,offset,at,start_va,f'{operation} {destination}, {source}',
                write={'register':destination,'value':'conditional signed integer/Single conversion'},scalarSignedConversionOperation=facts)
