"""Finite ordinary TrackingRouteInfo and its distinct raw/value/reference children.

The actual ReadPackable requests select fresh Bounds/Point value lists and an
independently owned Rectangle2D reference list. Direct Bounds36 never supplies
the canonical list element framing. Complete parent source, lifecycle, named
field transfers, four frames and ordinary adapter/GetValue remain mandatory.
Runtime callback selection, coherent initialized contexts, normal helpers and
disjoint storage are conditions; no MissionArea, host or physical EOF is owned.
"""
import copy
import json

from scripts.game_data.memorypack.leveldata_tracking_value_sources import BOUNDS,POINT
from scripts.game_data.memorypack import leveldata_tracking_components as values
from scripts.game_data.memorypack import leveldata_tracking_raw_sources as raw

SCHEMA='endfield.story-tracking-route-components.v1'
STATUS='validated-conditional-tracking-route'
TYPE='Beyond.Gameplay.TrackingRouteInfo'
RECTANGLE='Beyond.Gameplay.Rectangle2D'
CAPABILITY='story-tracking-route'
RECTANGLE_LIST='story-tracking-rectangle-list'
LIMIT=4096
NODE_LIMIT=16384
LIST=lambda name:'System.Collections.Generic.List`1<'+name+'>'
PLAN=(('boundingBox',BOUNDS,'tracking-bounds-raw36',None),
 ('ignoreYAxis','bool','bool-byte',None),
 ('listOfBoundingBoxes',LIST(BOUNDS),'tracking-bounds-list',values.LIST_CAPS[BOUNDS]),
 ('needBoundingBox','bool','bool-byte',None),('needMultiBoundingBox','bool','bool-byte',None),
 ('points',LIST(POINT),'tracking-point-list',values.LIST_CAPS[POINT]),
 ('segmentPlaneList',LIST(RECTANGLE),'tracking-rectangle-list',RECTANGLE_LIST),
 ('trackingPointIdxOutOfBoundingBox','int','scalar32',None))
COLLECTIONS={declared:(key,kind,key)for field,declared,kind,key in PLAN if key is not None}


def need(check,condition):
 if not condition:raise ValueError('storyTrackingRoute.'+check)


def same(left,right):
 return json.dumps(left,sort_keys=True,separators=(',',':'),allow_nan=False)==json.dumps(right,sort_keys=True,separators=(',',':'),allow_nan=False)


def bind_program(source,program,pending):
 need('exact-eight-owned-fields',not pending and source.get('wrappedType')==TYPE and isinstance(program,dict)
  and[(r.get('fieldName'),r.get('declaredType'))for r in source.get('orderedSourceReads',[])]==[(n,t)for n,t,k,c in PLAN]
  and type(program.get('memberCount'))is int and program['memberCount']==8
  and all(type(r.get('memberIndex'))is int for r in program.get('reads',[]))
  and[(r.get('memberIndex'),r.get('fieldName'),r.get('kind'),r.get('childCapability'))for r in program.get('reads',[])]==[
   (i,n,k,c)for i,(n,t,k,c)in enumerate(PLAN)]
  and program.get('requiredCapabilities')==sorted(c for n,t,k,c in PLAN if c is not None)
  and[(r.get('fieldName'),r.get('typeName'),r.get('capability'))for r in program.get('childBindings',[])]==[
   (n,t,c)for n,t,k,c in PLAN if c is not None])


def rectangle_list_capability(listing,rectangle,reader,pins):
 """Pure source/callback join; fresh native admission belongs to derive."""
 from scripts.game_data.memorypack.reference_list_induction_sources import _certificate
 from scripts.game_data.codecs.leveldata.current_leaf_record import validate
 need('same-finite-rectangle-owner',rectangle.get('schema')=='endfield.story-leaf-record-components.v1'
  and rectangle.get('status')=='validated-conditional-finite-leaf-records'and rectangle.get('nativeInputs')==pins
  and set(rectangle.get('records',{}))==set(rectangle.get('capabilities',{}))=={RECTANGLE})
 child=rectangle['capabilities'][RECTANGLE];validate(RECTANGLE,child)
 need('own-reference-element-list',listing.get('status')=='validated-bounded-reference-list-induction'
  and listing.get('nativeInputs')==pins and listing.get('elementType')==RECTANGLE
  and listing.get('countRange')==[-1,LIMIT]and all(type(n)is int for n in listing['countRange'])
  and all(listing.get(k)is False for k in('elementGrammarAdmitted','parentFieldAdmitted','wholeOwnerAdmitted')))
 witness=listing.get('witnessComponent',{});fresh=_certificate(witness,count_limit=LIMIT)
 need('both-complete-reference-list-loops',same(listing.get('induction'),fresh['induction'])
  and all(listing.get(k)is True for k in('nullable','freshListsAdmitted','reusedListsRequireCapacityAtLeastCount'))
  and type(listing.get('reusedListsRequireInitialCount'))is int and listing['reusedListsRequireInitialCount']==0)
 usage=witness.get('typedRequest',{});reference=witness.get('referenceSource',{});carrier=witness.get('closedCarrier',{})
 args=carrier.get('classArguments',[])
 need('exact-ordinary-Rectangle-argument',carrier.get('name')==LIST(RECTANGLE)and len(args)==1
  and args[0].get('name')==RECTANGLE and bytes.fromhex(args[0].get('rawHex',''))[10:12]==bytes((18,0)))
 need('exact-list-and-callback-Reader-identities',usage.get('tag')==6
  and(usage.get('typeName'),usage.get('methodName'),usage.get('classArguments'),usage.get('methodArguments'))==
   ('MemoryPack.MemoryPackReader','ReadPackable',[],[LIST(RECTANGLE)])
  and all(type(n)is int and n>=0 for n in(usage.get('methodSpec',[None])[0],witness.get('callTargetRva')))
  and reference.get('packableContext',{}).get('packableDefinition')==usage['methodSpec'][0]
  and type(reader.get('targetRva'))is int and reader['targetRva']>0
  and isinstance(reader.get('equivalentMethod'),list)and type(reader['equivalentMethod'][0])is int
  and reference.get('valueContext',{}).get('readerMethodDefinition')==reader['equivalentMethod'][0])
 record=rectangle['records'][RECTANGLE]
 need('ordinary-child-source-and-adapter',record.get('source',{}).get('wrappedType')==RECTANGLE
  and record.get('source',{}).get('completeSelectedCallerAdmitted')is True
  and record.get('source',{}).get('lifecycle',{}).get('GetValue',{}).get('program',{}).get('fullReferenceOutput')is True
  and record.get('adapter',{}).get('typeName')==RECTANGLE and record['adapter'].get('nativeInputs')==pins
  and same(record['source']['lifecycle']['GetValue']['method'],record['adapter'].get('getterMethod')))
 return dict(typeName=LIST(RECTANGLE),elementType=RECTANGLE,elementValueType=False,elementCapability=RECTANGLE,
  elementWireBytes=None,countLimit=LIMIT,countRange=[-1,LIMIT],headerBytes=4,nullable=True,
  positiveCountsAdmitted=True,elementGrammarAdmitted=True,initiallyNullListRequired=True,
  actualCallbackEqualsProvedChildRequired=True,profileAdmitted=True,
  readerMethodDefinition=usage['methodSpec'][0],sourceTargetRva=witness['callTargetRva'],
  referenceReaderMethodDefinition=reader['equivalentMethod'][0],referenceReaderTargetRva=reader['targetRva'],
  wholeGrammarAdmitted=False,liveFormatterSelectionObserved=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False)


def bind_collection(pins,join,child,capability):
 """Exact actual field request plus independently authenticated collection."""
 from scripts.game_data.codecs.leveldata.current_tracking import validate_list
 from scripts.game_data.codecs.leveldata.current_tracking_route import validate_rectangle_list
 choices=[(n,t,c)for n,t,k,c in PLAN if c==capability]
 need('one-finite-collection-field',len(choices)==1 and child.get('nativeInputs')==pins)
 field,closed,key=choices[0];cap=child.get('capabilities',{}).get(key,{});binding=child.get('actualBinding',{})
 if key==RECTANGLE_LIST:validate_rectangle_list(cap,child['capabilities'].get(RECTANGLE,{}));definition=cap['readerMethodDefinition'];target=cap['sourceTargetRva']
 else:
  name=BOUNDS if key==values.LIST_CAPS[BOUNDS]else POINT
  validate_list(cap,child['capabilities'].get(values.VALUE_CAPS[name],{}),name)
  definition=cap['packableReaderMethodDefinition'];target=cap['packableReaderTargetRva']
 usage=join.get('typedRequest',{});spec=usage.get('methodSpec')
 need('exact-parent-field-MethodSpec-target',join.get('fieldName')==field and join.get('typeName')==closed
  and same(usage,binding.get('typedRequest'))and type(join.get('sourceTargetRva'))is int and join['sourceTargetRva']==target
  and(usage.get('tag'),usage.get('typeName'),usage.get('methodName'),usage.get('classArguments'),usage.get('methodArguments'))==
   (6,'MemoryPack.MemoryPackReader','ReadPackable',[],[closed])
  and isinstance(spec,list)and len(spec)==3 and all(type(n)is int for n in spec)and spec[0]==definition)
 raw.bind_call(usage,binding.get('sourceInstruction'),source_target=child['imageBase']+target,base=child['imageBase'])
 return dict(fieldName=field,typeName=closed,capability=key,readerMethodDefinition=definition,sourceTargetRva=target,
  elementCapability=cap['elementCapability'],initiallyNullListRequired=True,actualCallbackEqualsProvedChildRequired=True)


def capability(program,tracking_caps,rectangle,rectangle_list,reader):
 """Finite declaration only; this function never grants native status."""
 return dict(typeName=TYPE,capability=CAPABILITY,memberCount=8,program=copy.deepcopy(program),
  trackingChildren=copy.deepcopy(tracking_caps),rectangle=copy.deepcopy(rectangle),rectangleCollection=copy.deepcopy(rectangle_list),
  countLimit=LIMIT,nodeLimit=NODE_LIMIT,nullAdmitted=True,positiveAdmitted=True,ordinaryAdapterAdmitted=True,
  profileAdmitted=True,actualCallbackEqualsProvedChildRequired=True,initiallyNullListsRequired=True,
  canonicalBooleanProfile=True,finiteRectangleFloatProfile=True,trackingRawBitsPreserved=True,
  referenceReaderMethodDefinition=reader['equivalentMethod'][0],referenceReaderTargetRva=reader['targetRva'],
  wholeGrammarAdmitted=False,liveFormatterSelectionObserved=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
  runtimeTrackingProved=False)


def derive(image,pins):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.memorypack import generated_reader_sources,leveldata_leaf_record_sources as leaf
 from scripts.game_data.memorypack import leveldata_tracking_composition as tracking,buff_ec_profiles_native as ec
 from scripts.game_data.memorypack.generated_record_components import compile_member_program
 from scripts.game_data.memorypack.reference_list_induction_sources import derive as reference_list
 from scripts.game_data.memorypack.reference_param_profile import derive_pair
 from scripts.game_data.memorypack.reference_object_sources import derive_adapter
 _publication_gate(image,pins);base=image.pe.image_base
 wrapper,=[w for w in image.memorypack_wrappers.values()if w.wrapped_type==TYPE]
 source=generated_reader_sources.derive(image,pins,wrapper.name)
 need('complete-own-route-reader',source.get('completeSelectedCallerAdmitted')is True)
 need('actual-eight-declarations',[(r.get('fieldName'),r.get('declaredType'))for r in source.get('orderedSourceReads',[])]==[(n,t)for n,t,k,c in PLAN])
 requests={};calls={}
 for index in(0,2,5,6):
  read=source['orderedSourceReads'][index]
  usage=derive_typed_usage_context(image,read['context']['instructionRva'],label='storyTrackingRoute.actualChild')
  need('same-selected-actual-request:'+str(index),same(usage['methodSpec'],read['context']['methodSpec'])and usage['instructionHex']==read['context']['instructionHex'])
  raw.bind_call(usage,read['instruction'],source_target=base+read['sourceTargetRva'],base=base)
  image.check_instruction_windows([read['instruction']],label='storyTrackingRoute.actualE8')
  requests[index]=usage;calls[index]=dict(typed_request=usage,call_target=base+read['sourceTargetRva'],source_instruction=read['instruction'])
 children=tracking.derive(image,pins,raw_request=requests[0],raw_target=calls[0]['call_target'],raw_instruction=calls[0]['source_instruction'],
  list_requests={BOUNDS:calls[2],POINT:calls[5]})
 rectangle=leaf.derive(image,pins,type_names=[RECTANGLE]);reader=ec.clone_facts(image,pins)['ReadValue']
 rectangle_listing=reference_list(image,pins,typed_request=requests[6],call_target=calls[6]['call_target'],element_type=RECTANGLE,count_limit=LIMIT)
 rectangle_cap=rectangle_list_capability(rectangle_listing,rectangle,reader,pins)
 envelopes={}
 for index,name in((2,BOUNDS),(5,POINT)):
  envelopes[index]=dict(nativeInputs=pins,imageBase=base,capabilities=children['capabilities'],
   actualBinding=children['proof']['actualListBindings'][name])
 envelopes[6]=dict(nativeInputs=pins,imageBase=base,capabilities={RECTANGLE_LIST:rectangle_cap,RECTANGLE:rectangle['capabilities'][RECTANGLE]},
  actualBinding=dict(typedRequest=requests[6],sourceInstruction=calls[6]['source_instruction']))
 program,pending=compile_member_program(source,pins,wrapper_name=wrapper.name,type_name=TYPE,value4={},
  typed_requests=requests,collections=COLLECTIONS,collection_children=envelopes,collection_binder=bind_collection)
 bind_program(source,program,pending)
 pair=derive_pair(image,TYPE);adapter=derive_adapter(image,pins,pair,wrapper)
 need('same-owned-route-getter',same(source['lifecycle']['GetValue']['method'],adapter['getterMethod'])
  and source['lifecycle']['GetValue']['program'].get('fullReferenceOutput')is True)
 need('same-owned-route-slot5',source['lifecycle']['concreteFormatter']['method'][0]==pair['composition']['interfaces'][0]['formatterDeserializeMethodIndex'])
 cap=capability(program,children['capabilities'],rectangle['capabilities'][RECTANGLE],rectangle_cap,reader)
 from scripts.game_data.codecs.leveldata.current_tracking_route import validate
 validate(cap);_publication_gate(image,pins)
 caps=dict(children['capabilities']);caps.update({CAPABILITY:cap,RECTANGLE:rectangle['capabilities'][RECTANGLE],RECTANGLE_LIST:rectangle_cap})
 return json.loads(json.dumps(dict(schema=SCHEMA,status=STATUS,nativeInputs=pins,capabilities=caps,
  proof=dict(source=source,compiled=program,pair=pair,adapter=adapter,tracking=children,rectangle=rectangle,
   rectangleList=rectangle_listing,referenceReader=reader,actualCollectionBindings=program['childBindings']),
  parentFieldAdmitted=False,wholeOwnerAdmitted=False,evidenceBoundary=dict(
   exact='Own complete Route8 source/four frames/lifecycle/ordinary adapter/GetValue, direct rawBounds36, independently canonical Bounds/Point lists and actual ordinary Rectangle2D callback/List source with bounded counted loops and exact parent MethodSpecs/E8/field transfers.',
   conditional=__doc__+' Fresh local list output, compatible initialized callback/context, normal typed allocations and helpers, canonical bool bytes and finite Rectangle floats are required. Tracking coordinate/enum bits are retained.',
   structuralOnly='Stored tracking route configuration; no path selection or runtime geometry behavior.',
   unresolved=['runtime callback/provider replacement','enclosing field/host source and physical EOF','public owner receipt']))))
