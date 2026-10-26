"""Offline normal untracked-handle construction, RetainHandle and ID storage.

The counter is not an observed or atomic source of globally unique IDs. Actual
selected class/context/comparer identities, valid stable storage, ready flags,
spare capacity and absent replacements are conditions on these byte effects.
"""
import hashlib,json
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack import leveldata_patrol_resource_id_programs as paths

SCHEMA='endfield.story-patrol-resource-id-sources.v1'
HANDLE='Beyond.Resource.FAssetProxyUntrackedHandle'
BUNDLE='Beyond.Resource.Runtime.BundleLoader+AssetProxy'
PREFAB='Beyond.Resource.Runtime.PrefabInstantiateProxy'
COMPACT='Beyond.Resource.Runtime.CompactIntSet'
UTILITY='Beyond.Resource.FAssetProxyHandleUtils'
MANAGER='Beyond.Resource.ResourceManager'
FLAGS='Beyond.Resource.ResourceManagerFlag'
HASHSET='System.Collections.Generic.HashSet`1'
POOL='Beyond.PoolCore.ObjectPool`1'


def need(check,condition):
    if not condition:raise ValueError('patrolResourceIdSources.'+check)


def norm(value):return json.loads(json.dumps(value))


def same(a,b):return json.dumps(a,sort_keys=True,separators=(',',':'))==json.dumps(b,sort_keys=True,separators=(',',':'))


def packet(image,at,span=None):
    from scripts.game_data.memorypack.leveldata_patrol_checkpoint_helper_sources import packet as owned
    if span is None:return dict(**owned(image,at),boundary='complete-native-owned-family')
    base=image.pe.image_base;b=image.pe.bytes_at_va(at,span)
    return dict(entryRva=at-base,regions=[[at-base,b.hex().upper()]],windows=[dict(startRva=at-base,endRva=at-base+span,
        sha256=hashlib.sha256(b).hexdigest().upper())],boundary='actual-selected-span-no-physical-extent')


def raw(own,base):
    from scripts.game_data.memorypack.leveldata_patrol_checkpoint_helper_sources import verify_packet,regions
    verify_packet(own);return regions(own,base)


def _programs(p):
    from scripts.game_data.memorypack import leveldata_patrol_proxy_storage_programs as storage,leveldata_patrol_event_collection_programs as pools
    from scripts.game_data.memorypack.int_list_sources import initialized_class
    h=p['helpers'];base=p['imageBase'];rr={k:raw(v,base)for k,v in h.items()}
    def one(k,fn,**kw):return fn(rr[k],base+h[k]['entryRva'],**kw)
    result=dict(constructor=[one('constructor',paths.constructor,kind=k,compatibility=c,frame=f)
        for k in('bundle','prefab')for c in('first','second','neither')for f in(False,True)],
        counter=one('counter',paths.counter),bundle=[one('bundle',paths.bundle_retain_handle,added=f)for f in(False,True)],
        prefab=[one('prefab',paths.prefab_retain_handle,set_present=f)for f in(False,True)],
        compatible=[one('compatible',paths.compatible_class,matches=f)for f in(False,True)],hierarchy=one('hierarchy',paths.hierarchy_ready),
        compact=[one('compact',paths.compact_add,count=c,match=m)for c in range(5)for m in range(c+1)if c<4 or m],
        overflow=[one('compact',paths.compact_add,overflow=True,added=f)for f in(False,True)],
        promotion=one('compact',paths.compact_promote),seed=one('seed',paths.seed_add),
        hashSet=[one('hashSet',paths.hashset_add,interface_steps=i,**kw)for i in(0,1,2)for kw in(
            dict(),dict(reuse_free=True),dict(duplicate=True),dict(misses=(False,)),dict(misses=(True,)),
            dict(misses=(False,True)),dict(misses=(True,False),reuse_free=True),dict(misses=(False,True),duplicate=True))],
        equality=[storage.key_equality_program(BytesPath(rr['equality'],base+h['equality']['entryRva']),interface_steps=i)for i in(0,1,2)],
        pool=[one('pool',pools.spare_pool_allocate,spare_count=n)for n in(1,2,4096)],barrier=one('barrier',pools.disabled_barrier))
    result['indexed']=initialized_class(rr['indexed']+rr['indexedReady'],base+h['indexed']['entryRva'],indexed=True)
    def compact(v):
        if isinstance(v,dict):return {k:compact(x)for k,x in v.items()if k!='selectedBytes'}
        if isinstance(v,list):return [compact(x)for x in v]
        return v
    return norm(compact(result))


def _calls(g):
    for p in g['constructor']:
        for c in p['calls']:yield {'compatibleClass':'compatible','bundleRetainHandle':'bundle','prefabRetainHandle':'prefab'}[c['role']],c['targetVa']
    for p in g['bundle']:
        for c in p['calls']:yield 'counter'if c['role']=='counter'else'compact',c['targetVa']
    for p in g['prefab']:
        yield 'counter',p['counterCall']['targetVa']
        if p['addCall']:yield 'hashSet',p['addCall']['targetVa']
    for p in g['compatible']:yield 'hierarchy',p['prepareHierarchyCall']['targetVa']
    for p in g['overflow']:yield 'hashSet',p['addCall']['targetVa']
    for c in g['promotion']['calls']:yield {'poolAllocate':'pool','barrier':'barrier','seedAdd':'seed'}[c['role']],c['targetVa']
    yield 'hashSet',g['seed']['addTargetVa']
    for p in g['hashSet']:
        for c in p['calls']:yield {'indexedContext':'indexed','prepareClass':'preparation','keyEquals':'equality'}[c['role']],c['targetVa']
    for p in g['equality']:yield 'preparation',p['preparationTargetVa']


def _sites(g):
    result={}
    def add(key,u,expected):
        s=dict(helper=key,site=u['instructionVa'],cell=u['cellVa'],expected=expected)
        need('one-meaning-per-typed-site',s['site']not in result or same(s,result[s['site']]));result[s['site']]=s
    for v in g['constructor']:
        for u in v['typedUsages']:add('constructor',u,('type',{'firstType':BUNDLE,'secondType':PREFAB,'versionClass':MANAGER}[u['role']]))
    for v in g['bundle']:
        for u in v['typedUsages']:add('bundle',u,('type',{'counterClass':UTILITY,'poolClass':COMPACT,'diagnosticClass':FLAGS}[u['role']]))
    add('counter',g['counter']['classUsage'],('type',UTILITY))
    for v in g['prefab']:
        add('prefab',v['classUsage'],('type',UTILITY))
        if v['addContextUsage']:add('prefab',v['addContextUsage'],('method',HASHSET,'Add',['int'],[]))
    for v in g['overflow']:add('compact',v['addContextUsage'],('method',HASHSET,'Add',['int'],[]))
    for u in g['promotion']['typedUsages']:
        expected=('type',COMPACT)if u['role']=='compactClass'else('method',POOL,'Allocate',[HASHSET+'<int>'],[])if u['role']=='allocate'else('method',HASHSET,'EnsureCapacity',['int'],[])if u['role']=='ensureCapacity'else('method',HASHSET,'Add',['int'],[])
        add('compact',u,expected)
    return result


def _comparer_requirements(g):
    return dict(hashCallbackMarkerVa=g['hashSet'][0]['selectedInt32HashCallbackVa'],
        equalityCallbackMarkerVa=g['equality'][0]['selectedCallbackVa'],inputKeyBytes=4,closedElementType='int',
        hashContextIndex=18,equalitySelector=0,actualCallbackAndMethodInfoPairRequired=True,selectionObserved=False)


def _fields(image,ctx):
    from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets
    md=image.metadata;result={}
    names=[HANDLE,BUNDLE,PREFAB,COMPACT,UTILITY,MANAGER,FLAGS,'Beyond.ELogChannel','Beyond.Resource.EAssetProxyHandleType',
        'Beyond.Resource.FAssetObjectID','Beyond.Resource.FObjectHandle']
    for name in names:
        td=ctx.index.types[name];fields=list(md.fields_for(td));offsets=runtime_type_field_offsets(md,image.pe,image.registration,td.index)
        result[name]=dict(typeDefinition=td.index,valueType=ctx.is_value_type(name),parent=ctx.parent(name),
            fields=[dict(name=md.string(f.name_index),typeName=ctx.type_name(f.type_index),offset=offsets.get(md.string(f.name_index)),
                static=bool(ctx.field_attributes(f.type_index)&16))for f in fields])
    return result


def _method(image,ctx,owner,name,params,slot):
    md=image.metadata;ms=[m for m in md.methods_for(ctx.index.types[owner])if md.string(m.name_index)==name
        and [ctx.type_name(v.type_index)for v in md.parameters_for(m)]==params]
    need('unique-own-named-method:'+owner+'.'+name,len(ms)==1);m,=ms
    need('own-method-slot',m.slot==slot)
    return dict(method=[m.index,owner,name,image.method_pointer_va(m)-image.pe.image_base],parameters=params,slot=m.slot,returnType=ctx.type_name(m.return_type))


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack import leveldata_patrol_resource_handle_sources as parent,leveldata_patrol_class_preparation_sources as preparation
    _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);source=parent.derive(image,pins);h={};targets={}
    def add(role,target,span=None):
        need('one-actual-source-target:'+role,role not in targets or targets[role]==target);targets[role]=target;h[role]=packet(image,target,span);return raw(h[role],base)
    at=source['proof']['programs']['create-handle']['constructorCall']['targetVa'];rr=add('constructor',at)
    for kind in('bundle','prefab'):
        g=paths.constructor(rr,at,kind=kind)
        for c in g['calls']:add({'compatibleClass':'compatible','bundleRetainHandle':'bundle','prefabRetainHandle':'prefab'}[c['role']],c['targetVa'])
    for c in paths.bundle_retain_handle(raw(h['bundle'],base),targets['bundle'])['calls']:add(c['role'],c['targetVa'])
    # Keep role vocabulary separate from any historic GetID discovery label.
    h['compact']=h.pop('compactAdd');targets['compact']=targets.pop('compactAdd')
    g=paths.prefab_retain_handle(raw(h['prefab'],base),targets['prefab'],set_present=True);add('hashSet',g['addCall']['targetVa'])
    g=paths.compatible_class(raw(h['compatible'],base),targets['compatible']);add('hierarchy',g['prepareHierarchyCall']['targetVa'])
    g=paths.compact_promote(raw(h['compact'],base),targets['compact'])
    for c in g['calls']:
        role={'poolAllocate':'pool','barrier':'barrier','seedAdd':'seed'}[c['role']]
        if role=='barrier':continue
        add(role,c['targetVa'])
    barrier=next(c['targetVa']for c in g['calls']if c['role']=='barrier');prefix=image.pe.bytes_at_va(barrier,12)
    walk=BytesPath([(barrier,prefix)],barrier);walk.relative('833d');walk.take('00','4c8bc1');ret=walk.relative('74',1)
    h['barrier']=packet(image,barrier,12);tail=packet(image,ret,1);h['barrier']['regions']+=tail['regions'];h['barrier']['windows']+=tail['windows']
    table=paths.hashset_add(raw(h['hashSet'],base),targets['hashSet'],duplicate=True)
    for c in table['calls']:
        if c['role']=='indexedContext':add('indexed',c['targetVa'],15)
        elif c['role']=='keyEquals':add('equality',c['targetVa'])
    prepare={c['targetVa']for c in table['calls']if c['role']=='prepareClass'};need('one-actual-class-preparation',len(prepare)==1)
    prep=preparation.derive(image,pins,target=next(iter(prepare)))
    walk=BytesPath(raw(h['indexed'],base),targets['indexed']);walk.take('488bc1','4863ca','488b0cc8');add('indexedReady',walk.relative('e9'),20)
    proof=dict(imageBase=base,resourceHandleSource=source,helpers=h,classPreparation=prep,fields=_fields(image,ctx),
        methods=dict(constructor=_method(image,ctx,HANDLE,'.ctor',['Beyond.Resource.IAssetProxy','Beyond.ELogChannel'],65535),
            bundle=_method(image,ctx,BUNDLE,'RetainHandle',[],13),prefab=_method(image,ctx,PREFAB,'RetainHandle',[],17)))
    proof['programs']=_programs(proof);proof['requiredSelectedComparerCallbacks']=_comparer_requirements(proof['programs'])
    proof['typedRequests']={str(at-base):derive_typed_usage_context(image,at-base,label='patrolResourceIds.actualContext')for at in _sites(proof['programs'])}
    value=norm(dict(schema=SCHEMA,status='validated-conditional-patrol-resource-id-sources',nativeInputs=pins,proof=proof,
        selectedConstructorAndRetainHandleEffectsProved=True,selectedCounterAndInt32SetEffectsProved=True,
        selectedInlineToPooledSetPromotionProved=True,outputBytes=20,storageCountRange=[0,4096],
        runtimeInvocationObserved=False,liveHandleOrAssetIdentityObserved=False,counterUniquenessOrAtomicityProved=False,playbackProved=False,
        conditions=['Same nonnull request result reaches the actual FAssetProxyUntrackedHandle constructor in a zeroed20-byte caller local; R8b is the unmodified ELogChannel byte. Padding remains caller-zero. Named object/handle fields and RetainHandle methods are independently joined.',
            'Compatible stable actual source class/discriminator and hierarchy, actual selected Int32 hash/equality callback and MethodInfo contexts, ready classes/metadata, absent replacements, normal Win64 ABI, disjoint valid writable storage and disabled collection.',
            'The global non-atomic counter returns its old Int32 bits and increments modulo2^32. No uniqueness, nonzero result or cross-thread safety is inferred. Optional asset-load/unload diagnostics are disabled on the selected added-ID path.',
            'Compact inline IDs are distinct with count0..4 and unused packed high halves zero, or a valid existing HashSet<int> within4096. Hash storage is stable and acyclic, with positive buckets and available free/spare slots; duplicate paths do not mutate the set.',
            'Inline count4 promotion selects a nonnull spare pooled empty HashSet<int> with existing capacity at least8 and null OnGet action, then seeds the four old and one new pairwise-distinct IDs. Pool creation, capacity allocation/resize, diagnostic logging and cold/exceptional alternatives remain outside these selected normal source effects.',
            'This byte-source proof observes neither the live proxy type/state nor a live counter/set/pool, resource request outcome, successful load, handle lifetime, event dispatch or playback.']))
    validate(value,pins);_publication_gate(image,pins);return value


def validate(value,pins):
    from scripts.game_data.memorypack import leveldata_patrol_resource_handle_sources as parent,leveldata_patrol_class_preparation_sources as preparation
    need('envelope',value.get('schema')==SCHEMA and value.get('status')=='validated-conditional-patrol-resource-id-sources'and value.get('nativeInputs')==pins
        and all(value.get(k)is True for k in('selectedConstructorAndRetainHandleEffectsProved','selectedCounterAndInt32SetEffectsProved','selectedInlineToPooledSetPromotionProved'))
        and all(value.get(k)is False for k in('runtimeInvocationObserved','liveHandleOrAssetIdentityObserved','counterUniquenessOrAtomicityProved','playbackProved'))
        and type(value.get('outputBytes'))is int and value['outputBytes']==20 and same(value.get('storageCountRange'),[0,4096]))
    p=value['proof'];base=p['imageBase'];h=p['helpers'];parent.validate(p['resourceHandleSource'],pins);preparation.validate(p['classPreparation'],pins)
    need('image-base',type(base)is int and base>=1<<32)
    need('finite-helper-family',set(h)=={'constructor','bundle','prefab','compatible','counter','compact','hierarchy','hashSet','seed','pool','barrier','indexed','indexedReady','equality'})
    programs=_programs(p);need('complete-selected-normal-effect-replay',same(programs,p['programs']))
    need('exact-selected-Int32-comparer-conditions',same(p['requiredSelectedComparerCallbacks'],_comparer_requirements(programs)))
    for role,target in _calls(programs):need('exact-actual-child-call:'+role,target==base+(p['classPreparation']['actualEntryRva']if role=='preparation'else h[role]['entryRva']))
    enclosing=p['resourceHandleSource']['proof'];ctor=enclosing['callees']['constructor'];own=h['constructor']
    need('exact-fresh-enclosing-constructor-source',own['entryRva']==ctor['entryRva']==enclosing['programs']['create-handle']['constructorCall']['targetVa']-base
        and same(own['windows'],ctor['sourceWindows'])and same(own['regions'],[[a-base,b.upper()]for a,b in ctor['sourceRegions']]))
    need('zeroed-parent-output-and-full20-copy',enclosing['programs']['create-handle']['constructorArguments']==dict(rcx='zeroed20-byte local RSP88',rdx='same actual request result',r8b=1,r9d=0)
        and enclosing['programs']['create-handle']['constructorOutputCopiedUnchanged']is True)
    for role,owner,name,params,slot,ret in(('constructor',HANDLE,'.ctor',['Beyond.Resource.IAssetProxy','Beyond.ELogChannel'],65535,'void'),
        ('bundle',BUNDLE,'RetainHandle',[],13,'int'),('prefab',PREFAB,'RetainHandle',[],17,'int')):
        m=p['methods'][role];need('exact-own-method-metadata',m['method'][1:3]==[owner,name]and m['method'][3]==h[role]['entryRva']
            and type(m['method'][0])is int and m['parameters']==params and type(m['slot'])is int and m['slot']==slot and m['returnType']==ret)
    sites=_sites(programs);need('all-and-only-actual-source-typed-sites',set(p['typedRequests'])=={str(at-base)for at in sites})
    for at,s in sites.items():
        u=p['typedRequests'][str(at-base)];_usage(h[s['helper']],base,at,s['cell'],u);expected=s['expected']
        if expected[0]=='type':
            need('exact-owned-class-request',u['tag']==1 and u['typeName']==expected[1])
            descriptor=bytes.fromhex(u['typeRawHex']);declaration=p['fields'][expected[1]]
            need('exact-nominal-type-carrier',type(declaration['valueType'])is bool and len(descriptor)==16 and descriptor[10]==(17 if declaration['valueType']else 18)
                and int.from_bytes(descriptor[:8],'little')==declaration['typeDefinition'])
        else:need('exact-closed-method-request',u['tag']==6 and same([u['typeName'],u['methodName'],u['classArguments'],u['methodArguments']],expected[1:]))
    need('source-Int32-set-context-not-width-alias',all(s['expected'][3]==['int']for s in sites.values()if s['expected'][0]=='method'and s['expected'][1]==HASHSET))
    need('single-actual-Int32-Add-definition',len({u['methodSpec'][0]for u in p['typedRequests'].values()if u.get('methodName')=='Add'})==1)
    fields=p['fields'];need('finite-owned-layouts',set(fields)=={HANDLE,BUNDLE,PREFAB,COMPACT,UTILITY,MANAGER,FLAGS,'Beyond.ELogChannel','Beyond.Resource.EAssetProxyHandleType','Beyond.Resource.FAssetObjectID','Beyond.Resource.FObjectHandle'})
    def field(owner,name,typename,offset,static=False):
        matches=[f for f in fields[owner]['fields']if f['name']==name]
        need('own-field:'+owner+'.'+name,len(matches)==1 and matches[0]['typeName']==typename
            and type(matches[0]['offset'])is int and matches[0]['offset']==offset and matches[0]['static']is static)
    for name,t,off in(('m_handleObjectID','int',16),('m_assetProxyID','Beyond.Resource.FAssetObjectID',20),('m_assetProxyObj','Beyond.Resource.FObjectHandle',24),
        ('m_handleType','Beyond.Resource.EAssetProxyHandleType',28),('m_logChannel','Beyond.ELogChannel',29),('m_mainVersion','int',32)):field(HANDLE,name,t,off)
    need('own-untracked-value-layout',fields[HANDLE]['valueType']is True and fields[HANDLE]['parent']=='System.ValueType')
    field(BUNDLE,'m_handlesSet',COMPACT,176);field(PREFAB,'m_handlesSet',HASHSET+'<int>',144)
    for owner,obj,gc in((BUNDLE,156,160),(PREFAB,160,164)):
        field(owner,'<objectID>k__BackingField','Beyond.Resource.FAssetObjectID',obj);field(owner,'<gcHandle>k__BackingField','Beyond.Resource.FObjectHandle',gc)
    for name,t,off in(('m_count','int',16),('m_packed0','long',24),('m_packed1','long',32),('m_set',HASHSET+'<int>',40)):field(COMPACT,name,t,off)
    field(COMPACT,'s_pooledHashSet',POOL+'<'+HASHSET+'<int>>',0,True);field(UTILITY,'s_uniqueCounter','int',0,True)
    field(MANAGER,'<mainResourceVersion>k__BackingField','int',0,True);field(FLAGS,'s_enableAssetLoadAndUnloadLog','bool',18,True)
    field('Beyond.ELogChannel','value__','byte',16);field('Beyond.Resource.EAssetProxyHandleType','value__','byte',16)
    for role,span in(('indexed',15),('indexedReady',20)):
        need('selected-leaf-span:'+role,h[role]['boundary']=='actual-selected-span-no-physical-extent'and len(h[role]['regions'])==1 and len(bytes.fromhex(h[role]['regions'][0][1]))==span)
    need('disabled-barrier-declared-spans',h['barrier']['boundary']=='actual-selected-span-no-physical-extent'and sorted(len(bytes.fromhex(b))for a,b in h['barrier']['regions'])==[1,12])
    for role in set(h)-{'indexed','indexedReady','barrier'}:need('complete-native-owned-family:'+role,h[role]['boundary']=='complete-native-owned-family')
    return dict(selectedConstructorAndRetainHandleEffectsProved=True,selectedCounterAndInt32SetEffectsProved=True,
        selectedInlineToPooledSetPromotionProved=True,counterUniquenessOrAtomicityProved=False,runtimeInvocationObserved=False,playbackProved=False)


def _usage(own,base,at,cell,u):
    cells={a+i:b for a,bb in raw(own,base)for i,b in enumerate(bb)};encoded=bytes(cells[at+i]for i in range(7))
    need('exact-owned-typed-site',u['instructionRva']==at-base and u['usageCellRva']==cell-base and encoded.hex().upper()==u['instructionHex'].upper()
        and encoded[:3]in(bytes.fromhex('488b05'),bytes.fromhex('488b0d'),bytes.fromhex('488b15'),bytes.fromhex('488b2d'),bytes.fromhex('488b3d'),bytes.fromhex('4c8b05'))
        and at+7+int.from_bytes(encoded[3:],'little',signed=True)==cell)
    word=int.from_bytes(bytes.fromhex(u['usageRawHex']),'little');need('actual-uninitialized-usage-cell',type(u['tag'])is int and word&1==1 and word>>29==u['tag'])
    if u['tag']==6:need('actual-owned-MethodSpec-index',u['methodSpecIndex']==(word&((1<<29)-1))>>1 and len(u['methodSpec'])==3)
    else:need('actual-owned-type-index',u['tag']==1 and u['typeIndex']==(word&((1<<29)-1))>>1)
