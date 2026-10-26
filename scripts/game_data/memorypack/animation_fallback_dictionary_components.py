"""Own reference dictionary joined to independent pooled key and Montage grammar.

The exact SerializeReferenceDictionary source requires a fresh null output.
Its actual dispatcher is replayed under each independent selected callback;
sharing a helper address never establishes callback or grammar equivalence.
"""
import json
from scripts.game_data.memorypack import animation_fallback_dictionary_sources as source
from scripts.game_data.memorypack import animation_custom_dictionary_components as children
from scripts.game_data.memorypack import animation_custom_dictionary_callbacks as callbacks

SCHEMA='endfield.animation-fallback-reference-dictionary-components.v1'
CAPABILITY='animation-fallback-reference-dictionary'
WIRE='animation-fallback-reference-dictionary'


def need(key,condition):
    if not condition:raise ValueError('animationFallbackDictionaryComponents.'+key)


def normalized(value):return json.loads(json.dumps(value))


def dispatch_programs(actual,key,montage,pins):
    """Replay this actual helper, using independently selected callback symbols."""
    from scripts.game_data.il2cpp.formatter_value_paths import BytesPath,deserialize_slot
    from scripts.game_data.memorypack.reference_adapter_sources import dispatch
    base=source.verify_source(actual,pins);children.replay_callback(key,pins)
    need('own-independent-string-key',key.get('typeName')=='string')
    _,_,target,_=children.montage_child(montage,pins)
    helper=actual['proof']['helpers']['dispatch']
    need('same-actual-dispatch-helper',helper['targetRva']==actual['proof']['symbolRvas']['dispatch'])
    raw=callbacks.regions(helper['windows'],helper['regions'],base,'fallback-selected-dispatch')
    entry=base+helper['targetRva'];g=BytesPath(raw,entry)
    g.take('48895c2408','55','56','57','4154','4155','4156','4157','4883ec70','4d8be9','4d8bf8','488bfa','0fb7d9','488b0a')
    prepare=g.relative('e8')
    string=deserialize_slot(raw,entry,prepare=prepare,callback=base+key['callbackTargetRva'])
    adapter=montage['proof']['unionSource']['families']['montage']['adapter']
    binding=adapter['callbackBinding'];routes=adapter['canonicalRoutes']
    need('own-independent-canonical-Montage-symbols',adapter.get('typeName')==source.VALUE
        and adapter.get('nativeInputs')==pins and binding.get('canonicalTargetRva')==target
        and routes.get('symbolRvas',{}).get('main')==target
        and binding.get('actualCallbackEqualsCanonicalRequired')is True
        and binding.get('runtimeSelectionObserved')is False)
    symbols={k:base+v for k,v in routes['symbolRvas'].items()}
    value=[dispatch(raw,entry,symbols,**options)for options in(
        {},dict(create=False),dict(wrapper_null=True),dict(create=False,wrapper_null=True),dict(null=True))]
    return normalized(dict(sourceTargetRva=helper['targetRva'],keyCallbackTargetRva=key['callbackTargetRva'],
        valueCallbackTargetRva=target,keyProgram=string,valuePrograms=value,
        actualPointerAliasInferred=False,callbackSelectionConditional=True,runtimeSelectionObserved=False))


def compose(actual,pins,*,key,montage):
    source.verify_source(actual,pins);children.replay_callback(key,pins)
    caps,value,callback,external=children.montage_child(montage,pins)
    dispatch=dispatch_programs(actual,key,montage,pins)
    required=sorted(set(external)|{'byte-payload'})
    cap=dict(typeName=source.TYPE,keyType='string',valueType=source.VALUE,
        staticReaderMethodDefinition=actual['staticReaderMethodDefinition'],sourceTargetRva=actual['sourceTargetRva'],
        resultAbi='void-byref-reference8',referenceBytes=8,wholeGrammarAdmitted=True,
        nullable=True,nullMarker=255,nullWireBytes=1,positiveMarkerDomain=[0,254],
        countEncoding='signed-int32',countBytes=4,minimumCount=0,countLimit=actual['proof']['induction']['maxCount'],nodeLimit=16384,
        keyWireBytes=4,keyEncoding='int32-pool-index',nullStringKeyAdmitted=False,
        keyCallbackTargetRva=key['callbackTargetRva'],valueCallbackTargetRva=callback,valueCapability=value,
        requiredChildCapabilities=caps,requiredExternalCapabilities=required,
        initiallyNullOutputRequired=True,existingOutputReuseAdmitted=False,
        orderedEntriesPreserved=True,duplicateKeysPreserved=True,finalMutableDictionaryReconstructed=False,
        callbackSelectionConditional=True,runtimeSelectionObserved=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False)
    from scripts.game_data.memorypack.animation_fallback_dictionary_codec import require_capability
    require_capability(cap)
    result=normalized(dict(schema=SCHEMA,status='validated-conditional-fallback-reference-dictionary-components',
        nativeInputs=pins,capability=CAPABILITY,capabilities={**caps,CAPABILITY:cap},requiredExternalCapabilities=required,
        proof=dict(source=actual,key=key,montage=montage,dispatch=dispatch),parentFieldAdmitted=False,wholeOwnerAdmitted=False))
    return result


def validate_component(actual,pins):
    need('own-selected-component',actual.get('schema')==SCHEMA and actual.get('nativeInputs')==pins)
    p=actual['proof'];checked=compose(p['source'],pins,key=p['key'],montage=p['montage'])
    need('same-complete-source-key-value-join',checked==actual)
    return dict(capability=CAPABILITY,capabilities=checked['capabilities'],requiredExternalCapabilities=checked['requiredExternalCapabilities'])


def derive(image,pins,*,typed_request,source_target,montage,count_limit=4096):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    _publication_gate(image,pins)
    actual=source.derive(image,pins,typed_request=typed_request,source_target=source_target,count_limit=count_limit)
    key=callbacks.derive_string(image,pins)
    result=compose(actual,pins,key=key,montage=montage)
    _publication_gate(image,pins);return result
