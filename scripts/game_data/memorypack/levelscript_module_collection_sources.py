"""Finite Module list sources and exact actual requests, without element grants.

Reference elements, primitive callbacks and nominal value callbacks retain
separate owners. A successful source join never supplies a record grammar or
an enclosing field. The EntityPtr list is owned by its dedicated component.
"""
import hashlib
import json

SCHEMA='endfield.story-module-collection-source.v1'
LIST='System.Collections.Generic.List`1<'
REFERENCE_TYPES=('Beyond.Gameplay.BattlerStageData','Beyond.Gameplay.BeaconPoleControllerData+AltarInfo',
 'Beyond.Gameplay.ButterflyScatterSerializeInfo','Beyond.Gameplay.ParamKeyValue',
 'Beyond.Gameplay.RollingStoneControllerData+LauncherData','Beyond.Gameplay.TyphoeaArcheryObstacleData','Beyond.Gameplay.TyphoeaArcheryTargetData')
VALUE_TYPES=('Beyond.Gameplay.Core.LsmPtr','Beyond.Gameplay.Core.LevelScriptShape')
NUMERIC_TYPES=('float','int','ulong','UnityEngine.Vector3')
ELEMENTS=REFERENCE_TYPES+VALUE_TYPES+NUMERIC_TYPES


def need(check,condition):
 if not condition:raise ValueError('storyModuleCollection.'+check)


def _windows(value):
 if isinstance(value,dict):
  if all(k in value for k in('startRva','endRva','sha256')):yield value
  else:
   for item in value.values():yield from _windows(item)
 elif isinstance(value,(list,tuple)):
  for item in value:yield from _windows(item)


def _whole_windows(image,proof):
 selected={}
 for window in _windows(proof):
  key=tuple(window[k]for k in('startRva','endRva','sha256'));selected[key]=window
 windows=list(selected.values());image.check_windows(windows,label='storyModuleCollection.all-owned-windows')
 return dict(windows=windows,regions=[[w['startRva'],image.window_bytes(w).hex().upper()]for w in windows])


def verify_windows(component):
 p=component['nativeSource'];windows=p['windows'];rows=p['regions']
 need('complete-unique-source-window-payloads',len(windows)==len(rows)>0
  and len({(w['startRva'],w['endRva'],w['sha256'])for w in windows})==len(windows))
 need('all-and-only-source-proof-windows',{tuple(w[k]for k in('startRva','endRva','sha256'))for w in _windows(component['proof'])}==
  {tuple(w[k]for k in('startRva','endRva','sha256'))for w in windows})
 for w,(at,h)in zip(windows,rows,strict=True):
  raw=bytes.fromhex(h)
  need('exact-owned-source-window',type(at)is int and at==w['startRva']and len(raw)==w['endRva']-at
   and hashlib.sha256(raw).hexdigest().upper()==w['sha256'])
 return component


def derive(image,pins,*,typed_request,call_target,element_type):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import validate_typed_usage_context
 from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
 from scripts.game_data.memorypack import modelview_packable_sources
 from scripts.game_data.memorypack.skill_cost_data_list_sources import _load
 _publication_gate(image,pins);base=image.pe.image_base;name=LIST+element_type+'>'
 need('finite-explicit-element',element_type in ELEMENTS)
 validate_typed_usage_context(image,typed_request,label='storyModuleCollection.actual')
 bind_typed_read(image,typed_request,method_name='ReadPackable',argument=name,kind=21,reference=True)
 context=None;limit=4096
 if element_type in REFERENCE_TYPES:
  from scripts.game_data.memorypack.reference_list_induction_sources import derive as reference_list
  proof=reference_list(image,pins,typed_request=typed_request,call_target=call_target,element_type=element_type,count_limit=limit)
  need('own-complete-reference-loop',proof.get('status')=='validated-bounded-reference-list-induction'
   and proof.get('elementType')==element_type and proof['induction']['maxCount']==limit)
 elif element_type=='int':
  from scripts.game_data.memorypack.leveldata_int_list_sources import derive as integers
  proof=integers(image,pins,typed_request=typed_request,call_target=call_target,count_limit=limit)
 elif element_type=='ulong':
  from scripts.game_data.memorypack.levelscript_collection_sources import derive_ulong_list_component
  proof=derive_ulong_list_component(image,pins,typed_request=typed_request,call_target=call_target,count_limit=limit)
 elif element_type=='UnityEngine.Vector3':
  from scripts.game_data.memorypack.leveldata_vector3_list_sources import derive as vectors
  proof=vectors(image,pins,typed_request=typed_request,call_target=call_target)
  limit=proof['capability']['countLimit']
 elif element_type=='float':
  import copy
  from scripts.game_data.memorypack.float_list_sources import derive as floating
  from scripts.game_data import levelscript_int_list_native
  fact=_load('levelscript_int_list_native.json',pins);levelscript_int_list_native._validate_native(image,fact)
  proof=floating(image,pins,dict(typedRead=typed_request),fact)
  core=_load('npc_runtime_native.json',pins)['readPackable'];generic=_load('leveldata_npc_patrol_native.json',pins)['declarations']
  routes=copy.deepcopy(generic['adapters']['referenceRoutes']);routes['wrappers']=[]
  reference=modelview_packable_sources.validate_components(image,pins,core,routes)
  need('same-actual-floating-reference-helper',call_target==base+core['entryRva'])
  proof=dict(floating=proof,reference=reference);need('bounded-floating-induction',proof['floating']['countInduction']['maxCount']>=limit)
 else:
  from scripts.game_data.memorypack.skill_value_list_context import derive as value_context
  context,body=value_context(image,pins,typed_request=typed_request,call_target=call_target,element_type=element_type)
  if element_type=='Beyond.Gameplay.Core.LsmPtr':
   from scripts.game_data.memorypack.levelscript_condition_lsm_list_sources import derive as lsm
   proof=lsm(image,pins);listing=proof['proof']['elementList']
   need('same-exact-Lsm-list-body-and-context',listing['context']['registration']==context['registration']
    and listing['context']['closedCarrier']==context['closedCarrier']and listing['countInduction']['maxCount']>=limit)
  else:
   from scripts.game_data.memorypack.levelscript_owner_sources import derive as owners
   from scripts.game_data.memorypack.levelscript_shape_sources import derive_record,derive_transfer
   from scripts.game_data.memorypack.levelscript_shape_list_sources import derive as shapes
   root=owners(image,pins);record=derive_record(image,pins);transfer=derive_transfer(image,pins,record)
   listing=shapes(image,pins,root,record,transfer);proof=dict(record=record,transfer=transfer,collection=listing)
   need('same-exact-Shape-list-body-and-context',listing['context']['registration']==context['registration']
    and listing['context']['closedCarrier']==context['closedCarrier']and listing['capability']['wholeGrammarAdmitted']is True)
   limit=listing['capability']['countLimit']
 result=dict(schema=SCHEMA,status='validated-conditional-module-collection-source',nativeInputs=pins,typeName=name,elementType=element_type,
  typedRequest=typed_request,readerMethodDefinition=typed_request['methodSpec'][0],sourceTargetRva=call_target-base,
  headerBytes=4,countLimit=limit,countRange=[-1,limit],nullable=True,listFramingProved=True,
  actualCallbackEqualsProvedChildRequired=True,initiallyNullOutputRequired=True,proof=proof,actualValueContext=context,
  elementGrammarAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,liveFormatterSelectionObserved=False)
 result['nativeSource']=_whole_windows(image,proof);_publication_gate(image,pins)
 return json.loads(json.dumps(result))


def bind_request(pins,join,component):
 verify_windows(component);element=component.get('elementType');usage=join.get('typedRequest',{});request=component.get('typedRequest',{})
 need('exact-own-source-and-domain',element in ELEMENTS and component.get('schema')==SCHEMA
  and component.get('status')=='validated-conditional-module-collection-source'and component.get('nativeInputs')==pins
  and component.get('typeName')==LIST+element+'>'==join.get('typeName')and component.get('listFramingProved')is True
  and type(component.get('countLimit'))is int and component['countLimit']==(64 if element=='Beyond.Gameplay.Core.LevelScriptShape'else 4096)
  and component.get('countRange')==[-1,component['countLimit']]and component.get('headerBytes')==4 and component.get('nullable')is True
  and all(component.get(k)is False for k in('elementGrammarAdmitted','parentFieldAdmitted','wholeOwnerAdmitted','liveFormatterSelectionObserved'))
  and component.get('initiallyNullOutputRequired')is True and component.get('actualCallbackEqualsProvedChildRequired')is True)
 need('same-exact-closed-MethodSpec-and-source-target',tuple(usage.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments','methodSpec'))==
  tuple(request.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments','methodSpec'))
  and tuple(usage.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments'))==
   (6,'MemoryPack.MemoryPackReader','ReadPackable',[],[component['typeName']])
  and type(join.get('sourceTargetRva'))is int and join['sourceTargetRva']==component.get('sourceTargetRva')
  and usage['methodSpec'][0]==component['readerMethodDefinition'])
 return dict(fieldName=join['fieldName'],typeName=join['typeName'],readerMethodDefinition=component['readerMethodDefinition'],
  sourceTargetRva=component['sourceTargetRva'],countLimit=component['countLimit'],listFramingProved=True,
  elementGrammarAdmitted=False,parentFieldAdmitted=False)
