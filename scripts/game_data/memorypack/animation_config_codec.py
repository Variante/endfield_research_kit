"""MC15 AnimationConfig cursor using the explicit current-animation operation."""
import struct
from scripts.game_data.memorypack.animation_extra_record_codec import AnimationExtraReader
from scripts.game_data.memorypack import animation_config_components as component


def need(check,condition):
    if not condition:raise ValueError('animationConfigCodec.'+check)


def require_capability(cap):
    from scripts.game_data.memorypack.animation_config_root_programs import FIELDS
    need('all-fifteen-field-owner',cap.get('memberCount')==15 and cap.get('orderedFieldNames')==list(FIELDS)
        and cap.get('wholeGrammarAdmitted')is True and cap.get('allFifteenFieldsAdmitted')is True
        and cap.get('wholeNamedFieldAndBothPositiveFramesProved')is True
        and cap.get('rootNullMarkerAdmitted')is False and cap.get('fallbackPositiveAdmitted')is True
        and cap.get('maskCountLimit')==4096 and cap.get('nodeLimit')==16384 and cap.get('physicalEOFRequired')is True)
    return cap


def masks(reader,budget):
    from scripts.game_data.memorypack.animation_mask_positive_codec import read
    return read(reader,budget=budget)


def gameplay_tags(reader,budget):
    cap=reader.operation.child(component.TAGS);element=reader.operation.child('skill-root-gameplay-tag')
    need('own-generated-tag-list',cap.get('elementCapability')=='skill-root-gameplay-tag'
        and cap.get('elementGrammarAdmitted')is True and cap.get('positiveCountsAdmitted')is True
        and cap.get('countLimit')==4096 and cap.get('collectionCounts')==[-1,0]
        and element.get('memberCount')==1 and element.get('nullReturnsDefaultValue')is True
        and element.get('positiveWireBytes')==5 and element.get('rawUnmanagedTagGrammarUsed')is False)
    start=reader.pos;need('complete-tag-count',start+4<=reader.limit)
    count=struct.unpack_from('<i',reader.data,start)[0];need('tag-count-before-consumption',-1<=count<=4096)
    need('tag-budget-before-consumption',budget['remaining']>=1+max(count,0));budget['remaining']-=1+max(count,0)
    reader.take(4,'npcMontages.count');rows=[]
    for i in range(max(count,0)):
        at=reader.pos;marker=reader.peek();need('generated-tag-MC1-or-default',marker in(1,255));reader.take(1,'npcMontages.tag.memberCount')
        raw=bytes(4)if marker==255 else reader.take(4,'npcMontages.tag.tagId')
        rows.append(dict(start=at,end=reader.pos,isNull=marker==255,tagIdRawHex=raw.hex()))
    return dict(start=start,end=reader.pos,count=count,isNull=count==-1,rows=rows)


def frame(data,selected,*,operation):
    from scripts.game_data.memorypack import animation_fallback_set_codec as fallback
    from scripts.game_data.memorypack import animation_extra_union_codec as extra
    from scripts.game_data.memorypack import animation_custom_dictionary_codec as dictionaries
    from scripts.game_data.memorypack import animation_int_curve_dictionary_codec as ordinary
    from scripts.game_data.memorypack.animation_config_root_programs import FIELDS
    cap=require_capability(operation.child(component.CAPABILITY))
    need('same-operation-owned-root-capability',cap==selected['capabilities'][component.CAPABILITY])
    for child in cap['requiredChildCapabilities']:operation.child(child)
    reader=AnimationExtraReader(data,'AnimationConfig.current',operation=operation);reader.header(15)
    fields=[];budget=dict(remaining=16384)
    for index,name in enumerate(FIELDS):
        start=reader.pos
        if index==0:value=fallback.read(reader,budget=budget)
        elif index in(1,2,4,8,9):value=dict(rawHex=reader.take(8,name).hex())
        elif index==3:value=masks(reader,budget)
        elif index==5:value=extra.read(reader,budget=budget)
        elif index in(6,11,12):value=dictionaries.read(reader,name,budget=budget)
        elif index==7:value=gameplay_tags(reader,budget)
        elif index==10:value=ordinary.read(reader,budget=budget)
        else:
            raw=reader.take(1,name);value=dict(rawHex=raw.hex(),value=raw[0]!=0)
        fields.append(dict(memberIndex=index,fieldName=name,start=start,end=reader.pos,value=value))
    need('physical-EOF',reader.pos==reader.limit==len(data))
    return dict(status='complete-current-animation-config-frame',schemaStatus='named_exact',wholeSchemaExact=True,
        serializedMemberCount=15,bytesConsumed=reader.pos,
        physicalEOF=True,fields=fields,records=reader.records,runtimeAnimationProved=False,
        sourceSelectionConditional=True,fallbackPositiveAdmitted=True,remainingNodeBudget=budget['remaining'])
