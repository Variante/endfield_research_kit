"""Exact buffered float4 capture into nonvolatile XMM6, before Advance.

This is a byte program only. The caller proves its own nominal layout,
Advance effects, XMM6 frame preservation and full source-to-field transfer.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def program(regions,entry,offsets,*,reader,output,path_factory=None):
    if (reader,output)not in(('rbx','rdi'),('rdi','rbx')):
        raise ValueError('float4Capture.reader-output')
    keys=('currentPtr','bufferLength','advancedCount','consumed')
    if not set(keys)<=set(offsets) or len({offsets[k]for k in keys})!=4 or any(
            type(offsets[k])is not int or not 0<=offsets[k]<128 for k in keys):
        raise ValueError('float4Capture.independent-reader-offsets')
    if path_factory is not None and not callable(path_factory):raise ValueError('float4Capture.path-factory')
    g=BytesPath(regions,entry)if path_factory is None else path_factory(regions,entry)
    rdi=reader=='rdi'
    g.take(('837f'if rdi else'837b')+bytes((offsets['bufferLength'],)).hex()+'10')
    wrapper=g.at;load=bytes(g.bytes.get(g.at+i,-1)for i in range(3))
    allowed=(bytes.fromhex('488b33'),)if rdi else(bytes.fromhex('488b37'),bytes.fromhex('488b3f'))
    if load not in allowed:
        raise ValueError('float4Capture.wrapper-load')
    wrapper_register='rsi'if load[-1]in(0x37,0x33)else'rdi'
    g.take(load.hex());g.branch('0f8c',False)
    pointer=g.at;g.take(('488b47'if rdi else'488b43')+bytes((offsets['currentPtr'],)).hex(),'ba10000000','488bcf'if rdi else'488bcb')
    load=g.at;g.take('0f1030');call=g.at;target=g.relative('e8')
    return dict(selectedBytes=g.seen,guardInstructionVa=entry,
        sourcePointerInstructionVa=pointer,sourcePointerRegister='rax',wireBytes=16,
        capturedSourceSlices=[dict(register='xmm6',sourceOffset=0,bytes=16,loadInstructionVa=load,kind='sse')],
        wrapperLoad=dict(instructionVa=wrapper,register=wrapper_register,outputRegister=output),remainingRegister=None,
        sourceLocalValues=[],preservedCaptureRegistersRequired=['xmm6'],
        readerOffsets={k:offsets[k]for k in keys},advanceCallInstructionVa=call,advanceTargetVa=target,
        actualReaderArgument=reader,actualSignedCountArgument=16,
        independentAdvanceSourceRequired=True,completeSourceBitsCaptured=True,
        managedLayoutUsedForWidth=False)
