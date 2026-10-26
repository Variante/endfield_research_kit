"""Finite Tracking child profiles; direct raw and canonical wrapper stay distinct.

Projection functions only check independently derived source components. They
do not open native inputs, observe provider selection or grant a host/EOF.
"""
from scripts.game_data.memorypack.leveldata_tracking_value_sources import BOUNDS,POINT,ENUM,SPECS

SCHEMA='endfield.story-tracking-components.v1'
VALUE_CAPS={BOUNDS:'story-tracking-bounds-value',POINT:'story-tracking-point-value'}
LIST_CAPS={BOUNDS:'story-tracking-bounds-list',POINT:'story-tracking-point-list'}


def need(check,condition):
 if not condition:raise ValueError('storyTrackingComponents.'+check)


def value_capability(component,pins):
 """Exact domain projection; the caller still owns fresh native admission."""
 from scripts.game_data.memorypack import leveldata_tracking_transfer_sources as owner
 name=component.get('typeName');need('finite-owned-type',type(name)is str and name in SPECS);spec=SPECS[name]
 need('current-own-canonical-component',component.get('schema')==owner.SCHEMA
  and component.get('status')=='validated-conditional-tracking-value-transfer'and component.get('nativeInputs')==pins
  and type(component.get('managedBytes'))is int and component['managedBytes']==spec['managedBytes']
  and component.get('referenceLaneOffsets')==[]and component.get('paddingByteRanges')==[]
  and type(component.get('canonicalCallbackTargetRva'))is int and component['canonicalCallbackTargetRva']>0
  and all(component.get(k)is True for k in('canonicalCallbackAdmitted','wrapperGrammarAdmitted','actualCallbackEqualsCanonicalRequired'))
  and all(component.get(k)is False for k in('liveFormatterSelectionObserved','parentFieldAdmitted','containerAdmitted','wholeOwnerAdmitted')))
 count=len(spec['order']);positive=37 if name==BOUNDS else 17;width=spec['managedBytes']
 need('exact-wire-distinct-from-managed',all(type(component.get(k))is int and component[k]==v for k,v in
  dict(canonicalFFWireBytes=1,canonicalFFDefaultManagedBytes=width,positiveMemberCount=count,positiveWireBytes=positive).items()))
 record=component.get('record',{});programs=component.get('proof',{}).get('programs',{})
 need('complete-own-record-source',record.get('schema')=='endfield.story-tracking-value-wrapper.v1'
  and record.get('status')=='validated-conditional-tracking-value-wrapper'and record.get('nativeInputs')==pins
  and record.get('typeName')==name and record.get('managedBytes')==width
  and record.get('orderedMembers')==[list(pair)for pair in spec['order']]
  and record.get('layout',{}).get('fields')==[list(row)for row in spec['fields']]
  and record.get('referenceLaneOffsets')==[]and record.get('paddingByteRanges')==[]
  and len(record.get('programs',[]))==4
  and {(p.get('existing'),p.get('wrapperNull'))for p in record['programs']}=={(False,False),(True,False),(False,True),(True,True)}
  and all(p.get('normalReturn')is True and p.get('entryRspRestored')is True and p.get('allNonvolatilesRestored')is True
   and p.get('managedBytes')==width and bool(p.get('selectedBytes'))for p in record['programs']))
 need('all-canonical-paths-and-frame',len(programs.get('adapter',[]))==3 and len(programs.get('nonnull',[]))==2
  and len(programs.get('readNull',[]))==2 and all(p.get('entryRspRestored')is True and p.get('normalReturn')is True
   and bool(p.get('selectedBytes'))for p in programs['adapter']+programs['nonnull']+[programs.get('conversion',{})])
  and {(p.get('null'),p.get('createWrapper'))for p in programs['adapter']}=={(False,False),(False,True),(True,None)}
  and {p.get('wrapperNull')for p in programs['nonnull']}=={False,True}
  and all(p.get('managedOutputBytes')==width and p.get('defaultOutputBytes')==(width if p['null']else 0)
   and p.get('sameIncomingReaderAndOutput')is True for p in programs['adapter'])
  and all(p.get('managedOutputBytes')==width and p.get('defaultZeroBytes')==(width if p['wrapperNull']else 0)
   and p.get('copiedCompleteGetterBytes')==(0 if p['wrapperNull']else width)
   and p.get('referenceLaneOffsets')==[]and p.get('sameIncomingReaderAndOutput')is True for p in programs['nonnull'])
  and {(p.get('null'),p.get('consumedBytes'))for p in programs['readNull']}=={(False,0),(True,1)}
  and programs['conversion'].get('managedOutputBytes')==width
  and programs['conversion'].get('copiedSlices')==([[0,16],[16,16],[32,4]]if name==BOUNDS else[[0,16]])
  and programs['conversion'].get('sameOutputReturnedInRax')is True
  and programs['conversion'].get('referenceLaneOffsets')==[]and programs['conversion'].get('interfaceFallbackAdmitted')is False)
 backing=None
 if name==POINT:
  enum=record.get('enumSource',{});backing=enum.get('backingType')
  need('own-point-enum-source',enum.get('schema')=='endfield.unmanaged-enum-member-source.v1'
   and enum.get('status')=='validated-conditional-direct-enum-source'and enum.get('nativeInputs')==pins
   and enum.get('typeName')==ENUM and backing in('int','uint')and type(enum.get('wireBytes'))is int and enum['wireBytes']==4
   and enum.get('resultRegister')=='eax'and enum.get('sourceMethod')=='ReadUnmanaged'
   and enum.get('actualSourceProved')is True and enum.get('formatterCallbackSelectionAdmitted')is False)
 return dict(typeName=name,capability=VALUE_CAPS[name],memberCount=count,managedBytes=width,
  positiveWireBytes=positive,canonicalFFWireBytes=1,canonicalFFDefaultManagedBytes=width,
  serializedOrder=[list(pair)for pair in spec['order']],enumBackingType=backing,referenceLaneOffsets=[],paddingByteRanges=[],
  canonicalCallbackTargetRva=component['canonicalCallbackTargetRva'],canonicalOriginalAdapterAdmitted=True,
  actualCallbackEqualsCanonicalRequired=True,rawBitsPreserved=True,profileAdmitted=True,
  wholeGrammarAdmitted=False,liveFormatterSelectionObserved=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False)


def derive_value(image,pins,type_name):
 from scripts.game_data.memorypack.leveldata_tracking_transfer_sources import derive
 source=derive(image,pins,type_name);cap=value_capability(source,pins)
 return dict(schema=SCHEMA,status='validated-conditional-tracking-value-profile',nativeInputs=pins,
  capabilities={VALUE_CAPS[type_name]:cap},proof=dict(value=source),parentFieldAdmitted=False,wholeOwnerAdmitted=False)


def bind_raw(context,source_target,component,pins,*,base):
 """Bind one actual R8 source request; parent local/store/frame stays separate."""
 from scripts.game_data.memorypack import leveldata_tracking_raw_sources as owner
 need('literal-selected-native-addresses',type(base)is int and type(source_target)is int and source_target>base)
 need('complete-raw-source-replay',owner.verify(component,pins)==base)
 usage=component['proof']['typedRequest'];nominal=component['proof']['nominalLayout']
 need('exact-actual-Bounds-source-context',context.get('methodOwner')=='MemoryPack.MemoryPackReader'
  and context.get('methodName')=='ReadUnmanaged'and context.get('register')=='r8'
  and context.get('fullTypeName')==BOUNDS and type(context.get('typeKind'))is int and context['typeKind']==17
  and type(context.get('typeDefinition'))is int and context['typeDefinition']==component.get('typeDefinition')==nominal.get('typeDefinition')
  and context.get('methodSpec')==usage.get('methodSpec')and context.get('instructionRva')==usage.get('instructionRva')
  and context.get('instructionHex')==usage.get('instructionHex')
  and component.get('readerMethodDefinition')==usage['methodSpec'][0]
  and component.get('sourceTargetRva')==source_target-base
  and component.get('sourceMethod')=='ReadUnmanaged'and component.get('contextRegister')=='r8'
  and component.get('resultAbi')=='hidden-output-rcx'
  and nominal.get('typeName')==BOUNDS and nominal.get('fields')==[list(row)for row in SPECS[BOUNDS]['fields']]
  and nominal.get('managedBytes')==36 and nominal.get('referenceLaneOffsets')==[]and nominal.get('paddingByteRanges')==[]
  and nominal.get('layoutUsedForWireWidth')is False and nominal.get('canonicalWrapperWireUsed')is False)
 return dict(capability=owner.CAPABILITY,typeName=BOUNDS,typeDefinition=component['typeDefinition'],
  readMethod=component['sourceMethod'],readerMethodDefinition=component['readerMethodDefinition'],
  sourceTargetRva=component['sourceTargetRva'],wireBytes=36,managedBytes=36,resultAbi='hidden-output-rcx',
  referenceLaneOffsets=[],paddingByteRanges=[],parentLocalStoreFrameRequired=True)
