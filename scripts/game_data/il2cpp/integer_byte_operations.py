"""Byte-register updates and read-only TEST-immediate instruction facts.

Intel SDM INC/DEC preserve CF; AND/OR clear CF/OF and leave AF undefined.
Byte writes preserve every other parent-register bit, including AH's distinct
bit range and REX's replacement of high-byte registers by SPL/BPL/SIL/DIL.
This optional lane adds no stored-schema or runtime-field meaning.
"""
from __future__ import annotations
from scripts.game_data.il2cpp.integer_addressing import _address, _prefix, _reg, _required
from scripts.game_data.il2cpp.integer_widths import _byte
from scripts.game_data.il2cpp.integer_tag_dispatch import _memory_text, _row
from scripts.game_data.il2cpp.integer_effects import decode_effect_instructions


def _destination(number, rex):
    high = not rex and 4 <= number < 8
    return {'destinationRegister': _byte(number, rex),
            'parentRegister': _reg(number-4 if high else number),
            'bitOffset': 8 if high else 0, 'bits': 8,
            'preservesOtherParentBits': True, 'zeroExtendsTo64': False,
            'memoryReadBytes': 0, 'memoryWriteBytes': 0}


def decode_byte_register_step(data, offset, start_va):
    if not 0 <= offset < len(data): return None
    at, rex = _prefix(data, offset)
    if rex & 4 or data[at:at+1] != b'\xfe': return None
    at += 1; modrm = _required(data, at, 1, offset, 'byte-register-step')[0]; at += 1
    group = (modrm >> 3) & 7
    if modrm >> 6 != 3 or group not in (0,1): return None
    fact = _destination((modrm & 7) | ((rex & 1) << 3), rex)
    operation = 'inc' if group == 0 else 'dec'
    fact.update(operation=operation, delta=1 if group == 0 else -1,
                wrapsModulo=256, preservesCarryFlag=True,
                writesFlags=['OF','SF','ZF','AF','PF'])
    return _row(data, offset, at, start_va, f'{operation} {fact["destinationRegister"]}',
                byteRegisterStepOperation=fact)


def decode_byte_register_logic(data, offset, start_va):
    if not 0 <= offset < len(data): return None
    at, rex = _prefix(data, offset); opcode = data[at:at+1]
    if opcode not in (b'\x24',b'\x0c',b'\x0a',b'\x08'): return None
    at += 1
    if opcode in (b'\x24',b'\x0c'):
        immediate = _required(data, at, 1, offset, 'byte-accumulator-logic')[0]; at += 1
        fact = _destination(0,rex); fact.update(immediateWord=immediate,sourceRegister=None)
        operation = 'and' if opcode == b'\x24' else 'or'; operand = hex(immediate)
    else:
        modrm = _required(data, at, 1, offset, 'byte-register-logic')[0]; at += 1
        if modrm >> 6 != 3: return None
        reg = ((modrm >> 3) & 7) | ((rex & 4) << 1); rm = (modrm & 7) | ((rex & 1) << 3)
        destination, source = (reg,rm) if opcode == b'\x0a' else (rm,reg)
        fact = _destination(destination,rex); fact.update(sourceRegister=_byte(source,rex),immediateWord=None)
        operation = 'or'; operand = fact['sourceRegister']
    fact.update(operation=operation, clearsFlags=['CF','OF'], undefinedFlags=['AF'],
                writesResultFlags=['SF','ZF','PF'])
    return _row(data, offset, at, start_va, f'{operation} {fact["destinationRegister"]}, {operand}',
                byteLogicalOperation=fact)


def decode_byte_immediate_test(data, offset, start_va):
    if not 0 <= offset < len(data):return None
    at,rex=_prefix(data,offset)
    if rex&4 or data[at:at+1]!=b'\xf6':return None
    at+=1;modrm=_required(data,at,1,offset,'byte-immediate-test')[0];at+=1
    if (modrm>>3)&7:return None
    register=_byte((modrm&7)|((rex&1)<<3),rex) if modrm>>6==3 else None
    address=None
    if register is None:address,at=_address(data,at,modrm,rex,offset,'byte-immediate-test')
    immediate=_required(data,at,1,offset,'byte-immediate-test')[0];at+=1
    operand=register or _memory_text(address,at,start_va,8)
    return _row(data,offset,at,start_va,f'test {operand}, {hex(immediate)}',write=None,
        byteImmediateTestOperation={'bits':8,'sourceRegister':register,'sourceAddress':address,'immediateWord':immediate,
            'memoryReadBytes':0 if register else 1,'memoryWriteBytes':0,'preservesRegisters':True,
            'clearsFlags':['CF','OF'],'undefinedFlags':['AF'],'writesResultFlags':['SF','ZF','PF']})


def decode_byte_operation_instructions(mapper, data, start_va):
    class Fallback:
        def decode_one_x64(self, raw, offset, at):
            for decoder in (decode_byte_register_step, decode_byte_register_logic, decode_byte_immediate_test):
                result = decoder(raw, offset, at)
                if result is not None: return result
            return mapper.decode_one_x64(raw, offset, at)
    return decode_effect_instructions(Fallback(), data, start_va)
