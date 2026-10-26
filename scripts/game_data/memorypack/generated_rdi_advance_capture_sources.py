"""Two exact RDI Reader captures with an independently owned Advance call.

The raw twelve-byte capture keeps its low eight bytes in XMM6 and its high four
in R14d. The DWORD variant keeps the whole value in EBX. Their complete caller
frames, nominal fields and actual helper program remain independent gates.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

LABEL='generatedRdiAdvanceCapture'


def need(key,condition):
    if not condition:raise ValueError(LABEL+'.'+key)


def program(regions,entry,offsets,*,reader,output,path_factory=None):
    need('literal-reader-output-profile',(reader,output)in(('rdi','rsi'),('rdi','r14')))
    high_rsi=output=='r14'
    keys=('currentPtr','bufferLength','advancedCount','consumed')
    need('four-independent-small-offsets',set(offsets)>=set(keys)and
        len({offsets[k]for k in keys})==4 and all(type(offsets[k])is int and 0<=offsets[k]<128 for k in keys))
    need('callable-only-path-factory',path_factory is None or callable(path_factory))
    g=(BytesPath if path_factory is None else path_factory)(regions,entry)
    cur,rem=(bytes((offsets[k],)).hex()for k in keys[:2])
    g.take('837f'+rem);width=g.read(1)[0]
    need('two-literal-source-profiles',width in(4,12))
    wrapper=g.at;g.take(('498b1e'if width==12 else'498b36')if high_rsi else'488b1e'if width==12 else'4c8b36');g.branch('7d',True,1)
    pointer=g.at;g.take(('488b47'if width==12 else'488b5f')+cur,
        'ba'+width.to_bytes(4,'little').hex(),'488bcf')
    low=g.at
    if width==12:
        g.take('f20f1030');high=g.at;g.take('8b7008'if high_rsi else'448b7008')
        captured=[dict(register='xmm6',sourceOffset=0,bytes=8,loadInstructionVa=low,kind='sse'),
                  dict(register='rsi'if high_rsi else'r14',sourceOffset=8,bytes=4,loadInstructionVa=high,kind='integer')]
    else:
        g.take('8b1b')
        captured=[dict(register='rbx',sourceOffset=0,bytes=4,loadInstructionVa=low,kind='integer')]
    call=g.at;target=g.relative('e8')
    return dict(selectedBytes=g.seen,guardInstructionVa=entry,sourcePointerInstructionVa=pointer,
        sourcePointerRegister='rax'if width==12 else'rbx',wireBytes=width,capturedSourceSlices=captured,
        wrapperLoad=dict(instructionVa=wrapper,register='rbx'if width==12 else'rsi'if high_rsi else'r14',outputRegister=output),
        remainingRegister=None,sourceLocalValues=[],readerOffsets={k:offsets[k]for k in keys},
        advanceCallInstructionVa=call,advanceTargetVa=target,actualReaderArgument='rdi',actualSignedCountArgument=width,
        independentAdvanceSourceRequired=True,completeSourceBitsCaptured=True,managedLayoutUsedForWidth=False,
        preservedCaptureRegistersRequired=[p['register']for p in captured],
        condition='Literal enough-buffer edge and exact disjoint raw captures. The independently proved actual Advance must preserve the named Win64 nonvolatile registers; every captured byte, destination field and full caller frame remains separately owned. No nominal type or wire grammar is inferred from width.')
