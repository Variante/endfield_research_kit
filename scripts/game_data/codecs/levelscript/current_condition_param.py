"""Finite source-gated four-field Param records, with pooled binding tails."""
import math
import struct

PREFIX='Beyond.Gameplay.Actions.Param`1<'
SPECS={'bool':('bool-byte',1),'int':('i32',4),'string':('pool',4),'float':('single-raw4',4),
 'uint':('u32',4),'ulong':('u64',8),'UnityEngine.Vector2':('vector2-raw8',8),'UnityEngine.Vector3':('vector3-raw12',12)}


def validate(cap):
 if not isinstance(cap,dict):raise ValueError('currentConditionParam.missing-capability')
 value=cap.get('valueType');spec=SPECS.get(value)
 if spec is None:raise ValueError('currentConditionParam.finite-primitive-value-domain')
 kind,width=spec
 _validate_shape(cap,kind,width)


def _validate_shape(cap,kind,width):
 value=cap.get('valueType')
 expected=dict(typeName=PREFIX+value+'>',memberCount=4,fieldOrder=['constValue','idRef','paramSource','path'],
  constantWireKind=kind,constantWireBytes=width,idRefWireKind='i32',paramSourceWireKind='i32',pathEncoding='int32-pool-index',
  positiveWireBytes=width+13,nullWireBytes=1,nullOutput='reference-null',sourceReferenceKind=21,referenceOutputBytes=8)
 integer_keys=('memberCount','constantWireBytes','positiveWireBytes','nullWireBytes','sourceReferenceKind','referenceOutputBytes')
 if(any(cap.get(k)!=v for k,v in expected.items())or any(type(cap.get(k))is not int for k in integer_keys)
   or any(cap.get(k)is not True for k in('nullAdmitted','positiveAdmitted','wholeGrammarAdmitted','closedCarrierProved','actualCallbackEqualsProvedChildRequired'))
   or cap.get('liveFormatterSelectionObserved')is not False
   or type(cap.get('readerMethodDefinition'))is not int or cap['readerMethodDefinition']<0
   or type(cap.get('sourceTargetRva'))is not int or cap['sourceTargetRva']<=0
   or type(cap.get('canonicalCallbackTargetRva'))is not int or cap['canonicalCallbackTargetRva']<=0):
  raise ValueError('currentConditionParam.exact-closed-four-field-source')


def _raw_floats(reader,field,width):
 start=reader.offset;reader.need(width,field);raw=bytes(reader.data[start:start+width]);reader.offset+=width
 values=struct.unpack('<'+'f'*(width//4),raw)
 return dict(rawHex=raw.hex().upper(),values=[v if math.isfinite(v)else None for v in values],
  finite=[math.isfinite(v)for v in values])


def read(reader,field,cap):
 validate(cap);return _read_record(reader,field,cap)


def _read_record(reader,field,cap):
 start=reader.offset;marker=reader.number('<B',field+'.memberCount')
 if marker==255:return None
 if marker!=4:raise ValueError(f'{field}:Param-member-count,offset={start},expected=4,actual={marker}')
 kind=cap['constantWireKind']
 if kind=='pool':constant=reader.string(field+'.constValue')
 elif kind=='bool-byte':
  raw=reader.number('<B',field+'.constValue');constant=dict(value=bool(raw),rawByte=raw)
 elif kind in('single-raw4','vector2-raw8','vector3-raw12'):
  constant=_raw_floats(reader,field+'.constValue',cap['constantWireBytes'])
 else:constant=reader.number({'i32':'<i','u32':'<I','u64':'<Q','raw-u8':'<B'}[kind],field+'.constValue')
 result=dict(startOffset=start,typeName=cap['typeName'],constValue=constant,
  idRef=reader.number('<i',field+'.idRef'),paramSource=reader.number('<i',field+'.paramSource'),path=reader.string(field+'.path'))
 result['endOffset']=reader.offset;return result
