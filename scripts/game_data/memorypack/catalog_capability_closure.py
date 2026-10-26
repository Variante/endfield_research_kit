"""Role-aware finite capability closure for current catalog consumer reviews.

An explicit selector grammar can be complete for its declared finite routes
while its whole-union flag remains false. Every such route must have its own
normative program and dependency list. A nominal enum callback is usable only
through the reached list that embeds the same independently selected callback;
it never grants parent or collection grammar by itself. This is a pure review
of a supplied aggregate, not native authentication or catalog admission.
"""
import json

SELECTORS={
    'SelectorFinder':'Beyond.Gameplay.Core.Selector+Finder+Data',
    'SelectorValidator':'Beyond.Gameplay.Core.Selector+Validator+Data',
    'SelectorPostProcessor':'Beyond.Gameplay.Core.Selector+PostProcessor+Data',
}


def _children(value):
    result=set()
    if isinstance(value,dict):
        for key in('childCapability','elementCapability'):
            if isinstance(value.get(key),str)and value[key]:result.add(value[key])
        for key in('requiredCapabilities','requiredExternalCapabilities'):
            if isinstance(value.get(key),list):result.update(n for n in value[key]if isinstance(n,str)and n)
        for child in value.values():result.update(_children(child))
    elif isinstance(value,list):
        for child in value:result.update(_children(child))
    return result


def _finite_selector(aggregate,name,cap):
    tags=cap.get('admittedRouteTags')
    if not(cap.get('typeName')==SELECTORS[name]and cap.get('wholeGrammarAdmitted')is False
            and cap.get('nullAdmitted')is True and cap.get('positiveRoutesRequireExplicitProgram')is True
            and isinstance(tags,list)and tags and all(type(tag)is int and tag>=0 for tag in tags)
            and len(set(tags))==len(tags)):return None
    programs=aggregate.get('programs');requirements=aggregate.get('routeRequirements')
    if not(isinstance(programs,list)and isinstance(requirements,dict)):return None
    selected=[];dependencies=set()
    for tag in tags:
        matching=[p for p in programs if isinstance(p,dict)and p.get('family')==name
            and type(p.get('tag'))is int and p['tag']==tag]
        if len(matching)!=1:return None
        program=matching[0];reads=program.get('reads');key=name+':'+str(tag);required=requirements.get(key)
        if not(isinstance(program.get('wrapperName'),str)and program['wrapperName']
                and type(program.get('memberCount'))is int and program['memberCount']>=0
                and isinstance(reads,list)and len(reads)==program['memberCount']
                and [r.get('memberIndex')for r in reads]==list(range(program['memberCount']))
                and all(isinstance(r.get('fieldName'),str)and r['fieldName']and isinstance(r.get('kind'),str)and r['kind']for r in reads)
                and len({r['fieldName']for r in reads})==len(reads)
                and isinstance(required,list)and all(isinstance(n,str)and n for n in required)
                and len(set(required))==len(required)):return None
        dependencies.update(required);dependencies.update(_children(reads))
        selected.append(dict(family=name,tag=tag,wrapperName=program['wrapperName'],routeKey=key))
    return dict(closedLocally=True,mode='explicit-finite-selector-programs',requiredCapabilities=sorted(dependencies),
        selectedPrograms=selected,wholeUnionGrammarGranted=False,unselectedTagsAdmitted=False)


def _bound_callback(aggregate,name,cap,path):
    if not(name.startswith('skill-enum-callback:')and len(path)>=2 and path[-1]==name):return None
    typename=name.split(':',1)[1];parent=aggregate.get('capabilities',{}).get(path[-2],{})
    embedded=parent.get('elementCallback')
    if not(isinstance(embedded,dict)and cap.get('schema')=='endfield.enum-nominal-callback-sources.v1'
            and cap.get('status')=='validated-conditional-callback'and cap.get('typeName')==typename
            and type(cap.get('typeDefinition'))is int and cap['typeDefinition']>0
            and type(cap.get('wireBytes'))is int and cap['wireBytes']==4
            and type(cap.get('callbackSlot'))is int and cap['callbackSlot']==5
            and all(type(cap.get(k))is int and cap[k]>0 for k in('callbackTargetRva','formatterMethodDefinition'))
            and cap.get('readerByref')is True and cap.get('outputByref')is True
            and cap.get('parentOrCollectionGrammarAdmitted')is False
            and cap.get('actualRuntimeSelectionObserved')is False and cap.get('unconditionalCallbackSelectionProved')is False
            and isinstance(cap.get('conditions'),list)and cap['conditions']
            and parent.get('elementCapability')==name and parent.get('elementType')==typename
            and type(parent.get('elementTypeDefinition'))is int and parent['elementTypeDefinition']==cap['typeDefinition']
            and parent.get('closedListType')=='System.Collections.Generic.List`1<'+typename+'>'
            and parent.get('positiveCountsAdmitted')is True and parent.get('elementGrammarAdmitted')is True
            and type(parent.get('elementWireBytes'))is int and parent['elementWireBytes']==4
            and parent.get('rawBitsPreserved')is True and parent.get('nativeInputs')==aggregate.get('nativeInputs')
            and embedded.get('nativeInputs')==aggregate.get('nativeInputs')
            and('nativeInputs'not in cap or cap['nativeInputs']==aggregate.get('nativeInputs'))):return None
    comparable={k:v for k,v in embedded.items()if k!='nativeInputs'}
    own={k:v for k,v in cap.items()if k!='nativeInputs'}
    # JSON identity preserves the distinction between booleans and integers.
    if json.dumps(comparable,sort_keys=True,separators=(',',':'))!=json.dumps(own,sort_keys=True,separators=(',',':')):return None
    return dict(closedLocally=True,mode='reached-list-selected-enum-callback',requiredCapabilities=[],
        parentCapability=path[-2],parentOrCollectionGrammarGranted=False,unconditionalRuntimeSelectionGranted=False)


def describe(aggregate,name,path=()):
    cap=aggregate.get('capabilities',{}).get(name)
    if not isinstance(cap,dict):return dict(closedLocally=False,mode='missing-capability',requiredCapabilities=[])
    if cap.get('wholeGrammarAdmitted')is True:
        return dict(closedLocally=True,mode='whole-capability-grammar',requiredCapabilities=[])
    if cap.get('positiveCountsAdmitted')is True and cap.get('elementGrammarAdmitted')is True:
        return dict(closedLocally=True,mode='selected-positive-collection',requiredCapabilities=[])
    from scripts.game_data.memorypack.catalog_consumer_domains import value_domain_complete
    if value_domain_complete(name,cap):
        return dict(closedLocally=True,mode='exact-generated-value-domain',requiredCapabilities=[],wholeOwnerGranted=False)
    if name in SELECTORS:
        selected=_finite_selector(aggregate,name,cap)
        if selected is not None:return selected
    callback=_bound_callback(aggregate,name,cap,path)
    if callback is not None:return callback
    return dict(closedLocally=False,mode='unproved-selected-capability-role',requiredCapabilities=[])
