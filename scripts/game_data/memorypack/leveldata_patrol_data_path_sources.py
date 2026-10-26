"""Selected small-buffer data-path encoding and byte-hash caller effects.

This owns caller control, actual requests, byte-array/count arguments, low32
duplication and restored frames. Pool/encoding/disposal callback effects and
their actual runtime identities stay separate. The selected normal domain
requires compatible ready contexts, positive cached threshold/capacity and
normally returning exact callbacks with valid disjoint buffer/count results.
"""
import json
import hashlib
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

SCHEMA='endfield.story-patrol-data-path-source.v1'

def need(check,condition):
 if not condition:raise ValueError('storyPatrolDataPath.'+check)

def program(regions,entry,*,nonnull=True,nonempty=True):
 need('finite-normal-string-domain',type(nonnull)is bool and type(nonempty)is bool and(nonnull or not nonempty))
 g=BytesPath(regions,entry);calls=[];uses=[]
 def call(role):
  at=g.at;target=g.relative('e8');calls.append(dict(role=role,instructionVa=at,targetVa=target));return target
 def use(prefix,role):
  at=g.at;cell=g.relative(prefix);uses.append(dict(role=role,instructionVa=at,cellVa=cell));return cell
 g.take('48895c2408','4889742410','57','4156','4157','4881ec90000000','488bf9');root=g.relative('488b05')
 g.take('488b8898000000','4885c9');g.branch('74',True,1)
 g.take('33db','48899c24c0000000','48895c2440','48899c24c8000000','4885ff');g.branch('0f84',not nonnull)
 if nonnull:
  g.take('395f10');g.branch('0f86',not nonempty)
 if nonnull and nonempty:
  g.take('48895c2448','8b7710');threshold=use('488b05','thresholdClass');g.take('3998e0000000');g.branch('75',True,1)
  g.take('488b80b8000000','3b7008');g.branch('0f8f',False)
  use('488b0d','poolClass');g.take('3999e0000000');g.branch('75',True,1)
  context=use('488b35','poolContext');g.take('488b4e20');ready=call('readyContext')
  g.take('33d2','488b88c0000000');indexed=call('indexedContext');g.take('3998e0000000');g.branch('75',True,1)
  g.take('488b4e20');need('same-ready-context-helper',call('readyContext')==ready)
  g.take('33d2','488b88c0000000');need('same-indexed-context-helper',call('indexedContext')==indexed)
  g.take('488b88b8000000','488b31','4889742440')
  need('same-threshold-class-cell',use('488b05','thresholdClass')==threshold);g.take('3998e0000000');g.branch('75',True,1)
  g.take('488b80b8000000','448b700c','4885f6');g.branch('0f84',False)
  g.take('488b0e');prepare=call('preparePoolClass')
  g.take('4c8b06','498b8080010000','4d8b8088010000','418bd6','488bce')
  pool_site=g.at;g.take('ffd0','48898424c8000000','48895c2470','488d442440','4889442478',
   '488d8424c8000000','4889842480000000','33c9');encoding_getter=call('getEncoding')
  g.take('488bf0','448b7710','4c8bbc24c8000000','4885c0');g.branch('0f84',False)
  g.take('488b08');need('same-encoding-preparation-helper',call('prepareEncodingClass')==prepare)
  g.take('488b06','4c8b9080020000','488b8088020000','4889442430','895c2428','4c897c2420',
   '458bce','4533c0','488bd7','488bce');encode_site=g.at;g.take('41ffd2')
  g.take('48895c2460','488d8c24c0000000','48894c2468','488b8c24c8000000','48898c24c0000000','4885c9');g.branch('74',False,1)
  g.take('83791800');g.branch('74',False,1);g.branch('0f86',False)
  g.take('4883c120');g.at=g.relative('eb',1)
  g.take('4863d0','4533c0');hash_target=call('byteHash')
  g.take('488bf8','48b9');mask=int.from_bytes(g.read(8),'little');need('literal-upper-half-preservation-mask',mask==0xffffffff00000000)
  g.take('4823f9','8bc8','4803f9','48897c2448','48899c24c0000000','488d4c2478');dispose=call('disposeBufferGuard');g.at=g.relative('e9')
  g.take('488bc7');g.at=g.relative('eb',1)
 else:
  pool_site=encode_site=context=encoding_getter=hash_target=dispose=None;g.take('33c0')
 g.take('4c8d9c2490000000','498b5b20','498b7328','498be3','415f','415e','5f','c3')
 return dict(selectedBytes=g.seen,entry=entry,inputNonnull=nonnull,inputNonempty=nonempty,replacementRootCell=root,
  selectedReplacementReceiverAt152RequiredNull=True,classAndMethodUsages=uses,calls=calls,
  selectedInputLengthAtMostCachedThresholdRequired=nonnull and nonempty,thresholdStaticOffset=8,rentSizeStaticOffset=12,
  poolContextCellVa=context,poolRentInstructionVa=pool_site,poolRentCallbackClassOffset=384,poolRentMethodInfoClassOffset=392,
  encodingGetterTargetVa=encoding_getter,encodingInstructionVa=encode_site,encodingCallbackClassOffset=640,encodingMethodInfoClassOffset=648,
  encodingArguments=dict(receiver='same actual getEncoding result',string='unchanged incoming string',stringIndex=0,
   stringCount='incoming string length',byteArray='same actual Rent result',byteIndex=0),
  hashTargetVa=hash_target,hashArguments=dict(pointer='same nonempty returned buffer+32',count='sign-extended exact encoding EAX',thirdArgument=0),
  validEncodedCountInZeroThrough127AndWithinBufferRequired=nonnull and nonempty,
  resultEffect='zero64'if not(nonnull and nonempty)else'low32(hashResult) repeated into both DWORD lanes',
  normalGuardDisposeArguments='same guard at RSP120 contains actual pool and address of actual byte buffer',
  entryRspRestored=True,allNonvolatilesRestored=True,normalReturn=True,
  poolEncodingAndDisposalEffectsProved=False,actualRuntimeCallbacksOrBuffersObserved=False)

def derive(image,pins):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.il2cpp import ready_context_sources
 from scripts.game_data.memorypack import leveldata_patrol_byte_hash_sources as byte_hash,pointer_param as pointer
 from scripts.game_data.memorypack import leveldata_patrol_class_preparation_sources as prepare
 _publication_gate(image,pins);base=image.pe.image_base;source=byte_hash.derive(image,pins)
 data=source['proof']['pathHashSource']['proof']['pathSource']['proof']['dataHashSource'];body=pointer.owned(image,base+data['entryRva'])
 programs=[program(body['regions'],body['pointer'],nonnull=n,nonempty=e)for n,e in((False,False),(True,False),(True,True))]
 contexts={};children={};p=programs[-1]
 for u in p['classAndMethodUsages']:
  key=str(u['instructionVa']-base);contexts[key]=derive_typed_usage_context(image,u['instructionVa']-base,label='storyPatrolDataPath.'+u['role'])
 for c in p['calls']:
  if c['role']=='byteHash':need('same-independent-byte-hash-target',c['targetVa']-base==source['proof']['hashTargetRva']);continue
  if c['role']=='readyContext':children[c['role']]=ready_context_sources.derive(image,pins,entry=c['targetVa'])
  elif c['role']=='indexedContext':
   from scripts.game_data.memorypack.int_list_sources import initialized_class
   at=c['targetVa'];raw=image.pe.bytes_at_va(at,15)
   need('exact-indexed-context-tail-span',raw[:11]==bytes.fromhex('488bc14863ca488b0cc8e9'))
   ready=ready_context_sources.derive(image,pins,entry=at+15+int.from_bytes(raw[-4:],'little',signed=True))
   rr=[(a,bytes.fromhex(h))for a,h in ready['proof']['sourceRegions']]
   children[c['role']]=dict(entryRva=at-base,spanHex=raw.hex(),spanSha256=hashlib.sha256(raw).hexdigest().upper(),
    readySource=ready,program=initialized_class([(at,raw),*rr],at,indexed=True),physicalFunctionExtentProved=False)
  elif c['role']in('preparePoolClass','prepareEncodingClass'):children[c['role']]=prepare.derive(image,pins,target=c['targetVa'])
  else:
   b=pointer.owned(image,c['targetVa']);children[c['role']]=dict(entryRva=b['pointer']-base,sourceWindows=b['windows'],
    sourceRegions=[[a,h.hex()]for a,h in b['regions']],rows=b['rows'],effectsProved=False)
 result=json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-small-buffer-data-path-caller-source',nativeInputs=pins,
  proof=dict(imageBase=base,byteHashSource=source,sourceWindows=body['windows'],sourceRegions=[[a,h.hex()]for a,h in body['regions']],
   programs=programs,actualUsages=contexts,children=children),selectedDataPathPoolEncodingRequestsAndFramesProved=True,
  actualByteHashAndLow32DuplicationProved=True,poolEncodingAndDisposalEffectsProved=False,
  runtimeInvocationObserved=False,actualRuntimeCallbacksOrBuffersObserved=False,playbackProved=False,
  conditions=__doc__)))
 validate(result,pins);_publication_gate(image,pins);return result

def validate(source,pins):
 import hashlib
 from scripts.game_data.memorypack import leveldata_patrol_byte_hash_sources as byte_hash,leveldata_patrol_class_preparation_sources as prepare
 from scripts.game_data.il2cpp import ready_context_sources
 need('same-source-envelope',source.get('schema')==SCHEMA and source.get('status')=='validated-conditional-small-buffer-data-path-caller-source'
  and source.get('nativeInputs')==pins and all(source.get(k)is True for k in('selectedDataPathPoolEncodingRequestsAndFramesProved','actualByteHashAndLow32DuplicationProved'))
  and all(source.get(k)is False for k in('poolEncodingAndDisposalEffectsProved','runtimeInvocationObserved','actualRuntimeCallbacksOrBuffersObserved','playbackProved')))
 p=source['proof'];base=p['imageBase'];byte_hash.validate(p['byteHashSource'],pins);regions=[]
 need('same-owned-window-set',bool(p['sourceWindows'])and len(p['sourceWindows'])==len(p['sourceRegions']))
 for w,(a,h)in zip(p['sourceWindows'],p['sourceRegions']):
  raw=bytes.fromhex(h);need('complete-owned-source-authenticated',w==dict(startRva=a-base,endRva=a-base+len(raw),sha256=hashlib.sha256(raw).hexdigest().upper()));regions.append((a,raw))
 entry=p['programs'][0]['entry'];actual=[program(regions,entry,nonnull=n,nonempty=e)for n,e in((False,False),(True,False),(True,True))]
 need('complete-selected-caller-replay',json.loads(json.dumps(actual))==p['programs'])
 need('same-independent-source-entry',entry-base==p['byteHashSource']['proof']['pathHashSource']['proof']['pathSource']['proof']['dataHashSource']['entryRva'])
 for c in actual[-1]['calls']:
  role=c['role'];target=c['targetVa']-base
  if role=='byteHash':need('same-byte-hash-call-target',target==p['byteHashSource']['proof']['hashTargetRva']);continue
  child=p['children'][role]
  if role=='readyContext':ready_context_sources.validate(child,pins);need('same-ready-source-target',target==child['actualEntryRva'])
  elif role=='indexedContext':
   from scripts.game_data.memorypack.int_list_sources import initialized_class
   raw=bytes.fromhex(child['spanHex']);at=base+child['entryRva'];ready=child['readySource'];ready_context_sources.validate(ready,pins)
   need('exact-indexed-context-child-span',target==child['entryRva']and len(raw)==15 and raw[:11]==bytes.fromhex('488bc14863ca488b0cc8e9')
    and child['spanSha256']==hashlib.sha256(raw).hexdigest().upper()and child['physicalFunctionExtentProved']is False
    and at+15+int.from_bytes(raw[-4:],'little',signed=True)==base+ready['actualEntryRva'])
   rr=[(a,bytes.fromhex(h))for a,h in ready['proof']['sourceRegions']]
   need('exact-indexed-context-ready-replay',json.loads(json.dumps(initialized_class([(at,raw),*rr],at,indexed=True)))==child['program'])
  elif role.startswith('prepare'):prepare.validate(child,pins);need('same-preparation-source-target',target==child['actualEntryRva'])
  else:need('same-actual-callee-target',target==child['entryRva']and child['effectsProved']is False)
 for u in actual[-1]['classAndMethodUsages']:
  usage=p['actualUsages'][str(u['instructionVa']-base)];need('same-actual-usage-cell',usage['instructionRva']==u['instructionVa']-base and usage['usageCellRva']==u['cellVa']-base)
 return dict(selectedDataPathPoolEncodingRequestsAndFramesProved=True,actualByteHashAndLow32DuplicationProved=True,
  poolEncodingAndDisposalEffectsProved=False,runtimeInvocationObserved=False)
