"""Selected cached-manager and resource-handle creation source programs.

The cached manager is a normally returning static reference load under its
actual ready class and nonnull storage conditions. Handle creation selects the
ordinary absent-replacement path and a normally returning nonnull resource
request; it passes that exact result into the actual constructor and preserves
the complete20-byte constructor result. No service, asset or heap identity is
observed and resource request effects require their own source owner.
"""
import json
import hashlib
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

SCHEMA='endfield.story-patrol-resource-handle-source.v1'

def need(check,condition):
 if not condition:raise ValueError('storyPatrolResourceHandle.'+check)

def manager_program(regions,entry):
 g=BytesPath(regions,entry);g.take('4883ec28');root=g.relative('488b05')
 g.take('488bd1','488b4878','4885c9');g.branch('0f85',False)
 site=g.at;cls=g.relative('488b05');g.take('83b8e000000000');g.branch('0f84',False)
 g.take('488b88b8000000','4883790800');g.branch('74',False,1)
 g.take('83b8e000000000');g.branch('0f84',False)
 g.take('488b80b8000000','488b4008','4883c428','c3')
 return dict(selectedBytes=g.seen,entry=entry,replacementRootCell=root,classUsageInstructionVa=site,classCell=cls,
  selectedReplacementReceiverAt120RequiredNull=True,selectedClassInitializedRequired=True,
  staticFieldsOffset=184,cachedReferenceOffset=8,cachedReferenceRequiredNonnull=True,
  returnsSameCachedReference=True,opaqueCalls=0,nonframeMemoryWrites=0,
  entryRspRestored=True,allNonvolatilesUnchanged=True,normalReturn=True,liveServiceIdentityObserved=False)

def create_program(regions,entry):
 g=BytesPath(regions,entry);g.take('48895c2410','48897c2420','4c89442418','48894c2408','4156','4883ec70',
  '498bf9','498bc0','4c8bda','488bd9');root=g.relative('4c8b05')
 g.take('498b5078','4885d2');g.branch('74',True,1)
 g.take('4533f6','4c89742440','4c89742430','c74424280a000000','4488742420','440fb68c24a0000000',
  '4c8bc7','488bd0','498bcb');request_site=g.at;request=g.relative('e8')
 g.take('4889442448','4885c0');g.branch('0f85',True)
 g.take('0f57c0','33c9','0f11442458','894c2468','4533c9','41b001','488bd0','488d4c2458')
 ctor_site=g.at;ctor=g.relative('e8')
 g.take('0f10442458','8b442468','0f1103','894310','488bc3','4c8d5c2470','498b5b18','498b7b28',
  '498be3','415e','c3')
 return dict(selectedBytes=g.seen,entry=entry,replacementRootCell=root,selectedReplacementReceiverAt120RequiredNull=True,
  requestCall=dict(instructionVa=request_site,targetVa=request),constructorCall=dict(instructionVa=ctor_site,targetVa=ctor),
  requestArguments=dict(rcx='incoming manager RDX',rdx='incoming hash R8',r8='incoming Type R9',
   r9='zero-extended incoming category byte',stack5=0,stack6=10,stack7=0),
  requestReturnsNonnullRequired=True,constructorArguments=dict(rcx='zeroed20-byte local RSP88',rdx='same actual request result',r8b=1,r9d=0),
  outputSlices=[dict(offset=0,bytes=16),dict(offset=16,bytes=4)],constructorOutputCopiedUnchanged=True,
  returnsIncomingHiddenOutputRcx=True,entryRspRestored=True,nonvolatilesRestored=['rbx','rdi','r14'],normalReturn=True,
  requestOrConstructorEffectsProved=False,liveHandleOrAssetIdentityObserved=False)

def derive(image,pins):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.memorypack import leveldata_patrol_resource_lookup_sources as parent,pointer_param as pointer
 _publication_gate(image,pins);base=image.pe.image_base;source=parent.derive(image,pins)
 children=source['proof']['resourceSource']['proof']['children'];packets={};programs={}
 for name,parser in(('get-manager',manager_program),('create-handle',create_program)):
  packet=pointer.owned(image,base+children[name]['entryRva']);programs[name]=parser(packet['regions'],packet['pointer'])
  packets[name]=dict(entryRva=packet['pointer']-base,sourceWindows=packet['windows'],sourceRegions=[[a,b.hex()]for a,b in packet['regions']])
 usage=derive_typed_usage_context(image,programs['get-manager']['classUsageInstructionVa']-base,label='storyPatrolResourceHandle.managerClass')
 cp=programs['create-handle'];callees={}
 for name,call in(('request',cp['requestCall']),('constructor',cp['constructorCall'])):
  packet=pointer.owned(image,call['targetVa']);callees[name]=dict(entryRva=packet['pointer']-base,sourceWindows=packet['windows'],
   sourceRegions=[[a,b.hex()]for a,b in packet['regions']],rows=packet['rows'],effectsProved=False)
 result=json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-resource-handle-caller-source',nativeInputs=pins,
  proof=dict(resourceLookupSource=source,sources=packets,programs=programs,managerClassUsage=usage,callees=callees),
  cachedManagerReferenceAndFrameSourceProved=True,selectedCreateArgumentsCopiesAndFrameProved=True,
  resourceRequestOrConstructorEffectsProved=False,runtimeInvocationObserved=False,liveServiceHandleOrAssetIdentityObserved=False,playbackProved=False,
  evidenceBoundary=dict(exact='Cached static manager result without calls or nonframe writes; actual normal create request, exact nonnull result passed to actual constructor and unchanged20-byte output/full frames.',
   conditional=__doc__,unresolved=['Resource request and handle constructor effects','live service, resource/handle validity and actual asset identities','cold/static/replacement and other create paths']))))
 validate(result,pins);_publication_gate(image,pins);return result

def validate(source,pins):
 need('same-envelope',source.get('schema')==SCHEMA and source.get('status')=='validated-conditional-resource-handle-caller-source'
  and source.get('nativeInputs')==pins and all(source.get(k)is True for k in('cachedManagerReferenceAndFrameSourceProved','selectedCreateArgumentsCopiesAndFrameProved'))
  and all(source.get(k)is False for k in('resourceRequestOrConstructorEffectsProved','runtimeInvocationObserved','liveServiceHandleOrAssetIdentityObserved','playbackProved')))
 p=source['proof'];parent=p['resourceLookupSource'];need('same-native-parent',parent['nativeInputs']==pins)
 base=parent['proof']['metadataHelper']['proof']['imageBase']
 expected=parent['proof']['resourceSource']['proof']['children']
 need('same-program-roles',set(p['sources'])==set(p['programs'])=={'get-manager','create-handle'}and set(p['callees'])=={'request','constructor'})
 for name,packet in {**p['sources'],**p['callees']}.items():
  windows=packet['sourceWindows'];regions=packet['sourceRegions'];need('same-full-window-region-count',bool(windows)and len(windows)==len(regions))
  for w,(a,h)in zip(windows,regions):
   raw=bytes.fromhex(h);need('whole-owned-bytes:'+name,w==dict(startRva=a-base,endRva=a-base+len(raw),sha256=hashlib.sha256(raw).hexdigest().upper()))
  if name in p['sources']:
   parser=manager_program if name=='get-manager'else create_program
   actual=parser([(a,bytes.fromhex(h))for a,h in regions],base+packet['entryRva'])
   need('same-actual-parent-child:'+name,packet['entryRva']==expected[name]['entryRva']and json.loads(json.dumps(actual))==p['programs'][name])
 for role,key in(('request','requestCall'),('constructor','constructorCall')):
  need('actual-create-call-target:'+role,p['callees'][role]['entryRva']==p['programs']['create-handle'][key]['targetVa']-base)
 u=p['managerClassUsage'];m=p['programs']['get-manager']
 need('actual-ready-manager-class-context',u.get('tag')==1 and u.get('typeName')=='Beyond.Resource.ResourceManager'and
  u['instructionRva']==m['classUsageInstructionVa']-base and u['usageCellRva']==m['classCell']-base)
 return dict(cachedManagerReferenceAndFrameSourceProved=True,selectedCreateArgumentsCopiesAndFrameProved=True,
  resourceRequestOrConstructorEffectsProved=False,runtimeInvocationObserved=False)
