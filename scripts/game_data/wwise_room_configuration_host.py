"""Original Room configuration on bounded owned buffers, without engine Init.

The caller supplies three selected native paths and a byte-identical private
AkSoundEngine copy. No game process is opened. Live parameter bytes supply only
values; their foreign vtable pointer is replaced by the private validated one.
"""
from __future__ import annotations
import ctypes
import hashlib
import math
import struct
from pathlib import Path
from scripts.game_data.wwise_room_configuration_native import load_validated
from scripts.game_data.wwise_room_wet_native import load_contract as load_wet
from scripts.game_data.wwise_room_history_native import load_contract as load_history


class RoomHostError(ValueError):pass


class OwnedAllocator:
    def __init__(self):
        self.live={};self.keep=[];self.used=0;self.errors=[]
        p=ctypes.c_void_p;q=ctypes.c_uint64;u=ctypes.c_uint32
        def allocate(size,alignment):
            if not 0<size<=4<<20 or self.used+size>64<<20 or len(self.keep)>=4096 or not 16<=alignment<=4096 or alignment&(alignment-1):self.errors.append('owned allocation bound');return None
            storage=ctypes.create_string_buffer(size+alignment);pointer=(ctypes.addressof(storage)+alignment-1)&~(alignment-1);self.live[pointer]=(storage,size);self.keep.append(storage);self.used+=size;return pointer
        @ctypes.CFUNCTYPE(p,p,q,p,u)
        def ordinary(this,size,file,line):return allocate(size,16)
        @ctypes.CFUNCTYPE(p,p,q,u,p,u)
        def aligned(this,size,alignment,file,line):return allocate(size,alignment)
        @ctypes.CFUNCTYPE(None,p,p)
        def free(this,pointer):
            if pointer and pointer not in self.live:self.errors.append('foreign or repeated owned free')
            if pointer in self.live:self.live.pop(pointer)
        @ctypes.CFUNCTYPE(None,p)
        def destructor(this):self.errors.append('unexpected allocator destructor')
        self.callbacks=(destructor,ordinary,free,aligned);self.table=(q*len(self.callbacks))(*(ctypes.cast(f,p).value for f in self.callbacks));self.object=(q*1)(ctypes.addressof(self.table))

    def read(self,pointer,size):
        if not any(base<=pointer and pointer+size<=base+n for base,(_,n) in self.live.items()):raise RoomHostError('configuration read outside owned live storage')
        return ctypes.string_at(pointer,size)

    def close(self):
        self.callbacks=();self.table=None;self.object=None;self.keep.clear()


class OriginalRoomConfiguration:
    def __init__(self,*,gameassembly,metadata,ak_sound_engine,original_ak):
        c,audit=load_validated(gameassembly=gameassembly,metadata=metadata,ak_sound_engine=ak_sound_engine)
        if c is None:raise RoomHostError('configuration native gate '+audit['status']+': '+audit['detail'])
        if original_ak is None or not Path(original_ak).is_file():raise RoomHostError('explicit private original DLL copy required')
        if hashlib.sha256(Path(original_ak).read_bytes()).hexdigest()!=c['nativeInputs']['akSoundEngineSha256'].casefold():raise RoomHostError('private original DLL differs from selected native input')
        self.contract=c;self.audit=audit;self.wet=load_wet();self.history=load_history()
        if any(owner['nativeInputs']!=c['nativeInputs'] for owner in (self.wet,self.history)):raise RoomHostError('configuration state owners differ from selected inputs')
        if not hasattr(ctypes,'WinDLL'):raise RoomHostError('original configuration requires Windows x64')
        self.dll=ctypes.WinDLL(str(Path(original_ak).resolve()));self.base=self.dll._handle;p=ctypes.c_void_p;u=ctypes.c_uint32;sites=audit['nativeEntryRvas']
        self.factory=ctypes.CFUNCTYPE(p,p)(self.base+int(sites['roomVerbFactory'],16))
        self.initialize=ctypes.CFUNCTYPE(u,p,p,p,p,p)(self.base+int(sites['roomEffectInitialize'],16))
        self.reset=ctypes.CFUNCTYPE(u,p)(self.base+int(sites['roomEffectReset'],16))
        self.terminate=ctypes.CFUNCTYPE(u,p,p)(self.base+int(sites['roomEffectTerminate'],16))

    def derive(self,parameter_hex,sample_rate,format_word):
        c=self.contract;l=c['layout'];w=self.wet['layout'];h=self.history['layout'];raw=bytes.fromhex(parameter_hex)
        if len(raw)!=c['parameterProjection']['byteExtent'] or type(sample_rate) is not int or not 8000<=sample_rate<=192000 or format_word!=12546:raise RoomHostError('configuration parameter/rate/standard-stereo extent not selected')
        def value(offset,fmt):return struct.unpack_from(fmt,raw,offset)[0]
        if value(l['parameterQuality'],'<I') not in range(2,17,2) or value(l['parameterPattern'],'<I')>30 or any(value(offset,'<B') not in (0,1) for offset in (l['parameterToneEnabled'],l['parameterEarlyEnabled'])):raise RoomHostError('configuration quality/pattern/enable not selected')
        if any(not math.isfinite(value(offset,'<f')) for offset in l['parameterFloatOffsets']):raise RoomHostError('configuration nonfinite parameter not selected')
        if value(l['parameterDecay'],'<f')<=0:raise RoomHostError('configuration decay must be positive')
        if any(value(offset,'<I')>3 for offset in l['parameterToneInsertOffsets']) or any(value(offset,'<I')>8 for offset in l['parameterToneCurveOffsets']):raise RoomHostError('configuration tone enum not selected')
        parameters=ctypes.create_string_buffer(raw,len(raw));ctypes.memmove(ctypes.addressof(parameters),struct.pack('<Q',self.base+int(self.audit['parameterVtableRva'],16)),8)
        format_data=ctypes.create_string_buffer(struct.pack('<II',sample_rate,format_word),16);allocator=OwnedAllocator()
        try:instance=self.factory(allocator.object)
        except (OSError,ValueError):allocator.close();raise
        if not instance:
            allocator.close();raise RoomHostError('original Room factory allocation failed')
        def read(pointer,offset,fmt):return struct.unpack(fmt,allocator.read(pointer+offset,struct.calcsize(fmt)))[0]
        def ring(pointer):return dict(length=read(pointer,l['ringLength'],'<I'),index=read(pointer,l['ringIndex'],'<I'))
        try:
            if self.initialize(instance,allocator.object,None,parameters,format_data)!=1 or allocator.errors:raise RoomHostError('original Room initialization failed: '+','.join(allocator.errors))
            count=read(instance,l['fdnCount'],'<I');array=read(instance,l['fdnArray'],'<Q');networks=[]
            if count not in range(2,17,2):raise RoomHostError('original FDN count not selected')
            allocator.read(array,count*l['fdnStride'])
            for j in range(count):
                state=array+j*l['fdnStride'];networks.append(dict(stateIndex=j,ringLengths=[ring(state+k*w['ringHeaderStride'])['length'] for k in range(4)],b0Words=[read(state,w['fdnB0']+k*w['fdnFilterStride'],'<I') for k in range(4)],a1Words=[read(state,w['fdnA1']+k*w['fdnFilterStride'],'<I') for k in range(4)],preDelayLength=ring(state+l['fdnPreDelay'])['length']))
            early_pointer=read(instance,l['earlyObject'],'<Q');early=None
            if early_pointer:
                counts=[read(early_pointer,w[key],'<H') for key in ('earlyLeftCount','earlyRightCount')]
                if any(n>64 for n in counts):raise RoomHostError('original early tap count outside stored banks')
                early=dict(length=ring(early_pointer)['length'],banks=[[dict(gainBits=read(early_pointer,w['earlyLeftCoefficients' if bank==0 else 'earlyRightCoefficients']+j*4,'<I'),initialIndex=read(early_pointer,w['earlyLeftIndices' if bank==0 else 'earlyRightIndices']+j*2,'<H')) for j in range(n)] for bank,n in enumerate(counts)])
            tone=[];tone_count=read(instance,l['toneCount'],'<B');tone_array=read(instance,l['toneArray'],'<Q')
            if tone_count>6:raise RoomHostError('original tone slot count not selected')
            for j in range(tone_count):
                state=tone_array+j*l['toneStride'];tone.append(dict(mode=read(state,l['toneMode'],'<I'),matrixWords=list(struct.unpack('<'+str(h['toneMatrixWords'])+'I',allocator.read(state-h['toneMatrixHistoryOffset'],h['toneMatrixWords']*4)))))
            return dict(schema='endfield.room-original-derived-configuration.v2',inputDelayLengths={role:ring(instance+offset)['length'] for role,offset in self.audit['inputDelayOffsets'].items()},fdnCount=count,networks=networks,early=early,diffusion=[dict(stateIndex=j,length=ring(instance+h['diffusionFirstState']+j*h['diffusionStateStride'])['length'],gainBits=read(instance,h['diffusionFirstState']+j*h['diffusionStateStride']+h['diffusionGain'],'<I')) for j in range(h['diffusionStateCount'])],dampingPoleBits=read(instance,l['dampingPole'],'<I'),toneSlots=tone,engineInitialized=False,liveHistoryClaim=False)
        finally:
            result=self.terminate(instance,allocator.object)
            failed=result!=1 or allocator.live or allocator.errors
            allocator.close()
            if failed:raise RoomHostError('original configuration cleanup incomplete')
