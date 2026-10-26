"""Selected cached Bundle proxy key, default Int64 lookup and output transfer.

Creation, cache miss, diagnostics and live cache/Type/comparer selection are not
inferred from this conditional normal hit source. No report is a derive input.
"""
import json
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack import leveldata_patrol_bundle_cache_programs as paths
from scripts.game_data.memorypack import leveldata_patrol_resource_validity_sources as packets

SCHEMA='endfield.story-patrol-bundle-cache-sources.v1'
CONTAINER='Beyond.Resource.Runtime.BundleLoader+BundleProxyContainer'
PROXY='Beyond.Resource.Runtime.BundleLoader+AssetProxy'
PACK='Beyond.ManifestBinary.RuntimeManifestBinary+AssetInfoPack'
ASSET_INFO='Beyond.ManifestBinary.ManifestDataBinary+AssetInfo'
DICTIONARY='System.Collections.Generic.Dictionary`2'


def need(check,condition):
    if not condition:raise ValueError('patrolBundleCacheSources.'+check)


def norm(v):return json.loads(json.dumps(v))


def same(a,b):return json.dumps(a,sort_keys=True,separators=(',',':'))==json.dumps(b,sort_keys=True,separators=(',',':'))


def _method(image,ctx,owner,name,*,arity=None,target=None):
    md=image.metadata;ms=[m for m in md.methods_for(ctx.index.types[owner])if(name is None or md.string(m.name_index)==name)
        and(arity is None or m.parameter_count==arity)and(target is None or image.method_pointer_va(m)==target)]
    need('one-own-method:'+owner+'.'+str(name),len(ms)==1);m,=ms
    return dict(definition=m.index,owner=owner,name=md.string(m.name_index),slot=m.slot,flags=m.flags,
        targetRva=image.method_pointer_va(m)-image.pe.image_base,parameters=[ctx.type_name(p.type_index)for p in md.parameters_for(m)],returns=ctx.type_name(m.return_type))


def _fields(image,ctx,name,*,ancestors=False):
    from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets
    md=image.metadata;out=[];lineage=[]
    while name and name not in lineage:
        lineage.append(name);td=ctx.index.types[name];fs=list(md.fields_for(td));offsets=runtime_type_field_offsets(md,image.pe,image.registration,td.index)if fs else{}
        for f in fs:out.append(dict(owner=name,name=md.string(f.name_index),typeName=ctx.type_name(f.type_index),
            offset=offsets.get(md.string(f.name_index)),static=bool(ctx.field_attributes(f.type_index)&16)))
        if not ancestors:break
        name=ctx.parent(name)
        if name=='object':name='System.Object'
    return dict(lineage=lineage,fields=out)


def _programs(p):
    from scripts.game_data.memorypack import int_list_sources as contexts,leveldata_patrol_type_dictionary_programs as type_paths
    h=p['helpers'];b=p['imageBase'];rr={k:packets.raw(v,b)for k,v in h.items()};s=p['symbols']
    def one(k,fn,**kw):return fn(rr[k],b+h[k]['entryRva'],**kw)
    return norm(dict(caller=one('caller',paths.caller),key=one('key',paths.key),mix=one('mix',paths.mix_final),tryGet=one('tryGet',paths.try_get),
        find=[one('find',paths.find,misses=m)for m in((),('hash',),('key',),('hash','key'),('key','hash'),('hash','key','hash'))],
        indexed=contexts.initialized_class(rr['indexed']+rr['ready'],b+h['indexed']['entryRva'],indexed=True),
        typeHash=one('typeHash',type_paths.runtime_type_hash_program,prepare=b+s['prepare'],self_getter=b+h['self']['entryRva']),
        typeInvoke=one('typeInvoke',type_paths.runtime_type_hash_invoker_program,prepare=b+s['prepare'],
            callback=b+h['typeHash']['entryRva'],self_getter=b+h['self']['entryRva']),self=one('self',type_paths.self_type_program)))


def _usages(p,g):
    b=p['imageBase'];u=p['typedUsages'];r=g['caller'];need('finite-own-context-sites',set(u)==set(r['typedSites']))
    for role,site in r['typedSites'].items():
        v=u[role];need('actual-parent-usage-site',v['instructionRva']==site['instructionVa']-b and v['usageCellRva']==site['cellVa']-b)
        memory={a+i:x for a,s in packets.raw(p['helpers']['caller'],b)for i,x in enumerate(s)}
        code=bytes.fromhex(v['instructionHex']);need('actual-parent-usage-bytes',code==bytes(memory[site['instructionVa']+i]for i in range(len(code))))
    need('own-AssetProxy-ready-context',u['keyClass']['typeName']==PROXY and u['keyClass']['tag']==1)
    need('own-resource-flag-context',u['config']['typeName']=='Beyond.Resource.ResourceManagerFlag'and u['config']['tag']==1)
    v=u['lookup'];need('actual-closed-dictionary-request',(v['typeName'],v['methodName'],v['classArguments'],v['methodArguments'])==(DICTIONARY,'TryGetValue',['long',PROXY],[]))


def _induction(g):
    need('selected-default-Int64-geometry',all(p['keyBytes']==8 and p['slotStride']==24 and p['slotKeyOffset']==8 and p['slotNextOffset']==4 for p in g['find']))
    return dict(countLimit=4096,slotStride=24,counterInitial=0,counterStep=1,
        invariant='Each failed hash or full Int64 equality loads entries[index].next, checks the stable entry-array length before counter increment, and returns to the exact same index-guarded loop. A hit returns its unchanged index. Stable valid acyclic chains of at most4096 entries reach the first exact match.',
        selectedHitRequired=True,stableSeedAndTablesRequired=True,liveCacheContentsObserved=False)


def _callbacks(p):
    m=p['methods'];b=p['imageBase'];c=p['comparer']
    return dict(typeHash=dict(slot=2,targetRva=m['typeHash']['targetRva'],methodDefinition=m['typeHash']['definition'],receiver='same nonnull actual RuntimeType',selectionObserved=False),
        underlyingType=dict(slot=40,targetRva=m['self']['targetRva'],methodDefinition=m['self']['definition'],returnsSameReceiver=True,selectionObserved=False),
        equality=dict(slot=8,targetRva=c['selectedTargetRva'],methodDefinition=c['definition'],classArguments=['long'],selectionObserved=False),
        dictionary=dict(targetRva=p['helpers']['tryGet']['entryRva'],methodDefinition=p['typedUsages']['lookup']['methodSpec'][0],
            classArguments=['long',PROXY],actualMethodInfoCompatibilityRequired=True,canonicalPointerEquivalenceProved=False,selectionObserved=False))


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp import ready_context_sources
    from scripts.game_data.memorypack import leveldata_patrol_class_preparation_sources as preparation
    _publication_gate(image,pins);b=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata;h={};methods={}
    def add(k,at,span=None):
        need('one-actual-child-target:'+k,k not in h or b+h[k]['entryRva']==at);h[k]=packets.packet(image,at,span=span);return packets.raw(h[k],b)
    def one(k,fn,**kw):return fn(packets.raw(h[k],b),b+h[k]['entryRva'],**kw)
    methods['caller']=_method(image,ctx,CONTAINER,'GetOrCreateAssetProxy',arity=3);add('caller',b+methods['caller']['targetRva']);g=one('caller',paths.caller)
    add('key',g['keyCall']['targetVa']);add('tryGet',g['lookupCall']['targetVa'])
    methods['key']=_method(image,ctx,PROXY,None,arity=2,target=g['keyCall']['targetVa'])
    usages={k:derive_typed_usage_context(image,s['instructionVa']-b,label='patrolBundleCache.actual-'+k)for k,s in g['typedSites'].items()}
    kg=one('key',paths.key)
    for c in kg['calls']:add('typeInvoke'if c['role']=='typeHash'else'mix',c['targetVa'],None if c['role']=='typeHash'else 34)
    methods['mix']=_method(image,ctx,'System.HashCode','MixFinal',arity=1,target=b+h['mix']['entryRva'])
    tg=one('tryGet',paths.try_get);add('find',tg['findCall']['targetVa']);fg=one('find',paths.find)
    for c in fg['calls']:
        if c['role']=='readyContext':add('ready',c['targetVa'],20)
        elif c['role']=='indexedContext':add('indexed',c['targetVa'],15)
    w=BytesPath(packets.raw(h['indexed'],b),b+h['indexed']['entryRva']);w.take('488bc1','4863ca','488b0cc8')
    need('same-exact-ready-context-tail',w.relative('e9')==b+h['ready']['entryRva'])
    ready=ready_context_sources.derive(image,pins,entry=b+h['ready']['entryRva'])
    prepTargets={c['targetVa']for c in fg['calls']if c['role']=='prepareComparer'};need('one-own-comparer-class-preparation',len(prepTargets)==1);prep=preparation.derive(image,pins,target=next(iter(prepTargets)))
    methods['typeHash']=_method(image,ctx,'System.RuntimeType','GetHashCode',arity=0);add('typeHash',b+methods['typeHash']['targetRva'])
    methods['self']=_method(image,ctx,'System.RuntimeType','get_UnderlyingSystemType',arity=0);add('self',b+methods['self']['targetRva'],4)
    eqs=[m for m in md.methods_for(ctx.index.types['System.Collections.Generic.GenericEqualityComparer`1'])if md.string(m.name_index)=='Equals'and m.parameter_count==2]
    need('one-own-Int64-equality-method',len(eqs)==1);eq,=eqs;rows=GenericEntries(image).observe(eq.index,['long'],[])
    need('selected-own-Int64-equality-marker',any(r['pointer']==fg['selectedEqualityCallbackVa']for r in rows))
    comparer=dict(definition=eq.index,owner='System.Collections.Generic.GenericEqualityComparer`1',name='Equals',slot=eq.slot,
        classArguments=['long'],registrations=rows,selectedTargetRva=fg['selectedEqualityCallbackVa']-b,liveSelectionObserved=False)
    seedSite=next(a for a,s in kg['selectedBytes']if s=='488b0d')
    p=dict(imageBase=b,helpers=h,methods=methods,typedUsages=usages,comparer=comparer,
        seedUsage=derive_typed_usage_context(image,seedSite-b,label='patrolBundleCache.actual-seed'),
        declaredValueTypes={name:ctx.is_value_type(name)for name in(CONTAINER,PROXY,PACK,ASSET_INFO,'System.HashCode','System.RuntimeType')},
        fields={name:_fields(image,ctx,name,ancestors=name=='System.RuntimeType')for name in(CONTAINER,PACK,ASSET_INFO,'System.HashCode','System.RuntimeType','Beyond.Resource.ResourceManagerFlag')},
        classPreparation=prep,readyContext=ready,symbols=dict(prepare=next(iter(prepTargets))-b))
    p['programs']=_programs(p);p['chainInduction']=_induction(p['programs']);p['requiredCallbacks']=_callbacks(p)
    value=norm(dict(schema=SCHEMA,status='validated-conditional-patrol-bundle-cache-source',nativeInputs=pins,proof=p,
        selectedCacheKeyLookupAndOutputEffectsProved=True,cacheMissOrCreationEffectsProved=False,liveProxyCacheOrTypeObserved=False,
        runtimeInvocationObserved=False,playbackProved=False,
        conditions=['Same named BundleProxyContainer receiver/AssetInfoPack80 reference, nonnull actual RuntimeType argument, same writable outref, absent replacements, ready owned contexts/classes and stable seed. The actual Type slot2 callback and MethodInfo select the named RuntimeType hash body; its slot40 callback selects the independent self getter.',
            'The actual Dictionary<long,AssetProxy> MethodInfo/context selects the captured compatible Int64/reference helper and its own FindEntry; ready indexed contexts and cached nonnull GenericEqualityComparer<long>, actual selected Equals slot8 target/MethodInfo, positive bucket count, stable valid acyclic entries with at most4096 links and an existing exact hit.',
            'Debug config static byte20 is false; collection is disabled. Key/type hash and outref storage stay disjoint from the call frame. This preserves the same cached proxy reference and makes no proxy-creation call; live hash/seed/cache contents, miss/creation paths, diagnostics, successful loading and playback are not observed.']))
    validate(value,pins);_publication_gate(image,pins);return value


def validate(v,pins):
    from scripts.game_data.il2cpp import ready_context_sources
    from scripts.game_data.memorypack import leveldata_patrol_class_preparation_sources as preparation
    need('envelope',v.get('schema')==SCHEMA and v.get('status')=='validated-conditional-patrol-bundle-cache-source'and v.get('nativeInputs')==pins
        and v.get('selectedCacheKeyLookupAndOutputEffectsProved')is True and all(v.get(k)is False for k in('cacheMissOrCreationEffectsProved','liveProxyCacheOrTypeObserved','runtimeInvocationObserved','playbackProved')))
    p=v['proof'];h=p['helpers'];b=p['imageBase'];need('finite-helper-family',set(h)=={'caller','key','tryGet','mix','typeInvoke','find','ready','indexed','typeHash','self'})
    g=_programs(p);need('complete-source-replay',same(g,p['programs']));_usages(p,g);need('full-Int64-chain-induction',same(_induction(g),p['chainInduction']))
    seedSite=next(a for a,s in g['key']['selectedBytes']if s=='488b0d');seed=p['seedUsage']
    need('actual-seed-class-usage',seed['typeName']=='System.HashCode'and seed['tag']==1 and seed['instructionRva']==seedSite-b
        and seed['usageCellRva']==g['key']['hashCodeClassCellVa']-b)
    memory={a+i:x for a,s in packets.raw(h['key'],b)for i,x in enumerate(s)};code=bytes.fromhex(seed['instructionHex'])
    need('actual-seed-usage-instruction',code==bytes(memory[seedSite+i]for i in range(len(code))))
    need('own-value-and-reference-carriers',same(p['declaredValueTypes'],{CONTAINER:False,PROXY:False,PACK:True,ASSET_INFO:True,'System.HashCode':True,'System.RuntimeType':False}))
    need('actual-key-and-lookup-calls',g['caller']['keyCall']['targetVa']==b+h['key']['entryRva']and g['caller']['lookupCall']['targetVa']==b+h['tryGet']['entryRva']
        and g['tryGet']['findCall']['targetVa']==b+h['find']['entryRva'])
    for c in g['key']['calls']:need('actual-key-callee',c['targetVa']==b+h['typeInvoke'if c['role']=='typeHash'else'mix']['entryRva'])
    preparation.validate(p['classPreparation'],pins);ready_context_sources.validate(p['readyContext'],pins)
    need('exact-own-ready-helper',same(p['readyContext']['proof']['sourceRegions'],[[b+a,s.lower()]for a,s in h['ready']['regions']]))
    for f in g['find']:
        for c in f['calls']:
            target=p['classPreparation']['actualEntryRva']if c['role']=='prepareComparer'else h['ready'if c['role']=='readyContext'else'indexed']['entryRva']
            need('actual-lookup-context-callee',c['targetVa']==b+target)
    m=p['methods'];need('finite-methods',set(m)=={'caller','key','mix','typeHash','self'})
    need('own-whole-caller-method',(m['caller']['owner'],m['caller']['name'],m['caller']['parameters'],m['caller']['returns'],m['caller']['targetRva'])==(CONTAINER,'GetOrCreateAssetProxy',[PACK,'System.Type',PROXY],'void',h['caller']['entryRva']))
    need('own-static-key-method',m['key']['owner']==PROXY and m['key']['name']=='GetHashKey'and m['key']['parameters']==['long','System.Type']and m['key']['returns']=='long'and m['key']['flags']&16 and m['key']['targetRva']==h['key']['entryRva'])
    for k,name,slot,returns,args in(('mix','MixFinal',65535,'uint',['uint']),('typeHash','GetHashCode',2,'int',[]),('self','get_UnderlyingSystemType',40,'System.Type',[])):
        d=m[k];need('own-selected-method:'+k,(d['owner'],d['name'],d['slot'],d['returns'],d['parameters'],d['targetRva'])==('System.HashCode'if k=='mix'else'System.RuntimeType',name,slot,returns,args,h[k]['entryRva']))
    f=p['fields'];need('own-pool-field',any(x==dict(owner=CONTAINER,name='<assetPools>k__BackingField',typeName=DICTIONARY+'<long,'+PROXY+'>',offset=40,static=False)for x in f[CONTAINER]['fields']))
    need('own-seed-field',any(x==dict(owner='System.HashCode',name='s_seed',typeName='uint',offset=0,static=True)for x in f['System.HashCode']['fields']))
    need('own-inherited-runtime-type-handle',any(x==dict(owner='System.Type',name='_impl',typeName='System.RuntimeTypeHandle',offset=16,static=False)for x in f['System.RuntimeType']['fields'])
        and f['System.RuntimeType']['lineage']==['System.RuntimeType','System.Reflection.TypeInfo','System.Type','System.Reflection.MemberInfo','System.Object'])
    need('own-debug-flag-field',any(x['static']is True and x['typeName']=='bool'and x['offset']==20 for x in f['Beyond.Resource.ResourceManagerFlag']['fields']))
    need('actual-info-pack-key',any(x==dict(owner=PACK,name='assetData',typeName=ASSET_INFO,offset=16,static=False)for x in f[PACK]['fields'])
        and any(x==dict(owner=ASSET_INFO,name='pathHashHead',typeName='long',offset=16,static=False)for x in f[ASSET_INFO]['fields']))
    c=p['comparer'];need('own-selected-default-Int64-comparer',(c['owner'],c['name'],c['slot'],c['classArguments'])==('System.Collections.Generic.GenericEqualityComparer`1','Equals',8,['long'])
        and c['liveSelectionObserved']is False and all(x['selectedEqualityCallbackVa']==b+c['selectedTargetRva']for x in g['find'])
        and any(r['pointer']==b+c['selectedTargetRva']and r['runtimeSelectionObserved']is False for r in c['registrations']))
    selected=[r for r in c['registrations']if r['pointer']==b+c['selectedTargetRva']]
    need('own-exact-Int64-comparer-registration',selected and all(c['definition']in r['methodDefinitionIndices']
        and len(r['classInstantiation']['arguments'])==1 and bytes.fromhex(r['classInstantiation']['arguments'][0]['raw_type_record_hex'])[10:12]==bytes((10,128))
        and r['methodInstantiation']['arguments']==[]for r in selected))
    need('exact-dynamic-callback-conditions',same(p['requiredCallbacks'],_callbacks(p)))
