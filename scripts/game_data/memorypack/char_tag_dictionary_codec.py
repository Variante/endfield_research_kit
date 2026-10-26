"""Ordinary string/GameplayTag entries under their own selected callback.

The signed four-byte dictionary header is independent of Char's static
one-byte marker dictionaries. GameplayTag values use the independently selected
MC1/default4 callback; their managed width never implies a raw four-byte wire.
"""
import struct

TYPE='System.Collections.Generic.Dictionary`2<string,Beyond.Gameplay.Core.GameplayTag>'
CAPABILITY='char-string-gameplay-tag-dictionary'
TAG='Beyond.Gameplay.Core.GameplayTag'
TAG_CAPABILITY='char-dictionary-gameplay-tag-value'


def need(check,condition):
    if not condition:raise ValueError('charTagDictionaryCodec.'+check)


def require_capability(capability,cap):
    need('exact-selected-dictionary',capability==CAPABILITY and isinstance(cap,dict)and cap.get('typeName')==TYPE
        and cap.get('keyType')=='string'and cap.get('valueType')==TAG
        and all(type(cap.get(k))is int and cap[k]>0 for k in
            ('packableReaderMethodDefinition','packableReaderTargetRva','dictionaryFormatterMethodDefinition',
             'dictionaryFormatterTargetRva','keyCallbackTargetRva','valueCallbackTargetRva'))
        and all(type(cap.get(k))is int and cap[k]==v for k,v in
            (('headerBytes',4),('keyWireBytes',4),('managedValueBytes',4),('countLimit',4096),('nodeLimit',16384))))
    need('own-ordinary-positive-framing',cap.get('countRange')==[-1,4096]
        and all(type(n)is int for n in cap['countRange'])and cap.get('valueWireProfile')=='generated-gameplay-tag-MC1'
        and cap.get('valueCapability')==TAG_CAPABILITY
        and all(cap.get(k)is True for k in('wholeGrammarAdmitted','positiveCountsAdmitted','nullable',
            'initiallyNullOutputRequired','callbackSelectionConditional','orderedEntriesPreserved','duplicateKeysPreserved'))
        and all(cap.get(k)is False for k in('rawUnmanagedTagGrammarUsed','closedPointerEquivalenceProved',
            'actualRuntimeSelectionObserved','finalMutableDictionaryReconstructed','parentFieldAdmitted','wholeOwnerAdmitted')))
    children=cap.get('requiredChildCapabilities',{});child=children.get(TAG_CAPABILITY,{})
    need('whole-generated-Tag-callback',isinstance(children,dict)and bool(children)
        and child.get('typeName')==TAG and child.get('memberCount')==1 and child.get('managedBytes')==4
        and child.get('positiveWireBytes')==5 and child.get('nullWireBytes')==1
        and child.get('nullable')is True and child.get('nullMarker')==255 and child.get('nullReturnsDefaultValue')is True
        and child.get('rawUnmanagedTagGrammarUsed')is False and child.get('wholeGrammarAdmitted')is True
        and child.get('canonicalAdapterTargetRva')==cap['valueCallbackTargetRva'])
    external=cap.get('requiredExternalCapabilities')
    need('explicit-pool-capability',isinstance(external,list)and external==sorted(set(external))
        and'byte-payload'in external and all(isinstance(k,str)and k for k in external))
    return cap


def read(reader,capability,*,depth=0,budget=None):
    need('bounded-depth',type(depth)is int and 0<=depth<64)
    cap=require_capability(capability,reader.operation.child(capability))
    for name,child in cap['requiredChildCapabilities'].items():need('same-child-before-count:'+name,reader.operation.child(name)==child)
    for name in cap['requiredExternalCapabilities']:
        child=reader.operation.child(name)
        if name=='byte-payload':need('selected-pool-before-count',child.get('wholeGrammarAdmitted')is True
            and child.get('encoding')=='int32-pool-index'and child.get('emptyIndex')==-1 and child.get('nullIndex')==-2)
    start=reader.pos;need('complete-signed-count',start+4<=reader.limit);count=struct.unpack_from('<i',reader.data,start)[0]
    need('bounded-count-before-consumption',-1<=count<=4096)
    need('minimum-entry-bytes',start+4+max(count,0)*5<=reader.limit)
    budget=dict(remaining=16384)if budget is None else budget
    need('shared-budget-before-count',isinstance(budget,dict)and set(budget)=={'remaining'}
        and type(budget['remaining'])is int and 1+max(count,0)*2<=budget['remaining']<=16384)
    budget['remaining']-=1+max(count,0)*2;reader.take(4,capability+'.count');entries=[]
    for index in range(max(count,0)):
        at=reader.pos;raw=reader.take(4,capability+'.key');pool_index=struct.unpack('<i',raw)[0]
        key=reader.operation.pool_index(pool_index);need('nonnull-normal-insertion-key',isinstance(key,str))
        value_start=reader.pos;marker=reader.peek();need('generated-Tag-MC1-or-FF',marker in(1,255))
        reader.take(1,capability+'.GameplayTag.memberCount');bits=bytes(4)if marker==255 else reader.take(4,capability+'.GameplayTag.tagId')
        value=dict(typeName=TAG,start=value_start,end=reader.pos,isDefault=marker==255,rawHex=bits.hex(),tagId=struct.unpack('<i',bits)[0],
            wrapperFramingUsed=True,rawUnmanagedTagGrammarUsed=False)
        entries.append(dict(index=index,start=at,end=reader.pos,poolIndex=pool_index,key=key,keyRawHex=raw.hex(),value=value))
    result=dict(kind=capability,typeName=TYPE,start=start,end=reader.pos,count=count,isNull=count==-1,entries=entries,
        serializedOrderPreserved=True,duplicateKeysPreserved=True,finalMutableDictionaryReconstructed=False,
        containingOwnerClaimed=False,runtimeAnimationProved=False)
    reader.records.append(result);return result
