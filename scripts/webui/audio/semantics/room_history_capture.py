"""Bounded original tone and paired-history diffusion inside actual Room calls."""
from __future__ import annotations
from collections import Counter
import struct
from scripts.game_data.wwise_room_input_arithmetic import tone_prefix,diffusion_prefix,UnsupportedArithmetic

KINDS=('roomToneKernel','roomDiffusionKernel')
LIMIT=100000


def words(f,name,count=4):
    v=[f.get(name+str(i)) for i in range(count)]
    return v if all(type(w) is int and 0<=w<2**32 for w in v) else None


def hex_words(v):return struct.pack('<'+str(len(v))+'I',*v).hex()


class RoomHistoryCapture:
    def __init__(self,config):self.config=config;self.rows=[];self.counts=Counter();self.inputs={}

    def entry(self,row,facts,pending,ancestor,room,input_observer):
        if row['phase']!=1 or row['hook'].rsplit('.',1)[-1] not in KINDS:return
        root=ancestor(row,pending,'roomVerbExecute')
        if not root:return
        if len(self.inputs)>=LIMIT:raise ValueError('room history call bound exceeded')
        stages=input_observer.stages.get((row['windowId'],root['captureId']),{})
        pointer=facts.get('samplePointer') if row['hook'].endswith('.roomToneKernel') else facts.get('input')
        self.inputs[(row['windowId'],row['captureId'])]=stages.pop(pointer,None)

    def validate_addresses(self,row,facts,fields):
        if row['phase']==3:return
        for n,f in enumerate(fields):
            if facts.get(f['name']) is None or f['kind'] in ('argument','argumentU32'):continue
            base=row['args'][f['argIndex']] if f['argIndex']<4 else row['extraArgument'];offset=f['offset']
            if f['kind']=='ringPairU32':
                length=facts.get('length');index=facts.get('ringIndex');base=facts.get('ringPointer')
                if not length or index is None or index>=length:raise ValueError('room diffusion read lacks valid paired geometry')
                offset=((index+offset//8)%length)*8+offset%8
            elif f.get('pointerOffsets'):base=facts.get('samplePointer')
            if not base or row['addresses'][n]!=base+offset:raise ValueError(f"room history operand address differs: {f['name']}")
        pointer=facts.get('coefficientPointer') if row['hook'].endswith('.roomToneKernel') else facts.get('input')
        if row['spanBytes'] and row['spanAddress']!=pointer:raise ValueError('room history span address differs')

    def compare(self,b,r,i,f,closed,root):
        kind=r['hook'].rsplit('.',1)[-1]
        result=dict(captureId=r['captureId'],parentCaptureId=b['parentCaptureId'],entrySequence=b['sequence'],returnSequence=r['sequence'],kind=kind,frames=i.get('frames'),mxcsr=b.get('mxcsr'))
        def stop(s):result['status']=s;return result
        if not closed or r['phase']!=2 or not b.get('observationWindowOpen'):return stop('roomHistoryNotClosedNormally')
        caller=b['returnAddress']-b['moduleBase'];result['callerRva']=caller
        result['stagePurpose']=self.config.get('callerPurposeByReturnRva',{}).get(hex(caller))
        if caller not in [int(x,16) for x in self.config['callerReturnRvas'][kind]]:return stop('roomHistoryCallerNotSelected')
        if i.get('frames') not in self.config['selection']['blockFrames'] or f.get('frames')!=i['frames']:return stop('roomHistoryExtentNotSelected')
        if not b.get('roundingModeSampled'):return stop('roomHistoryRoundingNotObserved')
        try:
            if kind=='roomToneKernel':
                keys=('samplePointer','coefficientPointer','historyPointer')
                if any(not i.get(k) or i[k]!=f.get(k) for k in keys) or b['args'][2]!=r['args'][2] or b['args'][2]!=0 or b['extraArgument']!=r['extraArgument']:return stop('roomToneIdentityChanged')
                if b['spanBytes']!=128 or r['spanBytes']!=128 or b['spanHex']!=r['spanHex']:return stop('roomToneMatrixIncompleteOrChanged')
                if i['historyPointer']!=i['coefficientPointer']+self.config['layout']['toneMatrixHistoryOffset']:return stop('roomToneStateMatrixRelationDiffers')
                p=i['samplePointer'];end=p+i['frames']*4
                if p<i['coefficientPointer']+128 and i['historyPointer']<end:return stop('roomToneStateOverlapsSamples')
                inputs=words(i,'sampleWord');actual=words(f,'sampleWord');history=words(i,'historyWord')
                if inputs is None or actual is None or history is None:return stop('roomToneOperandsIncomplete')
                matrix=list(struct.unpack('<32I',bytes.fromhex(b['spanHex'])));expected,_=tone_prefix(inputs,matrix,history,b.get('mxcsr'))
                result.update(output=p,beforePrefix=hex_words(inputs),afterPrefix=hex_words(actual),matrixWords=matrix,initialHistoryWords=history,returnedHistoryWords=words(f,'historyWord'))
                status='exactRoomTonePrefix' if expected==actual else 'roomToneArithmeticMismatch'
            else:
                keys=('input','ringPointer','length','gainBits')
                if any(i.get(k) is None or i[k]!=f.get(k) for k in keys) or not i.get('input') or not i.get('ringPointer') or i.get('length',0)<4 or not 0<=i.get('ringIndex',-1)<i['length']:return stop('roomDiffusionGeometryNotSelected')
                returned=(i['ringIndex']+i['frames'])%i['length']
                if f.get('ringIndex')!=returned:return stop('roomDiffusionIndexDiffers')
                layout=self.config['layout'];relative=b['args'][0]-root['args'][0]-layout['diffusionFirstState']
                if relative<0 or relative%layout['diffusionStateStride'] or relative//layout['diffusionStateStride']>=layout['diffusionStateCount']:return stop('roomDiffusionStateNotOwnedByInstance')
                if i['input']<i['ringPointer']+i['length']*8 and i['ringPointer']<i['input']+i['frames']*4:return stop('roomDiffusionRingOverlapsSamples')
                inputs=words(i,'inputWord');history=words(i,'historyWord',8)
                if inputs is None or history is None or b['spanBytes']!=16 or r['spanBytes']!=16 or b['spanHex']!=hex_words(inputs):return stop('roomDiffusionOperandsIncomplete')
                actual=list(struct.unpack('<4I',bytes.fromhex(r['spanHex'])))
                if words(f,'inputWord')!=actual:return stop('roomDiffusionOutputIdentityDiffers')
                expected,_=diffusion_prefix(inputs,history,i['gainBits'],b.get('mxcsr'))
                result.update(output=i['input'],beforePrefix=b['spanHex'],afterPrefix=r['spanHex'],initialHistoryWords=history,gainBits=i['gainBits'],ringLength=i['length'],initialRingIndex=i['ringIndex'],returnedRingIndex=returned,stateIndex=relative//layout['diffusionStateStride'])
                status='exactRoomDiffusionPrefix' if expected==actual else 'roomDiffusionArithmeticMismatch'
        except UnsupportedArithmetic as error:return stop(str(error))
        result.update(inputWords=inputs,expected=expected,actual=actual,nonzeroPrefix=any(w&0x7fffffff for w in actual),changedPrefix=actual!=inputs)
        return stop(status)

    def completed(self,b,r,i,f,pending,ancestor,room,input_observer,*,closed):
        kind=r['hook'].rsplit('.',1)[-1]
        if kind not in KINDS:return
        key=r['windowId'],r['captureId'];producer=self.inputs.pop(key,None)
        root=ancestor(r,pending,'roomVerbExecute');scope=room.instances.get((r['windowId'],root['captureId'])) if root else None
        if not scope or not scope['admitted']:self.counts['roomHistoryInstanceNotSelected']+=1;return
        result=self.compare(b,r,i,f,closed,root)
        result.update(windowId=r['windowId'],threadId=r['threadId'],roomCaptureId=root['captureId'],taskCaptureId=scope['taskCaptureId'],wholeEventToDeviceClaim=False)
        result['producerPrefixCandidate']=dict(producer) if producer and producer['returnSequence']<b['sequence'] and producer['afterPrefix']==result.get('beforePrefix') else None
        if kind=='roomToneKernel':
            prep=ancestor(r,pending,'roomInputPreparation');result['preparationCaptureId']=prep['captureId'] if prep else None
        self.counts[result['status']]+=1
        if len(self.rows)<LIMIT:self.rows.append(result)
        else:self.counts['reportRowsOmitted']+=1
        if result['status'] in ('exactRoomTonePrefix','exactRoomDiffusionPrefix'):
            input_observer.stages.setdefault((r['windowId'],root['captureId']),{})[result['output']]=dict(captureId=r['captureId'],kind=kind,returnSequence=r['sequence'],afterPrefix=result['afterPrefix'])

    def publish(self,diagnostics,room_result,input_result):
        rows=[] if diagnostics else self.rows;roots={(r['windowId'],r['roomCaptureId']):r for r in (room_result or {}).get('rows',())}
        preparations={(r['windowId'],r['captureId']):r for r in (input_result or {}).get('rows',()) if r['kind']=='roomInputPreparation'}
        for r in rows:
            root=roots.get((r['windowId'],r['roomCaptureId']));r['busProcessingNode']=root.get('busProcessingNode') if root else None
        chains=[];tones={}
        for r in rows:
            if r['kind']=='roomToneKernel':tones.setdefault((r['windowId'],r.get('preparationCaptureId')),[]).append(r)
        for key,prep in preparations.items():
            steps=sorted(tones.get(key,()),key=lambda r:r['entrySequence'])
            folds=prep['folds']
            if prep['status']=='roomInputPreparationReturn' and len(folds)==1 and folds[0]['status']=='exactRoomFoldPrefix' and steps and all(s['status']=='exactRoomTonePrefix' and prep['entrySequence']<s['entrySequence']<s['returnSequence']<prep['returnSequence'] and s['output']==prep['output'] for s in steps) and folds[0]['returnSequence']<steps[0]['entrySequence'] and folds[0]['afterPrefix']==steps[0]['beforePrefix'] and all(a['returnSequence']<b['entrySequence'] and a['afterPrefix']==b['beforePrefix'] for a,b in zip(steps,steps[1:])) and steps[-1]['afterPrefix']==prep['afterPrefix']:
                chains.append(dict(windowId=key[0],preparationCaptureId=key[1],roomCaptureId=prep['roomCaptureId'],foldCaptureId=folds[0]['captureId'],toneCaptureIds=[s['captureId'] for s in steps],afterPrefix=prep['afterPrefix'],wholeEventToDeviceClaim=False))
        return dict(schema='endfield.audio-room-history-witness.v2',rows=rows,counts=dict(self.counts),inputToneChains=chains,openCalls=len(self.inputs),diagnostics=list(diagnostics),wholeEventToDeviceClaim=False,evidenceBoundary='Four-sample expanded tone and paired-history diffusion replay under original caller/registered instance admission, with observed nearest rounding and per-operation FTZ/DAZ controls. Preparation chains require ordered fold/tone/return content identity. Diffusion output uses observed paired old history; complete live history, ER taps, late feedback and isolated Event attribution remain unresolved.')
