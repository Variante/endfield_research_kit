"""Own SequenceActionData's conditional ordinary-reference lifecycle.

The existing Sequence source proves an existing wrapper. The canonical adapter
precreates that wrapper before its selected callback. This component proves
its concrete holder, constructors and exact reference ABI; it supplies no
array elements, action routes or wire grammar. Runtime allocation descriptors,
ready metadata, normal typed fresh zeroed allocation and disabled collector
are explicit conditions of the selected complete source paths.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack import scalar_param_native as scalar

LABEL='skillSequenceReferenceSources'
TYPE='Beyond.Gameplay.Core.SequenceActionData'
ARRAY='Beyond.Gameplay.Core.AbilityAction+AbilityActionData[]'


def need(check,expected,actual):scalar.need(LABEL,check,expected,actual)


def constructor_program(regions,entry,*,wrapper):
    """Full source path through the reference-array generic allocator branch.

    The array class has references (class flag bit0x20). Its prepared runtime
    descriptor selects the generic fallback with a nonnull GC descriptor.
    The helper receives size32 and that very class, and returns the fresh
    empty array. Neither branch conditions nor compatible helper effects are
    asserted as a live runtime observation.
    """
    need('literal-constructor-profile',True,type(wrapper)is bool)
    g=BytesPath(regions,entry);original=None;ready=None
    if wrapper:
        g.take('4055','4157','4883ec38')
        ready=g.relative('803d')+1;g.take('00','4c8bf9');g.branch('75',True,1)
        at=g.at;cell=g.relative('488b0d');allocate=g.relative('e8')
        original=dict(instruction=at,cell=cell,allocate=allocate)
        g.take('488be8','4885c0');g.branch('0f84',False)
        g.take('48895c2450','48897c2430')
    else:
        g.take('4154','4156','4883ec28','4c8bf1','48895c2440','48897c2420')
    array_at=g.at;array_cell=g.relative('488b3d');g.take('488bcf')
    if wrapper:g.take('4c896c2428')
    prepare=g.relative('e8')
    g.take('f6873801000020')
    collector_base=g.relative('4c8d2d'if wrapper else'4c8d25')
    g.branch('75',True,1) # Has reference elements, never the non-reference shortcut.
    g.take('488b4740','83782800');g.branch('0f8d',True)
    g.take('48837f0800','b920000000');g.branch('74',False,1)
    g.take('488bd7');array_allocate=g.relative('e8');g.jump('eb',1)
    g.take('488bd8');array_flag=g.relative('f605')+1;g.take('80','48c7431800000000')
    g.branch('74',True,1)
    collector=g.relative('833d')+1;g.take('00')
    if wrapper:
        g.take('488b7c2430','48895d10','488b5c2450');g.branch('74',True,1)
        again=g.relative('833d')+1;g.take('00','49896f10');g.branch('74',True,1)
        need('one-disabled-collector',collector,again)
        g.take('4c8b6c2428','4883c438','415f','5d','c3')
    else:
        g.take('488b7c2420','49895e10','488b5c2440');g.branch('74',True,1)
        g.take('4883c428','415e','415c','c3')
    return dict(selectedBytes=g.seen,wrapperConstructor=wrapper,metadataReadyFlag=ready,
        originalAllocation=original,arrayClassUsage=dict(instruction=array_at,cell=array_cell),
        classPrepareTarget=prepare,arrayAllocatorTarget=array_allocate,arrayAllocationBytes=32,
        arrayClassArgument='rdx exact prepared class',arrayHasReferencesRequired=True,
        runtimeDescriptorNonnegativeRequired=True,gcDescriptorNonNullRequired=True,
        arrayLength=0,arrayPayloadBytes=0,optionalArrayHelperDisabledFlag=array_flag,
        disabledCollector=collector,collectorBase=collector_base,originalActionDataOffset=16,
        wrapperOriginalHolderOffset=16 if wrapper else None,
        normalReturn=True,entryRspRestored=True,
        restoredNonvolatiles=['rbx','rdi','rbp','r13','r15']if wrapper else['rbx','rdi','r12','r14'],
        wireBytes=0,liveRuntimeSelectionObserved=False)


def factory_program(regions,entry):
    """Own CreateInstance, including the actual named Original constructor."""
    g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20')
    ready=g.relative('803d')+1;g.take('00','488bf9');g.branch('75',True,1)
    at=g.at;cell=g.relative('488b0d');allocate=g.relative('e8')
    g.take('488bd8','4885c0');g.branch('75',True,1)
    g.take('33d2','488bcb');constructor=g.relative('e8')
    g.take('488d4f10','48895f10','488b5c2430','4883c420','5f')
    barrier=g.relative('e9')
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,
        originalClassUsage=dict(instruction=at,cell=cell),allocate=allocate,
        originalConstructorTarget=constructor,wrapperHolderOffset=16,
        unchangedFreshOriginal=True,barrierTarget=barrier,normalReturnViaBarrier=True,
        entryRspRestored=True,wireBytes=0)


def derive(image,pins):
    """Re-prove every lifecycle/context on the caller's selected open image."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack.pointer_param import owned,methods,leaf
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.skill_root_child_bindings import reference_reader_abi
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _selected_wrapper,_fast_barrier
    _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image)
    wrapper=_selected_wrapper(image,'Beyond.MemoryPack.Beyond_Gameplay_Core_SequenceActionDataForMemoryPack')
    need('exact-sequence-original',TYPE,wrapper.wrapped_type)
    need('wrapper-holder',(wrapper.name,TYPE,16),ctx.field(wrapper.name+'::__instance'))
    need('own-array-field',(TYPE,ARRAY,16),ctx.field(TYPE+'::actionData'))
    flags=[ctx.field(TYPE+'::'+name)for name in('onlyExecuteWhenSourceIsGuard','onlyExecuteWhenSourceIsMainChar')]
    need('own-distinct-zero-initialized-flags',True,
        all(field[:2]==(TYPE,'bool')and 24<=field[2]<32 for field in flags)
        and flags[0][2]!=flags[1][2])
    mm=methods(image,wrapper);getter=leaf(image,image.method_pointer_va(mm['GetValue']),['488B4110','C3'])
    scalar.owned_method_abi(image,ctx,mm['GetValue'].index,wrapper.type_definition,
        (TYPE,18,False),[],LABEL+'.getter')
    bodies={name:owned(image,image.method_pointer_va(mm[name]))for name in('.ctor','CreateInstance')}
    om,=[m for m in image.metadata.methods_for(ctx.index.types[TYPE])
        if image.metadata.string(m.name_index)=='.ctor'and m.parameter_count==0]
    scalar.owned_method_abi(image,ctx,om.index,om.declaring_type,('void',1,False),[],LABEL+'.originalConstructor')
    original_body=owned(image,image.method_pointer_va(om))
    ctor=constructor_program(bodies['.ctor']['regions'],bodies['.ctor']['pointer'],wrapper=True)
    original_ctor=constructor_program(original_body['regions'],original_body['pointer'],wrapper=False)
    factory=factory_program(bodies['CreateInstance']['regions'],bodies['CreateInstance']['pointer'])
    need('factory-calls-own-original-constructor',original_body['pointer'],factory['originalConstructorTarget'])
    need('same-typed-original-allocator',factory['allocate'],ctor['originalAllocation']['allocate'])
    usages={}
    for role,usage,nominal in(
        ('wrapperOriginal',ctor['originalAllocation'],TYPE),
        ('factoryOriginal',factory['originalClassUsage'],TYPE),
        ('wrapperArray',ctor['arrayClassUsage'],ARRAY),
        ('originalArray',original_ctor['arrayClassUsage'],ARRAY)):
        observed=derive_typed_usage_context(image,usage['instruction']-base,label=LABEL+'.'+role)
        need('exact-allocation-class:'+role,(1,nominal),(observed['tag'],observed['typeName']))
        scalar.ordinary(image,ctx.type_pointer(observed['typeIndex']),29 if nominal==ARRAY else 18,
            LABEL+'.'+role,reference=True)
        usages[role]=observed
    need('same-array-runtime-class',usages['wrapperArray']['typeIndex'],usages['originalArray']['typeIndex'])
    for key in('classPrepareTarget','arrayAllocatorTarget','disabledCollector','collectorBase','optionalArrayHelperDisabledFlag'):
        need('same-array-constructor-helper:'+key,ctor[key],original_ctor[key])
    barrier,barrier_proof,_=_fast_barrier(image,factory['barrierTarget'])
    need('same-disabled-collector',base+barrier_proof['disabledFlagRva'],ctor['disabledCollector'])
    pair=derive_pair(image,TYPE,wrapper.name);adapter=derive_adapter(image,pins,pair,wrapper)
    need('same-own-getter',getter['entryRva'],adapter['getterMethod'][3])
    reader=reference_reader_abi(image,pins);_publication_gate(image,pins)
    return dict(schema='endfield.sequence-reference-lifecycle-source.v1',nativeInputs=dict(pins),
        status='validated-conditional-reference-lifecycle',typeName=TYPE,wrapperName=wrapper.name,
        getter=getter,wrapperConstructor=ctor,originalConstructor=original_ctor,factory=factory,
        codeWindows={**{name:body['windows']for name,body in bodies.items()},'original.ctor':original_body['windows']},
        typedClassUsages=usages,barrier=barrier,barrierProof=barrier_proof,adapter=adapter,referenceAbi=reader,
        **{key:reader[key]for key in('referenceReaderMethodDefinition','referenceReaderTargetRva')},
        ownConcreteGetterSemanticsProved=True,ownConcreteFactorySemanticsProved=True,
        canonicalAdapterPrecreatesWrapperRequired=True,existingWrapperSourceRequired=True,
        ordinaryOriginalReadValueSourceAdmitted=True,wholeGrammarAdmitted=False,
        evidenceBoundary=dict(exact='Own holder16 getter, named Original constructor and CreateInstance, complete selected wrapper/original constructor paths, exact array-class usages, eager adapter/conversion and generic reference reader identity.',
            conditional=__doc__,unresolved=['Sequence child wire grammar','actual parent typed call','live callback/provider/allocator selection','whole SkillData and physical EOF']))
