"""Pooled tag-list Param; generated MC1/default values retain raw tag IDs."""
from scripts.game_data.codecs.levelscript.param_graph import Reader

SCHEMA='endfield.levelscript-gameplay-tag-list-param-capability.v1'
VALUE='Beyond.Gameplay.Core.GameplayTag'
LIST='System.Collections.Generic.List`1<'+VALUE+'>'
TYPE='Beyond.Gameplay.Actions.Param`1<'+LIST+'>'


def validate(cap):
    expected=dict(schema=SCHEMA,typeName=TYPE,valueType=LIST,memberCount=4,
        fieldOrder=['constValue','idRef','paramSource','path'],pathEncoding='int32-pool-index',
        countLimit=4096,countRange=[-1,4096],headerBytes=4,elementType=VALUE,
        elementWireKind='generated-MC1-int32-or-FF-default4',elementMemberCount=1,
        positiveElementWireBytes=5,defaultElementWireBytes=1,defaultElementValue=0,
        outerNullReference=True,positiveCountsAdmitted=True,exactOwnNominalsProved=True,
        actualParamAndListAndElementCallbacksRequired=True,liveFormatterSelectionObserved=False,
        runtimeTagResolutionProved=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False)
    if not isinstance(cap,dict)or any(type(cap.get(k))is not type(v)or cap[k]!=v for k,v in expected.items())or any(type(n)is not int for n in cap['countRange']):
        raise ValueError('currentGameplayTagListParam.own-generated-MC1-list-Param')
    for key in('readerMethodDefinition','sourceTargetRva','canonicalParamCallbackTargetRva'):
        if type(cap.get(key))is not int or cap[key]<=0:raise ValueError('currentGameplayTagListParam.own-typed-reference-callbacks')


def read(reader,field,cap):
    validate(cap)
    marker=reader.number('<B',field+'.memberCount')
    if marker==255:return None
    if marker!=4:raise ValueError(field+':GameplayTag-list-Param-member-count')
    count=reader.number('<i',field+'.value.count')
    if not -1<=count<=cap['countLimit']:raise ValueError(field+':GameplayTag-list-count-limit:'+str(count))
    value=None if count==-1 else[]
    for i in range(max(count,0)):
        name=field+'.value['+str(i)+']';marker=reader.number('<B',name+'.memberCount')
        if marker==255:tag=0
        elif marker==1:tag=reader.number('<i',name+'.tagId')
        else:raise ValueError(name+':GameplayTag-element-member-count')
        value.append(dict(tagId=tag))
    return dict(value=value,idRef=reader.number('<i',field+'.idRef'),
        paramSource=reader.number('<i',field+'.paramSource'),path=reader.string(field+'.path'))


def decode(data,offset,*,field,strings,capability):
    reader=Reader(data,offset,strings,field);value=read(reader,field,capability)
    return value,reader.offset
