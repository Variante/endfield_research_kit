"""Exact generated DWORD capture with a separately owned Reader advance.

The enough-buffer edge, current pointer, whole captured DWORD and actual E8
arguments are checked here. The actual called helper independently proves all
four Reader updates and its complete restored frame. No managed field width,
refill path, registered method alias or child grammar is inferred.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

LABEL='generatedCalledAdvance'
def need(key,condition,detail=None):
    if not condition:raise ValueError(LABEL+'.'+key+':'+str(detail)[:800])

def program(regions,entry,offsets,*,reader,output):
    need('finite-actual-reader-output',reader=='r15'and output=='r14')
    need('four-distinct-small-Reader-offsets',set(offsets)>={'currentPtr','bufferLength','advancedCount','consumed'}and
        len({offsets[k]for k in('currentPtr','bufferLength','advancedCount','consumed')})==4 and
        all(type(offsets[k])is int and 0<=offsets[k]<128 for k in('currentPtr','bufferLength','advancedCount','consumed')))
    g=BytesPath(regions,entry);g.take('41837f'+bytes((offsets['bufferLength'],4)).hex());wrapper=g.at;g.take('498b3e');g.branch('7d',True,1)
    pointer=g.at;g.take('498b5f'+bytes((offsets['currentPtr'],)).hex(),'ba04000000','498bcf');load=g.at;g.take('8b1b')
    call=g.at;target=g.relative('e8')
    return dict(selectedBytes=g.seen,guardInstructionVa=entry,sourcePointerInstructionVa=pointer,sourcePointerRegister='rbx',
        wireBytes=4,capturedSourceSlices=[dict(register='rbx',sourceOffset=0,bytes=4,loadInstructionVa=load,kind='integer')],
        wrapperLoad=dict(instructionVa=wrapper,register='rdi',outputRegister=output),remainingRegister=None,sourceLocalValues=[],
        readerOffsets={k:offsets[k]for k in('currentPtr','bufferLength','advancedCount','consumed')},
        advanceCallInstructionVa=call,advanceTargetVa=target,actualReaderArgument='r15',actualSignedCountArgument=4,
        independentAdvanceSourceRequired=True,completeSourceBitsCaptured=True,managedLayoutUsedForWidth=False,
        condition='At least four contiguous buffered bytes, disjoint stable Reader/input/output/frame and normal noninterfering helpers. The whole captured EBX is preserved by an independently proved actual Advance call; refill and child grammar remain separate.')

def advance_program(regions,entry,offsets,*,zero=False):
    """Whole actual helper's nonnegative buffered and zero-count paths."""
    need('literal-count-case',type(zero)is bool)
    cur,rem,adv,used=(bytes((offsets[k],)).hex()for k in('currentPtr','bufferLength','advancedCount','consumed'))
    g=BytesPath(regions,entry);g.take('85d2');g.branch('74',zero,1)
    if not zero:
        g.take('48895c2410','57','4883ec20','4863fa','488bd9','4889742430','8b71'+rem,'2bf7');g.branch('0f88',False)
        g.take('48017b'+cur,'017b'+adv,'017b'+used,'8973'+rem,'488b742430','488b5c2438','4883c420','5f')
    g.take('c3')
    return dict(selectedBytes=g.seen,zeroCount=zero,allFourReaderUpdatesProved=not zero,normalReturn=True,entryRspRestored=True,
        allNonvolatilesRestored=True,readerRegister='incoming rcx',signedCountRegister='incoming edx',preservedCapturedRegister='rbx')

def derive(image,pins,*,target,offsets):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack import buff_ec_profiles_native as ec,scalar_param_native as scalar
    _publication_gate(image,pins);base=image.pe.image_base
    need('explicit-actual-call-target',type(target)is int and target>=base)
    family,windows,rows=ec.family(image,target-base)
    primary,=[w for w in windows if w['startRva']==target-base];end=primary['endRva']
    for window in sorted(windows,key=lambda w:w['startRva']):
        if window['startRva']==end:end=window['endRva']
    import hashlib
    raw=image.pe.bytes_at_va(target,end-(target-base))
    normal=dict(startRva=target-base,endRva=end,sha256=hashlib.sha256(raw).hexdigest().upper())
    record=dict(pointerRva=target-base,window=normal,fragmentWindows=[w for w in windows if w is not primary])
    scalar.advance_source(image,record,offsets,LABEL+'.actualAdvance')
    regions=[(base+w['startRva'],image.window_bytes(w))for w in windows]
    programs=[advance_program(regions,target,offsets,zero=zero)for zero in(False,True)]
    proof=dict(nativeInputs=dict(pins),targetRva=target-base,readerOffsets=dict(offsets),family=family,codeWindows=windows,
        sourceRegions=[(at,raw.hex().upper())for at,raw in regions],programs=programs,
        completeAdvanceProgramProved=True,allFourReaderUpdatesProved=True,entryRspRestored=True,allNonvolatilesRestored=True,
        zeroCountReturnsWithoutMutation=True,registeredMethodIdentityClaimed=False,childGrammarAdmitted=False,
        condition='Exact selected actual E8 helper, nonnegative requested count no larger than Reader remaining bytes, nonwrapping disjoint Reader/storage and ordinary Win64 call ABI. Full currentPtr/advancedCount/consumed/bufferLength effects and saved frame are proved; underflow/refill and runtime invocation remain unobserved.')
    _publication_gate(image,pins);return proof
