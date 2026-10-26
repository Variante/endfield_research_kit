"""Exact named SkMorph hidden40 field transfer and runtime-object barrier."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack import sk_morph_value_sources as value

TYPE=value.TYPE


def need(check,condition):
    if not condition:raise ValueError('generatedSkMorphField.'+check)


def setter_program(regions,entry,*,field,barrier):
    from scripts.game_data.memorypack.generated_inline_constructor_sources import _nonnull
    from scripts.game_data.memorypack.generated_member_sources import _displacement
    need('literal-own-field-and-barrier',type(field)is int and 16<=field<2**31-40 and type(barrier)is int and barrier>0)
    g=BytesPath(regions,entry);g.take('4883ec28','488b4910','4885c9');null=_nonnull(g)
    g.take('0f1002','0f104a10',_displacement('0f1141',field),'f20f104220',
        _displacement('0f1149',field+16),_displacement('f20f1141',field+32))
    address=field+24;g.take('4883c1'+bytes((address,)).hex()if address<128 else'4881c1'+address.to_bytes(4,'little').hex(),'4883c428')
    need('own-disabled-object-lane-tail',g.relative('e9')==barrier)
    return dict(selectedBytes=g.seen,storedBytes=40,managedBytes=40,holderOffset=16,sourceSlices=value.SLICES,
        referenceLaneOffsets=[24],paddingByteRanges=value.PADDING,barrierReferenceLaneOffset=24,
        wholeInputBitsStoredUnchanged=True,completeSourceBitsStoredUnchanged=True,entryRspRestored=True,
        normalReturnViaBarrier=True,normalFrameAndReturn=True,disabledCollectorRequired=True,ownedNullExit=null)


def derive_setter(image,pins,member,wrappers,barrier,getter_cache):
    from scripts.game_data.il2cpp.reference_field_programs import _setter_metadata
    from scripts.game_data.memorypack import generated_member_sources as members,scalar_param_native as scalar
    from scripts.game_data.memorypack.generated_alpha_blend_field_sources import direct_holder
    ctx,wrapper,field,target,offset,method=_setter_metadata(image,wrappers,member)
    need('own-ordinary-reference-parent',member.declared_type==TYPE and not ctx.is_value_type(wrapper.wrapped_type))
    nominal=value.layout(image,ctx);holder=direct_holder(image,ctx,wrapper)
    scalar.owned_method_abi(image,ctx,method.index,wrapper.type_definition,('void',1,False),[(TYPE,17,False)],'generatedSkMorphField.setter')
    need('nongeneric-own-setter',method.generic_container_index<0)
    parameter,=image.metadata.parameters_for(method);raw=image.pe.bytes_at_va(ctx.type_pointer(parameter.type_index),16)
    body=members._body(image,image.method_pointer_va(method),pins=pins)
    program=setter_program(body['regions'],body['pointer'],field=offset,barrier=image.pe.image_base+barrier)
    return dict(method=[method.index,wrapper.name,image.metadata.string(method.name_index),body['pointer']-image.pe.image_base],
        member=member.row(),targetField=target,fieldOffset=offset,parameterTypeRecordHex=raw.hex().upper(),storedBytes=40,
        managedValueLayout=nominal,sourceFamily=body['family'],codeWindows=body['windows'],profile='direct-base-holder-setter',
        program=program,getter=None,directHolder=holder,ordinarySourceRows=body['rows'],
        ordinarySourceRegions=[[a-image.pe.image_base,h.hex().upper()]for a,h in body['regions']],
        incomingValueStoredUnchanged=True,childGrammarAdmitted=False,factoryAdmitted=False)


def validate_event(event,setter):
    nominal=setter.get('managedValueLayout',{});program=setter.get('program',{});raw=bytes.fromhex(setter.get('parameterTypeRecordHex',''))
    context=event.get('context',{})
    need('own-exact-hidden40-source',event.get('kind')=='managed:'+TYPE and event.get('declaredType')==nominal.get('typeName')==TYPE
        and event.get('mode')=='typed-managed-value'and event.get('actualSourceProved')is True
        and event.get('resultAbi')=='hidden-local'and'wireBytes'not in event
        and event.get('managedBytes')==nominal.get('managedBytes')==setter.get('storedBytes')==40
        and event.get('referenceLaneOffsets')==nominal.get('referenceLaneOffsets')==program.get('referenceLaneOffsets')==[24]
        and nominal.get('paddingByteRanges')==program.get('paddingByteRanges')==value.PADDING
        and nominal.get('fields')==[list(r)for r in value.FIELDS]and type(nominal.get('typeDefinition'))is int
        and len(raw)==16 and raw[10:12]==bytes((17,128))and int.from_bytes(raw[:8],'little')==nominal['typeDefinition']
        and program.get('sourceSlices')==value.SLICES and program.get('barrierReferenceLaneOffset')==24
        and all(program.get(k)is True for k in('wholeInputBitsStoredUnchanged','completeSourceBitsStoredUnchanged',
            'entryRspRestored','normalReturnViaBarrier','disabledCollectorRequired')))
    need('own-actual-ReadValue40-context',context.get('fullTypeName')==TYPE and context.get('methodOwner')=='MemoryPack.MemoryPackReader'
        and context.get('methodName')=='ReadValue'and context.get('register')=='r8'and context.get('typeKind')==17
        and context.get('typeDefinition')==nominal['typeDefinition']and event.get('sourceContextMode')is None)
    return True


def read_source(image,pins,*,context,source_target):
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    need('own-literal-source-context',context.get('fullTypeName')==TYPE and context.get('methodOwner')=='MemoryPack.MemoryPackReader'
        and context.get('methodName')=='ReadValue'and context.get('register')=='r8'and context.get('typeKind')==17)
    usage=derive_typed_usage_context(image,context['instructionRva'],label='generatedSkMorphField.ReadValue')
    need('same-actual-context-bytes',usage['methodSpec']==context['methodSpec']and usage['instructionHex']==context['instructionHex'])
    proof=value.derive(image,pins,typed_request=usage,source_target=source_target)
    need('fresh-own-layout-and-source',proof.get('nativeInputs')==pins and proof.get('typeName')==TYPE
        and proof.get('managedBytes')==40 and proof.get('actualSourceProved')is True
        and proof.get('sourceTargetRva')==source_target-image.pe.image_base
        and proof.get('readerMethodDefinition')==context['methodSpec'][0])
    return proof
