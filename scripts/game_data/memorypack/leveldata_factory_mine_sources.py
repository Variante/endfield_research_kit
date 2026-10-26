"""Finite mine/grid-transform records, with independently typed current children."""
import json
from scripts.game_data.memorypack import leveldata_int_list_sources as integers

TRANSFORM='Beyond.Gameplay.LevelFactoryRegionGridTransform'
MINE='Beyond.Gameplay.LevelFactoryRegionMineInstanceData'
FIELD='factoryMines'
LIMIT=4096
NODE_LIMIT=16384
KEYS={TRANSFORM:'story-factory-grid-transform',MINE:'story-factory-mine'}
PLANS={
 TRANSFORM:(('face','int','scalar32'),('position','UnityEngine.Vector2Int','unity-vector2-int-raw8'),
  ('voxelPosition','UnityEngine.Vector3Int','unity-vector3-int-raw12')),
 MINE:(('densityLevel',integers.TYPE,'int32-list'),('itemId','string','byte-payload'),('logicMineDataId','ulong','scalar64-bits'),
  ('mineHeight','float','float32-bits'),('offset','float','float32-bits'),('protoId','string','byte-payload'),
  ('trans',TRANSFORM,'factory-grid-transform'))}
OPERATIONS={'int32-list':integers.CAP,'byte-payload':'byte-payload','factory-grid-transform':KEYS[TRANSFORM]}


def bind_program(name,source,program,pending):
 plan=PLANS.get(name)
 if (plan is None or pending or not isinstance(program,dict)or source.get('wrappedType')!=name
  or[(r.get('fieldName'),r.get('declaredType'))for r in source.get('orderedSourceReads',[])]!=[(n,t)for n,t,k in plan]
  or type(program.get('memberCount'))is not int or program['memberCount']!=len(plan)
  or any(type(r.get('memberIndex'))is not int for r in program.get('reads',[]))
  or[(r.get('memberIndex'),r.get('fieldName'),r.get('kind'),r.get('childCapability'))for r in program.get('reads',[])]!=[
   (j,n,k,OPERATIONS.get(k))for j,(n,t,k)in enumerate(plan)]
  or program.get('requiredCapabilities')!=sorted({OPERATIONS[k]for n,t,k in plan if k in OPERATIONS})
  or[(r.get('fieldName'),r.get('typeName'),r.get('capability'))for r in program.get('childBindings',[])]!=[
   (n,t,OPERATIONS[k])for n,t,k in plan if k in('int32-list','factory-grid-transform')]):
  raise ValueError('storyFactoryMine.exact-finite-program:'+str(name))


def bind_reference(pins,join,child,key):
 usage=join.get('typedRequest',{});cap=child.get('capabilities',{}).get(key,{})
 if (key!=KEYS[TRANSFORM]or child.get('nativeInputs')!=pins or cap.get('typeName')!=TRANSFORM
  or cap.get('profileAdmitted')is not True or cap.get('ordinaryAdapterAdmitted')is not True
  or cap.get('actualCallbackEqualsProvedChildRequired')is not True or cap.get('wholeGrammarAdmitted')is not False
  or join.get('typeName')!=TRANSFORM or usage.get('methodName')!='ReadValue'or usage.get('methodArguments')!=[TRANSFORM]
  or not isinstance(usage.get('methodSpec'),(tuple,list))or not usage['methodSpec']
  or type(usage['methodSpec'][0])is not int or usage['methodSpec'][0]<0
  or type(join.get('sourceTargetRva'))is not int or join['sourceTargetRva']<=0
  or type(cap.get('referenceReaderMethodDefinition'))is not int or type(cap.get('referenceReaderTargetRva'))is not int
  or(cap['referenceReaderMethodDefinition'],cap['referenceReaderTargetRva'])!=(usage['methodSpec'][0],join['sourceTargetRva'])):
  raise ValueError('storyFactoryMine.exact-transform-reference-parent')
 return dict(fieldName=join['fieldName'],typeName=TRANSFORM,capability=key,
  readerMethodDefinition=usage['methodSpec'][0],sourceTargetRva=join['sourceTargetRva'],
  actualCallbackEqualsProvedChildRequired=True)


def derive(image,pins,host):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.memorypack import generated_reader_sources,scalar_param_native as scalar,pooled_source_helper
 from scripts.game_data.memorypack.generated_record_components import compile_member_program
 from scripts.game_data.memorypack.leveldata_source_refusal import require_complete
 from scripts.game_data.memorypack.leveldata_integer_host_sources import bind_collection
 from scripts.game_data.memorypack.reference_list_induction_sources import derive as reference_list
 from scripts.game_data.memorypack.reference_object_sources import derive_adapter
 from scripts.game_data.memorypack.reference_param_profile import derive_pair
 from scripts.game_data.memorypack.skill_root_child_bindings import reference_reader_abi
 need=lambda k,e,a:scalar.need('storyFactoryMine',k,e,a)
 _publication_gate(image,pins);need('same-selected-host',pins,host['nativeInputs']);base=image.pe.image_base
 wrappers={w.wrapped_type:w for w in image.memorypack_wrappers.values()if w.wrapped_type in PLANS}
 need('two-exact-current-wrappers',set(PLANS),set(wrappers));abi=reference_reader_abi(image,pins)
 generated=generated_reader_sources.derive_many(image,pins,[wrappers[n].name for n in PLANS]);records={};caps={}
 for name,row in zip(PLANS,generated['owners'],strict=True):
  source=require_complete(row,validator='storyFactoryMine',type_name=name);plan=PLANS[name]
  need('exact-own-order:'+name,[(n,t)for n,t,k in plan],[(r['fieldName'],r['declaredType'])for r in source['orderedSourceReads']])
  requests={};collections={};components={};references={};reference_children={};children={};proofs={}
  for read in source['orderedSourceReads']:
   j=read['memberIndex'];member,declared,kind=plan[j]
   if kind not in('int32-list','factory-grid-transform'):continue
   usage=derive_typed_usage_context(image,read['context']['instructionRva'],label='storyFactoryMine.actualChild');requests[j]=usage
   key=OPERATIONS[kind]
   if kind=='int32-list':
    proof=integers.derive(image,pins,typed_request=usage,call_target=base+read['sourceTargetRva'])
    children[key]=proof['capability'];collections[declared]=(key,kind,key)
    components[j]=dict(nativeInputs=pins,capabilities={key:proof['capability']});proofs[member]=proof
   else:
    need('transform-independently-complete',True,TRANSFORM in caps)
    children[key]=caps[TRANSFORM];references[declared]=(key,kind,key)
    reference_children[declared]=dict(nativeInputs=pins,capabilities={key:caps[TRANSFORM]})
  program,pending=compile_member_program(source,pins,wrapper_name=wrappers[name].name,type_name=name,value4={},
   typed_requests=requests,collections=collections,collection_children=components,collection_binder=bind_collection,
   references=references,reference_children=reference_children,reference_binder=bind_reference)
  bind_program(name,source,program,pending);pair=derive_pair(image,name);adapter=derive_adapter(image,pins,pair,wrappers[name])
  need('same-owned-original-getter:'+name,source['lifecycle']['GetValue']['method'],adapter['getterMethod'])
  need('same-concrete-callback:'+name,source['lifecycle']['concreteFormatter']['method'][0],pair['composition']['interfaces'][0]['formatterDeserializeMethodIndex'])
  need('whole-owned-original:'+name,True,source['lifecycle']['GetValue']['program'].get('fullReferenceOutput'))
  pooled={r['fieldName']:pooled_source_helper.validate_on_image(image,base+r['sourceTargetRva'],pins)for r in source['orderedSourceReads']if r['kind']=='byte-payload'}
  caps[name]=dict(typeName=name,memberCount=len(plan),program=program,childCapabilities=children,nodeLimit=NODE_LIMIT,
   nullAdmitted=True,positiveAdmitted=True,profileAdmitted=True,ordinaryAdapterAdmitted=True,
   actualCallbackEqualsProvedChildRequired=True,wholeGrammarAdmitted=False,liveFormatterSelectionObserved=False,
   integerVectorSourceProved=True,finiteFloatProfile=True,
   referenceReaderMethodDefinition=abi['referenceReaderMethodDefinition'],referenceReaderTargetRva=abi['referenceReaderTargetRva'])
  records[name]=dict(source=source,compiled=program,pair=pair,adapter=adapter,pooled=pooled,children=proofs)
 declaration,read=next((f,r)for f,r in zip(host['fields'],host['program']['orderedReads'],strict=True)if f['name']==FIELD)
 need('exact-actual-host-type','System.Collections.Generic.List`1<'+MINE+'>',declaration['typeName'])
 usage=derive_typed_usage_context(image,read['typedUsage']['instruction']-base,label='storyFactoryMine.actualHost')
 listing=reference_list(image,pins,typed_request=usage,call_target=read['sourceTarget'],element_type=MINE,count_limit=LIMIT)
 binding=dict(ownerType='Beyond.Gameplay.LevelData',fieldName=FIELD,typeName=declaration['typeName'],capability=KEYS[MINE],countLimit=LIMIT,
  readerMethodDefinition=usage['methodSpec'][0],sourceTargetRva=listing['witnessComponent']['callTargetRva'],actualCallbackEqualsProvedChildRequired=True)
 caps[MINE]['parentBinding']=binding
 from scripts.game_data.codecs.leveldata.current_factory_mine import validate
 validate(MINE,caps[MINE]);_publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema='endfield.story-factory-mine-components.v1',status='validated-conditional-factory-mine',nativeInputs=pins,
  records=records,capabilities=caps,referenceABI=abi,parent=dict(declaration=declaration,source=read,typedRequest=usage,collection=listing,binding=binding),
  parentFieldAdmitted=False,wholeOwnerAdmitted=False,evidenceBoundary=dict(
   exact='Own GridTransform3/Mine7 complete ordinary sources/adapters/all4 frames, distinct signed integer vectors, actual Int32 list source/callback and transform reference joins plus actual LevelData list parent.',
   conditional='Initialized matching callbacks/contexts, normal compatible helpers/provider/allocation/collector and coherent caches with stable disjoint buffered storage. Finite floats/counts/node budgets are projection bounds.',
   unresolved=['runtime factory/mining behavior or formatter selection','whole host physical EOF/public source receipt']))))
