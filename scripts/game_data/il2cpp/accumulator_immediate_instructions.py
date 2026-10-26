"""Optional DWORD/QWORD SUB accumulator immediate instruction facts."""
from scripts.game_data.il2cpp.integer_addressing import _required
from scripts.game_data.il2cpp.integer_tag_dispatch import _row
from scripts.game_data.il2cpp.metadata_initialization_instructions import decode_metadata_initialization_instructions

def decode_accumulator_immediate_subtraction(data,offset,start_va):
    if not 0<=offset<len(data):return None
    at=offset;bits=32
    if data[at:at+1]==b'\x48':bits=64;at+=1
    if data[at:at+1]!=b'\x2d':return None
    at+=1;encoded=int.from_bytes(_required(data,at,4,offset,'accumulator-immediate-subtraction'),'little');at+=4
    value=(encoded-(1<<32) if bits==64 and encoded>=1<<31 else encoded)&((1<<bits)-1)
    destination='rax' if bits==64 else 'eax'
    return _row(data,offset,at,start_va,f'sub {destination}, {hex(value)}',
        write={'register':destination,'value':f'previous low {bits} bits minus immediate modulo 2^{bits}'},
        accumulatorImmediateSubtractionOperation={'bits':bits,'destinationRegister':destination,
            'encodedImmediateBits':32,'encodedImmediate':encoded,'effectiveImmediateWord':value,
            'immediateSignExtendedTo64':bits==64,'zeroExtendsDestinationTo64':bits==32,
            'writesMemory':False,'memoryReadBytes':0,'memoryWriteBytes':0,
            'preservesOtherRegisters':True,'writesFlags':['CF','OF','SF','ZF','AF','PF']})

def decode_accumulator_immediate_instructions(mapper,data,start_va):
    class Fallback:
        def decode_one_x64(self,raw,offset,at):
            result=decode_accumulator_immediate_subtraction(raw,offset,at)
            return result if result is not None else mapper.decode_one_x64(raw,offset,at)
    return decode_metadata_initialization_instructions(Fallback(),data,start_va)
