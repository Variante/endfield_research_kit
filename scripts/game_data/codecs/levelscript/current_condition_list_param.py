"""Finite source-owned list constants in four-field condition Params."""
import struct

from scripts.game_data.memorypack.levelscript_condition_list_param_sources import LIST,ENTITY,LSM,ELEMENTS

SCHEMA='endfield.story-condition-list-param-capability.v1'


def validate(cap):
 if not isinstance(cap,dict)or cap.get('elementType')not in ELEMENTS:raise ValueError('currentListParam.explicit-element-domain')
 element=cap['elementType'];value=LIST+element+'>'
 expected=dict(schema=SCHEMA,typeName='Beyond.Gameplay.Actions.Param`1<'+value+'>',valueType=value,memberCount=4,
  fieldOrder=['constValue','idRef','paramSource','path'],constantWireKind='owned-list',constantWireBytes=None,
  idRefWireKind='i32',paramSourceWireKind='i32',pathEncoding='int32-pool-index',positiveWireBytes=None,
  nullWireBytes=1,nullOutput='reference-null',sourceReferenceKind=21,referenceOutputBytes=8,
  collectionCountEncoding='signed-int32',collectionNullCount=-1,countLimit=10000,
  elementWireKind={'string':'pooled-string-index','uint':'u32',ENTITY:'entity-ptr-mc3',LSM:'lsm-ptr-mc1'}[element],
  elementWireBytes=None if element in(ENTITY,LSM)else 4,reusedListsRequireInitialCount=0)
 integers=('memberCount','nullWireBytes','sourceReferenceKind','referenceOutputBytes','collectionNullCount','countLimit',
  'reusedListsRequireInitialCount')
 if(any(cap.get(k)!=v for k,v in expected.items())or any(type(cap.get(k))is not int for k in integers)
   or any(cap.get(k)is not True for k in('nullAdmitted','positiveAdmitted','wholeGrammarAdmitted','closedCarrierProved',
    'actualCallbackEqualsProvedChildRequired','listSourceAdmitted','elementSourceAdmitted','callbackSelectionConditional',
    'freshListsAdmitted','reusedListsRequireCapacityAtLeastCount'))
   or cap.get('liveFormatterSelectionObserved')is not False or cap.get('runtimeConstantEvaluationAdmitted')is not False
   or type(cap.get('readerMethodDefinition'))is not int or cap['readerMethodDefinition']<0
   or any(type(cap.get(k))is not int or cap[k]<=0 for k in('sourceTargetRva','canonicalCallbackTargetRva'))):
  raise ValueError('currentListParam.exact-owned-four-field-list-source')
 if element not in(ENTITY,LSM)and type(cap.get('elementWireBytes'))is not int:raise ValueError('currentListParam.literal-element-wire-width')
 if element==ENTITY and(cap.get('elementGrammar')!=dict(nullMarker=255,memberCount=3,fields=['uint64','uint32','bool-byte'])
    or cap.get('runtimeEntityResolutionProved')is not False):raise ValueError('currentListParam.own-Entity-element-grammar')
 if element==LSM and(cap.get('elementGrammar')!=dict(nullMarker=255,memberCount=1,fields=['uint64'],nullOutput='default-zero8')
    or type(cap.get('elementManagedBytes'))is not int or cap['elementManagedBytes']!=8
    or cap.get('actualElementValueCallbackEqualsCanonicalRequired')is not True
    or cap.get('runtimeLsmResolutionProved')is not False):raise ValueError('currentListParam.own-Lsm-element-grammar')


def read(reader,field,cap,*,budget=None):
 validate(cap)
 if budget is None:budget=[cap['countLimit']]
 if not isinstance(budget,list)or len(budget)!=1 or type(budget[0])is not int or budget[0]<0:
  raise ValueError('currentListParam.literal-shared-budget')
 start=reader.offset;marker=reader.number('<B',field+'.memberCount')
 if marker==255:return None
 if marker!=4:raise ValueError(f'{field}:list-Param-member-count,offset={start},expected=4,actual={marker}')
 at=reader.offset;reader.need(4,field+'.constValue.count');count=struct.unpack_from('<i',reader.data,at)[0]
 if not -1<=count<=cap['countLimit']:raise ValueError(f'{field}:list-Param-count,offset={at},actual={count}')
 if max(count,0)>budget[0]:raise ValueError(field+':list-Param-shared-budget')
 budget[0]-=max(count,0);reader.offset+=4;constant=None
 if count>=0:
  constant=[]
  for index in range(count):
   selected=field+'.constValue['+str(index)+']';element=cap['elementType']
   if element=='string':value=reader.string(selected)
   elif element=='uint':value=reader.number('<I',selected)
   elif element==LSM:
    marker=reader.number('<B',selected+'.memberCount')
    if marker==255:value=dict(id=0,defaultValue=True)
    elif marker==1:value=dict(id=reader.number('<Q',selected+'.id'),defaultValue=False)
    else:raise ValueError(selected+':Lsm-member-count')
   else:
    from scripts.game_data.codecs.levelscript.entity_ptr_param import decode_entity_ptr_value
    result=decode_entity_ptr_value(reader.data,reader.offset)
    if result is None:raise ValueError(selected+':Entity-member-or-extent')
    value,reader.offset=result
   constant.append(value)
 result=dict(startOffset=start,typeName=cap['typeName'],constValue=constant,
  idRef=reader.number('<i',field+'.idRef'),paramSource=reader.number('<i',field+'.paramSource'),path=reader.string(field+'.path'))
 result['endOffset']=reader.offset;return result
