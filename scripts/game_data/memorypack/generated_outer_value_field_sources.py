"""Named raw TrackingBounds36 and TriggerShape44 fields, separately nominal.

Each direct-holder setter stores every physical bit through its exact owned
ordinary value parameter. The independent actual ReadUnmanaged owner supplies
the raw source; canonical wrappers, lists, defaults and parent frames remain
separate. Neither width admits another type.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

BOUNDS='Beyond.Gameplay.TrackingBounds'
TRIGGER='Beyond.Gameplay.Core.TriggerShapeData'
WIDTHS={BOUNDS:36,TRIGGER:44}


def need(check,condition):
    if not condition:raise ValueError('outerValueField.'+check)


def layout(image,ctx,type_name):
    need('finite-own-nominal',type_name in WIDTHS)
    if type_name==BOUNDS:
        from scripts.game_data.memorypack.leveldata_tracking_raw_sources import layout as own
    else:
        from scripts.game_data.memorypack.leveldata_trigger_shape_raw_sources import layout as own
    result=own(image,ctx)
    need('own-physical-value-layout',result.get('typeName')==type_name and result.get('managedBytes')==WIDTHS[type_name]
        and type(result.get('typeDefinition'))is int and result.get('referenceLaneOffsets')==result.get('paddingByteRanges')==[])
    return result


def setter_program(regions,entry,*,type_name,field,path_factory=None):
    from scripts.game_data.memorypack.generated_inline_constructor_sources import _nonnull
    from scripts.game_data.memorypack.generated_member_sources import _displacement
    need('finite-literal-owned-field',type_name in WIDTHS and type(field)is int and 16<=field<2**31-WIDTHS[type_name])
    need('callable-only-path-factory',path_factory is None or callable(path_factory))
    width=WIDTHS[type_name];trigger=type_name==TRIGGER
    g=(BytesPath if path_factory is None else path_factory)(regions,entry)
    g.take('4883ec28','4c8b4110','4d85c0');null=_nonnull(g)
    g.take('0f1002','8b42'+('28'if trigger else'20'),'0f104a10',_displacement('410f1140',field))
    if trigger:g.take('f20f104220')
    g.take(_displacement('410f1148',field+16))
    if trigger:g.take(_displacement('f2410f1140',field+32))
    g.take(_displacement('418940',field+(40 if trigger else 32)),'4883c428','c3')
    null=dict(null,bytes=bytes(g.bytes[null['nullTargetVa']+i]for i in range(6)).hex().upper())
    slices=[[0,16],[16,16]]+([[32,8],[40,4]]if trigger else[[32,4]])
    return dict(typeName=type_name,managedBytes=width,storedBytes=width,fieldOffset=field,holderOffset=16,
        selectedBytes=g.seen,sourceSlices=slices,sourceValuePointer='unchanged incoming rdx',originalRegister='r8',
        referenceLaneOffsets=[],paddingByteRanges=[],barrierCalls=[],ownedNullExit=null,
        wholeInputBitsStoredUnchanged=True,completeSourceBitsStoredUnchanged=True,
        rawEnumAndCoordinateBitsPreserved=True,entryRspRestored=True,normalFrameAndReturn=True,
        childGrammarAdmitted=False,parentCallerFrameProved=False)


def derive_setter(image,pins,member,wrappers,barrier,getter_cache):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_field_programs import _setter_metadata
    from scripts.game_data.memorypack import generated_member_sources as members,scalar_param_native as scalar
    from scripts.game_data.memorypack.generated_alpha_blend_field_sources import direct_holder
    _publication_gate(image,pins)
    ctx,wrapper,field,target,offset,method=_setter_metadata(image,wrappers,member)
    need('own-ordinary-reference-parent',member.declared_type in WIDTHS and not ctx.is_value_type(wrapper.wrapped_type))
    nominal=layout(image,ctx,member.declared_type);holder=direct_holder(image,ctx,wrapper)
    scalar.owned_method_abi(image,ctx,method.index,wrapper.type_definition,('void',1,False),
        [(member.declared_type,17,False)],'outerValueField.setter')
    need('nongeneric-owned-setter',method.generic_container_index<0)
    parameter,=image.metadata.parameters_for(method);raw=image.pe.bytes_at_va(ctx.type_pointer(parameter.type_index),16)
    body=members._body(image,image.method_pointer_va(method),pins=pins)
    program=setter_program(body['regions'],body['pointer'],type_name=member.declared_type,field=offset)
    _publication_gate(image,pins)
    return dict(method=[method.index,wrapper.name,image.metadata.string(method.name_index),body['pointer']-image.pe.image_base],
        member=member.row(),targetField=target,fieldOffset=offset,parameterTypeRecordHex=raw.hex().upper(),storedBytes=nominal['managedBytes'],
        nominalValueLayout=nominal,sourceFamily=body['family'],codeWindows=body['windows'],profile='direct-base-holder-setter',sourceProfile='direct-named-outer-raw-value-setter',
        program=program,getter=None,directHolder=holder,ordinarySourceRows=body['rows'],
        ordinarySourceRegions=[[a-image.pe.image_base,h.hex().upper()]for a,h in body['regions']],
        incomingValueStoredUnchanged=True,childGrammarAdmitted=False,factoryAdmitted=False)


def validate_event(event,setter):
    name=event.get('declaredType');nominal=setter.get('nominalValueLayout',{});program=setter.get('program',{})
    context=event.get('context',{});raw=bytes.fromhex(setter.get('parameterTypeRecordHex',''))
    need('finite-independent-nominal-source-and-setter',name in WIDTHS and event.get('kind')=='value'+str(WIDTHS[name])+':'+name
        and nominal.get('typeName')==program.get('typeName')==name
        and event.get('mode')=='typed-hidden-value'and event.get('resultAbi')=='hidden-local'
        and event.get('actualSourceProved')is True and event.get('wireBytes')==nominal.get('managedBytes')==setter.get('storedBytes')==WIDTHS[name]
        and nominal.get('referenceLaneOffsets')==nominal.get('paddingByteRanges')==[]
        and type(nominal.get('typeDefinition'))is int and len(raw)==16 and raw[10:12]==bytes((17,128))
        and int.from_bytes(raw[:8],'little')==nominal['typeDefinition']
        and program.get('sourceSlices')==([[0,16],[16,16],[32,4]]if name==BOUNDS else[[0,16],[16,16],[32,8],[40,4]])
        and program.get('referenceLaneOffsets')==program.get('paddingByteRanges')==program.get('barrierCalls')==[]
        and all(program.get(k)is True for k in('wholeInputBitsStoredUnchanged','completeSourceBitsStoredUnchanged',
            'rawEnumAndCoordinateBitsPreserved','entryRspRestored','normalFrameAndReturn')))
    source=event.get('nominalHiddenSource',{})
    expected=('endfield.story-tracking-bounds-raw36.v1','validated-conditional-tracking-bounds-raw36')if name==BOUNDS else(
        'endfield.story-trigger-shape-raw44.v1','validated-conditional-trigger-shape-raw44')
    need('actual-own-ReadUnmanaged-context',context.get('fullTypeName')==name
        and context.get('methodOwner')=='MemoryPack.MemoryPackReader'and context.get('methodName')=='ReadUnmanaged'
        and context.get('register')=='r8'and context.get('typeKind')==17 and context.get('typeDefinition')==nominal['typeDefinition']
        and event.get('sourceContextMode')is None and(source.get('schema'),source.get('status'))==expected
        and source.get('typeName')==name and source.get('actualSourceProved')is True and source.get('managedBytes')==WIDTHS[name])
    return True


def read_source(image,pins,*,context,source_target,source_instruction):
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    need('literal-own-ReadUnmanaged-context',isinstance(context,dict)and context.get('fullTypeName')in WIDTHS
        and context.get('methodOwner')=='MemoryPack.MemoryPackReader'and context.get('methodName')=='ReadUnmanaged'
        and context.get('register')=='r8'and context.get('typeKind')==17)
    name=context['fullTypeName'];usage=derive_typed_usage_context(image,context['instructionRva'],label='outerValueField.ReadUnmanaged')
    need('same-current-usage',usage['methodSpec']==context['methodSpec']and usage['instructionHex']==context['instructionHex'])
    if name==BOUNDS:
        from scripts.game_data.memorypack.leveldata_tracking_raw_sources import derive
    else:
        from scripts.game_data.memorypack.leveldata_trigger_shape_raw_sources import derive
    result=derive(image,pins,typed_request=usage,source_target=source_target,source_instruction=source_instruction)
    need('same-complete-nominal-raw-source',result.get('nativeInputs')==pins and result.get('typeName')==name
        and result.get('managedBytes')==result.get('wireBytes')==WIDTHS[name]and result.get('actualSourceProved')is True
        and result.get('sourceTargetRva')==source_target-image.pe.image_base
        and result.get('readerMethodDefinition')==context['methodSpec'][0]
        and result.get('referenceLaneOffsets')==result.get('paddingByteRanges')==[]
        and result.get('canonicalWrapperUsed')is False and result.get('objectHeaderRead')is False)
    return result
