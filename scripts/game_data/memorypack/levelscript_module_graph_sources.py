"""Complete current Module grammars with separate source and field owners.

Pure composition checks supplied relationships. Only derive authenticates
every selected source on the caller's one native image. Live formatter
selection, helper effects and runtime module behavior remain conditional.
"""
import json
import traceback

from scripts.game_data.memorypack import levelscript_module_record_components as records
from scripts.game_data.memorypack import levelscript_module_collection_sources as collections
from scripts.game_data.memorypack import levelscript_module_value_components as values

SCHEMA='endfield.story-module-graph-components.v1'
CAP_SCHEMA='endfield.story-module-graph-capability.v1'
CAPABILITY='story-current-module-dictionary'
WIRE='story-current-module-dictionary'
BASE='Beyond.Gameplay.LevelScriptModuleData'
ROOT='Beyond.Gameplay.LevelScriptData'


def need(key,condition):
 if not condition:raise ValueError('storyModuleGraph.'+key)


def _merge(target,source):
 for key,value in source.items():
  need('same-shared-capability:'+key,key not in target or target[key]==value)
  target[key]=value


def compile_records(sources,requests,pins,*,ordinary,reference_reader,value_component,generic,enums,entity_lists,rune_arrays,rune_dictionary,progress=None):
 """Compile the finite dependency DAG; retain independent actionable holds."""
 from scripts.game_data.memorypack import levelscript_module_record_sources as source_owner
 from scripts.game_data.memorypack import levelscript_module_enum_list_sources as enum_owner
 from scripts.game_data.memorypack import levelscript_module_entity_list_components as entity_owner
 from scripts.game_data.memorypack import module_entity_ptr_value_bindings as entity,module_lang_key_value_bindings as lang
 need('all-independent-ordinary-adapters',set(ordinary)==set(source_owner.TYPES))
 need('all-explicit-collection-source-nominals',set(generic)==set(collections.ELEMENTS))
 need('optional-callable-compiler-progress',progress is None or callable(progress))
 done={};pending=dict(sources);holds=[];caps={};list_proofs={};managed_proofs={}
 def list_child(read):
  nominal=read['declaredType'];element=nominal[len(collections.LIST):-1]
  if element in collections.REFERENCE_TYPES and element!=values.PKV and element not in done:return None
  if element in generic:
   child=records.collection_component(generic[element],pins,
    record=done[element]['capabilities'][records.record_key(element)]if element in done else None,
    parameters=value_component['capabilities'][values.PARAM_ARRAY]if element==values.PKV else None)
   return child,records.list_key(element),records.LIST_WIRE
  if element in values.LIST_CAPS:return value_component,values.LIST_CAPS[element],'story-module-value-list'
  if element==entity.TYPE:return entity_lists,entity_owner.CAP,entity_owner.WIRE
  key='skill-enum-list:'+element
  if key in enums['capabilities']:return enums,key,enum_owner.WIRE
  raise ValueError('storyModuleGraph.unowned-positive-list:'+nominal)
 while pending:
  advanced=False
  for name,source in list(pending.items()):
   try:
    listing={};managed={};blocked=False;typed={int(i):u for i,u in requests[name].items()}
    for read in source['orderedSourceReads']:
     index=read['memberIndex'];nominal=read['declaredType']
     if nominal in sources and nominal not in done:blocked=True;break
     if nominal.startswith(collections.LIST):
      selected=list_child(read)
      if selected is None:blocked=True;break
      listing[index]=selected
     if nominal in(entity.TYPE,lang.TYPE):
      child=source['sourceScope']['managedValueSources'][str(index)];owner=entity if nominal==entity.TYPE else lang
      managed[index]=owner.component(child,pins)
      if index not in typed:typed[index]=child['proof']['typedRequest']
    if blocked:continue
    program,held=records.compile_record(source,pins,typed_requests=typed,ordinary_children=done,list_children=listing,
     value_children=managed,value_components=value_component,
     rune_arrays=rune_arrays if name=='Beyond.Gameplay.RunePuzzleData'else None,
     rune_dictionary=rune_dictionary if name=='Beyond.Gameplay.RunePuzzleData'else None)
    need('all-source-members-compiled:'+name,held==[])
    component=records.record_component(source,pins,program,ordinary=ordinary.get(name),reference_reader=reference_reader)
    done[name]=component;_merge(caps,component['capabilities'])
    if progress is not None:progress('record-complete:'+name)
    for child,key,wire in listing.values():
     _merge(caps,child['capabilities']);list_proofs.setdefault(key,child)
    for index,child in managed.items():
     _merge(caps,child['capabilities']);managed_proofs[name+'::'+str(index)]=child
    del pending[name];advanced=True
   except(ValueError,KeyError,TypeError,IndexError,RuntimeError,AttributeError)as error:
    holds.append(dict(typeName=name,stage='record-child-field-composition',validator='storyModuleGraph',
     failedGate=str(error).split(':',1)[0],reason=str(error)[:2600],traceback=traceback.format_exc()[-10000:],
     sourcePath='scripts/game_data/memorypack/levelscript_module_graph_sources.py'))
    del pending[name];advanced=True
  if not advanced:break
 holds.extend(dict(typeName=name,stage='record-dependency',reason='Required ordinary record did not complete')for name in pending)
 _merge(caps,value_component['capabilities']);_merge(caps,rune_dictionary['capabilities'])
 for child in rune_arrays.values():_merge(caps,child['capabilities'])
 return dict(owners=done,capabilities=caps,holds=holds,listProofs=list_proofs,managedProofs=managed_proofs)


def root_binding(owners,dictionary,pins):
 from scripts.game_data.memorypack import levelscript_owner_sources as roots
 need('same-complete-root-source',owners.get('nativeInputs')==pins and owners.get('wholeOwnerAdmitted')is False)
 parent=owners['owners'][ROOT];program=parent['program'];fields=parent['fields'];selected=program['selectedBytes']
 need('complete-root-plan-and-frame',program.get('originalType')==ROOT and program.get('memberCount')==len(roots.ROOT_FIELDS)
  and program.get('normalReturn')is True and program.get('entryFrameRestored')is True and program.get('existingWrapper')is True
  and[r['fieldName']for r in program['orderedReads']]==[n for n,k in roots.ROOT_FIELDS]
  and[f['name']for f in fields]==[n for n,k in roots.ROOT_FIELDS])
 field,read=next((f,r)for f,r in zip(fields,program['orderedReads'],strict=True)if f['name']=='modules')
 usage=dictionary['proof']['typedRequest'];base=selected[0][0]-parent['method'][3];target=dictionary['proof']['callTargetRva']
 need('same-root-actual-module-context-store-and-call',field['typeName']==dictionary['typeName']and field['kind']=='reference'
  and read['storeOffset']==field['offset']==dictionary['proof']['parent']['fieldOffset']
  and read['sourceTarget']==base+target and read['typedUsage']['instruction']==base+usage['instructionRva']
  and usage in parent['typedUsages'])
 chunks={at+i:b for at,h in selected for i,b in enumerate(bytes.fromhex(h))}
 raw=bytes(chunks[read['sourceCall']+i]for i in range(5))
 need('same-actual-root-E8',raw[0]==232 and read['sourceCall']+5+int.from_bytes(raw[1:],'little',signed=True)==base+target)
 return dict(ownerType=ROOT,fieldName='modules',typeName=dictionary['typeName'],typedRequest=usage,
  sourceInstruction=[read['sourceCall']-base,raw.hex().upper()],readerMethodDefinition=usage['methodSpec'][0],sourceTargetRva=target,
  storeOffset=field['offset'],existingWrapperRequired=True,disabledCollectorRequired=True,completeRootFrameProved=True,
  rootGrammarAdmitted=False)


def compose(transport,compiled,dictionary,pins,*,owners,pooled_sources):
 from scripts.game_data.memorypack import levelscript_module_dictionary_sources as dictionaries
 from scripts.game_data.memorypack import levelscript_module_record_sources as ordinary
 from scripts.game_data.codecs.levelscript.current_module_graph import validate
 need('same-exact-current-Module-transport',transport.get('schema')=='endfield.levelscript-module-union-transport.v1'
  and transport.get('status')=='validated-conditional-module-union-transport'and transport.get('nativeInputs')==pins
  and transport.get('typeName')==BASE and all(transport.get(k)is False for k in('concreteChildGrammarAdmitted','parentFieldAdmitted','wholeOwnerAdmitted')))
 rows=transport['programs'];definition=transport['referencePackable']['packableContext']['packableDefinition']
 need('all-current-finite-21-routes',len(rows)==21 and[r['tag']for r in rows]==list(range(21)))
 need('all-34-complete-records-and-only-own-ordinary-children',compiled.get('holds')==[]
  and set(compiled['owners'])=={r['wrappedType']for r in rows}|set(ordinary.TYPES))
 routes={}
 for row in rows:
  usage=row['typedRequest'];bound=row['typedArgument'];name=row['wrappedType'];child=compiled['owners'][name]
  need('own-selected-wrapper-context-and-concrete-source:'+name,usage['methodSpec'][0]==bound['methodDefinition']==definition
   and(usage['typeName'],usage['methodName'],usage['classArguments'],usage['methodArguments'])==
    ('MemoryPack.MemoryPackReader','ReadPackable',[],[row['wrapperName']])
   and(bound['concreteTypeKind'],bound['argumentType'])==(18,row['wrapperName'])
   and child['proof']['source']['wrapperName']==row['wrapperName']
   and row['wrapperLineage'][0]==row['wrapperName']and row['wrapperLineage'][-1]==transport['wrapperName']
   and row['originalLineage'][0]['typeName']==name and row['originalLineage'][-1]['typeName']==BASE
   and all(row['source'].get(k)is True for k in('sameReader','sameOutput','outputInitiallyNullRequired','wholeReferenceStoredUnchanged','normalReturn','entryRspRestored')))
  routes[str(row['tag'])]=dict(typeName=name,wrapperName=row['wrapperName'],recordCapability=records.record_key(name),
   actualClosedReadPackableProved=True,actualWrapperCallbackEqualsProvedChildRequired=True)
 ff=transport['canonicalFF'];need('canonical-base-FF-and-all-inherited-Original-conversions',ff.get('canonicalFF')is True
  and ff.get('clearedOutputBytes')==8 and ff.get('normalReturn')is True and ff.get('entryRspRestored')is True
  and{r['wrapperName']for r in transport['inheritedConversions']}=={r['wrapperName']for r in rows}
  and transport['pair']['composition']['interfaces'][0]['formatterDeserializeMethodIndex']==transport['slot5Method'][0])
 dictionaries.verify_source(dictionary,pins);callback=dictionaries.bind_callback(dictionary,pins,transport['adapter'])
 binding=root_binding(owners,dictionary,pins)
 need('every-actual-pooled-field-has-independent-source',all(r['sourceTargetRva']in pooled_sources
  for c in compiled['owners'].values()for r in c['proof']['source']['orderedSourceReads']if r['kind']=='byte-payload'))
 for target,source in pooled_sources.items():
  need('same-independent-pooled-index-source',type(target)is int and source.get('status')=='validated'
   and source.get('nativeInputs')==pins and target in source.get('sourceHelpers',[])
   and(source.get('wireEncoding'),source.get('emptyIndex'),source.get('nullIndex'))==('int32-pool-index',-1,-2))
 cap=dict(schema=CAP_SCHEMA,typeName=dictionary['typeName'],moduleType=BASE,rootWrapper=transport['wrapperName'],routes=routes,
  capabilities=compiled['capabilities'],dictionary=dict(headerBytes=4,keyWireBytes=8,countLimit=dictionary['countRange'][1],
   countRange=dictionary['countRange'],keyType='ulong',valueType=BASE,initiallyNullOutputRequired=True,
   actualKeyCallbackEqualsProvedUInt64Required=True,actualValueCallbackEqualsProvedModuleRequired=True,
   freshDictionaryRequired=True,duplicateAndHashBehaviorAdmitted=False,callbackBinding=callback),rootBinding=binding,
  nodeLimit=16384,elementLimit=16384,depthLimit=64,pooledIndexBytes=4,pooledNullIndex=-2,pooledEmptyIndex=-1,
  headerModes=['short','extended','canonical-FF'],storedModuleGrammarAdmitted=True,allPositiveChildDomainsAdmitted=True,
  liveFormatterSelectionObserved=False,runtimeModuleBehaviorAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False)
 validate(cap);return cap


def derive(image,pins,*,owners=None,progress=None):
 """Fresh full same-image graph; no retained source packet is authority."""
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.memorypack import generated_reader_sources as readers,pooled_source_helper
 from scripts.game_data.memorypack import levelscript_module_union_sources as unions,levelscript_module_record_sources as ordinary
 from scripts.game_data.memorypack import levelscript_module_entity_list_components as entity
 from scripts.game_data.memorypack import levelscript_module_enum_list_sources as enums
 from scripts.game_data.memorypack import levelscript_rune_array_components as rune_arrays,levelscript_rune_dictionary_components as rune_dictionary
 from scripts.game_data.memorypack import levelscript_rune_dictionary_sources as rune_source,levelscript_module_dictionary_sources as dictionary
 from scripts.game_data.memorypack.skill_root_child_bindings import reference_reader_abi
 from scripts.game_data.memorypack.levelscript_owner_sources import derive as derive_owners
 _publication_gate(image,pins);base=image.pe.image_base;stage='transport'
 need('optional-callable-progress',progress is None or callable(progress))
 def mark(name):
  nonlocal stage
  stage=name
  if progress is not None:progress(name)
 result=dict(schema=SCHEMA,status='pendingReview',nativeInputs=pins,capabilities={},proof={},holds=[],parentFieldAdmitted=False,wholeOwnerAdmitted=False)
 try:
  mark('transport');transport=unions.derive_transport(image,pins);result['proof']['transport']=transport
  names=[r['wrappedType']for r in transport['programs']]+list(ordinary.TYPES)
  need('34-distinct-actual-source-owners',len(names)==len(set(names))==34)
  wrappers={w.wrapped_type:w for w in image.memorypack_wrappers.values()if w.wrapped_type in names}
  mark('complete-34-reader-sources');source_rows=readers.derive_many(image,pins,[wrappers[n].name for n in names]);result['proof']['readerSources']=source_rows
  source_holds=[r for r in source_rows['owners']if r.get('status')!='complete-reader-source-proved']
  need('all-independent-34-complete-reader-sources',source_holds==[])
  sources={r['proof']['wrappedType']:r['proof']for r in source_rows['owners']};requests={};list_requests={};opera_requests={};enum_requests={};pool={}
  for name,source in sources.items():
   requests[name]={}
   for read in source['orderedSourceReads']:
    index=read['memberIndex'];context=read.get('context')
    if not context:continue
    usage=derive_typed_usage_context(image,context['instructionRva'],label='storyModuleGraph.actualField')
    need('actual-MethodSpec-instruction-equality:'+name+'::'+str(index),all(context[k]==usage[k]for k in('instructionRva','instructionHex','methodSpec')))
    requests[name][index]=usage
    request=dict(typed_request=usage,call_target=base+read['sourceTargetRva'],source_instruction=read['instruction'])
    if read['declaredType'].startswith(collections.LIST):list_requests.setdefault(read['declaredType'][len(collections.LIST):-1],request)
    if read['declaredType']==values.values.OPERA+'[]':opera_requests[name]=request
    for enum,plan in enums.PLANS.items():
     if name==plan['parentType']and index==plan['memberIndex']:
      enum_requests[enum]=dict({k:v for k,v in plan.items()if k!='memberCount'},typeName=read['declaredType'],typedRequest=usage,
       instruction=read['instruction'],sourceTargetRva=read['sourceTargetRva'])
  adapters={}
  for name in ordinary.TYPES:
   mark('ordinary-adapter:'+name);adapters[name]=ordinary.derive_adapter_for_source(image,pins,sources[name])
  result['proof']['ordinary']=adapters;reference=reference_reader_abi(image,pins);result['proof']['referenceReader']=reference
  mark('Module-value-and-Opera-children');value_component=values.derive(image,pins,list_requests={n:list_requests[n]for n in values.LIST_CAPS},opera_requests=opera_requests)
  result['proof']['values']=value_component;mark('independent-13-list-sources')
  generic={n:collections.derive(image,pins,typed_request=list_requests[n]['typed_request'],call_target=list_requests[n]['call_target'],element_type=n)for n in collections.ELEMENTS}
  result['proof']['genericLists']=generic;mark('Entity-list');selected=list_requests[entity.ELEMENT]
  entity_component=entity.derive(image,pins,typed_request=selected['typed_request'],call_target=selected['call_target']);result['proof']['entityList']=entity_component
  mark('enum-list-2');enum_component=enums.derive(image,pins,requests=enum_requests);result['proof']['enumLists']=enum_component
  mark('Rune-primitive-arrays');rune=sources[rune_arrays.OWNER];arrays={}
  for index,(_,element)in rune_arrays.MEMBERS.items():
   mark('Rune-primitive-array:'+str(index));read=rune['orderedSourceReads'][index];arrays[index]=rune_arrays.derive(image,pins,typed_request=requests[rune_arrays.OWNER][index],
    call_target=base+read['sourceTargetRva'],source_instruction=read['instruction'],element_type=element)
  result['proof']['runeArrays']=arrays;mark('Rune-raw16-dictionary')
  rd=rune_dictionary.compose(rune_source.derive_member(image,pins,rune,member_index=2),pins);result['proof']['runeDictionary']=rd
  mark('all-record-parent-field-compilation')
  compiled=compile_records(sources,requests,pins,ordinary=adapters,reference_reader=reference,value_component=value_component,generic=generic,
   enums=enum_component,entity_lists=entity_component,rune_arrays=arrays,rune_dictionary=rd,progress=mark)
  result['proof']['records']=compiled
  need('all-34-record-grammars',compiled['holds']==[])
  mark('pooled-string-sources')
  for source in sources.values():
   for read in source['orderedSourceReads']:
    if read['kind']=='byte-payload'and read['sourceTargetRva']not in pool:
     pool[read['sourceTargetRva']]=pooled_source_helper.validate_on_image(image,base+read['sourceTargetRva'],pins)
  result['proof']['pooledSources']=pool;mark('root-and-UInt64-Module-dictionary')
  if owners is None:owners=derive_owners(image,pins)
  root=owners['owners'][ROOT]
  # Keep this owner's source once; unrelated outer child graphs are neither
  # dependencies of the Module proof nor a reason to nest the whole Story.
  result['proof']['root']=dict(nativeInputs=pins,owners={ROOT:root},wholeOwnerAdmitted=False)
  read,=[r for r in root['program']['orderedReads']if r['fieldName']=='modules']
  usage,=[u for u in root['typedUsages']if u['instructionRva']==read['typedUsage']['instruction']-base]
  root_dictionary=dictionary.derive(image,pins,typed_request=usage,call_target=read['sourceTarget'],count_limit=4096)
  result['proof']['dictionary']=root_dictionary;mark('whole-Module-union-root-composition')
  cap=compose(transport,compiled,root_dictionary,pins,owners=owners,pooled_sources=pool)
  result.update(status='validated-conditional-current-module-graph',capabilities={CAPABILITY:cap},holds=[])
 except(ValueError,KeyError,TypeError,IndexError,RuntimeError,AttributeError)as error:
  result['holds']=[dict(stage=stage,validator='storyModuleGraph',failedGate=str(error).split(':',1)[0],reason=str(error)[:3000],
   traceback=traceback.format_exc()[-12000:],sourcePath='scripts/game_data/memorypack/levelscript_module_graph_sources.py')]
 _publication_gate(image,pins);return json.loads(json.dumps(result))
