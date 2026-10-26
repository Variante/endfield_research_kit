"""Bounded ordered Char static dictionaries on the selected Char cursor."""
import struct


def need(check,condition):
    if not condition:raise ValueError('charStaticDictionaryCodec.'+check)


def require_capability(capability,cap):
    from scripts.game_data.memorypack.char_static_dictionary_components import CAPABILITIES
    from scripts.game_data.memorypack.char_perform_positive_dictionary_sources import DOMAINS,OWNER
    matches=[(field,key,value)for field,(_,key,value)in DOMAINS.items()
        if CAPABILITIES[OWNER+'<'+key+','+value+'>']==capability]
    need('finite-owned-capability',len(matches)==1);_,key,value=matches[0]
    need('exact-static-reference-identity',isinstance(cap,dict)and cap.get('typeName')==OWNER+'<'+key+','+value+'>'
        and(cap.get('keyType'),cap.get('valueType'))==(key,value)and cap.get('resultAbi')=='void-byref-reference8'
        and all(type(cap.get(k))is int and cap[k]>0 for k in('staticReaderMethodDefinition','sourceTargetRva','valueCallbackTargetRva'))
        and all(type(cap.get(k))is int and cap[k]==v for k,v in
            (('referenceBytes',8),('nullMarker',255),('nullWireBytes',1),('countBytes',4),('keyWireBytes',4),('nodeLimit',16384))))
    need('bounded-positive-selected-wire',type(cap.get('countLimit'))is int and 3<=cap['countLimit']<=4096
        and cap.get('countEncoding')=='signed-int32'and cap.get('positiveMarkerDomain')==[0,254]
        and all(type(n)is int for n in cap['positiveMarkerDomain'])
        and all(cap.get(k)is True for k in('wholeGrammarAdmitted','staticOutReferenceAdmitted','nullable','positiveCountsAdmitted',
            'callbackSelectionConditional','initiallyNullOutputRequired','orderedEntriesPreserved','duplicateKeysPreserved'))
        and all(cap.get(k)is False for k in('nativePositiveHeaderOneEnforced','clearExistingDictionaryAdmitted',
            'finalMutableDictionaryReconstructed','actualRuntimeSelectionObserved','parentFieldAdmitted','wholeOwnerAdmitted')))
    callback=cap.get('keyCallback',{})
    need('independently-typed-key-callback',callback.get('typeName')==key
        and callback.get('wireBytes')==4 and callback.get('outputBytes')==(4 if key=='uint'else 8)
        and callback.get('callbackSlot')==5 and callback.get('actualRuntimeSelectionObserved')is False
        and all(type(callback.get(k))is int and callback[k]>0 for k in('callbackMethodDefinition','callbackTargetRva')))
    children=cap.get('requiredChildCapabilities');primary=cap.get('valueCapability')
    need('complete-own-reference-value-map',isinstance(children,dict)and isinstance(primary,str)and primary in children)
    from scripts.game_data.memorypack.char_record_codec import require_capability as record
    child=children[primary];record(child,ordinary=True)
    need('exact-value-child',child.get('typeName')==value and child.get('canonicalAdapterTargetRva')==cap['valueCallbackTargetRva']
        and child.get('valueStorageKind')=='reference8'and child.get('ordinaryOriginalCallbackAdmitted')is True)
    required=cap.get('requiredExternalCapabilities')
    need('explicit-external-capabilities',isinstance(required,list)and required==sorted(set(required))
        and all(isinstance(k,str)and k for k in required)and(key!='string'or'byte-payload'in required)
        and isinstance(cap.get('conditions'),list)and bool(cap['conditions']))
    return cap


def read(reader,capability,*,depth=0,budget=None):
    need('bounded-depth',type(depth)is int and 0<=depth<64)
    cap=require_capability(capability,reader.operation.child(capability))
    for name,child in cap['requiredChildCapabilities'].items():need('same-child-before-marker:'+name,reader.operation.child(name)==child)
    for name in cap['requiredExternalCapabilities']:
        selected=reader.operation.child(name)
        if name=='byte-payload':need('selected-pooled-string-operation',selected.get('wholeGrammarAdmitted')is True
            and selected.get('encoding')=='int32-pool-index'and selected.get('emptyIndex')==-1 and selected.get('nullIndex')==-2)
    if budget is None:budget=dict(remaining=cap['nodeLimit'])
    need('shared-node-budget',isinstance(budget,dict)and set(budget)=={'remaining'}
        and type(budget['remaining'])is int and 0<=budget['remaining']<=cap['nodeLimit'])
    start=reader.pos;marker=reader.peek();null=marker==255;count=None
    if not null:
        need('complete-header',start+5<=reader.limit);count=struct.unpack_from('<i',reader.data,start+1)[0]
        need('bounded-nonnegative-count',0<=count<=cap['countLimit'])
    nodes=1+(0 if null else count);need('node-budget-before-consumption',nodes<=budget['remaining']);budget['remaining']-=nodes
    reader.take(1 if null else 5,capability+'.marker-count');entries=[]
    for index in range(0 if null else count):
        at=reader.pos;need('complete-key',at+4<=reader.limit);raw=bytes(reader.data[at:at+4]);extra={}
        key=struct.unpack('<I'if cap['keyType']=='uint'else'<i',raw)[0]
        if cap['keyType']=='string':
            extra['poolIndex']=key;key=reader.operation.pool_index(key);need('nonnull-string-key',isinstance(key,str))
        reader.take(4,capability+'.key');value_start=reader.pos
        need('selected-record-cursor',callable(getattr(reader,'record',None)))
        value=reader.record(cap['valueCapability'],depth=depth+1,budget=budget)
        entries.append(dict(index=index,start=at,end=reader.pos,key=key,keyRawHex=raw.hex(),valueStart=value_start,value=value,**extra))
    row=dict(kind=capability,typeName=cap['typeName'],start=start,end=reader.pos,isNull=null,marker=marker,count=count,
        entries=entries,serializedOrderPreserved=True,duplicateKeysPreserved=True,finalMutableDictionaryReconstructed=False,
        containingOwnerClaimed=False,runtimeAnimationProved=False)
    reader.records.append(row);return row
