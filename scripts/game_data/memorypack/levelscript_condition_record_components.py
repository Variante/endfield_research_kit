"""Concrete GameCondition wrapper programs with explicit Param children.

The union reads these wrappers through ReadPackable. Their independently
proved static reader, wrapper factory and concrete formatter supply that
boundary; an unrelated Original eager adapter is not required here. The
union's actual closed callback and inherited Original conversion remain
separate joins. No source census or type spelling activates a record.
"""
import copy
import json

from scripts.game_data.memorypack.levelscript_condition_param_sources import CAP_PREFIX

SCHEMA='endfield.story-condition-record-components.v1'
CAP_SCHEMA='endfield.story-condition-record-capability.v1'
BASE='Beyond.Gameplay.GameCondition'
LIST='System.Collections.Generic.List`1<'+BASE+'>'
LIST_CAP='story-game-condition-recursive-list'
PREFIX='story-condition-record:'
LABEL='storyConditionRecords'


def need(key,condition):
 if not condition:raise ValueError(LABEL+'.'+key)


def _children(components,pins):
 from scripts.game_data.memorypack.levelscript_condition_param_bindings import _validate_capability
 need('explicit-independent-Param-components',isinstance(components,(list,tuple)))
 selected={}
 for component in components:
  need('same-Param-child-native-inputs',isinstance(component,dict)and component.get('nativeInputs')==pins)
  for key,cap in component.get('capabilities',{}).items():
   _validate_capability(component,key);name=cap['typeName']
   need('exact-Param-key-and-no-overlap',key==CAP_PREFIX+name and name not in selected)
   selected[name]=(component,key)
 return selected


def _collection_binder(pins,join,component,capability):
 from scripts.game_data.memorypack.levelscript_condition_list_sources import bind_request
 need('only-owned-recursive-list-operation',capability==LIST_CAP)
 binding=bind_request(pins,dict(join,sourceInstruction=component.get('parentBinding',{}).get('sourceInstruction')),component)
 return dict(binding,capability=capability)


def compile_record(source,pins,*,param_components,typed_requests,recursive_list=None):
 """Pure compiler; fresh request, pool and nominal joins belong to derive_many."""
 from scripts.game_data.memorypack.generated_record_components import compile_member_program
 from scripts.game_data.memorypack.levelscript_condition_param_bindings import bind_reference
 selected=_children(param_components,pins);references={};children={};collections={};collection_children={}
 reads=source.get('orderedSourceReads',[])
 for read in reads:
  name=read['declaredType']
  if name in selected:
   component,key=selected[name];references[name]=(key,'condition-param',key);children[name]=component
  elif name==LIST and recursive_list is not None:
   need('only-CombineCondition-recursive-field',(source.get('wrappedType'),read.get('fieldName'))==
    ('Beyond.Gameplay.CombineCondition','subConditions'))
   joined=recursive_list.get('parentBinding',{})
   need('same-actual-recursive-list-parent-site',joined.get('fieldName')==read['fieldName']
    and joined.get('typeName')==LIST and joined.get('sourceInstruction')==read['instruction']
    and joined.get('typedRequest')==typed_requests.get(read['memberIndex'])
    and joined.get('sourceTargetRva')==read['sourceTargetRva'])
   collections[name]=(LIST_CAP,'game-condition-list',LIST_CAP);collection_children[read['memberIndex']]=recursive_list
 program,pending=compile_member_program(source,pins,wrapper_name=source['wrapperName'],type_name=source['wrappedType'],
  value4={},references=references,reference_children=children,typed_requests=typed_requests,reference_binder=bind_reference,
  collections=collections,collection_children=collection_children,collection_binder=_collection_binder)
 if pending:return None,pending
 allowed={'scalar32','bool-byte','byte-payload','condition-param','game-condition-list'}
 need('finite-condition-field-operations',all(r['kind']in allowed for r in program['reads']))
 fields=[dict(memberIndex=r['memberIndex'],fieldName=r['fieldName'],declaredType=r['declaredType'])for r in reads]
 cap=dict(schema=CAP_SCHEMA,typeName=source['wrappedType'],wrapperName=source['wrapperName'],memberCount=program['memberCount'],
  fields=fields,program=program,readerMethod=source['method'],formatterMethod=source['lifecycle']['concreteFormatter']['method'],
  nullAdmitted=True,positiveAdmitted=True,storedRecordGrammarAdmitted=True,
  actualWrapperCallbackEqualsProvedConcreteRequired=True,liveFormatterSelectionObserved=False,
  eagerOriginalAdapterRequired=False,unionSelectionAdmitted=False,parentFieldAdmitted=False,
  runtimeConditionEvaluationAdmitted=False)
 return cap,[]


def _nominal(ctx,md,wrapper):
 need('concrete-own-wrapper',md.types[wrapper.type_definition].flags&128==0)
 current=wrapper.wrapped_type;lineage=[]
 for _ in range(64):
  need('acyclic-bounded-condition-lineage',current not in lineage);lineage.append(current)
  if current==BASE:return lineage
  current=ctx.parent(current)
  need('actual-GameCondition-inheritance',isinstance(current,str)and current not in('', 'object','System.Object'))
 raise ValueError(LABEL+'.finite-condition-lineage')


def derive_many(image,pins,*,wrapper_names,param_components,recursive_list=None):
 """Freshly derive only an explicit finite selection of concrete wrappers."""
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.memorypack import generated_reader_sources,pooled_source_helper
 from scripts.game_data.memorypack.levelscript_condition_param_bindings import derive_binding
 from scripts.game_data.memorypack.wrapper_members import derive_from_image
 need('explicit-distinct-record-selection',isinstance(wrapper_names,(list,tuple))and 0<len(wrapper_names)<=512
  and all(type(n)is str and n for n in wrapper_names)and len(set(wrapper_names))==len(wrapper_names))
 _publication_gate(image,pins);selected=_children(param_components,pins);ctx=NativeReferenceContext(image)
 wrappers={w.name:w for w in derive_from_image(image).values()};base=image.pe.image_base
 need('all-exact-current-wrappers',all(n in wrappers for n in wrapper_names))
 sources=generated_reader_sources.derive_many(image,pins,list(wrapper_names));owners=[];caps={};pool={}
 for name,row in zip(wrapper_names,sources['owners'],strict=True):
  try:
   if row.get('status')!='complete-reader-source-proved':
    raise ValueError(LABEL+'.complete-selected-wrapper-reader:status='+str(row.get('status'))+
     ':source='+str(row.get('reason',row.get('diagnostic')))[:1800])
   source=row['proof'];lineage=_nominal(ctx,image.metadata,wrappers[name]);requests={};components={};list_source=None
   for read in source['orderedSourceReads']:
    declared=read['declaredType'];index=read['memberIndex']
    if read['kind']=='byte-payload':
     target=read['sourceTargetRva']
     if target not in pool:pool[target]=pooled_source_helper.validate_on_image(image,base+target,pins)
     need('actual-pooled-index-helper',pool[target].get('wireEncoding')=='int32-pool-index')
    if declared in selected:
     component,key=selected[declared]
     # Copy only when this record needs parent bindings. The source child is
     # unchanged and may also be used by independently compiled records.
     if declared not in components:
      components[declared]=copy.copy(component);components[declared]['parentBindings']={}
      components[declared]['capabilities']={key:component['capabilities'][key]}
      components[declared]['owners']=[o for o in component['owners']if o.get('typeName')==declared]
     child=components[declared];context=read['context']
     usage=derive_typed_usage_context(image,context['instructionRva'],label=LABEL+'.actualParam')
     requests[index]=usage
     binding=derive_binding(image,pins,typed_request=usage,source_target=base+read['sourceTargetRva'],
      source_instruction=read['instruction'],component=child,capability=key)
     child['parentBindings'][str(usage['instructionRva'])]=binding
    elif declared==LIST and recursive_list is not None:
     from scripts.game_data.memorypack.levelscript_condition_list_sources import derive_member
     # A fresh derivation at this actual parent site owns the collection
     # request. A supplied source only opts into the finite list boundary.
     need('same-recursive-list-build',recursive_list.get('nativeInputs')==pins)
     list_source=derive_member(image,pins,parent_source=source,member_index=index,count_limit=recursive_list['countLimit'])
     requests[index]=list_source['parentBinding']['typedRequest']
   cap,pending=compile_record(source,pins,param_components=list(components.values()),typed_requests=requests,recursive_list=list_source)
   if pending:
    owners.append(dict(status='pendingReview',wrapperName=name,typeName=source['wrappedType'],pending=pending,
     source=row,parentFieldAdmitted=False,unionSelectionAdmitted=False));continue
   caps[PREFIX+source['wrappedType']]=cap
   owners.append(dict(status='validated-conditional-condition-record',wrapperName=name,typeName=source['wrappedType'],capability=cap,
    proof=dict(source=source,actualConditionLineage=lineage,
     paramBindings={n:dict(componentSchema=c['schema'],bindings=c['parentBindings'])for n,c in components.items()},recursiveList=list_source,
     pooledSources={str(r['memberIndex']):pool[r['sourceTargetRva']]for r in source['orderedSourceReads']if r['kind']=='byte-payload'}),
    unionSelectionAdmitted=False,parentFieldAdmitted=False))
  except(ValueError,KeyError,IndexError,TypeError)as error:
   import traceback
   from pathlib import Path
   sites=[dict(source=Path(f.filename).as_posix().split('/scripts/',1)[-1],function=f.name,line=f.lineno)
    for f in traceback.extract_tb(error.__traceback__)[-8:]]
   owners.append(dict(status='pendingReview',wrapperName=name,reason=str(error)[:2200],source=row,
    diagnostic=dict(validator=LABEL,failedGate=str(error).split(':',1)[0],errorType=type(error).__name__,
     expected='complete own concrete wrapper, exact Param/list request and full field/frame program',
     actual=str(error)[:1600],sourceCallSites=sites,
     sourceFailedGate=str(row.get('reason','')).split(':',1)[0]if row.get('status')!='complete-reader-source-proved'else None,
     sourcePath='scripts/game_data/memorypack/generated_reader_sources.py'if row.get('status')!='complete-reader-source-proved'else None),
    unionSelectionAdmitted=False,parentFieldAdmitted=False))
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema=SCHEMA,nativeInputs=pins,capabilities=caps,owners=owners,
  unionSelectionAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,runtimeConditionEvaluationAdmitted=False)))
