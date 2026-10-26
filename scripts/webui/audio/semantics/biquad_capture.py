"""Retain original biquad operands and their local effect-call transport."""
from __future__ import annotations
import math
import struct
from scripts.webui.audio.semantics.biquad_pcm_witness import compare_prefix


def snapshot(before,row,initial,final,selection):
    result=dict(captureId=row['captureId'],parentCaptureId=before['parentCaptureId'],entrySequence=before['sequence'],returnSequence=row['sequence'],
        callerRva=before['returnAddress']-before['moduleBase'],status='biquadOperandsUnsupported',wholeEventToDeviceClaim=False)
    geometry=('inputPlane','outputPlane','coefficientPointer','historyPointer','frameCountPointer','frameCount','segmentCount','bufferCount','processorMode')
    coefficients=['coefficientWord'+str(i) for i in range(5)];history=['historyWord'+str(i) for i in range(4)]
    if row['phase']!=2 or any(initial.get(k) is None or final.get(k) is None for k in list(geometry)+coefficients+history):return result
    if any(initial[k]!=final[k] for k in list(geometry)+coefficients):return result
    if initial['frameCount']!=selection['validFrames'] or initial['segmentCount']!=1 or initial['bufferCount']!=2 or not initial['inputPlane'] or initial['inputPlane']!=initial['outputPlane']:return result
    if before.get('roundingModeSampled') is not True or before['spanBytes']!=16 or row['spanBytes']!=16:return result
    words=[initial[k] for k in coefficients+history]
    if not all(math.isfinite(struct.unpack('<f',struct.pack('<I',w))[0]) for w in words):return result
    values=struct.unpack('<4f',bytes.fromhex(before['spanHex']))+struct.unpack('<4f',bytes.fromhex(row['spanHex']))
    if not all(math.isfinite(v) for v in values):return result
    result.update(status='pairedBiquadOperands',geometry={k:initial[k] for k in geometry},coefficientWords=[initial[k] for k in coefficients],
        initialHistoryWords=[initial[k] for k in history],finalHistoryWords=[final[k] for k in history],mxcsr=before['mxcsr'],
        beforePrefix=before['spanHex'],afterPrefix=row['spanHex'],finiteNonzeroPrefix=any(values),changedPrefix=before['spanHex']!=row['spanHex'])
    return result


def effect_steps(task,fx,declared):
    """An actual outer EQ call must contain the admitted service invocations."""
    if not declared:return dict(status='biquadPhasesNotRecorded',steps=[])
    # The driver assembles a new AkAudioObjects collection on its stack. Its
    # pointer and layout differ from the earlier descriptor-array collection.
    eq=[e for e in task.get('eq',[]) if e['parentCaptureId']==fx['captureId'] and e['instance']==fx['effectObject'] and fx['entrySequence']<e['entrySequence']<e['returnSequence']<fx['returnSequence']]
    if len(eq)!=1:return dict(status='eqCallNotSelected',steps=[])
    eq=eq[0]
    if any(eq[p].get(k) is None for p in ('initial','final') for k in ('outputGainBits','bandEnabled0','bandEnabled1','bandEnabled2')):return dict(status='eqControlsNotRecorded',steps=[])
    identity=('collectionCount','descriptor','samplePointer','owner','firstCollectionOwner','format','capacity','validFrames','parameterPointer','outputDbBits','includeLfe','processorService','processorVtable','processorExecuteTarget')
    if any(eq['initial'].get(k) is None or eq['initial'][k]!=eq['final'].get(k) for k in identity):return dict(status='eqCollectionChanged',steps=[])
    if eq['initial']['collectionCount']!=1 or eq['initial']['samplePointer']!=fx['initial']['sample'] or eq['initial']['descriptor']!=fx['selectedDescriptor'] or eq['initial']['owner']!=fx['initial']['owner'] or eq['initial']['firstCollectionOwner']!=eq['initial']['owner']:return dict(status='eqCollectionNotSelected',steps=[])
    if eq['initial']['processorExecuteTarget']!=eq['moduleBase']+int(declared['serviceEntryRva'],16):return dict(status='differentEqProcessorImplementation',steps=[])
    steps=sorted((s for s in task.get('filters',[]) if s['parentCaptureId']==eq['captureId']),key=lambda s:s['entrySequence'])
    if not steps:return dict(status='noBiquadServiceObserved',steps=[],eqCaptureId=eq['captureId'])
    if any(s['status']!='pairedBiquadOperands' or s['callerRva']!=int(declared['callerReturnRva'],16) or s['geometry']['inputPlane']!=fx['initial']['sample'] or not eq['entrySequence']<s['entrySequence']<s['returnSequence']<eq['returnSequence'] for s in steps):return dict(status='biquadServiceNotSelected',steps=[])
    if any(a['returnSequence']>=b['entrySequence'] or a['afterPrefix']!=b['beforePrefix'] for a,b in zip(steps,steps[1:])):return dict(status='biquadPrefixChainDiffers',steps=[])
    if steps[0]['beforePrefix']!=fx['beforePrefix']:return dict(status='biquadEntryPrefixDiffers',steps=[])
    for step in steps:step['comparison']=compare_prefix(step,declared)
    return dict(status='eqBiquadOperandChain',eqCaptureId=eq['captureId'],steps=steps,
        previousOutputGainBits=eq['initial'].get('outputGainBits'),targetOutputGainBits=eq['final'].get('outputGainBits'),
        outputDbBits=eq['initial'].get('outputDbBits'),includeLfe=eq['initial'].get('includeLfe'),
        processorExecuteTarget=eq['initial'].get('processorExecuteTarget'),
        parameterPointer=eq['initial']['parameterPointer'],
        initialEnabledBands=[eq['initial']['bandEnabled'+str(i)] for i in range(3)],
        finalEnabledBands=[eq['final']['bandEnabled'+str(i)] for i in range(3)],
        eqReturnPrefixMatchesLastBiquad=steps[-1]['afterPrefix']==fx['afterPrefix'],
        evidenceBoundary='Original service calls retain first-buffer PCM, coefficients, initial/final history and processor selection inside the actual EQ instance call. The final effect prefix may additionally include EQ output gain; DSP replay and whole-channel claims are separate.')
