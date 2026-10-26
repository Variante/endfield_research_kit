"""Finite ordered ExtraData dictionary entries on an authenticated cursor."""
import struct

from scripts.game_data.memorypack.animation_extra_dictionary_sources import TYPES,DOMAINS
from scripts.game_data.memorypack.animation_extra_dictionary_components import CAPABILITIES


def need(check,condition):
    if not condition:raise ValueError('animationExtraDictionaryCodec.'+check)


def require_capability(cap,typename):
    need('finite-owned-dictionary',typename in TYPES and isinstance(cap,dict))
    key,value=TYPES[typename];profile,key_output=DOMAINS[(key,value)]
    key_wire=4 if key=='string'else key_output
    need('exact-static-source-and-wire-domain',cap.get('typeName')==typename
        and(cap.get('keyType'),cap.get('valueType'))==(key,value)
        and cap.get('valueStorageKind')==('value8'if profile=='enum1-value8'else'reference8')
        and cap.get('resultAbi')=='void-byref-reference8'and cap.get('referenceBytes')==8
        and cap.get('keyWireBytes')==key_wire and cap.get('countBytes')==4
        and cap.get('countEncoding')=='signed-int32'and cap.get('nullMarker')==255
        and cap.get('nullWireBytes')==1 and cap.get('positiveMarkerDomain')==[0,254]
        and type(cap.get('countLimit'))is int and 3<=cap['countLimit']<=4096
        and cap.get('nodeLimit')==16384
        and all(type(cap.get(k))is int and cap[k]>0 for k in('staticReaderMethodDefinition','staticReaderTargetRva',
            'valueCallbackTargetRva'))
        and all(cap.get(k)is True for k in('wholeGrammarAdmitted','staticOutReferenceAdmitted','nullable',
            'positiveCountsAdmitted','callbackSelectionConditional','initiallyNullOutputRequired',
            'orderedEntriesPreserved','duplicateKeysPreserved'))
        and all(cap.get(k)is False for k in('ordinaryOriginalReadValueAdmitted','nativePositiveHeaderOneEnforced',
            'clearExistingDictionaryAdmitted','finalMutableDictionaryReconstructed','actualRuntimeSelectionObserved',
            'parentFieldAdmitted','wholeOwnerAdmitted')))
    callback=cap.get('keyCallback',{})
    need('own-exact-key-callback',callback.get('typeName')==key and callback.get('wireBytes')==key_wire
        and callback.get('callbackSlot')==5 and callback.get('actualRuntimeSelectionObserved')is False
        and all(type(callback.get(k))is int and callback[k]>0 for k in('callbackMethodDefinition','callbackTargetRva'))
        and isinstance(callback.get('conditions'),list)and bool(callback['conditions']))
    if key=='string':
        need('selected-pooled-string-key',callback.get('encoding')=='int32-pool-index'
            and callback.get('outputBytes')==8 and callback.get('emptyIndex')==-1 and callback.get('nullIndex')==-2)
    else:
        need('own-nominal-enum-key',type(callback.get('typeDefinition'))is int and callback['typeDefinition']>=0
            and callback.get('readerByref')is True and callback.get('outputByref')is True
            and callback.get('parentOrCollectionGrammarAdmitted')is False)
    children=cap.get('requiredChildCapabilities');primary=cap.get('valueCapability')
    need('exact-independently-required-value',isinstance(children,dict)and primary in children
        and all(isinstance(k,str)and isinstance(v,dict)for k,v in children.items()))
    child=children[primary]
    if value=='string':
        need('own-pooled-string-value',primary=='byte-payload'and child.get('wholeGrammarAdmitted')is True
            and child.get('encoding')=='int32-pool-index'and child.get('emptyIndex')==-1 and child.get('nullIndex')==-2)
    else:
        need('own-complete-value-record',child.get('typeName')==value
            and child.get('valueStorageKind')==cap['valueStorageKind']
            and child.get('wholeGrammarAdmitted')is True
            and child.get('ordinaryOriginalReadValueAdmitted')is (profile!='enum1-value8')
            and(profile!='enum1-value8'or child.get('ordinaryOriginalCallbackAdmitted')is True)
            and child.get('canonicalAdapterTargetRva')==cap['valueCallbackTargetRva']
            and type(child.get('formatterDeserializeMethodDefinition'))is int and child['formatterDeserializeMethodDefinition']>0)
    requirements=cap.get('requiredExternalCapabilities')
    need('explicit-external-child-set',isinstance(requirements,list)and requirements==sorted(set(requirements))
        and all(isinstance(k,str)and bool(k)for k in requirements)
        and('byte-payload'in requirements if key=='string'or value=='string'else True))
    return cap


def read(reader,typename,*,budget=None,depth=0):
    need('bounded-dictionary-depth',type(depth)is int and 0<=depth<64 and typename in CAPABILITIES)
    capability=CAPABILITIES[typename];cap=require_capability(reader.operation.child(capability),typename)
    for name,child in cap['requiredChildCapabilities'].items():
        need('same-independent-child:'+name,reader.operation.child(name)==child)
    for name in cap['requiredExternalCapabilities']:
        child=reader.operation.child(name)
        if name=='byte-payload':
            need('selected-pooled-string-operation',child.get('wholeGrammarAdmitted')is True
                and child.get('encoding')=='int32-pool-index'and child.get('emptyIndex')==-1 and child.get('nullIndex')==-2)
    if budget is None:budget=dict(remaining=cap['nodeLimit'])
    need('literal-shared-node-budget',isinstance(budget,dict)and set(budget)=={'remaining'}
        and type(budget['remaining'])is int and 0<=budget['remaining']<=cap['nodeLimit'])
    start=reader.pos;marker=reader.peek();null=marker==255;count=None
    if not null:
        need('complete-marker-and-count',start+5<=reader.limit)
        count=struct.unpack_from('<i',reader.data,start+1)[0]
        need('bounded-nonnegative-count-before-consumption',0<=count<=cap['countLimit'])
    required=1+(0 if null else count)
    need('shared-node-budget-before-consumption',required<=budget['remaining']);budget['remaining']-=required
    reader.take(1 if null else 5,capability+'.marker-count');entries=[]
    for index in range(0 if null else count):
        at=reader.pos;width=cap['keyWireBytes'];need('complete-key-before-consumption',at+width<=reader.limit)
        raw=bytes(reader.data[at:at+width]);key=int.from_bytes(raw,'little',signed=width==4)
        extra={}
        if cap['keyType']=='string':
            pool_index=key;key=reader.operation.pool_index(pool_index)
            need('nonnull-selected-string-key',isinstance(key,str));extra['poolIndex']=pool_index
        reader.take(width,capability+'.key');value_start=reader.pos
        if cap['valueType']=='string':
            need('complete-value-pool-index',reader.pos+4<=reader.limit)
            pool_index=struct.unpack_from('<i',reader.data,reader.pos)[0]
            value=reader.operation.pool_index(pool_index)
            reader.take(4,capability+'.value-pool-index');extra['valuePoolIndex']=pool_index
        else:
            need('selected-extra-record-cursor',callable(getattr(reader,'extra_record',None)))
            value=reader.extra_record(cap['valueCapability'],depth=depth+1,budget=budget)
        entries.append(dict(index=index,start=at,end=reader.pos,key=key,keyRawHex=raw.hex(),
            valueStart=value_start,value=value,**extra))
    row=dict(kind=capability,typeName=typename,start=start,end=reader.pos,isNull=null,marker=marker,count=count,
        entries=entries,serializedOrderPreserved=True,duplicateKeysPreserved=True,
        finalMutableDictionaryReconstructed=False,containingOwnerClaimed=False,runtimeAnimationProved=False)
    reader.records.append(row);return row
