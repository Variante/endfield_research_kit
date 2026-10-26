"""Literal CameraInitial24 capture in XMM6/XMM7 before actual Advance(24).

There is no typed Reader call in this profile. Literal buffered guard and
captured slices establish24 source bytes; the separate nominal layout, named
setter, actual Advance and complete caller frame must all join those bits.
"""
import json
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.skill_camera_initial_raw_sources import TYPE,FIELDS,PADDING

LABEL='generatedInitial24Capture'


def need(key,value,detail=None):
    if not value:raise ValueError(LABEL+'.'+key+(':'+str(detail)[:1000]if detail is not None else''))


def program(regions,entry,offsets,*,reader='rdi',output='rbx',path_factory=None):
    need('literal-reader-output',(reader,output)==('rdi','rbx'))
    need('callable-only-path-factory',path_factory is None or callable(path_factory))
    keys=('currentPtr','bufferLength','advancedCount','consumed')
    need('distinct-owned-reader-slots',set(offsets)>=set(keys)and len({offsets[k]for k in keys})==4
        and all(type(offsets[k])is int and 0<=offsets[k]<128 for k in keys))
    rem,cur=(bytes((offsets[k],)).hex()for k in('bufferLength','currentPtr'))
    g=(BytesPath if path_factory is None else path_factory)(regions,entry)
    g.take('837f'+rem+'18');wrapper=g.at;g.take('488b33');g.branch('0f8c',False)
    pointer=g.at;g.take('488b47'+cur,'ba18000000','488bcf')
    low=g.at;g.take('0f1030');high=g.at;g.take('f20f107810');call=g.at;advance=g.relative('e8')
    return dict(selectedBytes=g.seen,guardInstructionVa=entry,sourcePointerInstructionVa=pointer,
        sourcePointerRegister='rax',wireBytes=24,
        capturedSourceSlices=[dict(register='xmm6',sourceOffset=0,bytes=16,loadInstructionVa=low,kind='sse'),
            dict(register='xmm7',sourceOffset=16,bytes=8,loadInstructionVa=high,kind='sse')],
        sourceLocalValues=[],wrapperLoad=dict(instructionVa=wrapper,register='rsi',outputRegister=output),remainingRegister=None,
        readerOffsets={k:offsets[k]for k in keys},advanceCallInstructionVa=call,advanceTargetVa=advance,
        actualReaderArgument='rdi',actualSignedCountArgument=24,independentAdvanceSourceRequired=True,
        completeSourceBitsCaptured=True,preservedCaptureRegistersRequired=['xmm6','xmm7'],
        managedLayoutUsedForWidth=False,typedReadUnmanagedClaimed=False,fieldTransferProved=False,callerFrameProved=False,
        boolBytesNormalized=False,paddingBytesCopied=True)


def validate_nominal(event,setter):
    layout=event.get('inlineNominalLayout',{});raw=bytes.fromhex(setter.get('parameterTypeRecordHex',''))
    same_layout=json.loads(json.dumps(layout))==json.loads(json.dumps(setter.get('nominalValueLayout')))
    need('own-nominal-Initial24-parameter',event.get('kind')=='value24:'+TYPE and event.get('declaredType')==layout.get('typeName')==TYPE
        and same_layout and layout.get('managedBytes')==setter.get('storedBytes')==24
        and layout.get('boxedBytes')==40 and layout.get('referenceLaneOffsets')==[]and layout.get('paddingByteRanges')==PADDING
        and [tuple(f)for f in layout.get('fields',[])]==list(FIELDS)and layout.get('marshaledSizeUsedForWidth')is False
        and len(raw)==16 and raw[10:12]==bytes((17,128))and int.from_bytes(raw[:8],'little')==layout.get('typeDefinition'),
        dict(memberIndex=event.get('memberIndex'),fieldName=event.get('fieldName'),declaredType=event.get('declaredType'),
            sameSetterLayout=same_layout,layout=layout,parameterTypeRecordHex=setter.get('parameterTypeRecordHex'),storedBytes=setter.get('storedBytes')))
    program=setter.get('program',{})
    need('complete-own24-setter',program.get('sourceSlices')==[[0,16],[16,8]]
        and program.get('completeSourceBitsStoredUnchanged')is True and program.get('normalFrameAndReturn')is True)
    need('literal-inline24-event',event.get('mode')=='buffered-called-advance-initial24'
        and event.get('wireBytes')==24 and event.get('actualSourceProved')is True and event.get('context')is None)
    return layout
