"""Only the selected owner's dedicated LangKey child supplies this cursor."""
TYPE='Beyond.LangKey'


def validate(cap):
    expected=dict(typeName=TYPE,managedBytes=16,referenceLaneOffsets=[0,8],memberCount=1,
        keyName='key',keyEncoding='int32-pool-index',positiveWireBytes=5,nullWireBytes=1,
        nullHeaderDefaultValueBytes=16,nonserializedRawText=True)
    if (any(cap.get(k)!=value for k,value in expected.items())
            or type(cap.get('referenceLaneOffsets'))is not list or any(type(n)is not int for n in cap['referenceLaneOffsets'])
            or any(type(cap.get(k))is not int for k in('managedBytes','memberCount','positiveWireBytes','nullWireBytes','nullHeaderDefaultValueBytes'))
            or any(cap.get(k)is not True for k in('nonserializedRawText','nullAdmitted','positiveAdmitted','wholeGrammarAdmitted','actualCallbackEqualsProvedChildRequired'))
            or cap.get('liveFormatterSelectionObserved')is not False
            or type(cap.get('readerMethodDefinition'))is not int or cap['readerMethodDefinition']<0
            or type(cap.get('sourceTargetRva'))is not int or cap['sourceTargetRva']<=0):
        raise ValueError('currentLangKey.exact-dedicated-wire-child')


def read(reader,field,cap):
    validate(cap);start=reader.offset;marker=reader.number('<B',field+'.memberCount')
    if marker==255:return dict(startOffset=start,endOffset=reader.offset,key=None,defaultValue=True,rawTextSerialized=False)
    if marker!=1:raise ValueError(f'{field}:LangKey-member-count,offset={start},expected=1,actual={marker}')
    key=reader.string(field+'.key')
    return dict(startOffset=start,endOffset=reader.offset,key=key,defaultValue=False,rawTextSerialized=False)
