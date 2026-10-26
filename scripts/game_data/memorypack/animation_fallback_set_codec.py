"""Positive MC2 fallback syntax, preserving opaque ScriptableObject semantics."""
from scripts.game_data.memorypack.animation_fallback_set_sources import TYPE
CAPABILITY='animation-fallback-montages-positive'


def need(key,condition):
    if not condition:raise ValueError('animationFallbackSetCodec.'+key)


def require_capability(cap):
    need('whole-own-fallback-MC2',isinstance(cap,dict)and cap.get('typeName')==TYPE
        and cap.get('memberCount')==2 and cap.get('fieldOrder')==['_montages','_npcMontages']
        and all(cap.get(k)is True for k in('wholeGrammarAdmitted','positiveGrammarAdmitted','ordinaryOriginalReadValueAdmitted',
            'ordinaryOriginalCallbackAdmitted','nullable','ownTypedFactoryAndAllFourFramesProved','opaqueUnityInitializationRequired',
            'initiallyNullDictionaryOutputProved','bothNamedWholeReferenceTransfersProved','callbackSelectionConditional'))
        and all(cap.get(k)is False for k in('nullOnlyGrammarAdmitted','originalManagedConstructorInvoked',
            'runtimeSelectionObserved','runtimeAnimationProved'))
        and cap.get('nullMarker')==255 and cap.get('nullWireBytes')==1 and cap.get('positiveHeader')==2
        and cap.get('outputReferenceBytes')==8 and cap.get('dictionaryCapability')=='animation-fallback-reference-dictionary'
        and cap.get('tagListCapability')=='skill-root-gameplay-tag-value-list'and cap.get('nodeLimit')==16384
        and isinstance(cap.get('requiredChildCapabilities'),list)
        and cap['requiredChildCapabilities']==sorted(set(cap['requiredChildCapabilities']))
        and {cap['dictionaryCapability'],cap['tagListCapability']}<=set(cap['requiredChildCapabilities'])
        and all(type(cap.get(k))is int and cap[k]>0 for k in('canonicalAdapterTargetRva','referenceReaderMethodDefinition','referenceReaderTargetRva')))
    return cap


def read(reader,*,depth=0,budget=None):
    from scripts.game_data.memorypack.animation_extra_record_codec import budget_node
    from scripts.game_data.memorypack import animation_fallback_dictionary_codec as dictionary
    from scripts.game_data.memorypack.animation_config_codec import gameplay_tags
    need('bounded-depth',type(depth)is int and 0<=depth<64)
    cap=require_capability(reader.operation.child(CAPABILITY))
    for key in cap['requiredChildCapabilities']:reader.operation.child(key)
    # These complete child gates apply even when the outer object is null.
    dictionary.require_capability(reader.operation.child(cap['dictionaryCapability']))
    budget=budget_node(budget);start=reader.pos;null=reader.peek()==255
    if null:reader.take(1,'fallback-montages.null');fields=[]
    else:
        reader.header(2);fields=[dictionary.read(reader,depth=depth+1,budget=budget),gameplay_tags(reader,budget)]
    out=dict(kind=CAPABILITY,typeName=TYPE,start=start,end=reader.pos,isNull=null,fields=fields,
        opaqueUnityInitializationRequired=True,runtimeAnimationProved=False)
    reader.records.append(out);return out
