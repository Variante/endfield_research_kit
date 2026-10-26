"""Named Envelope managed32 field setter, separate from its MC7 wire grammar."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.skill_impulse_envelope_sources import TYPE


def need(key,condition):
    if not condition:raise ValueError('generatedEnvelopeField.'+key)


def setter_program(regions,entry,*,field,barrier,path_factory=None):
    from scripts.game_data.memorypack.generated_inline_constructor_sources import _nonnull
    from scripts.game_data.memorypack.generated_member_sources import _displacement
    need('literal-owned-field-and-barrier',type(field)is int and field>=16 and type(barrier)is int and barrier>0)
    need('callable-only-path-factory',path_factory is None or callable(path_factory))
    g=(BytesPath if path_factory is None else path_factory)(regions,entry)
    g.take('4883ec28','488b4910','4885c9');null=_nonnull(g)
    null=dict(null,bytes=bytes(g.bytes[null['nullTargetVa']+i]for i in range(6)).hex().upper())
    g.take('0f1002','0f104a10',_displacement('0f1141',field),_displacement('0f1149',field+16),
        ('4883c1'+field.to_bytes(1,'little').hex())if field<128 else('4881c1'+field.to_bytes(4,'little').hex()),'4883c428')
    need('same-exact-disabled-barrier',g.relative('e9')==barrier)
    return dict(selectedBytes=g.seen,managedBytes=32,storedBytes=32,fieldOffset=field,holderOffset=16,
        sourceSlices=[[0,16],[16,16]],referenceLaneOffsets=[0,8],barrierReferenceLaneOffset=0,
        wholeInputBitsStoredUnchanged=True,completeSourceBitsStoredUnchanged=True,
        entryRspRestored=True,normalFrameAndReturn=True,nonvolatileRegistersRestored=[],
        normalReturnViaBarrier=True,ownedNullExit=null,disabledCollectorRequired=True,childGrammarAdmitted=False)


def derive_setter(image,pins,member,wrappers,barrier,getter_cache):
    from scripts.game_data.il2cpp.reference_field_programs import _setter_metadata
    from scripts.game_data.memorypack import generated_member_sources as members,scalar_param_native as scalar
    from scripts.game_data.memorypack.skill_impulse_envelope_sources import layout
    ctx,wrapper,field,target,offset,method=_setter_metadata(image,wrappers,member)
    need('exact-nominal-reference-parent-field',member.declared_type==TYPE and not ctx.is_value_type(wrapper.wrapped_type))
    need('direct-current-holder16',ctx.field(wrapper.name+'::__instance')==(wrapper.name,wrapper.wrapped_type,16))
    nominal=dict(layout(image,ctx),typeDefinition=ctx.index.types[TYPE].index)
    need('own-padded-two-reference-layout',nominal['managedBytes']==32 and nominal['referenceLaneOffsets']==[0,8]
        and nominal['paddingByteRanges']==[[30,32]])
    scalar.owned_method_abi(image,ctx,method.index,wrapper.type_definition,('void',1,False),[(TYPE,17,False)],'generatedEnvelopeField.setter')
    need('nongeneric-owned-setter',method.generic_container_index<0)
    parameter,=image.metadata.parameters_for(method);raw=image.pe.bytes_at_va(ctx.type_pointer(parameter.type_index),16)
    body=members._body(image,image.method_pointer_va(method))
    parsed=setter_program(body['regions'],body['pointer'],field=offset,barrier=image.pe.image_base+barrier)
    return dict(method=[method.index,wrapper.name,image.metadata.string(method.name_index),body['pointer']-image.pe.image_base],
        member=member.row(),targetField=target,fieldOffset=offset,parameterTypeRecordHex=raw.hex().upper(),storedBytes=32,
        managedValueLayout=nominal,sourceFamily=body['family'],codeWindows=body['windows'],profile='direct-base-holder-setter',
        program=parsed,getter=None,incomingValueStoredUnchanged=True,childGrammarAdmitted=False,factoryAdmitted=False)


def read_source(image,pins,*,context,source_target):
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack.skill_impulse_envelope_transfer import derive
    need('exact-current-hidden32-context',type(context)is dict and context.get('fullTypeName')==TYPE
        and context.get('methodOwner')=='MemoryPack.MemoryPackReader'and context.get('methodName')=='ReadValue'
        and context.get('register')=='r8'and context.get('typeKind')==17)
    usage=derive_typed_usage_context(image,context['instructionRva'],label='generatedEnvelopeField.ReadValue')
    need('same-current-raw-context',usage['methodSpec']==context['methodSpec']and usage['instructionHex']==context['instructionHex'])
    proof=derive(image,pins,typed_request=usage,source_target=source_target)
    need('independently-proved-managed32-read',proof['nativeInputs']==pins and proof['typeName']==TYPE
        and proof['managedBytes']==32 and proof['resultAbi']=='hidden-local'and proof['actualSourceProved']is True
        and proof['sourceTargetRva']==source_target-image.pe.image_base
        and proof['readerMethodDefinition']==context['methodSpec'][0]and proof['referenceLaneOffsets']==[0,8]
        and proof['wireGrammarAdmitted']is False)
    return proof
