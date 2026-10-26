"""Finite current map-region records with independently proved typed collections."""
import json
from scripts.game_data.memorypack import leveldata_int_list_sources as integers

REGION='Beyond.Gameplay.LevelMapRegionData'
SHAPE='Beyond.Gameplay.LevelMapShapeData'
CAP='story-map-region'
SHAPE_CAP='story-map-shape'
SHAPES='System.Collections.Generic.List`1<'+SHAPE+'>'
SHAPES_CAP='story-map-shape-list'
VECTORS='System.Collections.Generic.List`1<UnityEngine.Vector2>'
VECTORS_CAP='story-map-vector2-list'
LIMIT=4096
NODE_LIMIT=16384
PLANS={
 SHAPE:(('polyLineCenter','UnityEngine.Vector3','unity-vector3-raw12'),('polyLinePoints',VECTORS,'vector2-list'),
  ('position','UnityEngine.Vector3','unity-vector3-raw12'),('radius','float','float32-bits'),
  ('rotation','UnityEngine.Vector3','unity-vector3-raw12'),('shapeType','Beyond.GEnums.MapRegionShapeType','scalar32'),
  ('size','UnityEngine.Vector3','unity-vector3-raw12')),
 REGION:(('groupId','int','scalar32'),('hideByMistId','int','scalar32'),('isMist','bool','bool-byte'),
  ('levelId','string','byte-payload'),('mapRegionId','int','scalar32'),('mapRegionIdName','string','byte-payload'),
  ('mapRegionType','Beyond.Gameplay.MapRegionType','scalar32'),('priority','int','scalar32'),
  ('shapeList',SHAPES,'map-shape-list'),('tierIndex','int','scalar32'),('tierMapRegionIds',integers.TYPE,'int32-list'))}
OPERATIONS={'byte-payload':'byte-payload','vector2-list':VECTORS_CAP,'map-shape-list':SHAPES_CAP,'int32-list':integers.CAP}


def bind_program(name,source,program,pending):
 plan=PLANS.get(name)
 if (plan is None or pending or source.get('wrappedType')!=name or not isinstance(program,dict)
   or[(r.get('fieldName'),r.get('declaredType'))for r in source.get('orderedSourceReads',[])]!=[(n,t)for n,t,k in plan]
   or type(program.get('memberCount'))is not int or program['memberCount']!=len(plan)
   or any(type(r.get('memberIndex'))is not int for r in program.get('reads',[]))
   or[(r.get('memberIndex'),r.get('fieldName'),r.get('kind'),r.get('childCapability'))for r in program.get('reads',[])]!=[
    (index,n,k,OPERATIONS.get(k))for index,(n,t,k)in enumerate(plan)]
   or program.get('requiredCapabilities')!=sorted({OPERATIONS[k]for n,t,k in plan if k in OPERATIONS})
   or[(r.get('fieldName'),r.get('typeName'),r.get('capability'))for r in program.get('childBindings',[])]!=[
    (n,t,OPERATIONS[k])for n,t,k in plan if k in('vector2-list','map-shape-list','int32-list')]):
  raise ValueError('storyMapRegion.exact-finite-program:'+name)


def bind_collection(pins,join,child,capability):
 expected={VECTORS_CAP:(VECTORS,'UnityEngine.Vector2',8),SHAPES_CAP:(SHAPES,SHAPE,None),integers.CAP:(integers.TYPE,'int',4)}
 if capability not in expected:raise ValueError('storyMapRegion.closed-collection')
 typename,element,width=expected[capability];cap=child.get('capabilities',{}).get(capability,{});usage=join['typedRequest']
 if (child.get('nativeInputs')!=pins or join['typeName']!=typename or(cap.get('typeName'),cap.get('elementType'))!=(typename,element)
   or cap.get('countRange')!=[-1,LIMIT]or type(cap.get('countLimit'))is not int or cap['countLimit']!=LIMIT
   or any(cap.get(k)is not True for k in('nullable','positiveCountsAdmitted','actualCallbackEqualsProvedChildRequired'))
   or usage.get('methodName')!='ReadPackable'or usage.get('methodArguments')!=[typename]
   or(cap.get('packableReaderMethodDefinition'),cap.get('packableReaderTargetRva'))!=(usage['methodSpec'][0],join['sourceTargetRva'])
   or(width is not None and(type(cap.get('elementWireBytes'))is not int or cap['elementWireBytes']!=width))
   or(capability==VECTORS_CAP and any(cap.get(k)is not True for k in('rawBitsPreserved','finiteFloatProfile','initiallyNullListRequired')))
   or(capability==SHAPES_CAP and cap.get('finiteElementProfileAdmitted')is not True)):
  raise ValueError('storyMapRegion.exact-collection-parent:'+capability)
 return dict(fieldName=join['fieldName'],typeName=typename,capability=capability,countLimit=LIMIT,
  readerMethodDefinition=cap['packableReaderMethodDefinition'],sourceTargetRva=cap['packableReaderTargetRva'],
  actualCallbackEqualsProvedChildRequired=True)


def derive(image,pins,host):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.memorypack import generated_reader_sources,leveldata_vector2_list_sources,pooled_source_helper,scalar_param_native as scalar
 from scripts.game_data.memorypack.generated_record_components import compile_member_program
 from scripts.game_data.memorypack.reference_list_induction_sources import derive as reference_list
 from scripts.game_data.memorypack.reference_object_sources import derive_adapter
 from scripts.game_data.memorypack.reference_param_profile import derive_pair
 need=lambda k,e,a:scalar.need('storyMapRegion',k,e,a)
 _publication_gate(image,pins);need('same-current-host',pins,host['nativeInputs']);base=image.pe.image_base;ctx=NativeReferenceContext(image)
 wrappers={w.wrapped_type:w for w in image.memorypack_wrappers.values()if w.wrapped_type in PLANS}
 need('two-finite-wrappers',set(PLANS),set(wrappers));names=(SHAPE,REGION)
 generated=generated_reader_sources.derive_many(image,pins,[wrappers[name].name for name in names]);records={};caps={}
 for name,result in zip(names,generated['owners'],strict=True):
  need('complete-own-reader:'+name,'complete-reader-source-proved',result['status']if result['status']=='complete-reader-source-proved'else result)
  source=result['proof'];need('exact-nominal-order:'+name,[(n,t)for n,t,k in PLANS[name]],[(r['fieldName'],r['declaredType'])for r in source['orderedSourceReads']])
  requests={};collections={};children={};child_caps={};child_proofs={}
  for read in source['orderedSourceReads']:
   index=read['memberIndex'];kind=PLANS[name][index][2]
   if kind not in('vector2-list','int32-list','map-shape-list'):continue
   usage=derive_typed_usage_context(image,read['context']['instructionRva'],label='storyMapRegion.actualChild')
   requests[index]=usage;target=base+read['sourceTargetRva'];key=OPERATIONS[kind]
   if kind=='vector2-list':
    proof=leveldata_vector2_list_sources.derive_collection(image,pins,typed_request=usage,call_target=target)
    need('independent-vector2-wire',(8,8,True),(proof['capability']['elementWireBytes'],proof['capability']['managedElementBytes'],proof['capability']['wholeGrammarAdmitted']))
    need('source-count-bound-not-inferred',True,proof['capability']['countLimit']>=LIMIT)
    context=proof['context'];need('same-actual-vector2-request',usage,context['typedRequest'])
    cap=dict(typeName=VECTORS,elementType='UnityEngine.Vector2',elementWireBytes=8,managedElementBytes=8,
     countLimit=LIMIT,countRange=[-1,LIMIT],nullable=True,positiveCountsAdmitted=True,initiallyNullListRequired=True,
     rawBitsPreserved=True,finiteFloatProfile=True,actualCallbackEqualsProvedChildRequired=True,
     packableReaderMethodDefinition=usage['methodSpec'][0],packableReaderTargetRva=context['callTargetRva'])
   elif kind=='int32-list':proof=integers.derive(image,pins,typed_request=usage,call_target=target);cap=proof['capability']
   else:
    need('ordinary-shape-first',True,SHAPE in caps)
    proof=reference_list(image,pins,typed_request=usage,call_target=target,element_type=SHAPE,count_limit=LIMIT)
    cap=dict(typeName=SHAPES,elementType=SHAPE,countLimit=LIMIT,countRange=[-1,LIMIT],nullable=True,positiveCountsAdmitted=True,
     finiteElementProfileAdmitted=True,actualCallbackEqualsProvedChildRequired=True,
     packableReaderMethodDefinition=usage['methodSpec'][0],packableReaderTargetRva=proof['witnessComponent']['callTargetRva'])
    child_caps[SHAPE_CAP]=caps[SHAPE]
   collections[read['declaredType']]=(key,kind,key);children[index]=dict(nativeInputs=pins,capabilities={key:cap})
   child_caps[key]=cap;child_proofs[read['fieldName']]=proof
  program,pending=compile_member_program(source,pins,wrapper_name=wrappers[name].name,type_name=name,value4={},
   typed_requests=requests,collections=collections,collection_children=children,collection_binder=bind_collection)
  bind_program(name,source,program,pending)
  pool={read['fieldName']:pooled_source_helper.validate_on_image(image,base+read['sourceTargetRva'],pins)for read in source['orderedSourceReads']if read['kind']=='byte-payload'}
  enums={}
  for field,declared,kind in PLANS[name]:
   if kind!='scalar32'or declared=='int':continue
   need('nominal-enum-parent:'+declared,'System.Enum',ctx.parent(declared));value=ctx.field(declared+'::value__')
   need('exact-enum32:'+declared,True,value[1]in('int','uint'));enums[field]=dict(typeName=declared,backing=value[1],field=list(value))
  pair=derive_pair(image,name);adapter=derive_adapter(image,pins,pair,wrappers[name])
  need('same-owned-GetValue:'+name,source['lifecycle']['GetValue']['method'],adapter['getterMethod'])
  need('same-owned-concrete-callback:'+name,source['lifecycle']['concreteFormatter']['method'][0],pair['composition']['interfaces'][0]['formatterDeserializeMethodIndex'])
  need('full-owned-original-reference:'+name,True,source['lifecycle']['GetValue']['program'].get('fullReferenceOutput'))
  cap=dict(typeName=name,memberCount=len(PLANS[name]),program=program,enumBackings=enums,childCapabilities=child_caps,nodeLimit=NODE_LIMIT,
   nullAdmitted=True,positiveAdmitted=True,profileAdmitted=True,wholeGrammarAdmitted=False,finiteFloatProfile=True,
   ordinaryAdapterAdmitted=True,actualCallbackEqualsProvedChildRequired=True,liveFormatterSelectionObserved=False)
  caps[name]=cap;records[name]=dict(source=source,compiled=program,pooled=pool,enums=enums,pair=pair,adapter=adapter,children=child_proofs)
 declaration,read=next((f,r)for f,r in zip(host['fields'],host['program']['orderedReads'],strict=True)if f['name']=='mapVolumeDatas')
 need('exact-host-map-list','System.Collections.Generic.List`1<'+REGION+'>',declaration['typeName'])
 usage=derive_typed_usage_context(image,read['typedUsage']['instruction']-base,label='storyMapRegion.host')
 listing=reference_list(image,pins,typed_request=usage,call_target=read['sourceTarget'],element_type=REGION,count_limit=LIMIT)
 binding=dict(ownerType='Beyond.Gameplay.LevelData',fieldName='mapVolumeDatas',typeName=declaration['typeName'],capability=CAP,
  readerMethodDefinition=usage['methodSpec'][0],sourceTargetRva=listing['witnessComponent']['callTargetRva'],countLimit=LIMIT,
  actualCallbackEqualsProvedChildRequired=True)
 caps[REGION]['parentBinding']=binding
 from scripts.game_data.codecs.leveldata.current_map_region import validate
 validate(REGION,caps[REGION]);_publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema='endfield.story-map-region-components.v1',status='validated-finite-current-map-region-profile',nativeInputs=pins,
  records=records,capabilities=caps,parent=dict(declaration=declaration,source=read,typedRequest=usage,collection=listing,binding=binding),
  parentFieldAdmitted=False,wholeOwnerAdmitted=False,evidenceBoundary=dict(exact='Complete MapRegion11/MapShape7 generated sources/ordinary adapters, explicit finite typed wire plans, independently proved Vector2/Int32/shape collections and actual host parent.',
   conditional='Compatible current ready callbacks/providers, fresh count-sized lists, coherent original/cache, buffered disjoint nonwrapping storage and normal helper effects. Finite floats/counts/node budget are separate consumer bounds.',
   unresolved=['runtime provider/formatter selection','whole owner/physical EOF']))))
