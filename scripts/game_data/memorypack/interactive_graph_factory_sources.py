"""ParamListForGraph's own inline empty-list constructor and holder writes."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

TYPE='Beyond.Gameplay.ParamListForGraph'
LIST='System.Collections.Generic.List`1<Beyond.Gameplay.ParamKeyValue>'


def need(check,condition):
    if not condition:raise ValueError('interactiveGraphFactory.'+check)


def program(regions,entry,s):
    g=BytesPath(regions,entry);g.take('48895c2418','55','4883ec20')
    flag=g.relative('803d')+1;g.take('00','488be9');g.branch('0f84',False)
    original_site=g.at;original_cell=g.relative('488b0d');g.take('48897c2438');g.call(s['allocate'])
    g.take('488bd8','4885c0');g.branch('0f84',False)
    list_site=g.at;list_cell=g.relative('488b0d');g.call(s['allocate'])
    g.take('488bf8','4885c0');g.branch('74',False,1)
    g.take('4889742430','33d2');method_site=g.at;method_cell=g.relative('488b35')
    g.take('488b4e20','488b89c0000000');resolver=g.relative('e8')
    g.take('83b8e000000000');g.branch('74',False,1)
    g.take('488b4e20','33d2','488b89c0000000');g.call(resolver)
    g.take('488b88b8000000','488b01','488d4f10','48894710');g.call(s['barrier'])
    g.take('488d4b10','48897b10');g.call(s['barrier'])
    g.take('488d4d10','48895d10','488b742430','488b7c2438','488b5c2440','4883c420','5d')
    need('same-complete-holder-tail',g.relative('e9')==s['barrier'])
    return dict(selectedBytes=g.seen,initializedFlag=flag,
        allocation=dict(site=original_site,cell=original_cell),allocationTarget=s['allocate'],
        listAllocation=dict(site=list_site,cell=list_cell),listMethodContext=dict(site=method_site,cell=method_cell),
        initializedClassResolver=resolver,baseHolderOffset=16,typedCacheOffset=None,
        inlineHolderWrites=[dict(offset=16,bytes=8,sameAllocatedReference=True)],
        sameAllocatedOriginalStored=True,entryRspRestored=True,allNonvolatilesRestored=True,normalReturnViaBarrier=True,
        emptyListReferenceStoredAt16=True,emptyListItemsReferenceStoredAt16=True,
        originalConstructorCalled=False,childGrammarAdmitted=False)


def derive(image,ctx,wrapper,body,s,original_ctor):
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.memorypack import generated_lifecycle_sources as life,scalar_param_native as scalar
    if wrapper.wrapped_type!=TYPE:return NotImplemented
    md=image.metadata;base=image.pe.image_base
    # Only the fully inlined .ctor program is owned here. CreateInstance's
    # actual zero-context Original call remains under the existing factory.
    if not body['regions'][0][1].startswith(bytes.fromhex('48895c2418554883ec20')):return NotImplemented
    proof=program(body['regions'],body['pointer'],s)
    allocation=derive_typed_usage_context(image,proof['allocation']['site']-base,label='interactiveGraphFactory.original')
    list_allocation=derive_typed_usage_context(image,proof['listAllocation']['site']-base,label='interactiveGraphFactory.list')
    method=derive_typed_usage_context(image,proof['listMethodContext']['site']-base,label='interactiveGraphFactory.listCtor')
    need('same-own-typed-original-allocation',(allocation['tag'],allocation['typeName'])==(1,TYPE))
    need('same-own-typed-list-allocation',(list_allocation['tag'],list_allocation['typeName'])==(1,LIST))
    need('actual-exact-closed-list-constructor',(method['tag'],method['typeName'],method['methodName'],method['classArguments'],method['methodArguments'])
        ==(6,'System.Collections.Generic.List`1','.ctor',['Beyond.Gameplay.ParamKeyValue'],[]))
    owner=ctx.index.types['System.Collections.Generic.List`1'];context=ContextSymbols(image).context(owner.index)
    scalar.owned_method_abi(image,ctx,method['methodSpec'][0],owner.index,('void',1,False),[],'interactiveGraphFactory.listCtor')
    member,=wrapper.members
    need('own-literal-Original-list-field',member.declared_type==LIST and ctx.field(TYPE+'::'+member.name)==(TYPE,LIST,16))
    fields=[f for f in md.fields_for(ctx.index.types[TYPE])if not ctx.field_attributes(f.type_index)&16]
    need('sole-own-Original-list-field',len(fields)==1 and md.string(fields[0].name_index)==member.name)
    raw=image.pe.bytes_at_va(ctx.type_pointer(fields[0].type_index),16)
    need('same-closed-list-field-carrier',raw[10:12]==bytes((21,0))and raw[:8]==bytes.fromhex(list_allocation['typeRawHex'])[:8])
    slot,=[r for r in context['entries']if r['relativeSlot']==0]
    need('own-constructor-class-context-slot',slot['kind']==2
        and slot['type']['definition']['name']=='System.Collections.Generic.List`1')
    argument,=slot['type']['classArguments']
    need('own-constructor-reciprocal-VAR0',(argument['parameterOwner'].get('typeIndex'),argument['parameterOwner'].get('ordinal'))==(owner.index,0))
    statics=[f for f in md.fields_for(owner)if ctx.field_attributes(f.type_index)&16 and not ctx.field_attributes(f.type_index)&64]
    need('one-actual-static-empty-array',len(statics)==1)
    empty_raw=image.pe.bytes_at_va(ctx.type_pointer(statics[0].type_index),16)
    need('own-List-static-array-record',empty_raw[10:12]==bytes((29,0)))
    need('same-actual-static-array-context-VAR',int.from_bytes(empty_raw[:8],'little')==argument['typePointerVa'])
    element=ContextSymbols(image).type(int.from_bytes(empty_raw[:8],'little'))
    need('own-List-VAR0-empty-array',element['parameterOwner'].get('typeIndex')==owner.index
        and element['parameterOwner'].get('ordinal')==0)
    empty=dict(rawTypeRecordHex=empty_raw.hex().upper(),element=element)
    resolver=life._initialized_indexer(image,proof['initializedClassResolver'])
    return dict(program=proof,originalConstructor=None,proof=dict(wrapperName=wrapper.name,typeName=TYPE,
        completeSelectedFactoryAdmitted=True,childGrammarAdmitted=False,originalAllocation=allocation,
        listAllocation=list_allocation,actualListConstructorContext=method,listClassContext=context,
        emptyArrayType=empty,initializedClassResolver=resolver,
        condition='Exact selected closed List<ParamKeyValue> context and its sole empty-array static field; zeroed fresh allocations, initialized class state, ordinary noninterfering helper returns and disabled barriers. No runtime constructor invocation or child wire grammar is inferred.'))


def formatter_source(image,wrapper,reader,method,body,*,pins):
    """Own the inlined static reader at its real slot5 entry and shifted ABI."""
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.memorypack import generated_action_sources as actions,generated_header_sources as headers
    from scripts.game_data.memorypack import generated_reader_sources as readers,pointer_param as pointer
    from scripts.game_data.memorypack.generated_inline_value_scope import derive_scope
    from scripts.game_data.memorypack.generated_value_programs import complete_program
    from scripts.game_data.memorypack.generated_owned_code_sources import source_family
    from scripts.game_data.memorypack.interactive_value_wrapper_sources import prefix_program
    from scripts.game_data.memorypack.reference_param_profile import _method_row
    need('finite-own-formatter',wrapper.wrapped_type==TYPE)
    # The opened image has one authenticated selected build. Reuse only its
    # freshly checked preparation; no diagnostic receipt supplies these pins.
    targets,barrier,disabled=actions._prepare(image,pins);base=image.pe.image_base;entry=body['pointer']
    family,windows,rows,partition=source_family(image,pins,entry_rva=entry-base,tail_targets=(base+barrier,))
    need('same-current-formatter-windows',windows==body['windows'])
    claim,enums=actions._claim(image,wrapper)
    header,count=headers.derive(image,rows,entry,1,actions.ec.source_offsets(image),barrier,
        disabled_flag=disabled,owned_partition=partition,argument_registers=('rdx','r8'))
    scope=derive_scope(image,pins,wrapper,targets,barrier,claim,enums,_method_row(image,method),family,windows,rows,header,count,program_prover=complete_program)
    allocators=[]
    for i,row in enumerate(rows[:-1]):
        if len(actions.ec.raw(row))!=7 or actions.ec.raw(row)[:3]!=bytes.fromhex('488b0d')or actions.ec.raw(rows[i+1])[:1]!=b'\xe8':continue
        usage=derive_typed_usage_context(image,actions.ec.va(row)-base,label='interactiveGraphFactory.wrapperAllocation')
        if(usage.get('tag'),usage.get('typeName'))==(1,wrapper.name):allocators.append(control_transfer(rows[i+1])['target'])
    need('one-actual-formatter-wrapper-allocator',len(set(allocators))==1);allocate=allocators[0]
    mm=pointer.methods(image,wrapper);constructor=image.method_pointer_va(mm['.ctor']);positive=readers.positive_program(rows,scope,base);programs=[]
    for existing,ff in((False,False),(True,False),(False,True),(True,True)):
        selected=prefix_program(rows,entry,header,base=base,barrier=base+barrier,existing=existing,ff=ff,
            wrapper_name=wrapper.name,allocate=allocate,constructor=constructor)
        for guard in selected['initializedGuards']:
            if guard['kind']=='wrapper-class-ready':
                usage=derive_typed_usage_context(image,guard['instruction'][0],label='interactiveGraphFactory.formatterClass')
                need('same-formatter-own-class',(usage.get('tag'),usage.get('typeName'))==(1,wrapper.name))
                guard['typedRequest']=usage
        if selected['allocation']is not None:
            usage=derive_typed_usage_context(image,selected['allocation']['usageInstruction'][0],label='interactiveGraphFactory.selectedAllocation')
            need('same-selected-formatter-wrapper',(usage.get('tag'),usage.get('typeName'))==(1,wrapper.name))
            selected['allocation']['typedRequest']=usage
        path=selected.pop('selectedRows')+([]if ff else positive)
        frame=readers.frame_program(path,header_local=header.get('headerLocalDisplacement'),base=base,tail_barrier=base+barrier)
        programs.append(dict(**selected,frame=frame,selectedProgram=[actions.ec.site(r,base)for r in path]))
    return dict(completeSelectedFormatterAdmitted=True,childGrammarAdmitted=False,programs=programs,
        sourceScope=scope,wrapperConstructorMethod=_method_row(image,mm['.ctor']),
        exactOwnedConstructorEffectsRequired=True,callbackAndProviderRuntimeSelectionObserved=False)
