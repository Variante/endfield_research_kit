"""Finite pooled LevelWide syntax; only an owning native graph supplies caps."""
from scripts.game_data.memorypack import leveldata_levelwide_records as records
from scripts.game_data.memorypack.leveldata_levelwide_union_sources import TYPE as VALUE_TYPE,CHILDREN
from scripts.game_data.codecs.leveldata import current_lang_key
from scripts.game_data.memorypack import leveldata_levelwide_condition as condition_scope

KEY='Beyond.Gameplay.LevelWideConfig+LevelWideConfigType'
INNER='System.Collections.Generic.Dictionary`2<string,'+VALUE_TYPE+'>'
TYPE='System.Collections.Generic.Dictionary`2<'+KEY+','+INNER+'>'
CAP='story-levelwide-configs'
LIMIT=4096
NODE_LIMIT=16384
WRAPPERS={
    records.DOCK:'Beyond.MemoryPack.Beyond_Gameplay_BambooRaftDockInfoForMemoryPack',
    records.DOCK_CONFIG:'Beyond.MemoryPack.Beyond_Gameplay_BambooRaftDockWideConfigForMemoryPack',
    records.RAFT_CONFIG:'Beyond.MemoryPack.Beyond_Gameplay_BambooRaftWideConfigForMemoryPack',
}


def need(check,condition):
    if not condition:raise ValueError('currentLevelWide.'+check)


def validate(cap):
    need('complete-conditional-graph',type(cap)is dict and (cap.get('typeName'),cap.get('capability'))==(TYPE,CAP)
        and type(cap.get('countLimit'))is int and cap['countLimit']==LIMIT
        and type(cap.get('nodeLimit'))is int and cap['nodeLimit']==NODE_LIMIT
        and all(cap.get(k)is True for k in ('profileAdmitted','externalStringPoolRequired',
            'actualCallbackEqualsCanonicalRequired','coherentOriginalContextsRequired','initiallyNullDictionariesRequired'))
        and cap.get('wholeOwnerAdmitted')is False and cap.get('runtimeFormatterSelectionObserved')is False)
    enum=cap.get('enumCallback',{})
    need('own-nominal-enum-callback',enum.get('typeName')==KEY and enum.get('status')=='validated-conditional-callback'
        and type(enum.get('wireBytes'))is int and enum['wireBytes']==4 and enum.get('callbackSlot')==5
        and enum.get('formatterType')=='MemoryPack.Formatters.UnmanagedFormatter`1'
        and type(enum.get('typeDefinition'))is int and enum['typeDefinition']>=0
        and all(enum.get(k)is True for k in ('readerByref','outputByref'))
        and enum.get('actualRuntimeSelectionObserved')is False)
    maps=cap.get('dictionaries',{})
    need('exact-two-dictionary-domains',type(maps)is dict and set(maps)=={'outer','inner'})
    for role,name,key,value,witness in (('outer',TYPE,KEY,INNER,['System.Int32Enum','object']),
            ('inner',INNER,'string',VALUE_TYPE,['object','object'])):
        row=maps[role]
        need('exact-'+role+'-dictionary',type(row)is dict and (row.get('typeName'),row.get('keyType'),row.get('valueType'))==(name,key,value)
            and row.get('sourceWitnessClassArguments')==witness and type(row.get('headerBytes'))is int and row['headerBytes']==4
            and type(row.get('countLimit'))is int and row['countLimit']==LIMIT and row.get('outputBytes')==8
            and all(row.get(k)is True for k in ('positiveCountsAdmitted','keyGrammarAdmitted','valueGrammarAdmitted',
                'actualCallbackEqualsSourceWitnessRequired','typedConstructorAndHelperCompatibilityRequired','initiallyNullOutputRequired'))
            and row.get('closedPointerEquivalenceProved')is False and row.get('runtimeFormatterSelectionObserved')is False)
    need('inner-pooled-key-callback',maps['inner'].get('keyEncoding')=='int32-pool-index'
        and maps['inner'].get('actualKeyCallbackEqualsPooledStringRequired')is True)
    union=cap.get('union',{});routes=union.get('routes',{})
    need('exact-two-route-union',union.get('typeName')==VALUE_TYPE and union.get('admittedRouteTags')==[0,1]
        and type(routes)is dict and set(routes)=={'0','1'}and all(union.get(k)is True for k in (
            'canonicalFFAdmitted','shortTagsOnly','ordinaryAdapterAdmitted','inheritedConversionsProved'))
        and union.get('runtimeFormatterSelectionObserved')is False)
    actual_records=cap.get('records',{})
    need('exact-three-records',type(actual_records)is dict and set(actual_records)==set(records.PLANS))
    ordinary=cap.get('ordinaryRecords',{})
    need('exact-three-ordinary-records',type(ordinary)is dict and set(ordinary)==set(records.PLANS))
    for name,plan in records.PLANS.items():
        row=actual_records[name]
        need('exact-record-profile:'+name,type(row)is dict and row.get('typeName')==name
            and type(row.get('memberCount'))is int and row['memberCount']==len(plan)
            and all(row.get(k)is True for k in ('nullAdmitted','positiveAdmitted','profileAdmitted',
                'ordinaryAdapterAdmitted','actualCallbackEqualsProvedChildRequired'))
            and row.get('wholeGrammarAdmitted')is False and row.get('liveFormatterSelectionObserved')is False
            and type(row.get('referenceReaderMethodDefinition'))is int and row['referenceReaderMethodDefinition']>=0
            and type(row.get('referenceReaderTargetRva'))is int and row['referenceReaderTargetRva']>0)
        entry=ordinary[name]
        need('exact-nominal-ordinary-record:'+name,type(entry)is dict and entry.get('typeName')==name
            and entry.get('wrapperName')==WRAPPERS[name]and entry.get('ordinaryAdapterAdmitted')is True)
        records.bind_program(name,dict(wrappedType=name,orderedSourceReads=[dict(fieldName=n,declaredType=t)for n,t,k in plan]),row.get('program'),[])
    for tag,name in CHILDREN.items():
        row=routes[str(tag)]
        need('same-nominal-union-record',row.get('tag')==tag and type(row.get('tag'))is int and row.get('typeName')==name
            and row.get('wrapperName')==ordinary[name]['wrapperName']
            and row.get('actualWrapperCallbackEqualsProvedConcreteRequired')is True)
    listing=cap.get('dockList',{})
    records.bind_collection({},dict(fieldName='bambooRaftDockInfo',typeName=records.LIST,
        sourceTargetRva=listing.get('packableReaderTargetRva'),typedRequest=dict(methodName='ReadPackable',
            methodArguments=[records.LIST],methodSpec=[listing.get('packableReaderMethodDefinition')])),
        dict(nativeInputs={},capabilities={records.LIST_CAP:listing}),records.LIST_CAP)
    current_lang_key.validate(cap.get('langKey',{}));condition_scope.validate(cap.get('condition',{}))
    from scripts.game_data.memorypack import leveldata_condition_components as condition_source
    for name,row in actual_records.items():
        for binding in row['program']['childBindings']:
            declared=binding['typeName'];join=dict(fieldName=binding['fieldName'],typeName=declared,
                sourceTargetRva=binding.get('sourceTargetRva'),typedRequest=dict(tag=6,typeName='MemoryPack.MemoryPackReader',
                    methodName='ReadPackable'if declared==records.LIST else'ReadValue',classArguments=[],
                    methodArguments=[declared],methodSpec=[binding.get('readerMethodDefinition'),-1,0]))
            if declared==records.LIST:
                expected=records.bind_collection({},join,dict(nativeInputs={},capabilities={records.LIST_CAP:listing}),records.LIST_CAP)
            elif declared==records.CONDITION:
                expected=condition_scope.bind_reference({},join,dict(nativeInputs={},capabilities={condition_source.CAP:cap['condition']}),condition_source.CAP)
            elif declared==records.LANG:
                language=cap['langKey']
                expected=dict(fieldName='dockName',typeName=records.LANG,capability='story-lang-key',
                    readerMethodDefinition=language['readerMethodDefinition'],sourceTargetRva=language['sourceTargetRva'],
                    managedBytes=16,referenceLaneOffsets=[0,8],wireMemberCount=1,positiveWireBytes=5,nullWireBytes=1,
                    nonserializedRawText=True,actualCallbackEqualsProvedChildRequired=True,completeFieldTransferAndFrameProved=True)
            else:raise ValueError('currentLevelWide.unproved-record-child-binding')
            need('same-exact-record-child-binding:'+name+':'+binding['fieldName'],binding==expected)
    parent=cap.get('parentBinding',{})
    need('actual-host-parent',parent.get('ownerType')=='Beyond.Gameplay.LevelData'and parent.get('fieldName')=='levelWideConfigs'
        and parent.get('typeName')==TYPE and parent.get('capability')==CAP
        and type(parent.get('readerMethodDefinition'))is int and parent['readerMethodDefinition']>=0
        and type(parent.get('sourceTargetRva'))is int and parent['sourceTargetRva']>0
        and parent.get('actualCallbackEqualsCanonicalRequired')is True)


def _node(budget,field):
    need('node-budget:'+field,budget[0]>0);budget[0]-=1


def _condition(reader,field,cap):
    return condition_scope.read(reader,field,cap['condition'])


def _record(reader,field,name,cap,budget):
    _node(budget,field);start=reader.offset;marker=reader.number('<B',field+'.memberCount');plan=records.PLANS[name]
    if marker==255:return None
    need('record-member-count:'+field,marker==len(plan));out=dict(startOffset=start,recordType=name,memberCount=marker);ranges={}
    for member,declared,kind in plan:
        at=reader.offset;path=field+'.'+member
        if kind=='byte-payload':value=reader.string(path)
        elif kind=='scalar64-bits':value=str(reader.number('<Q',path))
        elif kind=='scalar32':value=reader.number('<i',path)
        elif kind=='lang-key':value=current_lang_key.read(reader,path,cap['langKey'])
        elif kind=='condition-runtime':value=_condition(reader,path,cap)
        elif kind=='levelwide-dock-list':
            list_start=reader.offset;count=reader.number('<i',path+'.count')
            need('dock-list-count:'+path,-1<=count<=LIMIT and max(count,0)<=budget[0]);reader.need(max(count,0),path+'.elements')
            rows=[_record(reader,path+'['+str(i)+']',records.DOCK,cap,budget)for i in range(max(count,0))]
            value=dict(startOffset=list_start,endOffset=reader.offset,count=count,rows=None if count==-1 else rows)
        else:raise ValueError('currentLevelWide.unowned-record-operation:'+kind)
        out[member]=value;ranges[member]=[at,reader.offset]
    out.update(endOffset=reader.offset,fieldRanges=ranges);return out


def _union(reader,field,cap,budget):
    _node(budget,field);start=reader.offset;tag=reader.number('<B',field+'.unionTag')
    if tag==255:return None
    need('short-owned-union-tag:'+field,tag in CHILDREN)
    value=_record(reader,field+'.value',CHILDREN[tag],cap,budget)
    return dict(startOffset=start,endOffset=reader.offset,tag=tag,recordType=CHILDREN[tag],value=value)


def _dictionary(reader,field,cap,budget,*,outer):
    _node(budget,field);start=reader.offset;count=reader.number('<i',field+'.count')
    need('dictionary-count:'+field,-1<=count<=LIMIT and max(count,0)<=budget[0])
    reader.need(max(count,0)*(8 if outer else 5),field+'.entries');rows=[];seen=set()
    for i in range(max(count,0)):
        _node(budget,field);path=field+'['+str(i)+']';at=reader.offset
        key=reader.number('<i',path+'.key')if outer else reader.string(path+'.key')
        need('nonnull-distinct-stored-key:'+path,key is not None and key not in seen);seen.add(key)
        value=_dictionary(reader,path+'.value',cap,budget,outer=False)if outer else _union(reader,path+'.value',cap,budget)
        rows.append(dict(startOffset=at,endOffset=reader.offset,keyRaw=key if outer else None,key=None if outer else key,value=value))
    return dict(startOffset=start,endOffset=reader.offset,count=count,rows=None if count==-1 else rows)


def read(reader,field,cap):
    # Every domain and actual parent is required even for a null root count.
    validate(cap);need('explicit-external-string-pool',getattr(reader,'strings',None)is not None)
    state=getattr(reader,'_current_levelwide_budget',None)
    if state is None:state=(cap,[NODE_LIMIT]);reader._current_levelwide_budget=state
    else:need('same-levelwide-budget-capability',state[0]is cap)
    return _dictionary(reader,field,cap,state[1],outer=True)


def conditional_sources(cap):
    validate(cap)
    rows=[dict(typeName=cap['typeName'],actualCallbackEqualsCanonicalRequired=True,
        coherentOriginalContextsRequired=True,initiallyNullDictionariesRequired=True,
        runtimeFormatterSelectionObserved=False,runtimeGameplayBehaviorProved=False)]
    for role in ('outer','inner'):
        item=cap['dictionaries'][role]
        row=dict(typeName=item['typeName'],dictionaryRole=role,
            sourceWitnessClassArguments=list(item['sourceWitnessClassArguments']),
            actualCallbackEqualsSourceWitnessRequired=True,typedConstructorAndHelperCompatibilityRequired=True,
            initiallyNullOutputRequired=True,closedPointerEquivalenceProved=False,runtimeFormatterSelectionObserved=False)
        if role=='inner':row['actualKeyCallbackEqualsPooledStringRequired']=True
        rows.append(row)
    rows.append(dict(typeName=cap['dockList']['typeName'],initiallyNullListRequired=True,
        actualCallbackEqualsProvedChildRequired=True,runtimeFormatterSelectionObserved=False))
    rows.append(dict(typeName=cap['condition']['typeName'],admittedRouteTags=list(cap['condition']['admittedRouteTags']),
        actualCallbackEqualsProvedChildRequired=True,runtimeFormatterSelectionObserved=False))
    return rows
