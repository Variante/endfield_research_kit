"""Finite current factory-region graph with independent child and parent joins.

This owner uses the generated-reader compiler. Its explicit declarations do
not turn a field name, nominal width or old host receipt into a source proof.
"""
import json
from scripts.game_data.memorypack import leveldata_factory_mine_sources as mines
from scripts.game_data.memorypack import leveldata_leaf_record_sources as leaves
from scripts.game_data.memorypack import leveldata_ordinary_leaf_sources as ordinary
from scripts.game_data.memorypack import leveldata_int_list_sources as integers
from scripts.game_data.memorypack import leveldata_integer_vector_list_sources as pairs

PREFIX='Beyond.Gameplay.'
REGION=PREFIX+'LevelFactoryRegionData'
FIELD='factoryRegions'
CAP='story-factory-region-graph'
LIMIT=4096
NODE_LIMIT=32768
LIST=lambda name:'System.Collections.Generic.List`1<'+name+'>'
R=lambda suffix:PREFIX+suffix
REF=lambda field,name:(field,R(name),'factory-region-record')
SEQ=lambda field,name:(field,LIST(R(name)),'factory-region-record-list')
PLANS={
 R('InventorySystem+ItemInstData'):leaves.PLANS[R('InventorySystem+ItemInstData')],
 R('LevelFactoryRegionBusData'):ordinary.PLANS[R('LevelFactoryRegionBusData')],
 mines.TRANSFORM:mines.PLANS[mines.TRANSFORM],
 mines.MINE:tuple((n,t,'factory-region-record'if k=='factory-grid-transform'else k)for n,t,k in mines.PLANS[mines.MINE]),
 R('LevelFactoryRegionGridPathData'):(('initialFace','int','scalar32'),('segments',pairs.LIST,'vector2-int-list'),
  ('startPoint',pairs.TYPE,'unity-vector2-int-raw8')),
 R('LevelFactoryRegionBuildableRangeMaskEntry'):(('point',pairs.TYPE,'unity-vector2-int-raw8'),('val','int','scalar32')),
 R('LevelFactoryRegionAreaBound'):(('size','UnityEngine.Vector3Int','unity-vector3-int-raw12'),
  ('start','UnityEngine.Vector3Int','unity-vector3-int-raw12')),
 R('InventorySystem+ItemBundle'):(('count','int','scalar32'),('id','string','byte-payload'),
  REF('instData','InventorySystem+ItemInstData'),('instId','ulong','scalar64-bits')),
 R('LevelFactoryRegionInitialBelt'):(('beltId','string','byte-payload'),REF('gridPath','LevelFactoryRegionGridPathData')),
 R('LevelFactoryRegionInitialBuildingData'):(('broken','bool','bool-byte'),('buildingDataId','string','byte-payload'),
  SEQ('repairRequireItems','InventorySystem+ItemBundle'),REF('trans','LevelFactoryRegionGridTransform')),
 R('LevelFactoryRegionAreaSingleLevel'):(('level','int','scalar32'),SEQ('levelBounds','LevelFactoryRegionAreaBound')),
 R('LevelFactoryRegionBuildableRangeData'):(('initialMaskValue','int','scalar32'),
  SEQ('postMaks','LevelFactoryRegionBuildableRangeMaskEntry'),SEQ('preMasks','LevelFactoryRegionBuildableRangeMaskEntry'),
  ('rangeH','int','scalar32'),('rangeW','int','scalar32'),('rangeX','int','scalar32'),('rangeY','int','scalar32'),('regionLevel','int','scalar32')),
 R('LevelFactoryRegionAreaData'):(('fenceHeight','float','float32-bits'),('index','int','scalar32'),('isMain','bool','bool-byte'),
  ('levelCnt','int','scalar32'),SEQ('levelData','LevelFactoryRegionAreaSingleLevel'),('maxCnt','int','scalar32')),
 R('LevelFactorySettlementArea'):(('areaId','string','byte-payload'),SEQ('areas','LevelFactoryRegionAreaBound')),
 REGION:(('aoiRadiusType','Beyond.Gameplay.Core.AoiRadiusEnum','scalar32'),('belongLevelScriptId','ulong','scalar64-bits'),
  ('createState','Beyond.Gameplay.Core.CreateState','scalar32'),('dependencyGroupId','ulong','scalar64-bits'),
  ('entityDataIdKey','string','byte-payload'),('entityType','Beyond.Gameplay.Core.ObjectType','scalar32'),
  ('forceLoad','bool','bool-byte'),('keepCrossMap','bool','bool-byte'),('levelLogicId','ulong','scalar64-bits'),
  ('overrideSendDieEvent','bool','bool-byte'),('position','UnityEngine.Vector3','unity-vector3-raw12'),
  ('rotation','UnityEngine.Vector3','unity-vector3-raw12'),('scale','UnityEngine.Vector3','unity-vector3-raw12'),
  ('sendDieEvent','bool','bool-byte'),SEQ('areas','LevelFactoryRegionAreaData'),SEQ('buildableRange','LevelFactoryRegionBuildableRangeData'),
  SEQ('buses','LevelFactoryRegionBusData'),SEQ('cropPanels','LevelFactoryRegionAreaData'),SEQ('initialBelts','LevelFactoryRegionInitialBelt'),
  SEQ('initialBuildings','LevelFactoryRegionInitialBuildingData'),('isMainRegion','bool','bool-byte'),
  SEQ('mines','LevelFactoryRegionMineInstanceData'),('powerStorageCapacity','int','scalar32'),('regionId','string','byte-payload'),
  SEQ('roads','LevelFactoryRegionGridPathData'),SEQ('settlementAreas','LevelFactorySettlementArea')),
}
COLLECTIONS={declared:(pairs.TYPE if kind=='vector2-int-list'else'int'if kind=='int32-list'else declared[len(LIST(''))-1:-1],kind)
 for plan in PLANS.values()for field,declared,kind in plan if kind in('factory-region-record-list','int32-list','vector2-int-list')}


def record_key(name):
 if name not in PLANS:raise ValueError('factoryRegion.unknown-record:'+str(name))
 return 'story-factory-region-record:'+name


def list_key(name):
 if name not in COLLECTIONS:raise ValueError('factoryRegion.unknown-list:'+str(name))
 return 'story-factory-region-list:'+name


def operation(declared,kind):
 if kind=='factory-region-record':return record_key(declared)
 if kind in('factory-region-record-list','int32-list','vector2-int-list'):return list_key(declared)
 return 'byte-payload'if kind=='byte-payload'else None


def ordered_types():
 result=[];pending=list(PLANS)
 while pending:
  ready=[name for name in pending if all((declared if kind=='factory-region-record'else COLLECTIONS[declared][0])in result
   for field,declared,kind in PLANS[name]if kind in('factory-region-record','factory-region-record-list'))]
  if not ready:raise ValueError('factoryRegion.finite-acyclic-record-graph')
  result.extend(ready);pending=[n for n in pending if n not in ready]
 return result


def bind_program(name,source,program,pending):
 plan=PLANS.get(name)
 if(plan is None or pending or not isinstance(program,dict)or source.get('wrappedType')!=name
  or[(r.get('fieldName'),r.get('declaredType'))for r in source.get('orderedSourceReads',[])]!=[(n,t)for n,t,k in plan]
  or type(program.get('memberCount'))is not int or program['memberCount']!=len(plan)
  or any(type(r.get('memberIndex'))is not int for r in program.get('reads',[]))
  or[(r.get('memberIndex'),r.get('fieldName'),r.get('kind'),r.get('childCapability'))for r in program.get('reads',[])]!=[
   (j,n,k,operation(t,k))for j,(n,t,k)in enumerate(plan)]
  or program.get('requiredCapabilities')!=sorted({operation(t,k)for n,t,k in plan if operation(t,k)is not None})
  or[(r.get('fieldName'),r.get('typeName'),r.get('capability'))for r in program.get('childBindings',[])]!=[
   (n,t,operation(t,k))for n,t,k in plan if k in('factory-region-record','factory-region-record-list','int32-list','vector2-int-list')]):
  raise ValueError('factoryRegion.exact-finite-program:'+str(name))


def bind_reference(pins,join,child,key):
 name=join.get('typeName');cap=child.get('capabilities',{}).get(key,{});usage=join.get('typedRequest',{})
 if(name not in PLANS or key!=record_key(name)or child.get('nativeInputs')!=pins or cap.get('typeName')!=name
  or any(cap.get(k)is not True for k in('profileAdmitted','ordinaryAdapterAdmitted','actualCallbackEqualsProvedChildRequired'))
  or cap.get('wholeGrammarAdmitted')is not False or cap.get('liveFormatterSelectionObserved')is not False
  or usage.get('methodName')!='ReadValue'or usage.get('methodArguments')!=[name]
  or not isinstance(usage.get('methodSpec'),(tuple,list))or not usage['methodSpec']
  or type(usage['methodSpec'][0])is not int or usage['methodSpec'][0]<0
  or type(join.get('sourceTargetRva'))is not int or join['sourceTargetRva']<=0
  or type(cap.get('referenceReaderMethodDefinition'))is not int or type(cap.get('referenceReaderTargetRva'))is not int
  or(cap['referenceReaderMethodDefinition'],cap['referenceReaderTargetRva'])!=(usage['methodSpec'][0],join['sourceTargetRva'])):
  raise ValueError('factoryRegion.exact-reference-parent:'+str(name))
 return dict(fieldName=join['fieldName'],typeName=name,capability=key,readerMethodDefinition=usage['methodSpec'][0],
  sourceTargetRva=join['sourceTargetRva'],actualCallbackEqualsProvedChildRequired=True)


def bind_collection(pins,join,child,key):
 declared=join.get('typeName');cap=child.get('capabilities',{}).get(key,{});usage=join.get('typedRequest',{})
 if(declared not in COLLECTIONS or key!=list_key(declared)or child.get('nativeInputs')!=pins
  or cap.get('typeName')!=declared or(cap.get('elementType'),cap.get('wireKind'))!=COLLECTIONS[declared]
  or any(type(cap.get(k))is not int or cap[k]!=v for k,v in dict(countLimit=LIMIT,headerBytes=4).items())
  or cap.get('countRange')!=[-1,LIMIT]
  or any(cap.get(k)is not True for k in('nullable','positiveCountsAdmitted','elementGrammarAdmitted','initiallyNullListRequired','actualCallbackEqualsProvedChildRequired'))
  or cap.get('liveFormatterSelectionObserved')is not False
  or usage.get('methodName')!='ReadPackable'or usage.get('methodArguments')!=[declared]
  or not isinstance(usage.get('methodSpec'),(tuple,list))or not usage['methodSpec']
  or type(usage['methodSpec'][0])is not int or usage['methodSpec'][0]<0
  or type(join.get('sourceTargetRva'))is not int or join['sourceTargetRva']<=0
  or type(cap.get('packableReaderMethodDefinition'))is not int or type(cap.get('packableReaderTargetRva'))is not int
  or(cap['packableReaderMethodDefinition'],cap['packableReaderTargetRva'])!=(usage['methodSpec'][0],join['sourceTargetRva'])):
  raise ValueError('factoryRegion.exact-list-parent:'+str(declared))
 element,kind=COLLECTIONS[declared]
 if kind in('vector2-int-list','int32-list'):
  if(type(cap.get('elementWireBytes'))is not int or cap['elementWireBytes']!=(8 if kind=='vector2-int-list'else 4)
   or cap.get('rawBitsPreserved')is not True or cap.get('wholeGrammarAdmitted')is not True):
   raise ValueError('factoryRegion.exact-raw-element-list')
  if kind=='vector2-int-list'and(cap.get('rawInt32Axes')!=['x','y']or type(cap.get('managedElementBytes'))is not int
   or cap['managedElementBytes']!=8 or type(cap.get('elementRecordHeaderBytes'))is not int or cap['elementRecordHeaderBytes']!=0):
   raise ValueError('factoryRegion.exact-signed-Int2-list')
 return dict(fieldName=join['fieldName'],typeName=declared,capability=key,countLimit=LIMIT,
  readerMethodDefinition=usage['methodSpec'][0],sourceTargetRva=join['sourceTargetRva'],
  initiallyNullListRequired=True,actualCallbackEqualsProvedChildRequired=True)


def derive(image,pins,host):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.memorypack import generated_reader_sources,scalar_param_native as scalar,pooled_source_helper
 from scripts.game_data.memorypack.generated_record_components import compile_member_program
 from scripts.game_data.memorypack.leveldata_source_refusal import require_complete
 from scripts.game_data.memorypack.reference_list_induction_sources import derive as reference_list
 from scripts.game_data.memorypack.reference_param_profile import derive_pair
 from scripts.game_data.memorypack.reference_object_sources import derive_adapter
 from scripts.game_data.memorypack.skill_root_child_bindings import reference_reader_abi
 need=lambda k,e,a:scalar.need('factoryRegion',k,e,a)
 _publication_gate(image,pins);need('same-current-host',pins,host['nativeInputs']);base=image.pe.image_base;ctx=NativeReferenceContext(image)
 names=ordered_types();wrappers={w.wrapped_type:w for w in image.memorypack_wrappers.values()if w.wrapped_type in PLANS}
 need('exact-current-wrapper-set',set(PLANS),set(wrappers))
 generated=generated_reader_sources.derive_many(image,pins,[wrappers[n].name for n in names])
 sources={n:require_complete(r,validator='factoryRegion',type_name=n)for n,r in zip(names,generated['owners'],strict=True)}
 # Reject any known atomic/source transfer gap before repeating heavy child
 # adapters. Omitted independent children remain explicit pending rows here.
 for name in names:
  compile_member_program(sources[name],pins,wrapper_name=wrappers[name].name,type_name=name,value4={})
 abi=reference_reader_abi(image,pins);records={};caps={};list_caps={}
 for name in names:
  source=sources[name];plan=PLANS[name]
  need('exact-declared-field-order:'+name,[(n,t)for n,t,k in plan],[(r['fieldName'],r['declaredType'])for r in source['orderedSourceReads']])
  references={};reference_children={};collections={};collection_children={};requests={};proofs={}
  for read,(member,declared,kind)in zip(source['orderedSourceReads'],plan,strict=True):
   if kind not in('factory-region-record','factory-region-record-list','int32-list','vector2-int-list'):continue
   index=read['memberIndex'];key=operation(declared,kind)
   usage=derive_typed_usage_context(image,read['context']['instructionRva'],label='factoryRegion.actualChild');requests[index]=usage
   target=base+read['sourceTargetRva']
   if kind=='factory-region-record':
    references[declared]=(key,kind,key);reference_children[declared]=dict(nativeInputs=pins,capabilities={key:caps[declared]});continue
   element,_=COLLECTIONS[declared]
   proof=(integers.derive(image,pins,typed_request=usage,call_target=target,count_limit=LIMIT)if kind=='int32-list'else
    pairs.derive(image,pins,typed_request=usage,call_target=target)if kind=='vector2-int-list'else
    reference_list(image,pins,typed_request=usage,call_target=target,element_type=element,count_limit=LIMIT))
   raw=proof.get('capability',{})
   actual_target=raw['packableReaderTargetRva']if kind!='factory-region-record-list'else proof['witnessComponent']['callTargetRva']
   cap=dict(typeName=declared,elementType=element,wireKind=kind,countLimit=LIMIT,countRange=[-1,LIMIT],headerBytes=4,
    nullable=True,positiveCountsAdmitted=True,elementGrammarAdmitted=True,initiallyNullListRequired=True,
    actualCallbackEqualsProvedChildRequired=True,liveFormatterSelectionObserved=False,
    packableReaderMethodDefinition=usage['methodSpec'][0],packableReaderTargetRva=actual_target)
   if kind!='factory-region-record-list':
    for attr in('elementWireBytes','rawBitsPreserved','wholeGrammarAdmitted'):cap[attr]=raw[attr]
   if kind=='vector2-int-list':
    for attr in('rawInt32Axes','managedElementBytes','elementRecordHeaderBytes'):cap[attr]=raw[attr]
   if key in list_caps:need('same-independent-list-profile:'+declared,list_caps[key],cap)
   list_caps[key]=cap;collections[declared]=(key,kind,key);collection_children[index]=dict(nativeInputs=pins,capabilities={key:cap});proofs[member]=proof
  program,pending=compile_member_program(source,pins,wrapper_name=wrappers[name].name,type_name=name,value4={},typed_requests=requests,
   references=references,reference_children=reference_children,reference_binder=bind_reference,
   collections=collections,collection_children=collection_children,collection_binder=bind_collection)
  bind_program(name,source,program,pending);enums={}
  for member,declared,kind in plan:
   if kind!='scalar32'or declared=='int':continue
   need('nominal-enum:'+declared,'System.Enum',ctx.parent(declared));field=ctx.field(declared+'::value__')
   need('own-int32-enum:'+declared,True,field[1]in('int','uint'));enums[member]=dict(typeName=declared,backing=field[1],field=list(field))
  pair=derive_pair(image,name);adapter=derive_adapter(image,pins,pair,wrappers[name])
  need('whole-owned-original:'+name,True,source['lifecycle']['GetValue']['program'].get('fullReferenceOutput'))
  need('same-owned-getter:'+name,source['lifecycle']['GetValue']['method'],adapter['getterMethod'])
  need('same-owned-slot5:'+name,source['lifecycle']['concreteFormatter']['method'][0],pair['composition']['interfaces'][0]['formatterDeserializeMethodIndex'])
  pooled={r['fieldName']:pooled_source_helper.validate_on_image(image,base+r['sourceTargetRva'],pins)for r in source['orderedSourceReads']if r['kind']=='byte-payload'}
  caps[name]=dict(typeName=name,memberCount=len(plan),program=program,enumBackings=enums,nullAdmitted=True,positiveAdmitted=True,
   profileAdmitted=True,ordinaryAdapterAdmitted=True,actualCallbackEqualsProvedChildRequired=True,wholeGrammarAdmitted=False,
   liveFormatterSelectionObserved=False,referenceReaderMethodDefinition=abi['referenceReaderMethodDefinition'],referenceReaderTargetRva=abi['referenceReaderTargetRva'])
  records[name]=dict(source=source,compiled=program,pair=pair,adapter=adapter,enums=enums,pooled=pooled,children=proofs)
 field,read=next((f,r)for f,r in zip(host['fields'],host['program']['orderedReads'],strict=True)if f['name']==FIELD)
 need('exact-actual-host-list',LIST(REGION),field['typeName'])
 usage=derive_typed_usage_context(image,read['typedUsage']['instruction']-base,label='factoryRegion.actualHost')
 listing=reference_list(image,pins,typed_request=usage,call_target=read['sourceTarget'],element_type=REGION,count_limit=LIMIT)
 binding=dict(ownerType='Beyond.Gameplay.LevelData',fieldName=FIELD,typeName=LIST(REGION),capability=CAP,countLimit=LIMIT,
  readerMethodDefinition=usage['methodSpec'][0],sourceTargetRva=listing['witnessComponent']['callTargetRva'],
  initiallyNullListRequired=True,actualCallbackEqualsProvedChildRequired=True)
 cap=dict(typeName=REGION,capability=CAP,records=caps,collections=list_caps,countLimit=LIMIT,nodeLimit=NODE_LIMIT,
  parentBinding=binding,profileAdmitted=True,wholeGrammarAdmitted=False,liveFormatterSelectionObserved=False,
  actualCallbackEqualsProvedChildRequired=True,initiallyNullListsRequired=True,coherentWrapperStorageRequired=True,finiteFloatProfile=True)
 from scripts.game_data.codecs.leveldata.current_factory_region import validate
 validate(cap);_publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema='endfield.story-factory-region-components.v1',status='validated-conditional-finite-factory-region-graph',
  nativeInputs=pins,capability=cap,records=records,parent=dict(field=field,source=read,typedRequest=usage,collection=listing,binding=binding),
  referenceABI=abi,parentFieldAdmitted=False,wholeOwnerAdmitted=False,evidenceBoundary=dict(
   exact='Only fifteen named current records, each own complete generated sources/lifecycle/adapters/frames, actual child reference/list joins, nominal enums, signed Int2/Int3 fields and own Int32/Int2/reference lists, plus the actual LevelData factoryRegions parent.',
   conditional='Ready matching callbacks and coherent wrapper/original/cache/context, initially-null count-sized lists, normal compatible provider/allocation/helper/collector effects and disjoint buffered storage. Finite floats and resource limits define the projection.',
   unresolved=['runtime formatter selection or factory gameplay behavior','whole LevelData/Narrative physical EOF and public source receipts']))))
