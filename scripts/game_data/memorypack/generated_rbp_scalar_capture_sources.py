"""Literal RBP Reader/RSI output DWORD capture and actual Advance call.

The independently proved actual Advance owns its four Reader updates and
preserved RBX. Named setter, entire caller frame and enum/nominal semantics
remain separate from these captured four bytes. Refill is not selected.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def program(regions,entry,offsets,*,reader,output):
    def need(key,valid):
        if not valid:raise ValueError('generatedRbpScalarCapture.'+key)
    need('literal-reader-output-profile',(reader,output)==('rbp','rsi'))
    keys=('currentPtr','bufferLength','advancedCount','consumed')
    need('four-independent-small-offsets',set(offsets)>=set(keys)
        and len({offsets[key]for key in keys})==4
        and all(type(offsets[key])is int and 0<=offsets[key]<128 for key in keys))
    g=BytesPath(regions,entry);g.take('837d'+bytes((offsets['bufferLength'],4)).hex())
    wrapper=g.at;g.take('488b3e');g.branch('7d',True,1)
    pointer=g.at;g.take('488b5d'+bytes((offsets['currentPtr'],)).hex(),'ba04000000','488bcd')
    load=g.at;g.take('8b1b');call=g.at;target=g.relative('e8')
    return dict(selectedBytes=g.seen,guardInstructionVa=entry,sourcePointerInstructionVa=pointer,sourcePointerRegister='rbx',
        wireBytes=4,capturedSourceSlices=[dict(register='rbx',sourceOffset=0,bytes=4,loadInstructionVa=load,kind='integer')],
        wrapperLoad=dict(instructionVa=wrapper,register='rdi',outputRegister=output),remainingRegister=None,sourceLocalValues=[],
        readerOffsets={key:offsets[key]for key in keys},advanceCallInstructionVa=call,advanceTargetVa=target,
        actualReaderArgument='rbp',actualSignedCountArgument=4,independentAdvanceSourceRequired=True,
        completeSourceBitsCaptured=True,managedLayoutUsedForWidth=False,
        condition='At least four coherent buffered bytes, disjoint stable Reader/input/output/frame and normal helper effects. Entire EBX bits must be preserved by the independently proved actual Advance; refill and field/nominal/whole frame remain separate.')
