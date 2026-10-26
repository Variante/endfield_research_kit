"""Batch missing ActionMap source callers and independently read union identities.

The generated member inventory is a declaration census, never a wire layout.
Each complete outcome joins its own four-path source/lifecycle proof to the
actual selected native union case. Child grammars and route/owner admission
remain false until a separate finite compiler and child validators close them.
No retained report, tag rank, or historical read plan supplies native facts.
"""
from __future__ import annotations

import json
from pathlib import Path

from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
from scripts.game_data.levelscript_route_deserialize_native import LAYOUT_PATH
from scripts.game_data.memorypack import generated_reader_sources
from scripts.game_data.memorypack.union_dispatch import read_union_switch


SCHEMA='endfield.levelscript-action-route-sources.v1'
LABEL='levelscriptActionRouteSources'
BASES={
    'ActionBase':'Beyond_Gameplay_Actions_ActionBaseForMemoryPack',
    'GetterBase':'Beyond_Gameplay_Actions_PureGetterForMemoryPack',
    'ActionHeader':'Beyond_Gameplay_Actions_ActionHeaderForMemoryPack',
}


def _need(check,condition,detail=''):
    if not condition:raise ValueError(LABEL+'.'+check+(':'+str(detail)[:1200]if detail else''))


def _declaration(wrapper):
    return dict(wrapperName=wrapper.name,typeName=wrapper.wrapped_type,
        typeDefinition=wrapper.type_definition,memberCount=len(wrapper.members),
        inheritedMemberCount=len(wrapper.inherited_members),members=[m.row()for m in wrapper.members],
        wireGrammarAdmitted=False)


def _inventory(image,layouts):
    _need('reviewed-layout-schema',layouts.get('schema')=='endfield.action-map-layouts.v5')
    reviewed={(r['family'],r['wrapperName'])for r in layouts['layouts']}
    _need('unique-reviewed-layouts',len(reviewed)==len(layouts['layouts']))
    inventory=list(image.memorypack_wrappers.values())
    wrappers={w.type_definition:w for w in inventory}
    _need('unique-current-wrapper-definitions',len(wrappers)==len(inventory))
    _need('unique-current-wrapper-names',len({w.name for w in inventory})==len(inventory))
    routes=[];switches={}
    for family,base in BASES.items():
        switch=read_union_switch(image,base,wrappers=wrappers)
        entries=switch['entries'];switches[family]=switch
        _need('current-union-table-cardinality',type(switch['entryCount'])is int
            and switch['entryCount']==len(entries)and len({e['tag']for e in entries})==len(entries)
            and len({e['wrapperName']for e in entries})==len(entries),family)
        for entry in entries:
            _need('literal-current-union-tag',type(entry['tag'])is int and 0<=entry['tag']<=65535,family)
            wrapper=wrappers.get(entry['typeDefinition'])
            _need('actual-union-wrapper-definition',wrapper is not None
                and wrapper.name==entry['wrapperName'],(family,entry['tag']))
            if(family,wrapper.name)in reviewed:continue
            routes.append(dict(family=family,tag=entry['tag'],**_declaration(wrapper),
                unionIdentity=dict(dispatcherVa=switch['dispatcherVa'],tableVa=switch['tableVa'],
                    entryCount=switch['entryCount'],**entry),
                routeGrammarAdmitted=False,wholeOwnerAdmitted=False))
    return switches,routes


def _types(routes):
    types={}
    for route in routes:
        for index,member in enumerate(route['members']):
            name=member['declaredType']
            record=types.setdefault(name,dict(typeName=name,occurrences=0,memberKinds=[],examples=[],
                grammarAdmitted=False))
            record['occurrences']+=1
            shape=dict(kind=member['kind'],underlyingKind=member.get('underlyingKind'),width=member.get('width'))
            if shape not in record['memberKinds']:record['memberKinds'].append(shape)
            if len(record['examples'])<8:record['examples'].append(dict(family=route['family'],
                wrapperName=route['wrapperName'],memberIndex=index,fieldName=member['name']))
    return [types[name]for name in sorted(types,key=lambda name:str(name))]


def _join_source(route,source,pins):
    count=route['memberCount'];reads=source.get('orderedSourceReads')
    _need('complete-own-generated-source',source.get('schema')=='endfield.generated-concrete-reader-source.v1'
        and source.get('nativeInputs')==pins and source.get('wrapperName')==route['wrapperName']
        and source.get('wrappedType')==route['typeName']
        and source.get('completeSelectedCallerAdmitted')is True
        and source.get('childGrammarAdmitted')is False and source.get('wholeOwnerAdmitted')is False,
        route['wrapperName'])
    _need('complete-source-member-order',isinstance(reads,list)and len(reads)==count
        and all(type(r.get('memberIndex'))is int and r['memberIndex']==i
            and r.get('fieldName')==m['name']and r.get('declaredType')==m['declaredType']
            for i,(r,m)in enumerate(zip(reads,route['members'],strict=True))),route['wrapperName'])
    programs=source.get('programs',[])
    _need('complete-four-source-frames',len(programs)==4
        and all(type(p.get('existing'))is bool and type(p.get('wrapperNull'))is bool
            and p.get('frame',{}).get('entryRspRestored')is True
            and p.get('frame',{}).get('allWin64IntegerNonvolatilesRestored')is True for p in programs)
        and {(p['existing'],p['wrapperNull'])for p in programs}=={(False,False),(True,False),(False,True),(True,True)},
        route['wrapperName'])
    return dict(family=route['family'],tag=route['tag'],wrapperName=route['wrapperName'],
        typeName=route['typeName'],memberCount=count,status='complete-route-source-proved',
        unionIdentity=route['unionIdentity'],source=source,routeGrammarAdmitted=False,
        childGrammarAdmitted=False,wholeOwnerAdmitted=False)


def _parent_bindings(image,owner):
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    result=[]
    for read in owner['source']['orderedSourceReads']:
        context=read.get('context')
        if context is None:continue
        request=derive_typed_usage_context(image,context['instructionRva'],label=LABEL+'.parentRequest')
        instruction=read['instruction'];raw=bytes.fromhex(instruction[1])
        _need('same-fresh-parent-request',request.get('methodSpec')==context.get('methodSpec')
            and request.get('methodArguments')==[read['declaredType']]
            and len(raw)==5 and raw[0]==232
            and instruction[0]+5+int.from_bytes(raw[1:],'little',signed=True)==read['sourceTargetRva'],
            (owner['wrapperName'],read['fieldName']))
        result.append(dict(wrapperName=owner['wrapperName'],fieldName=read['fieldName'],
            memberIndex=read['memberIndex'],typeName=read['declaredType'],
            sourceTargetRva=read['sourceTargetRva'],sourceInstruction=instruction,typedRequest=request))
    return result


def derive(image,pins,*,requests=None,layout_path=LAYOUT_PATH,progress=None):
    """Fresh census on the caller's sole image, with at most 512 owners per pass.

    requests is an optional list of {family,wrapperName} declaration selectors.
    None derives every currently missing route, so later payload refusals do
    not require another metadata/source discovery sweep. No selector carries
    a tag, field layout, source proof or capability. Progress receives copies.
    """
    _publication_gate(image,pins)
    path=Path(layout_path);raw=path.read_bytes();layouts=json.loads(raw)
    switches,routes=_inventory(image,layouts)
    by_key={(r['family'],r['wrapperName']):r for r in routes}
    _need('unique-missing-route-keys',len(by_key)==len(routes))
    if requests is None:selected=routes
    else:
        _need('request-list',type(requests)is list and bool(requests))
        keys=[]
        for request in requests:
            _need('declaration-selectors-only',type(request)is dict and set(request)=={'family','wrapperName'}
                and type(request['family'])is str and type(request['wrapperName'])is str)
            keys.append((request['family'],request['wrapperName']))
        _need('distinct-requested-routes',len(keys)==len(set(keys)))
        _need('requested-current-missing-routes',all(key in by_key for key in keys),[key for key in keys if key not in by_key][:8])
        selected=[by_key[key]for key in keys]
    declared_types=_types(routes)
    def announce(event):
        if progress is not None:progress(json.loads(json.dumps(event)))
    announce(dict(stage='current-route-declarations',missingRoutes=len(routes),requestedRoutes=len(selected),
        declaredTypes=declared_types,routes=routes))
    owners=[]
    for offset in range(0,len(selected),512):
        group=selected[offset:offset+512]
        batch=generated_reader_sources.derive_many(image,pins,[r['wrapperName']for r in group])
        _need('same-current-batch-native-inputs',batch.get('nativeInputs')==pins)
        _need('one-outcome-per-request',len(batch['owners'])==len(group))
        for route,outcome in zip(group,batch['owners'],strict=True):
            try:
                if outcome.get('status')!='complete-reader-source-proved':
                    _need('pending-outcome-owner',outcome.get('wrapperName')==route['wrapperName'])
                    raise ValueError(outcome.get('reason','missing-complete-generated-source'))
                owner=_join_source(route,outcome['proof'],pins)
                owner['parentBindings']=_parent_bindings(image,owner)
            except(ValueError,KeyError,IndexError,TypeError)as error:
                owner=dict(family=route['family'],tag=route['tag'],wrapperName=route['wrapperName'],
                    typeName=route['typeName'],memberCount=route['memberCount'],status='pendingReview',
                    reason=str(error)[:2400],unionIdentity=route['unionIdentity'],routeGrammarAdmitted=False,
                    childGrammarAdmitted=False,wholeOwnerAdmitted=False)
            owners.append(owner)
        announce(dict(stage='current-route-source-batch',processed=len(owners),requestedRoutes=len(selected),
            complete=sum(o['status']=='complete-route-source-proved'for o in owners),
            pending=sum(o['status']=='pendingReview'for o in owners)))
    _need('reviewed-layout-input-unchanged',path.read_bytes()==raw)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='complete-source-census',nativeInputs=pins,
        unionSwitches=switches,missingRouteDeclarations=routes,declaredTypes=declared_types,owners=owners,
        routeGrammarAdmitted=False,childGrammarAdmitted=False,wholeOwnerAdmitted=False,nativeAdmissionGranted=False,
        evidenceBoundary='Fresh actual union identity and individual complete generated source outcomes. '
            'Declared member types are an inventory only; every child wire grammar, route admission, '
            'whole owner EOF, runtime selection and execution remain separate.')))
