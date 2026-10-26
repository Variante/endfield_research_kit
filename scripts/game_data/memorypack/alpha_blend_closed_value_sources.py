"""Own closed AlphaBlend helper; hidden-pointer preservation supplies no wire."""
import json

TYPE='Beyond.Gameplay.View.Animation.AlphaBlend'
SCHEMA='endfield.alpha-blend-closed-value-source.v1'


def need(check,condition,detail=None):
    if not condition:raise ValueError('alphaBlendClosed.'+check+(':'+str(detail)[:1200]if detail is not None else''))


def derive(image,pins,*,source_target):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack.generated_vector3_source import forwarder_program
    from scripts.game_data.memorypack import generated_action_sources as actions,pointer_param as pointer
    from scripts.game_data.memorypack.alpha_blend_value_transfer import derive as nested_read
    _publication_gate(image,pins);base=image.pe.image_base
    need('actual-owned-helper',type(source_target)is int and source_target>base)
    body=pointer.owned(image,source_target);program=forwarder_program(body['regions'],source_target)
    contexts,skipped=actions._contexts(image,body['rows']);need('one-internal-actual-context',len(contexts)==1);context,=contexts
    raw=bytes.fromhex(context.get('argumentRawHex',''))
    need('own-ordinary-Alpha56-context',tuple(context.get(k)for k in('methodOwner','methodName','fullTypeName','typeKind','register'))
        ==('MemoryPack.MemoryPackReader','ReadValue',TYPE,17,'r8')and len(raw)==16 and raw[10:12]==bytes((17,128))
        and int.from_bytes(raw[:8],'little')==context.get('typeDefinition')
        and context.get('instructionRva')==program['contextInstructionVa']-base)
    usage=derive_typed_usage_context(image,context['instructionRva'],label='alphaBlendClosed.internal')
    need('same-actual-context-bytes-and-spec',usage.get('instructionHex')==context['instructionHex']and usage.get('methodSpec')==context['methodSpec'])
    nested=nested_read(image,pins,typed_request=usage,source_target=program['nestedTargetVa'],count_limit=10000)
    need('own-independent-nested-managed56',nested.get('nativeInputs')==pins and nested.get('typeName')==TYPE
        and nested.get('managedBytes')==56 and nested.get('resultAbi')=='hidden-local'and nested.get('actualSourceProved')is True
        and nested.get('wireGrammarAdmitted')is False and nested.get('readerMethodDefinition')==context['methodSpec'][0]
        and nested.get('sourceTargetRva')==program['nestedTargetVa']-base)
    _publication_gate(image,pins)
    result=dict(nested);result.update(schema=SCHEMA,status='proved-conditional-own-Alpha56-closed-forwarder',
        sourceTargetRva=source_target-base,sourceContextMode='owned-closed-forwarder',contextMode='owned-closed-forwarder',
        pointerAliasClaimed=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        proof=dict(nested['proof'],internalContext=context,forwarderProgram=program,nestedSource=nested,
            actualFamily=image.unwind_index.family(source_target-base),actualWindows=body['windows'],
            closedSourceRegions=[[a-base,h.hex()]for a,h in body['regions']],skippedRuntimeCells=skipped))
    result=json.loads(json.dumps(result));verify(result,pins);return result


def verify(actual,pins):
    from scripts.game_data.memorypack.generated_vector3_source import forwarder_program
    from scripts.game_data.memorypack.animation_custom_dictionary_callbacks import regions
    from scripts.game_data.memorypack import alpha_blend_value_transfer as transfer
    need('own-current-closed-Alpha56',actual.get('schema')==SCHEMA and actual.get('nativeInputs')==pins
        and actual.get('status')=='proved-conditional-own-Alpha56-closed-forwarder'and actual.get('typeName')==TYPE
        and actual.get('managedBytes')==56 and actual.get('resultAbi')=='hidden-local'and actual.get('actualSourceProved')is True
        and actual.get('referenceLaneOffsets')==[8]and actual.get('paddingByteRanges')==[[52,56]]
        and actual.get('sourceContextMode')==actual.get('contextMode')=='owned-closed-forwarder'
        and all(actual.get(k)is False for k in('wireGrammarAdmitted','pointerAliasClaimed','parentFieldAdmitted','wholeOwnerAdmitted')))
    p=actual['proof'];program=p['forwarderProgram'];selected=program.get('selectedBytes',[]);need('owned-helper-entry',bool(selected))
    base=selected[0][0]-actual['sourceTargetRva'];raw=regions(p['actualWindows'],p['closedSourceRegions'],base,'closed-Alpha56')
    need('whole-hidden-pointer-helper',json.loads(json.dumps(forwarder_program(raw,base+actual['sourceTargetRva'])))==program)
    nested=p['nestedSource'];q=nested['proof'];usage=q['typedRequest'];context=p['internalContext'];carrier=bytes.fromhex(context.get('argumentRawHex',''))
    need('same-independent-nested-source',nested.get('schema')=='endfield.alpha-blend-value-transfer.v1'
        and nested.get('status')=='proved-conditional-alpha-blend-value56-read'and nested.get('nativeInputs')==pins
        and nested.get('typeName')==TYPE and nested.get('managedBytes')==56 and nested.get('resultAbi')=='hidden-local'
        and nested.get('actualSourceProved')is True and nested.get('wireGrammarAdmitted')is False
        and nested.get('sourceTargetRva')==program['nestedTargetVa']-base
        and nested.get('readerMethodDefinition')==context.get('methodSpec',[None])[0]
        and q.get('childSource')==p.get('childSource'))
    nominal=q['childSource']['proof']['layout']
    need('same-own-ordinary-internal-context',len(carrier)==16 and carrier[10:12]==bytes((17,128))
        and int.from_bytes(carrier[:8],'little')==nominal.get('typeDefinition')
        and q['childSource'].get('schema')=='endfield.alpha-blend-wrapper-source.v1'
        and q['childSource'].get('typeName')==TYPE and q['childSource'].get('managedBytes')==56
        and tuple(context.get(k)for k in('methodOwner','methodName','fullTypeName','typeKind','register'))==('MemoryPack.MemoryPackReader','ReadValue',TYPE,17,'r8')
        and context.get('instructionRva')==program['contextInstructionVa']-base
        and usage.get('instructionHex')==context.get('instructionHex')and usage.get('methodSpec')==context.get('methodSpec'),
        dict(carrierLength=len(carrier),carrierKind=carrier[10:12].hex(),carrierDefinition=int.from_bytes(carrier[:8],'little'),
            nominalType=q['childSource'].get('typeName'),nominalDefinition=nominal.get('typeDefinition'),
            actualContext={k:context.get(k)for k in('methodOwner','methodName','fullTypeName','typeKind','register','instructionRva')},
            expectedInstructionRva=program['contextInstructionVa']-base,sameUsageBytes=usage.get('instructionHex')==context.get('instructionHex'),
            sameMethodSpec=usage.get('methodSpec')==context.get('methodSpec')))
    transfer.request_shape(usage)
    source=regions(q['sourceWindows']['read'],q['actualSourceRegions']['read'],base,'nested-Alpha56-read')
    symbols={k:base+v for k,v in q['symbolRvas'].items()}
    need('whole-nested-actual-hidden56-reader',json.loads(json.dumps(transfer.read_program(source,program['nestedTargetVa'],symbols)))==q['readerProgram'])
    return base
