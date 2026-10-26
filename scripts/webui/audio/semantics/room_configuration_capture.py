"""Stable original parameter settings joined to actual registered Room calls."""
from __future__ import annotations
import struct
from collections import Counter
from scripts.game_data.wwise_room_input_arithmetic import _history_binary,UnsupportedArithmetic


def known_bytes(raw,projection):
    return b''.join(raw[begin:end] for begin,end in projection['knownRanges'])


def diffusion_gains(raw,configuration,mxcsr):
    constants={v['role']:v['word'] for v in configuration['constants']};constants['positiveZero']=0
    if type(mxcsr) is not int or not 0<=mxcsr<2**16 or mxcsr&0x6000 or mxcsr&0x1f80!=0x1f80:raise UnsupportedArithmetic('roomConfigurationRoundingUnsupported')
    control=struct.unpack_from('<I',raw,configuration['storedControlOffset'])[0];scaled=_history_binary(control,constants['scale'],'mul',mxcsr);maximum=constants['maximum']
    result=[]
    for role in configuration['thresholdRoles']:
        value=_history_binary(scaled,constants[role]^0x80000000,'add',mxcsr);number=struct.unpack('<f',struct.pack('<I',value))[0]
        result.append(0 if number<=0 else maximum if number>=struct.unpack('<f',struct.pack('<I',maximum))[0] else value)
    return result


class RoomConfigurationCapture:
    def __init__(self,config):self.config=config;self.rows=[];self.counts=Counter()

    def validate_addresses(self,row,facts,fields):
        if row['phase']==3:return
        pointer=facts.get('parameterObject')
        for n,field in enumerate(fields):
            if field['name'].startswith('parameterWord') and facts.get(field['name']) is not None and (not pointer or row['addresses'][n]!=pointer+field['offset']):raise ValueError('Room configuration parameter address differs')
            if field['name']=='sampleRate' and facts.get('sampleRate') is not None and row['addresses'][n]!=row['args'][0]+field['offset']:raise ValueError('Room configuration sample-rate address differs')

    def completed(self,b,r,i,f,room,*,closed):
        if not r['hook'].endswith('.roomVerbExecute'):return
        scope=room.instances.get((r['windowId'],r['captureId']))
        if not scope or not scope['admitted']:self.counts['roomConfigurationInstanceNotSelected']+=1;return
        result=dict(windowId=r['windowId'],roomCaptureId=r['captureId'],taskCaptureId=scope['taskCaptureId'],entrySequence=b['sequence'],returnSequence=r['sequence'],parameterObject=i.get('parameterObject'),wholeEventToDeviceClaim=False)
        def stop(status):
            result['status']=status;self.counts[status]+=1
            if len(self.rows)<100000:self.rows.append(result)
            else:self.counts['reportRowsOmitted']+=1
        if not closed or r['phase']!=2:return stop('roomConfigurationNotClosedNormally')
        p=self.config['parameterProjection'];count=p['byteExtent']//p['wordBytes'];initial=[i.get('parameterWord'+str(j)) for j in range(count)];final=[f.get('parameterWord'+str(j)) for j in range(count)]
        if any(type(w) is not int or not 0<=w<2**32 for w in initial+final):return stop('roomConfigurationParametersIncomplete')
        if not i.get('parameterObject') or i['parameterObject']!=f.get('parameterObject'):return stop('roomConfigurationParameterPointerChanged')
        if type(i.get('sampleRate')) is not int or not 8000<=i['sampleRate']<=192000 or i['sampleRate']!=f.get('sampleRate'):return stop('roomConfigurationSampleRateNotSelected')
        result['sampleRate']=i['sampleRate']
        before=struct.pack('<'+str(count)+'I',*initial);after=struct.pack('<'+str(count)+'I',*final);expected=b['moduleBase']+int(self.config['parameterVtableRva'],16)
        if struct.unpack_from('<Q',before)[0]!=expected or struct.unpack_from('<Q',after)[0]!=expected:return stop('roomConfigurationParameterClassDiffers')
        result['stateMetadataChanges']=[key for key in ('fdnArray','fdnCount','earlyObject','earlyEnabled') if i.get(key)!=f.get(key)]
        result.update(initialParameterHex=before.hex(),returnedParameterHex=after.hex(),initialKnownHex=known_bytes(before,p).hex(),returnedKnownHex=known_bytes(after,p).hex(),transientChanges=[j for j in p['transientBytes'] if before[j]!=after[j]])
        if known_bytes(before,p)!=known_bytes(after,p):return stop('roomConfigurationSettingsChanged')
        return stop('stableOriginalRoomParameters')

    def publish(self,diagnostics,room_result,history_result,wet_result,oracle=None,*,input_result=None):
        rows=[] if diagnostics else self.rows;roots={(r['windowId'],r['roomCaptureId']):r for r in (room_result or {}).get('rows',())};history={}
        for row in (history_result or {}).get('rows',()):history.setdefault((row['windowId'],row['roomCaptureId']),[]).append(row)
        inputs={}
        for stage in (input_result or {}).get('rows',()):inputs.setdefault((stage['windowId'],stage['roomCaptureId']),[]).append(stage)
        wet={};cache={};rejected={}
        for row in (wet_result or {}).get('rows',()):wet.setdefault((row['windowId'],row['roomCaptureId']),[]).append(row)
        for row in rows:
            root=roots.get((row['windowId'],row['roomCaptureId']));row['busProcessingNode']=root.get('busProcessingNode') if root else None;row['diffusionComparisons']=[]
            if row['status']!='stableOriginalRoomParameters':continue
            raw=bytes.fromhex(row['returnedParameterHex'])
            for stage in history.get((row['windowId'],row['roomCaptureId']),()):
                if stage['kind']!='roomDiffusionKernel' or stage['status']!='exactRoomDiffusionPrefix':continue
                try:gains=diffusion_gains(raw,self.config['diffusionConfiguration'],stage['mxcsr'])
                except UnsupportedArithmetic as error:row['diffusionComparisons'].append(dict(captureId=stage['captureId'],status=str(error)));continue
                index=stage['stateIndex'];row['diffusionComparisons'].append(dict(captureId=stage['captureId'],stateIndex=index,expectedGain=gains[index],actualGain=stage['gainBits'],status='exactParameterToDiffusionGain' if gains[index]==stage['gainBits'] else 'parameterToDiffusionGainDiffers'))
            row['originalConfigurationComparisons']=[]
            if oracle is None:row['originalConfigurationStatus']='originalConfigurationOracleNotProvided';continue
            key=(row['returnedParameterHex'][16:],row['sampleRate'])
            if key in rejected:
                row['originalConfigurationStatus']=rejected[key]
                continue
            try:
                if key not in cache:
                    if len(cache)+len(rejected)>=64:raise ValueError('originalConfigurationUniqueBoundExceeded')
                    cache[key]=oracle.derive(row['returnedParameterHex'],row['sampleRate'],12546)
                derived=cache[key]
            except (ValueError,OSError) as error:
                row['originalConfigurationStatus']=str(error)[:240]
                if len(cache)+len(rejected)<64:rejected[key]=row['originalConfigurationStatus']
                continue
            row['originalConfigurationStatus']='originalOwnedConfigurationDerived';row['derivedConfiguration']=derived
            for stage in inputs.get((row['windowId'],row['roomCaptureId']),()):
                if stage['kind']!='roomInputPreparation' or stage['status']!='roomInputPreparationReturn':continue
                snapshots=stage['delayLengthSnapshots'];equal=all(snapshots[role+'Initial']==snapshots[role+'Returned']==derived['inputDelayLengths'][role] for role in ('copy','swap'))
                row['originalConfigurationComparisons'].append(dict(captureId=stage['captureId'],kind='inputDelayLengths',status='exactOriginalDerivedConfiguration' if equal else 'originalDerivedConfigurationDiffers'))
            for stage in wet.get((row['windowId'],row['roomCaptureId']),()):
                if not stage.get('ownershipStableAtRoomReturn'):continue
                if stage['status']=='exactRoomFdnPrefix':
                    index=stage['stateIndex'];model=derived['networks'][index] if index<len(derived['networks']) else None
                    equal=model is not None and derived['fdnCount']==stage['fdnCount'] and model['ringLengths']==[v['length'] for v in stage['ringProgression']] and model['b0Words']==stage['b0Words'] and model['a1Words']==stage['a1Words'];kind='fdnLengthsAndCoefficients'
                elif stage['status']=='exactRoomEarlyPrefixes':
                    model=derived['early'];actual=stage['projection'];equal=model is not None and model['length']==actual['length'] and [[v['gainBits'] for v in bank] for bank in model['banks']]==[[v['gainBits'] for v in bank] for bank in actual['banks']] and [[(v['initialIndex']+actual['ringIndex'])%actual['length'] for v in bank] for bank in model['banks']]==[[v['index'] for v in bank] for bank in actual['banks']];kind='earlyLengthsGainsAndPhase'
                elif stage['status']=='exactRoomDampingPrefix':equal=derived['dampingPoleBits']==stage['poleBits'];kind='wetDampingPole'
                else:continue
                row['originalConfigurationComparisons'].append(dict(captureId=stage['captureId'],kind=kind,status='exactOriginalDerivedConfiguration' if equal else 'originalDerivedConfigurationDiffers'))
            for stage in history.get((row['windowId'],row['roomCaptureId']),()):
                if stage['status']=='exactRoomDiffusionPrefix':
                    model=derived['diffusion'][stage['stateIndex']];equal=model['length']==stage['ringLength'] and model['gainBits']==stage['gainBits'];kind='diffusionLengthAndGain'
                elif stage['status']=='exactRoomTonePrefix':
                    mode=self.config['toneStageModes'].get(stage.get('stagePurpose'));equal=any(s['mode']==mode and s['matrixWords']==stage['matrixWords'] for s in derived['toneSlots']);kind='toneMatrixCandidate'
                else:continue
                row['originalConfigurationComparisons'].append(dict(captureId=stage['captureId'],kind=kind,status='exactOriginalDerivedConfiguration' if equal else 'originalDerivedConfigurationDiffers'))
        return dict(schema='endfield.audio-room-configuration-witness.v2',rows=rows,counts=dict(self.counts),diagnostics=list(diagnostics),originalConfigurationCacheEntries=len(cache),originalConfigurationRejectedEntries=len(rejected),wholeEventToDeviceClaim=False,evidenceBoundary='Original registered Room parameter class and complete stored parameter projection with matching known settings at normal paired return. Only native bulk-store bytes are settings; padding, vtable addresses and transient refresh flags do not identify authored values. Matching snapshots do not prove atomicity or exclude intervening changes. Captured control to diffusion gains uses observed DSP rounding; optional original owned configuration compares lengths, coefficients, taps and matrix candidates. Full live history, actual authored bank occurrence, update lifetime and isolated Event contributions remain separate.')
