"""Bounded ordered fallback reference-dictionary syntax on an active cursor."""
import struct
from scripts.game_data.memorypack.animation_fallback_dictionary_sources import TYPE,VALUE
CAPABILITY='animation-fallback-reference-dictionary'


def need(key,condition):
    if not condition:raise ValueError('animationFallbackDictionaryCodec.'+key)


def require_capability(cap):
    need('whole-own-dictionary-capability',isinstance(cap,dict)and cap.get('typeName')==TYPE
        and cap.get('keyType')=='string'and cap.get('valueType')==VALUE
        and cap.get('resultAbi')=='void-byref-reference8'and cap.get('referenceBytes')==8
        and all(cap.get(k)is True for k in('wholeGrammarAdmitted','nullable','initiallyNullOutputRequired',
            'orderedEntriesPreserved','duplicateKeysPreserved','callbackSelectionConditional'))
        and all(cap.get(k)is False for k in('nullStringKeyAdmitted','existingOutputReuseAdmitted',
            'finalMutableDictionaryReconstructed','runtimeSelectionObserved','parentFieldAdmitted','wholeOwnerAdmitted'))
        and cap.get('nullMarker')==255 and cap.get('nullWireBytes')==1 and cap.get('positiveMarkerDomain')==[0,254]
        and cap.get('countEncoding')=='signed-int32'and cap.get('countBytes')==4 and cap.get('minimumCount')==0
        and type(cap.get('countLimit'))is int and 3<=cap['countLimit']<=4096 and cap.get('nodeLimit')==16384
        and cap.get('keyWireBytes')==4 and cap.get('keyEncoding')=='int32-pool-index'
        and cap.get('valueCapability')=='animation-montage-selected-union'
        and all(type(cap.get(k))is int and cap[k]>0 for k in('staticReaderMethodDefinition','sourceTargetRva',
            'keyCallbackTargetRva','valueCallbackTargetRva')))
    children=cap.get('requiredChildCapabilities',{});union=children.get(cap['valueCapability'],{})
    need('whole-independent-selected-Montage',bool(children)and union.get('typeName')==VALUE
        and union.get('wholeGrammarAdmitted')is True and union.get('allDeclaredTagsCovered')is True
        and union.get('declaredUnionEntries')==2 and union.get('selectedStoredByteGrammarAdmitted')is True)
    need('explicit-pooled-string-dependency',isinstance(cap.get('requiredExternalCapabilities'),list)
        and cap['requiredExternalCapabilities']==sorted(set(cap['requiredExternalCapabilities']))
        and 'byte-payload'in cap['requiredExternalCapabilities'])
    return cap


def read(reader,*,depth=0,budget=None):
    need('bounded-depth',type(depth)is int and 0<=depth<64)
    cap=require_capability(reader.operation.child(CAPABILITY))
    for name,expected in cap['requiredChildCapabilities'].items():
        need('same-independent-child:'+name,reader.operation.child(name)==expected)
    for name in cap['requiredExternalCapabilities']:
        child=reader.operation.child(name)
        if name=='byte-payload':need('active-shared-pool',child.get('wholeGrammarAdmitted')is True
            and child.get('encoding')=='int32-pool-index'and child.get('emptyIndex')==-1 and child.get('nullIndex')==-2)
    if budget is None:budget=dict(remaining=cap['nodeLimit'])
    need('shared-dict-budget',isinstance(budget,dict)and set(budget)=={'remaining'}
        and type(budget['remaining'])is int and 0<=budget['remaining']<=cap['nodeLimit'])
    start=reader.pos;marker=reader.peek();null=marker==255;count=None
    if not null:
        need('complete-marker-and-count',start+5<=reader.limit)
        count=struct.unpack_from('<i',reader.data,start+1)[0]
        need('bounded-count-before-consumption',0<=count<=cap['countLimit'])
    nodes=1+(0 if null else count);need('budget-before-consumption',nodes<=budget['remaining']);budget['remaining']-=nodes
    reader.take(1 if null else 5,'fallback-reference-dictionary.header');entries=[]
    for index in range(0 if null else count):
        at=reader.pos;need('complete-key',at+4<=reader.limit)
        raw=bytes(reader.data[at:at+4]);pool_index=struct.unpack('<i',raw)[0];key=reader.operation.pool_index(pool_index)
        need('nonnull-normal-string-key',isinstance(key,str));reader.take(4,'fallback-reference-dictionary.key')
        value=reader.selected_union(cap['valueCapability'],depth=depth+1)
        entries.append(dict(index=index,start=at,end=reader.pos,key=key,poolIndex=pool_index,keyRawHex=raw.hex(),value=value))
    row=dict(kind=CAPABILITY,typeName=TYPE,start=start,end=reader.pos,isNull=null,marker=marker,count=count,entries=entries,
        serializedOrderPreserved=True,duplicateKeysPreserved=True,finalMutableDictionaryReconstructed=False,
        runtimeAnimationProved=False)
    reader.records.append(row);return row
