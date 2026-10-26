"""Two explicit Module enum-list children, outside the default Skill domain.

Own nominal callback, constructor/provider/list/count/Add sources and actual
parent MethodSpec/E8 are re-proved. Enclosing fields, frames, Module selection,
recursive children and EOF belong to the containing owner.
"""
import json
from scripts.game_data.memorypack import nominal_enum_list_codec as codec

SCHEMA='endfield.story-module-enum-list-components.v1'
STATUS='validated-conditional-module-enum-lists'
DOMAIN='story-module-enum-lists'
WIRE='story-module-enum-list'
COUNT_LIMIT=4096
PLANS={
 'Beyond.Gameplay.Core.SuperPressureBoardState':dict(parentType='Beyond.Gameplay.SuperPressureBoardGroupData',
  fieldName='initialEntityStates',memberIndex=5,memberCount=9),
 'Beyond.Gameplay.TyphoeaArcheryStageType':dict(parentType='Beyond.Gameplay.TyphoeaArcheryUnitAdvancedData',
  fieldName='stageTypes',memberIndex=4,memberCount=5),
}


def need(check,condition,detail=None):
 if not condition:raise ValueError('storyModuleEnumLists.'+check+(':'+str(detail)[:1200]if detail is not None else''))


def list_type(name):
 need('finite-owned-enum',name in PLANS)
 return 'System.Collections.Generic.List`1<'+name+'>'


def list_capability(name):return 'skill-enum-list:'+name
def element_capability(name):return 'skill-enum-callback:'+name


def require_capability(cap,element,*,enum_type):
 need('finite-capability-enum',enum_type in PLANS)
 return codec.require_capability(cap,element,name=enum_type,count_limit=COUNT_LIMIT,
  element_capability=element_capability(enum_type))


def validate_component(component,pins,capability=None):
 need('own-source-component',type(component)is dict and component.get('schema')==SCHEMA
  and component.get('status')==STATUS and component.get('nativeInputs')==pins
  and component.get('domain')==DOMAIN and component.get('requiredExternalCapabilities')==[]
  and component.get('parentFieldAdmitted')is False and component.get('wholeOwnerAdmitted')is False)
 expected={key for name in PLANS for key in(list_capability(name),element_capability(name))}
 caps=component.get('capabilities',{})
 need('exact-two-nominal-list-and-callback-caps',type(caps)is dict and set(caps)==expected)
 for name in PLANS:
  cap=require_capability(caps[list_capability(name)],caps[element_capability(name)],enum_type=name)
  need('same-current-build:'+name,cap.get('nativeInputs')==pins)
 source=component.get('proof',{}).get('source',{})
 need('fresh-explicit-domain-source',source.get('schema')=='endfield.enum-optin-sources.v1'
  and source.get('status')=='validated-conditional-optin-enum-domain'and source.get('domain')==DOMAIN
  and source.get('nativeInputs')==pins and source.get('capabilities')==caps
  and source.get('domainDeclaration')==dict(nominalEnums=sorted(PLANS),collectionEnums=sorted(PLANS),countLimit=COUNT_LIMIT)
  and source.get('defaultSkillDomainChanged')is False)
 bindings=component.get('actualBindings',{})
 need('two-and-only-two-owned-parent-bindings',type(bindings)is dict and set(bindings)==set(PLANS))
 for name,plan in PLANS.items():
  row=bindings[name];usage=row.get('typedRequest',{});binding=row.get('sourceBinding',{});cap=caps[list_capability(name)]
  need('exact-actual-own-parent:'+name,all(row.get(k)==v for k,v in plan.items())
   and row.get('typeName')==list_type(name)and type(row.get('sourceTargetRva'))is int
   and row['sourceTargetRva']==cap['packableReaderTargetRva']
   and(usage.get('tag'),usage.get('typeName'),usage.get('methodName'),usage.get('classArguments'),usage.get('methodArguments'))==
    (6,'MemoryPack.MemoryPackReader','ReadPackable',[],[list_type(name)])
   and isinstance(usage.get('methodSpec'),list)and len(usage['methodSpec'])==3
   and usage['methodSpec'][0]==cap['packableReaderMethodDefinition']
   and binding.get('sourceRequest')==usage and binding.get('collectionCapability')==cap
   and binding.get('closedListType')==list_type(name)and binding.get('elementType')==name
   and binding.get('packableReaderMethodDefinition')==cap['packableReaderMethodDefinition']
   and binding.get('packableReaderTargetRva')==row['sourceTargetRva'])
  instruction=row.get('instruction');call=row.get('actualCall',{})
  need('actual-parent-call-shape:'+name,isinstance(instruction,list)and len(instruction)==2
   and type(instruction[0])is int and instruction[0]>=0 and type(instruction[1])is str)
  raw=bytes.fromhex(instruction[1])
  need('actual-parent-E8-and-source-identity:'+name,len(raw)==5 and raw[0]==232
   and instruction[0]+5+int.from_bytes(raw[1:],'little',signed=True)==row['sourceTargetRva']
   and call.get('sourceInstruction')==instruction and call.get('sourceTargetRva')==row['sourceTargetRva']
   and call.get('canonicalPointerIdentityClaimed')is False and call.get('parentFieldAdmitted')is False
   and call.get('incomingRequestAndReaderOriginsRequired')is True)
 if capability is not None:
  need('owned-list-capability',capability in{list_capability(name)for name in PLANS})
  return caps[capability]
 return caps


def _derive_on_source(image,pins,*,requests,source):
 """Fresh candidate source is still joined to the actual owned parent bytes."""
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.memorypack import enum_optin_native_sources as optin,primitive_param
 from scripts.game_data.memorypack.pointer_param import owned,methods
 from scripts.game_data.memorypack.unmanaged_enum_member_sources import bind_actual_call
 _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image)
 need('exact-two-explicit-parent-requests',type(requests)is dict and set(requests)==set(PLANS))
 bindings={};parents={};caps=source.get('capabilities',{})
 for name,plan in PLANS.items():
  request=requests[name]
  need('own-actual-request-declaration:'+name,type(request)is dict and all(request.get(k)==v for k,v in plan.items()if k!='memberCount')
   and request.get('typeName')==list_type(name))
  wrapper,=[w for w in image.memorypack_wrappers.values()if w.wrapped_type==plan['parentType']]
  need('exact-current-parent-member-count:'+name,len(wrapper.members)==plan['memberCount'])
  member=wrapper.members[plan['memberIndex']]
  need('exact-current-parent-member:'+name,member.name==plan['fieldName']and member.declared_type==list_type(name))
  method=methods(image,wrapper)['Deserialize'];primitive_param.reader_abi(image,ctx,method,wrapper)
  parent=owned(image,image.method_pointer_va(method));by={int(r['va'],16):r for r in parent['rows']}
  usage=request.get('typedRequest',{});site=usage.get('instructionRva');instruction=request.get('instruction');target=request.get('sourceTargetRva')
  need('owned-actual-MethodInfo-instruction:'+name,type(site)is int and base+site in by)
  actual=derive_typed_usage_context(image,site,label='storyModuleEnumLists.parent')
  need('same-exact-fresh-MethodInfo:'+name,actual==usage,dict(expectedCurrentRequest=actual,suppliedRequest=usage))
  need('owned-actual-call-instruction:'+name,isinstance(instruction,(list,tuple))and len(instruction)==2
   and type(instruction[0])is int and base+instruction[0]in by and type(target)is int and 0<target<1<<32
   and bytes.fromhex(instruction[1])==bytes.fromhex(by[base+instruction[0]]['bytes']))
  image.check_instruction_windows([instruction],label='storyModuleEnumLists.parentCall')
  actual_call=bind_actual_call(actual,instruction,source_target=base+target,base=base)
  binding=optin.bind_request(image,pins,source,typed_request=actual,call_target=base+target,enum_type=name)
  bindings[name]=dict(**plan,typeName=list_type(name),typedRequest=actual,instruction=list(instruction),
   sourceTargetRva=target,actualCall=actual_call,sourceBinding=binding)
  parents[name]=dict(method=[method.index,wrapper.name,'Deserialize',parent['pointer']-base],sourceWindows=parent['windows'])
 result=json.loads(json.dumps(dict(schema=SCHEMA,status=STATUS,nativeInputs=pins,domain=DOMAIN,capabilities=caps,
  requiredExternalCapabilities=[],actualBindings=bindings,proof=dict(source=source,parents=parents),
  parentFieldAdmitted=False,wholeOwnerAdmitted=False)))
 validate_component(result,pins);_publication_gate(image,pins);return result


def derive(image,pins,*,requests):
 from scripts.game_data.memorypack import enum_optin_native_sources as optin
 return _derive_on_source(image,pins,requests=requests,source=optin.derive(image,pins,domain=DOMAIN))


def bind(pins,join,component,capability):
 cap=validate_component(component,pins,capability)
 name,=[n for n in PLANS if list_capability(n)==capability];owned=component['actualBindings'][name]
 need('exact-actual-parent-collection-join',type(join)is dict
  and all(join.get(k)==owned[k]for k in('parentType','fieldName','memberIndex','typeName','typedRequest','sourceTargetRva'))
  and('instruction'not in join or join['instruction']==owned['instruction']))
 return dict(operation=WIRE,childCapability=capability,elementCapability=element_capability(name),
  collectionCapability=cap,sourceBinding=owned['sourceBinding'],parentFieldAdmitted=False,wholeOwnerAdmitted=False)


def read(reader,capability,*,budget=None,depth=0):
 names=[name for name in PLANS if list_capability(name)==capability]
 need('explicit-owned-cursor-capability',len(names)==1);name,=names
 return codec.read(reader,capability=capability,element_capability=element_capability(name),name=name,
  count_limit=COUNT_LIMIT,budget=budget,depth=depth)
