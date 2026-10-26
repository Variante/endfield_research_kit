"""Finite MissionArea8, direct Trigger44 and independently owned TrackingRoute8.

The direct raw shape has no wrapper header/default path. Parent reference
lists and their actual callbacks remain independent of either value width.
Only fresh derive authenticates the native graph; pure projections grant no
runtime selection, gameplay behavior, whole LevelData or public receipt.
"""
import copy
import json

from scripts.game_data.memorypack import leveldata_trigger_shape_raw_sources as raw
from scripts.game_data.memorypack import leveldata_tracking_route_sources as route

TYPE='Beyond.Gameplay.MissionAreaData'
CAP='story-mission-area'
FIELD='missionAreas'
ROOT='Beyond.Gameplay.LevelData'
LIMIT=4096
NODE_LIMIT=16384
LIST='System.Collections.Generic.List`1<'+TYPE+'>'
PLAN=(('activeOnTravelLine','bool','bool-byte'),('missionAreaId','string','byte-payload'),
 ('needTrackingRoute','bool','bool-byte'),('shape',raw.TYPE,'trigger-shape-raw44'),
 ('snapToGround','bool','bool-byte'),('subDataParentId','ulong','scalar64-bits'),
 ('trackingOffset','UnityEngine.Vector3','unity-vector3-raw12'),
 ('trackingRouteInfo',route.TYPE,'tracking-route-record'))


def need(check,condition):
 if not condition:raise ValueError('storyMissionArea.'+check)


def same(left,right):
 return json.dumps(left,sort_keys=True,separators=(',',':'),allow_nan=False)==json.dumps(right,sort_keys=True,separators=(',',':'),allow_nan=False)


def raw_capability(component,pins):
 from scripts.game_data.memorypack.leveldata_trigger_shape_raw_components import verify_source
 verify_source(component,pins)
 cap={key:copy.deepcopy(component[key])for key in('typeName','capability','wireBytes','managedBytes',
  'readerMethodDefinition','sourceTargetRva','resultAbi','contextRegister','enumType','enumBacking',
  'actualSourceProved','referenceLaneOffsets','paddingByteRanges','objectHeaderRead','canonicalWrapperUsed','actualCallbackSelectionRequired')}
 cap.update(physicalFields=copy.deepcopy(component['proof']['fields']),rawBitsPreserved=True,
  profileAdmitted=True,wholeGrammarAdmitted=False,liveFormatterSelectionObserved=False)
 return cap


def bind_program(source,program,pending):
 need('exact-eight-member-program',not pending and isinstance(program,dict)and source.get('wrappedType')==TYPE
  and[(r.get('fieldName'),r.get('declaredType'))for r in source.get('orderedSourceReads',[])]==[(n,t)for n,t,k in PLAN]
  and type(program.get('memberCount'))is int and program['memberCount']==8
  and all(type(r.get('memberIndex'))is int for r in program.get('reads',[]))
  and[(r.get('memberIndex'),r.get('fieldName'),r.get('kind'),r.get('childCapability'))for r in program['reads']]==[
   (i,n,k,'byte-payload'if k=='byte-payload'else route.CAPABILITY if k=='tracking-route-record'else None)for i,(n,t,k)in enumerate(PLAN)]
  and program.get('requiredCapabilities')==sorted(['byte-payload',route.CAPABILITY])
  and[(r.get('fieldName'),r.get('typeName'),r.get('capability'))for r in program.get('childBindings',[])]==[
   ('trackingRouteInfo',route.TYPE,route.CAPABILITY)])


def bind_reference(pins,join,child,capability):
 from scripts.game_data.codecs.leveldata.current_tracking_route import validate
 cap=child.get('capabilities',{}).get(capability,{});usage=join.get('typedRequest',{})
 need('exact-route-child-native-and-request',child.get('nativeInputs')==pins and capability==route.CAPABILITY
  and join.get('fieldName')=='trackingRouteInfo'and join.get('typeName')==route.TYPE
  and(usage.get('tag'),usage.get('typeName'),usage.get('methodName'),usage.get('classArguments'),usage.get('methodArguments'))==
   (6,'MemoryPack.MemoryPackReader','ReadValue',[],[route.TYPE])
  and isinstance(usage.get('methodSpec'),(list,tuple))and len(usage['methodSpec'])==3
  and type(usage['methodSpec'][0])is int and usage['methodSpec'][0]>=0
  and type(join.get('sourceTargetRva'))is int and join['sourceTargetRva']>0
  and cap.get('referenceReaderMethodDefinition')==usage['methodSpec'][0]
  and cap.get('referenceReaderTargetRva')==join['sourceTargetRva'])
 validate(cap)
 return dict(fieldName='trackingRouteInfo',typeName=route.TYPE,capability=route.CAPABILITY,
  readerMethodDefinition=usage['methodSpec'][0],sourceTargetRva=join['sourceTargetRva'],
  actualCallbackEqualsProvedChildRequired=True)


def capability(program,shape,tracking,parent):
 return dict(typeName=LIST,capability=CAP,recordType=TYPE,memberCount=8,program=copy.deepcopy(program),rawShape=copy.deepcopy(shape),
  trackingRoute=copy.deepcopy(tracking),parentBinding=copy.deepcopy(parent),countLimit=LIMIT,nodeLimit=NODE_LIMIT,headerBytes=4,
  profileAdmitted=True,nullAdmitted=True,positiveAdmitted=True,ordinaryAdapterAdmitted=True,
  initiallyNullListsRequired=True,actualCallbackEqualsProvedChildRequired=True,canonicalBooleanProfile=True,
  rawTriggerBitsPreserved=True,finiteTrackingOffsetProfile=True,wholeGrammarAdmitted=False,
  liveFormatterSelectionObserved=False,runtimeMissionAreaBehaviorProved=False)


def derive(image,pins,host):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.memorypack import generated_reader_sources,pooled_source_helper
 from scripts.game_data.memorypack.generated_record_components import compile_member_program
 from scripts.game_data.memorypack.reference_list_induction_sources import derive as reference_list
 from scripts.game_data.memorypack.reference_param_profile import derive_pair
 from scripts.game_data.memorypack.reference_object_sources import derive_adapter
 _publication_gate(image,pins);base=image.pe.image_base
 need('same-current-host',host.get('nativeInputs')==pins)
 wrapper,=[w for w in image.memorypack_wrappers.values()if w.wrapped_type==TYPE]
 source=generated_reader_sources.derive(image,pins,wrapper.name)
 need('complete-current-MissionArea-source',source.get('completeSelectedCallerAdmitted')is True
  and[(r['fieldName'],r['declaredType'])for r in source['orderedSourceReads']]==[(n,t)for n,t,k in PLAN])
 requests={i:derive_typed_usage_context(image,source['orderedSourceReads'][i]['context']['instructionRva'],
  label='storyMissionArea.actualChild')for i in(3,7)}
 shape=source['orderedSourceReads'][3]
 shape_source=raw.derive(image,pins,typed_request=requests[3],source_target=base+shape['sourceTargetRva'],source_instruction=shape['instruction'])
 need('same-independent-raw44-source',same(shape_source,shape['nominalHiddenSource']))
 tracking=route.derive(image,pins);child=tracking['capabilities'][route.CAPABILITY]
 program,pending=compile_member_program(source,pins,wrapper_name=wrapper.name,type_name=TYPE,value4={},
  typed_requests=requests,references={route.TYPE:(route.CAPABILITY,'tracking-route-record',route.CAPABILITY)},
  reference_children={route.TYPE:tracking},reference_binder=bind_reference)
 bind_program(source,program,pending)
 pair=derive_pair(image,TYPE);adapter=derive_adapter(image,pins,pair,wrapper)
 need('same-own-complete-reference-getter',same(source['lifecycle']['GetValue']['method'],adapter['getterMethod'])
  and source['lifecycle']['GetValue']['program'].get('fullReferenceOutput')is True)
 need('same-own-slot5',source['lifecycle']['concreteFormatter']['method'][0]==pair['composition']['interfaces'][0]['formatterDeserializeMethodIndex'])
 pooled={r['fieldName']:pooled_source_helper.validate_on_image(image,base+r['sourceTargetRva'],pins)
  for r in source['orderedSourceReads']if r['kind']=='byte-payload'}
 field,read=next((f,r)for f,r in zip(host['fields'],host['program']['orderedReads'],strict=True)if f['name']==FIELD)
 need('actual-own-host-list',field['typeName']==LIST)
 usage=derive_typed_usage_context(image,read['typedUsage']['instruction']-base,label='storyMissionArea.actualHost')
 listing=reference_list(image,pins,typed_request=usage,call_target=read['sourceTarget'],element_type=TYPE,count_limit=LIMIT)
 binding=dict(ownerType=ROOT,fieldName=FIELD,typeName=LIST,elementType=TYPE,capability=CAP,
  readerMethodDefinition=usage['methodSpec'][0],sourceTargetRva=listing['witnessComponent']['callTargetRva'],
  initiallyNullListRequired=True,actualCallbackEqualsProvedChildRequired=True)
 cap=capability(program,raw_capability(shape_source,pins),child,binding)
 from scripts.game_data.codecs.leveldata.current_mission_area import validate
 validate(cap);_publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema='endfield.story-mission-area-components.v1',
  status='validated-conditional-positive-mission-area',nativeInputs=pins,capability=cap,
  proof=dict(source=source,compiled=program,pair=pair,adapter=adapter,pooled=pooled,rawShape=shape_source,tracking=tracking),
  parent=dict(declaration=field,source=read,typedRequest=usage,collection=listing,binding=binding),
  parentFieldAdmitted=False,wholeOwnerAdmitted=False,evidenceBoundary=dict(
   exact='Own MissionArea8 complete reader/lifecycle/four frames/ordinary adapter, exact direct raw44 R8/E8/named field and independently complete TrackingRoute8 with distinct raw/canonical/reference children, bounded actual host list.',
   conditional='Ready exact typed contexts and callbacks, initially-null list outputs, normal compatible helper effects, disjoint buffered input/output/frame, canonical bools and finite ordinary Vector3s; raw Trigger and Tracking bits remain unchanged.',
   unresolved=['live formatter/provider selection','runtime mission-area or tracking behavior','whole LevelData physical EOF/public owner receipt']))))
