"""Selected normal resource-manager request and handle-copy caller source.

Actual service getter calls are independent results. Their concrete class-ID
predicate and backend readiness are source conditions; no class name is
inferred from a numeric ID. Backend request/create/validity effects remain
separate until their own sources are joined. No live asset is inferred.
"""
import json
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

SCHEMA='endfield.story-patrol-resource-request-sources.v1'


def need(check,condition):
 if not condition:raise ValueError('storyPatrolResource.'+check)


def program(regions,entry,*,available=True,requested=True,created_valid=True):
 need('literal-resource-source-branches',all(type(v)is bool for v in(available,requested,created_valid))and
  (available or(not requested and not created_valid))and(requested or not created_valid))
 g=BytesPath(regions,entry);calls=[];usages=[]
 def call(role):
  at=g.at;target=g.relative('e8');calls.append(dict(role=role,instructionVa=at,targetVa=target));return target
 def use():
  at=g.at;cell=g.relative('488b0d');usages.append(dict(instructionVa=at,cellVa=cell));return cell
 g.take('4053','56','4154','4155','4881ec88000000');replacements=g.relative('488b05')
 g.take('488bd9','450fb6e1','498bf0','4c8bea','488b4878','4885c9');g.branch('74',True,1)
 cls=use();g.take('4c89b424c0000000','83b9e000000000');g.branch('75',True,1)
 g.take('4889ac24b0000000','33c9','4889bc24b8000000','4c89bc2480000000');getter=call('get-manager-first')
 g.take('4c8bf0','4885c0');g.branch('0f84',False);g.take('488b00','33ff','81b81c010000')
 class_id=int.from_bytes(g.read(4),'little');g.branch('0f84',True)
 g.take('49397e28','0f97c0','84c0');g.branch('0f84',not available)
 result='literal false';output='zero20';second_id=None
 if available:
  need('same-resource-manager-class-cell',use()==cls);g.take('39b9e0000000');g.branch('75',True,1)
  g.take('33c9');need('same-service-getter-target',call('get-manager-second')==getter)
  g.take('4c8bf0','4885c0');g.branch('0f84',False);g.take('488b00','81b81c010000')
  second_id=int.from_bytes(g.read(4),'little');need('same-literal-concrete-backend-class-id',second_id==class_id);g.branch('0f84',True)
  need('same-actual-replacement-root',g.relative('488b05')==replacements);g.take('488b4878','4885c9');g.branch('74',True,1)
  g.take('4533c9','450fb6c4','488bd3','498bce');call('request-backend')
  g.take('84c0');g.branch('0f84',not requested)
  if requested:
   need('same-actual-create-replacement-root',g.relative('488b05')==replacements);g.take('488b5078','4885d2');g.branch('74',True,1)
   g.take('48897c2428','488d4c2460','4d8bcd','4488642420','4c8bc3','498bd6');call('create-handle')
   g.take('488d4c2440','0f1000','8b4010','89442450','0f29442440');call('created-handle-valid')
   g.take('84c0');g.branch('74',not created_valid,1)
   if created_valid:g.take('0f28442440','8b4c2450');g.at=g.relative('eb',1)
   else:g.take('0f57c0','33c9')
   g.take('0f1106','894e10','33d2','488bce');call('output-handle-valid');g.at=g.relative('e9')
   result='unchanged output-handle-valid Bool';output='unchanged created20'if created_valid else'zero20'
 if not available or not requested:
  g.take('0f57c0','33c0','0f1106','894610');g.at=g.relative('e9')
 g.take('488bac24b0000000','488bbc24b8000000','4c8bbc2480000000','4c8bb424c0000000','4881c488000000','415d','415c','5e','5b','c3')
 return dict(selectedBytes=g.seen,entry=entry,backendAvailable=available,requestSucceeded=requested,createdValid=created_valid,
  actualClassIdPredicate=class_id,classIdSourceOffset=284,readyFieldOffset=40,readyFieldBytes=8,selectedReadyFieldUnsignedPositiveRequired=available,
  selectedReplacementReceiverAt120RequiredNull=True,replacementRootCell=replacements,classUsages=usages,calls=calls,
  incomingPathHashRcxRetainedInRbx=True,incomingTypeRdxRetainedInR13=True,incomingOutputR8RetainedInRsi=True,
  incomingRootCategoryR9bRetainedInR12b=True,serviceGetterResultsIndependent=True,
  backendArguments=dict(rcx='second actual manager result',rdx='same path-hash QWORD',r8d='zero-extended incoming category byte',r9d=0),
  createdArguments=dict(rcx='address of20-byte hidden output RSP96',rdx='second actual manager result',
   r8='same path-hash QWORD',r9='unchanged incoming runtime Type',stackArgument5='incoming category byte',stackArgument6=0),
  outputSlices=[dict(offset=0,bytes=16),dict(offset=16,bytes=4)],outputSource=output,resultAlSource=result,
  entryRspRestored=True,nonvolatilesRestored=['rbx','rbp','rsi','rdi','r12','r13','r14','r15'],normalReturn=True,
  actualBackendRequestCreateOrValidityEffectsProved=False,liveServiceOrAssetSelectionObserved=False)


def derive(image,pins):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.memorypack import leveldata_patrol_asset_sources as asset_owner,pointer_param as pointer
 _publication_gate(image,pins);base=image.pe.image_base;asset=asset_owner.derive(image,pins);child=asset['proof']['children']['resource-TryLoad']
 body=pointer.owned(image,base+child['entryRva']);programs=[program(body['regions'],body['pointer'],available=a,requested=r,created_valid=v)
  for a,r,v in((False,False,False),(True,False,False),(True,True,False),(True,True,True))]
 children={};usages={}
 for p in programs:
  for u in p['classUsages']:
   usage=derive_typed_usage_context(image,u['instructionVa']-base,label='storyPatrolResource.actualClass')
   need('own-resource-manager-class',usage.get('tag')==1 and usage.get('typeName')=='Beyond.Resource.ResourceManager');usages[str(u['instructionVa']-base)]=usage
  for c in p['calls']:
   key='get-manager'if c['role'].startswith('get-manager-')else c['role']
   if key in children:need('same-actual-child-target:'+key,children[key]['entryRva']==c['targetVa']-base);continue
   b=pointer.owned(image,c['targetVa']);children[key]=dict(entryRva=b['pointer']-base,sourceWindows=b['windows'],
    sourceRegions=[[a,h.hex()]for a,h in b['regions']],rows=b['rows'],effectsProved=False)
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-resource-request-caller-source',nativeInputs=pins,
  proof=dict(assetSource=asset,sourceWindows=body['windows'],sourceRegions=[[a,h.hex()]for a,h in body['regions']],programs=programs,
   actualClassUsages=usages,children=children),selectedNormalResourceArgumentsHandleCopiesAndFramesProved=True,
  actualBackendRequestCreateOrValidityEffectsProved=False,liveServiceOrAssetSelectionObserved=False,
  runtimeInvocationObserved=False,playbackProved=False,wholeConversionProved=False,
  evidenceBoundary=dict(exact='Actual warm absent-replacement source with both independent manager results, selected literal class-ID/readiness predicates, backend request/create/validation arguments, complete20-byte copy or zero output and full frames.',
   conditional=__doc__,unresolved=['backend readiness/type/callback identity','actual request/create/validity and service helper effects','live asset state and controller activation']))))
