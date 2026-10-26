"""Actual selected byte-hash body for zero through127 input bytes.

The named data-path caller does not choose an algorithm by its class name.
Actual scalar instructions and selected arithmetic callees determine the
result. A stable valid secret array of at least128 bytes, actual ready class,
and disjoint readable input are conditions, not observed runtime state.
Larger lengths and alternative hashing implementations remain unselected.
"""
import json
import hashlib
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

SCHEMA='endfield.story-patrol-byte-hash-source.v1'

def need(check,condition):
 if not condition:raise ValueError('storyPatrolByteHash.'+check)

def program(regions,entry,*,length):
 need('finite-selected-byte-length',type(length)is int and 0<=length<=127)
 g=BytesPath(regions,entry);calls=[];reads=[]
 def call(role):
  at=g.at;target=g.relative('e8');calls.append(dict(role=role,instructionVa=at,targetVa=target))
 def mul(data0,data1,secret0,secret1,*,first=False,tail=False):
  if first:
   g.take('488b5518','4c8d442430','488b4d10','4533c9','48335628','48334e20','4c897c2430')
  elif tail:
   g.take('488b542fe8','4c8d442478','488b4c2fe0','4533c9','48335638','488bd8','48334e30','4c897c2478')
  else:raise ValueError('storyPatrolByteHash.finite-pair-role')
  call('multiply128');reads.extend([[data0,data0+8],[data1,data1+8]])
 def higher():
  g.take('488b5528','4c8d442478','488b4d20','4533c9','48335648','48334e40','4c897c2478');call('multiply128')
  g.take('488d4dd0','4533c0','4803cf','488d5650','488bd8');call('mix16')
  reads.extend([[32,48],[length-48,length-32]])
  g.take('48335c2478','4c03f3','4c03f0');g.at=g.relative('e9')
 g.take('4055','57','4157','4883ec40');class_site=g.at;cls=g.relative('488b05')
 g.take('488bfa','488be9','83b8e000000000');g.branch('0f84',False)
 g.take('488b80b8000000','4533ff','4889742468','488b00','4885c0');g.branch('0f84',False)
 g.take('44397818');g.branch('0f84',False);g.branch('0f86',False)
 g.take('488d7020','4883ff10');g.branch('0f8c',length<16)
 if length>=16:
  g.take('4881ff80000000');g.branch('0f8d',False)
  g.take('48895c2460','48b8');prime=int.from_bytes(g.read(8),'little')
  g.take('4c89742470','4c8bf7','4c0faff0','4883ff20');g.branch('7e',length<=32,1)
  if length>32:
   g.take('4883ff40');g.branch('0f8f',length>64)
   if length>64:
    g.take('4883ff60');g.branch('0f8f',length>96)
    if length>96:
     g.take('488b5538','4c8d442478','488b4d30','4533c9','48335668','48334e60','4c897c2478');call('multiply128')
     g.take('488d4dc0','4533c0','4803cf','488d5670','488bd8');call('mix16')
     reads.extend([[48,64],[length-64,length-48]])
     g.take('48335c2478','4c03f3','4c03f0');g.at=g.relative('e9')
    higher()
   mul(16,24,32,40,first=True);mul(length-32,length-24,48,56,tail=True)
   g.take('48335c2430','4833442478','4c03f3','4c03f0')
  g.take('488b5608','4c8d442430','488b0e','4533c9','48335508','48334d00','4c897c2430');call('multiply128')
  g.take('488b542ff8','4c8d442478','488b4c2ff0','4533c9','48335618','488bd8','48334e10','4c897c2478');call('multiply128')
  reads.extend([[0,16],[length-16,length]])
  g.take('4833442478','48335c2430','498d0c06','4803cb');call('avalanche')
  g.take('4c8b742470','488b5c2460')
 else:
  prime=None;g.take('4883ff08');g.branch('7f',length>8,1)
  if length>8:
   g.take('4533c9','4c897c2420','4c8bc6','488bd7','488bcd');call('nineToFifteen');g.at=g.relative('e9')
   reads.extend([[0,8],[length-8,length]])
  else:
   g.take('4883ff04');g.branch('0f8c',length<4)
   if length>=4:
    g.take('8b4500','488bd7','8b4c2ffc','48c1e020','4803c8','48334e08','48334e10');call('fourToEight');g.at=g.relative('eb',1)
    reads.extend([[0,4],[length-4,length]])
   else:
    g.take('4885ff');g.branch('0f8e',length==0)
    if length:
     g.take('488bc7','48d1e8','0fb60c28','0fb64500','c1e108','0bc8','0fb6442fff','c1e108','0bcf','c1e108','480bc8',
      '8b4604','4833c8','8b06','4833c8');call('avalancheTwo');g.at=g.relative('e9')
     reads.extend([[0,1],[length//2,length//2+1],[length-1,length]])
    else:
     g.take('488b4e38','48334e40');call('avalancheTwo');g.take('90');g.at=g.relative('e9')
 g.take('488b742468','89442478','48c1e820','8944247c','488b442478','4883c440','415f','5f','5d','c3')
 need('every-selected-input-read-within-exact-length',all(0<=a<=b<=length for a,b in reads))
 return dict(selectedBytes=g.seen,entry=entry,length=length,classUsageInstructionVa=class_site,classCellVa=cls,
  calls=calls,mainLengthPrime=prime,inputReadRanges=reads,inputReadExtentProved=True,
  secretArrayRequiredNonnullAndLengthAtLeast=128,secretElementBytes=1,secretArrayDataOffset=32,secretAndInputRequiredStable=True,
  selectedLengthInZeroThrough127Required=True,resultReconstructedUnchangedFromBothDwords=True,
  entryRspRestored=True,allNonvolatilesRestored=True,normalReturn=True,actualSecretContentsOrIdentityObserved=False,
  calledArithmeticEffectsRequireIndependentSource=True)

def _arithmetic_parsers():
 from scripts.game_data.il2cpp import byte_hash_arithmetic as a
 return dict(multiply128=a.multiply128_program,avalanche=a.avalanche_program,fourToEight=a.four_to_eight_program,
  mix16=a.mix_sixteen_program,nineToFifteen=a.nine_to_fifteen_program,
  avalancheTwo=lambda r,e:a.avalanche_program(r,e,kind='two-multiply'),fold128=a.fold128_program)

def _arithmetic_children(program):
 result=[]
 for key,role in(('multiplyCall','multiply128'),('foldMultiplyCall','fold128'),('avalancheTail','avalanche')):
  if key in program:result.append((role,program[key]['targetVa']))
 return result

def derive(image,pins):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.memorypack import leveldata_patrol_hash_sources as parent,pointer_param as pointer
 _publication_gate(image,pins);base=image.pe.image_base;source=parent.derive(image,pins);data=source['proof']['pathSource']['proof']['dataHashSource']
 candidates=[]
 for row in data['rows']:
  raw=bytes.fromhex(row['bytes']);at=int(row['va'],16)
  if len(raw)==5 and raw[0]==0xe8 and image.pe.bytes_at_va(at-6,6)==bytes.fromhex('4863d04533c0'):
   candidates.append((at,raw,at+5+int.from_bytes(raw[1:],'little',signed=True)))
 need('one-owned-byte-buffer-count-and-hash-call',len(candidates)==1);at,raw,target=candidates[0]
 byte_map={a+i:v for a,h in data['sourceRegions']for i,v in enumerate(bytes.fromhex(h))}
 need('complete-actual-call-in-owned-parent',all(byte_map.get(at+i)==v for i,v in enumerate(raw)))
 b=pointer.owned(image,target);programs=[program(b['regions'],target,length=n)for n in range(128)]
 parsers=_arithmetic_parsers();arithmetic={};pending=[(c['role'],c['targetVa'])for p in programs for c in p['calls']]
 while pending:
  kind,entry=pending.pop();key=str(entry-base)
  if key in arithmetic:need('same-actual-arithmetic-role',arithmetic[key]['kind']==kind);continue
  prefix=image.pe.bytes_at_va(entry,128);p=parsers[kind]([(entry,prefix)],entry);span=p['nextInstructionVa']-entry
  need('finite-complete-selected-arithmetic-span',0<span<=128);selected=prefix[:span]
  arithmetic[key]=dict(kind=kind,entryRva=entry-base,sourceWindows=[dict(startRva=entry-base,endRva=entry-base+span,
   sha256=hashlib.sha256(selected).hexdigest().upper())],sourceRegions=[[entry,selected.hex()]],program=p,physicalFunctionExtentProved=False)
  pending.extend(_arithmetic_children(p))
 usage=derive_typed_usage_context(image,programs[0]['classUsageInstructionVa']-base,label='storyPatrolByteHash.actualClass')
 need('actual-byte-hash-class-usage',usage.get('tag')==1)
 result=json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-byte-hash-zero-through127-source',nativeInputs=pins,
  proof=dict(imageBase=base,pathHashSource=source,actualHashCall=[at-base,raw.hex().upper()],hashTargetRva=target-base,
   sourceWindows=b['windows'],sourceRegions=[[a,h.hex()]for a,h in b['regions']],programs=programs,
   actualClassUsage=usage,arithmeticSources=arithmetic),
  selectedByteHashArithmeticAndReadExtentsProved=True,finiteByteLengthDomain=[0,127],
  byteHashNameOrCanonicalAliasClaimed=False,actualSecretContentsOrIdentityObserved=False,
  dataPathEncodingEffectsProved=False,runtimeInvocationObserved=False,playbackProved=False,
  evidenceBoundary=dict(exact='Actual full hash body and every selected length0..127 path/read extent, complete current scalar multiply/fold/rotation/avalanche leaves and unchanged64-bit result/full frames.',
   conditional=__doc__,unresolved=['Actual encoding callback/output bytes and stable secret-array identity/contents','Input lengths128 and above and other hash/initialization alternatives','Actual resource index key/asset/runtime identity']))))
 validate(result,pins);_publication_gate(image,pins);return result

def validate(source,pins):
 need('same-source-envelope',source.get('schema')==SCHEMA and source.get('status')=='validated-conditional-byte-hash-zero-through127-source'
  and source.get('nativeInputs')==pins and source.get('finiteByteLengthDomain')==[0,127]
  and source.get('selectedByteHashArithmeticAndReadExtentsProved')is True and all(source.get(k)is False for k in
   ('byteHashNameOrCanonicalAliasClaimed','actualSecretContentsOrIdentityObserved','dataPathEncodingEffectsProved','runtimeInvocationObserved','playbackProved')))
 p=source['proof'];base=p['imageBase']
 def regions(packet):
  windows=packet['sourceWindows'];items=packet['sourceRegions'];need('same-owned-source-window-set',bool(windows)and len(windows)==len(items))
  for w,(a,h)in zip(windows,items):
   raw=bytes.fromhex(h);need('all-source-bytes-authenticated',w==dict(startRva=a-base,endRva=a-base+len(raw),sha256=hashlib.sha256(raw).hexdigest().upper()))
  return [(a,bytes.fromhex(h))for a,h in items]
 actual=[program(regions(p),base+p['hashTargetRva'],length=n)for n in range(128)]
 need('all-selected-lengths-replay',json.loads(json.dumps(actual))==p['programs'])
 data=p['pathHashSource']['proof']['pathSource']['proof']['dataHashSource'];at=base+p['actualHashCall'][0];raw=bytes.fromhex(p['actualHashCall'][1])
 byte_map={a+i:v for a,h in data['sourceRegions']for i,v in enumerate(bytes.fromhex(h))}
 need('same-native-parent-and-actual-call',p['pathHashSource']['nativeInputs']==pins and len(raw)==5 and raw[0]==0xe8 and
  all(byte_map.get(at+i)==v for i,v in enumerate(raw))and at+5+int.from_bytes(raw[1:],'little',signed=True)==base+p['hashTargetRva'])
 u=p['actualClassUsage'];need('own-class-context-site',u['tag']==1 and all(q['classUsageInstructionVa']==base+u['instructionRva']and
  q['classCellVa']==base+u['usageCellRva']for q in actual))
 parsers=_arithmetic_parsers();sources=p['arithmeticSources'];needed={(c['role'],c['targetVa'])for q in actual for c in q['calls']};seen=set()
 while needed:
  kind,entry=needed.pop();key=str(entry-base)
  if (kind,entry)in seen:continue
  seen.add((kind,entry));packet=sources[key];need('exact-actual-arithmetic-entry-kind',packet['kind']==kind and packet['entryRva']==entry-base and packet['physicalFunctionExtentProved']is False)
  replay=parsers[kind](regions(packet),entry)
  need('whole-declared-arithmetic-span',len(packet['sourceRegions'])==1 and packet['sourceRegions'][0][0]==entry and
   len(bytes.fromhex(packet['sourceRegions'][0][1]))==replay['nextInstructionVa']-entry)
  need('all-actual-arithmetic-replays',json.loads(json.dumps(replay))==packet['program'])
  needed.update(_arithmetic_children(replay))
 need('no-unused-arithmetic-identity',{str(entry-base)for _,entry in seen}==set(sources))
 return dict(selectedByteHashArithmeticAndReadExtentsProved=True,finiteByteLengthDomain=[0,127],
  actualSecretContentsOrIdentityObserved=False,dataPathEncodingEffectsProved=False,runtimeInvocationObserved=False)
