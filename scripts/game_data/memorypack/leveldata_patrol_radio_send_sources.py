"""Selected SendGlobal frames, payload locals and no-Lua-registration return.

The ordinary dispatcher is independently joined. Its listeners receive the
unchanged EventData argument; actual listener effects/registration and playback
remain runtime boundaries. This domain selects a nonnull empty Lua-key set.
"""
from scripts.game_data.memorypack import leveldata_patrol_radio_send_programs as paths
from scripts.game_data.memorypack import leveldata_patrol_radio_request_programs as request_paths
from scripts.game_data.memorypack import leveldata_patrol_radio_dispatch_sources as dispatcher
from scripts.game_data.memorypack import leveldata_patrol_resource_validity_sources as packets

SCHEMA='endfield.story-patrol-radio-send-sources.v1'
MANAGER='Beyond.EventManager'
KEY='Beyond.CombineKey'
SINGLETON='Beyond.Singleton`1'
SET='System.Collections.Generic.HashSet`1'


def need(check,condition):
 if not condition:raise ValueError('patrolRadioSendSources.'+check)


def _programs(p):
 b=p['imageBase'];h=p['helpers'];raw={k:packets.raw(v,b)for k,v in h.items()}
 return packets.norm(dict(play=paths.play(raw['playSend'],b+h['playSend']['entryRva']),
  stop=[paths.stop(raw['stopSend'],b+h['stopSend']['entryRva'],found=f)for f in(False,True)],
  singleton=request_paths.singleton_cached(raw['singleton'],b+h['singleton']['entryRva']),
  emptyLuaKeys=paths.empty_lua_keys(raw['containsLuaKey'],b+h['containsLuaKey']['entryRva'])))


def derive(image,pins):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.il2cpp.generic_entries import GenericEntries
 from scripts.game_data.memorypack.leveldata_patrol_request_lookup_sources import _layout
 _publication_gate(image,pins);source=dispatcher.derive(image,pins);p=source['proof'];base=p['imageBase'];ctx=NativeReferenceContext(image);symbols=ContextSymbols(image);ge=GenericEntries(image)
 h={k:p['helpers'][k]for k in('playSend','stopSend')};q=paths.play(packets.raw(h['playSend'],base),base+h['playSend']['entryRva'])
 for role in('singleton','containsLuaKey'):h[role]=packets.packet(image,next(c['targetVa']for c in q['calls']if c['role']==role))
 uses={};methods={};registrations={}
 for role,f in(('playSend',paths.play),('stopSend',lambda r,e:paths.stop(r,e,found=False))):
  program=f(packets.raw(h[role],base),base+h[role]['entryRva'])
  for site in program['usageSites']:
   u=derive_typed_usage_context(image,site['instructionVa']-base,label='patrolRadioSend.actualMethod');uses[str(site['instructionVa']-base)]=u
   r=site['role']
   if r in methods:continue
   m=image.metadata.methods[u['methodSpec'][0]];methods[r]=dict(definition=m.index,declaringType=m.declaring_type,typeName=image.type_name(m.declaring_type),name=image.metadata.string(m.name_index),
    static=bool(m.flags&16),returnType=symbols.type(ctx.type_pointer(m.return_type)),parameters=[symbols.type(ctx.type_pointer(a.type_index))for a in image.metadata.parameters_for(m)])
   registrations[r]=dict(rows=ge.observe(m.index,u['classArguments'],u['methodArguments']),actualTargetRva=h[r]['entryRva'],canonicalPointerAliasClaimed=False)
 singleton_method=methods['singleton'];fields=_layout(image,ctx,symbols,SINGLETON)
 proof=dict(imageBase=base,dispatcherSource=source,helpers=h,actualUsages=uses,methods=methods,registrations=registrations,
  managerLayout=_layout(image,ctx,symbols,MANAGER),setLayout=_layout(image,ctx,symbols,SET),singletonLayout=fields,
  singletonContext=symbols.context(singleton_method['declaringType'],is_method=False,slots=[0]),genericDefinitionOffsetsUsedForClosedSetLayout=False)
 proof['programs']=_programs(proof)
 value=packets.norm(dict(schema=SCHEMA,status='validated-conditional-radio-send-normal-frames',nativeInputs=pins,proof=proof,
  selectedSendGlobalFramesAndPayloadTransfersProved=True,selectedNoLuaKeyReturnProved=True,
  liveSingletonTableOrListenerObserved=False,selectedListenerCallbackEffectsProved=False,runtimeInvocationObserved=False,playbackProved=False,
  conditions=['Initialized actual SendGlobal method contexts, ready coherent Singleton<EventManager> class/static/context and the same nonnull current EventManager are required. The actual global EventDispatcher<CombineKey> field and its independently proved default handler table/list paths are selected.',
   'The same nonnull HashSet<CombineKey> in EventManager field32 has a null bucket array. Its actual Contains source returns false without hashing/callbacks or nonframe writes, so no Lua dispatch is requested. Nonempty Lua-key search and Lua-present paths are outside this finite domain.',
   'Collector is disabled, stack/payload storage is valid and callbacks preserve the caller frame and remaining listener-bound conditions. Play copies all56 bytes including padding; Stop forwards the same string reference in its own8-byte EventData local. Actual listeners/delegates, registration/mutation and playback remain unobserved.']))
 validate(value,pins);_publication_gate(image,pins);return value


def validate(value,pins):
 need('envelope',value.get('schema')==SCHEMA and value.get('status')=='validated-conditional-radio-send-normal-frames'and value.get('nativeInputs')==pins
  and all(value.get(k)is True for k in('selectedSendGlobalFramesAndPayloadTransfersProved','selectedNoLuaKeyReturnProved'))
  and all(value.get(k)is False for k in('liveSingletonTableOrListenerObserved','selectedListenerCallbackEffectsProved','runtimeInvocationObserved','playbackProved')))
 p=value['proof'];b=p['imageBase'];source=p['dispatcherSource'];dispatcher.validate(source,pins);d=source['proof'];parent=d['parentRadioRequest']['proof']
 need('actual-helper-set',set(p['helpers'])=={'playSend','stopSend','singleton','containsLuaKey'})
 q=_programs(p);need('full-source-replay',q==p['programs'])
 for role in('playSend','stopSend'):need('same-independent-enclosing-send:'+role,p['helpers'][role]==d['helpers'][role])
 need('same-actual-play-dispatch-call',q['play']['dispatchMacro']==d['programs']['playCall'])
 need('same-actual-stop-dispatch-macros',[x['dispatchMacro']for x in q['stop']]==d['programs']['stopInline'])
 for role,program in [('playSend',q['play'])]+[('stopSend',x)for x in q['stop']]:
  for c in program['calls']:
   target=b+(parent['helpers']['barrier']['entryRva']if c['role']=='barrier'else p['helpers'][c['role']]['entryRva'])
   need('actual-independent-child:'+c['role'],c['targetVa']==target)
  for site in program['usageSites']:
   u=p['actualUsages'][str(site['instructionVa']-b)];need('actual-typed-site',u['instructionRva']+b==site['instructionVa']and u['usageCellRva']+b==site['cellVa']and u['tag']==6)
   need('actual-own-method-request',u['typeName']==(SINGLETON if site['role']=='singleton'else SET)and u['methodName']==('get_instance'if site['role']=='singleton'else'Contains')
    and u['classArguments']==([MANAGER]if site['role']=='singleton'else[KEY])and u['methodArguments']==[])
 for c in q['singleton']['calls']:
  need('same-independent-ready-or-indexed-source',c['targetVa']==b+parent['helpers']['ready'if c['role']=='readyContext'else'indexed']['entryRva'])
 need('same-disabled-collector',all(x['collectorDisabledFlagVa']==parent['programs']['barrier']['collectorDisabledFlagVa']for x in q['stop']))
 for role,owner,name,param_names in(('singleton',SINGLETON,'get_instance',[]),('containsLuaKey',SET,'Contains',['VAR[0]'])):
  m=p['methods'][role];need('own-method-declaration:'+role,m['typeName']==owner and m['name']==name and m['static']is(role=='singleton')and len(m['parameters'])==len(param_names))
  formal=m['returnType']if role=='singleton'else m['parameters'][0]
  need('reciprocal-own-VAR:'+role,bytes.fromhex(formal['rawHex'])[10]==19 and formal['parameterOwner']['typeIndex']==m['declaringType']and formal['parameterOwner']['ordinal']==0)
  need('no-canonical-pointer-alias',p['registrations'][role]['actualTargetRva']==p['helpers'][role]['entryRva']and p['registrations'][role]['canonicalPointerAliasClaimed']is False)
 manager=p['managerLayout'];need('own-manager-layout',manager['typeName']==MANAGER and manager['valueType']is False)
 for offset,typ in((24,dispatcher.DISPATCHER+'<'+KEY+'>'),(32,SET+'<'+KEY+'>')):
  rows=[f for f in manager['fields']if not f['static']and f['offset']==offset]
  need('own-current-manager-field:'+str(offset),len(rows)==1 and rows[0]['type']['name']==typ and [a['name']for a in rows[0]['type']['classArguments']]==[KEY])
 rows=[f for f in p['setLayout']['fields']if not f['static']and f['type']['name']=='int[]']
 need('own-key-set-array-declaration',p['setLayout']['typeName']==SET and len(rows)==1 and p['genericDefinitionOffsetsUsedForClosedSetLayout']is False)
 # The actual closed method's complete source proves the null QWORD predicate
 # at16. An open generic metadata offset is never used to establish that slot.
 s=p['singletonContext'];row,=s['entries'];arg,=row['type']['classArguments'];decl=p['methods']['singleton']
 need('actual-singleton-class-context',s['typeName']==SINGLETON and s['definition']==decl['declaringType']and s['isMethod']is False and s['selectedSlots']==[0]
  and row['kind']==2 and row['relativeSlot']==0 and row['type']['definition']['name']==SINGLETON and arg['parameterOwner']==decl['returnType']['parameterOwner'])
 field,=[f for f in p['singletonLayout']['fields']if f['static']and f['offset']==0]
 need('own-singleton-static-reference',bytes.fromhex(field['type']['rawHex'])[10]==19 and field['type']['parameterOwner']==decl['returnType']['parameterOwner'])
 return value
