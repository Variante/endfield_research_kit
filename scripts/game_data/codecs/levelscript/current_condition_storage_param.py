"""Exact owned storage Param constants, without runtime pointer evaluation."""
import struct

from scripts.game_data.memorypack.levelscript_condition_storage_param_sources import POINTER_TYPES,SCRIPT,ENTITY

SCHEMA='endfield.story-condition-storage-param-capability.v1'
SPECS={**{name:('nominal-id-uint64',8)for name in POINTER_TYPES},'long':('i64',8),
 SCRIPT:('level-script-ptr-raw16',16),ENTITY:('entity-ptr-stored-value',None)}


def validate(cap):
 if not isinstance(cap,dict)or cap.get('valueType')not in SPECS:raise ValueError('currentStorageParam.explicit-storage-domain')
 value=cap['valueType'];kind,width=SPECS[value]
 expected=dict(schema=SCHEMA,typeName='Beyond.Gameplay.Actions.Param`1<'+value+'>',memberCount=4,
  fieldOrder=['constValue','idRef','paramSource','path'],constantWireKind=kind,constantWireBytes=width,
  idRefWireKind='i32',paramSourceWireKind='i32',pathEncoding='int32-pool-index',
  positiveWireBytes=width+13 if width is not None else None,nullWireBytes=1,nullOutput='reference-null',
  sourceReferenceKind=21,referenceOutputBytes=8,constantValueEvaluationAdmitted=False)
 integers=['memberCount','nullWireBytes','sourceReferenceKind','referenceOutputBytes']
 if width is not None:integers+=['constantWireBytes','positiveWireBytes']
 if(any(cap.get(k)!=v for k,v in expected.items())or any(type(cap.get(k))is not int for k in integers)
   or any(cap.get(k)is not True for k in('nullAdmitted','positiveAdmitted','wholeGrammarAdmitted','closedCarrierProved','actualCallbackEqualsProvedChildRequired'))
   or cap.get('liveFormatterSelectionObserved')is not False or cap.get('constantValueEvaluationAdmitted')is not False
   or type(cap.get('readerMethodDefinition'))is not int or cap['readerMethodDefinition']<0
   or any(type(cap.get(k))is not int or cap[k]<=0 for k in('sourceTargetRva','canonicalCallbackTargetRva'))):
  raise ValueError('currentStorageParam.exact-owned-four-field-source')
 if value in POINTER_TYPES and cap.get('constantValueFields')!=[['id','ulong',16]]:
  raise ValueError('currentStorageParam.own-id-field')
 if value==SCRIPT and(cap.get('constantValueFields')!=[['scriptId','ulong',16],['<levelId>k__BackingField','int',24]]
    or cap.get('copiedUninterpretedRanges')!=[[12,16]]or cap.get('runtimeScriptResolutionProved')is not False):
  raise ValueError('currentStorageParam.own-script-pointer-source')
 if value==ENTITY:
  from scripts.game_data.codecs.leveldata.current_entity_ptr import validate as validate_entity
  if cap.get('positiveWireBytesRange')!=[14,27]:raise ValueError('currentStorageParam.Entity-constant-wire-domain')
  validate_entity(cap.get('constantCapability'))


def read(reader,field,cap):
 validate(cap);start=reader.offset;marker=reader.number('<B',field+'.memberCount')
 if marker==255:return None
 if marker!=4:raise ValueError(f'{field}:storage-Param-member-count,offset={start},expected=4,actual={marker}')
 value=cap['valueType']
 if value in POINTER_TYPES:constant=dict(id=reader.number('<Q',field+'.constValue.id'))
 elif value=='long':constant=reader.number('<q',field+'.constValue')
 elif value==SCRIPT:
  at=reader.offset;reader.need(16,field+'.constValue');raw=bytes(reader.data[at:at+16]);reader.offset+=16
  script,level=struct.unpack_from('<Qi',raw);constant=dict(scriptId=script,levelId=level,
   rawHex=raw.hex().upper(),copiedUninterpretedHex=raw[12:16].hex().upper())
 else:
  from scripts.game_data.codecs.leveldata.current_entity_ptr import read as read_entity
  constant=read_entity(reader,field+'.constValue',cap['constantCapability'])
 result=dict(startOffset=start,typeName=cap['typeName'],constValue=constant,
  idRef=reader.number('<i',field+'.idRef'),paramSource=reader.number('<i',field+'.paramSource'),path=reader.string(field+'.path'))
 result['endOffset']=reader.offset;return result
