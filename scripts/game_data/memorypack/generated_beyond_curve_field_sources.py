"""Exact Beyond FAnimationCurve managed field, independent from Unity curves.

The one-reference managed16 transfer is composed with its own named keys and
wrap enums. Its MC3/default16/raw FKeyframe-array wire stays in the existing
Beyond curve domain; no serialized width follows from this layout.
"""

TYPE='Beyond.FAnimationCurve'
WRAPPER='Beyond.MemoryPack.Beyond_FAnimationCurveForMemoryPack'
FIELDS=[('keys','Beyond.FKeyframe[]',16,29),('preWrapMode','UnityEngine.WrapMode',24,17),
        ('postWrapMode','UnityEngine.WrapMode',28,17)]


def need(check,condition):
    if not condition:raise ValueError('generatedBeyondCurveField.'+check)


def layout(image,ctx):
    from scripts.game_data.memorypack import scalar_param_native as scalar
    md=image.metadata;td=ctx.index.types[TYPE]
    need('own-nongeneric-value',ctx.is_value_type(TYPE)and not ctx.is_enum(TYPE)and td.generic_container_index<0)
    fields=[f for f in md.fields_for(td)if not ctx.field_attributes(f.type_index)&16]
    actual=[]
    for field in fields:
        name=md.string(field.name_index);_,declared,offset=ctx.field(TYPE+'::'+name)
        raw=image.pe.bytes_at_va(ctx.type_pointer(field.type_index),16);actual.append((name,declared,offset,raw[10]))
        scalar.ordinary(image,ctx.type_pointer(field.type_index),raw[10],'generatedBeyondCurveField.field',reference=raw[10]==29)
    need('own-array-and-two-enum-fields',actual==FIELDS)
    enum=ctx.index.types['UnityEngine.WrapMode'];need('own-wrap-enum',ctx.is_enum('UnityEngine.WrapMode')and enum.generic_container_index<0)
    backing,=[f for f in md.fields_for(enum)if not ctx.field_attributes(f.type_index)&16]
    need('wrap-enum-int32',md.string(backing.name_index)=='value__'and ctx.field('UnityEngine.WrapMode::value__')==('UnityEngine.WrapMode','int',16))
    scalar.ordinary(image,ctx.type_pointer(backing.type_index),8,'generatedBeyondCurveField.enumBacking')
    size=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+td.index*8)
    need('own-complete-managed16',(image.pe.u32_at_va(size),image.pe.u32_at_va(size+4))==(32,16))
    return dict(typeName=TYPE,typeDefinition=td.index,fields=[list(r)for r in actual],managedBytes=16,
        referenceLaneOffsets=[0],paddingByteRanges=[],wireGrammarAdmitted=False)


def setter_program(regions,entry,*,field,barrier,getter=None):
    from scripts.game_data.memorypack.generated_managed_value_sources import setter_program as whole16
    proof=whole16(regions,entry,field=field,managed_bytes=16,reference_lane_offsets=[0],barrier=barrier,getter=getter)
    need('exact-own-whole16-lane0',proof['storedBytes']==16 and proof['referenceLaneOffsets']==[0]
        and proof['barrierReferenceLaneOffset']==0 and proof['wholeInputBitsStoredUnchanged']is True)
    return dict(proof,sourceSlices=[[0,16]],completeSourceBitsStoredUnchanged=True,normalFrameAndReturn=True)


def derive_setter(image,pins,member,wrappers,barrier,getter_cache):
    from scripts.game_data.il2cpp.reference_field_programs import _setter_metadata
    from scripts.game_data.memorypack import generated_member_sources as members,pointer_param as pointer,scalar_param_native as scalar
    from scripts.game_data.memorypack.generated_alpha_blend_field_sources import direct_holder
    ctx,wrapper,field,target,offset,method=_setter_metadata(image,wrappers,member)
    need('own-ordinary-reference-parent',member.declared_type==TYPE and not ctx.is_value_type(wrapper.wrapped_type))
    nominal=layout(image,ctx)
    scalar.owned_method_abi(image,ctx,method.index,wrapper.type_definition,('void',1,False),[(TYPE,17,False)],'generatedBeyondCurveField.setter')
    need('nongeneric-owned-setter',method.generic_container_index<0)
    parameter,=image.metadata.parameters_for(method);raw=image.pe.bytes_at_va(ctx.type_pointer(parameter.type_index),16)
    body=members._body(image,image.method_pointer_va(method),pins=pins)
    getter_target=None;getter_proof=None;holder=None
    if image.pe.bytes_at_va(body['pointer'],4)==bytes.fromhex('4883ec28'):
        holder=direct_holder(image,ctx,wrapper);profile='direct-base-holder-setter'
    else:
        getter=pointer.methods(image,wrapper)['get___instance'];getter_target=image.method_pointer_va(getter)
        getter_proof=members._coherent_getter(image,ctx,wrapper,getter,getter_cache,barrier=image.pe.image_base+barrier)
        profile='cached-getter-setter'
    program=setter_program(body['regions'],body['pointer'],getter=getter_target,field=offset,barrier=image.pe.image_base+barrier)
    return dict(method=[method.index,wrapper.name,image.metadata.string(method.name_index),body['pointer']-image.pe.image_base],
        member=member.row(),targetField=target,fieldOffset=offset,parameterTypeRecordHex=raw.hex().upper(),storedBytes=16,
        managedValueLayout=nominal,sourceFamily=body['family'],codeWindows=body['windows'],profile=profile,
        program=program,getter=getter_proof,directHolder=holder,ordinarySourceRows=body['rows'],
        ordinarySourceRegions=[[a-image.pe.image_base,h.hex().upper()]for a,h in body['regions']],
        incomingValueStoredUnchanged=True,childGrammarAdmitted=False,factoryAdmitted=False)


def validate_event(event,setter):
    nominal=setter.get('managedValueLayout',{});program=setter.get('program',{});raw=bytes.fromhex(setter.get('parameterTypeRecordHex',''))
    context=event.get('context',{})
    need('own-hidden16-field-source',event.get('kind')=='managed:'+TYPE and event.get('declaredType')==nominal.get('typeName')==TYPE
        and event.get('mode')=='typed-managed-value'and event.get('actualSourceProved')is True
        and event.get('resultAbi')=='hidden-local'and'wireBytes'not in event
        and event.get('managedBytes')==nominal.get('managedBytes')==setter.get('storedBytes')==16
        and event.get('referenceLaneOffsets')==nominal.get('referenceLaneOffsets')==[0]
        and nominal.get('paddingByteRanges')==[]and type(nominal.get('typeDefinition'))is int
        and nominal.get('fields')==[list(r)for r in FIELDS]
        and len(raw)==16 and raw[10:12]==bytes((17,128))and int.from_bytes(raw[:8],'little')==nominal['typeDefinition']
        and program.get('sourceSlices')==[[0,16]]and program.get('referenceLaneOffsets')==[0]
        and program.get('barrierReferenceLaneOffset')==0 and all(program.get(k)is True for k in(
            'wholeInputBitsStoredUnchanged','completeSourceBitsStoredUnchanged','entryRspRestored','normalFrameAndReturn')))
    need('actual-own-hidden-ReadValue-context',context.get('fullTypeName')==TYPE and context.get('methodOwner')=='MemoryPack.MemoryPackReader'
        and context.get('methodName')=='ReadValue'and context.get('register')=='r8'and context.get('typeKind')==17
        and context.get('typeDefinition')==nominal['typeDefinition']and event.get('sourceContextMode')is None)
    return True


def read_source(image,pins,*,context,source_target):
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack.managed_value16_read_sources import derive
    need('literal-own-ReadValue-context',isinstance(context,dict)and context.get('fullTypeName')==TYPE
        and context.get('methodOwner')=='MemoryPack.MemoryPackReader'and context.get('methodName')=='ReadValue'
        and context.get('register')=='r8'and context.get('typeKind')==17)
    usage=derive_typed_usage_context(image,context['instructionRva'],label='generatedBeyondCurveField.ReadValue')
    need('same-actual-context-bytes',usage['methodSpec']==context['methodSpec']and usage['instructionHex']==context['instructionHex'])
    proof=derive(image,pins,typed_request=usage,source_target=source_target,reference_lane=0,wrapper_name=WRAPPER)
    need('fresh-own-one-reference-source',proof['nativeInputs']==pins and proof['typeName']==TYPE
        and proof['wrapperName']==WRAPPER and proof['managedBytes']==16 and proof['resultAbi']=='hidden-local'
        and proof['actualSourceProved']is True and proof['sourceTargetRva']==source_target-image.pe.image_base
        and proof['readerMethodDefinition']==context['methodSpec'][0]and proof['wireGrammarAdmitted']is False)
    return dict(proof,referenceLaneOffsets=[0],paddingByteRanges=[])
