"""Actual cached loader wrapper and its literal-state-two normal return.

The cached proxy/key lookup is a separate source owner. Numeric state predicates
are preserved literally; no loading/ready-state name or live asset is inferred.
"""
from scripts.game_data.memorypack import leveldata_patrol_request_load_programs as paths
from scripts.game_data.memorypack import leveldata_patrol_request_lookup_sources as manifest
from scripts.game_data.memorypack import leveldata_patrol_resource_validity_sources as packets

SCHEMA='endfield.story-patrol-request-load-sources.v1'
MANAGER='Beyond.Resource.Runtime.BundleLoader+Manager'
PROXY='Beyond.Resource.Runtime.BundleLoader+AssetProxy'
PRIORITY='Beyond.Resource.EResourceRequestPriority'


def need(check,condition):
 if not condition:raise ValueError('patrolRequestLoadSources.'+check)


def _programs(p):
 b=p['imageBase'];h=p['helpers']
 return packets.norm(dict(load=paths.cached_load(packets.raw(h['load'],b),b+h['load']['entryRva']),
  process=paths.process_state_two(packets.raw(h['process'],b),b+h['process']['entryRva'])))


def derive(image,pins):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 _publication_gate(image,pins);source=manifest.derive(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);symbols=ContextSymbols(image)
 call=next(c for c in source['proof']['programs']['request']['calls']if c['role']=='proxy')
 h={'load':packets.packet(image,call['targetVa'])};q=paths.cached_load(packets.raw(h['load'],base),base+h['load']['entryRva'])
 h['process']=packets.packet(image,next(c['targetVa']for c in q['calls']if c['role']=='process'))
 td=ctx.index.types[MANAGER];methods={}
 for role,name in(('load','LoadAsset'),('process','_LoadAssetProxy')):
  m,=[m for m in image.metadata.methods_for(td)if image.metadata.string(m.name_index)==name and image.method_pointer_va(m)==base+h[role]['entryRva']]
  methods[role]=dict(definition=m.index,typeDefinition=td.index,typeName=MANAGER,name=name,targetRva=image.method_pointer_va(m)-base,
   static=bool(m.flags&16),returnType=symbols.type(ctx.type_pointer(m.return_type)),parameters=[symbols.type(ctx.type_pointer(a.type_index))for a in image.metadata.parameters_for(m)])
 uses={str(u['instructionVa']-base):derive_typed_usage_context(image,u['instructionVa']-base,label='patrolRequestLoad.actualClass')for u in q['usageSites']}
 names={u['typeName']for u in uses.values()};layouts={n:manifest._layout(image,ctx,symbols,n)for n in names|{MANAGER,PROXY}}
 chain=[];name=PROXY
 for _ in range(8):
  chain.append(name);parent_name=ctx.parent(name)
  if parent_name=='object':break
  need('finite-own-reference-ancestry',parent_name in ctx.index.types and parent_name not in chain and not ctx.is_value_type(parent_name))
  name=parent_name;layouts[name]=manifest._layout(image,ctx,symbols,name)
 else:need('bounded-reference-ancestry',False)
 state_fields=[(n,f)for n in chain for f in layouts[n]['fields']if not f['static']and f['offset']==56]
 need('one-actual-state-field',len(state_fields)==1);state_owner,state=state_fields[0];state_name=state['type']['name']
 state_layout=manifest._layout(image,ctx,symbols,state_name)
 p=dict(imageBase=base,manifestSource=source,helpers=h,methods=methods,actualUsages=uses,layouts=layouts,
  proxyAncestorChain=chain,stateOwner=state_owner,stateLayout=state_layout,priorityLayout=manifest._layout(image,ctx,symbols,PRIORITY));p['programs']=_programs(p)
 value=packets.norm(dict(schema=SCHEMA,status='validated-conditional-cached-loader-wrapper-source',nativeInputs=pins,proof=p,
  actualLoaderArgumentsCounterAndFramesProved=True,selectedLiteralStateTwoSameProxyReturnProved=True,
  cacheKeyOrLookupEffectsProved=False,counterUniquenessOrAtomicityProved=False,liveProxyStateOrAssetObserved=False,
  runtimeInvocationObserved=False,playbackProved=False,
  conditions=['Same initialized BundleLoader Manager/configuration classes; absent replacement receiver; valid manager/container and successful nonnull cached output. The independent GetOrCreateAssetProxy source must prove the actual key/lookup effects.',
   'The actual signed counter is initially1..divisor-1; its positive reciprocal arithmetic yields quotient zero, retains that value and increments it once without signed overflow. This proves source arithmetic, not uniqueness, atomicity or live counter state.',
   'The selected proxy state byte-field is literally2. The wrapper excludes4, the processor immediately returns the same proxy for2, and the outer request excludes3; no semantic state name, actual resource loading, scheduling or completion is inferred.',
   'Both actual configuration bytes at static offsets18/80 are zero. Other logging/debug paths, state alternatives, cache miss/new-proxy construction and operation scheduling are not selected.']))
 validate(value,pins);_publication_gate(image,pins);return value


def validate(value,pins):
 need('envelope',value.get('schema')==SCHEMA and value.get('status')=='validated-conditional-cached-loader-wrapper-source'and value.get('nativeInputs')==pins
  and all(value.get(k)is True for k in('actualLoaderArgumentsCounterAndFramesProved','selectedLiteralStateTwoSameProxyReturnProved'))
  and all(value.get(k)is False for k in('cacheKeyOrLookupEffectsProved','counterUniquenessOrAtomicityProved','liveProxyStateOrAssetObserved','runtimeInvocationObserved','playbackProved')))
 p=value['proof'];b=p['imageBase'];manifest.validate(p['manifestSource'],pins);need('helper-set',set(p['helpers'])=={'load','process'})
 q=_programs(p);need('complete-owned-source-replay',q==p['programs'])
 call=next(c for c in p['manifestSource']['proof']['programs']['request']['calls']if c['role']=='proxy')
 need('actual-outer-request-E8',call['targetVa']==b+p['helpers']['load']['entryRva'])
 need('actual-process-E8',next(c['targetVa']for c in q['load']['calls']if c['role']=='process')==b+p['helpers']['process']['entryRva'])
 need('same-literal-state-and-root',q['process']['selectedProxyStateLiteral']==2 and q['load']['excludedProxyStateLiteral']==4
  and q['process']['replacementRootCellVa']==q['load']['replacementRootCellVa']==p['manifestSource']['proof']['programs']['request']['replacementRootCellVa'])
 for role,name,args in(('load','LoadAsset',[manifest.PACK,'System.Type','bool','Beyond.Resource.EResourceRequestPriority']),
  ('process','_LoadAssetProxy',[PROXY,'int','bool','Beyond.Resource.EResourceRequestPriority'])):
  m=p['methods'][role];need('actual-named-method:'+role,m['typeName']==MANAGER and m['name']==name and m['static']is False
   and m['targetRva']==p['helpers'][role]['entryRva']and m['returnType']['name']==PROXY and [x['name']for x in m['parameters']]==args)
  for sym,kind in[(m['returnType'],18)]+list(zip(m['parameters'][1:]if role=='load'else m['parameters'],[18,2,17]if role=='load'else[18,8,2,17])):
   raw=bytes.fromhex(sym['rawHex']);need('ordinary-actual-method-ABI:'+role,len(raw)==16 and raw[10]==kind and raw[11]&127==0)
 need('exact-info-byref',bytes.fromhex(p['methods']['load']['parameters'][0]['rawHex'])[10:12]==bytes((17,32)))
 priority=p['priorityLayout'];need('own-priority-enum',priority['typeName']==PRIORITY and priority['valueType']is True and priority['parent']=='System.Enum')
 backing,=[f for f in priority['fields']if not f['static']]
 need('priority-UInt32-backing:actual='+repr((backing['name'],backing['offset'],backing['type']['name'],bytes.fromhex(backing['type']['rawHex'])[10])),backing['name']=='value__'and backing['offset']==16 and backing['type']['name']=='uint'and bytes.fromhex(backing['type']['rawHex'])[10]==9)
 for site in q['load']['usageSites']:
  u=p['actualUsages'][str(site['instructionVa']-b)];need('actual-class-site',u['tag']==1 and u['instructionRva']+b==site['instructionVa']and u['usageCellRva']+b==site['cellVa'])
  if site['role']=='manager':need('own-manager-context',u['typeName']==MANAGER)
 manager=p['layouts'][MANAGER];counter,=[f for f in manager['fields']if f['name']=='s_operationGroupIDGenerator']
 need('own-static-counter',counter['static']is True and counter['offset']==q['load']['counterFieldOffset']and counter['type']['name']=='int')
 container,=[f for f in manager['fields']if f['name']=='m_bundleProxyContainer']
 need('own-container-field',container['offset']==q['load']['cacheReceiverFieldOffset']and container['type']['name']=='Beyond.Resource.Runtime.BundleLoader+BundleProxyContainer'and container['static']is False)
 chain=p['proxyAncestorChain'];need('finite-own-proxy-ancestor-chain',isinstance(chain,list)and 1<=len(chain)<=8 and chain[0]==PROXY and len(chain)==len(set(chain)))
 for i,n in enumerate(chain):
  layout=p['layouts'][n];need('actual-reference-ancestor:'+n,layout['valueType']is False and layout['parent']==(chain[i+1]if i+1<len(chain)else'object'))
 matches=[(n,f)for n in chain for f in p['layouts'][n]['fields']if f['offset']==q['process']['selectedProxyStateOffset']and not f['static']]
 need('unique-inherited-state-field',len(matches)==1);owner,state=matches[0];s=p['stateLayout']
 need('own-proxy-state-Int32-enum',owner==p['stateOwner']and state['type']['name']==s['typeName']and bytes.fromhex(state['type']['rawHex'])[10]==17
  and s['valueType']is True and s['parent']=='System.Enum')
 backing,=[f for f in s['fields']if not f['static']]
 need('actual-state-enum-backing',backing['name']=='value__'and backing['offset']==16 and backing['type']['name']=='int'and bytes.fromhex(backing['type']['rawHex'])[10]==8)
 config_u,=[u for site in q['load']['usageSites']if site['role']=='configuration'for u in[p['actualUsages'][str(site['instructionVa']-b)]]]
 for offset in q['load']['configurationFlagsRequiredZero']:
  fields=[f for f in p['layouts'][config_u['typeName']]['fields']if f['static']and f['offset']==offset]
  need('own-static-configuration-byte:'+str(offset),len(fields)==1 and fields[0]['type']['name']=='bool'and bytes.fromhex(fields[0]['type']['rawHex'])[10]==2)
 return value
