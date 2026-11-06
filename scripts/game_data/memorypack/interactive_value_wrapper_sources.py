"""Owned fields of the finite Interactive inline value wrappers.

Each declaration comes from independently checked whole-value/accessor native
programs. A wrapper's embedded value is never treated as an Original reference
holder, and these fields alone admit neither a wire grammar nor a provider.
"""
from scripts.game_data.memorypack import interactive_value_layouts as layouts

TYPES={layouts.MOUNT}|{layouts.OPTIONAL+t+'>'for t in layouts.REFERENCES}
PROFILE='interactive-inline-value-wrapper-field'


def need(check,condition):
    if not condition:raise ValueError('interactiveValueWrapper.'+check)


def derive_setter(image,pins,member,wrappers,barrier):
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import pointer_param as pointer
    from scripts.game_data.memorypack.reference_param_profile import _method_row
    wrapper=wrappers[member.declaring_wrapper];name=wrapper.wrapped_type
    need('finite-own-inline-value-wrapper',name in TYPES and not wrapper.abstract)
    layout=layouts.derive(image,pins,name,barrier=image.pe.image_base+barrier)
    field,=[f for f in layout['fields']if f['fieldName']==member.name]
    method=image.metadata.methods[member.method_index]
    need('same-owned-compiled-field',field['method']==_method_row(image,method)
        and field['declaredType']==member.declared_type and method.declaring_type==wrapper.type_definition)
    parameter,=image.metadata.parameters_for(method);ctx=NativeReferenceContext(image)
    raw=image.pe.bytes_at_va(ctx.type_pointer(parameter.type_index),16)
    return dict(method=field['method'],member=member.row(),targetField=name+'::'+member.name,
        fieldOffset=16+field['offset'],parameterTypeRecordHex=raw.hex().upper(),storedBytes=field['bytes'],
        profile=PROFILE,inlineValueWrapperLayout=layout,program=dict(field['program'],storedBytes=field['bytes']),
        getter=None,incomingValueStoredUnchanged=True,childGrammarAdmitted=False,factoryAdmitted=False)


def require_inline_fields(setters):
    """Pure closed roster check before the caller assigns embedded receiver roles."""
    need('nonempty-exact-inline-roster',type(setters)is list and len(setters)==2)
    layout=setters[0].get('inlineValueWrapperLayout',{})
    need('own-finite-layout',layout.get('typeName')in TYPES and layout.get('schema')=='endfield.interactive-value-layout.v1'
        and layout.get('managedBytes')==16 and layout.get('referenceLaneOffsets')==[8]
        and layout.get('wireGrammarAdmitted')is False and layout.get('openGenericOffsetsUsed')is False)
    need('both-own-exact-fields',all(s.get('profile')==PROFILE and s.get('inlineValueWrapperLayout')==layout
        and s.get('getter')is None and s.get('incomingValueStoredUnchanged')is True
        and s.get('childGrammarAdmitted')is False and s.get('factoryAdmitted')is False
        and s.get('method')==f['method']and s.get('member',{}).get('name')==f['fieldName']
        and s.get('member',{}).get('declaredType')==f['declaredType']
        and s.get('targetField')==layout['typeName']+'::'+f['fieldName']
        and s.get('fieldOffset')==16+f['offset']and s.get('storedBytes')==f['bytes']
        and s.get('program',{}).get('selectedBytes')==f['program']['selectedBytes']
        for s,f in zip(setters,layout.get('fields',[]),strict=True)))
    return layout


def prefix_program(rows,entry,header,*,base,barrier,existing,ff,wrapper_name,allocate,constructor=None):
    """Complete initialized direct-value entry, allocation/zero and FF paths."""
    from scripts.game_data.memorypack.generated_reader_sources import _Path
    from scripts.game_data.memorypack import buff_ec_profiles_native as ec
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    need('finite-literal-entry-path',type(existing)is bool and type(ff)is bool)
    need('finite-called-constructor-owner',constructor is None or type(constructor)is int and constructor>base
        and wrapper_name=='Beyond.MemoryPack.Beyond_Gameplay_ParamListForGraphForMemoryPack')
    g=_Path(rows,entry);reader=header['readerRegister'];output=header['outputRegister']
    for at,h in header['prologue']:g.take(site=[base+at,h])
    saves={base+header[role+'Save'][0]:header[role+'Save']for role in('reader','output')}
    start=base+header['call'][0]if header['mode']=='helper'else base+header['bufferPredicate'][0]
    guards=[]
    # Exact current warm metadata flags and wrapper class-state guards only.
    # No unknown call, store or branch is silently passed over.
    for _ in range(20):
        row=g.row();raw=ec.raw(row);at=ec.va(row)
        if at==start:break
        if at in saves:g.take(site=[base+saves.pop(at)[0],raw.hex().upper()]);continue
        if len(raw)==7 and raw[:2]==bytes.fromhex('803d')and raw[-1]==0:
            guard=dict(kind='metadata-ready',instruction=ec.site(row,base));g.take()
            while ec.va(g.row())in saves:
                at=ec.va(g.row());site=saves.pop(at);g.take(site=[base+site[0],site[1]])
            g.branch(False);guards.append(guard);continue
        if raw[:3]==bytes.fromhex('488b0d')and len(raw)==7:
            load=g.take();cmp=g.take('cmp dword [rcx+0xe0], 0x0')
            need('literal-own-wrapper-state-compare',ec.raw(cmp)==bytes.fromhex('83b9e000000000'))
            g.branch(False);guards.append(dict(kind='wrapper-class-ready',instruction=ec.site(load,base)));continue
        if header['mode']=='helper'and row['text']in(
                f"lea rdx, [rsp+{header['headerLocalDisplacement']:#x}]",
                f"mov byte [rsp+{header['headerLocalDisplacement']:#x}], 0x0",f'mov rcx, {reader}'):
            g.take();continue
        raise ValueError('interactiveValueWrapper.unowned-entry-prefix:'+str(row))
    else:raise ValueError('interactiveValueWrapper.entry-prefix-bound')
    need('all-owned-entry-arguments-saved',not saves)
    if header['mode']=='helper':
        g.call(base+header['helperTargetRva']);g.take('test al, al');g.branch(ff)
    else:
        g.take(site=[base+header['bufferPredicate'][0],header['bufferPredicate'][1]])
        edge=control_transfer(g.row());need('buffered-header-edge',edge.get('conditionCode')in(12,13));g.take()
        if edge['conditionCode']==13:g.at=edge['target']
        for at,h in header['sourceProgram']:
            row=g.take(site=[base+at,h]);flow=control_transfer(row)
            if flow['kind']=='conditional':
                need('nonnegative-header-update',flow['conditionCode']in(8,9))
                if flow['conditionCode']==9:g.at=flow['target']
        g.take(site=[base+header['nullCompare'][0],header['nullCompare'][1]]);g.branch(ff)
    allocation=None
    if ff:
        for at,h in header['nullReturnProgram']:
            row=g.take(site=[base+at,h]);flow=control_transfer(row)
            if flow['kind']=='jump':g.at=flow['target']
            elif flow['kind']=='conditional':
                need('exact-disabled-collector-edge',flow['conditionCode']==4 and header['nullReturn']['disabledCollectorFlagRva']is not None)
                g.at=flow['target']
    else:
        while g.row()['text'].startswith('mov [rsp+')and g.row().get('memoryOperation',{}).get('register')in('rbx','rbp','rsi','rdi'):
            g.take()
        g.take(f'cmp qword [{output}], 0x0');g.branch(not existing)
        if not existing:
            load=g.take();need('actual-typed-wrapper-allocation',ec.raw(load)[:3]==bytes.fromhex('488b0d')and len(ec.raw(load))==7)
            g.call(allocate)
            if constructor is not None:g.take('mov rbp, rax')
            g.take('test rax, rax');g.branch(False)
            if constructor is None:
                g.take('xorps xmm0, xmm0');g.take(f'mov rcx, {output}')
                zero=g.take('movups [rax+0x10], xmm0');need('whole-embedded-value-zero',ec.raw(zero)==bytes.fromhex('0f114010'))
                g.take(f'mov [{output}], rax');g.call(barrier)
            else:
                g.take('xor edx, edx');g.take('mov rcx, rax');g.call(constructor)
                g.take(f'mov rcx, {output}');g.take(f'mov [{output}], rbp');g.call(barrier)
            if g.row()['text']=='nop':g.take()
            if control_transfer(g.row())['kind']=='jump':g.jump()
            allocation=dict(usageInstruction=ec.site(load,base),inlineCompleteValueZero=constructor is None,wrapperName=wrapper_name,
                **(dict(actualConstructorTargetRva=constructor-base)if constructor is not None else{}))
        if header.get('resultLoad')is not None:g.take(site=[base+header['resultLoad'][0],header['resultLoad'][1]])
        need('exact-count-join',g.at==base+header['memberCountInstruction'][0])
    return dict(selectedRows=g.seen,existing=existing,wrapperNull=ff,allocation=allocation,initializedGuards=guards)


def _complete(image,pins,wrapper,targets,barrier,disabled_flag,*,body=None,formatter=False):
    """Fresh complete Reader/slot5 programs, retaining child obligations."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.memorypack import generated_action_sources as actions,generated_header_sources as headers
    from scripts.game_data.memorypack import generated_reader_sources as readers,pointer_param as pointer
    from scripts.game_data.memorypack.reference_param_profile import _method_row
    base=image.pe.image_base;ctx=NativeReferenceContext(image);mm=pointer.methods(image,wrapper)
    need('finite-own-value-reader',wrapper.wrapped_type in TYPES and 'OnDeserialized'not in mm)
    layout=layouts.derive(image,pins,wrapper.wrapped_type,barrier=base+barrier)
    if not formatter:
        scope,owned=actions._derive_with_source(image,pins,wrapper.name,targets,barrier,disabled_flag)
        family,windows,rows,partition=owned;entry=base+scope['method'][3]
    else:
        from scripts.game_data.memorypack.generated_inline_value_scope import derive_scope
        from scripts.game_data.memorypack.generated_value_programs import complete_program
        from scripts.game_data.memorypack import generated_owned_code_sources
        entry=body['pointer'];family,windows,rows,partition=generated_owned_code_sources.source_family(image,pins,entry_rva=entry-base)
        need('same-actual-slot5-body',body['windows']==windows)
        method=body['method'];claim,enums=actions._claim(image,wrapper)
        header,count=headers.derive(image,rows,entry,2,actions.ec.source_offsets(image),barrier,
            disabled_flag=disabled_flag,owned_partition=partition,argument_registers=('rdx','r8'))
        scope=derive_scope(image,pins,wrapper,targets,barrier,claim,enums,method,family,windows,rows,header,count,program_prover=complete_program)
    fields=scope.get('richSetters')
    need('complete-own-field-roster',fields is not None);require_inline_fields(fields)
    allocators=[]
    for i,row in enumerate(rows[:-1]):
        if len(actions.ec.raw(row))!=7 or actions.ec.raw(row)[:3]!=bytes.fromhex('488b0d')or actions.ec.raw(rows[i+1])[:1]!=b'\xe8':continue
        usage=derive_typed_usage_context(image,actions.ec.va(row)-base,label='interactiveValueWrapper.allocation')
        if(usage.get('tag'),usage.get('typeName'))==(1,wrapper.name):allocators.append(control_transfer(rows[i+1])['target'])
    need('one-actual-wrapper-allocator',len(set(allocators))==1);allocate=allocators[0]
    positive=readers.positive_program(rows,scope,base);programs=[]
    for existing,ff in((False,False),(True,False),(False,True),(True,True)):
        selected=prefix_program(rows,entry,scope['headerProof'],base=base,barrier=base+barrier,
            existing=existing,ff=ff,wrapper_name=wrapper.name,allocate=allocate)
        path=selected.pop('selectedRows')+([]if ff else positive)
        for guard in selected['initializedGuards']:
            if guard['kind']=='wrapper-class-ready':
                usage=derive_typed_usage_context(image,guard['instruction'][0],label='interactiveValueWrapper.classReady')
                need('exact-own-ready-wrapper-class',(usage.get('tag'),usage.get('typeName'))==(1,wrapper.name));guard['typedRequest']=usage
        if selected['allocation']is not None:
            usage=derive_typed_usage_context(image,selected['allocation']['usageInstruction'][0],label='interactiveValueWrapper.selectedAllocation')
            need('exact-selected-wrapper-class',(usage.get('tag'),usage.get('typeName'))==(1,wrapper.name));selected['allocation']['typedRequest']=usage
        frame=readers.frame_program(path,header_local=scope['headerProof'].get('headerLocalDisplacement'),base=base,
            tail_barrier=base+barrier if ff or scope.get('referenceBarrierTargetRva')==barrier else None)
        programs.append(dict(**selected,selectedProgram=[actions.ec.site(r,base)for r in path],frame=frame))
    _publication_gate(image,pins)
    return dict(schema='endfield.interactive-inline-value-wrapper-source.v1',nativeInputs=pins,
        typeName=wrapper.wrapped_type,wrapperName=wrapper.name,layout=layout,sourceScope=scope,programs=programs,
        concreteFormatter=formatter,completeSelectedCallerAdmitted=True,childGrammarAdmitted=False,wholeOwnerAdmitted=False)


def derive(image,pins,wrapper,targets,barrier,disabled_flag):
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import generated_lifecycle_sources as life,pointer_param as pointer
    from scripts.game_data.memorypack.reference_param_profile import _method_row
    result=_complete(image,pins,wrapper,targets,barrier,disabled_flag)
    def formatter_source(image,wrapper,reader,method,body):
        body=dict(body,method=_method_row(image,method))
        proof=_complete(image,pins,wrapper,targets,barrier,disabled_flag,body=body,formatter=True)
        return dict(completeSelectedFormatterAdmitted=True,childGrammarAdmitted=False,
            programs=proof['programs'],inlineValueWrapperSource=proof)
    mm=pointer.methods(image,wrapper)
    from scripts.game_data.memorypack import buff_ec_profiles_native as ec
    formatter=image.named_types[wrapper.name+'+'+wrapper.name.rsplit('.',1)[-1]+'Formatter']
    method,=[m for m in image.metadata.methods_for(formatter)if image.metadata.string(m.name_index)=='Deserialize']
    raw=image.pe.bytes_at_va(image.method_pointer_va(method),10)
    ordinary_forwarder=raw.startswith(bytes.fromhex('48895c2408574883ec20'))
    result['formatterSource']=life._concrete_formatter(image,NativeReferenceContext(image),wrapper,mm['Deserialize'],
        formatter_prover=None if ordinary_forwarder else formatter_source,pins=pins)
    return result
