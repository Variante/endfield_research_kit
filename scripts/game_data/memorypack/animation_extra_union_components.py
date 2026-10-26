"""Own three-case ExtraData union joined to complete concrete record children."""
import json
from scripts.game_data.memorypack import animation_extra_union_sources as source
from scripts.game_data.memorypack.animation_custom_dictionary_callbacks import regions

SCHEMA='endfield.animation-extra-union-components.v1'
CAPABILITY='animation-extra-selected-union'
TYPES=['Beyond.Gameplay.View.Animation.'+name for name in('CharacterAnimExtraData','EnemyAnimExtraData','UpperBodyFightExtraData')]


def need(check,condition):
    if not condition:raise ValueError('animationExtraUnionComponents.'+check)


def normalized(v):return json.loads(json.dumps(v))


def replay_transport(transport,pins):
    need('own-complete-transport',transport.get('schema')=='endfield.animation-extra-union-transport.v1'
        and transport.get('status')=='validated-conditional-animation-extra-union-transport'
        and transport.get('nativeInputs')==pins and transport.get('typeName')==source.TYPE
        and transport.get('admittedRouteTags')==[0,1,2]and transport.get('nullUnionMarker')==255
        and transport.get('reservedMarkersRefused')==[251,252,253,254]and transport.get('canonicalTagEncoding')is True
        and transport.get('concreteChildGrammarAdmitted')is False and transport.get('parentFieldAdmitted')is False
        and transport.get('wholeOwnerAdmitted')is False)
    selected=transport.get('programs',[]);method=transport.get('slot5Method',[])
    need('exact-three-nominal-routes',len(selected)==3 and[r.get('tag')for r in selected]==[0,1,2]
        and[r.get('wrappedType')for r in selected]==TYPES and len(method)==4 and method[2]=='Deserialize')
    base=selected[0]['source']['selectedBytes'][0][0]-method[3];need('literal-selected-native-base',type(base)is int and base>=2**32)
    raw=regions(transport['ownedWindows'],[[r['start']-base,r['hex']]for r in transport['sourceRegions']],base,'extra-union')
    symbols={k:base+v for k,v in transport['symbolRvas'].items()}
    for row in selected:
        need('same-full-case-program',normalized(source.program(raw,base+method[3],symbols,tag=row['tag']))==row['source'])
        usage=row['typedRequest'];typed=row['typedArgument']
        need('own-actual-concrete-wrapper-request',tuple(usage.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments'))
            ==(6,'MemoryPack.MemoryPackReader','ReadPackable',[],[row['wrapperName']])
            and typed.get('argumentType')==row['wrapperName']and typed.get('concreteTypeKind')==18
            and typed.get('methodDefinition')==usage.get('methodSpec',[None])[0]
            and row.get('concreteGrammarAdmitted')is False
            and row.get('originalLineage',[None])[0]==row['wrappedType']
            and row['originalLineage'][-1]==source.TYPE and row.get('wrapperLineage',[None])[0]==row['wrapperName']
            and row['wrapperLineage'][-1]==transport['wrapperName'])
    need('same-canonical-null-program',normalized(source.program(raw,base+method[3],symbols,tag=0,ff=True))==transport['canonicalFF'])
    holder=transport.get('baseHolder',{});pair=transport.get('pair',{});adapter=transport.get('adapter',{})
    need('own-ordinary-abstract-base-adapter',holder.get('declaredType')==source.TYPE and holder.get('offset')==16
        and pair.get('registration',{}).get('originalType')==source.TYPE
        and pair['registration'].get('wrapperType')==transport['wrapperName']
        and adapter.get('schema')=='endfield.reference-object-adapter-source.v1'and adapter.get('nativeInputs')==pins
        and adapter.get('typeName')==source.TYPE and adapter.get('wrapperName')==transport['wrapperName']
        and adapter.get('pair')==pair and adapter.get('callbackBinding',{}).get('actualCallbackEqualsCanonicalRequired')is True
        and adapter['callbackBinding'].get('runtimeSelectionObserved')is False)
    conversions=transport.get('inheritedConversions',[])
    need('all-own-inherited-base-conversions',len(conversions)==3
        and{r.get('wrapperName')for r in conversions}=={r['wrapperName']for r in selected})
    for row in conversions:
        proof=row['conversion'];need('same-whole-inherited-reference',row['holder']['declaredType']==source.TYPE
            and row['holder']['offset']==16 and proof.get('normalReturn')is True
            and proof.get('sameFullReferenceReturned')is True and proof.get('interfaceOrdinal')==row['interfaceOrdinal'])
    return base


def compose(transport,records):
    from scripts.game_data.memorypack.animation_extra_record_components import validate_component
    pins=transport.get('nativeInputs');replay_transport(transport,pins)
    need('all-and-only-three-own-strong-records',isinstance(records,list)and len(records)==3 and{r.get('typeName')for r in records}==set(TYPES))
    caps={};required=set();routes=[];by_name={r['typeName']:r for r in records}
    for selected in transport['programs']:
        record=by_name[selected['wrappedType']];joined=validate_component(record,pins)
        child=record['capabilities'][record['capability']]
        need('own-complete-concrete-wrapper',child.get('wrapperName')==selected['wrapperName']
            and child.get('typeName')==selected['wrappedType']and child.get('valueStorageKind')=='reference8'
            and child.get('wholeGrammarAdmitted')is True and child.get('directWrapperGrammarAdmitted')is True
            and child.get('ordinaryOriginalReadValueAdmitted')is True and child.get('ownConcreteGetterSemanticsProved')is True
            and child.get('ownConcreteFactorySemanticsProved')is True)
        for key,cap in joined['capabilities'].items():
            need('coherent-shared-child:'+key,key not in caps or caps[key]==cap);caps[key]=cap
        required.update(joined['requiredExternalCapabilities'])
        routes.append(dict(tag=selected['tag'],typeName=selected['wrappedType'],wrapperName=selected['wrapperName'],
            memberCount=child['memberCount'],childCapability=record['capability']))
    callback=transport['adapter']['callbackBinding']
    caps[CAPABILITY]=dict(typeName=source.TYPE,wrapperName=transport['wrapperName'],wholeGrammarAdmitted=True,nullable=True,
        nullMarker=255,tagEncoding='short-byte',wideTagsAdmitted=False,selectedRoutes=routes,declaredUnionEntries=3,allDeclaredTagsCovered=True,
        canonicalAdapterTargetRva=callback['canonicalTargetRva'],ordinaryBaseAdapterAdmitted=True,inheritedBaseConversionsAdmitted=True,
        selectedStoredByteGrammarAdmitted=True,compatibleExistingWrapperAdmitted=False,collectionParentAdmitted=False,wholeOwnerAdmitted=False)
    return normalized(dict(schema=SCHEMA,status='validated-conditional-animation-extra-union-components',nativeInputs=pins,
        capability=CAPABILITY,capabilities=caps,requiredExternalCapabilities=sorted(required-set(caps)),
        proof=dict(transport=transport,records=records),parentFieldAdmitted=False,wholeOwnerAdmitted=False))


def validate_component(component,pins):
    need('own-selected-union-component',component.get('schema')==SCHEMA
        and component.get('status')=='validated-conditional-animation-extra-union-components'
        and component.get('nativeInputs')==pins and component.get('parentFieldAdmitted')is False and component.get('wholeOwnerAdmitted')is False)
    p=component['proof'];checked=compose(p['transport'],p['records'])
    need('same-independently-composed-union',checked==component)
    return checked
