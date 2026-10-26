"""Finite current NPC groups and slots; authored placements do not prove patrols."""
import json
from scripts.game_data.memorypack import leveldata_vector3_list_sources as vectors

GROUP='Beyond.Gameplay.LevelNpcGroupData'
SLOT='Beyond.Gameplay.NpcGroupSlot'
CAP='story-npc-group'
SLOT_CAP='story-npc-group-slot'
SLOTS='System.Collections.Generic.List`1<'+SLOT+'>'
SLOTS_CAP='story-npc-group-slot-list'
LIMIT=4096
NODE_LIMIT=16384
PLANS={
 SLOT:(('inversePositions',vectors.LIST,'vector3-list'),('isLeader','bool','bool-byte'),('npcId','string','byte-payload'),
  ('positions',vectors.LIST,'vector3-list')),
 GROUP:(('groupId','ulong','scalar64-bits'),('patrolId','int','scalar32'),('patrolLoopType','Beyond.Gameplay.Core.PatrolLoopType','scalar32'),
  ('slots',SLOTS,'npc-slot-list'),('templateId','string','byte-payload'))}
OPERATIONS={'byte-payload':'byte-payload','vector3-list':vectors.CAP,'npc-slot-list':SLOTS_CAP}


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
    (n,t,OPERATIONS[k])for n,t,k in plan if k in('vector3-list','npc-slot-list')]):
  raise ValueError('storyNpcGroup.exact-finite-program:'+name)


def bind_collection(pins,join,child,capability):
 expected={vectors.CAP:(vectors.LIST,vectors.TYPE,12),SLOTS_CAP:(SLOTS,SLOT,None)}
 if capability not in expected:raise ValueError('storyNpcGroup.closed-collection')
 typename,element,width=expected[capability];cap=child.get('capabilities',{}).get(capability,{});usage=join['typedRequest']
 if (child.get('nativeInputs')!=pins or join['typeName']!=typename or(cap.get('typeName'),cap.get('elementType'))!=(typename,element)
   or cap.get('countRange')!=[-1,LIMIT]or type(cap.get('countLimit'))is not int or cap['countLimit']!=LIMIT
   or any(cap.get(k)is not True for k in('nullable','positiveCountsAdmitted','actualCallbackEqualsProvedChildRequired'))
   or usage.get('methodName')!='ReadPackable'or usage.get('methodArguments')!=[typename]
   or(cap.get('packableReaderMethodDefinition'),cap.get('packableReaderTargetRva'))!=(usage['methodSpec'][0],join['sourceTargetRva'])
   or(width is not None and(type(cap.get('elementWireBytes'))is not int or cap['elementWireBytes']!=width))
   or(capability==vectors.CAP and any(cap.get(k)is not True for k in('rawBitsPreserved','finiteFloatProfile','initiallyNullListRequired')))
   or(capability==SLOTS_CAP and cap.get('finiteElementProfileAdmitted')is not True)):
  raise ValueError('storyNpcGroup.exact-collection-parent:'+capability)
 return dict(fieldName=join['fieldName'],typeName=typename,capability=capability,countLimit=LIMIT,
  readerMethodDefinition=cap['packableReaderMethodDefinition'],sourceTargetRva=cap['packableReaderTargetRva'],
  actualCallbackEqualsProvedChildRequired=True)


def derive(image,pins,host):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.memorypack import generated_reader_sources,pooled_source_helper,scalar_param_native as scalar
 from scripts.game_data.memorypack.generated_record_components import compile_member_program
 from scripts.game_data.memorypack.reference_list_induction_sources import derive as reference_list
 from scripts.game_data.memorypack.reference_object_sources import derive_adapter
 from scripts.game_data.memorypack.reference_param_profile import derive_pair
 need=lambda k,e,a:scalar.need('storyNpcGroup',k,e,a)
 _publication_gate(image,pins);need('same-current-host',pins,host['nativeInputs']);base=image.pe.image_base;ctx=NativeReferenceContext(image)
 wrappers={w.wrapped_type:w for w in image.memorypack_wrappers.values()if w.wrapped_type in PLANS}
 need('two-finite-wrappers',set(PLANS),set(wrappers));names=(SLOT,GROUP)
 generated=generated_reader_sources.derive_many(image,pins,[wrappers[name].name for name in names]);records={};caps={}
 for name,result in zip(names,generated['owners'],strict=True):
  need('complete-own-reader:'+name,'complete-reader-source-proved',result['status']if result['status']=='complete-reader-source-proved'else result)
  source=result['proof'];need('exact-nominal-order:'+name,[(n,t)for n,t,k in PLANS[name]],[(r['fieldName'],r['declaredType'])for r in source['orderedSourceReads']])
  requests={};collections={};children={};child_caps={};child_proofs={}
  for read in source['orderedSourceReads']:
   index=read['memberIndex'];kind=PLANS[name][index][2]
   if kind not in('vector3-list','npc-slot-list'):continue
   usage=derive_typed_usage_context(image,read['context']['instructionRva'],label='storyNpcGroup.actualChild')
   requests[index]=usage;target=base+read['sourceTargetRva'];key=OPERATIONS[kind]
   if kind=='vector3-list':
    proof=vectors.derive(image,pins,typed_request=usage,call_target=target);cap=proof['capability']
   else:
    need('ordinary-slot-first',True,SLOT in caps)
    proof=reference_list(image,pins,typed_request=usage,call_target=target,element_type=SLOT,count_limit=LIMIT)
    cap=dict(typeName=SLOTS,elementType=SLOT,countLimit=LIMIT,countRange=[-1,LIMIT],nullable=True,positiveCountsAdmitted=True,
     finiteElementProfileAdmitted=True,actualCallbackEqualsProvedChildRequired=True,
     packableReaderMethodDefinition=usage['methodSpec'][0],packableReaderTargetRva=proof['witnessComponent']['callTargetRva'])
    child_caps[SLOT_CAP]=caps[SLOT]
   if key in child_caps:need('same-independent-collection:'+key,child_caps[key],cap)
   collections[read['declaredType']]=(key,kind,key);children[index]=dict(nativeInputs=pins,capabilities={key:cap})
   child_caps[key]=cap;child_proofs[read['fieldName']]=proof
  program,pending=compile_member_program(source,pins,wrapper_name=wrappers[name].name,type_name=name,value4={},
   typed_requests=requests,collections=collections,collection_children=children,collection_binder=bind_collection)
  bind_program(name,source,program,pending)
  pool={read['fieldName']:pooled_source_helper.validate_on_image(image,base+read['sourceTargetRva'],pins)for read in source['orderedSourceReads']if read['kind']=='byte-payload'}
  enums={}
  for field,declared,kind in PLANS[name]:
   if kind!='scalar32'or declared=='int':continue
   need('nominal-enum:'+declared,'System.Enum',ctx.parent(declared));value=ctx.field(declared+'::value__')
   need('actual-four-byte-enum:'+declared,True,value[1]in('int','uint'));enums[field]=dict(typeName=declared,backing=value[1],field=list(value))
  pair=derive_pair(image,name);adapter=derive_adapter(image,pins,pair,wrappers[name])
  need('same-owned-GetValue:'+name,source['lifecycle']['GetValue']['method'],adapter['getterMethod'])
  need('same-owned-concrete-callback:'+name,source['lifecycle']['concreteFormatter']['method'][0],pair['composition']['interfaces'][0]['formatterDeserializeMethodIndex'])
  need('full-owned-original-reference:'+name,True,source['lifecycle']['GetValue']['program'].get('fullReferenceOutput'))
  cap=dict(typeName=name,memberCount=len(PLANS[name]),program=program,enumBackings=enums,childCapabilities=child_caps,nodeLimit=NODE_LIMIT,
   nullAdmitted=True,positiveAdmitted=True,profileAdmitted=True,wholeGrammarAdmitted=False,finiteFloatProfile=True,
   ordinaryAdapterAdmitted=True,actualCallbackEqualsProvedChildRequired=True,liveFormatterSelectionObserved=False)
  caps[name]=cap;records[name]=dict(source=source,compiled=program,pooled=pool,enums=enums,pair=pair,adapter=adapter,children=child_proofs)
 declaration,read=next((f,r)for f,r in zip(host['fields'],host['program']['orderedReads'],strict=True)if f['name']=='npcGroup')
 need('exact-host-group-list','System.Collections.Generic.List`1<'+GROUP+'>',declaration['typeName'])
 usage=derive_typed_usage_context(image,read['typedUsage']['instruction']-base,label='storyNpcGroup.host')
 listing=reference_list(image,pins,typed_request=usage,call_target=read['sourceTarget'],element_type=GROUP,count_limit=LIMIT)
 binding=dict(ownerType='Beyond.Gameplay.LevelData',fieldName='npcGroup',typeName=declaration['typeName'],capability=CAP,
  readerMethodDefinition=usage['methodSpec'][0],sourceTargetRva=listing['witnessComponent']['callTargetRva'],countLimit=LIMIT,
  actualCallbackEqualsProvedChildRequired=True)
 caps[GROUP]['parentBinding']=binding
 from scripts.game_data.codecs.leveldata.current_npc_group import validate
 validate(GROUP,caps[GROUP]);_publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema='endfield.story-npc-group-components.v1',status='validated-finite-current-npc-group-profile',nativeInputs=pins,
  records=records,capabilities=caps,parent=dict(declaration=declaration,source=read,typedRequest=usage,collection=listing,binding=binding),
  parentFieldAdmitted=False,wholeOwnerAdmitted=False,evidenceBoundary=dict(exact='Complete NpcGroup5/Slot4 generated sources/ordinary adapters, explicit finite typed wire plans, independently current Vector3/slot lists and actual host parent.',
   conditional='Compatible ready callbacks/providers, fresh count-sized lists, coherent original/cache, buffered disjoint nonwrapping storage and normal helper effects. Finite floats/counts/node budget remain separate consumer bounds.',
   unresolved=['runtime provider/formatter selection','group activation/patrol behavior','whole owner/physical EOF']))))
