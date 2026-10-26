"""Named AnimationClipAsyncInfo raw36 setter and parent-value gates.

The physical payload36, boxed52 and marshaled40 are independently retained.
The exact setter copies16+16+4 through its own coherent getter. It preserves
both raw Boolean bytes and padding, and has no reference/barrier semantics.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack import skill_animation_clip_raw_sources as value

TYPE=value.TYPE
SLICES=[[0,16],[16,16],[32,4]]


def need(check,condition):
    if not condition:raise ValueError('generatedAnimationClipField.'+check)


def layout(image,ctx):
    actual=value.layout(image,ctx)
    need('own-physical36-layout',actual['managedPayloadBytes']==36 and actual['boxedBytes']==52
        and actual['marshaledNativeBytes']==40 and actual['referenceLaneOffsets']==[]
        and actual['paddingByteRanges']==[[34,36]])
    return dict(actual,managedBytes=36)


def setter_program(regions,entry,*,getter,field,path_factory=None):
    from scripts.game_data.memorypack.generated_inline_constructor_sources import _nonnull
    from scripts.game_data.memorypack.generated_member_sources import _displacement
    need('literal-own-getter-and-field',type(getter)is int and getter>0 and type(field)is int and 16<=field<2**31-36)
    need('callable-only-path-factory',path_factory is None or callable(path_factory))
    g=(BytesPath if path_factory is None else path_factory)(regions,entry)
    g.take('4053','4883ec20','488bda','33d2');g.call(getter);g.take('4885c0');null=_nonnull(g)
    g.take('0f1003','8b4b20','0f104b10',_displacement('0f1180',field),
        _displacement('0f1188',field+16),_displacement('8988',field+32),'4883c420','5b','c3')
    null=dict(null,bytes=bytes(g.bytes[null['nullTargetVa']+i]for i in range(6)).hex().upper())
    return dict(selectedBytes=g.seen,managedBytes=36,storedBytes=36,fieldOffset=field,sourceSlices=SLICES,
        referenceLaneOffsets=[],paddingByteRanges=[[34,36]],barrierCalls=[],ownedNullExit=null,
        sourceValuePointer='incoming rdx preserved in rbx',getterReceiver='incoming rcx with zero edx',
        wholeInputBitsStoredUnchanged=True,completeSourceBitsStoredUnchanged=True,boolBytesNormalized=False,
        paddingBytesCopied=True,entryRspRestored=True,normalFrameAndReturn=True,nonvolatileRegistersRestored=['rbx'],
        childGrammarAdmitted=False)


def direct_setter_program(regions,entry,*,field,path_factory=None):
    from scripts.game_data.memorypack.generated_inline_constructor_sources import _nonnull
    from scripts.game_data.memorypack.generated_member_sources import _displacement
    need('literal-direct-named-field',type(field)is int and 16<=field<2**31-36)
    need('callable-only-path-factory',path_factory is None or callable(path_factory))
    g=(BytesPath if path_factory is None else path_factory)(regions,entry)
    g.take('4883ec28','4c8b4110','4d85c0');null=_nonnull(g)
    g.take('0f1002','8b4220','0f104a10',_displacement('410f1180',field),
        _displacement('410f1188',field+16),_displacement('418980',field+32),'4883c428','c3')
    null=dict(null,bytes=bytes(g.bytes[null['nullTargetVa']+i]for i in range(6)).hex().upper())
    return dict(selectedBytes=g.seen,holderOffset=16,managedBytes=36,storedBytes=36,fieldOffset=field,sourceSlices=SLICES,
        referenceLaneOffsets=[],paddingByteRanges=[[34,36]],barrierCalls=[],ownedNullExit=null,
        sourceValuePointer='incoming rdx',holderRegister='r8',wholeInputBitsStoredUnchanged=True,
        completeSourceBitsStoredUnchanged=True,boolBytesNormalized=False,paddingBytesCopied=True,
        entryRspRestored=True,normalFrameAndReturn=True,nonvolatileRegistersRestored=[],childGrammarAdmitted=False)


def derive_setter(image,pins,member,wrappers,barrier,getter_cache):
    from scripts.game_data.il2cpp.reference_field_programs import _setter_metadata
    from scripts.game_data.memorypack import generated_member_sources as members,pointer_param as pointer,scalar_param_native as scalar
    ctx,wrapper,field,target,offset,method=_setter_metadata(image,wrappers,member)
    need('own-ordinary-reference-parent',member.declared_type==TYPE and not ctx.is_value_type(wrapper.wrapped_type))
    nominal=layout(image,ctx)
    scalar.owned_method_abi(image,ctx,method.index,wrapper.type_definition,('void',1,False),[(TYPE,17,False)],'generatedAnimationClipField.setter')
    need('nongeneric-owned-setter',method.generic_container_index<0)
    parameter,=image.metadata.parameters_for(method);raw=image.pe.bytes_at_va(ctx.type_pointer(parameter.type_index),16)
    body=members._body(image,image.method_pointer_va(method),pins=pins)
    direct=image.pe.bytes_at_va(body['pointer'],8)==bytes.fromhex('4883ec284c8b4110')
    holder=None;direct_getter=None
    if direct:
        from scripts.game_data.memorypack.generated_alpha_blend_field_sources import direct_holder
        holder=direct_holder(image,ctx,wrapper);getter_proof=None
        getter=pointer.methods(image,wrapper)['GetValue']
        scalar.owned_method_abi(image,ctx,getter.index,wrapper.type_definition,(wrapper.wrapped_type,18,False),[],
            'generatedAnimationClipField.directGetValue')
        direct_getter=dict(method=[getter.index,wrapper.name,'GetValue',image.method_pointer_va(getter)-image.pe.image_base],
            program=pointer.leaf(image,image.method_pointer_va(getter),['488B4110','C3']))
        program=direct_setter_program(body['regions'],body['pointer'],field=offset)
        profile='direct-base-holder-setter'
    else:
        getter=pointer.methods(image,wrapper)['get___instance'];getter_target=image.method_pointer_va(getter)
        getter_proof=members._coherent_getter(image,ctx,wrapper,getter,getter_cache,barrier=image.pe.image_base+barrier)
        program=setter_program(body['regions'],body['pointer'],getter=getter_target,field=offset)
        profile='cached-getter-value36-setter'
    result=dict(method=[method.index,wrapper.name,image.metadata.string(method.name_index),body['pointer']-image.pe.image_base],
        member=member.row(),targetField=target,fieldOffset=offset,parameterTypeRecordHex=raw.hex().upper(),storedBytes=36,
        nominalValueLayout=nominal,sourceFamily=body['family'],codeWindows=body['windows'],profile=profile,
        program=program,getter=getter_proof,ordinarySourceRows=body['rows'],
        ordinarySourceRegions=[[a-image.pe.image_base,h.hex().upper()]for a,h in body['regions']],
        incomingValueStoredUnchanged=True,childGrammarAdmitted=False,factoryAdmitted=False)
    if direct:result.update(sourceProfile='direct-clip36-setter',directHolder=holder,directGetValue=direct_getter)
    return result


def validate_event(event,setter):
    nominal=setter.get('nominalValueLayout',{});program=setter.get('program',{});raw=bytes.fromhex(setter.get('parameterTypeRecordHex',''))
    need('exact-own-physical36-source-and-setter',event.get('kind')=='value36:'+TYPE and event.get('declaredType')==nominal.get('typeName')==TYPE
        and event.get('wireBytes')==nominal.get('managedBytes')==nominal.get('managedPayloadBytes')==setter.get('storedBytes')==36
        and nominal.get('boxedBytes')==52 and nominal.get('marshaledNativeBytes')==40 and nominal.get('referenceLaneOffsets')==[]
        and nominal.get('paddingByteRanges')==[[34,36]]and type(nominal.get('typeDefinition'))is int
        and len(raw)==16 and raw[10:12]==bytes((17,128))and int.from_bytes(raw[:8],'little')==nominal['typeDefinition']
        and program.get('sourceSlices')==SLICES and program.get('referenceLaneOffsets')==[]and program.get('barrierCalls')==[]
        and all(program.get(k)is True for k in('wholeInputBitsStoredUnchanged','completeSourceBitsStoredUnchanged','paddingBytesCopied','entryRspRestored','normalFrameAndReturn'))
        and program.get('boolBytesNormalized')is False and event.get('actualSourceProved')is True)
    if event.get('mode')=='typed-hidden-value':
        context=event.get('context',{});source=event.get('nominalHiddenSource',{})
        need('actual-own-ReadUnmanaged36-context',context.get('fullTypeName')==TYPE and context.get('methodOwner')=='MemoryPack.MemoryPackReader'
            and context.get('methodName')=='ReadUnmanaged'and context.get('register')=='r8'and context.get('typeKind')==17
            and context.get('typeDefinition')==nominal['typeDefinition']and event.get('resultAbi')=='hidden-local'
            and event.get('sourceContextMode')is None and source.get('schema')==value.SCHEMA and source.get('status')=='validated')
    else:
        capture=event.get('inlineSourceProgram',{})
        need('actual-own-inline36-capture',event.get('mode')=='buffered-called-advance-clip36'
            and event.get('context')is None and event.get('inlineNominalLayout')==nominal
            and capture.get('wireBytes')==36 and capture.get('preservedCaptureRegistersRequired')==['xmm6','rbp','xmm7']
            and[(s.get('register'),s.get('sourceOffset'),s.get('bytes'))for s in capture.get('capturedSourceSlices',[])]==
                [('xmm6',0,16),('rbp',32,4),('xmm7',16,16)]and capture.get('boolBytesNormalized')is False
            and capture.get('paddingBytesCopied')is True and capture.get('typedReadUnmanagedClaimed')is False)
    return True


def read_source(image,pins,*,context,source_target):
    need('literal-typed-ReadUnmanaged36-context',isinstance(context,dict)and context.get('fullTypeName')==TYPE
        and context.get('methodOwner')=='MemoryPack.MemoryPackReader'and context.get('methodName')=='ReadUnmanaged'
        and context.get('typeKind')==17 and context.get('register')=='r8')
    return value.derive(image,pins,context=context,source_target=source_target)
