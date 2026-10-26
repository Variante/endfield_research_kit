"""Whole selected fallback MC2 with separate dictionary and Tag-list children.

Unity creation, providers, initialized classes, selected canonical callbacks,
successful insertion and disabled collection remain normal-path conditions.
This proves stored syntax, without reconstructing live ScriptableObjects.
"""
import json
from scripts.game_data.memorypack import animation_fallback_set_sources as source
from scripts.game_data.memorypack import animation_fallback_dictionary_components as dictionary

SCHEMA='endfield.animation-fallback-set-components.v1'
CAPABILITY='animation-fallback-montages-positive'
TAGS='skill-root-gameplay-tag-value-list'


def need(key,condition):
    if not condition:raise ValueError('animationFallbackSetComponents.'+key)


def normalized(value):return json.loads(json.dumps(value))


def tag_child(tags,pins,actual):
    """Join a separately fresh list grammar to this caller's actual MethodInfo."""
    cap=tags.get('capabilities',{}).get(TAGS,{});element=tags.get('capabilities',{}).get('skill-root-gameplay-tag',{})
    usage=actual['proof']['tagRequest'];context=tags.get('proof',{}).get('context',{})
    other=context.get('typedRequest',{})
    need('independent-generated-Tag-list',tags.get('schema')=='endfield.skill-gameplay-tag-list-components.v1'
        and tags.get('nativeInputs')==pins and tags.get('status')=='validated-conditional-components'
        and set(tags.get('capabilities',{}))=={TAGS,'skill-root-gameplay-tag'}
        and cap.get('closedListType')==source.TAGS and cap.get('elementType')=='Beyond.Gameplay.Core.GameplayTag'
        and cap.get('elementCapability')=='skill-root-gameplay-tag'and cap.get('elementGrammarAdmitted')is True
        and cap.get('positiveCountsAdmitted')is True and cap.get('collectionCounts')==[-1,0]
        and cap.get('countLimit')==4096 and cap.get('elementValueType')is True and cap.get('managedElementBytes')==4
        and element.get('memberCount')==1 and element.get('positiveWireBytes')==5 and element.get('nullWireBytes')==1
        and element.get('nullReturnsDefaultValue')is True and element.get('rawUnmanagedTagGrammarUsed')is False)
    need('same-actual-closed-MethodInfo-and-list-frontend',all(usage.get(k)==other.get(k)for k in(
        'tag','typeName','methodName','classArguments','methodArguments','methodSpec','methodSpecIndex','usageCellRva','usageRawHex'))
        and cap.get('packableReaderMethodDefinition')==usage['methodSpec'][0]
        and cap.get('packableReaderTargetRva')==actual['proof']['tagSourceTargetRva'])
    return tags['capabilities']


def compose(actual,pins,*,montages,tags):
    source.verify_source(actual,pins);selected=dictionary.validate_component(montages,pins)
    need('same-actual-reference-dictionary-source',montages['proof']['source']==actual['proof']['dictionary'])
    tag_caps=tag_child(tags,pins,actual);caps=dict(selected['capabilities'])
    for name,cap in tag_caps.items():need('coherent-independent-child:'+name,name not in caps or caps[name]==cap);caps[name]=cap
    ordinary=actual['proof']['ordinary']['capabilities']['animation-fallback-montages-null']
    cap=dict(typeName=source.TYPE,wrapperName=actual['wrapperName'],memberCount=2,fieldOrder=['_montages','_npcMontages'],
        wholeGrammarAdmitted=True,positiveGrammarAdmitted=True,ordinaryOriginalReadValueAdmitted=True,
        ordinaryOriginalCallbackAdmitted=True,nullOnlyGrammarAdmitted=False,nullable=True,nullMarker=255,nullWireBytes=1,
        positiveHeader=2,outputReferenceBytes=8,canonicalAdapterTargetRva=ordinary['canonicalAdapterTargetRva'],
        referenceReaderMethodDefinition=ordinary['referenceReaderMethodDefinition'],referenceReaderTargetRva=ordinary['referenceReaderTargetRva'],
        dictionaryCapability=dictionary.CAPABILITY,tagListCapability=TAGS,requiredChildCapabilities=list(sorted(caps)),
        ownTypedFactoryAndAllFourFramesProved=True,opaqueUnityInitializationRequired=True,originalManagedConstructorInvoked=False,
        initiallyNullDictionaryOutputProved=True,bothNamedWholeReferenceTransfersProved=True,
        callbackSelectionConditional=True,runtimeSelectionObserved=False,nodeLimit=16384,runtimeAnimationProved=False)
    from scripts.game_data.memorypack.animation_fallback_set_codec import require_capability
    require_capability(cap);caps[CAPABILITY]=cap
    return normalized(dict(schema=SCHEMA,status='validated-conditional-fallback-set-components',nativeInputs=pins,
        capability=CAPABILITY,capabilities=caps,requiredExternalCapabilities=selected['requiredExternalCapabilities'],
        proof=dict(source=actual,dictionary=montages,tags=tags),wholeOwnerGrammarAdmitted=True,
        publicDecoderActivated=False,runtimeAnimationProved=False,evidenceBoundary=__doc__))


def validate_component(actual,pins):
    need('own-selected-whole-component',actual.get('schema')==SCHEMA and actual.get('nativeInputs')==pins)
    p=actual['proof'];checked=compose(p['source'],pins,montages=p['dictionary'],tags=p['tags'])
    need('same-whole-independent-fallback-components',checked==actual)
    return dict(capability=CAPABILITY,capabilities=checked['capabilities'],requiredExternalCapabilities=checked['requiredExternalCapabilities'])


def bind_root(root,pins,actual):
    from scripts.game_data.memorypack import animation_config_root_sources as roots,animation_fallback_null_sources as null
    roots.verify(root,pins);validate_component(actual,pins)
    null.bind_root(root,pins,actual['proof']['source']['proof']['ordinary'])
    return dict(memberIndex=0,fieldName='_fallbackMontages',capability=CAPABILITY,
        positiveGrammarAdmitted=True,wholeReferenceFieldAndBothParentFramesProved=True)


def derive(image,pins,*,typed_request,source_target,montage,tags):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.animation_custom_dictionary_callbacks import derive_string
    _publication_gate(image,pins)
    actual=source.derive(image,pins,typed_request=typed_request,source_target=source_target)
    montages=dictionary.compose(actual['proof']['dictionary'],pins,key=derive_string(image,pins),montage=montage)
    result=compose(actual,pins,montages=montages,tags=tags)
    _publication_gate(image,pins);return result
