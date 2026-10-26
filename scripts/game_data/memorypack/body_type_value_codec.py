"""BodyTypeDef MC3 wire; managed padding and display name consume no bytes."""
from scripts.game_data.memorypack import body_type_value_components as owner


def need(check,condition):
    if not condition:raise ValueError('bodyTypeValueCodec.'+check)


def require_capability(cap):
    need('own-nominal-and-wire',cap.get('typeName')==owner.source.TYPE and cap.get('wrapperName')==owner.source.WRAPPER
        and all(type(cap.get(k))is int and cap[k]==v for k,v in(('managedBytes',32),('memberCount',3),
            ('nullMarker',255),('nullWireBytes',1),('positiveWireBytes',10)))
        and cap.get('orderedReads')==owner.ORDER and cap.get('referenceLaneOffsets')==[8,24]
        and cap.get('paddingByteRanges')==[[1,7],[20,4]]and cap.get('runtimeOnlyFieldNames')==['m_displayName']
        and cap.get('wireBytes')is None and cap.get('wholeOwnerAdmitted')is False
        and all(cap.get(k)is True for k in('nullable','nullReturnsDefaultValue','wholeGrammarAdmitted',
            'ownConcreteGetterSemanticsProved','ownConcreteFactorySemanticsProved'))
        and type(cap.get('valueReaderMethodDefinition'))is int and cap['valueReaderMethodDefinition']>0
        and type(cap.get('valueDispatcherTargetRva'))is int and cap['valueDispatcherTargetRva']>0)
    return cap


def read(reader,capability=owner.CAPABILITY,depth=0):
    need('own-capability',capability==owner.CAPABILITY);need('depth',type(depth)is int and 0<=depth<=64)
    cap=require_capability(reader.operation.child(capability));pool=reader.operation.child('byte-payload')
    need('signed-pool-domain',pool.get('wholeGrammarAdmitted')is True and pool.get('encoding')=='int32-pool-index'
        and type(pool.get('emptyIndex'))is int and pool['emptyIndex']==-1
        and type(pool.get('nullIndex'))is int and pool['nullIndex']==-2)
    start=reader.pos;null=reader.peek()==255;fields=[]
    if null:reader.take(1,capability+'.null')
    else:
        need('pool-depth',depth+1<=64);reader.header(3)
        for field in cap['orderedReads']:
            at=reader.pos
            if field['kind']=='pooled-string':reader.byte_payload()
            else:reader.take(1 if field['kind']=='enum-byte'else 4,capability+'.'+field['fieldName'])
            fields.append(dict(fieldName=field['fieldName'],start=at,end=reader.pos))
    row=dict(kind=capability,start=start,end=reader.pos,isNull=null,fields=fields);reader.records.append(row);return row
