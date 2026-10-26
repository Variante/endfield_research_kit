"""Exact EntityPtr40 setter bits and its one selected disabled barrier.

The native runtime tail remains opaque. This copies all forty bytes and owns
the observed barrier at value offset24 without inferring a complete reference
lane or padding map. Nominal layout, child source and parent frames are separate.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

TYPE='Beyond.Gameplay.Core.EntityPtr'
SLICES=[[0,16],[16,16],[32,8]]
OPAQUE=[[24,40]]
KNOWN_PADDING=[[1,8],[20,24]]


def need(check,condition):
    if not condition:raise ValueError('entityPtrFieldSource.'+check)


def validate_destination(offset,width,row,setter,*,base,pending):
    """Only exact physical slices or the independently owned whole setter."""
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    need('no-interleaved-opaque-destination',pending is None)
    if(offset,width)in((0,16),(16,16),(32,8)):return True
    transfer=control_transfer(row);program=setter.get('program',{})
    need('whole-owned-Entity40-setter-call',(offset,width)==(0,40)and transfer['kind']=='call'
        and transfer['target']==base+setter['method'][3]and setter.get('storedBytes')==40
        and program.get('sourceSlices')==SLICES and program.get('storedBytes')==40
        and all(program.get(key)is True for key in('wholeInputBitsStoredUnchanged','entryRspRestored',
            'normalReturnViaBarrier','disabledCollectorRequired')))
    return True


def setter_program(regions,entry,*,field,barrier,path_factory=None,getter=None):
    from scripts.game_data.memorypack.generated_inline_constructor_sources import _nonnull
    from scripts.game_data.memorypack.generated_member_sources import _displacement
    need('literal-owned-field-and-barrier',type(field)is int and 16<=field<2**31-40
        and type(barrier)is int and barrier>0 and(getter is None or type(getter)is int and getter>0))
    need('callable-only-path-factory',path_factory is None or callable(path_factory))
    g=(BytesPath if path_factory is None else path_factory)(regions,entry)
    if getter is None:g.take('4883ec28','488b4910','4885c9')
    else:
        g.take('4053','4883ec20','488bda','33d2');g.call(getter);g.take('4885c0')
    null=_nonnull(g)
    null=dict(null,bytes=bytes(g.bytes[null['nullTargetVa']+i]for i in range(6)).hex().upper())
    address=field+24
    if getter is None:
        g.take('0f1002','0f104a10',_displacement('0f1141',field),'f20f104220',
            _displacement('0f1149',field+16),_displacement('f20f1141',field+32))
        g.take('4883c1'+bytes((address,)).hex()if address<128 else'4881c1'+address.to_bytes(4,'little').hex(),'4883c428')
    else:
        g.take('0f1003',_displacement('488d48',address),'0f104b10',_displacement('0f1140',field),
            'f20f104320',_displacement('0f1148',field+16),_displacement('f20f1140',field+32),'4883c420','5b')
    at=g.at;need('same-selected-disabled-barrier',g.relative('e9')==barrier)
    result=dict(typeName=TYPE,managedBytes=40,storedBytes=40,fieldOffset=field,selectedBytes=g.seen,
        sourceSlices=[list(s)for s in SLICES],sourceValuePointer='unchanged incoming rdx',holderOffset=16,
        selectedBarrierValueOffsets=[24],barrierInstructionVa=at,barrierTargetVa=barrier,
        knownPaddingByteRanges=[list(s)for s in KNOWN_PADDING],opaqueRuntimeStorageRanges=[list(s)for s in OPAQUE],
        runtimeReferenceLayoutAdmitted=False,completeRuntimePaddingMapAdmitted=False,
        wholeInputBitsStoredUnchanged=True,opaqueRuntimeBitsPreserved=True,entryRspRestored=True,
        normalReturnViaBarrier=True,disabledCollectorRequired=True,ownedNullExit=null,
        nominalMetadataProved=False,childGrammarAdmitted=False,parentCallerFrameProved=False)
    if getter is not None:result.update(holderOffset=None,sourceValuePointer='incoming rdx preserved rbx',
        getterTargetVa=getter,getterReceiver='incoming rcx with zero edx',nonvolatileRegistersRestored=['rbx'])
    return result


def parent_program(regions,entry,*,field,source_target,barrier):
    """Exact GroupSlot hidden40 result to its same original, with no GC map."""
    from scripts.game_data.memorypack.generated_inline_constructor_sources import _nonnull
    from scripts.game_data.memorypack.generated_member_sources import _displacement
    need('literal-parent-field-and-helpers',type(field)is int and 16<=field<2**31-40
        and type(source_target)is type(barrier)is int and source_target>0 and barrier>0)
    g=BytesPath(regions,entry);context_at=g.at;context_cell=g.relative('4c8b05')
    g.take('488d4c2420','488b37','488bd3');source_at=g.at;g.call(source_target)
    nulls=[]
    for guard in('4885f6','4885c9'):
        if guard=='4885c9':g.take('488b4e10')
        g.take(guard);null=_nonnull(g)
        nulls.append(dict(null,bytes=bytes(g.bytes[null['nullTargetVa']+i]for i in range(6)).hex().upper()))
    g.take('0f10442420','0f104c2430');stores=[]
    def store(raw,offset,size):
        at=g.at;g.take(raw);stores.append(dict(instructionVa=at,hex=raw.upper(),sourceOffset=offset,storedBytes=size))
    store(_displacement('0f1141',field),0,16)
    g.take('f20f10442440')
    store(_displacement('0f1149',field+16),16,16);store(_displacement('f20f1141',field+32),32,8)
    address=field+24
    g.take('4883c1'+bytes((address,)).hex()if address<128 else'4881c1'+address.to_bytes(4,'little').hex())
    barrier_at=g.at;g.call(barrier)
    return dict(typeName=TYPE,managedBytes=40,selectedBytes=g.seen,fieldOffset=field,
        actualContextLoadInstructionVa=context_at,actualContextCellVa=context_cell,contextRegister='r8',
        sourceInstructionVa=source_at,sourceTargetVa=source_target,hiddenSourceLocal=dict(displacement=32,bytes=40),
        actualReaderRegister='rbx',outputRegister='rdi',wrapperRegister='rsi',holderOffset=16,
        fieldStores=stores,completePhysicalCopyProgram=True,opaqueRuntimeBitsPreserved=True,
        barrierInstructionVa=barrier_at,barrierTargetVa=barrier,selectedBarrierValueOffsets=[24],
        knownPaddingByteRanges=[list(s)for s in KNOWN_PADDING],opaqueRuntimeStorageRanges=[list(s)for s in OPAQUE],
        runtimeReferenceLayoutAdmitted=False,completeRuntimePaddingMapAdmitted=False,ownedNullExits=nulls,
        disabledCollectorRequired=True,nominalMetadataProved=False,actualChildReadSourceProved=False,
        parentCallerFrameProved=False,childGrammarAdmitted=False,parentFieldAdmitted=False)


def derive_setter(image,pins,member,wrappers,barrier,getter_cache):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_field_programs import _setter_metadata
    from scripts.game_data.memorypack import generated_member_sources as members,scalar_param_native as scalar,pointer_param as pointer
    from scripts.game_data.memorypack import leveldata_entity_ptr_value_sources as value
    from scripts.game_data.memorypack.generated_alpha_blend_field_sources import direct_holder
    _publication_gate(image,pins)
    ctx,wrapper,field,target,offset,method=_setter_metadata(image,wrappers,member)
    need('own-ordinary-reference-parent',member.declared_type==TYPE and not ctx.is_value_type(wrapper.wrapped_type))
    scalar.owned_method_abi(image,ctx,method.index,wrapper.type_definition,
        ('void',1,False),[(TYPE,17,False)],'entityPtrFieldSource.setter')
    need('nongeneric-owned-setter',method.generic_container_index<0)
    parameter,=image.metadata.parameters_for(method);type_pointer=ctx.type_pointer(parameter.type_index)
    raw=image.pe.bytes_at_va(type_pointer,16);nominal=value.derive_layout(image,type_pointer=type_pointer)
    body=members._body(image,image.method_pointer_va(method),pins=pins);getter=None;getter_target=None;holder=None
    if image.pe.bytes_at_va(body['pointer'],4)==bytes.fromhex('4883ec28'):
        holder=direct_holder(image,ctx,wrapper);profile='direct-base-holder-setter';source_profile='direct-opaque-EntityPtr40-setter'
    else:
        method_getter=pointer.methods(image,wrapper)['get___instance'];getter_target=image.method_pointer_va(method_getter)
        getter=members._coherent_getter(image,ctx,wrapper,method_getter,getter_cache,barrier=image.pe.image_base+barrier,pins=pins)
        profile='cached-getter-setter';source_profile='cached-opaque-EntityPtr40-setter'
    program=setter_program(body['regions'],body['pointer'],field=offset,barrier=image.pe.image_base+barrier,**(dict(getter=getter_target)if getter_target is not None else{}))
    _publication_gate(image,pins)
    return dict(method=[method.index,wrapper.name,image.metadata.string(method.name_index),body['pointer']-image.pe.image_base],
        member=member.row(),targetField=target,fieldOffset=offset,parameterTypeRecordHex=raw.hex().upper(),storedBytes=40,
        managedValueLayout=nominal,sourceFamily=body['family'],codeWindows=body['windows'],profile=profile,sourceProfile=source_profile,
        program=program,getter=getter,directHolder=holder,ordinarySourceRows=body['rows'],
        ordinarySourceRegions=[[a-image.pe.image_base,h.hex().upper()]for a,h in body['regions']],
        incomingValueStoredUnchanged=True,childGrammarAdmitted=False,factoryAdmitted=False)


def validate_event(event,setter):
    layout=setter.get('managedValueLayout',{});program=setter.get('program',{});context=event.get('context',{})
    raw=bytes.fromhex(setter.get('parameterTypeRecordHex',''))
    need('exact-own-opaque40-event-and-setter',event.get('kind')=='managed:'+TYPE
        and event.get('declaredType')==layout.get('typeName')==TYPE and event.get('mode')=='typed-managed-value'
        and event.get('resultAbi')=='hidden-local'and event.get('actualSourceProved')is True and'wireBytes'not in event
        and event.get('managedBytes')==layout.get('managedBytes')==setter.get('storedBytes')==40
        and type(layout.get('typeDefinition'))is int and len(raw)==16 and raw[10:12]==bytes((17,128))
        and int.from_bytes(raw[:8],'little')==layout['typeDefinition']
        and program.get('sourceSlices')==SLICES and program.get('storedBytes')==40
        and all(program.get(k)is True for k in('wholeInputBitsStoredUnchanged','opaqueRuntimeBitsPreserved',
            'entryRspRestored','normalReturnViaBarrier','disabledCollectorRequired')))
    for item in(event,layout,program):
        need('opaque-runtime-policy-no-invented-reference-map','referenceLaneOffsets'not in item
            and item.get('runtimeReferenceLayoutAdmitted')is False and item.get('completeRuntimePaddingMapAdmitted')is False
            and item.get('knownPaddingByteRanges')==KNOWN_PADDING and item.get('opaqueRuntimeStorageRanges')==OPAQUE
            and item.get('selectedBarrierValueOffsets')==[24])
    if event.get('sourceContextMode')=='owned-closed-forwarder':
        from scripts.game_data.memorypack.generated_module_value_forwarder_sources import context_shape,SCHEMA
        source=event.get('moduleClosedForwarderSource',{});context=source.get('proof',{}).get('internalContext',{})
        context_shape(context,TYPE)
        need('own-closed-Entity40-forwarder-source',event.get('context')is None and source.get('schema')==SCHEMA
            and source.get('typeName')==TYPE and source.get('sourceTargetRva')==event.get('sourceTargetRva')
            and source.get('actualSourceProved')is True and source.get('managedBytes')==40
            and source.get('resultAbi')=='hidden-local'and source.get('pointerAliasClaimed')is False)
    else:need('ordinary-explicit-Entity40-context-mode',event.get('sourceContextMode')is None)
    need('actual-own-ReadValue40-context',context.get('fullTypeName')==TYPE
        and context.get('methodOwner')=='MemoryPack.MemoryPackReader'and context.get('methodName')=='ReadValue'
        and context.get('register')=='r8'and context.get('typeKind')==17
        and context.get('typeDefinition')==layout['typeDefinition'])
    return True


def read_source(image,pins,*,context,source_target):
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack.leveldata_entity_ptr_value_sources import derive_read_value
    need('literal-own-ReadValue-context',isinstance(context,dict)and context.get('fullTypeName')==TYPE
        and context.get('methodOwner')=='MemoryPack.MemoryPackReader'and context.get('methodName')=='ReadValue'
        and context.get('register')=='r8'and context.get('typeKind')==17)
    usage=derive_typed_usage_context(image,context['instructionRva'],label='entityPtrFieldSource.ReadValue')
    need('same-current-usage',usage['methodSpec']==context['methodSpec']and usage['instructionHex']==context['instructionHex'])
    result=derive_read_value(image,pins,typed_request=usage,source_target=source_target)
    need('complete-own-current-hidden40-source',result.get('nativeInputs')==pins and result.get('typeName')==TYPE
        and result.get('managedBytes')==40 and result.get('resultAbi')=='hidden-local'and result.get('actualSourceProved')is True
        and result.get('sourceTargetRva')==source_target-image.pe.image_base
        and result.get('readerMethodDefinition')==context['methodSpec'][0]
        and result.get('proof',{}).get('layout',{}).get('typeDefinition')==context['typeDefinition']
        and result.get('runtimeReferenceLayoutAdmitted')is False and result.get('completeRuntimePaddingMapAdmitted')is False
        and result.get('opaqueRuntimeStorageRanges')==OPAQUE and result.get('knownPaddingByteRanges')==KNOWN_PADDING
        and result.get('selectedBarrierValueOffsets')==[24]and'referenceLaneOffsets'not in result
        and result.get('wireGrammarAdmitted')is False)
    return result


def validate_local_copy(row,event,setter,source,locals_,*,register,width,offset):
    """Exact whole opaque40 hidden80 to argument32 physical copy slices."""
    from scripts.game_data.memorypack import buff_ec_profiles_native as ec
    validate_event(event,setter)
    need('same-owned-Entity40-local-slice',len(source)>=4 and source[0]=='member'
        and source[1]==event.get('memberIndex')and source[3]>=width
        and(width,source[2],register)in((16,0,'xmm0'),(16,16,'xmm1'),(8,32,'xmm0'))
        and offset==32+source[2])
    expected={(16,0):'0f29442420',(16,16):'0f294c2430',(8,32):'f20f11442440'}
    need('exact-owned-Entity40-RSP-store',ec.raw(row).hex()==expected[width,source[2]])
    need('complete-owned-Entity40-hidden80-source',
        [locals_.get(80+i)for i in range(40)]==[(source[1],i)for i in range(40)])
    need('no-other-member-argument-overwrite',all(locals_.get(offset+i)in(None,(source[1],source[2]+i))
        for i in range(width)))
    return True
