"""Independent raw Quaternion and canonical PosRot-list constant cursors."""
import math
import struct

SCHEMA='endfield.actionmap-additional-constant-capability.v1'
QUATERNION='UnityEngine.Quaternion'
POSROT_LIST='System.Collections.Generic.List`1<Beyond.PosRot>'


def validate_constant(cap,value_type):
    if not isinstance(cap,dict)or cap.get('schema')!=SCHEMA or cap.get('valueType')!=value_type:
        raise ValueError('additionalActionParam.own-constant-source-required')
    expected=(dict(wireKind='quaternion-raw16',wireBytes=16,fieldOrder=['x','y','z','w'])
        if value_type==QUATERNION else dict(wireKind='posrot-list',countLimit=4096,
            elementMemberCount=2,nullElementMarker=255,elementPositiveWireBytes=25,
            elementDefaultBytes=24,fieldOrder=['eulerAngles','position'])if value_type==POSROT_LIST else None)
    if expected is None or any(cap.get(k)!=v or type(cap.get(k))is not type(v)for k,v in expected.items()):
        raise ValueError('additionalActionParam.exact-finite-constant-grammar')
    if(any(cap.get(k)is not True for k in('constantSourceProved','fullParamSourceProved','actualCallbackEqualsProvedChildRequired'))
            or any(cap.get(k)is not False for k in('liveFormatterSelectionObserved','runtimeValueEvaluationAdmitted','wholeOwnerAdmitted'))):
        raise ValueError('additionalActionParam.complete-independent-source-required')


def _floats(reader,field,count):
    at=reader.offset;reader.need(count*4,field);raw=bytes(reader.data[at:at+count*4]);reader.offset+=count*4
    values=struct.unpack('<'+'f'*count,raw)
    return dict(rawHex=raw.hex().upper(),values=[v if math.isfinite(v)else None for v in values],finite=[math.isfinite(v)for v in values])


def read_constant(reader,field,cap,value_type):
    validate_constant(cap,value_type)
    if value_type==QUATERNION:return _floats(reader,field,4)
    count=reader.number('<i',field+'.count')
    if not -1<=count<=cap['countLimit']:raise ValueError(field+':PosRot-list-count-limit')
    if count==-1:return None
    values=[]
    for index in range(count):
        at=reader.offset;path=field+'['+str(index)+']';marker=reader.number('<B',path+'.memberCount')
        if marker==255:
            def zero_vector():return dict(rawHex='000000000000000000000000',values=[0.0,0.0,0.0],finite=[True,True,True])
            value=dict(eulerAngles=zero_vector(),position=zero_vector(),wasDefaultMarker=True)
        elif marker==2:
            value=dict(eulerAngles=_floats(reader,path+'.eulerAngles',3),position=_floats(reader,path+'.position',3),wasDefaultMarker=False)
        else:raise ValueError(path+':PosRot-member-count')
        value.update(startOffset=at,endOffset=reader.offset);values.append(value)
    return values
