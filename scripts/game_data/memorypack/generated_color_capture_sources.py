"""Exact raw16 Color caller capture followed by an actual Advance call.

This finite RDI Reader/RBX wrapper-output program spills all captured bytes
before its actual helper call. Independent nominal layout, Advance effects,
subsequent local-to-field stores, named setter and full caller remain required.
It is not a Quaternion or hidden-result source and grants no field grammar.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def need(check,condition):
    if not condition:raise ValueError('generatedColorCapture.'+check)


def program(regions,entry,offsets,*,reader='rdi',output='rbx',path_factory=None):
    need('literal-reader-output',reader=='rdi'and output=='rbx')
    keys=('currentPtr','bufferLength','advancedCount','consumed')
    need('independent-small-reader-offsets',set(offsets)>=set(keys)
        and all(type(offsets[k])is int and 0<=offsets[k]<128 for k in keys)
        and len({offsets[k]for k in keys})==4)
    current=bytes((offsets['currentPtr'],)).hex();remaining=bytes((offsets['bufferLength'],)).hex()
    need('callable-only-path-factory',path_factory is None or callable(path_factory))
    g=(BytesPath if path_factory is None else path_factory)(regions,entry);g.take('837f'+remaining+'10');wrapper=g.at;g.take('488b33');g.branch('0f8c',False)
    pointer=g.at;g.take('488b47'+current,'ba10000000','488bcf');load=g.at;g.take('0f1000');spill=g.at;g.take('0f11442420')
    call=g.at;advance=g.relative('e8')
    return dict(selectedBytes=g.seen,guardInstructionVa=entry,sourcePointerInstructionVa=pointer,sourcePointerRegister='rax',
        wireBytes=16,capturedSourceSlices=[dict(register='xmm0',sourceOffset=0,bytes=16,loadInstructionVa=load,kind='sse')],
        wrapperLoad=dict(instructionVa=wrapper,register='rsi',outputRegister=output),remainingRegister=None,
        sourceLocalValues=[dict(displacement=32,bytes=16,sourceOffset=0,register='xmm0',storeInstructionVa=spill)],
        readerOffsets={k:offsets[k]for k in keys},advanceCallInstructionVa=call,advanceTargetVa=advance,
        actualReaderArgument='rdi',actualSignedCountArgument=16,independentAdvanceSourceRequired=True,
        completeSourceBitsCaptured=True,completeSourceBitsSpilledBeforeAdvance=True,managedLayoutUsedForWidth=False,
        condition='At least16 coherent contiguous buffered bytes, stable disjoint Reader/input/output/frame and normal ABI-preserving actual Advance. Captured bits survive in the exact stack local; independent nominal/setter/frame/Advance effects must be composed before field admission.')
