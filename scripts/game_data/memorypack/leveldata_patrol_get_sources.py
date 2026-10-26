"""Selected positive Patrol handle Get and actual generic getter invocation.

The normal domain uses a coherent existing MethodInfo cache hit, the actual
IAssetProxy interface slot and an explicitly selected callback/MethodInfo pair.
All handle storage, class, context, table and asset identities remain conditions.
Cache construction, arbitrary callback effects and actual asset loading are not
inferred from the static generic registration or the inline marker comparisons.
"""
import json
from scripts.game_data.memorypack import leveldata_patrol_get_programs as paths
from scripts.game_data.memorypack import leveldata_patrol_generic_getter_programs as generic
from scripts.game_data.memorypack import leveldata_patrol_resource_validity_sources as validity

SCHEMA='endfield.story-patrol-handle-get-sources.v1'
LEAD='Beyond.Gameplay.Core.PatrolLeadConfigSo'
CHAIN=('Beyond.Resource.FAssetProxyLoaderHandle','Beyond.Resource.FAssetProxyHandle','Beyond.Resource.FAssetProxyUntrackedHandle','Beyond.Resource.IAssetProxy')


def need(check,condition):
 if not condition:raise ValueError('patrolHandleGetSources.'+check)


def norm(value):return json.loads(json.dumps(value))


def _programs(p):
 base=p['imageBase'];h=p['helpers'];rr={k:validity.raw(v,base)for k,v in h.items()}
 return norm(dict(get=[paths.program(rr['get'],base+h['get']['entryRva'],positive=a,hit=b,misses=m,object_id_lane=lane)
  for a,b,m,lane in((False,False,(),156),(True,False,(),156),(True,True,(),156),(True,True,(False,True),156),(True,True,(True,False),160))],
  invocation=[generic.invocation(rr['invoke'],base+h['invoke']['entryRva'],interface_steps=n,inflated=f,inline=i,alternate_pointer=a)
   for n in range(4)for f in(False,True)for i in range(4)for a in(False,True)],
  resolution=generic.resolution_wrapper(rr['resolve'],base+h['resolve']['entryRva']),
  cache=[generic.cache_hit(rr['cache'],base+h['cache']['entryRva'],misses=m)
   for m in((),('tag',),('method',),('class',),('arguments',),('tag','method','class','arguments'))]))


def _contexts(image,usage):
 from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 ctx=NativeReferenceContext(image);symbols=ContextSymbols(image);method=image.metadata.methods[usage['methodSpec'][0]]
 contexts=[];declarations=[]
 for owner in CHAIN:
  need('fresh-nominal-Get-chain',image.type_name(method.declaring_type)==owner and image.metadata.string(method.name_index)=='Get'
   and method.parameter_count==0 and not method.flags&16 and method.generic_container_index>=0)
  formal=symbols.type(ctx.type_pointer(method.return_type));declarations.append(dict(definition=method.index,typeName=owner,
   methodName='Get',slot=method.slot,returnType=formal))
  if owner==CHAIN[-1]:break
  context=symbols.context(method.index,is_method=True);contexts.append(context)
  need('one-own-next-method-context',context['count']==1 and len(context['entries'])==1)
  row,=context['entries'];need('method-context-actual-next-definition',row['kind']==3 and row['relativeSlot']==0 and row['classArguments']==[])
  method=image.metadata.methods[row['methodSpec'][0]]
 return contexts,declarations


def derive(image,pins):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
 from scripts.game_data.il2cpp.generic_entries import GenericEntries
 _publication_gate(image,pins);base=image.pe.image_base;source=validity.derive(image,pins)
 lookup=source['proof']['resourceSource']['proof']['assetSource']['proof']['lookupSource'];child=lookup['proof']['tailChildren']['Get']
 h={'get':validity._parent_packet(child,base)};p=paths.program(validity.raw(h['get'],base),base+child['entryRva'])
 invoke=next(c for c in p['calls']if c['role']=='invokeActualGenericGetter');h['invoke']=validity.packet(image,invoke['targetVa'])
 iv=generic.invocation(validity.raw(h['invoke'],base),invoke['targetVa'],inline=1)
 target=next(c['targetVa']for c in iv['calls']if c['role']=='resolveGenericMethod');h['resolve']=validity.packet(image,target)
 r=generic.resolution_wrapper(validity.raw(h['resolve'],base),target);h['cache']=validity.packet(image,r['actualCacheCall']['targetVa'])
 usage=lookup['proof']['leadSource']['proof']['actualTypedUsages']['Get-MethodInfo'];contexts,decls=_contexts(image,usage)
 ctx=NativeReferenceContext(image);field=list(ctx.field('Beyond.Resource.Runtime.BundleLoader+AssetProxy::m_asset'))
 owner=ctx.index.types['Beyond.Resource.Runtime.BundleLoader+AssetProxy'];method,=[m for m in image.metadata.methods_for(owner)
  if image.metadata.string(m.name_index)=='Get'and m.parameter_count==0 and m.generic_container_index>=0]
 ge=GenericEntries(image);marker=iv['inlineMarkerTargets'][0];observations=[]
 for _,spec_index in ge._rows_by_method.get(method.index,()):
  spec=ge.specs[spec_index];ca=ge.arguments(spec[1])[0];ma=ge.arguments(spec[2])[0]
  for registered in ge.observe(method.index,ca,ma):
   if registered['pointer']==marker and registered not in observations:observations.append(registered)
 need('own-Bundle-Get-inline-marker-static-registration',bool(observations))
 symbols=ContextSymbols(image)
 bundle=dict(definition=method.index,typeName=ctx.image.type_name(method.declaring_type),methodName='Get',slot=method.slot,
  returnType=symbols.type(ctx.type_pointer(method.return_type)),methodContext=symbols.context(method.index,is_method=True),
  markerRegistrations=observations,requestedLeadRegistrations=ge.observe(method.index,[],[LEAD]),runtimeSelectionObserved=False)
 usage_sites={str(u['instructionVa']-base):derive_typed_usage_context(image,u['instructionVa']-base,label='patrolHandleGet.actualTableContext')
  for u in p['table']['classUsages']}
 proof=dict(imageBase=base,resourceValiditySource=source,helpers=h,actualGetRequest=usage,methodContexts=contexts,
  methodDeclarations=decls,bundleAssetField=field,bundleGetter=bundle,actualTableUsages=usage_sites)
 proof['programs']=_programs(proof)
 result=norm(dict(schema=SCHEMA,status='validated-conditional-handle-get-sources',nativeInputs=pins,proof=proof,
  selectedHandleGetStorageAndFrameSourceProved=True,actualInterfaceMethodInfoInvocationSourceProved=True,
  selectedWarmMethodInfoCacheHitSourceProved=True,selectedInlineGetterReferenceEffectsProved=True,
  actualMethodInfoCacheConstructionProved=False,ordinaryDynamicCallbackEffectsProved=False,
  actualHandleAssetOrCallbackIdentityObserved=False,runtimeInvocationObserved=False,playbackProved=False,
  conditions=['Warm coherent closed Get<PatrolLeadConfigSo> contexts follow the exact reciprocal MVAR chain to IAssetProxy.Get; selected actual class/vtable/MethodInfo and matched interface array are valid and stable. No live context identity is observed.',
   'The actual generic MethodInfo cache has compatible stable power-of-two capacity, tag-zero real entries, nonzero sentinel tag, zero sentinel-count branch, exact matching three-QWORD key and an existing bounded hit within4096 probes. Actual IAT lock/unlock calls return normally with ordinary Win64 preservation and no incoherent aliases. Cache creation/history/miss resolution is outside this domain.',
   'The selected callback and MethodInfo pair is the actual first inline getter marker and its compatible initialized closed context, and the receiver has the independently named BundleLoader.AssetProxy m_asset field. The same nonnull field is compatible with both actual expected classes, including the requested Lead class. Other inline byte paths are source witnesses only; no unrelated folded registration identifies them nominally.',
   'Proxy table, class/discriminator, object/asset IDs, generation membership, replacement absence, compatible not-disposed storage and collector conditions from the independent validity owner remain required. No asset, controller or game invocation is observed.']))
 validate(result,pins);_publication_gate(image,pins);return result


def validate(value,pins):
 need('source-envelope',value.get('schema')==SCHEMA and value.get('status')=='validated-conditional-handle-get-sources'and value.get('nativeInputs')==pins
  and all(value.get(k)is True for k in('selectedHandleGetStorageAndFrameSourceProved','actualInterfaceMethodInfoInvocationSourceProved','selectedWarmMethodInfoCacheHitSourceProved','selectedInlineGetterReferenceEffectsProved'))
  and all(value.get(k)is False for k in('actualMethodInfoCacheConstructionProved','ordinaryDynamicCallbackEffectsProved','actualHandleAssetOrCallbackIdentityObserved','runtimeInvocationObserved','playbackProved')))
 p=value['proof'];base=p['imageBase'];validity.validate(p['resourceValiditySource'],pins);need('exact-helper-set',set(p['helpers'])=={'get','invoke','resolve','cache'})
 programs=_programs(p);need('all-complete-programs-replayed',programs==p['programs'])
 src=p['resourceValiditySource']['proof'];lookup=src['resourceSource']['proof']['assetSource']['proof']['lookupSource']
 need('same-fresh-Get-body',p['helpers']['get']==validity._parent_packet(lookup['proof']['tailChildren']['Get'],base))
 expected={'objectGet':'objectGet','compatibleClass':'compatibleInterface','containsGeneration':'containsId','proxyGet':'proxyGet','disposed':'disposed'}
 for c in programs['get'][-1]['calls']:
  target=p['helpers']['invoke']['entryRva']if c['role']=='invokeActualGenericGetter'else src['helpers'][expected[c['role']]]['entryRva']
  need('exact-independent-Get-callee:'+c['role'],c['targetVa']==base+target)
 table=programs['get'][-1]['table']
 need('exact-independent-table-helpers',table['indexedContextTargetVa']==base+src['helpers']['indexedContext']['entryRva']
  and table['preparationTargetVa']==base+src['classPreparation']['actualEntryRva']and table['keyEqualityTargetVa']==base+src['helpers']['keyEquals']['entryRva'])
 for iv in programs['invocation']:
  for c in iv['calls']:
   target=p['helpers']['resolve']['entryRva']if c['role']=='resolveGenericMethod'else src['classPreparation']['actualEntryRva']if c['role']=='prepareClass'else src['helpers']['indexedContext'if c['role']=='indexedContext'else'compatibleInterface']['entryRva']
   need('exact-independent-invocation-callee:'+c['role'],c['targetVa']==base+target)
 need('actual-key-cache-wrapper-E8',programs['resolution']['actualCacheCall']['targetVa']==base+p['helpers']['cache']['entryRva'])
 usage=p['actualGetRequest'];need('exact-actual-Lead-request',usage==lookup['proof']['leadSource']['proof']['actualTypedUsages']['Get-MethodInfo']
  and usage['tag']==6 and usage['typeName']==CHAIN[0]and usage['methodName']=='Get'and usage['classArguments']==[]and usage['methodArguments']==[LEAD])
 need('exact-context-and-declaration-count',len(p['methodContexts'])==3 and len(p['methodDeclarations'])==4)
 definition=usage['methodSpec'][0]
 for index,owner in enumerate(CHAIN):
  decl=p['methodDeclarations'][index];formal=decl['returnType'];parameter=formal['parameterOwner']
  need('reciprocal-Get-return-MVAR',decl['definition']==definition and decl['typeName']==owner and decl['methodName']=='Get'
   and bytes.fromhex(formal['rawHex'])[10]==30 and parameter['methodIndex']==definition and parameter['ordinal']==0)
  if index==3:break
  context=p['methodContexts'][index];row,=context['entries']
  need('exact-next-closed-context',context['definition']==definition and context['typeName']==owner and context['methodName']=='Get'
   and context['isMethod']is True and context['count']==1 and row['kind']==3 and row['relativeSlot']==0 and row['classArguments']==[]
   and row['typeName']==CHAIN[index+1]and row['methodName']=='Get'and len(row['methodArguments'])==1)
  arg,=row['methodArguments'];need('actual-next-parameter-substitution',bytes.fromhex(arg['rawHex'])[10]==30
   and arg['parameterOwner']['methodIndex']==definition and arg['parameterOwner']['ordinal']==0)
  definition=row['methodSpec'][0]
 need('own-Bundle-asset-field',p['bundleAssetField']==['Beyond.Resource.Runtime.BundleLoader+AssetProxy','UnityEngine.Object',208])
 bundle=p['bundleGetter'];formal=bundle['returnType'];context=bundle['methodContext']
 need('own-named-Bundle-generic-getter',bundle['typeName']=='Beyond.Resource.Runtime.BundleLoader+AssetProxy'and bundle['methodName']=='Get'
  and type(bundle['definition'])is int and bundle['definition']>=0 and type(bundle['slot'])is int
  and bytes.fromhex(formal['rawHex'])[10]==30 and formal['parameterOwner']['methodIndex']==bundle['definition']
  and formal['parameterOwner']['ordinal']==0 and bundle['runtimeSelectionObserved']is False)
 need('own-Bundle-generic-context',context['definition']==bundle['definition']and context['typeName']==bundle['typeName']
  and context['methodName']=='Get'and context['isMethod']is True and context['count']==1 and len(context['entries'])==1)
 entry,=context['entries'];need('exact-Bundle-expected-class-MVAR-context',entry['relativeSlot']==0 and entry['kind']==2
  and bytes.fromhex(entry['type']['rawHex'])[10]==30 and entry['type']['parameterOwner']['methodIndex']==bundle['definition']
  and entry['type']['parameterOwner']['ordinal']==0)
 marker=next(iv['inlineMarkerTargets'][0]for iv in programs['invocation']if iv['selectedInline']==1)
 need('actual-Bundle-marker-registration-not-Lead-alias',bool(bundle['markerRegistrations'])and all(
  r['pointer']==marker and bundle['definition']in r['methodDefinitionIndices']and r['runtimeSelectionObserved']is False
  for r in bundle['markerRegistrations']))
 for row in bundle['requestedLeadRegistrations']:
  need('explicit-Lead-registration-observation-only',bundle['definition']in row['methodDefinitionIndices']and row['runtimeSelectionObserved']is False)
 for u in programs['get'][-1]['table']['classUsages']:
  actual=p['actualTableUsages'][str(u['instructionVa']-base)]
  need('actual-table-context-cell',actual['instructionRva']==u['instructionVa']-base and actual['usageCellRva']==u['cellVa']-base)
 return value
