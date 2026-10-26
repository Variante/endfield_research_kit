"""Selected executor cached EventParams deep-copy effects.

The destination is a separate cached container, cleared before copying ordinary
producer variables. Typed pool resets and actual get/set programs are joined;
live identity, writable capacity and nonselected fresh Event factories are not
inferred from method names or closed registration addresses.
"""
from scripts.game_data.memorypack import leveldata_patrol_executor_copy_programs as programs
from scripts.game_data.memorypack import leveldata_patrol_event_pool_sources as event_pool
from scripts.game_data.memorypack import leveldata_patrol_checkpoint_callee_sources as sources
from scripts.game_data.memorypack import leveldata_patrol_checkpoint_helper_sources as packets

SCHEMA='endfield.story-patrol-executor-copy-sources.v1'
EXECUTOR='Beyond.Gameplay.Actions.ActionExecutor'
EVENT='Beyond.Gameplay.Core.EventParams'
BLACKBOARD=sources.BLACKBOARD
VARIABLE=sources.VARIABLE
BASE_VARIABLE=sources.BASE_VARIABLE
DICT='System.Collections.Generic.Dictionary`2'
DOMAIN=(('@event_sender','Beyond.Gameplay.Core.EntityPtr'),('@event_receiver','Beyond.Gameplay.Core.EntityPtr'),
 ('id','int'),('index','int'),('position','UnityEngine.Vector3'))


def need(check,condition):
 if not condition:raise ValueError('patrolExecutorCopySources.'+check)


def _call(program,role):return next(c for c in program['calls']if c['role']==role)
def _without_rows(packet):return{k:v for k,v in packet.items()if k!='rows'}


def _parents(pool):
 recycle=pool['proof']['recyclerSource'];clear=recycle['proof']['clearSource'];variable=recycle['proof']['poolSource']
 return dict(clear=clear,scope=clear['proof']['scopeSource'],variable=variable,
  storage=variable['proof']['storageSource'],callee=variable['proof']['storageSource']['proof']['calleeSource'])


def _replay(p):
 pool=p['eventPoolSource'];parents=_parents(pool);base=p['imageBase'];h=p['packets']
 def r(k):return packets.regions(h[k],base)
 def e(k):return base+h[k]['entryRva']
 values=parents['callee']['proof']['values'];prepare=base+parents['storage']['proof']['classes']['preparation']['entryRva']
 return sources.norm(dict(assign=[programs.assign(r('assign'),e('assign'),cached=c,incoming=i)for c in(False,True)for i in(False,True)],
  newEmpty=programs.new_empty(r('newEmpty'),e('newEmpty')),deepCopy=programs.deep_copy_paths(r('deepCopy'),e('deepCopy')),
  setVariable={kind:programs.set_variable(r('setVariable'),e('setVariable'),kind=kind)for kind in programs.KINDS},
  copies={kind:programs.copy_variable(packets.regions(v['packet'],base),base+v['packet']['entryRva'],kind=kind)for kind,v in p['copies'].items()},
  enumerator=programs.enumerator_constructor(r('enumerator'),e('enumerator')),
  intGetter=programs.int_get_invoker(r('intGetter'),e('intGetter'),prepare=prepare,
   callback=values['int']['methods']['get_value']['registration']['pointer']),
  entityGetter=programs.entity_get_invoker(r('entityGetter'),e('entityGetter'),prepare=prepare)))


def _metadata(image,ctx):
 from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
 symbols=ContextSymbols(image);md=image.metadata;result={}
 for role,owner,name,count in(('assign',EXECUTOR,'_AssignEventParams',1),('newEmpty',EVENT,'NewEmpty',0),
  ('deepCopy','Beyond.Gameplay.ParamBlackboardExtensions','DeepCopyAllParamValue',2),('setVariable',BLACKBOARD,'SetVariableValue',2),
  ('copy',VARIABLE,'Copy',0)):
  m=sources._single_method(ctx,owner,name,count);pointer=None if role=='copy'else image.method_pointer_va(m)
  result[role]=dict(definition=m.index,owner=owner,name=name,slot=m.slot,static=bool(m.flags&16),
   parameters=sources._parameter_type(ctx,m),returns=ctx.type_name(m.return_type),pointerRva=pointer-image.pe.image_base if pointer else None)
 result['eventField']=list(ctx.field(EXECUTOR+'::<eventParams>k__BackingField'))
 result['copyContext']=symbols.context(ctx.index.types[VARIABLE].index,slots=[4])
 result['dictionaryMethods']={}
 for role,owner,name,count in(('getEnumerator',DICT,'GetEnumerator',0),('moveNext',DICT+'+Enumerator','MoveNext',0),
   ('lookup',DICT,'TryGetValue',2),('setItem',DICT,'set_Item',2)):
  m=sources._single_method(ctx,owner,name,count)
  result['dictionaryMethods'][role]=dict(definition=m.index,owner=owner,name=name,parameterCount=count,
   returnType=symbols.type(ctx.type_pointer(m.return_type)))
 result['dictionaryDefinition']=ctx.index.types[DICT].index
 return result


def _require_metadata(m,parents):
 for role,owner,name,args,returns,static in(('assign',EXECUTOR,'_AssignEventParams',[EVENT],'void',False),
  ('newEmpty',EVENT,'NewEmpty',[],EVENT,True),
  ('deepCopy','Beyond.Gameplay.ParamBlackboardExtensions','DeepCopyAllParamValue',[BLACKBOARD,BLACKBOARD],'void',True),
  ('setVariable',BLACKBOARD,'SetVariableValue',['string',BASE_VARIABLE],'void',False),
  ('copy',VARIABLE,'Copy',[],BASE_VARIABLE,False)):
  r=m[role];need('own-named-method-'+role,(r['owner'],r['name'],r['parameters'],r['returns'],r['static'])==(owner,name,args,returns,static))
 need('own-cached-EventParams-field',m['eventField']==[EXECUTOR,EVENT,48])
 c=m['copyContext'];need('own-Copy-virtual-context',m['copy']['slot']==12 and c['typeName']==VARIABLE and c.get('selectedSlots')==[4]
  and c['definition']==parents['callee']['proof']['nominal']['variableDefinition'])
 row,=c['entries'];arg,=row['classArguments'];raw=bytes.fromhex(arg['rawHex'])
 need('own-Copy-Allocate-reciprocal-VAR',row['relativeSlot']==4 and row['kind']==3 and row['typeName']=='Beyond.Gameplay.ParamVariablePool`1'
  and row['methodName']=='Allocate'and row['methodSpec'][0]==parents['variable']['proof']['metadata']['allocateMethod'][0]
  and row['methodArguments']==[]and raw[10]==19 and raw[11]==0
  and(arg['parameterOwner']['typeIndex'],arg['parameterOwner']['ordinal'])==(c['definition'],0))
 result=m['dictionaryMethods']['getEnumerator']['returnType'];raw=bytes.fromhex(result['rawHex']);definition=result['definition']
 need('own-value-enumerator-return-carrier',raw[10:12]==bytes((21,128))and definition['name']==DICT+'+Enumerator'
  and bytes.fromhex(definition['rawHex'])[10:12]==bytes((17,128))and len(result['classArguments'])==2
  and all(bytes.fromhex(a['rawHex'])[10:12]==bytes((19,0))
   and(a['parameterOwner']['typeIndex'],a['parameterOwner']['ordinal'])==(m['dictionaryDefinition'],i)
   for i,a in enumerate(result['classArguments'])))


def _domain(parents):
 values=parents['storage']['proof']['strings']['domain'];producer=parents['scope']['proof']['parentProducer'];result={}
 requests=producer['typedRequests'];literals=producer['literals']
 for name,kind in DOMAIN:
  own=values[name];raw=bytes.fromhex(own['literalHex']);units=list(raw.decode('utf-8').encode('utf-16-le'))
  need('owned-ASCII-key-literal-'+name,raw.decode('ascii')==name and own['utf16Units']==list(map(ord,name))
   and units==[b for u in own['utf16Units']for b in(u&255,u>>8)])
  producer_role={'@event_sender':'setEntity','id':'setId','index':'setIndex','position':'setPosition'}.get(name)
  if producer_role:
   need('own-produced-key-type-'+name,requests[producer_role]['methodArguments']==[kind]and literals[name]['literalHex']==own['literalHex'])
  result[name]=dict(typeName=kind,valueBytes=4 if kind=='int'else 12 if kind=='UnityEngine.Vector3'else 40,
   utf16Units=own['utf16Units'],literalHex=own['literalHex'],producerRole=producer_role,
   optionalReceiverOriginRequiresIndependentCaller=producer_role is None)
 need('pairwise-distinct-source-key-content',len({tuple(v['utf16Units'])for v in result.values()})==len(DOMAIN))
 return dict(keys=result,maximumLiveKeys=len(DOMAIN),maximumSourceSlots=4096,
  sourceMayContainAnySubsetInAnyEnumerationOrder=True,sourceKeysUniqueRequired=True,
  sourceAndDestinationEventsAndDictionariesRequiredDistinct=True,
  destinationAfterClear=dict(count=0,freeCount=0,freeList=-1,usedEntriesCleared=True),
  destinationBucketsAndEntriesRequiredPresent=True,destinationEntryCapacityRequiredAtLeast=len(DOMAIN),
  canonicalOrdinaryValueClassesRequired=True,newCopyMustNotAliasSourceOrExistingDestinationVariables=True,
  selectedResult=dict(destinationCount='source live key count',keys='identical enumerated strings',
   valueBits='same whole4/12/40 source bits in separately allocated/reset variables',
   sourceDictionaryAndVariablesUnchanged=True,allCopiesCompleteBeforeCallerReturns=True),
  optionalReceiverOriginProved=False,runtimeStorageObserved=False)


def _selections(p):
 parents=_parents(p['eventPoolSource']);values=parents['callee']['proof']['values'];pool=parents['variable']['proof']
 return{kind:dict(copy=p['copies'][kind]['registration']['pointer'],
  getter=values[kind]['methods']['get_value']['registration']['pointer'],
  propertySetter=values[kind]['methods']['set_value']['registration']['pointer'],
  SetValue=values[kind]['methods']['SetValue']['registration']['pointer'],
  reset=pool['resets'][kind]['registration']['pointer'],
  selectors=dict(copy=12,getter=14,propertySetter=15,SetValue=17,reset=7),
  actualRuntimeClassAndMethodInfoMustSelectTheseSources=True,runtimeSelectionObserved=False)for kind in programs.KINDS}


def _post_state(domain):
 keys=list(domain['keys'])
 need('event-key-outside-copied-domain','@event_key'not in keys)
 return dict(conditionalSourcePostcondition=True,observedRuntimeFact=False,requiresIncomingNonnull=True,
  requiresExactAdmittedSourceKeySubsetAndNoOtherEntries=True,requiresSelectedCallbackStability=True,
  requiresAllDomainOwnershipAndCapacityConditions=True,
  possibleKeys=keys,copiedKeyTypes={k:v['typeName']for k,v in domain['keys'].items()},
  sourceLiveKeyCountRange=[0,len(keys)],destinationCountEqualsSourceLiveKeyCount=True,
  destinationKeySetEqualsExactSourceSubset=True,noOtherDestinationEntries=True,
  guaranteedAbsentKeys=['@event_key'],freeCount=0,freeList=-1,
  existingBucketsAndEntryCapacityPreserved=True,
  remainingCapacityExpression='existing entry capacity minus source live key count',
  subsequentInsertRequiresOneAdditionalSpareSlot=True,
  noNewKeyWriterBetweenCopyAndSubsequentLookupRequired=True)


def _usage_sites(p):
 q=p['programs'];uses=dict(newEmptyClass=q['newEmpty']['classUsage'],poolAllocate=q['newEmpty']['allocateUsage'])
 for u in q['deepCopy']['witnesses'][-1]['usageSites']:uses[u['role']]=u
 for u in q['setVariable']['int']['usageSites']:uses[u['role']]=u
 return uses


def derive(image,pins):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.il2cpp.generic_entries import GenericEntries
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 _publication_gate(image,pins);pool=event_pool.derive(image,pins);parents=_parents(pool);base=image.pe.image_base
 ctx=NativeReferenceContext(image);ge=GenericEntries(image);metadata=_metadata(image,ctx);_require_metadata(metadata,parents)
 h={role:packets.packet(image,base+metadata[role]['pointerRva'])for role in('assign','newEmpty','deepCopy','setVariable')}
 def program(role,parser,**kw):
  try:return parser(packets.regions(h[role],base),base+h[role]['entryRva'],**kw)
  except ValueError as e:raise ValueError('patrolExecutorCopySources.program:'+role+' entryRva='+str(h[role]['entryRva'])+' detail='+str(e))from e
 copies={}
 for kind in programs.KINDS:
  rows=ge.observe(metadata['copy']['definition'],[kind],[]);need('one-own-closed-Copy-'+kind,len(rows)==1 and rows[0].get('pointer'))
  packet=packets.packet(image,rows[0]['pointer']);copies[kind]=dict(registration=rows[0],packet=packet)
 deep=program('deepCopy',programs.deep_copy,count=1);h['enumerator']=packets.packet(image,_call(deep,'getEnumerator')['targetVa'])
 cp={kind:programs.copy_variable(packets.regions(v['packet'],base),base+v['packet']['entryRva'],kind=kind)for kind,v in copies.items()}
 h['intGetter']=packets.packet(image,_call(cp['int'],'getInt')['targetVa'])
 h['entityGetter']=packets.packet(image,_call(cp['Beyond.Gameplay.Core.EntityPtr'],'getEntity')['targetVa'])
 p=dict(imageBase=base,eventPoolSource=pool,metadata=metadata,packets=h,assignPacket=h['assign'],copies=copies)
 p['programs']=_replay(p);p['domain']=_domain(parents);p['selectedCallbacks']=_selections(p)
 p['postAssignDictionaryState']=_post_state(p['domain'])
 p['usages']={role:derive_typed_usage_context(image,u['instructionVa']-base,label='patrolExecutorCopy.'+role)for role,u in _usage_sites(p).items()}
 p['enumeratorRegistrations']=ge.observe(p['usages']['getEnumerator']['methodSpec'][0],['string',BASE_VARIABLE],[])
 p['enumeratorSelection']=dict(closedRegistrationAbsent=not p['enumeratorRegistrations'],
  actualE8AndTypedValueReturnBodyProved=True,canonicalPointerAliasClaimed=False)
 value=sources.norm(dict(schema=SCHEMA,status='validated-conditional-executor-cached-copy-effects',nativeInputs=pins,proof=p,
  selectedExecutorCachedDeepCopyEffectsProved=True,selectedOrdinaryVariableCopyAndDictionaryInsertEffectsProved=True,
  selectedNonemptyEventPoolReuseRequired=True,freshEventFactoryOrActivatorEffectsProved=False,
  canonicalEnumeratorPointerClaimed=False,runtimeExecutorOrVariableIdentityObserved=False,runtimeInvocationObserved=False,actionExecutionOrPlaybackProved=False,
  evidenceBoundary=dict(exact='Own cached EventParams field48; NewEmpty actual generic pool tail; Clear10-before-DeepCopy; full enum40/current pair16; each ordinary typed Copy12/Allocate4/get14/set15 and complete4/12/40 store; enumerated key overwrite and own typed mode1 dictionary insertion.',
   conditional='Same ready original receiver/MethodInfos/canonical typed callbacks, disabled collector and normal ABI. GetEnumerator has an independently authenticated actual E8, exact closed typed request, reciprocal VALUE return and full40 body; absent registration remains absent without a pointer alias. Cached destination and incoming producer/dictionaries are distinct; nonempty Event pool reuse, valid pool ownership and independently proved prior state/reset. Stable ordinary source dictionary/variables uses only the explicit own key/type subset. Destination existing buckets/entries retain capacity for all five keys after Clear; typed variable allocations return distinct compatible writable storage and OnAllocate establishes consumed fields. Callback observers and replacements remain absent.',
   unresolved=['fresh Event factory/Activator invocation and alternate allocation paths','destination cold initialization/resize/free-list or aliased source storage','foreign/global/map/observer variable alternatives and optional receiver-key origin without its own caller','live executor/pool/variable/callback identity, actual action invocation and playback'])))
 validate(value,pins);_publication_gate(image,pins);return value


def validate(value,pins):
 need('source-envelope',value.get('schema')==SCHEMA and value.get('status')=='validated-conditional-executor-cached-copy-effects'and value.get('nativeInputs')==pins
  and all(value.get(k)is True for k in('selectedExecutorCachedDeepCopyEffectsProved','selectedOrdinaryVariableCopyAndDictionaryInsertEffectsProved','selectedNonemptyEventPoolReuseRequired'))
  and all(value.get(k)is False for k in('freshEventFactoryOrActivatorEffectsProved','canonicalEnumeratorPointerClaimed','runtimeExecutorOrVariableIdentityObserved','runtimeInvocationObserved','actionExecutionOrPlaybackProved')))
 p=value['proof'];pool=p['eventPoolSource'];event_pool.validate(pool);parents=_parents(pool);base=p['imageBase'];h=p['packets']
 need('same-full-event-pool-source',pool['nativeInputs']==pins and pool['proof']['imageBase']==base)
 need('exact-own-packet-and-value-domains',set(h)=={'assign','newEmpty','deepCopy','setVariable','enumerator','intGetter','entityGetter'}and set(p['copies'])==set(programs.KINDS))
 for packet in list(h.values())+[v['packet']for v in p['copies'].values()]:packets.verify_packet(packet)
 need('canonical-Assign-fullpacket-seam',p['assignPacket']==h['assign'])
 _require_metadata(p['metadata'],parents);q=_replay(p);need('all-selected-own-source-replay',q==p['programs'])
 need('explicit-own-key-type-and-storage-domain',_domain(parents)==p['domain'])
 need('conditional-exact-post-Assign-state',_post_state(p['domain'])==p['postAssignDictionaryState'])
 need('exact-own-typed-callback-source-closure',_selections(p)==p['selectedCallbacks'])
 for role in('assign','newEmpty','deepCopy','setVariable'):need('own-named-source-'+role,h[role]['entryRva']==p['metadata'][role]['pointerRva'])
 scope=parents['scope']['proof'];clear=parents['clear']['proof'];variable=parents['variable']['proof'];callee=parents['callee']['proof'];storage=parents['storage']['proof']
 def target(prog,role,packet):need('actual-source-child-'+role,_call(prog,role)['targetVa']==base+packet['entryRva'])
 for a in q['assign']:
  for call in a['calls']:
   role=call['role']
   if role=='barrier':need('same-disabled-store-barrier',call['targetVa']==base+clear['symbolRvas']['barrier'])
   else:target(a,role,h[role]if role in('newEmpty','deepCopy')else scope['packets']['virtual_invoke'])
 need('own-Clear-before-copy-callback',pool['proof']['programs']['virtualClear']['selectedCallbackRequired']==base+clear['packets']['clear']['entryRva'])
 need('NewEmpty-same-generic-allocation-source',q['newEmpty']['allocateTail']['targetVa']==base+scope['packets']['genericAllocate']['entryRva'])
 for d in q['deepCopy']['witnesses']:
  for c in d['calls']:target(d,c['role'],h['enumerator']if c['role']=='getEnumerator'else h['setVariable']if c['role']=='setVariable'else clear['packets']['moveNext'])
 need('same-enumerator-ready-helper',clear['symbolRvas']['context_type']==variable['symbolRvas']['context_type'])
 for kind,copy in q['copies'].items():
  owned=p['copies'][kind];registration=owned['registration'];values=callee['values'][kind]
  need('own-closed-Copy-registration-'+kind,registration['pointer']==base+owned['packet']['entryRva']
   and p['metadata']['copy']['definition']in registration['methodDefinitionIndices']
   and registration['classInstantiation']==values['methods']['SetValue']['registration']['classInstantiation']
   and registration['methodInstantiation']['index']==-1 and registration['runtimeSelectionObserved']is False)
  for c in copy['calls']:
   role=c['role']
   if role=='getVectorVirtual':continue
   packet=variable['allocate']if role=='allocate'else h['intGetter']if role=='getInt'else h['entityGetter']if role=='getEntity'else values['invoker']if role=='setValue'else storage['classes']['preparation']if role=='prepare'else scope['packets']['barrier']
   target(copy,role,packet)
  setter=q['setVariable'][kind];selected=registration['pointer']
  need('own-Copy-selection-ordinary-kind-'+kind,(setter['optimizedCopyTargets'][2]==selected)if kind=='int'else selected not in setter['optimizedCopyTargets'])
  for c in setter['calls']:
   role=c['role']
   if role=='copyVirtual':continue
   packet=callee['dictionary']['lookup']if role=='lookup'else storage['dictionary']['setter']if role=='setItem'else variable['allocate']if role=='allocate'else h['intGetter']if role=='getInt'else values['invoker']if role=='setInt'else storage['classes']['preparation']if role=='prepare'else scope['packets']['barrier']
   target(setter,role,packet)
 sites=_usage_sites(p);need('exact-consumed-usage-set',set(sites)==set(p['usages']))
 expected=dict(getEnumerator=(DICT,'GetEnumerator'),
  moveNext=('System.Collections.Generic.Dictionary`2+Enumerator','MoveNext'),lookup=('System.Collections.Generic.Dictionary`2','TryGetValue'),setItem=('System.Collections.Generic.Dictionary`2','set_Item'))
 for role,u in p['usages'].items():
  site=sites[role];need('actual-consumed-RIP-site-'+role,u['instructionRva']+base==site['instructionVa']and u['usageCellRva']+base==site['cellVa'])
  if role=='newEmptyClass':need('own-Event-static-pool-class',u['tag']==1 and u['typeName']=='Beyond.PoolCore.GenericStaticPool`1<'+EVENT+'>')
  elif role=='poolAllocate':need('own-Event-static-pool-Allocate-context',all(u[k]==scope['usages']['poolAllocate'][k]for k in('tag','methodSpec','typeName','methodName','classArguments','methodArguments')))
  else:
   method=p['metadata']['dictionaryMethods'][role]
   need('own-dictionary-context-'+role,u['tag']==6 and(u['typeName'],u['methodName'])==expected[role]
    and(method['owner'],method['name'])==expected[role]and method['definition']==u['methodSpec'][0]
    and method['parameterCount']==(0 if role in('getEnumerator','moveNext')else 2)
    and u['classArguments']==['string',BASE_VARIABLE]and u['methodArguments']==[])
 u=p['usages']['moveNext'];need('same-enumerator-as-Clear',all(u[k]==clear['usages']['moveNext'][k]for k in('tag','methodSpec','typeName','methodName','classArguments','methodArguments')))
 rows=p['enumeratorRegistrations'];need('own-enumerator-registration-observation',isinstance(rows,list)
  and(not rows or any(r['pointer']==base+h['enumerator']['entryRva']for r in rows))
  and all(p['usages']['getEnumerator']['methodSpec'][0]in r['methodDefinitionIndices']and r['runtimeSelectionObserved']is False for r in rows))
 need('actual-source-only-enumerator-boundary',p['enumeratorSelection']==dict(closedRegistrationAbsent=not rows,
  actualE8AndTypedValueReturnBodyProved=True,canonicalPointerAliasClaimed=False)
  and q['enumerator']['selectedMethodInfoArgumentUnused']is True)
 return value
