"""Finite Doodad/Guide owners with nominal integer vectors and exact list parents."""
import json
from scripts.game_data.memorypack import leveldata_int_list_sources as integers
from scripts.game_data.memorypack import leveldata_integer_vector_list_sources as pairs

DOODAD='Beyond.Gameplay.LevelDoodadGroupData'
GUIDE='Beyond.Gameplay.LevelDataGuideHintConfig'
VECTOR='UnityEngine.Vector3Int'
ULONGS='System.Collections.Generic.List`1<ulong>'
ULONG_CAP='story-integer-host-uint64-list'
CAPS={DOODAD:'story-doodad-group',GUIDE:'story-guide-hint'}
FIELDS={'doodadGroup':DOODAD,'guideHints':GUIDE}
LIMIT=4096
PLANS={
 DOODAD:(('centerId','ulong','scalar64-bits'),('centerShortId','int','scalar32'),('factoryPosition',VECTOR,'unity-vector3-int-raw12'),
  ('outerId',ULONGS,'uint64-list'),('outputSpeedPercentage',integers.TYPE,'int32-list'),('refreshGroupNumLevel',integers.TYPE,'int32-list'),
  ('refreshGroupUpperLimitLevel',integers.TYPE,'int32-list'),('upgradeSceneGrade',integers.TYPE,'int32-list'),
  ('upgradeSource','Beyond.GEnums.DoodadGroupUpgradeSource','scalar32')),
 GUIDE:(('beginGuideGroupId','string','byte-payload'),('defaultEnable','bool','bool-byte'),('endGuideGroupId','string','byte-payload'),
  ('fromInstKey','string','byte-payload'),('hintId','string','byte-payload'),('segments',pairs.LIST,'vector2-int-list'),
  ('startFace','int','scalar32'),('startPoint',VECTOR,'unity-vector3-int-raw12'),('toInstKey','string','byte-payload'),
  ('type','Beyond.Gameplay.GuideHintType','scalar32'))}
OPERATIONS={'byte-payload':'byte-payload','int32-list':integers.CAP,'vector2-int-list':pairs.CAP,'uint64-list':ULONG_CAP}


def validate_collection(key,cap):
 expected={integers.CAP:(integers.TYPE,'int',4),pairs.CAP:(pairs.LIST,pairs.TYPE,8),ULONG_CAP:(ULONGS,'ulong',8)}
 if key not in expected:raise ValueError('storyIntegerHosts.closed-collection')
 typename,element,width=expected[key]
 if (not isinstance(cap,dict)or(cap.get('typeName'),cap.get('elementType'),cap.get('countRange'))!=(typename,element,[-1,LIMIT])
  or any(type(cap.get(k))is not int or cap[k]!=v for k,v in dict(countLimit=LIMIT,headerBytes=4,elementWireBytes=width).items())
  or any(cap.get(k)is not True for k in('nullable','positiveCountsAdmitted','rawBitsPreserved','actualCallbackEqualsProvedChildRequired'))):
  raise ValueError('storyIntegerHosts.exact-collection-profile:'+key)
 if key==integers.CAP:
  if cap.get('wholeGrammarAdmitted')is not True or cap.get('liveFormatterSelectionObserved')is not False:
   raise ValueError('storyIntegerHosts.exact-Int32-list-source')
 elif key==pairs.CAP:
  if (type(cap.get('managedElementBytes'))is not int or cap['managedElementBytes']!=8
   or type(cap.get('elementRecordHeaderBytes'))is not int or cap['elementRecordHeaderBytes']!=0
   or cap.get('rawInt32Axes')!=['x','y']or cap.get('initiallyNullListRequired')is not True
   or cap.get('wholeGrammarAdmitted')is not True or cap.get('runtimeProviderSelectionObserved')is not False):
   raise ValueError('storyIntegerHosts.exact-Int2-list-source')
 elif cap.get('elementRawBits')!=64 or type(cap.get('elementRawBits'))is not int or cap.get('initiallyNullOutputRequired')is not True or cap.get('runtimeProviderSelectionObserved')is not False:
  raise ValueError('storyIntegerHosts.exact-UInt64-list-source')


def bind_collection(pins,join,child,key):
 cap=child.get('capabilities',{}).get(key,{});usage=join.get('typedRequest',{});spec=usage.get('methodSpec')
 if (child.get('nativeInputs')!=pins or usage.get('methodName')!='ReadPackable'or usage.get('methodArguments')!=[join.get('typeName')]
  or not isinstance(spec,(list,tuple))or not spec or type(spec[0])is not int or spec[0]<0
  or cap.get('typeName')!=join.get('typeName')or type(join.get('sourceTargetRva'))is not int or join['sourceTargetRva']<=0
  or type(cap.get('packableReaderMethodDefinition'))is not int or type(cap.get('packableReaderTargetRva'))is not int
  or(cap['packableReaderMethodDefinition'],cap['packableReaderTargetRva'])!=(spec[0],join['sourceTargetRva'])):
  raise ValueError('storyIntegerHosts.exact-collection-parent')
 validate_collection(key,cap)
 return dict(fieldName=join['fieldName'],typeName=join['typeName'],capability=key,countLimit=LIMIT,
  readerMethodDefinition=spec[0],sourceTargetRva=join['sourceTargetRva'],actualCallbackEqualsProvedChildRequired=True)


def bind_program(name,source,program,pending):
 plan=PLANS.get(name)
 if (plan is None or pending or source.get('wrappedType')!=name or not isinstance(program,dict)
  or[(r.get('fieldName'),r.get('declaredType'))for r in source.get('orderedSourceReads',[])]!=[(n,t)for n,t,k in plan]
  or type(program.get('memberCount'))is not int or program['memberCount']!=len(plan)
  or any(type(r.get('memberIndex'))is not int for r in program.get('reads',[]))
  or[(r.get('memberIndex'),r.get('fieldName'),r.get('kind'),r.get('childCapability'))for r in program.get('reads',[])]!=[
   (i,n,k,OPERATIONS.get(k))for i,(n,t,k)in enumerate(plan)]
  or program.get('requiredCapabilities')!=sorted({OPERATIONS[k]for n,t,k in plan if k in OPERATIONS})
  or[(r.get('fieldName'),r.get('typeName'),r.get('capability'))for r in program.get('childBindings',[])]!=[
   (n,t,OPERATIONS[k])for n,t,k in plan if k in('int32-list','uint64-list','vector2-int-list')]):
  raise ValueError('storyIntegerHosts.exact-finite-program:'+str(name))


def derive(image,pins,host):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.memorypack import generated_reader_sources,scalar_param_native as scalar,pooled_source_helper
 from scripts.game_data.memorypack.generated_record_components import compile_member_program
 from scripts.game_data.memorypack.levelscript_collection_sources import derive_ulong_list_component
 from scripts.game_data.memorypack.reference_list_induction_sources import derive as reference_list
 from scripts.game_data.memorypack.reference_param_profile import derive_pair
 from scripts.game_data.memorypack.reference_object_sources import derive_adapter
 need=lambda k,e,a:scalar.need('storyIntegerHosts',k,e,a)
 _publication_gate(image,pins);need('same-current-host',pins,host['nativeInputs']);base=image.pe.image_base;ctx=NativeReferenceContext(image)
 wrappers={w.wrapped_type:w for w in image.memorypack_wrappers.values()if w.wrapped_type in PLANS}
 need('two-finite-wrappers',set(PLANS),set(wrappers))
 generated=generated_reader_sources.derive_many(image,pins,[wrappers[n].name for n in PLANS]);records={};caps={};parents={}
 for name,result in zip(PLANS,generated['owners'],strict=True):
  need('complete-own-reader:'+name,'complete-reader-source-proved',result['status']if result['status']=='complete-reader-source-proved'else result)
  source=result['proof'];plan=PLANS[name]
  need('exact-own-field-order:'+name,[(n,t)for n,t,k in plan],[(r['fieldName'],r['declaredType'])for r in source['orderedSourceReads']])
  requests={};children={};collections={};child_caps={};proofs={}
  for read in source['orderedSourceReads']:
   index=read['memberIndex'];kind=plan[index][2]
   if kind not in('int32-list','uint64-list','vector2-int-list'):continue
   usage=derive_typed_usage_context(image,read['context']['instructionRva'],label='storyIntegerHosts.child')
   target=base+read['sourceTargetRva'];key=OPERATIONS[kind]
   if kind=='int32-list':proof=integers.derive(image,pins,typed_request=usage,call_target=target);cap=proof['capability']
   elif kind=='vector2-int-list':proof=pairs.derive(image,pins,typed_request=usage,call_target=target);cap=proof['capability']
   else:
    proof=derive_ulong_list_component(image,pins,typed_request=usage,call_target=target,count_limit=LIMIT)
    cap={k:proof[k]for k in('typeName','elementType','countRange','countLimit','headerBytes','elementWireBytes','elementRawBits',
     'nullable','positiveCountsAdmitted','rawBitsPreserved','initiallyNullOutputRequired','actualCallbackEqualsProvedChildRequired',
     'runtimeProviderSelectionObserved','packableReaderMethodDefinition','packableReaderTargetRva')}
   if key in child_caps:need('same-exact-child-profile:'+key,child_caps[key],cap)
   child_caps[key]=cap;requests[index]=usage;collections[read['declaredType']]=(key,kind,key)
   children[index]=dict(nativeInputs=pins,capabilities={key:cap});proofs[read['fieldName']]=proof
  program,pending=compile_member_program(source,pins,wrapper_name=wrappers[name].name,type_name=name,value4={},
   typed_requests=requests,collections=collections,collection_children=children,collection_binder=bind_collection)
  bind_program(name,source,program,pending)
  enums={}
  for member,declared,kind in plan:
   if kind!='scalar32'or declared=='int':continue
   need('own-enum-parent:'+declared,'System.Enum',ctx.parent(declared));field=ctx.field(declared+'::value__')
   need('own-enum-32backing:'+declared,True,field[1]in('int','uint'));enums[member]=dict(typeName=declared,backing=field[1],field=list(field))
  pool={read['fieldName']:pooled_source_helper.validate_on_image(image,base+read['sourceTargetRva'],pins)for read in source['orderedSourceReads']if read['kind']=='byte-payload'}
  pair=derive_pair(image,name);adapter=derive_adapter(image,pins,pair,wrappers[name])
  need('same-owned-original-getter:'+name,source['lifecycle']['GetValue']['method'],adapter['getterMethod'])
  need('same-concrete-callback:'+name,source['lifecycle']['concreteFormatter']['method'][0],pair['composition']['interfaces'][0]['formatterDeserializeMethodIndex'])
  need('full-owned-reference-output:'+name,True,source['lifecycle']['GetValue']['program'].get('fullReferenceOutput'))
  field_name,= [field for field,original in FIELDS.items()if original==name]
  declaration,read=next((f,r)for f,r in zip(host['fields'],host['program']['orderedReads'],strict=True)if f['name']==field_name)
  typename='System.Collections.Generic.List`1<'+name+'>';need('actual-host-closed-list:'+field_name,typename,declaration['typeName'])
  usage=derive_typed_usage_context(image,read['typedUsage']['instruction']-base,label='storyIntegerHosts.host')
  listing=reference_list(image,pins,typed_request=usage,call_target=read['sourceTarget'],element_type=name,count_limit=LIMIT)
  binding=dict(ownerType='Beyond.Gameplay.LevelData',fieldName=field_name,typeName=typename,capability=CAPS[name],countLimit=LIMIT,
   readerMethodDefinition=usage['methodSpec'][0],sourceTargetRva=listing['witnessComponent']['callTargetRva'],actualCallbackEqualsProvedChildRequired=True)
  cap=dict(typeName=name,memberCount=len(plan),program=program,enumBackings=enums,childCapabilities=child_caps,parentBinding=binding,
   nullAdmitted=True,positiveAdmitted=True,profileAdmitted=True,wholeGrammarAdmitted=False,ordinaryAdapterAdmitted=True,
   integerVectorSourceProved=True,actualCallbackEqualsProvedChildRequired=True,liveFormatterSelectionObserved=False)
  from scripts.game_data.codecs.leveldata.current_integer_hosts import validate
  validate(name,cap);caps[name]=cap;records[name]=dict(source=source,compiled=program,pair=pair,adapter=adapter,enums=enums,pooled=pool,children=proofs)
  parents[field_name]=dict(declaration=declaration,source=read,typedRequest=usage,collection=listing,binding=binding)
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema='endfield.story-integer-host-components.v1',status='validated-finite-current-integer-hosts',nativeInputs=pins,
  records=records,capabilities=caps,parents=parents,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
  evidenceBoundary=dict(exact='Complete finite Doodad9/Guide10 generated source/lifecycle/ordinary adapters, independently nominal Int3 capture/Advance/field/frame programs, exact Int32/UInt64/Int2 list source/callback/context/count joins and both actual host list parents.',
   conditional='Ready matching callbacks/coherent contexts/cache, initial count-sized lists, normal provider/allocation/helper/barrier effects and stable disjoint nonwrapping buffered storage; bounded counts remain an explicit projection condition.',
   unresolved=['runtime selection/activation or authored guidance behavior','whole owner physical EOF/public source receipts']))))
