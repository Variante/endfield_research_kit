"""Actual RoomVerb stereo folding and circular history, bounded to four words."""
from __future__ import annotations
import struct
from collections import Counter
from scripts.game_data.wwise_room_input_arithmetic import fold_prefix,delay_prefix,UnsupportedArithmetic

KINDS=('roomInputPreparation','roomInputFold','roomDelayCopy','roomDelaySwap')
LIMIT=100000

def words(f,prefix):
    v=[f.get(prefix+str(i)) for i in range(4)]
    return v if all(type(w) is int and 0<=w<2**32 for w in v) else None

def prefix(r):return r['spanHex'] if r['spanBytes']==16 else None

class RoomInputCapture:
    def __init__(self,config):self.config=config;self.preps={};self.stages={};self.delay_inputs={};self.rows=[];self.counts=Counter()

    def entry(self,row,facts,pending,ancestor,room):
        if row['phase']!=1:return
        kind=row['hook'].rsplit('.',1)[-1];key=row['windowId'],row['captureId']
        if kind=='roomVerbExecute':
            if len(self.stages)>=LIMIT:raise ValueError('room input instance bound exceeded')
            self.stages[key]={};return
        if kind not in KINDS:return
        root=ancestor(row,pending,'roomVerbExecute');scope=room.instances.get((row['windowId'],root['captureId'])) if root else None
        if kind=='roomInputPreparation':
            if len(self.preps)>=LIMIT:raise ValueError('room input preparation bound exceeded')
            admitted=bool(scope and scope['admitted'] and row['args'][0]==root['args'][0] and row['args'][1]==root['args'][1])
            self.preps[key]=dict(admitted=admitted,roomCaptureId=root['captureId'] if root else None,folds=[])
        if root and kind in ('roomDelayCopy','roomDelaySwap'):
            self.delay_inputs[key]=self.stages.get((row['windowId'],root['captureId']),{}).get(facts.get('input'))
        if root and kind in KINDS:
            output=facts.get('output');self.stages.get((row['windowId'],root['captureId']),{}).pop(output,None)

    def validate_addresses(self,row,facts,fields,*,pending=None,ancestor=None,room=None):
        if row['phase']==3:return
        for i,f in enumerate(fields):
            if facts.get(f['name']) is None or f['kind'] in ('argument','argumentU32'):continue
            base=row['args'][f['argIndex']];offset=f['offset']
            if f['kind']=='indexedU32':base=facts.get('samplePointer');offset+=facts.get(f['indexField'],0)*4
            elif f['kind']=='ringU32':
                base=facts.get('ringPointer');length=facts.get(f['lengthField']);index=facts.get(f['indexField'])
                if not length or index is None or index>=length:raise ValueError('room history read lacks valid ring geometry')
                offset=((index+offset//4)%length)*4
            elif f.get('pointerOffsets'):
                # Preparation's tone byte is in the parameter object. Its
                # pointer was independently read at the enclosing Room entry;
                # the final byte address cannot prove that pointer by itself.
                root=ancestor(row,pending,'roomVerbExecute') if ancestor else None
                scope=room.instances.get((row['windowId'],root['captureId'])) if root and room else None
                if f['name']!='toneEnabled' or f['pointerOffsets']!=[self.config['layout']['parameterObject']] or not root or row['args'][0]!=root['args'][0]:
                    raise ValueError('room input parameter address lacks original Room identity')
                base=scope['initial'].get('parameterObject') if scope else None
            if not base or row['addresses'][i]!=base+offset:raise ValueError(f"room input operand address differs: {f['name']}")
        if row['spanBytes'] and row['spanAddress']!=facts.get('output'):raise ValueError('room input span address differs')

    def compare_fold(self,b,r,i,f,closed):
        result=dict(captureId=r['captureId'],entrySequence=b['sequence'],returnSequence=r['sequence'],output=i.get('output'),frames=i.get('frames'),frameOffset=i.get('frameOffset'),afterPrefix=prefix(r))
        def stop(s):result['status']=s;return result
        s=self.config['selection'];count=i.get('frames');offset=i.get('frameOffset')
        if r['phase']!=2 or not closed or not b.get('observationWindowOpen'):return stop('roomInputNotClosedNormally')
        if b['returnAddress']-b['moduleBase'] not in map(lambda x:int(x,16),self.config['callerReturnRvas']['roomInputFold']):return stop('roomFoldCallerNotSelected')
        if not (count in s['blockFrames'] and type(offset) is int and offset>=0 and offset+count<=s['validFrames'] and all(i.get(k)==f.get(k)==s[k] for k in ('format','capacity','validFrames'))):return stop('roomFoldGeometryNotSelected')
        if not all(i.get(k) and i.get(k)==f.get(k) for k in ('buffer','output','samplePointer')) or any(i.get(k)!=f.get(k) for k in ('frames','frameOffset','centerGainBits','lfeGainBits')):return stop('roomFoldIdentityOrArgumentsChanged')
        left,right=words(i,'leftWord'),words(i,'rightWord')
        if left is None or right is None or r['spanBytes']!=16:return stop('roomFoldOperandsIncomplete')
        if words(f,'leftWord')!=left or words(f,'rightWord')!=right:return stop('roomFoldInputChanged')
        if abs(i['output']-i['samplePointer'])<s['capacity']*8:return stop('roomFoldOutputOverlapsInput')
        if not b.get('roundingModeSampled'):return stop('roomFoldRoundingNotObserved')
        try:expected=fold_prefix(left,right,s['stereoFoldCoefficientBits'],b.get('mxcsr'))
        except UnsupportedArithmetic as e:return stop(str(e))
        actual=list(struct.unpack('<4I',bytes.fromhex(r['spanHex'])));result.update(expected=expected,actual=actual,inputWords=[left,right],nonzeroPrefix=any(w&0x7fffffff for w in actual))
        return stop('exactRoomFoldPrefix' if expected==actual else 'roomFoldArithmeticMismatch')

    def compare_delay(self,b,r,i,f,closed,kind):
        result=dict(captureId=r['captureId'],entrySequence=b['sequence'],returnSequence=r['sequence'],input=i.get('input'),output=i.get('output'),frames=i.get('frames'),afterPrefix=prefix(r),kind=kind)
        def stop(s):result['status']=s;return result
        if r['phase']!=2 or not closed or not b.get('observationWindowOpen'):return stop('roomInputNotClosedNormally')
        if b['returnAddress']-b['moduleBase'] not in map(lambda x:int(x,16),self.config['callerReturnRvas'][kind]):return stop('roomDelayCallerNotSelected')
        old=words(i,'historyWord');input_words=words(i,'inputWord')
        if old is None or input_words is None or r['spanBytes']!=16:return stop('roomDelayOperandsIncomplete')
        try:expected,index=delay_prefix(old,i.get('length'),i.get('ringIndex'),i.get('frames'))
        except ValueError:return stop('roomDelayGeometryNotSelected')
        if i['frames'] not in self.config['selection']['blockFrames'] or not all(i.get(k) for k in ('ringPointer','input','output')) or any(i.get(k)!=f.get(k) for k in ('length','ringPointer','input','output','frames')) or f.get('ringIndex')!=index:return stop('roomDelayStateTransitionDiffers')
        size=i['length']*4
        if any(not i.get(k) or (i[k]<i['ringPointer']+size and i['ringPointer']<i[k]+i['frames']*4) for k in ('input','output')):return stop('roomDelayRingOverlapsSamples')
        if kind=='roomDelayCopy' and (abs(i['input']-i['output'])<i['frames']*4 or words(f,'inputWord')!=input_words):return stop('roomDelayInputChangedOrOverlaps')
        actual=list(struct.unpack('<4I',bytes.fromhex(r['spanHex'])))
        if kind=='roomDelaySwap' and (prefix(b)!=struct.pack('<4I',*input_words).hex() or words(f,'inputWord')!=actual):return stop('roomDelaySwapSampleIdentityDiffers')
        result.update(expected=expected,actual=actual,initialRingIndex=i['ringIndex'],returnedRingIndex=index,ringLength=i['length'],inputWords=input_words,nonzeroPrefix=any(w&0x7fffffff for w in actual))
        return stop('exactRoomDelayPrefix' if expected==actual else 'roomDelayContentMismatch')

    def completed(self,b,r,i,f,pending,ancestor,room,*,closed):
        kind=r['hook'].rsplit('.',1)[-1];key=r['windowId'],r['captureId']
        if kind=='roomVerbExecute':self.stages.pop(key,None);return
        if kind not in KINDS:return
        root=ancestor(r,pending,'roomVerbExecute');scope=room.instances.get((r['windowId'],root['captureId'])) if root else None
        if not scope or not scope['admitted']:
            if kind=='roomInputPreparation':self.preps.pop(key,None)
            self.delay_inputs.pop(key,None)
            self.counts['roomInputInstanceNotSelected']+=1;return
        if kind=='roomInputPreparation':
            prep=self.preps.pop(key,None)
            if prep is None:raise ValueError('room input return lacks entry')
            s=self.config['selection'];caller=b['returnAddress']-b['moduleBase'] in [int(v,16) for v in self.config['callerReturnRvas'][kind]]
            normal=prep['admitted'] and caller and closed and r['phase']==2 and all(i.get(k)==f.get(k)==s[k] for k in ('format','capacity','validFrames')) and all(i.get(k)==f.get(k) for k in ('instance','buffer','output','frames','frameOffset')) and i.get('frames') in s['blockFrames'] and type(i.get('frameOffset')) is int and 0<=i['frameOffset']<=s['validFrames']-i['frames'] and bool(prefix(r))
            folds=prep['folds'];chain=normal and len(folds)==1 and folds[0]['status']=='exactRoomFoldPrefix' and folds[0]['afterPrefix']==prefix(r)
            result=dict(captureId=r['captureId'],entrySequence=b['sequence'],returnSequence=r['sequence'],status='roomInputPreparationReturn' if normal else 'roomInputPreparationNotSelected',
                output=i.get('output'),afterPrefix=prefix(r),frames=i.get('frames'),frameOffset=i.get('frameOffset'),folds=folds,foldPrefixMatchesPreparation=chain,
                delayLengthSnapshots=dict(copyInitial=i.get('copyDelayLength'),copyReturned=f.get('copyDelayLength'),swapInitial=i.get('swapDelayLength'),swapReturned=f.get('swapDelayLength')),
                toneSnapshots=dict(enabledInitial=i.get('toneEnabled'),enabledReturned=f.get('toneEnabled'),slotCountInitial=i.get('toneSlotCount'),slotCountReturned=f.get('toneSlotCount')))
        elif kind=='roomInputFold':
            parent=ancestor(r,pending,'roomInputPreparation');prep=self.preps.get((r['windowId'],parent['captureId'])) if parent else None
            if not prep or not prep['admitted'] or (b['args'][0],b['args'][3],b['args'][1],b['args'][2])!=(parent['args'][1],parent['args'][2],parent['args'][3],parent['extraArgument']):self.counts['roomFoldPreparationNotSelected']+=1;return
            result=self.compare_fold(b,r,i,f,closed)
            if len(prep['folds'])>=64:raise ValueError('room input fold count exceeds bounded preparation')
            prep['folds'].append(result)
        else:
            result=self.compare_delay(b,r,i,f,closed,kind)
            producer=self.delay_inputs.pop(key,None);input_words=words(i,'inputWord')
            result['producerPrefixCandidate']=dict(producer) if input_words and producer and producer['returnSequence']<b['sequence'] and producer['afterPrefix']==struct.pack('<4I',*input_words).hex() else None
        result.update(windowId=r['windowId'],threadId=r['threadId'],roomCaptureId=root['captureId'],taskCaptureId=scope['taskCaptureId'],kind=kind,wholeEventToDeviceClaim=False)
        self.counts[result['status']]+=1
        if len(self.rows)<LIMIT:self.rows.append(result)
        else:self.counts['reportRowsOmitted']+=1
        if result['status'] in ('roomInputPreparationReturn','exactRoomDelayPrefix'):
            self.stages.setdefault((r['windowId'],root['captureId']),{})[i['output']]=dict(captureId=r['captureId'],kind=kind,returnSequence=r['sequence'],afterPrefix=prefix(r))

    def publish(self,diagnostics,room_result):
        rows=[] if diagnostics else self.rows;rooms={(r['windowId'],r['roomCaptureId']):r for r in (room_result or {}).get('rows',())}
        for row in rows:
            root=rooms.get((row['windowId'],row['roomCaptureId']));row['busProcessingNode']=root.get('busProcessingNode') if root else None
        return dict(schema='endfield.audio-room-input-witness.v1',rows=rows,counts=dict(self.counts),openPreparations=len(self.preps),openInstances=len(self.stages),openDelayInputs=len(self.delay_inputs),diagnostics=list(diagnostics),wholeEventToDeviceClaim=False,
            evidenceBoundary='Four observed stereo fold samples and circular-history outputs in actual registered RoomVerb calls. Ordered preparation-to-delay content is checked within one Room call. Delay outputs use captured old history, not reconstructed state; tone processing, ER taps, diffusion/feedback, full buffers and isolated Event attribution remain unresolved.')
