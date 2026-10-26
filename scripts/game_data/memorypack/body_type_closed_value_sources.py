"""Own closed BodyTypeDef helper, independent of its parent or MC3 wire.

The actual helper supplies its own typed MethodInfo. Its neutral pointer
preservation lemma supplies no nominal layout or callback identity; those are
reproved by the existing BodyTypeDef source against the nested actual call.

The helper preserves hidden output/Reader pointers and supplies the actual
nested ReadValue context; absent outer context cannot become a generic call.
Parent copies into distinct argument locals require both full SIMD slices,
nominal identity, disjoint live homes, named setter and restored frame.
Managed copies add no wire bytes.
"""

TYPE='Beyond.Gameplay.BodyTypeDef'
SCHEMA='endfield.body-type-closed-value-source.v1'


def need(check,condition):
    if not condition:raise ValueError('bodyTypeClosedValue.'+check)


def derive(image,pins,*,source_target):
    import json
    from scripts.game_data.memorypack.generated_vector3_source import forwarder_program
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack import pointer_param as pointer,generated_action_sources as actions
    from scripts.game_data.memorypack.body_type_value_sources import derive as nested_read
    _publication_gate(image,pins);base=image.pe.image_base
    need('literal-actual-owned-helper',type(source_target)is int and source_target>base)
    body=pointer.owned(image,source_target);program=forwarder_program(body['regions'],source_target)
    contexts,skipped=actions._contexts(image,body['rows']);need('one-exact-internal-ReadValue-context',len(contexts)==1)
    context,=contexts;raw=bytes.fromhex(context.get('argumentRawHex',''))
    need('own-ordinary-BodyType-ReadValue-context',context.get('fullTypeName')==TYPE
        and context.get('methodOwner')=='MemoryPack.MemoryPackReader'and context.get('methodName')=='ReadValue'
        and context.get('typeKind')==17 and context.get('register')=='r8'
        and len(raw)==16 and raw[10:12]==b'\x11\x80'and int.from_bytes(raw[:8],'little')==context.get('typeDefinition')
        and context.get('instructionRva')==program['contextInstructionVa']-base)
    usage=derive_typed_usage_context(image,context['instructionRva'],label='bodyTypeClosedValue.internal')
    need('same-actual-MethodInfo-instruction-and-spec',usage.get('methodSpec')==context['methodSpec']
        and usage.get('instructionHex')==context['instructionHex'])
    nested=nested_read(image,pins,typed_request=usage,source_target=program['nestedTargetVa'])
    need('independent-own-nested-managed32',nested.get('nativeInputs')==pins and nested.get('typeName')==TYPE
        and nested.get('managedBytes')==32 and nested.get('resultAbi')=='hidden-local'
        and nested.get('actualSourceProved')is True and nested.get('wireGrammarAdmitted')is False
        and nested.get('sourceTargetRva')==program['nestedTargetVa']-base
        and nested.get('readerMethodDefinition')==context['methodSpec'][0]
        and nested.get('referenceLaneOffsets')==[8,24])
    _publication_gate(image,pins)
    result=dict(nested);result.update(schema=SCHEMA,status='proved-conditional-own-BodyType-closed-forwarder',
        sourceTargetRva=source_target-base,sourceContextMode='owned-closed-forwarder',contextMode='owned-closed-forwarder',
        pointerAliasClaimed=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        proof=dict(nested['proof'],internalContext=context,forwarderProgram=program,nestedSource=nested,
            actualFamily=image.unwind_index.family(source_target-base),actualWindows=body['windows'],
            actualSourceRegions=[[at,raw.hex().upper()]for at,raw in body['regions']],skippedRuntimeCells=skipped))
    return json.loads(json.dumps(result))


def verify(actual,pins):
    import json
    from scripts.game_data.memorypack.generated_vector3_source import forwarder_program
    from scripts.game_data.memorypack.animation_custom_dictionary_callbacks import regions
    from scripts.game_data.memorypack.body_type_value_sources import FIELDS
    need('own-current-closed-BodyType-source',actual.get('schema')==SCHEMA and actual.get('nativeInputs')==pins
        and actual.get('status')=='proved-conditional-own-BodyType-closed-forwarder'and actual.get('typeName')==TYPE
        and actual.get('managedBytes')==32 and actual.get('resultAbi')=='hidden-local'
        and actual.get('sourceContextMode')==actual.get('contextMode')=='owned-closed-forwarder'
        and actual.get('actualSourceProved')is True and actual.get('wireGrammarAdmitted')is False
        and actual.get('pointerAliasClaimed')is False and actual.get('parentFieldAdmitted')is False and actual.get('wholeOwnerAdmitted')is False)
    p=actual['proof'];program=p['forwarderProgram'];nested=p['nestedSource'];context=p['internalContext']
    need('own-full-forwarder-trace',bool(program.get('selectedBytes')))
    base=program['selectedBytes'][0][0]-actual['sourceTargetRva']
    need('selected-image-base',type(base)is int and base>=2**32)
    raw=regions(p['actualWindows'],[[at-base,h]for at,h in p['actualSourceRegions']],base,'closed-BodyType')
    need('exact-whole-pointer-forwarder',json.loads(json.dumps(forwarder_program(raw,base+actual['sourceTargetRva'])))==json.loads(json.dumps(program)))
    nominal=nested.get('proof',{}).get('nominal',{})
    need('same-independent-nominal-managed32-source',nested.get('schema')=='endfield.body-type-value-source.v1'
        and nested.get('status')=='proved-conditional-nominal-managed32-source'and nested.get('nativeInputs')==pins
        and nested.get('typeName')==TYPE and nested.get('managedBytes')==32 and nested.get('resultAbi')=='hidden-local'
        and nested.get('actualSourceProved')is True and nested.get('wireGrammarAdmitted')is False
        and nested.get('sourceTargetRva')==program['nestedTargetVa']-base
        and nested.get('readerMethodDefinition')==context.get('methodSpec',[None])[0]
        and nominal==p.get('nominal')and nominal.get('typeName')==TYPE
        and nominal.get('boxedBytes')==48 and nominal.get('managedBytes')==32
        and nominal.get('fields')==[list(row)for row in FIELDS]
        and nominal.get('referenceLaneOffsets')==actual.get('referenceLaneOffsets')==[8,24]
        and nominal.get('paddingByteRanges')==actual.get('paddingByteRanges')==[[1,7],[20,4]])
    usage=p.get('typedRequest',{});carrier=bytes.fromhex(context.get('argumentRawHex',''))
    need('own-actual-internal-MethodInfo',context.get('instructionRva')==program['contextInstructionVa']-base
        and context.get('fullTypeName')==TYPE and context.get('methodOwner')=='MemoryPack.MemoryPackReader'
        and context.get('methodName')=='ReadValue'and context.get('typeKind')==17 and context.get('register')=='r8'
        and len(carrier)==16 and carrier[10:12]==b'\x11\x80'and int.from_bytes(carrier[:8],'little')==nominal.get('typeDefinition')
        and tuple(usage.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments'))
            ==(6,'MemoryPack.MemoryPackReader','ReadValue',[],[TYPE])
        and usage.get('methodSpec')==context.get('methodSpec')and usage.get('instructionHex')==context.get('instructionHex')
        and nested['proof'].get('typedRequest')==usage)
    return base
