"""Finite RDI Reader/RSI output DWORD capture with four inline updates."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def program(regions,entry,offsets,*,reader,output,path_factory=None):
    def need(k,c):
        if not c:raise ValueError('generatedRdiScalarCapture.'+k)
    need('literal-register-profile',(reader,output)==('rdi','rsi'))
    keys=('currentPtr','bufferLength','advancedCount','consumed')
    need('independent-small-offsets',set(offsets)>=set(keys)and len({offsets[k]for k in keys})==4
         and all(type(offsets[k])is int and 0<=offsets[k]<128 for k in keys))
    cur,rem,adv,used=(bytes((offsets[k],)).hex()for k in keys)
    need('callable-only-path-factory',path_factory is None or callable(path_factory))
    g=(BytesPath if path_factory is None else path_factory)(regions,entry);g.take('837f'+rem+'04');wrapper=g.at
    head=bytes(g.bytes.get(g.at+i,0)for i in range(3))
    profiles={bytes.fromhex('488b1e'):('rbx','rbp','r14','448b30','8b6f','83c5fc','896f'),
              bytes.fromhex('488b2e'):('rbp','rbx','r14','448b30','8b5f','83c3fc','895f'),
              bytes.fromhex('488b36'):('rsi','rbx','rbp','8b28','8b5f','83c3fc','895f')}
    need('one-literal-preserved-register-profile',head in profiles)
    wrapper_register,remaining_register,captured,load_hex,remaining_hex,subtract,store_hex=profiles[head]
    g.take(head.hex());g.branch('0f8c',False)
    pointer=g.at;g.take('488b47'+cur);load=g.at;g.take(load_hex);remaining=g.at
    g.take(remaining_hex+rem,subtract);g.branch('0f88',False)
    g.take('488347'+cur+'04','8347'+adv+'04','8347'+used+'04',store_hex+rem)
    return dict(selectedBytes=g.seen,guardInstructionVa=entry,sourcePointerInstructionVa=pointer,wireBytes=4,
                capturedSourceSlices=[dict(register=captured,sourceOffset=0,bytes=4,loadInstructionVa=load,kind='integer')],
                wrapperLoad=dict(instructionVa=wrapper,register=wrapper_register,outputRegister=output),
                remainingRegister=remaining_register,remainingLoadInstructionVa=remaining,
                readerOffsets={k:offsets[k]for k in keys},allFourReaderUpdatesProved=True,
                completeSourceBitsCaptured=True,sourceLocalValues=[],managedLayoutUsedForWidth=False,
                condition='Four coherent contiguous input bytes and nonnegative remaining count, disjoint stable Reader/frame/output. Entire R14d bits and every four-counter update are exact; field/setter/frame and child grammar remain independent.')
