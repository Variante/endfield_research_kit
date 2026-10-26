"""Compose the six own idle-condition children below their own abstract union."""
import json
from scripts.game_data.memorypack import animation_idle_condition_sources as source

SCHEMA='endfield.animation-idle-condition-components.v1'
CAPABILITY='animation-idle-condition-union'


def need(check,condition):
    if not condition:raise ValueError('animationIdleConditionComponents.'+check)


def compose(transport,records):
    from scripts.game_data.memorypack.animation_extra_record_components import validate_component,record_key
    pins=transport.get('nativeInputs');source.replay_transport(transport,pins)
    need('all-six-independent-concrete-children',isinstance(records,list)and len(records)==6
        and{r.get('typeName')for r in records}==set(source.TYPES))
    by_name={r['typeName']:r for r in records};caps={};required=set();routes=[]
    for selected in transport['programs']:
        record=by_name[selected['wrappedType']];own=validate_component(record,pins);key=record_key(selected['wrappedType'])
        child=own['capabilities'][key]
        need('own-ordinary-complete-record',own['capability']==key and child.get('typeName')==selected['wrappedType']
            and child.get('wrapperName')==selected['wrapperName']and child.get('wholeGrammarAdmitted')is True
            and child.get('ordinaryOriginalReadValueAdmitted')is True and child.get('ordinaryOriginalCallbackAdmitted')is True
            and child.get('directWrapperGrammarAdmitted')is True and child.get('valueStorageKind')=='reference8')
        for name,cap in own['capabilities'].items():
            need('coherent-owned-child:'+name,name not in caps or caps[name]==cap);caps[name]=cap
        required.update(own['requiredExternalCapabilities'])
        routes.append(dict(tag=selected['tag'],typeName=selected['wrappedType'],wrapperName=selected['wrapperName'],
            memberCount=child['memberCount'],childCapability=key))
    adapter=transport['adapter'];face,=transport['pair']['composition']['interfaces']
    caps[CAPABILITY]=dict(typeName=source.TYPE,wrapperName=transport['wrapperName'],wholeGrammarAdmitted=True,
        selectedRoutes=routes,declaredUnionEntries=6,allDeclaredTagsCovered=True,nullable=True,nullMarker=255,
        tagEncoding='short-byte',wideTagsAdmitted=False,ordinaryBaseAdapterAdmitted=True,
        ordinaryOriginalReadValueAdmitted=True,ordinaryOriginalCallbackAdmitted=True,
        originalTypeDefinition=transport['nominalOriginal']['typeDefinition'],valueStorageKind='reference8',
        canonicalAdapterTargetRva=adapter['callbackBinding']['canonicalTargetRva'],
        formatterDeserializeMethodDefinition=face['formatterDeserializeMethodIndex'],
        inheritedBaseConversionsAdmitted=True,selectedStoredByteGrammarAdmitted=True,
        compatibleExistingWrapperAdmitted=False,collectionParentAdmitted=False,wholeOwnerAdmitted=False)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-animation-idle-condition-components',
        nativeInputs=pins,capability=CAPABILITY,capabilities=caps,requiredExternalCapabilities=sorted(required-set(caps)),
        proof=dict(transport=transport,records=records),parentFieldAdmitted=False,wholeOwnerAdmitted=False)))


def validate_component(component,pins):
    need('own-nominal-components',component.get('schema')==SCHEMA
        and component.get('status')=='validated-conditional-animation-idle-condition-components'
        and component.get('nativeInputs')==pins and component.get('parentFieldAdmitted')is False and component.get('wholeOwnerAdmitted')is False)
    p=component['proof'];checked=compose(p['transport'],p['records'])
    need('same-full-composition',checked==component)
    return {key:checked[key]for key in('capability','capabilities','requiredExternalCapabilities')}
