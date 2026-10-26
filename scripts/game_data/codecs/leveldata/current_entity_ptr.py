"""Canonical stored EntityPtr fields; a fresh caller must supply its own source."""
from scripts.game_data.codecs.levelscript.entity_ptr_param import decode_entity_ptr_value

TYPE='Beyond.Gameplay.Core.EntityPtr'
CAP='story-entity-ptr-value'


def validate(cap):
 if(not isinstance(cap,dict)or(cap.get('typeName'),cap.get('capability'))!=(TYPE,CAP)
  or any(type(cap.get(k))is not int or cap[k]!=v for k,v in dict(managedBytes=40,wireMemberCount=3,
   positiveWireBytes=14,nullWireBytes=1,defaultOutputZeroBytes=40).items())
  or cap.get('knownPaddingByteRanges')!=[[1,8],[20,24]]or cap.get('opaqueRuntimeStorageRanges')!=[[24,40]]
  or cap.get('selectedBarrierValueOffsets')!=[24]
  or cap.get('runtimeReferenceLayoutAdmitted')is not False or cap.get('completeRuntimePaddingMapAdmitted')is not False
  or 'referenceLaneOffsets'in cap or 'paddingByteRanges'in cap
  or any(cap.get(k)is not True for k in('profileAdmitted','nullAdmitted','positiveAdmitted','canonicalValueAdapterAdmitted',
   'runtimeOnlyObjectPtr','actualCallbackEqualsProvedChildRequired','coherentWrapperStorageRequired'))
  or cap.get('rawBoolNormalization')!='nonzero'or cap.get('wholeGrammarAdmitted')is not False
  or cap.get('runtimeEntityResolutionProved')is not False or cap.get('liveFormatterSelectionObserved')is not False
  or type(cap.get('readerMethodDefinition'))is not int or cap['readerMethodDefinition']<0
  or type(cap.get('sourceTargetRva'))is not int or cap['sourceTargetRva']<=0):
  raise ValueError('currentEntityPtr.exact-dedicated-value-capability')


def read(reader,field,cap):
 validate(cap);start=reader.offset
 reader.need(1,field+'.memberCount');result=decode_entity_ptr_value(reader.data,start)
 if result is None:raise ValueError(field+':entity-ptr-member-or-extent')
 value,end=result;reader.offset=end
 return dict(startOffset=start,endOffset=end,logicId=str(value['logicId']),slotId=value['slotId'],
  useSlotId=value['useSlotId'],useSlotIdRawByte=value['useSlotIdRawByte'],defaultValue=value['constantWasNull'],
  runtimeObjectPtrSerialized=False)
