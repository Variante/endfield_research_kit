"""Offline selected resource-handle validity and proxy-storage source effects.

All tables, callback markers, class flags/discriminators and replacement absence
are explicit incoming-state conditions. Native bytes and actual typed sites are
freshly authenticated; no game call, live asset or successful load is observed.
"""
import hashlib,json
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack import leveldata_patrol_proxy_storage_programs as storage
from scripts.game_data.memorypack import leveldata_patrol_resource_validity_programs as paths

SCHEMA='endfield.story-patrol-resource-validity-sources.v1'
OBJECT='Beyond.Resource.ObjectHandle'
OBJECT_VALUE='Beyond.Resource.FObjectHandle'
PROXY='Beyond.Resource.FAssetProxyHandle'
UNTRACKED='Beyond.Resource.FAssetProxyUntrackedHandle'
LOADER='Beyond.Resource.FAssetProxyLoaderHandle'
ASSET='Beyond.Resource.FAssetObjectID'
INTERFACE='Beyond.Resource.IAssetProxy'
INLINE_SET='Beyond.Resource.Runtime.CompactIntSet'


def need(check,condition):
    if not condition:raise ValueError('patrolResourceValiditySources.'+check)


def norm(value):return json.loads(json.dumps(value))


def same(left,right):return json.dumps(left,sort_keys=True,separators=(',',':'))==json.dumps(right,sort_keys=True,separators=(',',':'))


def packet(image,at,*,span=None):
    from scripts.game_data.memorypack.pointer_param import owned
    base=image.pe.image_base
    if span is None:
        b=owned(image,at)
        return dict(entryRva=at-base,windows=b['windows'],regions=[[a-base,h.hex().upper()]for a,h in b['regions']],boundary='complete-native-owned-family')
    raw=image.pe.bytes_at_va(at,span)
    return dict(entryRva=at-base,windows=[dict(startRva=at-base,endRva=at-base+span,sha256=hashlib.sha256(raw).hexdigest().upper())],
        regions=[[at-base,raw.hex().upper()]],boundary='actual-selected-span-no-physical-extent')


def raw(own,base):
    from scripts.game_data.memorypack.animation_custom_dictionary_callbacks import regions
    need('owned-entry',type(own.get('entryRva'))is int and own['entryRva']>0)
    result=regions(own['windows'],own['regions'],base,'patrolResourceValidity')
    need('entry-in-declared-regions',any(a<=base+own['entryRva']<a+len(h)for a,h in result))
    return result


def _parent_packet(child,base):
    return dict(entryRva=child['entryRva'],windows=child['sourceWindows'],regions=[[a-base,h]for a,h in child['sourceRegions']],boundary='complete-native-owned-family')


def _selected_programs(p):
    from scripts.game_data.memorypack.int_list_sources import initialized_class
    h=p['helpers'];base=p['imageBase'];rr={k:raw(v,base)for k,v in h.items()}
    def selected(key,prover,**kw):return prover(rr[key],base+h[key]['entryRva'],**kw)
    def cursor(key,prover,**kw):return prover(BytesPath(rr[key],base+h[key]['entryRva']),**kw)
    result=dict(validity={k:[selected(k,paths.validity_program,kind=k,outcome=o,object_kind=c)
        for c in('direct','wrapper')for o in('zero-id','lookup-miss','membership-miss','asset-id-zero','object-id-mismatch','disposed','valid')]
        for k in('created','output')},
        objectGet=[selected('objectGet',paths.object_getter_program,hit=hit,misses=misses)for hit,misses in((True,()),(False,()),(True,(False,True)),(False,(True,False)))],
        proxyGet=[selected('proxyGet',paths.proxy_getter_program,hit=hit,misses=misses)for hit,misses in((True,()),(False,()),(True,(False,True)),(False,(True,False)))],
        containsInline=[cursor('containsId',storage.inline_ids_program,count=c,match=m)for c in range(5)for m in range(c+1)],
        containsSet=[cursor('containsId',storage.set_ids_program,kind=k,set_present=present)for k,present in(('direct',True),('wrapper',True),('wrapper',False))],
        disposed=[cursor('disposed',storage.disposed_program,kind=k,state_disposed=s,replacement_present=r,wrapper_mode=m)
            for r in(False,True)for k,s,m in(('direct',False,'null'),('direct',True,'null'),('wrapper',False,'null'),('wrapper',False,'child-disposed'),('wrapper',False,'child-ready'))],
        compatible=[cursor('compatibleInterface',storage.compatible_interface_program,interface_steps=i)for i in range(4)],
        keyEquals=[cursor('keyEquals',storage.key_equality_program,interface_steps=i)for i in range(4)],
        ready={role:cursor('prepare'+role.title(),storage.ready_program,role=role)for role in('type','offsets','interfaces')},
        hashSet=[cursor('hashSetBody',storage.hashset_program,**args)for args in(
            dict(empty_buckets=True),dict(empty_bucket=True),*[dict(misses=misses,hit=hit,interface_steps=i)
                for misses,hit in(((),True),((False,),False),((True,),False),((False,True),True),((True,False,True),False))for i in range(4)])])
    indexed=rr['indexedContext']+rr['indexedReady'];result['indexedContext']=initialized_class(indexed,base+h['indexedContext']['entryRva'],indexed=True)
    g=BytesPath(rr['hashSetThunk'],base+h['hashSetThunk']['entryRva']);target=g.relative('e9')
    need('own-hashset-thunk-target',target==base+h['hashSetBody']['entryRva'])
    result['hashSetThunk']=dict(selectedBytes=g.seen,tailTargetVa=target,physicalThunkExtentProved=False)
    # The same exact table algorithm is replayed at the actual cursor inside
    # all four distinct enclosing caller bodies, including collision witnesses.
    result['tables']={}
    for key,profile,output,context in(('created','validity',144,152),('output','validity',152,48),('objectGet','object-get',152,None),('proxyGet','asset-get',152,None)):
        main=result['validity'][key][-1]if key in('created','output')else result[key][0]
        entry=main['table']['selectedBytes'][0][0]
        result['tables'][key]=[storage.proxy_table_program(BytesPath(rr[key],entry),output_home=output,context_home=context,profile=profile,
            hit=hit,misses=misses,interface_steps=i)for hit,misses in((True,()),(False,()),(True,(False,True)),(False,(True,False)))for i in range(4)]
    return norm(result)


def _all_calls(programs):
    for k in('created','output'):
        for g in programs['validity'][k]:
            for c in g['calls']:yield k,c
    for k in('objectGet','proxyGet'):
        for g in programs[k]:
            for c in g.get('calls',[]):yield k,c
    for k,programs_ in programs['tables'].items():
        for g in programs_:
            for c in g['calls']:yield k,c
    for k in('hashSet','compatible'):
        for g in programs[k]:
            for c in g['calls']:yield 'hashSetBody'if k=='hashSet'else'compatibleInterface',c
    for g in programs['keyEquals']:
        yield 'keyEquals',dict(role='prepareClass',targetVa=g['preparationTargetVa'])


def _usage_sites(programs):
    result={}
    def add(owner,u,tag,name,method=None,args=None):
        at=u['instructionVa'];value=dict(owner=owner,cellVa=u['cellVa'],tag=tag,typeName=name,methodName=method,classArguments=args)
        need('one-literal-usage-role',at not in result or result[at]==value);result[at]=value
    for k,entries in programs['tables'].items():
        for g in entries:
            for u in g['classUsages']:
                if u['role']=='storageClass':add(k,u,1,OBJECT)
                else:add(k,u,6,'System.Collections.Concurrent.ConcurrentDictionary`2','TryGetValue',['int','object'])
    for k in('created','output'):
        for g in programs['validity'][k]:
            for u in g['classUsages']:add(k,u,1,INTERFACE if u['role']=='proxyInterface'else ASSET)
    for g in programs['proxyGet']:
        for u in g['classUsages']:add('proxyGet',u,1,INTERFACE)
    for g in programs['containsInline']:
        add('containsId',dict(instructionVa=g['classUsageInstructionVa'],cellVa=g['classCellVa']),1,INLINE_SET)
    for g in programs['containsSet']:
        if g['classUsage']:add('containsId',g['classUsage'],1,INLINE_SET)
        if g['hashSetUsage']:add('containsId',g['hashSetUsage'],6,'System.Collections.Generic.HashSet`1','Contains',['int'])
    return result


def _verify_joins(p,programs):
    base=p['imageBase'];h=p['helpers'];source=p['resourceSource']
    expected={'created','output','objectGet','proxyGet','containsId','disposed','compatibleInterface','keyEquals',
        'indexedContext','indexedReady','prepareType','prepareOffsets','prepareInterfaces','hashSetThunk','hashSetBody'}
    need('finite-helper-roles',set(h)==expected)
    for caller,c in _all_calls(programs):
        role=c['role'];key='indexedContext'if role=='indexedContext'else role
        if role=='prepareClass':
            need('same-own-class-preparation-entry',c['targetVa']==base+p['classPreparation']['actualEntryRva'])
        else:need('actual-call-target:'+caller+':'+role,key in h and c['targetVa']==base+h[key]['entryRva'])
    for key,role in(('created','created-handle-valid'),('output','output-handle-valid')):
        need('parent-validity-full-source-identity:'+key,_parent_packet(source['proof']['children'][role],base)==h[key])
    for g in programs['containsSet']:
        if g['tailTargetVa']is not None:need('contains-exact-hashset-tail',g['tailTargetVa']==base+h['hashSetThunk']['entryRva'])
    expected_sites=_usage_sites(programs);need('all-and-only-actual-typed-sites',set(p['typedRequests'])=={str(at-base)for at in expected_sites})
    for at,site in expected_sites.items():
        u=p['typedRequests'][str(at-base)];rr=raw(h[site['owner']],base);cells={a+i:b for a,s in rr for i,b in enumerate(s)}
        try:encoded=bytes(cells[at+i]for i in range(7))
        except KeyError as e:raise ValueError('patrolResourceValiditySources.unowned-context-site')from e
        need('complete-literal-context-load',u['instructionRva']==at-base and u['usageCellRva']==site['cellVa']-base
            and encoded.hex().upper()==u['instructionHex'].upper()and encoded[:3]in tuple(bytes.fromhex(x)for x in('488b05','488b0d','488b1d','4c8b05','4c8b25'))
            and at+7+int.from_bytes(encoded[3:],'little',signed=True)==site['cellVa'])
        need('own-context-nominal:'+str(at-base)+':expected='+str([site['tag'],site['typeName']])+':actual='+str([u.get('tag'),u.get('typeName')]),type(u['tag'])is int and u['tag']==site['tag']and u['typeName']==site['typeName'])
        encoded_usage=int.from_bytes(bytes.fromhex(u['usageRawHex']),'little')
        need('exact-uninitialized-typed-usage-carrier',encoded_usage&1==1 and encoded_usage>>29==site['tag'])
        index=(encoded_usage&((1<<29)-1))>>1
        if site['tag']==6:
            need('own-closed-method-context',u['methodName']==site['methodName']and u['classArguments']==site['classArguments']and u['methodArguments']==[]
                and type(u['methodSpecIndex'])is int and u['methodSpecIndex']==index
                and len(u['methodSpec'])==3 and all(type(x)is int for x in u['methodSpec']))
        else:
            t=bytes.fromhex(u['typeRawHex']);expected_kind=18 if site['typeName']in(OBJECT,INTERFACE)else 17
            need('exact-owned-class-or-value-type-descriptor',type(u['typeIndex'])is int and u['typeIndex']==index
                and len(t)==16 and t[10]==expected_kind and int.from_bytes(t[:8],'little')==p['fields'][site['typeName']]['typeDefinition'])
    need('literal-proxy-class-predicates-agree',len({g['requiredClassDiscriminator']for g in programs['containsSet']if g['kind']=='direct'}
        |{g['requiredClassDiscriminator']for g in programs['disposed']if g['kind']=='direct'}
        |{g['requiredProxyClassDiscriminator']for k in('created','output')for g in programs['validity'][k]
            if g['requiredProxyClassDiscriminator']is not None and g['selectedProxyObjectIdOffset']==156})==1)
    # The adjacent ready-class branch is explicitly a selected span, not an
    # invented physical function boundary for a no-unwind helper.
    for key in set(h)-{'indexedContext','indexedReady','hashSetThunk'}:need('complete-owned-helper-family:'+key,h[key]['boundary']=='complete-native-owned-family')
    for key,size in(('indexedContext',15),('indexedReady',20),('hashSetThunk',5)):
        need('declared-bounded-helper-span:'+key,len(h[key]['windows'])==len(h[key]['regions'])==1
            and len(bytes.fromhex(h[key]['regions'][0][1]))==size and h[key]['boundary']=='actual-selected-span-no-physical-extent')
    need('indexed-context-actual-tail',base+h['indexedReady']['entryRva']==base+h['indexedContext']['entryRva']+15
        +int.from_bytes(bytes.fromhex(h['indexedContext']['regions'][0][1])[-4:],'little',signed=True))


def _fields(image):
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets
    ctx=NativeReferenceContext(image);md=image.metadata;result={}
    for name in(OBJECT,PROXY,LOADER,ASSET,INTERFACE,UNTRACKED,OBJECT_VALUE,INLINE_SET):
        td=ctx.index.types[name];declared=list(md.fields_for(td))
        offsets=runtime_type_field_offsets(md,image.pe,image.registration,td.index)if declared else{}
        result[name]=dict(typeDefinition=td.index,parent=ctx.parent(name),fields=[dict(name=md.string(f.name_index),
            typeName=ctx.type_name(f.type_index),offset=offsets.get(md.string(f.name_index)),static=bool(ctx.field_attributes(f.type_index)&16))for f in declared])
    return result


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack import leveldata_patrol_resource_sources as parent,leveldata_patrol_class_preparation_sources as preparation
    _publication_gate(image,pins);base=image.pe.image_base;source=parent.derive(image,pins)
    h={k:_parent_packet(source['proof']['children'][role],base)for k,role in(('created','created-handle-valid'),('output','output-handle-valid'))}
    targets={};prepare=None
    for key in('created','output'):
        g=paths.validity_program(raw(h[key],base),base+h[key]['entryRva'],kind=key)
        for c in g['calls']:
            need('same-actual-shared-validity-child',c['role']not in targets or targets[c['role']]==c['targetVa']);targets[c['role']]=c['targetVa']
        for c in g['table']['calls']:
            if c['role']=='prepareClass':prepare=c['targetVa']
            else:targets[c['role']]=c['targetVa']
    for key,at in targets.items():h[key]=packet(image,at,span=15 if key=='indexedContext'else None)
    need('actual-class-preparation-child',prepare is not None);class_prepare=preparation.derive(image,pins,target=prepare)
    indexed=bytes.fromhex(h['indexedContext']['regions'][0][1]);need('literal-indexed-context-tail',indexed[:11]==bytes.fromhex('488bc14863ca488b0cc8e9'))
    ready=targets['indexedContext']+15+int.from_bytes(indexed[-4:],'little',signed=True);h['indexedReady']=packet(image,ready,span=20)
    compatible=storage.compatible_interface_program(BytesPath(raw(h['compatibleInterface'],base),targets['compatibleInterface']))
    for c in compatible['calls']:
        role=c['role'];need('same-preparation-role',role not in targets or targets[role]==c['targetVa']);targets[role]=c['targetVa']
    for k in('prepareType','prepareOffsets','prepareInterfaces'):h[k]=packet(image,targets[k])
    selected=storage.set_ids_program(BytesPath(raw(h['containsId'],base),targets['containsId']),kind='direct')
    thunk=selected['tailTargetVa'];h['hashSetThunk']=packet(image,thunk,span=5)
    encoded=bytes.fromhex(h['hashSetThunk']['regions'][0][1]);need('literal-hashset-tail-thunk',encoded[:1]==b'\xe9')
    actual=thunk+5+int.from_bytes(encoded[1:],'little',signed=True);h['hashSetBody']=packet(image,actual)
    proof=dict(imageBase=base,resourceSource=source,helpers=h,classPreparation=class_prepare,fields=_fields(image))
    programs=_selected_programs(proof);proof['programs']=programs
    proof['typedRequests']={str(at-base):derive_typed_usage_context(image,at-base,label='patrolResourceValidity.actualContext')for at in _usage_sites(programs)}
    value=norm(dict(schema=SCHEMA,status='validated-conditional-resource-validity-normal-sources',nativeInputs=pins,proof=proof,
        selectedValidityCallersProved=True,selectedProxyTableAndGetterEffectsProved=True,selectedMembershipAndDisposalEffectsProved=True,
        selectedNormalPreparationEffectsProved=True,wholeResourceLoadProved=False,runtimeInvocationObserved=False,
        liveHandleOrAssetStateObserved=False,playbackProved=False,
        conditions=['Exact metadata/context pointers and selected callback/MethodInfo pairs are coherent and ready. Replacements are absent; selected interface compatibility and literal class-discriminator predicates hold.',
            'Valid disjoint stable handle, proxy, table, comparer, bucket, slot and frame storage. The collector is disabled for reference output. Repeated table and proxy reads select the same stable values.',
            'ConcurrentDictionary chains are acyclic and within the selected finite source budget; HashSet uses its own actual index and visited-count guards. No collection content or live class/state is observed.',
            'Wrapper disposal recursion selects a finite acyclic chain within32. Cold initialization, replacements, incompatible interfaces and invalid/cyclic storage are outside this selected normal grant.'],
        residualNativeSourceFrontiers=['Cold preparation, exceptional paths, dynamic replacements and other literal class-discriminator branches.',
            'Runtime asset selection, storage races/lifetime, successful loading, controller activation and playback remain unobserved.']))
    validate(value,pins);_publication_gate(image,pins);return value


def validate(value,pins):
    from scripts.game_data.memorypack import leveldata_patrol_resource_sources as parent,leveldata_patrol_class_preparation_sources as preparation
    need('source-envelope',value.get('schema')==SCHEMA and value.get('nativeInputs')==pins
        and value.get('status')=='validated-conditional-resource-validity-normal-sources'
        and all(value.get(k)is True for k in('selectedValidityCallersProved','selectedProxyTableAndGetterEffectsProved',
            'selectedMembershipAndDisposalEffectsProved','selectedNormalPreparationEffectsProved'))
        and all(value.get(k)is False for k in('wholeResourceLoadProved','runtimeInvocationObserved','liveHandleOrAssetStateObserved','playbackProved')))
    p=value['proof'];base=p['imageBase'];need('image-base',type(base)is int and base>=1<<32)
    source=p['resourceSource'];need('own-resource-parent',source['schema']==parent.SCHEMA and source['nativeInputs']==pins
        and source['selectedNormalResourceArgumentsHandleCopiesAndFramesProved']is True)
    sp=source['proof'];parent_raw=raw(dict(entryRva=sp['programs'][0]['entry']-base,windows=sp['sourceWindows'],
        regions=[[a-base,h]for a,h in sp['sourceRegions']]),base)
    parent_programs=norm([parent.program(parent_raw,sp['programs'][0]['entry'],available=a,requested=r,created_valid=v)
        for a,r,v in((False,False,False),(True,False,False),(True,True,False),(True,True,True))])
    need('own-resource-parent-programs',same(parent_programs,sp['programs']))
    for g in parent_programs:
        for c in g['calls']:
            role=c['role']
            if role in('created-handle-valid','output-handle-valid'):need('actual-resource-parent-E8',c['targetVa']==base+sp['children'][role]['entryRva'])
    preparation.validate(p['classPreparation'],pins)
    programs=_selected_programs(p);need('complete-pure-program-equality',same(programs,p['programs']));_verify_joins(p,programs)
    fields=p['fields'];need('finite-owned-metadata-types',set(fields)=={OBJECT,PROXY,LOADER,ASSET,INTERFACE,UNTRACKED,OBJECT_VALUE,INLINE_SET})
    need('exact-metadata-record-scalars',all(type(td['typeDefinition'])is int and td['typeDefinition']>=0 and all(type(f['static'])is bool and (f['offset']is None or type(f['offset'])is int)for f in td['fields'])for td in fields.values()))
    def field(owner,name):
        matches=[f for f in fields[owner]['fields']if f['name']==name];need('one-owned-field:'+name,len(matches)==1);return matches[0]
    need('actual-ObjectHandle-static-storage',field(OBJECT,'s_handleToObject')==dict(name='s_handleToObject',
        typeName='System.Collections.Concurrent.ConcurrentDictionary`2<int,object>',offset=0,static=True))
    need('actual-loader-proxy-field',field(LOADER,'m_proxyHandle')==dict(name='m_proxyHandle',typeName=PROXY,offset=16,static=False))
    need('actual-asset-ID-field',field(ASSET,'<objectIntID>k__BackingField')==dict(name='<objectIntID>k__BackingField',typeName='int',offset=16,static=False))
    need('actual-proxy-untracked-field',field(PROXY,'m_untrackedHandle')==dict(name='m_untrackedHandle',typeName=UNTRACKED,offset=16,static=False))
    for name,typename,offset in(('m_handleObjectID','int',16),('m_assetProxyID',ASSET,20),('m_assetProxyObj',OBJECT_VALUE,24)):
        need('actual-untracked-ID-fields:'+name,field(UNTRACKED,name)==dict(name=name,typeName=typename,offset=offset,static=False))
    own_id=[f for f in fields[OBJECT_VALUE]['fields']if not f['static']]
    need('actual-object-handle-ID-value-layout',len(own_id)==1 and own_id[0]['typeName']=='int'and own_id[0]['offset']==16)
    need('actual-value-handle-nominals',all(fields[k]['parent']=='System.ValueType'for k in(PROXY,LOADER,ASSET,UNTRACKED,OBJECT_VALUE)))
    return dict(selectedValidityCallersProved=True,selectedProxyTableAndGetterEffectsProved=True,
        selectedMembershipAndDisposalEffectsProved=True,selectedNormalPreparationEffectsProved=True,
        wholeResourceLoadProved=False,runtimeInvocationObserved=False,liveHandleOrAssetStateObserved=False,playbackProved=False)
