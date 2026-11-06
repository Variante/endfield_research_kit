"""Current native-gated complete MontageNew fields and bounded positive lists."""
import hashlib,math,struct
from contextlib import contextmanager
from pathlib import Path
from scripts.game_data import npc_montage_native as native
from scripts.game_data.levelscript_reader_inputs import snapshot_complete_reader_inputs,snapshot_string_pool_inputs,reader_input_changes
from scripts.game_data.string_pool import StringPool,resolve_string_pool_index

NPC_MONTAGE_RELATIVE_PREFIX='Data/Json/NPC/MontageJson/MontageNew/'

class NpcMontageFramingError(ValueError):
 def __init__(self,detail,*,gate='frame',field=None,offset=None,expected=None,actual=None):
  self.diagnostics=dict(validator='npcMontage',gate=gate,field=field,offset=offset,expected=expected,actual=actual)
  super().__init__(f'npcMontage.{gate}: field={field} offset={offset} expected={expected!r} actual={actual!r}; {str(detail)[:1000]}')

def is_npc_montage_memorypack_path(path):
 normalized='/'+str(path).replace('\\','/').lstrip('/').casefold()
 return '/'+NPC_MONTAGE_RELATIVE_PREFIX.casefold() in normalized and normalized.endswith('.json')

class _Reader:
 def __init__(self,data,strings,proof):
  self.data,self.strings,self.proof,self.offset,self.fields,self.collections=data,strings,proof,0,[],[]
  self.remaining=16384
 def take(self,size,field):
  at=self.offset
  if size<0 or at+size>len(self.data):raise NpcMontageFramingError('incomplete field',gate='truncated',field=field,offset=at,expected=size,actual=len(self.data)-at)
  self.offset+=size;return self.data[at:self.offset]
 def scalar(self,fmt,field):
  value=struct.unpack('<'+fmt,self.take(struct.calcsize('<'+fmt),field))[0]
  if fmt=='f' and not math.isfinite(value):raise NpcMontageFramingError('finite stored-value subset required',gate='nonfinite',field=field,offset=self.offset-4,actual=str(value))
  return value
 def value(self,row,path):
  wire,name=row['wire'],row['type']
  if wire in ('i32','i64','f32','bool'):return self.scalar({'i32':'i','i64':'q','f32':'f','bool':'B'}[wire],path) if wire!='bool' else bool(self.scalar('B',path))
  if wire=='pool':return resolve_string_pool_index(self.scalar('i',path),self.strings,path)
  if wire=='record':return self.record(name,path)
  if wire=='vector3':
   values=list(struct.unpack('<3f',self.take(12,path)))
   if not all(math.isfinite(v)for v in values):raise NpcMontageFramingError('finite stored-value subset required',gate='nonfinite',field=path,offset=self.offset-12)
   return values
  if wire in('reference-list','value-list'):
   cap=self.proof['layout'].get('completeCollections',{})
   if(cap.get('schema')!='endfield.npc-montage-complete-collections.v1'or cap.get('wholeGrammarAdmitted')is not True
      or cap.get('countRange')!=[-1,4096]or row.get('countLimit')!=4096 or row.get('elementType')not in self.proof['layout']['records']):
    raise NpcMontageFramingError('own complete native child/list proof required',gate='collection-proof',field=path,offset=self.offset)
   at=self.offset;count=self.scalar('i',path+'.count');self.collections.append(dict(field=path,offset=at,count=count))
   if not -1<=count<=4096:raise NpcMontageFramingError('bounded signed collection count required',gate='collection-count',field=path,offset=at,expected=[-1,4096],actual=count)
   if count==-1:return None
   if count>self.remaining:raise NpcMontageFramingError('whole-root node budget exceeded',gate='node-budget',field=path,offset=at,expected=self.remaining,actual=count)
   return[self.record(row['elementType'],path+f'[{i}]',value_default=wire=='value-list')for i in range(count)]
  if wire=='null-empty-list':
   at=self.offset;count=self.scalar('i',path+'.count');self.collections.append(dict(field=path,offset=at,count=count))
   if count not in (-1,0):raise NpcMontageFramingError('positive elements remain unproved for this current sparse profile',gate='collection-elements-unproved',field=path,offset=at,expected=[-1,0],actual=count)
   return None if count==-1 else []
  if wire.startswith('raw'):
   size=int(wire[3:]);raw=self.take(size,path);out=dict(rawHex=raw.hex().upper(),storedBytes=size)
   layout=next((r for r in self.proof['rawValues'] if r['type']==name),None)
   if layout:
    values={}
    for field,kind,at in layout['fields']:
     if kind=='UnityEngine.Vector3':value=list(struct.unpack_from('<3f',raw,at))
     else:value=struct.unpack_from('<'+{'System.Int64':'q','System.Single':'f','System.Boolean':'B'}[kind],raw,at)[0]
     if kind=='System.Boolean':value=bool(value)
     if any(isinstance(v,float) and not math.isfinite(v) for v in (value if isinstance(value,list) else [value])):raise NpcMontageFramingError('finite stored-value subset required',gate='nonfinite',field=path+'.'+field,offset=self.offset-size+at)
     values[field]=value
    out['fields']=values
   return out
  raise NpcMontageFramingError('native layout has no supported wire',gate='layout',field=path,offset=self.offset,actual=wire)
 def record(self,name,path,*,value_default=False):
  if self.remaining<=0:raise NpcMontageFramingError('whole-root node budget exceeded',gate='node-budget',field=path,offset=self.offset)
  self.remaining-=1
  rows=self.proof['layout']['records'][name];at=self.offset;count=self.scalar('B',path+'.memberCount')
  if count==255:
   if not value_default:return None
   cap=self.proof['layout'].get('completeCollections',{});child=cap.get('transitionChild',{})
   if cap.get('transitionNullReturnsDefaultValue')is not True or child.get('typeName')!=name or child.get('nullReturnsDefaultValue')is not True:
    raise NpcMontageFramingError('own value-default proof required',gate='value-default',field=path,offset=at)
   return{r['name']:0.0 if r['wire']=='f32'else 0 for r in rows}
  if count!=len(rows):raise NpcMontageFramingError('object member count changed',gate='member-count',field=path,offset=at,expected=len(rows),actual=count)
  out={}
  for row in rows:
   start=self.offset;field=path+'.'+row['name'];out[row['name']]=self.value(row,field);self.fields.append(dict(field=field,startOffset=start,endOffset=self.offset,type=row['type']))
  return out

def _frame(data,strings,proof):
 reader=_Reader(data,strings,proof);root=reader.record(proof['layout']['root'],'root')
 if reader.offset!=len(data):raise NpcMontageFramingError('physical EOF not reached',gate='trailing-bytes',offset=reader.offset,expected=len(data),actual=reader.offset)
 body=(root or {}).get('data');values=body or {};clip=values.get('clipInfo');deco=values.get('decoEntities');dynamic=values.get('dynamicEntities');overrides=values.get('montageOverrideTransitions')
 complete=proof['layout'].get('completeCollections',{}).get('wholeGrammarAdmitted')is True
 return dict(status='exact_current_npc_montage_complete_frame'if complete else'exact_current_npc_montage_sparse_frame',schemaStatus='named_exact',wholeSchemaExact=complete,physicalEOF=True,bytesConsumed=reader.offset,root=root,data=body,clipInfo=clip,animType=(root or {}).get('animType'),tag=(root or {}).get('tag'),frameRate=values.get('frameRate'),decoEntityCount=0 if deco is None else len(deco),dynamicEntityCount=0 if dynamic is None else len(dynamic),transitionOverrideCount=0 if overrides is None else len(overrides),fieldSpans=reader.fields,collections=reader.collections,nativeInputs=proof['nativeInputs'],evidenceBoundary=proof['evidenceBoundary'])

def _native_error(proof,gate):
 return NpcMontageFramingError(proof.get('detail') or proof.get('failedCheck') or 'native proof unavailable',gate=gate,expected='validated',actual=proof.get('status'))

@contextmanager
def montage_decoder(*,strings,game_root=None):
 """One lexical read operation, freshly proved and bookended; no success cache."""
 if not isinstance(strings,StringPool):raise NpcMontageFramingError('selected matching StringPool required',gate='string-pool-required')
 sources=snapshot_complete_reader_inputs();pool=snapshot_string_pool_inputs(Path(strings.root).parent)
 try:strings=StringPool(strings.root)
 except (OSError,ValueError) as error:raise NpcMontageFramingError(str(error),gate='string-pool-invalid',actual=str(strings.root)) from error
 proof=native.validate(game_root=game_root)
 if proof.get('status')!='validated':raise _native_error(proof,'native-enter')
 active=True;counts=dict(attempted=0,closed=0,failed=0)
 def decode(data):
  if not active:raise NpcMontageFramingError('decoder operation is closed',gate='operation-closed')
  counts['attempted']+=1
  try:
   value=_frame(data,strings,proof);counts['closed']+=1;return value
  except ValueError as error:
   counts['failed']+=1
   if isinstance(error,NpcMontageFramingError):error.diagnostics['sourceSha256']=hashlib.sha256(data).hexdigest().upper();raise
   raise NpcMontageFramingError(str(error),gate='value',offset=None,actual=type(error).__name__) from error
 try:yield decode
 finally:
  active=False;selected=proof['nativeSources'];after=native.validate(gameassembly=Path(selected['GameAssembly.dll']),metadata=Path(selected['global-metadata.dat']))
  if after.get('status')!='validated':raise _native_error(after,'native-exit')
  if (proof['nativeInputs'],proof['nativeSources'],proof['layout'],proof['rawValues'])!=(after['nativeInputs'],after['nativeSources'],after['layout'],after['rawValues']):raise NpcMontageFramingError('selected native proof changed',gate='native-drift')
  changed=snapshot_complete_reader_inputs()
  if sources!=changed:raise NpcMontageFramingError(str(reader_input_changes(sources,changed)),gate='reader-source-drift')
  if pool!=snapshot_string_pool_inputs(Path(strings.root).parent):raise NpcMontageFramingError('selected StringPool pages changed',gate='string-pool-drift')
  decode.receipt=dict(schema='endfield.complete-npc-montage-operation.v1',
   nativeInputs=proof['nativeInputs'],nativeSources=proof['nativeSources'],
   completeGrammarAdmitted=proof['layout'].get('completeCollections',{}).get('wholeGrammarAdmitted')is True,
   nativeSourcePoolExitBookendsPassed=True,physicalEOFRequired=True,sourceCounts=dict(counts),
   allAttemptedOwnersClosed=counts['failed']==0 and counts['attempted']==counts['closed'],runtimeAnimationProved=False)

def frame_npc_montage(data,*,strings=None,game_root=None):
 with montage_decoder(strings=strings,game_root=game_root) as decode:return decode(data)

def decode_npc_montage_memorypack(path,data,size=None,*,strings=None,game_root=None):
 if not is_npc_montage_memorypack_path(path):return None
 if size is not None and size!=len(data):raise NpcMontageFramingError('outer size mismatch',gate='outer-size',expected=size,actual=len(data))
 framed=frame_npc_montage(data,strings=strings,game_root=game_root);clip=framed.get('clipInfo') or {}
 return dict(kind='memorypack-json',subtype='NPCMontageJson',summary='Current native-gated complete MontageNew; bounded positive collections; EOF',rows=1,keys=['clipName','animType','tag'],sample='clipName='+str(clip.get('name') or '<null-or-empty>'),decoded=framed)
