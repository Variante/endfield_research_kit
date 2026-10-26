"""Join selected animation union sources to their exact ordinary record owners.

This closes only stored byte-payload tags. It supplies neither a containing
list/dictionary nor the enclosing CharInteract/AnimationConfig owner, runtime
compatible-wrapper selection, public decoder opt-in or catalog admission.
"""
import json
from scripts.game_data.memorypack.animation_union_sources import FAMILIES
from scripts.game_data.memorypack.animation_record_components import PLANS

CAPABILITIES={'char-animation':'animation-char-selected-union','montage':'animation-montage-selected-union'}


def need(check,condition,detail=None):
    if not condition:raise ValueError('animationUnionComponents.'+check+':'+str(detail)[:800])


def compose(union_source,records,*,family):
    need('finite-family',family in FAMILIES)
    pins=union_source.get('nativeInputs');proof=union_source.get('families',{}).get(family,{})
    original,children,count=FAMILIES[family]
    need('exact-selected-union-source',union_source.get('schema')=='endfield.animation-selected-union-sources.v1'
        and union_source.get('status')=='validated-conditional-selected-animation-union-sources'
        and bool(pins)and proof.get('typeName')==original and proof.get('switch',{}).get('entryCount')==count
        and proof.get('wholeUnionAdmitted')is False and proof.get('collectionParentAdmitted')is False)
    need('exact-concrete-record-set',isinstance(records,list)and len(records)==len(children)
        and{r.get('typeName')for r in records}==set(children))
    by_name={r['typeName']:r for r in records};routes=proof.get('selectedRoutes',[])
    need('all-and-only-selected-source-routes',len(routes)==len(children)
        and{r.get('wrappedType')for r in routes}==set(children)
        and len({r.get('tag')for r in routes})==len(routes)
        and all(type(r.get('tag'))is int and 0<=r['tag']<min(count,250)for r in routes))
    conversions=proof.get('derivedBaseConversions',[])
    need('same-base-holder-and-conversions',proof.get('baseHolder',{}).get('declaredType')==original
        and proof['baseHolder'].get('offset')==16 and len(conversions)==len(routes)
        and{c.get('wrapperName')for c in conversions}=={r['wrapperName']for r in routes})
    adapter=proof.get('adapter',{})
    need('own-ordinary-base-adapter',adapter.get('schema')=='endfield.reference-object-adapter-source.v1'
        and adapter.get('nativeInputs')==pins and adapter.get('typeName')==original
        and adapter.get('wrapperName')==proof.get('wrapperName'))
    null=proof.get('canonicalFF',{})
    need('actual-canonical-FF-clear-and-frame',null.get('canonicalFF')is True and null.get('clearedOutputBytes')==8
        and null.get('normalReturn')is True and null.get('entryRspRestored')is True)
    caps={};requirements=set();selected=[]
    for route in routes:
        record=by_name[route['wrappedType']];capability,member_count=PLANS[record['typeName']]
        cap=record.get('capabilities',{}).get(capability,{})
        need('same-complete-ordinary-record',record.get('schema')=='endfield.animation-record-components.v1'
            and record.get('status')=='validated-conditional-animation-record-components'
            and record.get('nativeInputs')==pins and record.get('capability')==capability
            and record.get('pending')==[] and record.get('ordinaryOriginalAdapterAdmitted')is True
            and cap.get('wrapperName')==route['wrapperName']and cap.get('typeName')==record['typeName']
            and cap.get('memberCount')==member_count and len(cap.get('orderedReads',[]))==member_count
            and all(cap.get(k)is True for k in('wholeGrammarAdmitted','directWrapperGrammarAdmitted',
                'ordinaryOriginalReadValueAdmitted','ownConcreteGetterSemanticsProved','ownConcreteFactorySemanticsProved')))
        programs=route.get('programs',[])
        need('both-fresh-incompatible-source-paths',len(programs)==2
            and{p.get('source',{}).get('existingBaseWrapper',p.get('source',{}).get('existingIncompatibleWrapper'))for p in programs}=={False,True})
        for program in programs:
            source=program.get('source',{});request=program.get('typedRequest',{});typed=program.get('typedArgument',{})
            need('same-actual-typed-wrapper-child',source.get('tag')==route['tag']and source.get('normalReturn')is True
                and source.get('concreteGrammarAdmitted')is False
                and request.get('typeName')=='MemoryPack.MemoryPackReader'and request.get('methodName')=='ReadPackable'
                and request.get('classArguments')==[]and request.get('methodArguments')==[route['wrapperName']]
                and typed.get('argumentType')==route['wrapperName']and typed.get('concreteTypeKind')==18
                and typed.get('methodDefinition')==request.get('methodSpec',[None])[0])
        conversion=next(c for c in conversions if c['wrapperName']==route['wrapperName'])
        need('same-full-inherited-reference-conversion',conversion.get('holder',{}).get('declaredType')==original
            and conversion['holder'].get('offset')==16 and conversion.get('program',{}).get('normalReturn')is True
            and conversion['program'].get('sameFullReferenceReturned')is True
            and conversion.get('interfaceOrdinal')==conversion['program'].get('interfaceOrdinal'))
        for name,value in record['capabilities'].items():
            need('coherent-shared-child-capability',name not in caps or caps[name]==value,name);caps[name]=value
        requirements.update(record.get('requiredExternalCapabilities',[]))
        selected.append(dict(tag=route['tag'],typeName=record['typeName'],wrapperName=route['wrapperName'],
            memberCount=member_count,childCapability=capability))
    capability=CAPABILITIES[family]
    caps[capability]=dict(typeName=original,wrapperName=proof['wrapperName'],selectedRoutes=sorted(selected,key=lambda r:r['tag']),
        nullable=True,nullMarker=255,tagEncoding='short-byte',wideTagsAdmitted=False,
        declaredUnionEntries=count,allDeclaredTagsCovered=len(selected)==count,
        wholeGrammarAdmitted=True,selectedStoredByteGrammarAdmitted=True,ordinaryBaseAdapterAdmitted=True,
        inheritedBaseConversionsAdmitted=True,compatibleExistingWrapperAdmitted=False,
        collectionParentAdmitted=False,wholeOwnerAdmitted=False)
    return json.loads(json.dumps(dict(schema='endfield.animation-selected-union-components.v1',
        status='validated-conditional-selected-animation-union-components',nativeInputs=pins,family=family,
        capability=capability,capabilities=caps,requiredExternalCapabilities=sorted(requirements),
        containingCollectionAdmitted=False,wholeOwnerAdmitted=False,catalogAdmitted=False,
        proof=dict(unionSource=union_source,records=records),evidenceBoundary=__doc__)))
