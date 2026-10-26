"""Finite positive LevelWide graph; actual whole LevelData remains separate."""
import copy,json

from scripts.game_data.memorypack import leveldata_levelwide_records as records
from scripts.game_data.memorypack.leveldata_levelwide_inner_sources import KEY,VALUE,TYPE as INNER,PARENT as TYPE

CAP='story-levelwide-configs'
ROOT='Beyond.Gameplay.LevelData'
FIELD='levelWideConfigs'


def need(check,condition):
    if not condition:raise ValueError('levelwideComponents.'+check)


def compose(pins,*,record_graph,union,inner,outer,condition,host,image_base):
    """Pure composition of independently source-proved components.

    Only derive supplies fresh native facts. This projection never authenticates
    arbitrary report JSON or establishes a runtime callback/provider choice.
    """
    from scripts.game_data.codecs.leveldata.current_levelwide import validate,WRAPPERS,LIMIT,NODE_LIMIT
    from scripts.game_data.memorypack.leveldata_empty_dictionary_sources import select_parent
    from scripts.game_data.memorypack.leveldata_condition_components import CAP as CONDITION_CAP
    from scripts.game_data.memorypack.leveldata_lang_key_components import CAP as LANG_CAP
    need('selected-image-base',type(image_base)is int and image_base>0)
    facts=(record_graph,union,inner,outer,condition,host)
    need('same-selected-native-inputs',all(fact.get('nativeInputs')==pins for fact in facts))
    need('exact-record-domain',set(record_graph['records'])==set(record_graph['capabilities'])==set(records.PLANS))
    ordinary={}
    for name in records.PLANS:
        item=record_graph['records'][name];adapter=item['adapter'];source=item['source']
        need('own-ordinary-source:'+name,item['capability']==record_graph['capabilities'][name]
            and adapter['typeName']==name and adapter['wrapperName']==source['wrapperName']==WRAPPERS[name]
            and source['lifecycle']['GetValue']['method']==adapter['getterMethod']
            and source['lifecycle']['GetValue']['program'].get('fullReferenceOutput')is True
            and adapter['callbackBinding']['actualCallbackEqualsCanonicalRequired']is True)
        ordinary[name]=dict(typeName=name,wrapperName=adapter['wrapperName'],ordinaryAdapterAdmitted=True)
    need('own-complete-two-route-union',union['typeName']==VALUE and union['adapter']['typeName']==VALUE
        and union['canonicalFF']['clearedOutputBytes']==8 and union['canonicalFF']['entryRspRestored']is True
        and union['canonicalFF']['normalReturn']is True
        and [(row['tag'],row['source']['existingIncompatibleWrapper'])for row in union['programs']]==[(0,False),(0,True),(1,False),(1,True)]
        and [row['tag']for row in union['conversions']]==[0,1]
        and all(row['source']['sameReader']and row['source']['sameOutput']and row['source']['normalReturn']and row['source']['entryRspRestored']for row in union['programs']))
    from scripts.game_data.memorypack.leveldata_levelwide_union_sources import CHILDREN
    routes={}
    for tag,name in CHILDREN.items():
        selected=[row for row in union['programs']if row['tag']==tag]
        need('exact-ordinary-child-union-route',len(selected)==2 and all(row['typeName']==name
            and row['wrapperName']==ordinary[name]['wrapperName']for row in selected)
            and next(row for row in union['conversions']if row['tag']==tag)['typeName']==name)
        routes[str(tag)]=dict(tag=tag,typeName=name,wrapperName=ordinary[name]['wrapperName'],
            actualWrapperCallbackEqualsProvedConcreteRequired=True)
    need('complete-owned-nested-map-source',inner['status']=='validated-conditional-source-only'
        and inner['typeName']==INNER and inner['positiveCountLoopProved']is True
        and inner['pooledStringKeyGrammarProved']is True
        and inner['valueCallback']['adapter']==union['adapter']
        and inner['actualValueCallbackEqualsOwnUnionAdapterRequired']is True)
    need('complete-owned-outer-map-source',outer['status']=='validated-conditional-source-only'
        and outer['typeName']==TYPE and outer['positiveCountLoopProved']is True
        and outer['positiveCountRange']==[1,LIMIT]and outer['keyGrammarProved']is True
        and outer['valueCallback']['typeName']==INNER
        and outer['valueCallback']['callbackTargetRva']==inner['registration']['pointer']-image_base
        and outer['helperABI']==inner['helperABI']
        and outer['actualValueCallbackEqualsOwnInnerSourceRequired']is True)
    need('both-source-induction-branches',[row['sameComparer']for row in outer['induction']]==[False,True]
        and all(row['proof']['maxCount']==LIMIT and row['proof']['noSignedCounterOverflow']is True
            and row['proof']['modeKey']=='newDictionary'for row in outer['induction']))
    for role,fact,witness in(('outer',outer,['System.Int32Enum','object']),('inner',inner,['object','object'])):
        need('exact-conditional-'+role+'-source',fact['sourceWitnessClassArguments']==witness
            and fact['closedPointerEquivalenceProved']is False
            and fact['actualCallbackEqualsSourceWitnessRequired']is True
            and fact['typedConstructorAndHelperCompatibilityRequired']is True
            and fact['runtimeFormatterSelectionObserved']is False
            and fact['parentFieldAdmitted']is False and fact['wholeOwnerAdmitted']is False)
    field,read=select_parent(host);request=outer['actualParent']['typedRequest']
    need('complete-actual-LevelData-parent',host['program']['originalType']==ROOT
        and host['program']['memberCount']==43 and host['program']['entryFrameRestored']is True
        and host['program']['normalReturnViaBarrier']is True
        and request==inner['actualParent']['typedRequest']
        and request['instructionRva']==read['typedUsage']['instruction']-image_base
        and request['methodName']=='ReadPackable'and request['methodArguments']==[TYPE]
        and outer['actualParent']['closedCarrier']==inner['actualParent']['closedOuterCarrier'])
    parent=dict(ownerType=ROOT,fieldName=FIELD,typeName=TYPE,capability=CAP,
        readerMethodDefinition=request['methodSpec'][0],sourceTargetRva=read['sourceTarget']-image_base,
        actualCallbackEqualsCanonicalRequired=True)
    dock_source=record_graph['children']['dockList'];witness=dock_source['witnessComponent']
    need('own-dock-positive-list',dock_source['status']=='validated-bounded-reference-list-induction'
        and dock_source['countRange']==[-1,LIMIT]and dock_source['elementType']==records.DOCK)
    listing=dict(typeName=records.LIST,elementType=records.DOCK,countLimit=LIMIT,headerBytes=4,nullable=True,
        positiveCountsAdmitted=True,elementGrammarAdmitted=True,initiallyNullListRequired=True,
        actualCallbackEqualsProvedChildRequired=True,liveFormatterSelectionObserved=False,
        packableReaderMethodDefinition=witness['typedRequest']['methodSpec'][0],
        packableReaderTargetRva=witness['callTargetRva'])
    dictionaries={}
    for role,name,key,value,witness in(('outer',TYPE,KEY,INNER,['System.Int32Enum','object']),
            ('inner',INNER,'string',VALUE,['object','object'])):
        dictionaries[role]=dict(typeName=name,keyType=key,valueType=value,sourceWitnessClassArguments=witness,
            headerBytes=4,countLimit=LIMIT,outputBytes=8,positiveCountsAdmitted=True,keyGrammarAdmitted=True,valueGrammarAdmitted=True,
            actualCallbackEqualsSourceWitnessRequired=True,typedConstructorAndHelperCompatibilityRequired=True,
            initiallyNullOutputRequired=True,closedPointerEquivalenceProved=False,runtimeFormatterSelectionObserved=False)
    dictionaries['inner'].update(keyEncoding='int32-pool-index',actualKeyCallbackEqualsPooledStringRequired=True)
    cap=dict(typeName=TYPE,capability=CAP,countLimit=LIMIT,nodeLimit=NODE_LIMIT,profileAdmitted=True,
        externalStringPoolRequired=True,actualCallbackEqualsCanonicalRequired=True,coherentOriginalContextsRequired=True,
        initiallyNullDictionariesRequired=True,wholeOwnerAdmitted=False,runtimeFormatterSelectionObserved=False,
        enumCallback=copy.deepcopy(outer['keyCallback']['capability']),dictionaries=dictionaries,
        union=dict(typeName=VALUE,admittedRouteTags=[0,1],routes=routes,canonicalFFAdmitted=True,
            shortTagsOnly=True,ordinaryAdapterAdmitted=True,inheritedConversionsProved=True,runtimeFormatterSelectionObserved=False),
        records=copy.deepcopy(record_graph['capabilities']),ordinaryRecords=ordinary,dockList=listing,
        langKey=copy.deepcopy(record_graph['children']['langKey']['capabilities'][LANG_CAP]),
        condition=copy.deepcopy(condition['capabilities'][CONDITION_CAP]),parentBinding=parent)
    validate(cap);return cap


def derive(image,pins,host,*,condition):
    """Fresh same-image readers, adapters, enum, nested maps and host binding."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.enum_nominal_callback_sources import derive as enum_source
    from scripts.game_data.memorypack import generated_reader_sources
    from scripts.game_data.memorypack import leveldata_levelwide_union_sources as unions
    from scripts.game_data.memorypack import leveldata_levelwide_inner_sources as inners
    from scripts.game_data.memorypack import leveldata_levelwide_outer_sources as outers
    from scripts.game_data.memorypack.leveldata_empty_dictionary_sources import select_parent
    from scripts.game_data.memorypack.leveldata_source_refusal import require_complete
    _publication_gate(image,pins);base=image.pe.image_base
    wrappers={w.wrapped_type:w for w in image.memorypack_wrappers.values()if w.wrapped_type in records.PLANS}
    need('same-exact-three-current-wrappers',set(wrappers)==set(records.PLANS))
    names=[records.DOCK,records.DOCK_CONFIG,records.RAFT_CONFIG]
    generated=generated_reader_sources.derive_many(image,pins,[wrappers[name].name for name in names])
    sources={name:require_complete(row,validator='levelwideComponents',type_name=name)
        for name,row in zip(names,generated['owners'],strict=True)}
    graph=records.derive(image,pins,sources=sources,condition=condition);union=unions.derive(image,pins)
    field,read=select_parent(host)
    request=derive_typed_usage_context(image,read['typedUsage']['instruction']-base,label='levelwideComponents.actual-host')
    key=enum_source(image,pins,type_name=KEY)
    inner=inners.derive(image,pins,parent_request=request,union_source=union)
    outer=outers.derive(image,pins,parent_request=request,key_source=key,inner_source=inner)
    cap=compose(pins,record_graph=graph,union=union,inner=inner,outer=outer,condition=condition,host=host,image_base=base)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.story-levelwide-components.v1',
        status='validated-conditional-finite-levelwide-graph',nativeInputs=pins,capability=cap,
        records=graph,union=union,inner=inner,outer=outer,parent=dict(field=field,source=read,typedRequest=request,binding=cap['parentBinding']),
        parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Three named current records and ordinary adapters, LangKey/Condition/Dock list field transfers, two short union routes and inherited conversions, own nominal enum callback, separate enum/reference and reference/reference dictionary source witnesses, exact helper/slot5 transfers, bounded positive loops and the actual LevelData field.',
            conditional='Matching original typed contexts and selected canonical callbacks, initially-null maps/list, buffered disjoint storage and normal compatible helper effects under the individual source conditions. No differently closed pointer identity is inferred.',
            structuralOnly='Stored syntax, raw identity bits and pooled strings; no gameplay or runtime selection claim.',
            unresolved=['whole LevelData physical EOF/public source operation','runtime factory/provider/callback replacement and nonselected paths']))))
