"""Selected actual Patrol TryLoad interface/inline handle transfer source.

Ready class/MethodInfo/interface records must select the literal inline target.
The actual resource request Bool and compatible20-byte output are conditional
helper results, never observed asset existence. Both Bool alternatives copy the
complete output and restore the full frame. No wire/default/callback alias is
obtained from a payload width or the missing ordinary source method name.
"""
import json
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

SCHEMA='endfield.story-patrol-asset-tryload-source.v1'


def need(check,condition):
 if not condition:raise ValueError('storyPatrolAsset.'+check)


def program(regions,entry,*,loaded=True,matched=True,miss_one=False,root_category_offset=16):
 need('literal-interface-and-result-path',all(type(v)is bool for v in(loaded,matched,miss_one))and(matched or not miss_one))
 need('own-root-category-small-offset',type(root_category_offset)is int and 16<=root_category_offset<128)
 g=BytesPath(regions,entry);calls=[]
 def call(role):
  at=g.at;target=g.relative('e8');calls.append(dict(role=role,instructionVa=at,targetVa=target));return target
 g.take('48895c2408','48896c2410','4889742418','57','4154','4155','4156','4157','4883ec70',
  '4d8bf9','498bf8','4c8bf2','488be9','440fb76150','488b5920','488b32','488bce');call('prepare-receiver-class')
 g.take('4533ed','410fb7c5','440fb78630010000','66453be8');g.branch('73',not matched,1)
 loop=None
 if matched:
  g.take('488b96b0000000');loop=g.at
  g.take('0fb7c8','4803c9','48391cca');g.branch('74',not miss_one,1)
  if miss_one:
   g.take('66ffc0','66413bc0');target=g.relative('72',1);need('exact-interface-record-loop-backedge',target==loop);g.at=target
   g.take('0fb7c8','4803c9','48391cca');g.branch('74',True,1)
  g.take('0fb7d0','4803d2','488b86b0000000','8b44d008','4103c4','4898','4883c014','48c1e004','4803c6')
 else:
  g.take('450fb7c4','488bd3','498bce');call('resolve-interface-slot');g.at=g.relative('eb',1)
 g.take('488b4808','498bd5','f6415402');g.branch('0f85',False)
 g.take('4c8b4540','4d8b4010');call('resolve-actual-method-context')
 g.take('488bd8','b958000000','b808000000');alternate=g.relative('4c392d');g.take('0f45c1','4c8b1403','4c392b')
 g.branch('0f84',False);inline=g.relative('488d05');g.take('4c3bd0');g.branch('0f85',False)
 g.take('4c396b38');g.branch('0f84',False);g.take('0f57c0','33c0','0f11442430','89442440','488b5b38','488b1b')
 type_usage=g.at;type_cell=g.relative('488b0d');g.take('3981e0000000');g.branch('0f84',False)
 g.take('33d2','488bcb');call('runtime-type-from-context');g.take('488bd8','410fb676'+bytes((root_category_offset,)).hex())
 resource_usage=g.at;resource_cell=g.relative('488b0d');g.take('4439a9e0000000');g.branch('0f84',False)
 g.take('4c896c2420','440fb6ce','4c8d442430','488bd3','488bcf');call('resource-TryLoad')
 g.take('84c0');g.branch('0f84',not loaded)
 if loaded:
  g.take('0f10442430','410f1107','8b442440','41894710','0f29442450','89442460','4533c0','488d542450','498bce')
  call('retain-loader-handle');g.take('b001')
 else:
  g.take('0f57c0','33c0','410f1107','41894710');g.at=g.relative('e9')
 g.take('4c8d5c2470','498b5b30','498b6b38','498b7340','498be3','415f','415e','415d','415c','5f','c3')
 return dict(selectedBytes=g.seen,entry=entry,loaded=loaded,matchedInterface=matched,oneNonmatchingInterfaceRecord=miss_one,
  interfaceRecordLoopEntryVa=loop,interfaceRecordStride=16,interfaceCountBytes=2,interfaceCountOffset=304,
  declaringTypeFromMethodInfoOffset=32,selectorFromMethodInfoOffset=80,vtableBase=320,vtableStride=16,
  actualInlineTargetVa=inline,alternativeMethodPointerModeCell=alternate,selectedAlternativeMethodPointerModeZeroRequired=True,
  selectedMethodContextNonzeroRequired=True,selectedRuntimeCallbackMustEqualInlineTarget=True,
  classUsageInstructions=[type_usage,resource_usage],classCells=[type_cell,resource_cell],calls=calls,
  inputArguments=dict(methodInfo='incoming RCX retained RBP',receiver='incoming RDX retained R14',
   pathHash='incoming R8 retained RDI',outputAddress='incoming R9 retained R15'),
  resourceArguments=dict(rcx='unchanged path-hash QWORD',rdx='runtime Type from actual generic context',
   r8='address of zeroed20-byte local at RSP48',r9d='zero-extended actual receiver RootCategory byte',stackArgument5=0),
  rootCategoryFieldOffset=root_category_offset,outputSlices=[dict(offset=0,bytes=16),dict(offset=16,bytes=4)],
  failedOutputIsZero20=not loaded,successfulOutputLocalCopied20Unchanged=loaded,
  successfulRetainReceivesSame20ByteLocal=loaded,resultAl=loaded,entryRspRestored=True,
  nonvolatilesRestored=['rbx','rbp','rsi','rdi','r12','r13','r14','r15'],normalReturn=True,
  actualResourceRequestOrRetainEffectsProved=False,liveAssetOrInterfaceSelectionObserved=False)


def interface_induction():
 return dict(counterBits=16,initialCounter=0,entryStride=16,declaringTypeComparedBeforeSelect=True,
  boundedByUnsignedRuntimeInterfaceCount=True,maximumPossibleVisitedRecords=65535,
  counterCannotWrapBeforeBoundExit=True,matchingRecordAddsOwnUnsignedSlotToSignedOffsetThenSelects16ByteVtablePair=True,
  firstMatchingRecordSelected=True,noMatchCallsActualResolver=True,liveInterfacePairIdentityObserved=False)


def derive(image,pins):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.memorypack import leveldata_patrol_lookup_sources as lookup_owner,leveldata_patrol_loader_sources as loader_owner,pointer_param as pointer
 from scripts.game_data.memorypack import leveldata_patrol_class_preparation_sources as prepare_owner
 _publication_gate(image,pins);base=image.pe.image_base;lookup=lookup_owner.derive(image,pins);loader=loader_owner.derive(image,pins);ctx=NativeReferenceContext(image)
 need('same-current-owned-lookup-lead-and-loader-construction',loader['proof']['controllerConstruction']['proof']['lead']==lookup['proof']['leadSource'])
 field,=[f for f in loader['proof']['parameterFields']if f['field']['field'][:2]==['Beyond.Resource.SimpleAssetLoader','Beyond.Resource.RootCategory']]
 need('independent-own-RootCategory-byte-source',field['bytes']==1 and field['backingType']=='byte')
 entry=base+lookup['proof']['leadSource']['proof']['actualTargets']['TryLoad'];body=pointer.owned(image,entry)
 programs=[program(body['regions'],entry,loaded=l,matched=m,miss_one=n,root_category_offset=field['fieldOffset'])
  for l in(False,True)for m,n in((True,False),(True,True),(False,False))]
 need('same-literal-inline-source-target',len({p['actualInlineTargetVa']for p in programs})==1)
 children={}
 for p in programs:
  for call in p['calls']:
   role=call['role']
   if role in children:need('same-actual-child-target:'+role,children[role]['entryRva']==call['targetVa']-base);continue
   if role=='prepare-receiver-class':
    prep=prepare_owner.derive(image,pins,target=call['targetVa']);prepare_owner.validate(prep,pins)
    need('same-actual-zero-write-preparation-source',prep['actualEntryRva']==call['targetVa']-base and
     prep['selectedNormalPreparationNoNonframeWritesProved']is True)
    children[role]=dict(entryRva=prep['actualEntryRva'],preparationSource=prep,selectedNormalEffectsProved=True);continue
   b=pointer.owned(image,call['targetVa']);children[role]=dict(entryRva=b['pointer']-base,sourceWindows=b['windows'],
    sourceRegions=[[a,h.hex()]for a,h in b['regions']],rows=b['rows'],effectsProved=False)
 usages=[derive_typed_usage_context(image,a-base,label='storyPatrolAsset.actualClass')for a in programs[0]['classUsageInstructions']]
 need('actual-Type-and-ResourceManager-classes',[u.get('typeName')for u in usages]==['System.Type','Beyond.Resource.ResourceManager']and all(u.get('tag')==1 for u in usages))
 td=ctx.index.types['Beyond.Resource.FAssetProxyLoaderHandle'];size=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+td.index*8)
 need('own-actual-managed20-handle-layout',ctx.is_value_type('Beyond.Resource.FAssetProxyLoaderHandle')and image.pe.u32_at_va(size)==36)
 field,=[f for f in image.metadata.fields_for(td)if not ctx.field_attributes(f.type_index)&16]
 handle_field=list(ctx.field('Beyond.Resource.FAssetProxyLoaderHandle::'+image.metadata.string(field.name_index)))
 need('own-proxy-handle-field',handle_field==['Beyond.Resource.FAssetProxyLoaderHandle','Beyond.Resource.FAssetProxyHandle',16])
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-asset-tryload-inline-source',nativeInputs=pins,
  proof=dict(lookupSource=lookup,loaderSource=loader,sourceWindows=body['windows'],sourceRegions=[[a,h.hex()]for a,h in body['regions']],
   programs=programs,interfaceInduction=interface_induction(),actualClassUsages=usages,
   handleLayout=dict(typeDefinition=td.index,boxedBytes=36,managedBytes=20,field=handle_field,wireGrammarAdmitted=False),children=children),
  selectedInterfaceAndInlineTryLoadHandleTransferSourceProved=True,actualResourceRequestOrRetainEffectsProved=False,
  liveAssetOrInterfaceSelectionObserved=False,runtimeInvocationObserved=False,playbackProved=False,wholeConversionProved=False,
  evidenceBoundary=dict(exact='Actual bounded interface record lookup/slot and selected inline code, own RootCategory constructor/field source, complete success/failure20-byte handle transfer/retain arguments/full return frames.',
   conditional=__doc__,unresolved=['actual class/context/interface callback selection','resource request/runtime Type/retention helper effects','actual live asset existence, Get selection and controller activation']))))
