"""Finite authored waypoint records and independent padded WayLane children."""
import json
from scripts.game_data.memorypack import leveldata_waylane_list_sources as lanes

TYPE='Beyond.Gameplay.AI.WayPointInEditorData'
LIST='System.Collections.Generic.List`1<'+TYPE+'>'
CAP='story-waypoint'
ULONGS='System.Collections.Generic.List`1<ulong>'
ULONG_CAP='story-waypoint-uint64-list'
LIMIT=4096
PLAN=(('gateLaneCount','int','scalar32'),('isGate','bool','bool-byte'),('isPoiPoint','bool','bool-byte'),
 ('level','int','scalar32'),('linkLane',lanes.LIST,'waylane-list'),('linkTo',ULONGS,'uint64-list'),
 ('mainId','ulong','scalar64-bits'),('position','UnityEngine.Vector3','unity-vector3-raw12'),('uuid','ulong','scalar64-bits'))
OPERATIONS={'waylane-list':lanes.CAP,'uint64-list':ULONG_CAP}


def bind_program(source,program,pending):
 if (pending or source.get('wrappedType')!=TYPE or not isinstance(program,dict)
   or[(r.get('fieldName'),r.get('declaredType'))for r in source.get('orderedSourceReads',[])]!=[(n,t)for n,t,k in PLAN]
   or type(program.get('memberCount'))is not int or program['memberCount']!=len(PLAN)
   or any(type(r.get('memberIndex'))is not int for r in program.get('reads',[]))
   or[(r.get('memberIndex'),r.get('fieldName'),r.get('kind'),r.get('childCapability'))for r in program.get('reads',[])]!=[
    (index,n,k,OPERATIONS.get(k))for index,(n,t,k)in enumerate(PLAN)]
   or program.get('requiredCapabilities')!=sorted(OPERATIONS.values())
   or[(r.get('fieldName'),r.get('typeName'),r.get('capability'))for r in program.get('childBindings',[])]!=[
    (n,t,OPERATIONS[k])for n,t,k in PLAN if k in OPERATIONS]):raise ValueError('storyWayPoint.exact-finite-program')


def bind_collection(pins,join,child,capability):
 cap=child.get('capabilities',{}).get(capability,{});usage=join['typedRequest']
 typename=lanes.LIST if capability==lanes.CAP else ULONGS if capability==ULONG_CAP else None
 if (typename is None or child.get('nativeInputs')!=pins or join['typeName']!=typename
   or usage.get('methodName')!='ReadPackable'or usage.get('methodArguments')!=[typename]
   or type(cap.get('packableReaderMethodDefinition'))is not int or type(cap.get('packableReaderTargetRva'))is not int
   or(cap.get('packableReaderMethodDefinition'),cap.get('packableReaderTargetRva'))!=(usage['methodSpec'][0],join['sourceTargetRva'])):
  raise ValueError('storyWayPoint.exact-collection-source-parent')
 if capability==lanes.CAP:
  from scripts.game_data.codecs.leveldata.current_waylane import validate_list
  validate_list(cap,child.get('capabilities',{}).get(lanes.VALUE_CAP))
 else:
  if ((cap.get('typeName'),cap.get('elementType'),cap.get('countRange'))!=(ULONGS,'ulong',[-1,LIMIT])
    or type(cap.get('countLimit'))is not int or cap['countLimit']!=LIMIT
    or type(cap.get('elementWireBytes'))is not int or cap['elementWireBytes']!=8
    or any(cap.get(k)is not True for k in('nullable','positiveCountsAdmitted','rawBitsPreserved',
     'initiallyNullOutputRequired','actualCallbackEqualsProvedChildRequired'))):raise ValueError('storyWayPoint.exact-uint64-list-profile')
 return dict(fieldName=join['fieldName'],typeName=typename,capability=capability,countLimit=LIMIT,
  readerMethodDefinition=cap['packableReaderMethodDefinition'],sourceTargetRva=cap['packableReaderTargetRva'],
  actualCallbackEqualsProvedChildRequired=True)


def derive(image,pins,host):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.memorypack import generated_reader_sources,scalar_param_native as scalar
 from scripts.game_data.memorypack.generated_record_components import compile_member_program
 from scripts.game_data.memorypack.levelscript_collection_sources import derive_ulong_list_component
 from scripts.game_data.memorypack.reference_list_induction_sources import derive as reference_list
 from scripts.game_data.memorypack.reference_object_sources import derive_adapter
 from scripts.game_data.memorypack.reference_param_profile import derive_pair
 need=lambda k,e,a:scalar.need('storyWayPoint',k,e,a)
 _publication_gate(image,pins);need('same-current-host',pins,host['nativeInputs']);base=image.pe.image_base
 wrapper,=[w for w in image.memorypack_wrappers.values()if w.wrapped_type==TYPE]
 source=generated_reader_sources.derive(image,pins,wrapper.name)
 need('complete-nominal-field-order',[(n,t)for n,t,k in PLAN],[(r['fieldName'],r['declaredType'])for r in source['orderedSourceReads']])
 typed={};collections={};children={};child_caps={};proofs={}
 for read in source['orderedSourceReads']:
  index=read['memberIndex'];kind=PLAN[index][2]
  if kind not in OPERATIONS:continue
  usage=derive_typed_usage_context(image,read['context']['instructionRva'],label='storyWayPoint.actualChild');typed[index]=usage
  key=OPERATIONS[kind];target=base+read['sourceTargetRva']
  if kind=='waylane-list':
   proof=lanes.derive(image,pins,typed_request=usage,call_target=target);caps=proof['capabilities']
  else:
   proof=derive_ulong_list_component(image,pins,typed_request=usage,call_target=target,count_limit=LIMIT)
   caps={key:{k:v for k,v in proof.items()if k not in('proof','typedRequest','typedBinding','closedCarrier','evidenceBoundary')}}
  collections[read['declaredType']]=(key,kind,key);children[index]=dict(nativeInputs=pins,capabilities=caps)
  child_caps.update(caps);proofs[read['fieldName']]=proof
 program,pending=compile_member_program(source,pins,wrapper_name=wrapper.name,type_name=TYPE,value4={},
  typed_requests=typed,collections=collections,collection_children=children,collection_binder=bind_collection)
 bind_program(source,program,pending)
 pair=derive_pair(image,TYPE);adapter=derive_adapter(image,pins,pair,wrapper)
 need('same-owned-GetValue',source['lifecycle']['GetValue']['method'],adapter['getterMethod'])
 need('same-owned-concrete-callback',source['lifecycle']['concreteFormatter']['method'][0],pair['composition']['interfaces'][0]['formatterDeserializeMethodIndex'])
 need('full-owned-original-reference',True,source['lifecycle']['GetValue']['program'].get('fullReferenceOutput'))
 declaration,read=next((f,r)for f,r in zip(host['fields'],host['program']['orderedReads'],strict=True)if f['name']=='worldWayPointData')
 need('exact-host-waypoint-list',LIST,declaration['typeName'])
 usage=derive_typed_usage_context(image,read['typedUsage']['instruction']-base,label='storyWayPoint.host')
 listing=reference_list(image,pins,typed_request=usage,call_target=read['sourceTarget'],element_type=TYPE,count_limit=LIMIT)
 binding=dict(ownerType='Beyond.Gameplay.LevelData',fieldName='worldWayPointData',typeName=LIST,capability=CAP,
  readerMethodDefinition=usage['methodSpec'][0],sourceTargetRva=listing['witnessComponent']['callTargetRva'],countLimit=LIMIT,
  actualCallbackEqualsProvedChildRequired=True)
 cap=dict(typeName=TYPE,memberCount=len(PLAN),program=program,childCapabilities=child_caps,parentBinding=binding,
  nullAdmitted=True,positiveAdmitted=True,profileAdmitted=True,wholeGrammarAdmitted=False,finiteFloatProfile=True,
  ordinaryAdapterAdmitted=True,actualCallbackEqualsProvedChildRequired=True,liveFormatterSelectionObserved=False)
 from scripts.game_data.codecs.leveldata.current_waypoint import validate
 validate(cap);_publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema='endfield.story-waypoint-components.v1',status='validated-finite-current-waypoint-profile',nativeInputs=pins,
  capability=cap,source=source,pair=pair,adapter=adapter,children=proofs,
  parent=dict(declaration=declaration,source=read,typedRequest=usage,collection=listing,binding=binding),
  parentFieldAdmitted=False,wholeOwnerAdmitted=False,evidenceBoundary=dict(
   exact='Complete WayPoint9 source/lifecycle/ordinary adapter, actual independently proved WayLane16 list and UInt64 list, finite primitive/Vector3 program and actual LevelData list parent.',
   conditional='Exact compatible ready actual WayLane canonical callback, independently bound UInt32-array contexts/helpers, all list callbacks/providers and fresh count-sized typed storage. Counts and finite floats are explicit consumer limits; padding remains unserialized.',
   unresolved=['pathfinding/waypoint activation and runtime provider selection','whole owner/physical EOF']))))
