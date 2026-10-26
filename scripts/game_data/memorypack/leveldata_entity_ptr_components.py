"""Finite EntityPtr stored-field child; enclosing hidden40 transfers are separate."""
from scripts.game_data.memorypack.leveldata_entity_ptr_value_sources import TYPE

CAP='story-entity-ptr-value'


def capability(source):
 from scripts.game_data.codecs.leveldata.current_entity_ptr import validate
 if(source.get('schema')!='endfield.story-entity-ptr-value-source.v1'or source.get('status')!='validated-conditional-source'
  or source.get('typeName')!=TYPE or source.get('actualSourceProved')is not True or source.get('wireGrammarAdmitted')is not False
  or 'referenceLaneOffsets'in source or 'paddingByteRanges'in source):
  raise ValueError('storyEntityPtr.exact-dedicated-source')
 cap=dict(typeName=TYPE,capability=CAP,managedBytes=source['managedBytes'],knownPaddingByteRanges=source['knownPaddingByteRanges'],
  opaqueRuntimeStorageRanges=source['opaqueRuntimeStorageRanges'],selectedBarrierValueOffsets=source['selectedBarrierValueOffsets'],
  runtimeReferenceLayoutAdmitted=source['runtimeReferenceLayoutAdmitted'],
  completeRuntimePaddingMapAdmitted=source['completeRuntimePaddingMapAdmitted'],
  wireMemberCount=source['wireMemberCount'],positiveWireBytes=source['positiveWireBytes'],
  nullWireBytes=source['nullWireBytes'],readerMethodDefinition=source['readerMethodDefinition'],sourceTargetRva=source['sourceTargetRva'],
  profileAdmitted=True,nullAdmitted=True,positiveAdmitted=True,canonicalValueAdapterAdmitted=True,
  defaultOutputZeroBytes=40,runtimeOnlyObjectPtr=True,rawBoolNormalization='nonzero',
  actualCallbackEqualsProvedChildRequired=True,coherentWrapperStorageRequired=True,wholeGrammarAdmitted=False,
  runtimeEntityResolutionProved=False,liveFormatterSelectionObserved=False)
 validate(cap);return cap


def derive(image,pins,*,typed_request,source_target):
 from scripts.game_data.memorypack.leveldata_entity_ptr_value_sources import derive_read_value
 source=derive_read_value(image,pins,typed_request=typed_request,source_target=source_target)
 return dict(schema='endfield.story-entity-ptr-value-component.v1',nativeInputs=pins,capabilities={CAP:capability(source)},
  proof=dict(readSource=source),parentFieldAdmitted=False,wholeOwnerAdmitted=False,
  evidenceBoundary=dict(exact='Only own canonical EntityPtr MC3 stored logicId/slotId/useSlotId and FF/default40, full hidden40 actual source/setter, exact selected barrier offset24 and distinct opaque runtime-only ObjectPtr<Entity> storage.',
   conditional='Ready exact selected callbacks/contexts and coherent wrapper cache; normal helper/provider/collector effects and buffered disjoint storage. Positive reuse may retain runtime-only ObjectPtr bits, which the wire projection does not expose.',
   unresolved=['actual enclosing hidden local/field/setter/frame','runtime ObjectPtr reference layout/padding/Entity selection or resolution','whole owner/physical EOF']))
