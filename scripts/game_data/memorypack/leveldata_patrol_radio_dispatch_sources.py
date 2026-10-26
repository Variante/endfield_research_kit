"""Own Radio Dispatcher<CombineKey> lookup and EventBinding call transport.

The two actual specializations differ: the reference-sized Stop EventData uses
an inline dispatcher macro. Closed registration observations never replace the
actual caller bytes, reciprocal generic contexts or independent child programs.
"""
from scripts.game_data.memorypack import leveldata_patrol_radio_dispatch_programs as paths
from scripts.game_data.memorypack import leveldata_patrol_radio_dictionary_programs as dictionary
from scripts.game_data.memorypack import leveldata_patrol_resource_validity_sources as packets

SCHEMA='endfield.story-patrol-radio-dispatch-sources.v1'
DISPATCHER='Beyond.EventDispatcher`1'
BINDING='Beyond.EventBinding`1'
HANDLER='Beyond.EventHandlerInfo'
KEY='Beyond.CombineKey'
DICT='System.Collections.Generic.Dictionary`2'


def need(check,condition):
 if not condition:raise ValueError('patrolRadioDispatchSources.'+check)


def _call(p,role):return next(c for c in p['calls']if c['role']==role)
def _row(context,slot):return next(r for r in context['entries']if r['relativeSlot']==slot)
def _kind(symbol):return bytes.fromhex(symbol['rawHex'])[10]
def _var(symbol,definition,*,method=False):
 owner=symbol.get('parameterOwner',{})
 return _kind(symbol)==(30 if method else 19)and owner.get('methodIndex'if method else'typeIndex')==definition and owner.get('ordinal')==0


def _programs(p):
 from scripts.game_data.memorypack import leveldata_patrol_checkpoint_callee_programs as contexts
 from scripts.game_data.memorypack.leveldata_patrol_dictionary_lookup_programs import preparation_program
 base=p['imageBase'];h=p['helpers'];rr={k:packets.raw(v,base)for k,v in h.items()}
 def entry(k):return base+h[k]['entryRva']
 def at(k):return rr[k],entry(k)
 return packets.norm(dict(playCall=paths.play_dispatch_call(rr['playSend'],base+p['sourceSites']['play']),
  stopInline=[paths.stop_inline_dispatch(rr['stopSend'],base+p['sourceSites']['stop'],found=f)for f in(False,True)],
  playDispatch=[paths.play_dispatch(*at('playDispatch'),found=f)for f in(False,True)],
  playBinding=paths.play_binding_paths(*at('playBinding')),stopBinding=paths.stop_handler_paths(*at('stopBinding')),
  lookup=[paths.try_get_handler(*at('lookup'),found=f)for f in(False,True)],find=dictionary.find_paths(*at('find')),
  defaultComparer=contexts.default_comparer_program(*at('defaultComparer'),type_from_context=entry('typeFromContext'),context_type=entry('ready')),
  canonicalDefaultComparer=dictionary.default_cached(*at('canonicalDefaultComparer')),
  equality=dictionary.equality_callback(*at('equality')),keyHash=dictionary.key_hash(*at('keyHash')),
  keyEquals=dictionary.key_equals(*at('keyEquals')),getItem=paths.listener_get_item(*at('getItem')),
  cast=paths.compatible_callback(*at('cast')),sameClass=paths.same_callback_class(*at('sameClass')),
  stringDelegate=paths.string_delegate_tail(*at('stringDelegate')),pendingEmpty=paths.pending_empty(*at('pending')),
  typeFromContext=contexts.ready_context_type_program(rr['typeFromContext']+rr['ready'],entry('typeFromContext'),inner=entry('ready')),
  preparation=[preparation_program(rr['prepare']+rr['prepareInner'],entry('prepare'),inner=entry('prepareInner'),mode=m)
   for m in('initialized','being-initialized')]))


def _locate(image,packet,parser,first,**kwargs):
 from scripts.game_data.memorypack.pointer_param import owned
 base=image.pe.image_base;regions=packets.raw(packet,base);found=[]
 for row in owned(image,base+packet['entryRva'])['rows']:
  if bytes.fromhex(row['bytes'])==bytes.fromhex(first):
   try:program=parser(regions,int(row['va'],16),**kwargs)
   except ValueError:continue
   found.append((int(row['va'],16),program))
 need('one-owned-caller-fragment-'+parser.__name__,len(found)==1);return found[0]


def _declaration(image,ctx,symbols,name):
 td=ctx.index.types[name];md=image.metadata
 return dict(typeName=name,definition=td.index,parent=ctx.parent(name),
  fields=[dict(name=md.string(f.name_index),type=symbols.type(ctx.type_pointer(f.type_index)),
   attributes=ctx.field_attributes(f.type_index))for f in md.fields_for(td)],
  methods=[dict(definition=m.index,name=md.string(m.name_index),slot=m.slot,flags=m.flags,
   returnType=symbols.type(ctx.type_pointer(m.return_type)),
   parameters=[symbols.type(ctx.type_pointer(a.type_index))for a in md.parameters_for(m)])for m in md.methods_for(td)])


def derive(image,pins):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.memorypack import leveldata_patrol_radio_request_sources as parent
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
 from scripts.game_data.il2cpp.generic_entries import GenericEntries
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
 _publication_gate(image,pins);base=image.pe.image_base;source=parent.derive(image,pins)
 ctx=NativeReferenceContext(image);symbols=ContextSymbols(image);ge=GenericEntries(image);h={}
 def capture(role,target,span=None):
  h[role]=packets.packet(image,target,span=span);return h[role]
 def program(role,parser,**kw):
  try:return parser(packets.raw(h[role],base),base+h[role]['entryRva'],**kw)
  except ValueError as e:
   raise ValueError('patrolRadioDispatchSources.program:'+role+' entryRva='+str(h[role]['entryRva'])
    +' windowSha256='+str(h[role]['windows'][0]['sha256'])+' parser='+parser.__name__+' detail='+str(e))from e
 capture('playSend',source['proof']['programs']['wrapper']['actualSendCall']['targetVa'])
 capture('stopSend',_call(source['proof']['programs']['stop'][-1],'sendString')['targetVa'])
 play_site,play_call=_locate(image,h['playSend'],paths.play_dispatch_call,'488b4738')
 stop_site,stop=_locate(image,h['stopSend'],paths.stop_inline_dispatch,'498b4638',found=True)
 capture('playDispatch',play_call['actualDispatchCall']['targetVa']);play=program('playDispatch',paths.play_dispatch,found=True)
 capture('playBinding',_call(play,'invokeHandler')['targetVa']);capture('stopBinding',_call(stop,'invokeHandler')['targetVa'])
 capture('lookup',_call(play,'tryGetHandler')['targetVa']);lookup=program('lookup',paths.try_get_handler,found=True)
 capture('find',lookup['findCall']['targetVa']);find=program('find',dictionary.find)
 capture('defaultComparer',_call(find,'defaultComparer')['targetVa'])
 capture('equality',find['requiredEqualityCallbackVa'])
 binding_play=program('playBinding',paths.play_binding,enabled=[True]);binding_stop=program('stopBinding',paths.stop_handler,enabled=[True])
 capture('getItem',_call(binding_play,'listenerGetItem')['targetVa'])
 capture('cast',_call(binding_play,'compatibleCallback')['targetVa']);cast=program('cast',paths.compatible_callback)
 capture('sameClass',cast['compatibilityCall']['targetVa'])
 capture('pending',_call(binding_play,'compactListeners')['targetVa'])
 capture('stringDelegate',_call(binding_stop,'invokeListener')['targetVa'])
 capture('typeFromContext',_call(binding_play,'callbackType')['targetVa'],15)
 g=BytesPath(packets.raw(h['typeFromContext'],base),base+h['typeFromContext']['entryRva']);g.take('488bc1','4863ca','488b0cc8')
 capture('ready',g.relative('e9'),20)
 capture('prepare',_call(find,'prepareComparerClass')['targetVa'],9)
 g=BytesPath(packets.raw(h['prepare'],base),base+h['prepare']['entryRva']);g.take('488b4978');capture('prepareInner',g.relative('e9'))
 key=ctx.index.types[KEY];hash_method,=[m for m in image.metadata.methods_for(key)if image.metadata.string(m.name_index)=='GetHashCode']
 equals_method,=[m for m in image.metadata.methods_for(key)if image.metadata.string(m.name_index)=='Equals'
  and[ctx.type_name(a.type_index)for a in image.metadata.parameters_for(m)]==[KEY]]
 capture('keyHash',image.method_pointer_va(hash_method),3);capture('keyEquals',image.method_pointer_va(equals_method),6)
 send_row=_row(source['proof']['contexts']['send'],0);dispatch=symbols.context(send_row['methodSpec'][0],is_method=True)
 binding_row=_row(dispatch,0);binding=symbols.context(binding_row['methodSpec'][0],is_method=True)
 contexts=dict(dispatch=dispatch,binding=binding,
  dispatcherClass=symbols.context(ctx.index.types[DISPATCHER].index,slots=[3,4]),
  bindingClass=symbols.context(ctx.index.types[BINDING].index,slots=[3]),
  dictionaryClass=symbols.context(ctx.index.types[DICT].index,slots=[2,22]),
  defaultComparerClass=symbols.context(ctx.index.types['System.Collections.Generic.EqualityComparer`1'].index,slots=[0]))
 dtypes=[KEY,BINDING+'<'+KEY+'>'];registrations={}
 def observed(role,definition,args,margs,target):
  rows=ge.observe(definition,args,margs)
  registrations[role]=dict(definition=definition,classArguments=args,methodArguments=margs,actualTargetRva=target-base,
   rows=rows,actualEqualsObservedCanonical=any(r['pointer']==target for r in rows),canonicalPointerAliasClaimed=False)
 for role,arg in(('play',parent.PAYLOAD),('stop','string')):
  event='Beyond.EventData`1<'+arg+'>'
  if role=='play':observed('dispatchPlay',dispatch['definition'],[KEY],[event],base+h['playDispatch']['entryRva'])
  else:
   registrations['dispatchStop']=dict(definition=dispatch['definition'],classArguments=[KEY],methodArguments=[event],
    rows=ge.observe(dispatch['definition'],[KEY],[event]),actualTargetRva=None,inlinedActualCaller=True,canonicalPointerAliasClaimed=False)
  observed('binding'+role,binding['definition'],[KEY],[event],base+h[role+'Binding']['entryRva'])
 observed('lookup',_row(contexts['dispatcherClass'],4)['methodSpec'][0],dtypes,[],base+h['lookup']['entryRva'])
 observed('find',_row(contexts['dictionaryClass'],22)['methodSpec'][0],dtypes,[],base+h['find']['entryRva'])
 observed('defaultComparer',_row(contexts['dictionaryClass'],2)['methodSpec'][0],[KEY],[],base+h['defaultComparer']['entryRva'])
 rows=registrations['defaultComparer']['rows'];need('one-own-canonical-provider-source',len(rows)==1 and rows[0]['pointer']>base)
 capture('canonicalDefaultComparer',rows[0]['pointer'])
 td=ctx.index.types['System.Collections.Generic.GenericEqualityComparer`1']
 method,=[m for m in image.metadata.methods_for(td)if image.metadata.string(m.name_index)=='Equals'and len(image.metadata.parameters_for(m))==2
  and all(_kind(symbols.type(ctx.type_pointer(a.type_index)))==19 for a in image.metadata.parameters_for(m))]
 observed('equality',method.index,[KEY],[],base+h['equality']['entryRva'])
 use=binding_play['usageSites'][0];get_item_usage=derive_typed_usage_context(image,use['instructionVa']-base,label='patrolRadioDispatch.ownListenerGetItem')
 observed('getItem',get_item_usage['methodSpec'][0],get_item_usage['classArguments'],[],base+h['getItem']['entryRva'])
 declarations={name:_declaration(image,ctx,symbols,name)for name in(DISPATCHER,BINDING,HANDLER,KEY,'Beyond.EventDelegateForStruct`1',
  'System.Collections.Generic.GenericEqualityComparer`1','System.Collections.Generic.EqualityComparer`1')}
 handler_fields=[list(ctx.field(HANDLER+'::'+image.metadata.string(f.name_index)))+[image.metadata.string(f.name_index)]
  for f in image.metadata.fields_for(ctx.index.types[HANDLER])if not ctx.field_attributes(f.type_index)&16]
 p=dict(imageBase=base,parentRadioRequest=source,helpers=h,sourceSites=dict(play=play_site-base,stop=stop_site-base),
  contexts=contexts,declarations=declarations,handlerFields=handler_fields,getItemUsage=get_item_usage,registrations=registrations,
  keyMethodDefinitions=dict(hash=dict(definition=hash_method.index,targetRva=image.method_pointer_va(hash_method)-base),
   equals=dict(definition=equals_method.index,targetRva=image.method_pointer_va(equals_method)-base)),
  keyClassUsage=derive_typed_usage_context(image,find['keyClassInstructionVa']-base,label='patrolRadioDispatch.ownCombineKeyClass'))
 p['programs']=_programs(p)
 result=packets.norm(dict(schema=SCHEMA,status='validated-conditional-radio-dispatch-transfers',nativeInputs=pins,proof=p,
  selectedTypedDispatcherAndListenerIterationProved=True,selectedCombineKeyDictionaryLookupProved=True,
  selectedEmptyPendingCleanupProved=True,actualListenerSelectionObserved=False,actualListenerCallbackEffectsProved=False,
  allListenerMutationOrCallbackBranchesProved=False,canonicalStopDispatchPointerClaimed=False,runtimeInvocationObserved=False,playbackProved=False,
  conditions=['Actual ready closed SendGlobal, Dispatcher<CombineKey>, EventBinding<CombineKey>, Dictionary<CombineKey,EventBinding<CombineKey>> and delegate contexts must equal their own reciprocal source substitutions. The selected dictionary/default comparer storage and actual callback MethodInfo/class are stable; registrations do not observe live choices.',
   'Collector is disabled. Dictionary buckets/entries form a valid stable acyclic bounded chain; comparer field is null and cached default comparer uses the independently authenticated own CombineKey raw32 equality body. Complete masked raw32 hash and full key equality retain the nominal plain value4 identity.',
   'The actual context-indexed default-comparer source and separately registered closed provider are independently proved; their pointers need not be equal. The actual helper must receive the exact closed provider MethodInfo and select its own EqualityComparer<CombineKey> static class/slot. No physical pointer equivalence is claimed.',
   'Listener count is nonnegative and at most4096, captured before iteration; indexed references and backing storage remain valid. Callbacks return normally, preserve the captured bound and remaining entries, and finish with no pending operations when dispatch depth returns to zero. Current depth has no overflow.',
   'Each enabled listener callback class is exactly its own context delegate type. Stop selects the generic delegate tail outside its three explicit inline target arms; Play passes the original EventData address to its selected delegate code. Actual installed callback identity and callback effects remain unobserved and unproved.',
   'The Stop inline macro requires the independently proved enclosing SendGlobal frame/local and its original EventData<string> local. Surrounding singleton/Lua/resource/runtime/audio behavior remains separate.']))
 validate(result,pins);_publication_gate(image,pins);return result


def validate(value,pins):
 from scripts.game_data.memorypack import leveldata_patrol_radio_request_sources as parent
 need('source-envelope',value.get('schema')==SCHEMA and value.get('status')=='validated-conditional-radio-dispatch-transfers'and value.get('nativeInputs')==pins
  and all(value.get(k)is True for k in('selectedTypedDispatcherAndListenerIterationProved','selectedCombineKeyDictionaryLookupProved','selectedEmptyPendingCleanupProved'))
  and all(value.get(k)is False for k in('actualListenerSelectionObserved','actualListenerCallbackEffectsProved','allListenerMutationOrCallbackBranchesProved',
   'canonicalStopDispatchPointerClaimed','runtimeInvocationObserved','playbackProved')))
 p=value['proof'];base=p['imageBase'];h=p['helpers'];parent.validate(p['parentRadioRequest'],pins)
 need('exact-own-helper-set',set(h)=={'playSend','stopSend','playDispatch','playBinding','stopBinding','lookup','find','defaultComparer','equality',
  'keyHash','keyEquals','getItem','cast','sameClass','pending','stringDelegate','typeFromContext','ready','prepare','prepareInner','canonicalDefaultComparer'})
 q=_programs(p);need('full-selected-source-replay',q==p['programs'])
 def target(program,role,helper):need('actual-child-'+role,_call(program,role)['targetVa']==base+h[helper]['entryRva'])
 source=p['parentRadioRequest']['proof']
 need('own-actual-SendGlobal-parent-targets',base+h['playSend']['entryRva']==source['programs']['wrapper']['actualSendCall']['targetVa']
  and base+h['stopSend']['entryRva']==_call(source['programs']['stop'][-1],'sendString')['targetVa'])
 need('actual-play-dispatch-E8',q['playCall']['actualDispatchCall']['targetVa']==base+h['playDispatch']['entryRva'])
 for program in(q['playDispatch'][-1],q['stopInline'][-1]):
  target(program,'tryGetHandler','lookup');target(program,'invokeHandler','playBinding'if program is q['playDispatch'][-1]else'stopBinding')
 need('inline-two-path-same-successor',q['stopInline'][0]['nextInstructionVa']==q['stopInline'][1]['nextInstructionVa'])
 for program in q['lookup']:need('own-actual-find-E8',program['findCall']['targetVa']==base+h['find']['entryRva'])
 for program in q['find']['witnesses']:
  for call in program['calls']:target(program,call['role'],'defaultComparer'if call['role']=='defaultComparer'else'prepare')
  if program['requiredEqualityCallbackVa']is not None:need('own-equality-selected-body',program['requiredEqualityCallbackVa']==base+h['equality']['entryRva'])
 for call in q['canonicalDefaultComparer']['calls']:need('same-canonical-default-ready-helper',call['targetVa']==base+h['ready']['entryRva'])
 need('same-key-class-in-inline-equality',q['equality']['keyClassCellVa']==q['find']['witnesses'][0]['keyClassCellVa'])
 key_usage=p['keyClassUsage'];key_site=q['find']['witnesses'][0]
 need('own-actual-CombineKey-class-cell',key_usage['tag']==1 and key_usage['typeName']==KEY
  and key_usage['instructionRva']+base==key_site['keyClassInstructionVa']and key_usage['usageCellRva']+base==key_site['keyClassCellVa'])
 for role in('playBinding','stopBinding'):
  for program in q[role]['witnesses']:
   for call in program['calls']:
    if call['role']=='dynamicListener':continue
    target(program,call['role'],dict(listenerGetItem='getItem',callbackType='typeFromContext',compatibleCallback='cast',invokeListener='stringDelegate',compactListeners='pending')[call['role']])
 need('actual-cast-compatibility-child',q['cast']['compatibilityCall']['targetVa']==base+h['sameClass']['entryRva'])
 contexts=p['contexts'];d=contexts['dispatch'];b=contexts['binding'];dc=contexts['dispatcherClass'];bc=contexts['bindingClass'];dictionary_context=contexts['dictionaryClass']
 send=_row(source['contexts']['send'],0)
 need('own-exact-dispatch-definition',d['definition']==send['methodSpec'][0]and d['typeName']==DISPATCHER and d['methodName']=='Dispatch'
  and d['isMethod']is True and d['count']==1 and dc['definition']==p['declarations'][DISPATCHER]['definition']and dc.get('selectedSlots')==[3,4])
 row=_row(d,0);arg,=row['classArguments'];marg,=row['methodArguments']
 need('own-dispatch-to-binding-reciprocal-arguments',row['typeName']==BINDING and row['methodName']=='Dispatch'and row['methodSpec'][0]==b['definition']
  and _var(arg,dc['definition'])and _var(marg,d['definition'],method=True))
 need('own-binding-method-context',b['typeName']==BINDING and b['methodName']=='Dispatch'and b['isMethod']is True and b['count']==3
  and bc['definition']==p['declarations'][BINDING]['definition']and bc.get('selectedSlots')==[3])
 delegate=_row(b,0)['type'];delegate_arg,=delegate['classArguments'];invoke=_row(b,2)
 need('own-typed-delegate-substitution',delegate['definition']['name']=='Beyond.EventDelegateForStruct`1'and _kind(delegate)==21
  and _kind(delegate['definition'])==18 and _var(delegate_arg,b['definition'],method=True)
  and _row(b,1)['type']==delegate and invoke['typeName']=='Beyond.EventDelegateForStruct`1'and invoke['methodName']=='Invoke'
  and invoke['classArguments']==[delegate_arg]and invoke['methodArguments']==[])
 dispatch_dict=_row(dc,3)['type'];key_var,binding_type=dispatch_dict['classArguments'];binding_arg,=binding_type['classArguments']
 need('own-exact-dispatch-dictionary-context',dispatch_dict['definition']['name']==DICT and _kind(dispatch_dict)==21
  and _var(key_var,dc['definition'])and binding_type['definition']['name']==BINDING and binding_arg==key_var)
 lookup=_row(dc,4);need('own-typed-TryGet-context',lookup['typeName']==DICT and lookup['methodName']=='TryGetValue'
  and lookup['classArguments']==[key_var,binding_type]and lookup['methodArguments']==[])
 need('own-Dictionary-consumed-context',dictionary_context['typeName']==DICT and dictionary_context.get('selectedSlots')==[2,22])
 default=_row(dictionary_context,2);find=_row(dictionary_context,22)
 need('own-dictionary-default-and-find-definitions',default['typeName']=='System.Collections.Generic.EqualityComparer`1'and default['methodName']=='get_Default'
  and _var(default['classArguments'][0],dictionary_context['definition'])and find['typeName']==DICT and find['methodName']=='FindEntry'
  and find['methodArguments']==[]and len(find['classArguments'])==2
  and all(_kind(a)==19 and a['parameterOwner']['typeIndex']==dictionary_context['definition']and a['parameterOwner']['ordinal']==i
   for i,a in enumerate(find['classArguments'])))
 provider=contexts['defaultComparerClass'];decl=p['declarations']['System.Collections.Generic.EqualityComparer`1'];slot=_row(provider,0)['type'];arg,=slot['classArguments']
 need('own-exact-default-provider-static-class',provider['definition']==decl['definition']and provider.get('selectedSlots')==[0]
  and slot['definition']['name']==decl['typeName']and _kind(slot)==21 and _var(arg,decl['definition']))
 static,=[f for f in decl['fields']if f['attributes']&16]
 need('own-default-provider-static-reference-field',static['type']['definition']['name']==decl['typeName']
  and static['type']['classArguments']==[arg]and _kind(static['type'])==21)
 dirty=_row(bc,3);need('own-pending-cleanup-context',dirty['typeName']==BINDING and dirty['methodName']=='_UpdateDirtyHandles'
  and dirty['methodArguments']==[]and _var(dirty['classArguments'][0],bc['definition']))
 for name,fields in((DISPATCHER,[('m_evtBindings',dispatch_dict['name'])]),(BINDING,[('m_iterCounter','int'),
  ('m_pendingOperator','System.Collections.Generic.List`1<Beyond.PendingInfo>'),('<key>k__BackingField','VAR'),('m_handlers','System.Collections.Generic.List`1<'+HANDLER+'>')])):
  decl=p['declarations'][name];actual=[(f['name'],f['type']['name'])for f in decl['fields']if not f['attributes']&16]
  need('own-declared-operational-field-roles-'+name,len(actual)==len(fields)
   and all(a[0]==e[0]and(a[1].startswith('VAR[')if e[1]=='VAR'else a[1]==e[1])for a,e in zip(actual,fields)))
 method,=[m for m in p['declarations'][BINDING]['methods']if m['definition']==b['definition']]
 need('own-byref-binding-parameter',len(method['parameters'])==1 and _var(method['parameters'][0],b['definition'],method=True)
  and bytes.fromhex(method['parameters'][0]['rawHex'])[11]&32)
 for role,name,args,helper in(('hash','GetHashCode',[],'keyHash'),('equals','Equals',[KEY],'keyEquals')):
  m,=[m for m in p['declarations'][KEY]['methods']if m['definition']==p['keyMethodDefinitions'][role]['definition']]
  need('own-CombineKey-named-leaf-'+role,m['name']==name and[a['name']for a in m['parameters']]==args
   and p['keyMethodDefinitions'][role]['targetRva']==h[helper]['entryRva'])
 need('own-handler-concrete-fields',any(f[:3]==[HANDLER,'System.Delegate',16]for f in p['handlerFields'])
  and any(f[:3]==[HANDLER,'bool',24]for f in p['handlerFields']))
 usage=p['getItemUsage'];need('own-actual-GetItem-context',usage['tag']==6 and usage['typeName']=='System.Collections.Generic.List`1'
  and usage['methodName']=='get_Item'and usage['classArguments']==[HANDLER]and usage['methodArguments']==[])
 uses=[u for program in q['playBinding']['witnesses']for u in program['usageSites']]
 need('same-full-GetItem-RIP-request',uses and all(u['instructionVa']==usage['instructionRva']+base and u['cellVa']==usage['usageCellRva']+base for u in uses))
 comparer=p['declarations']['System.Collections.Generic.GenericEqualityComparer`1']
 equality,=[m for m in comparer['methods']if m['name']=='Equals'and len(m['parameters'])==2 and all(_var(a,comparer['definition'])for a in m['parameters'])]
 expected_defs=dict(dispatchPlay=d['definition'],dispatchStop=d['definition'],bindingplay=b['definition'],bindingstop=b['definition'],
  lookup=lookup['methodSpec'][0],find=find['methodSpec'][0],defaultComparer=default['methodSpec'][0],getItem=usage['methodSpec'][0],equality=equality['definition'])
 need('exact-own-registration-observation-set',set(p['registrations'])==set(expected_defs))
 expected_arguments={role:([KEY],['Beyond.EventData`1<'+arg+'>'])for role,arg in
  (('dispatchPlay',parent.PAYLOAD),('dispatchStop','string'),('bindingplay',parent.PAYLOAD),('bindingstop','string'))}
 expected_arguments.update(lookup=([KEY,BINDING+'<'+KEY+'>'],[]),find=([KEY,BINDING+'<'+KEY+'>'],[]),
  defaultComparer=([KEY],[]),equality=([KEY],[]),getItem=([HANDLER],[]))
 for role,r in p['registrations'].items():
  need('own-registration-definition-'+role,r['definition']==expected_defs[role]and r['canonicalPointerAliasClaimed']is False
   and(r['classArguments'],r['methodArguments'])==expected_arguments[role]
   and all(r['definition']in row['methodDefinitionIndices']and row['runtimeSelectionObserved']is False for row in r['rows']))
  if role=='dispatchStop':need('inline-not-canonical-pointer',r['actualTargetRva']is None and r['inlinedActualCaller']is True)
  else:
   helper=dict(dispatchPlay='playDispatch',bindingplay='playBinding',bindingstop='stopBinding').get(role,role)
   need('same-actual-registered-target-'+role,r['actualTargetRva']==h[helper]['entryRva']
    and r['actualEqualsObservedCanonical']==any(row['pointer']==base+r['actualTargetRva']for row in r['rows']))
   if r['rows']and role!='defaultComparer':need('existing-own-registration-not-contradictory-'+role,r['actualEqualsObservedCanonical']is True)
   if role=='defaultComparer':need('independently-owned-canonical-provider-body',len(r['rows'])==1
    and r['rows'][0]['pointer']==base+h['canonicalDefaultComparer']['entryRva'])
 need('own-closed-registration-arguments',p['registrations']['lookup']['classArguments']==[KEY,BINDING+'<'+KEY+'>']
  and p['registrations']['find']['classArguments']==[KEY,BINDING+'<'+KEY+'>']
  and p['registrations']['defaultComparer']['classArguments']==[KEY]and p['registrations']['equality']['classArguments']==[KEY]
  and p['registrations']['getItem']['classArguments']==[HANDLER])
 return value
