"""Source-faithful Nullable<Single> raw8 child behind its exact capability."""
import math
import struct

TYPE='System.Nullable`1<float>'
CAP='story-nullable-single'


def validate(cap):
    if not isinstance(cap,dict):raise ValueError('currentNullableSingle.missing-capability')
    expected=dict(typeName=TYPE,capability=CAP,managedBytes=8,wireBytes=8,headerBytes=0,
        resultAbi='rax-managed-value',concreteTypeKind=21,hasValueByteOffset=0,
        paddingByteRanges=[[1,3]],singleBitsByteOffset=4)
    integer_keys=('managedBytes','wireBytes','headerBytes','concreteTypeKind','hasValueByteOffset','singleBitsByteOffset')
    if (any(cap.get(k)!=v for k,v in expected.items())
            or any(type(cap.get(k))is not int for k in integer_keys)
            or cap.get('paddingByteRanges')!=[[1,3]]
            or any(type(n)is not int for row in cap['paddingByteRanges']for n in row)
            or any(cap.get(k)is not True for k in('valueCarrier','actualSourceProved','wireGrammarAdmitted',
                'rawBitsPreserved','actualCallbackEqualsProvedChildRequired'))
            or any(cap.get(k)is not False for k in('hasValueByteNormalized','nullHeaderAdmitted','runtimeProviderSelectionObserved'))
            or type(cap.get('readerMethodDefinition'))is not int or cap['readerMethodDefinition']<0
            or type(cap.get('sourceTargetRva'))is not int or cap['sourceTargetRva']<=0):
        raise ValueError('currentNullableSingle.exact-constructed-value-source')


def read(reader,field,cap):
    validate(cap);start=reader.offset;reader.need(8,field+'.rawNullableSingle')
    raw=bytes(reader.data[start:start+8]);reader.offset+=8
    value=struct.unpack('<f',raw[4:])[0];finite=math.isfinite(value)
    return dict(startOffset=start,endOffset=reader.offset,hasValueByte=raw[0],hasValue=bool(raw[0]),
        value=value if raw[0]and finite else None,valueIsFinite=finite,
        paddingHex=raw[1:4].hex().upper(),valueBitsHex=raw[4:].hex().upper(),rawHex=raw.hex().upper())
