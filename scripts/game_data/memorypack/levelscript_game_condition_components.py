"""Explicit current GameCondition transports, concrete records and recursion.

Fresh derivation owns each selected source. The pure composer joins those
facts without changing any source-only proof's boundary. Matching live
provider/callback selection and initially null union output remain conditions;
no runtime condition evaluation or enclosing Task field is admitted.
"""
import json

from scripts.game_data.memorypack import levelscript_condition_record_components as record_owner

SCHEMA='endfield.story-game-condition-components.v1'
CAPABILITY='story-game-condition'


def need(key,condition):
 if not condition:raise ValueError('storyGameConditionComponents.'+key)


def _route(row,definition):
 usage=row.get('typedRequest',{});bound=row.get('typedArgument',{});wrapper=row.get('wrapperName')
 need('actual-owned-wrapper-Packable-context',type(row.get('tag'))is int and 0<=row['tag']<65536
  and type(wrapper)is str and type(row.get('wrappedType'))is str
  and(usage.get('typeName'),usage.get('methodName'),usage.get('classArguments'),usage.get('methodArguments'))==
   ('MemoryPack.MemoryPackReader','ReadPackable',[],[wrapper])
  and isinstance(usage.get('methodSpec'),list)and len(usage['methodSpec'])==3
  and type(bound.get('methodDefinition'))is int and usage['methodSpec'][0]==bound['methodDefinition']==definition
  and bound.get('concreteTypeKind')==18 and bound.get('argumentType')==wrapper)
 return dict(tag=row['tag'],wrapperName=wrapper,typeName=row['wrappedType'],
  actualClosedReadPackableProved=True,actualWrapperCallbackEqualsProvedChildRequired=True)


def _union(name,type_name,rows,definition):
 from scripts.game_data.codecs.levelscript.current_game_condition import UNION_SCHEMA
 routes={}
 for row in rows:
  route=_route(row,definition);key=str(route['tag']);need('no-duplicate-union-tags',key not in routes);routes[key]=route
 return dict(schema=UNION_SCHEMA,typeName=type_name,wrapperName=name,routes=routes,
  headerModes=['short','extended','canonical-FF'],nullAdmitted=True,positiveAdmitted=True,
  actualClosedReadPackableProved=True,actualWrapperCallbackEqualsProvedChildRequired=True,
  nullIncomingWrapperRequired=True,liveFormatterSelectionObserved=False)


def compose(transport,nested,records,param_components,pins):
 """Pure closure check. Only derive freshly authenticates the supplied sources."""
 from scripts.game_data.codecs.levelscript.current_game_condition import SCHEMA as CAP_SCHEMA,validate
 need('same-complete-base-transport',transport.get('schema')=='endfield.levelscript-game-condition-transport.v1'
  and transport.get('status')=='validated-conditional-game-condition-transport'and transport.get('nativeInputs')==pins
  and transport.get('typeName')==record_owner.BASE and transport.get('concreteChildGrammarAdmitted')is False
  and transport.get('parentFieldAdmitted')is False and transport.get('wholeOwnerAdmitted')is False)
 definition=transport['referencePackable']['packableContext']['packableDefinition']
 top=transport['programs'];need('complete-finite-base-table',129<=len(top)<=512
  and[r.get('tag')for r in top]==list(range(len(top)))and all(type(r.get('tag'))is int for r in top))
 null=transport['canonicalFF']
 need('base-canonical-FF-and-inherited-conversions',null.get('canonicalFF')is True and null.get('clearedOutputBytes')==8
  and null.get('normalReturn')is True and null.get('entryRspRestored')is True
  and{r.get('wrapperName')for r in transport['inheritedConversions']}=={r['wrapperName']for r in top}
  and transport['pair']['composition']['interfaces'][0]['formatterDeserializeMethodIndex']==transport['slot5Method'][0])
 unions={transport['wrapperName']:_union(transport['wrapperName'],record_owner.BASE,top,definition)}
 for component in nested:
  need('same-source-only-nested-build',component.get('schema')=='endfield.story-nested-condition-source.v1'
   and component.get('nativeInputs')==pins and component.get('concreteChildGrammarAdmitted')is False)
  for owner in component['owners']:
   need('complete-own-nested-source',owner.get('status')=='complete-nested-union-transport-source'
    and owner.get('concreteChildGrammarAdmitted')is False and owner.get('wholeOwnerAdmitted')is False)
   ff=owner['canonicalFF'];need('nested-full-FF-output-and-frame',ff.get('canonicalFF')is True and ff.get('clearedOutputBytes')==8
    and ff.get('wholeReferenceOutput')is True and ff.get('normalReturn')is True and ff.get('entryRspRestored')is True)
   wrapper=owner['wrapperName'];need('no-duplicate-nested-owner',wrapper not in unions)
   unions[wrapper]=_union(wrapper,owner['wrappedType'],owner['cases'],definition)
 need('same-record-component-build',records.get('schema')==record_owner.SCHEMA and records.get('nativeInputs')==pins
  and records.get('unionSelectionAdmitted')is False and records.get('parentFieldAdmitted')is False
  and records.get('wholeOwnerAdmitted')is False and all(o.get('status')=='validated-conditional-condition-record'for o in records['owners']))
 concrete={};used_params=set();recursive=[]
 for owner in records['owners']:
  cap=owner['capability'];name=owner['wrapperName'];source=owner['proof']['source']
  need('same-exact-record-source-and-methods',name not in concrete and cap==records['capabilities'][record_owner.PREFIX+owner['typeName']]
   and(source['wrapperName'],source['wrappedType'],source['method'],source['lifecycle']['concreteFormatter']['method'])==
    (name,cap['typeName'],cap['readerMethod'],cap['formatterMethod'])
   and source.get('completeSelectedCallerAdmitted')is True and owner['proof']['actualConditionLineage'][-1]==record_owner.BASE)
  concrete[name]=cap
  for read in cap['program']['reads']:
   if read['kind']=='condition-param':used_params.add(read['childCapability'])
   if read['kind']=='game-condition-list':recursive.append(owner['proof']['recursiveList'])
 params={}
 for component in param_components:
  need('same-selected-Param-build',component.get('nativeInputs')==pins)
  for key,cap in component.get('capabilities',{}).items():
   if key not in used_params:continue
   need('no-overlapping-selected-Params',key not in params)
   params[key]=dict(componentSchema=component['schema'],capability=cap)
 need('all-required-Param-child-grammars',set(params)==used_params)
 need('exact-one-Combine-recursive-source',len(recursive)==1)
 from scripts.game_data.memorypack.levelscript_condition_list_sources import verify
 verify(recursive[0],pins);need('same-finite-recursive-count',recursive[0]['countLimit']==4096)
 cap=dict(schema=CAP_SCHEMA,typeName=record_owner.BASE,rootWrapper=transport['wrapperName'],unions=unions,records=concrete,params=params,
  countLimit=4096,nodeLimit=16384,depthLimit=128,paramElementLimit=10000,nullAdmitted=True,positiveAdmitted=True,
  storedGraphGrammarAdmitted=True,actualWrapperCallbackEqualsProvedConcreteRequired=True,
  actualRecursiveCallbackEqualsProvedBaseRequired=True,liveFormatterSelectionObserved=False,
  runtimeConditionEvaluationAdmitted=False,parentFieldAdmitted=False)
 validate(cap)
 return cap


def derive(image,pins):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.memorypack import levelscript_game_condition_union_sources as base_owner
 from scripts.game_data.memorypack import levelscript_condition_nested_sources as nested_owner
 from scripts.game_data.memorypack import levelscript_condition_all_params as param_owner
 from scripts.game_data.memorypack.levelscript_condition_list_sources import derive_member
 _publication_gate(image,pins);transport=base_owner.derive_transport(image,pins);wrappers=image.memorypack_wrappers
 parts=dict(transport=transport)
 def result(capability=None,holds=None):
  _publication_gate(image,pins)
  return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-current-game-condition'if capability is not None else'pendingReview',
   nativeInputs=pins,capabilities={CAPABILITY:capability}if capability is not None else{},proof=parts,holds=holds or[],
   parentFieldAdmitted=False,wholeOwnerAdmitted=False,runtimeConditionEvaluationAdmitted=False)))
 by_name={w.name:w for w in wrappers.values()};selected={r['wrapperName']for r in transport['programs']};nested=[];done=set()
 while True:
  pending=sorted(n for n in selected-done if by_name[n].frames_as_union)
  if not pending:break
  need('bounded-finite-nested-owner-domain',len(done)+len(pending)<=64)
  for start in range(0,len(pending),32):
   component=nested_owner.derive_many(image,pins,pending[start:start+32]);nested.append(component);parts['nested']=nested
   held=[o for o in component['owners']if o.get('status')!='complete-nested-union-transport-source']
   if held:return result(holds=[dict(stage='nested-source',**o)for o in held])
   for owner in component['owners']:
    selected.update(r['wrapperName']for r in owner['cases']);done.add(owner['wrapperName'])
 concrete=sorted(n for n in selected if not by_name[n].frames_as_union)
 parameter_types=sorted({m.declared_type for n in concrete for m in by_name[n].members if m.declared_type.startswith(param_owner.PREFIX)})
 params=param_owner.derive(image,pins,parameter_types=parameter_types);parts['params']=params
 if not params['selectedChildDomainComplete']:
  return result(holds=[dict(stage='Param-child',**o)for o in params['owners']if o.get('status')!='validated-conditional-Param-child'])
 # Bind the recursive collection at its own freshly selected complete source,
 # then let the record composer independently repeat the exact parent join.
 from scripts.game_data.memorypack.generated_reader_sources import derive_many as source_readers
 combine,=[n for n in concrete if by_name[n].wrapped_type=='Beyond.Gameplay.CombineCondition']
 own=source_readers(image,pins,[combine])['owners'][0]
 if own.get('status')!='complete-reader-source-proved':return result(holds=[dict(stage='Combine-source',**own)])
 read,=[r for r in own['proof']['orderedSourceReads']if r['fieldName']=='subConditions'and r['declaredType']==record_owner.LIST]
 listing=derive_member(image,pins,parent_source=own['proof'],member_index=read['memberIndex'],count_limit=4096);parts['recursiveList']=listing
 records=record_owner.derive_many(image,pins,wrapper_names=concrete,param_components=params['components'],recursive_list=listing);parts['records']=records
 held=[o for o in records['owners']if o.get('status')!='validated-conditional-condition-record']
 if held:return result(holds=[dict(stage='concrete-record',wrapperName=o.get('wrapperName'),typeName=o.get('typeName'),
  reason=o.get('reason'),pending=o.get('pending'),diagnostic=o.get('diagnostic'))for o in held])
 try:capability=compose(transport,nested,records,params['components'],pins)
 except(ValueError,KeyError,IndexError,TypeError)as error:
  return result(holds=[dict(stage='graph-composition',reason=str(error)[:2200])])
 return result(capability)
