"""Actual Patrol radio request callers and complete value payload transfer.

The source selects the existing PredefinedEventKeys singleton and preserves its
own CombineKey value. The closed SendGlobal requests are authenticated separately
from the dynamic dispatcher, listeners and playback. No static registration is
treated as an observed runtime callback.
"""
from scripts.game_data.memorypack import leveldata_patrol_radio_request_programs as paths
from scripts.game_data.memorypack import leveldata_patrol_resource_validity_sources as packets

SCHEMA='endfield.story-patrol-radio-request-sources.v1'
PAYLOAD='Beyond.Gameplay.Actions.GameAction+RadioRuntimeData'
KEY='Beyond.CombineKey'
KEYS='Beyond.PredefinedEventKeys'
FIELDS=(('radioId','string',16),('fromBegin','bool',24),('index','int',28),
 ('entity','Beyond.Gameplay.Core.Entity',32),('callback','System.Action`1<string>',40),
 ('interruptFinish','bool',48),('enableAdvancedOptions','bool',49),('voOffset','float',52),
 ('reverbOffset','float',56),('attenuationType','Beyond.GEnums.RadioVoiceAttenuationType',60),('noFlushAfterLoading','bool',64))


def need(check,condition):
 if not condition:raise ValueError('patrolRadioRequestSources.'+check)


def _programs(p):
 from scripts.game_data.il2cpp import ready_context_sources
 from scripts.game_data.memorypack.int_list_sources import initialized_class
 from scripts.game_data.memorypack.leveldata_patrol_event_params_programs import disabled_barrier_program
 base=p['imageBase'];h=p['helpers'];rr={k:packets.raw(v,base)for k,v in h.items()}
 return packets.norm(dict(play=[paths.play(rr['play'],base+h['play']['entryRva'],nonnull=a,nonempty=b)for a,b in((False,False),(True,False),(True,True))],
  stop=[paths.stop(rr['stop'],base+h['stop']['entryRva'],nonnull=a,nonempty=b)for a,b in((False,False),(True,False),(True,True))],
  constructor=paths.payload_constructor(rr['constructor'],base+h['constructor']['entryRva']),
  wrapper=paths.send56_wrapper(rr['wrapper'],base+h['wrapper']['entryRva']),
  singleton=paths.singleton_cached(rr['singleton'],base+h['singleton']['entryRva']),
  classReady=paths.class_ready(rr['classReady'],base+h['classReady']['entryRva']),
  ready=ready_context_sources.program(rr['ready'],base+h['ready']['entryRva']),
  indexed=initialized_class(rr['indexed']+rr['indexedReady'],base+h['indexed']['entryRva'],indexed=True),
  barrier=disabled_barrier_program(rr['barrier'],base+h['barrier']['entryRva'])))


def _layout(image,ctx,name):
 from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets
 td=ctx.index.types[name];need('plain-value:'+name,ctx.is_value_type(name)and not ctx.is_enum(name)and ctx.parent(name)=='System.ValueType'and td.generic_container_index<0)
 offsets=runtime_type_field_offsets(image.metadata,image.pe,image.registration,td.index)
 fields=[dict(name=image.metadata.string(f.name_index),typeName=ctx.type_name(f.type_index),offset=offsets[image.metadata.string(f.name_index)],
  static=bool(ctx.field_attributes(f.type_index)&16))for f in image.metadata.fields_for(td)]
 need('owned-size-row:'+name,0<=td.index<image.registration['typeDefinitionsSizesCount'])
 row=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+8*td.index)
 return dict(typeName=name,typeDefinition=td.index,parent=ctx.parent(name),fields=fields,
  boxedBytes=image.pe.u32_at_va(row),marshaledNativeBytes=image.pe.u32_at_va(row+4),wireGrammarAdmitted=False)


def derive(image,pins):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.il2cpp.generic_entries import GenericEntries
 from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
 from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
 from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets
 from scripts.game_data.memorypack import leveldata_patrol_range_sources as parent
 _publication_gate(image,pins);base=image.pe.image_base;source=parent.derive(image,pins);ctx=NativeReferenceContext(image);h={}
 for role in('play','stop'):h[role]=packets.packet(image,base+source['namedMethods'][role][3])
 play=paths.play(packets.raw(h['play'],base),base+h['play']['entryRva']);stop=paths.stop(packets.raw(h['stop'],base),base+h['stop']['entryRva'])
 for role,callrole in(('constructor','payloadConstructor'),('wrapper','sendWrapper'),('singleton','singleton'),('classReady','readyEventManager')):
  h[role]=packets.packet(image,next(c['targetVa']for c in play['calls']if c['role']==callrole))
 ctor=paths.payload_constructor(packets.raw(h['constructor'],base),base+h['constructor']['entryRva'])
 barrier=ctor['barrierCalls'][0]['targetVa'];h['barrier']=packets.packet(image,barrier,span=12)
 g=BytesPath(packets.raw(h['barrier'],base),barrier);g.relative('833d');g.take('00','4c8bc1');ret=g.relative('74',1)
 tail=packets.packet(image,ret,span=1);h['barrier']['windows']+=tail['windows'];h['barrier']['regions']+=tail['regions']
 singleton=paths.singleton_cached(packets.raw(h['singleton'],base),base+h['singleton']['entryRva'])
 h['ready']=packets.packet(image,next(c['targetVa']for c in singleton['calls']if c['role']=='readyContext'),span=20)
 indexed=next(c['targetVa']for c in singleton['calls']if c['role']=='indexedContext');h['indexed']=packets.packet(image,indexed,span=15)
 g=BytesPath(packets.raw(h['indexed'],base),indexed);g.take('488bc1','4863ca','488b0cc8');h['indexedReady']=packets.packet(image,g.relative('e9'),span=20)
 proof=dict(imageBase=base,rangeSource=source,helpers=h);programs=_programs(proof);proof['programs']=programs
 uses={}
 for role in('play','stop'):
  uses[role]={u['role']:derive_typed_usage_context(image,u['instructionVa']-base,label='patrolRadioRequest.actualUsage')for u in programs[role][-1]['usageSites']}
 wrapper=programs['wrapper'];uses['playSend']=derive_typed_usage_context(image,wrapper['methodInfoSite']['instructionVa']-base,label='patrolRadioRequest.closedSend')
 proof['actualUsages']=uses;ge=GenericEntries(image);proof['registrations']={}
 for role,u,target in(('singleton',uses['play']['predefinedKeySingleton'],base+h['singleton']['entryRva']),
  ('playSend',uses['playSend'],wrapper['actualSendCall']['targetVa']),
  ('stopSend',uses['stop']['sendMethodInfo'],next(c['targetVa']for c in stop['calls']if c['role']=='sendString'))):
  rows=ge.observe(u['methodSpec'][0],u['classArguments'],u['methodArguments'])
  proof['registrations'][role]=dict(actualTargetRva=target-base,rows=rows,
   actualTargetEqualsObservedCanonical=any(r['pointer']==target for r in rows),canonicalPointerAliasClaimed=False)
 symbols=ContextSymbols(image);singleton_method=image.metadata.methods[uses['play']['predefinedKeySingleton']['methodSpec'][0]]
 proof['singletonDeclaration']=dict(definition=singleton_method.index,declaringType=singleton_method.declaring_type,
  returnType=symbols.type(ctx.type_pointer(singleton_method.return_type)))
 std=ctx.index.types['Beyond.Singleton`1'];offsets=runtime_type_field_offsets(image.metadata,image.pe,image.registration,std.index)
 proof['singletonFields']=[dict(name=image.metadata.string(f.name_index),type=symbols.type(ctx.type_pointer(f.type_index)),
  offset=offsets[image.metadata.string(f.name_index)],static=bool(ctx.field_attributes(f.type_index)&16))for f in image.metadata.fields_for(std)]
 proof['contexts']=dict(singleton=symbols.context(singleton_method.declaring_type,is_method=False),send=symbols.context(uses['playSend']['methodSpec'][0],is_method=True))
 proof['payloadLayout']=_layout(image,ctx,PAYLOAD);proof['keyLayout']=_layout(image,ctx,KEY)
 proof['keyFields']={name:list(ctx.field(KEYS+'::'+name))for name in('SHOW_RADIO','MANUAL_STOP_RADIO')}
 td=ctx.index.types[PAYLOAD];method,=[m for m in image.metadata.methods_for(td)if image.metadata.string(m.name_index)=='.ctor']
 proof['constructorMethod']=dict(definition=method.index,typeName=PAYLOAD,name='.ctor',static=bool(method.flags&16),
  parameters=[ctx.type_name(p.type_index)for p in image.metadata.parameters_for(method)],returnType=ctx.type_name(method.return_type),targetRva=image.method_pointer_va(method)-base)
 enum=ctx.index.types['Beyond.GEnums.RadioVoiceAttenuationType'];field,=[f for f in image.metadata.fields_for(enum)if image.metadata.string(f.name_index)=='value__']
 proof['attenuationEnum']=dict(typeName=ctx.image.type_name(enum.index),typeDefinition=enum.index,isEnum=ctx.is_enum(ctx.image.type_name(enum.index)),
  backingType=ctx.type_name(field.type_index),backing=symbols.type(ctx.type_pointer(field.type_index)))
 value=packets.norm(dict(schema=SCHEMA,status='validated-conditional-radio-request-sources',nativeInputs=pins,proof=proof,
  selectedPlayStopArgumentsAndFullFrameProved=True,completeRadioValue56ConstructionAndTransferProved=True,
  actualCombineKeyAndClosedSendRequestsProved=True,selectedCachedKeySingletonEffectsProved=True,
  actualDispatcherOrListenerEffectsProved=False,runtimeCallbackSelectionObserved=False,runtimeInvocationObserved=False,playbackProved=False,
  conditions=['Actual caller metadata is initialized and replacement receivers are absent; compatible stable strings and the selected ready nonnull PredefinedEventKeys singleton/static context are required.',
   'Collector is disabled. Actual closed Singleton and SendGlobal MethodInfo/class contexts and class-ready flags are coherent; static registrations do not observe these live selections.',
   'Nonnull nonempty radio IDs request the own SHOW_RADIO or MANUAL_STOP_RADIO CombineKey without scalar/enum reinterpretation. Empty/null IDs return without a request. The complete zero-initialized value56 includes padding, all constructor writes and the final noFlush byte.',
   'SendGlobal dispatcher/listener/optional Lua effects and actual audio playback remain independent source and runtime joins.']))
 validate(value,pins);_publication_gate(image,pins);return value


def validate(value,pins):
 need('source-envelope',value.get('schema')==SCHEMA and value.get('nativeInputs')==pins and value.get('status')=='validated-conditional-radio-request-sources'
  and all(value.get(k)is True for k in('selectedPlayStopArgumentsAndFullFrameProved','completeRadioValue56ConstructionAndTransferProved','actualCombineKeyAndClosedSendRequestsProved','selectedCachedKeySingletonEffectsProved'))
  and all(value.get(k)is False for k in('actualDispatcherOrListenerEffectsProved','runtimeCallbackSelectionObserved','runtimeInvocationObserved','playbackProved')))
 p=value['proof'];base=p['imageBase'];source=p['rangeSource'];need('same-current-consumer',source['nativeInputs']==pins)
 need('exact-helper-set',set(p['helpers'])=={'play','stop','constructor','wrapper','singleton','classReady','ready','indexed','indexedReady','barrier'})
 q=_programs(p);need('whole-selected-byte-replay',q==p['programs'])
 for role in('play','stop'):
  need('actual-range-call:'+role,p['helpers'][role]['entryRva']==source['namedMethods'][role][3])
  targets={'singleton':'singleton','readyEventManager':'classReady','payloadConstructor':'constructor','sendWrapper':'wrapper'}
  for call in q[role][-1]['calls']:
   if call['role']in targets:need('actual-request-child:'+call['role'],call['targetVa']==base+p['helpers'][targets[call['role']]]['entryRva'])
  for site in q[role][-1]['usageSites']:
   u=p['actualUsages'][role][site['role']];need('actual-RIP-cell:'+site['role'],u['instructionRva']+base==site['instructionVa']and u['usageCellRva']+base==site['cellVa'])
   if site['role']=='predefinedKeySingleton':need('own-closed-singleton',u['tag']==6 and u['typeName']=='Beyond.Singleton`1'and u['methodName']=='get_instance'and u['classArguments']==[KEYS]and u['methodArguments']==[])
   elif site['role']=='eventManagerClass':need('own-manager-class',u['tag']==1 and u['typeName']=='Beyond.EventManager')
   else:need('own-stop-send',u['tag']==6 and u['typeName']=='Beyond.EventManager'and u['methodName']=='SendGlobal'and u['classArguments']==[]and u['methodArguments']==['string'])
 u=p['actualUsages']['playSend'];site=q['wrapper']['methodInfoSite'];need('own-play-send',u['tag']==6 and u['typeName']=='Beyond.EventManager'and u['methodName']=='SendGlobal'
  and u['classArguments']==[]and u['methodArguments']==[PAYLOAD]and u['instructionRva']+base==site['instructionVa']and u['usageCellRva']+base==site['cellVa'])
 for role,target in(('singleton',base+p['helpers']['singleton']['entryRva']),('playSend',q['wrapper']['actualSendCall']['targetVa']),
  ('stopSend',next(c['targetVa']for c in q['stop'][-1]['calls']if c['role']=='sendString'))):
  r=p['registrations'][role];u=p['actualUsages']['play']['predefinedKeySingleton']if role=='singleton'else p['actualUsages']['playSend']if role=='playSend'else p['actualUsages']['stop']['sendMethodInfo']
  need('own-registration-observation-not-callee-alias:'+role,r['actualTargetRva']+base==target
   and r['actualTargetEqualsObservedCanonical']==any(row['pointer']==target for row in r['rows'])and r['canonicalPointerAliasClaimed']is False
   and all(u['methodSpec'][0]in row['methodDefinitionIndices']and row['runtimeSelectionObserved']is False for row in r['rows']))
 for c in q['constructor']['barrierCalls']:need('same-independent-disabled-barrier',c['targetVa']==base+p['helpers']['barrier']['entryRva'])
 for c in q['singleton']['calls']:need('same-ready-indexed-target',c['targetVa']==base+p['helpers']['ready'if c['role']=='readyContext'else'indexed']['entryRva'])
 payload=p['payloadLayout'];need('own-complete-payload-layout',payload['typeName']==PAYLOAD and payload['parent']=='System.ValueType'and payload['boxedBytes']==72
  and payload['wireGrammarAdmitted']is False and [(f['name'],f['typeName'],f['offset'])for f in payload['fields']if not f['static']]==list(FIELDS))
 key=p['keyLayout'];need('own-plain-key-layout',key['typeName']==KEY and key['parent']=='System.ValueType'and key['boxedBytes']==20 and key['marshaledNativeBytes']==4
  and key['wireGrammarAdmitted']is False and [(f['name'],f['typeName'],f['offset'])for f in key['fields']if not f['static']]==[('m_index','int',16)])
 need('own-key-fields',p['keyFields']==dict(SHOW_RADIO=[KEYS,KEY,1292],MANUAL_STOP_RADIO=[KEYS,KEY,1296]))
 m=p['constructorMethod'];need('own-payload-constructor-ABI',m['typeName']==PAYLOAD and m['name']=='.ctor'and m['static']is False and m['returnType']=='void'
  and m['parameters']==['string','bool','int','System.Action`1<string>','Beyond.Gameplay.Core.Entity']and m['targetRva']==p['helpers']['constructor']['entryRva'])
 e=p['attenuationEnum'];need('own-attenuation-backing',e['typeName']==FIELDS[-2][1]and e['isEnum']is True and e['backingType']=='int'and bytes.fromhex(e['backing']['rawHex'])[10]==8)
 decl=p['singletonDeclaration'];need('own-singleton-return-VAR',decl['definition']==p['actualUsages']['play']['predefinedKeySingleton']['methodSpec'][0]
  and bytes.fromhex(decl['returnType']['rawHex'])[10]==19 and decl['returnType']['parameterOwner']['ordinal']==0
  and decl['returnType']['parameterOwner']['typeIndex']==decl['declaringType'])
 need('own-context-definitions',p['contexts']['singleton']['definition']==decl['declaringType']and p['contexts']['singleton']['isMethod']is False
  and p['contexts']['singleton']['typeName']=='Beyond.Singleton`1'and p['contexts']['send']['definition']==p['actualUsages']['playSend']['methodSpec'][0]
  and p['contexts']['send']['typeName']=='Beyond.EventManager'and p['contexts']['send']['methodName']=='SendGlobal')
 context=p['contexts']['singleton'];row=context['entries'][0];arg,=row['type']['classArguments']
 need('own-singleton-slot-zero-static-carrier',row['relativeSlot']==0 and row['kind']==2 and row['type']['definition']['name']=='Beyond.Singleton`1'
  and arg==decl['returnType']and bytes.fromhex(row['type']['rawHex'])[10]==21)
 field,=[f for f in p['singletonFields']if f['static']and f['offset']==q['singleton']['staticReferenceOffset']]
 need('own-singleton-static-reference-field',bytes.fromhex(field['type']['rawHex'])[10]==19
  and field['type']['parameterOwner']==decl['returnType']['parameterOwner'])
 context=p['contexts']['send'];need('exact-selected-send-context-count',context['isMethod']is True and context['count']==2 and len(context['entries'])==2)
 row=context['entries'][0];key,=row['classArguments'];event,=row['methodArguments'];arg,=event['classArguments']
 need('actual-dispatch-recursive-substitution',row['relativeSlot']==0 and row['kind']==3 and row['typeName']=='Beyond.EventDispatcher`1'and row['methodName']=='Dispatch'
  and key['name']==KEY and bytes.fromhex(key['rawHex'])[10]==17 and event['definition']['name']=='Beyond.EventData`1'
  and bytes.fromhex(event['definition']['rawHex'])[10]==17 and bytes.fromhex(event['rawHex'])[10]==21
  and bytes.fromhex(arg['rawHex'])[10]==30 and arg['parameterOwner']['methodIndex']==context['definition']and arg['parameterOwner']['ordinal']==0)
 return value
