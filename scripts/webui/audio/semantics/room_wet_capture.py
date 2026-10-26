"""Actual RoomVerb wet generation from original per-call operands."""
from __future__ import annotations
import struct
from collections import Counter
from scripts.game_data.wwise_room_wet_arithmetic import fdn_prefix,fdn_prefix_modes,damping_prefix,early_prefix,UnsupportedArithmetic
from scripts.webui.audio.semantics.room_history_capture import words,hex_words

KINDS=('roomFdnKernel','roomWetDamping','roomEarlyReflectionKernel')
LIMIT=100000


def ordered_wet_paths(rows,room_result,history_result):
    """Join only observed, exact first prefixes within one completed Room call.

    A failed writer replaces the previous candidate. These are bounded sample
    joins, not allocation generations or a whole-buffer continuity claim.
    """
    roots={(r['windowId'],r['roomCaptureId']):r for r in (room_result or {}).get('rows',())}
    groups={}
    for row in rows+list((history_result or {}).get('rows',())):
        groups.setdefault((row['windowId'],row['roomCaptureId']),[]).append(row)
    links=[];accumulations=[]
    exact={'exactRoomFdnPrefix','exactRoomDampingPrefix','exactRoomEarlyPrefixes','exactRoomTonePrefix','exactRoomDiffusionPrefix'}
    for key,stages in groups.items():
        root=roots.get(key)
        if not root:continue
        writers={};chains={}
        calls=[dict(call,kind='roomBlend') for call in root.get('calls',())]
        for row in sorted(stages+calls,key=lambda r:r['returnSequence']):
            if row['kind'] in ('roomToneKernel','roomDiffusionKernel') and 'output' not in row:
                # Rejected geometry may not even identify the written plane.
                writers.clear();chains.clear();continue
            def candidate(pointer,prefix):
                previous=writers.get(pointer)
                return previous if previous and previous['returnSequence']<row['entrySequence'] and previous['frames']==row['frames'] and previous['afterPrefix']==prefix else None
            if row['kind']=='roomBlend':
                if row['status']!='exactRoomBlendPrefix':continue
                for bank,(pointer,values) in enumerate(zip(row['wetPointers'],row['wetWords'])):
                    previous=candidate(pointer,hex_words(values))
                    if previous:
                        links.append(dict(windowId=key[0],roomCaptureId=key[1],blendCaptureId=row['captureId'],wetBank=bank,producer=dict(previous),busProcessingNode=root.get('busProcessingNode') if previous['stable'] else None,wholeEventToDeviceClaim=False))
                continue
            outputs=[(pointer,(row.get('afterPrefixes') or [None]*len(row['outputs']))[bank]) for bank,pointer in enumerate(row['outputs'])] if row['kind']=='roomEarlyReflectionKernel' else [(row['output'],row.get('afterPrefix'))]
            inherited=candidate(row['output'],row.get('beforePrefix')) if row['kind'] in ('roomToneKernel','roomDiffusionKernel') else None
            if row['kind']=='roomFdnKernel':
                pointer=row['output'];previous=candidate(pointer,row.get('beforePrefix'))
                chain=chains.get(pointer)
                if row['status']=='exactRoomFdnPrefix' and row.get('ownershipStableAtRoomReturn'):
                    index=row['stateIndex']
                    if index in (0,1) and row['beforePrefix']==hex_words([0]*4):chain=[row['captureId']]
                    elif previous and previous['kind']=='roomFdnKernel' and chain and previous['stateIndex']+2==index:chain=chain+[row['captureId']]
                    else:chain=None
                else:chain=None
                chains[pointer]=chain
            elif row['kind']=='roomWetDamping':
                pointer=row['output'];previous=candidate(pointer,row.get('beforePrefix'));chain=chains.get(pointer)
                count=row.get('fdnCount')
                channel=row.get('stateIndex')
                selected=type(count) is int and type(channel) is int and channel in (0,1) and count>channel
                if row['status']=='exactRoomDampingPrefix' and row.get('ownershipStableAtRoomReturn') and previous and previous['kind']=='roomFdnKernel' and chain and selected and previous['stateIndex']==count-1-((count-1-channel)%2) and len(chain)==(count+1-channel)//2:
                    accumulations.append(dict(windowId=key[0],roomCaptureId=key[1],channel=row['stateIndex'],fdnCaptureIds=list(chain),dampingCaptureId=row['captureId'],busProcessingNode=root.get('busProcessingNode'),wholeEventToDeviceClaim=False))
                chains.pop(pointer,None)
            for pointer,prefix in outputs:
                writers.pop(pointer,None)
                if row['status'] in exact and prefix is not None and (row['kind'] in KINDS or inherited):
                    writers[pointer]=dict(captureId=row['captureId'],kind=row['kind'],returnSequence=row['returnSequence'],frames=row['frames'],afterPrefix=prefix,stable=inherited['stable'] if inherited else row.get('ownershipStableAtRoomReturn',False),stateIndex=row.get('stateIndex'),originKind=inherited['originKind'] if inherited else row['kind'])
    return dict(wetBlendPrefixLinks=links,fdnDampingPrefixChains=accumulations)


def decode_projection(row):
    if row['spanBytes']<32:raise ValueError('tap projection header missing')
    raw=bytes.fromhex(row['spanHex']);version,left,right,length,ring,index,reserved=struct.unpack_from('<4IQ2I',raw)
    if version!=1 or reserved or left>64 or right>64 or not 4<=length<=65535 or index>=length or not ring or len(raw)!=32+(left+right)*32:raise ValueError('tap projection header/extent differs')
    banks=[];cursor=32
    for count in (left,right):
        bank=[]
        for _ in range(count):
            gain,position,address,*samples=struct.unpack_from('<IIQ4I',raw,cursor);cursor+=32
            if position>=length or address!=ring+position*4:raise ValueError('tap projection sample address differs')
            bank.append(dict(gainBits=gain,index=position,address=address,words=samples))
        banks.append(bank)
    return dict(length=length,ringPointer=ring,ringIndex=index,banks=banks)


class RoomWetCapture:
    def __init__(self,config):self.config=config;self.rows=[];self.counts=Counter();self.inputs={};self.by_room={}

    def entry(self,row,facts,pending,ancestor,room,input_observer):
        if row['phase']!=1 or row['hook'].rsplit('.',1)[-1] not in KINDS:return
        root=ancestor(row,pending,'roomVerbExecute')
        if not root:return
        if len(self.inputs)>=LIMIT:raise ValueError('room wet call bound exceeded')
        stages=input_observer.stages.get((row['windowId'],root['captureId']),{})
        pointer=row['args'][1];producer=stages.get(pointer)
        outputs=row['args'][2:4] if row['hook'].endswith('.roomEarlyReflectionKernel') else [row['args'][2]] if row['hook'].endswith('.roomFdnKernel') else [pointer]
        self.inputs[(row['windowId'],row['captureId'])]=producer
        for output in outputs:stages.pop(output,None)

    def validate_addresses(self,row,facts,fields):
        if row['phase']==3:return
        for n,f in enumerate(fields):
            if facts.get(f['name']) is None or f['kind'] in ('argument','argumentU32'):continue
            base=row['args'][f['argIndex']];offset=f['offset']
            if f['kind']=='tapHistoryBytes':offset=0
            elif f['kind']=='ringU32':
                bank=f['name'][4];length=facts.get('length'+bank);index=facts.get('ringIndex'+bank);base=facts.get('ringPointer'+bank)
                if not length or index is None or index>=length:raise ValueError('room FDN read lacks ring geometry')
                offset=((index+offset//4)%length)*4
            if not base or row['addresses'][n]!=base+offset:raise ValueError(f"room wet operand address differs: {f['name']}")
        pointer=row['args'][0] if row['hook'].endswith('.roomEarlyReflectionKernel') else row['args'][2] if row['hook'].endswith('.roomFdnKernel') else row['args'][1]
        if row['spanBytes'] and row['spanAddress']!=pointer:raise ValueError('room wet span address differs')

    def compare(self,b,r,i,f,scope,closed):
        k=r['hook'].rsplit('.',1)[-1];root=scope['entry'];meta=scope['initial'];layout=self.config['layout'];s=self.config['selection']
        result=dict(captureId=r['captureId'],entrySequence=b['sequence'],returnSequence=r['sequence'],kind=k,frames=i.get('frames'),mxcsr=b.get('mxcsr'),fdnCount=meta.get('fdnCount'),output=r['args'][2] if k=='roomFdnKernel' else r['args'][1])
        if k=='roomEarlyReflectionKernel':result['outputs']=r['args'][2:]
        def stop(v):result['status']=v;return result
        if not closed or r['phase']!=2 or not b.get('observationWindowOpen'):return stop('roomWetNotClosedNormally')
        if b['returnAddress']-b['moduleBase'] not in [int(v,16) for v in self.config['callerReturnRvas'][k]]:return stop('roomWetCallerNotSelected')
        if i.get('frames') not in s['blockFrames'] or f.get('frames')!=i['frames'] or not b.get('roundingModeSampled'):return stop('roomWetExtentOrRoundingNotSelected')
        input_words=words(i,'inputWord')
        if input_words is None:return stop('roomWetInputIncomplete')
        try:
            if k=='roomFdnKernel':
                array=meta.get('fdnArray');count=meta.get('fdnCount');relative=b['args'][0]-(array or 0)
                if not array or type(count) is not int or relative<0 or relative%layout['fdnStride'] or relative//layout['fdnStride']>=count:return stop('roomFdnStateNotOwnedByInstance')
                rings=[];history=[];b0=[];a1=[];ranges=[];progress=[]
                for j in range(4):
                    length,index,pointer=(i.get(key+str(j)) for key in ('length','ringIndex','ringPointer'))
                    if type(length) is not int or length<4 or type(index) is not int or not 0<=index<length or not pointer:return stop('roomFdnGeometryNotSelected')
                    if any(i.get(key+str(j))!=f.get(key+str(j)) for key in ('length','ringPointer','b0Word','a1Word')) or f.get('ringIndex'+str(j))!=(index+i['frames'])%length:return stop('roomFdnGeometryOrIndexChanged')
                    ring=words(i,'ring'+str(j)+'Word')
                    if ring is None or any(i.get(key+str(j)) is None for key in ('filterHistory','b0Word','a1Word')):return stop('roomFdnOperandsIncomplete')
                    rings.append(ring);history.append(i['filterHistory'+str(j)]);b0.append(i['b0Word'+str(j)]);a1.append(i['a1Word'+str(j)]);ranges.append((pointer,pointer+length*4));progress.append(dict(length=length,initialIndex=index,returnedIndex=f['ringIndex'+str(j)]))
                ranges.extend((p,p+i['frames']*4) for p in b['args'][1:3])
                if any(a<d and c<bb for n,(a,bb) in enumerate(ranges) for c,d in ranges[n+1:]):return stop('roomFdnStorageOverlaps')
                if b['spanBytes']!=16 or r['spanBytes']!=16 or words(f,'inputWord')!=input_words:return stop('roomFdnOutputOrInputIncomplete')
                modes=fdn_prefix_modes([p['length'] for p in progress],[p['initialIndex'] for p in progress],i['frames'])
                before=list(struct.unpack('<4I',bytes.fromhex(b['spanHex'])));expected,_,_=fdn_prefix(rings,history,b0,a1,input_words,before,self.config['feedbackSumScale'],b['mxcsr'],modes);actual=list(struct.unpack('<4I',bytes.fromhex(r['spanHex'])))
                result.update(stateIndex=relative//layout['fdnStride'],scalarPrefixWords=modes,ringProgression=progress,ringWords=rings,filterHistory=history,b0Words=b0,a1Words=a1,beforePrefix=b['spanHex'],afterPrefix=r['spanHex'])
                status='exactRoomFdnPrefix' if expected==actual else 'roomFdnArithmeticMismatch'
            elif k=='roomWetDamping':
                relative=b['args'][0]-root['args'][0]-layout['dampingFirstState']
                if relative<0 or relative%layout['dampingStride'] or relative//layout['dampingStride']>=layout['dampingStateCount']:return stop('roomDampingStateNotOwnedByInstance')
                if any(i.get(key) is None for key in ('previousInput','previousOutput','poleBits','gainBits')) or any(i.get(key)!=f.get(key) for key in ('poleBits','gainBits')) or b['spanBytes']!=16 or r['spanBytes']!=16 or b['spanHex']!=hex_words(input_words):return stop('roomDampingOperandsIncomplete')
                expected,_,_=damping_prefix(input_words,i['previousInput'],i['previousOutput'],i['poleBits'],i['gainBits'],b['mxcsr']);actual=list(struct.unpack('<4I',bytes.fromhex(r['spanHex'])))
                if words(f,'inputWord')!=actual:return stop('roomDampingOutputIdentityDiffers')
                result.update(stateIndex=relative//layout['dampingStride'],gainBits=i['gainBits'],poleBits=i['poleBits'],previousInput=i['previousInput'],previousOutput=i['previousOutput'],beforePrefix=b['spanHex'],afterPrefix=r['spanHex'])
                status='exactRoomDampingPrefix' if expected==actual else 'roomDampingArithmeticMismatch'
            else:
                # The worker tests this byte against zero; live stereo instances
                # use 2. It also contributes to scratch-buffer allocation size.
                enabled=meta.get('earlyEnabled')
                if meta.get('earlyObject')!=b['args'][0] or type(enabled) is not int or not 0<enabled<256:return stop('roomEarlyStateNotOwnedByInstance')
                initial=decode_projection(b);final=decode_projection(r)
                for p,fields in [(initial,i),(final,f)]:
                    if any(p[key]!=fields.get(key) for key in ('length','ringPointer','ringIndex')) or [len(bank) for bank in p['banks']]!=[fields.get('leftCount'),fields.get('rightCount')]:return stop('roomEarlyProjectionMetadataDiffers')
                if any(initial[key]!=final[key] for key in ('length','ringPointer')) or final['ringIndex']!=(initial['ringIndex']+i['frames'])%initial['length']:return stop('roomEarlyGeometryOrIndexChanged')
                for a,bb in zip(initial['banks'],final['banks']):
                    if len(a)!=len(bb) or any(x['gainBits']!=y['gainBits'] or y['index']!=(x['index']+i['frames'])%initial['length'] for x,y in zip(a,bb)):return stop('roomEarlyTapProgressionDiffers')
                ranges=[(initial['ringPointer'],initial['ringPointer']+initial['length']*4)]+[(p,p+i['frames']*4) for p in b['args'][1:]]
                if any(a<d and c<bb for n,(a,bb) in enumerate(ranges) for c,d in ranges[n+1:]):return stop('roomEarlyStorageOverlaps')
                if words(f,'inputWord')!=input_words:return stop('roomEarlyInputChanged')
                expected=early_prefix(initial,input_words,b['mxcsr']);actual=[words(f,'leftWord'),words(f,'rightWord')]
                if any(v is None for v in actual):return stop('roomEarlyOutputIncomplete')
                result.update(outputs=r['args'][2:],projection=initial,beforePrefixes=[hex_words(words(i,'leftWord')),hex_words(words(i,'rightWord'))],afterPrefixes=[hex_words(v) for v in actual])
                status='exactRoomEarlyPrefixes' if expected==actual else 'roomEarlyArithmeticMismatch'
        except (UnsupportedArithmetic,ValueError) as error:return stop(str(error))
        result.update(inputWords=input_words,expected=expected,actual=actual,nonzeroPrefix=any(w&0x7fffffff for v in actual for w in v) if k=='roomEarlyReflectionKernel' else any(w&0x7fffffff for w in actual))
        return stop(status)

    def completed(self,b,r,i,f,pending,ancestor,room,input_observer,*,closed):
        k=r['hook'].rsplit('.',1)[-1]
        if k=='roomVerbExecute':
            stable=closed and r['phase']==2 and all(i.get(key) is not None and i[key]==f.get(key) for key in ('fdnArray','fdnCount','earlyObject','earlyEnabled'))
            for row in self.by_room.pop((r['windowId'],r['captureId']),[]):row['ownershipStableAtRoomReturn']=stable
            return
        if k not in KINDS:return
        producer=self.inputs.pop((r['windowId'],r['captureId']),None);root=ancestor(r,pending,'roomVerbExecute');scope=room.instances.get((r['windowId'],root['captureId'])) if root else None
        if not scope or not scope['admitted']:self.counts['roomWetInstanceNotSelected']+=1;return
        result=self.compare(b,r,i,f,scope,closed);result.update(windowId=r['windowId'],roomCaptureId=root['captureId'],taskCaptureId=scope['taskCaptureId'],threadId=r['threadId'],wholeEventToDeviceClaim=False)
        result['producerPrefixCandidate']=dict(producer) if producer and producer['returnSequence']<b['sequence'] and result.get('inputWords') and producer['afterPrefix']==hex_words(result['inputWords']) else None
        self.counts[result['status']]+=1
        if len(self.rows)<LIMIT:
            result['ownershipStableAtRoomReturn']=False;self.rows.append(result);self.by_room.setdefault((r['windowId'],root['captureId']),[]).append(result)
        else:self.counts['reportRowsOmitted']+=1
        if result['status'] in ('exactRoomFdnPrefix','exactRoomDampingPrefix','exactRoomEarlyPrefixes'):
            stages=input_observer.stages.setdefault((r['windowId'],root['captureId']),{})
            outputs=list(zip(result['outputs'],result['afterPrefixes'])) if k=='roomEarlyReflectionKernel' else [(result['output'],result['afterPrefix'])]
            for pointer,prefix in outputs:stages[pointer]=dict(captureId=r['captureId'],kind=k,returnSequence=r['sequence'],afterPrefix=prefix)

    def publish(self,diagnostics,room_result,history_result=None):
        rows=[] if diagnostics else self.rows;roots={(r['windowId'],r['roomCaptureId']):r for r in (room_result or {}).get('rows',())}
        for row in rows:
            root=roots.get((row['windowId'],row['roomCaptureId']));row['busProcessingNode']=root.get('busProcessingNode') if root and row['ownershipStableAtRoomReturn'] else None
        truncated=self.counts.get('reportRowsOmitted',0) or (history_result or {}).get('counts',{}).get('reportRowsOmitted',0)
        paths=ordered_wet_paths(rows,room_result,history_result) if not diagnostics and not truncated else dict(wetBlendPrefixLinks=[],fdnDampingPrefixChains=[])
        return dict(schema='endfield.audio-room-wet-witness.v2',rows=rows,counts=dict(self.counts),**paths,openCalls=len(self.inputs),openRoomReturns=len(self.by_room),diagnostics=list(diagnostics),wholeEventToDeviceClaim=False,evidenceBoundary='Original first-vector early taps, four feedback-prefix values with native vector/scalar segment selection, and four wet-damping values from observed operands and registered Room state ownership. Higher Room/bus attachment additionally requires unchanged instance-owned state metadata at normal Room return. Ordered prefix chains require original pointer, frame count, call order and sample equality; failed writers invalidate earlier candidates and truncated reports withhold chains. These joins do not reconstruct full live history or isolate an Event contribution. Early-reflection scalar/remainder paths, authored coefficient derivation and whole buffers remain separate.')
