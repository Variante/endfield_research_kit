"""Bounded EntityPtr lists; transported managed40 is not serialized wire40."""
from scripts.game_data.codecs.levelscript.entity_ptr_param import decode_entity_ptr_value
from scripts.game_data.memorypack import levelscript_module_entity_list_components as source


def validate(cap):
    need=source.need
    need('exact-list-capability',isinstance(cap,dict)and cap.get('typeName')==source.TYPE
        and cap.get('elementType')==source.ELEMENT and cap.get('elementValueType')is True
        and all(type(cap.get(k))is int and cap[k]==v for k,v in dict(managedElementBytes=40,headerBytes=4,
            countLimit=4096,wireMemberCount=3,positiveElementWireBytes=14,nullElementWireBytes=1,
            nullHeaderDefaultValueBytes=40).items())
        and cap.get('countRange')==[-1,4096]and all(type(n)is int for n in cap['countRange'])
        and cap.get('knownPaddingByteRanges')==[[1,8],[20,24]]and cap.get('opaqueRuntimeStorageRanges')==[[24,40]]
        and cap.get('selectedBarrierValueOffsets')==[24]
        and all(cap.get(k)is True for k in('nullable','positiveCountsAdmitted','elementGrammarAdmitted','wholeGrammarAdmitted',
            'freshListsAdmitted','reusedListsRequireCapacityAtLeastCount','actualCallbackEqualsProvedChildRequired'))
        and all(cap.get(k)is False for k in('runtimeReferenceLayoutAdmitted','completeRuntimePaddingMapAdmitted',
            'runtimeEntityResolutionProved','liveFormatterSelectionObserved','parentFieldAdmitted','wholeOwnerAdmitted'))
        and all(type(cap.get(k))is int and cap[k]>0 for k in('canonicalValueAdapterTargetRva',
            'actualSlotDispatchTargetRva','packableReaderMethodDefinition','packableReaderTargetRva'))
        and isinstance(cap.get('sourceMethodSpec'),list)and len(cap['sourceMethodSpec'])==3
        and all(type(n)is int for n in cap['sourceMethodSpec'])
        and cap['sourceMethodSpec'][0]==cap['packableReaderMethodDefinition']
        and'referenceLaneOffsets'not in cap and'paddingByteRanges'not in cap)
    carrier=cap.get('closedCarrier',{});arguments=carrier.get('classArguments',[])
    need('exact-list-nominal-carrier',carrier.get('name')==source.TYPE and len(arguments)==1
        and arguments[0].get('name')==source.ELEMENT)
    raw=bytes.fromhex(arguments[0].get('rawHex',''))
    need('exact-value17-carrier',len(raw)==16 and raw[10:12]==bytes((17,128)))


def read(reader,field,cap,*,budget=None):
    validate(cap)
    if budget is None:budget={'remaining':16384}
    if not(isinstance(budget,dict)and set(budget)=={'remaining'}and type(budget['remaining'])is int
        and 0<budget['remaining']<=16384):reader.refuse(field,'module-Entity-list-budget',budget)
    budget['remaining']-=1;start=reader.offset;count=reader.number('<i',field+'.count')
    if not -1<=count<=4096:reader.refuse(field,'module-Entity-list-count',count)
    reader.need(max(count,0),field+'.elements');rows=[]
    for i in range(max(count,0)):
        path=field+f'[{i}]'
        if budget['remaining']<=0:reader.refuse(path,'module-Entity-list-budget',0)
        budget['remaining']-=1;at=reader.offset
        result=decode_entity_ptr_value(reader.data,at)
        if result is None:reader.refuse(path,'module-Entity-MC3-or-FF-and-complete-extent')
        value,end=result;reader.offset=end
        rows.append(dict(startOffset=at,endOffset=end,logicId=str(value['logicId']),slotId=value['slotId'],
            useSlotId=value['useSlotId'],useSlotIdRawByte=value['useSlotIdRawByte'],defaultValue=value['constantWasNull'],
            runtimeObjectPtrSerialized=False))
    return dict(startOffset=start,endOffset=reader.offset,count=count,rows=None if count==-1 else rows)
