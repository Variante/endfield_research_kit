"""Finite current occlusion grid/area composition; no runtime visibility claim."""
import json

from scripts.game_data.memorypack import leveldata_line_list_sources as lines,leveldata_condition_components as conditions

GRID='Beyond.Gameplay.FactoryDynamicRegionOccludeAreaGridData'
AREA='Beyond.Gameplay.LevelDynamicOccludeAreaData'
GRID_CAP='story-occlusion-grid'
AREA_CAP='story-occlusion-area'
GRID_LIST='System.Collections.Generic.List`1<'+GRID+'>'
GRID_LIST_CAP='story-occlusion-grid-list'
LIMIT=4096
NODE_LIMIT=16384
FIELD='dynamicOccludeAreas'
PLANS={
 GRID:(('height','int','scalar32'),('lineList',lines.LIST,'line-value-list'),('yPos','int','scalar32')),
 AREA:(('areaId','int','scalar32'),('condition',conditions.TYPE,'condition-runtime'),('gridData',GRID_LIST,'occlusion-grid-list'))}
OPERATIONS={'line-value-list':lines.LIST_CAP,'condition-runtime':conditions.CAP,'occlusion-grid-list':GRID_LIST_CAP}


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
   (n,t,OPERATIONS[k])for n,t,k in plan if k in OPERATIONS]):raise ValueError('storyOcclusion.exact-finite-program:'+str(name))


def bind_collection(pins,join,child,key):
 cap=child.get('capabilities',{}).get(key,{});request=join.get('typedRequest',{});spec=request.get('methodSpec')
 if (key not in(lines.LIST_CAP,GRID_LIST_CAP)or child.get('nativeInputs')!=pins
  or request.get('methodName')!='ReadPackable'or request.get('methodArguments')!=[join.get('typeName')]
  or not isinstance(spec,(list,tuple))or not spec or type(spec[0])is not int or spec[0]<0
  or type(join.get('sourceTargetRva'))is not int or join['sourceTargetRva']<=0
  or type(cap.get('packableReaderMethodDefinition'))is not int or type(cap.get('packableReaderTargetRva'))is not int
  or(cap['packableReaderMethodDefinition'],cap['packableReaderTargetRva'])!=(spec[0],join['sourceTargetRva'])):
  raise ValueError('storyOcclusion.exact-collection-request:'+str(key))
 if key==lines.LIST_CAP:
  from scripts.game_data.codecs.leveldata.current_line_value import validate_list
  validate_list(cap,child.get('capabilities',{}).get(lines.VALUE_CAP))
  if join['typeName']!=lines.LIST:raise ValueError('storyOcclusion.exact-Line-list')
 else:
  if (join['typeName']!=GRID_LIST or(cap.get('typeName'),cap.get('elementType'),cap.get('countRange'))!=(GRID_LIST,GRID,[-1,LIMIT])
   or any(type(cap.get(k))is not int or cap[k]!=v for k,v in dict(countLimit=LIMIT,headerBytes=4).items())
   or any(cap.get(k)is not True for k in('nullable','positiveCountsAdmitted','finiteElementProfileAdmitted',
    'actualCallbackEqualsProvedChildRequired','initiallyNullListRequired'))
   or cap.get('runtimeProviderSelectionObserved')is not False or cap.get('elementWireBytes')is not None):
   raise ValueError('storyOcclusion.exact-grid-list')
 return dict(fieldName=join['fieldName'],typeName=join['typeName'],capability=key,countLimit=LIMIT,
  readerMethodDefinition=spec[0],sourceTargetRva=join['sourceTargetRva'],
  **({'actualCallbackEqualsCanonicalRequired':True}if key==lines.LIST_CAP else{'actualCallbackEqualsProvedChildRequired':True}))


def derive(image,pins,host):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.memorypack import generated_reader_sources,scalar_param_native as scalar
 from scripts.game_data.memorypack.generated_record_components import compile_member_program
 from scripts.game_data.memorypack.leveldata_source_refusal import require_complete
 from scripts.game_data.memorypack.reference_list_induction_sources import derive as reference_list
 from scripts.game_data.memorypack.reference_object_sources import derive_adapter
 from scripts.game_data.memorypack.reference_param_profile import derive_pair
 check=lambda k,e,a:scalar.need('storyOcclusion',k,e,a)
 _publication_gate(image,pins);check('same-selected-host',pins,host['nativeInputs']);base=image.pe.image_base
 wrappers={w.wrapped_type:w for w in image.memorypack_wrappers.values()if w.wrapped_type in PLANS}
 check('two-exact-ordinary-wrappers',set(PLANS),set(wrappers));generated=generated_reader_sources.derive_many(image,pins,[wrappers[n].name for n in PLANS])
 condition=conditions.derive(image,pins);records={};caps={}
 for name,row in zip(PLANS,generated['owners'],strict=True):
  source=require_complete(row,validator='storyOcclusion',type_name=name)
  check('exact-own-order:'+name,[(n,t)for n,t,k in PLANS[name]],[(r['fieldName'],r['declaredType'])for r in source['orderedSourceReads']])
  requests={};collections={};components={};references={};reference_children={};child_caps={};proofs={}
  for read in source['orderedSourceReads']:
   index=read['memberIndex'];member,declared,kind=PLANS[name][index]
   if kind not in OPERATIONS:continue
   usage=derive_typed_usage_context(image,read['context']['instructionRva'],label='storyOcclusion.actualChild');requests[index]=usage
   key=OPERATIONS[kind]
   if kind=='condition-runtime':
    references[declared]=(key,kind,key);reference_children[declared]=dict(nativeInputs=pins,capabilities={key:condition['capability']})
    continue
   if kind=='line-value-list':
    proof=lines.derive(image,pins,typed_request=usage,call_target=base+read['sourceTargetRva'])
    component=proof;child_caps.update(proof['capabilities'])
   else:
    check('grid-first',True,GRID in caps)
    proof=reference_list(image,pins,typed_request=usage,call_target=base+read['sourceTargetRva'],element_type=GRID,count_limit=LIMIT)
    cap=dict(typeName=GRID_LIST,elementType=GRID,countRange=[-1,LIMIT],countLimit=LIMIT,headerBytes=4,elementWireBytes=None,
     nullable=True,positiveCountsAdmitted=True,finiteElementProfileAdmitted=True,actualCallbackEqualsProvedChildRequired=True,
     initiallyNullListRequired=True,runtimeProviderSelectionObserved=False,
     packableReaderMethodDefinition=usage['methodSpec'][0],packableReaderTargetRva=proof['witnessComponent']['callTargetRva'])
    component=dict(nativeInputs=pins,capabilities={key:cap});child_caps.update({key:cap,GRID_CAP:caps[GRID]})
   collections[declared]=(key,kind,key);components[index]=component;proofs[member]=proof
  program,pending=compile_member_program(source,pins,wrapper_name=wrappers[name].name,type_name=name,value4={},typed_requests=requests,
   collections=collections,collection_children=components,collection_binder=bind_collection,
   references=references,reference_children=reference_children,reference_binder=conditions.bind_reference)
  bind_program(name,source,program,pending);pair=derive_pair(image,name);adapter=derive_adapter(image,pins,pair,wrappers[name])
  check('same-owned-getter:'+name,source['lifecycle']['GetValue']['method'],adapter['getterMethod'])
  check('same-concrete-callback:'+name,source['lifecycle']['concreteFormatter']['method'][0],pair['composition']['interfaces'][0]['formatterDeserializeMethodIndex'])
  check('whole-original-reference:'+name,True,source['lifecycle']['GetValue']['program'].get('fullReferenceOutput'))
  caps[name]=dict(typeName=name,memberCount=3,program=program,childCapabilities=child_caps,nodeLimit=NODE_LIMIT,
   nullAdmitted=True,positiveAdmitted=True,profileAdmitted=True,ordinaryAdapterAdmitted=True,
   actualCallbackEqualsProvedChildRequired=True,wholeGrammarAdmitted=False,liveFormatterSelectionObserved=False)
  records[name]=dict(source=source,compiled=program,pair=pair,adapter=adapter,children=proofs)
 declaration,read=next((f,r)for f,r in zip(host['fields'],host['program']['orderedReads'],strict=True)if f['name']==FIELD)
 check('exact-actual-host-list','System.Collections.Generic.List`1<'+AREA+'>',declaration['typeName'])
 request=derive_typed_usage_context(image,read['typedUsage']['instruction']-base,label='storyOcclusion.actualHost')
 listing=reference_list(image,pins,typed_request=request,call_target=read['sourceTarget'],element_type=AREA,count_limit=LIMIT)
 binding=dict(ownerType='Beyond.Gameplay.LevelData',fieldName=FIELD,typeName=declaration['typeName'],capability=AREA_CAP,
  readerMethodDefinition=request['methodSpec'][0],sourceTargetRva=listing['witnessComponent']['callTargetRva'],countLimit=LIMIT,
  actualCallbackEqualsProvedChildRequired=True)
 caps[AREA]['parentBinding']=binding
 from scripts.game_data.codecs.leveldata.current_occlusion import validate
 validate(AREA,caps[AREA],condition['capability']);_publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema='endfield.story-occlusion-components.v1',status='validated-conditional-occlusion-records',nativeInputs=pins,
  records=records,capabilities=caps,condition=condition,parent=dict(declaration=declaration,source=read,typedRequest=request,collection=listing,binding=binding),
  parentFieldAdmitted=False,wholeOwnerAdmitted=False,evidenceBoundary=dict(
   exact='Own Grid3/Area3 ordinary sources/frames/adapters, exact Line value12 canonical/list source and full recursive ConditionRuntime components, independent grid reference-list induction and actual LevelData host parent.',
   conditional='Initialized matching callbacks/contexts, initially null count-sized lists, compatible normal allocation/provider/collector/helper effects and stable disjoint buffered storage. Resource limits are separate consumer bounds.',
   unresolved=['runtime visibility/condition evaluation or provider selection','whole owner physical EOF/public source receipts']))))
