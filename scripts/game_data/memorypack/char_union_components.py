"""Compose each own CharInteract union from exact immediate wire children.

Direct wrapper routes and ordinary Original callbacks remain separate. Six
action sub-unions are usable through ReadPackable without an Original adapter;
the action root and the two list-element unions additionally require their
own independently proved canonical adapter.
"""
import json
from scripts.game_data.memorypack.char_union_sources import TYPE,NESTED

SCHEMA='endfield.char-interact-union-components.v1'
WIRE='char-interact-union'
ORDINARY=(TYPE,)+NESTED[-2:]


def need(check,condition):
    if not condition:raise ValueError('charUnionComponents.'+check)


def norm(value):return json.loads(json.dumps(value))
def key(name):need('finite-own-union',name in(TYPE,)+NESTED);return WIRE+':'+name


def _call(program,at):
    cells={a+i:b for a,h in program['selectedBytes']for i,b in enumerate(bytes.fromhex(h))}
    raw=bytes(cells.get(at+i,0)for i in range(5))
    need('own-selected-E8-call',raw[0]==232)
    return at+5+int.from_bytes(raw[1:],'little',signed=True)


def _typed(row):
    usage=row['typedRequest'];typed=row['typedArgument']
    need('own-actual-returning-wrapper-context',tuple(usage.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments'))
        ==(6,'MemoryPack.MemoryPackReader','ReadPackable',[],[row['wrapperName']])
        and typed.get('argumentType')==row['wrapperName']and typed.get('concreteTypeKind')==18
        and typed.get('methodDefinition')==usage.get('methodSpec',[None])[0])


def _adapter(value,pins,name,wrapper):
    pair=value['pair'];adapter=value['adapter'];registration=pair['registration'];face,=pair['composition']['interfaces']
    need('own-canonical-original-adapter',registration.get('originalType')==name and registration.get('wrapperType')==wrapper
        and adapter.get('schema')=='endfield.reference-object-adapter-source.v1'and adapter.get('nativeInputs')==pins
        and adapter.get('typeName')==name and adapter.get('wrapperName')==wrapper and adapter.get('pair')==pair
        and adapter.get('callbackBinding',{}).get('actualCallbackEqualsCanonicalRequired')is True
        and adapter['callbackBinding'].get('runtimeSelectionObserved')is False)
    raw=bytes.fromhex(registration['key']['typeRawHex'])
    need('own-nominal-class-key',len(raw)==16 and raw[10:12]==bytes((18,0))and registration['key']['typeName']==name)
    original=int.from_bytes(raw[:8],'little')
    if 'nominalOriginal'in value:
        nominal=value['nominalOriginal']
        need('same-independent-abstract-nominal',nominal.get('typeName')==name and nominal.get('typeDefinition')==original
            and nominal.get('valueType')is False and nominal.get('flags',0)&128==128)
    return dict(valueStorageKind='reference8',originalTypeDefinition=original,
        ordinaryOriginalReadValueAdmitted=True,ordinaryOriginalCallbackAdmitted=True,
        canonicalAdapterTargetRva=adapter['callbackBinding']['canonicalTargetRva'],
        formatterDeserializeMethodDefinition=face['formatterDeserializeMethodIndex'],
        ordinaryBaseAdapterAdmitted=True,inheritedBaseConversionsAdmitted=True)


def _top(value,pins):
    from scripts.game_data.memorypack.animation_custom_dictionary_callbacks import regions
    from scripts.game_data.memorypack.animation_union_sources import char_animation_program,_target
    need('own-full-action-source',value.get('schema')=='endfield.animation-selected-union-sources.v1'
        and value.get('status')=='validated-conditional-selected-animation-union-sources'and value.get('nativeInputs')==pins)
    source=value['families']['char-animation'];rows=source['selectedRoutes'];switch=source['switch']
    need('all-physical-action-routes',source.get('typeName')==TYPE and source.get('completePhysicalFamilyRequested')is True
        and source.get('wholeUnionAdmitted')is False and switch.get('entryCount')==48
        and len(rows)==48 and[r['tag']for r in rows]==list(range(48))
        and len({r['wrappedType']for r in rows})==48)
    entry=int(switch['dispatcherVa'],16);base=rows[0]['programs'][0]['source']['imageBase']
    raw=regions(source['codeWindows'],source['actualSourceRegions'],base,'char-action-union')
    first=rows[0]['programs'][0]['source'];site=first['childUsage']['instruction']+10
    null=source['canonicalFF'];barrier_site=next(a+3 for a,h in null['selectedBytes']if h=='488bcb')
    symbols=dict(header=_target(dict(regions=raw),'488d542438488bcf6689742438e8'),
        assignable=_target(dict(regions=raw),'488b09e8'),packable=_call(first,site),barrier=_call(null,barrier_site))
    table=int(switch['tableVa'],16)
    for row,slot in zip(rows,switch['entries'],strict=True):
        need('same-physical-table-route',row['route']==slot and row['tag']==slot['tag']and row['wrapperName']==slot['wrapperName'])
        need('both-selected-wrapper-preconditions',len(row['programs'])==2)
        for actual,existing in zip(row['programs'],(False,True),strict=True):
            expected=char_animation_program(raw,entry,symbols,tag=row['tag'],count=48,table=table,
                selected=int(slot['targetVa'],16),existing=existing)
            expected['childUsage']=expected['childContext'];_typed(dict(row,**{k:actual[k]for k in('typedRequest','typedArgument')}))
            need('whole-own-selected-action-bytes',norm(expected)==actual['source'])
    need('whole-canonical-action-FF',norm(char_animation_program(raw,entry,symbols,tag=0,count=48,table=table,
        selected=int(switch['entries'][0]['targetVa'],16),ff=True))==null)
    conversions=source['derivedBaseConversions']
    need('all-own-inherited-action-conversions',len(conversions)==48
        and{r['wrapperName']for r in conversions}=={r['wrapperName']for r in rows}
        and source['baseHolder'].get('declaredType')==TYPE and source['baseHolder'].get('offset')==16)
    for row in conversions:
        proof=row['program'];need('whole-inherited-action-reference',row['holder'].get('declaredType')==TYPE
            and row['holder'].get('offset')==16 and proof.get('normalReturn')is True
            and proof.get('sameFullReferenceReturned')is True and proof.get('interfaceOrdinal')==row['interfaceOrdinal'])
    return TYPE,source['wrapperName'],rows,_adapter(source,pins,TYPE,source['wrapperName'])


def _nested(value,pins):
    from scripts.game_data.memorypack.animation_custom_dictionary_callbacks import regions
    from scripts.game_data.memorypack.levelscript_condition_nested_sources import program
    source=value.get('source',value);name=source.get('wrappedType');rows=source.get('cases',[])
    need('own-complete-nested-transport',name in NESTED and source.get('status')=='complete-nested-union-transport-source'
        and source.get('concreteChildGrammarAdmitted')is False and source.get('wholeOwnerAdmitted')is False
        and 1<=len(rows)<=48 and[r['tag']for r in rows]==list(range(len(rows)))
        and len({r['wrappedType']for r in rows})==len(rows))
    method=source['slot5Method'];first=rows[0]['source']['nonnullChild'];entry=first['selectedBytes'][0][0];base=entry-method[3]
    raw=regions(source['sourceWindows'],[[a-base,h]for a,h in source['sourceRegions']],base,'char-nested-union')
    barrier=base+source['barrier']['actualEntryRva'];flag=base+source['barrier']['result']['disabledFlagRva']
    for row in rows:
        _typed(row)
        for child_null,label in((False,'nonnullChild'),(True,'nullChild')):
            actual=row['source'][label];cast=None
            if actual.get('nullableCastUsage')is not None:
                use=actual['nullableCastUsage'];cast=_call(actual,use['instructionVa']+7)
            expected=program(raw,entry,tag=row['tag'],header=actual.get('headerTargetVa',0),packable=actual['childTargetVa'],
                barrier=barrier,cast=cast,disabled_flag=flag,child_null=child_null)
            need('whole-own-selected-nested-bytes',norm(expected)==actual)
    actual=source['canonicalFF'];expected=program(raw,entry,tag=0,header=first.get('headerTargetVa',0),
        packable=first['childTargetVa'],barrier=barrier,cast=None,disabled_flag=flag,ff=True)
    need('whole-own-nested-FF',norm(expected)==actual)
    for hook in source.get('posthooks',{}).values():
        need('independent-whole-typed-cache-posthook',hook.get('cacheWriteAdmitted')is True
            and hook.get('inheritedBaseReferencePreserved')is True and hook.get('liveCacheCoherenceObserved')is False
            and len(hook.get('programs',[]))>=3)
        regions(hook['sourceWindows'],[[a-base,h]for a,h in hook['sourceRegions']],base,'char-nested-posthook')
    identity=dict(ordinaryOriginalReadValueAdmitted=False,ordinaryOriginalCallbackAdmitted=False,
        ordinaryBaseAdapterAdmitted=False,inheritedBaseConversionsAdmitted=False)
    if 'adapter'in value:
        identity=_adapter(value,pins,name,source['wrapperName']);joins=value['inheritedConversions']
        need('all-own-nested-inherited-conversions',len(joins)==len(rows)
            and{r['wrapperName']for r in joins}=={r['wrapperName']for r in rows})
        for join in joins:
            p=join['conversion'];need('whole-nested-inherited-reference',p.get('normalReturn')is True
                and p.get('sameFullReferenceReturned')is True and p.get('interfaceOrdinal')==join['interfaceOrdinal'])
    need('required-list-element-ordinary-adapter',name not in ORDINARY or identity['ordinaryOriginalReadValueAdmitted'])
    return name,source['wrapperName'],rows,identity


def compose(transport,children,pins):
    name,wrapper,rows,identity=_top(transport,pins)if 'families'in transport else _nested(transport,pins)
    need('all-and-only-immediate-children',isinstance(children,dict)and set(children)=={r['wrappedType']for r in rows})
    caps={};required=set();routes=[]
    for row in rows:
        child=children[row['wrappedType']]
        if row['wrappedType']in NESTED:
            own=validate_component(child,pins);wire=WIRE
        else:
            from scripts.game_data.memorypack.char_record_components import validate_component as record
            own=record(child,pins);wire='char-interact-record'
        cap=own['capabilities'][own['capability']]
        need('own-whole-direct-wrapper-child',cap.get('typeName')==row['wrappedType']and cap.get('wrapperName')==row['wrapperName']
            and cap.get('wholeGrammarAdmitted')is True and cap.get('directWrapperGrammarAdmitted')is True)
        need('coherent-whole-child-capability-map',all(k not in caps or caps[k]==v for k,v in own['capabilities'].items()))
        caps.update(own['capabilities']);required.update(own['requiredExternalCapabilities'])
        routes.append(dict(tag=row['tag'],typeName=row['wrappedType'],wrapperName=row['wrapperName'],
            childCapability=own['capability'],childWire=wire))
    capability=key(name)
    caps[capability]=dict(typeName=name,wrapperName=wrapper,selectedRoutes=routes,declaredUnionEntries=len(rows),
        allDeclaredTagsCovered=True,nullable=True,nullMarker=255,tagEncoding='short-byte',wideTagsAdmitted=False,
        wholeGrammarAdmitted=True,directWrapperGrammarAdmitted=True,selectedStoredByteGrammarAdmitted=True,
        compatibleExistingWrapperAdmitted=False,collectionParentAdmitted=False,wholeOwnerAdmitted=False,**identity)
    return dict(schema=SCHEMA,status='validated-conditional-char-interact-union-components',nativeInputs=pins,
        capability=capability,capabilities=caps,requiredExternalCapabilities=sorted(required-set(caps)),
        proof=dict(transport=transport,children=children),parentFieldAdmitted=False,wholeOwnerAdmitted=False)


def validate_component(component,pins):
    need('own-whole-conditional-union',component.get('schema')==SCHEMA
        and component.get('status')=='validated-conditional-char-interact-union-components'and component.get('nativeInputs')==pins
        and component.get('parentFieldAdmitted')is False and component.get('wholeOwnerAdmitted')is False)
    p=component['proof'];checked=compose(p['transport'],p['children'],pins)
    need('same-complete-owned-composition',checked==component)
    return {k:checked[k]for k in('capability','capabilities','requiredExternalCapabilities')}
