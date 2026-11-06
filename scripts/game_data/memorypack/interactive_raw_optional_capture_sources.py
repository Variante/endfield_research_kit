"""Finite RDI/RSI raw Optional capture; nominal closed layout stays separate."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def program(regions,entry,offsets,*,reader,output):
    def need(key,condition):
        if not condition:raise ValueError('interactiveRawOptionalCapture.'+key)
    need('literal-register-roles',(reader,output)==('rdi','rsi'))
    keys=('currentPtr','bufferLength','advancedCount','consumed')
    need('four-independent-small-fields',all(type(offsets.get(k))is int and 0<=offsets[k]<128 for k in keys)
        and len({offsets[k]for k in keys})==4)
    g=BytesPath(regions,entry);prefix=bytes(g.bytes.get(entry+i,0)for i in range(4))
    need('literal-two-or-eight-byte-guard',prefix[:3]==bytes((0x83,0x7f,offsets['bufferLength']))and prefix[3]in(2,8))
    width=prefix[3];w=bytes((width,)).hex();c,r,a,u=(bytes((offsets[k],)).hex()for k in keys)
    g.take(prefix.hex());wrapper=g.at;g.take('488b2e');g.branch('7d',True,1)
    pointer=g.at;g.take('488b5f'+c);load=g.at;g.take('488b1b'if width==8 else'0fb71b')
    remaining=g.at;g.take('448b77'+r,'4183c6'+bytes((-width&255,)).hex());g.branch('79',True,1)
    g.take('488347'+c+w,'8347'+a+w,'8347'+u+w,'448977'+r)
    return dict(selectedBytes=g.seen,guardInstructionVa=entry,sourcePointerInstructionVa=pointer,
        sourcePointerRegister='rbx',wireBytes=width,capturedSourceSlices=[dict(register='rbx',
            sourceOffset=0,bytes=width,loadInstructionVa=load,kind='integer')],
        wrapperLoad=dict(instructionVa=wrapper,register='rbp',outputRegister=output),
        remainingRegister='r14',remainingLoadInstructionVa=remaining,sourceLocalValues=[],
        readerOffsets={k:offsets[k]for k in keys},allFourReaderUpdatesProved=True,
        completeSourceBitsCaptured=True,managedLayoutUsedForWidth=False)
