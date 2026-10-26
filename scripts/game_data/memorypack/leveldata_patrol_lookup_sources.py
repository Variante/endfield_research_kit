"""Warm actual Patrol path/asset forwarders and null-comparison source.

The precise generic MethodInfo contexts and class state must already be ready.
These programs preserve string/handle input values and select actual tail
targets. They do not infer asset existence, live MethodInfo contents or Unity
object identity from file bytes. A nonzero native cached pointer is a source
predicate, not proof of a live Unity object.
"""
import json
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

SCHEMA='endfield.story-patrol-lookup-sources.v1'


def need(check,condition):
 if not condition:raise ValueError('storyPatrolLookup.'+check)


def concat_program(regions,entry):
 g=BytesPath(regions,entry);g.take('48895c2408','48896c2410','4889742418','57','4883ec20',
  '4983793800','498bd9','498bf8','488bf2','488be9');g.branch('74',False,1)
 usage=g.at;type_cell=g.relative('488b0d');g.take('83b9e000000000');g.branch('74',False,1)
 g.take('4c8b4b38','4c8bc7','488bd6','488bcd','4d8b09','488b5c2430','488b6c2438','488b742440','4883c420','5f')
 site=g.at;target=g.relative('e9')
 return dict(selectedBytes=g.seen,entry=entry,classUsageInstructionVa=usage,classCell=type_cell,
  methodInfoR9ContextOffset=56,selectedMethodContextNonzeroRequired=True,selectedClassInitializedRequired=True,
  tailInstructionVa=site,tailTargetVa=target,tailArguments=dict(rcx='unchanged first string',rdx='unchanged second string',
   r8='unchanged third string',r9='QWORD at actual MethodInfo context[0]'),
  entryRspRestored=True,nonvolatilesRestored=['rbx','rbp','rsi','rdi'],normalTail=True,tailEffectsProved=False)


def path_program(regions,entry):
 g=BytesPath(regions,entry);g.take('4053','4883ec20');ready=g.relative('803d')+1;g.take('00','488bd9');g.branch('74',False,1)
 usage=g.at;type_cell=g.relative('488b0d');g.take('83b9e000000000');g.branch('74',False,1)
 g.take('488bcb','4883c420','5b');site=g.at;target=g.relative('e9')
 return dict(selectedBytes=g.seen,entry=entry,metadataReadyCell=ready,classUsageInstructionVa=usage,classCell=type_cell,
  selectedMetadataReadyByteNonzeroRequired=True,selectedClassInitializedRequired=True,
  tailInstructionVa=site,tailTargetVa=target,tailArguments=dict(rcx='unchanged incoming path string'),
  entryRspRestored=True,nonvolatilesRestored=['rbx'],normalTail=True,tailEffectsProved=False)


def get_program(regions,entry):
 g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20','48837a3800','488bda','488bf9');g.branch('74',False,1)
 g.take('488b5338','488bcf','488b12','488b5c2430','4883c420','5f');site=g.at;target=g.relative('e9')
 return dict(selectedBytes=g.seen,entry=entry,methodInfoRdxContextOffset=56,selectedMethodContextNonzeroRequired=True,
  tailInstructionVa=site,tailTargetVa=target,tailArguments=dict(rcx='unchanged incoming handle address',
   rdx='QWORD at actual MethodInfo context[0]'),entryRspRestored=True,nonvolatilesRestored=['rbx','rdi'],
  normalTail=True,tailEffectsProved=False)


def unity_program(regions,entry,*,nonnull,cached_nonzero=False,cached_offset=16):
 need('literal-null-comparison-selections',type(nonnull)is bool and type(cached_nonzero)is bool and(nonnull or not cached_nonzero))
 need('owned-small-cached-field-offset',type(cached_offset)is int and 16<=cached_offset<128)
 g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20','488bda','488bf9');usage=g.at;cell=g.relative('488b15')
 g.take('83bae000000000');g.branch('74',False,1);g.take('4885ff','0f94c1','4885db','0f94c0','84c8');g.branch('75',not nonnull,1)
 if nonnull:
  g.take('4885db');g.branch('75',False,1);g.take('399ae0000000');g.branch('74',False,1)
  g.take('4885ff');g.branch('74',False,1);g.take('48837f'+bytes((cached_offset,)).hex()+'00');g.branch('74',not cached_nonzero,1)
  if cached_nonzero:g.take('b001')
  else:g.take('32c0');g.at=g.relative('eb',1)
 else:g.take('32c0');g.at=g.relative('eb',1)
 g.take('488b5c2430','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,entry=entry,classUsageInstructionVa=usage,classCell=cell,
  selectedClassInitializedRequired=True,rightArgumentRdxRequiredZero=True,leftNonnull=nonnull,
  cachedPointerOffset=cached_offset,cachedPointerBytes=8,cachedPointerNonzeroRequired=cached_nonzero,
  resultAl=nonnull and cached_nonzero,entryRspRestored=True,nonvolatilesRestored=['rbx','rdi'],normalReturn=True,
  liveUnityObjectIdentityOrValidityProved=False)


def derive(image,pins):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.memorypack import leveldata_patrol_lead_sources as lead_owner,pointer_param as pointer,scalar_param_native as scalar
 _publication_gate(image,pins);base=image.pe.image_base;lead=lead_owner.derive(image,pins);ctx=NativeReferenceContext(image)
 targets=lead['proof']['actualTargets'];programs={};sources={};children={};usages={}
 field=list(ctx.field('UnityEngine.Object::m_CachedPtr'))
 need('own-Unity-cached-pointer-field',field[:2]==['UnityEngine.Object','nint']and type(field[2])is int)
 td=ctx.index.types['UnityEngine.Object'];cached,=[f for f in image.metadata.fields_for(td)if image.metadata.string(f.name_index)=='m_CachedPtr']
 scalar.ordinary(image,ctx.type_pointer(cached.type_index),24,'storyPatrolLookup.cachedNativePointer')
 for role,parser in(('concat-path',concat_program),('process-path',path_program),('Get',get_program),('Unity-object-not-equal-null',None)):
  body=pointer.owned(image,base+targets[role]);sources[role]=dict(entryRva=body['pointer']-base,sourceWindows=body['windows'],
   sourceRegions=[[a,raw.hex()]for a,raw in body['regions']])
  if parser is None:programs[role]=[unity_program(body['regions'],body['pointer'],nonnull=n,cached_nonzero=c,cached_offset=field[2])for n,c in((False,False),(True,False),(True,True))]
  else:
   programs[role]=parser(body['regions'],body['pointer']);p=programs[role];child=pointer.owned(image,p['tailTargetVa'])
   children[role]=dict(entryRva=child['pointer']-base,sourceWindows=child['windows'],sourceRegions=[[a,h.hex()]for a,h in child['regions']],rows=child['rows'],effectsProved=False)
  p=programs[role][0]if parser is None else programs[role]
  if 'classUsageInstructionVa'in p:usages[role]=derive_typed_usage_context(image,p['classUsageInstructionVa']-base,label='storyPatrolLookup.'+role)
 for role,name in(('concat-path','Cysharp.Text.ZString'),('process-path','Beyond.Resource.HashStringPathProcessor'),('Unity-object-not-equal-null','UnityEngine.Object')):
  need('own-class-initialization-request:'+role,usages[role].get('tag')==1 and usages[role].get('typeName')==name)
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-warm-lookup-caller-sources',nativeInputs=pins,
  proof=dict(leadSource=lead,sources=sources,programs=programs,actualClassUsages=usages,nominalCachedPointerField=field,tailChildren=children),
  selectedGenericPathHandleForwarderArgumentsAndFramesProved=True,selectedUnityNullComparisonSourceProved=True,
  lookupPathAndHandleChildEffectsProved=False,liveUnityObjectIdentityOrValidityProved=False,
  runtimeInvocationObserved=False,playbackProved=False,wholeConversionProved=False,
  evidenceBoundary=dict(exact='Actual warm generic concat/Get and hash-path tail arguments/full restored frames, exact current class usages and ordinary Unity Object cached-pointer field null predicate.',
   conditional=__doc__,unresolved=['actual tail string/path/handle child effects','TryLoad interface/inline selection and resource service effects','live asset/MethodInfo/Unity object identity and controller activation']))))
