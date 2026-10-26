"""Exact ParamOutput21 request/call joins, separate from full field frames."""
import json

SCHEMA = 'endfield.levelscript-action-output-components.v1'
BINDING_SCHEMA = 'endfield.actionmap-ParamOutput-parent-request.v1'
CAP_PREFIX = 'story-actionmap-param-output:'


def need(check, condition):
    if not condition:
        raise ValueError('actionOutputBinding.'+check)


def _capability(component, capability):
    from scripts.game_data.codecs.levelscript.current_action_output_param import validate
    need('explicit-output-component', isinstance(component, dict) and component.get('schema') == SCHEMA)
    cap = component.get('capabilities', {}).get(capability)
    validate(cap)
    need('own-output-capability-key', capability == CAP_PREFIX+cap['typeName'])
    owners = [owner for owner in component.get('owners', []) if owner.get('typeName') == cap['typeName']]
    need('one-complete-output-owner', len(owners) == 1 and owners[0].get('status') == 'validated-conditional-output-child'
         and owners[0].get('capability') == cap)
    owner = owners[0]; source = owner.get('proof', {}).get('fullSource', {})
    need('complete-four-path-factory-and-reader-source', source.get('schema') == 'endfield.action-output-full-source.v1'
         and source.get('typeName') == cap['typeName'] and source.get('fourPathWrapperSourceProved') is True
         and source.get('factoryAndOriginalHolderProved') is True and source.get('typeArgumentSerialized') is False)
    from scripts.game_data.memorypack.levelscript_action_output_sources import verify
    verify(source, component.get('nativeInputs'))
    reader = component.get('referenceReader', {}); carrier = owner['proof'].get('closedCarrier', {})
    adapter = owner['proof'].get('adapter', {})
    need('same-own-output-graph-and-capability', source.get('typeName') == carrier.get('type') == cap['typeName']
         and carrier.get('argumentTypes') == [cap['outputType']] and type(carrier.get('bytes')) is int and carrier['bytes'] == 8
         and cap['readerMethodDefinition'] == reader.get('readerMethodDefinition')
         and cap['sourceTargetRva'] == reader.get('sourceTargetRva')
         and cap['canonicalCallbackTargetRva'] == adapter.get('callbackBinding', {}).get('canonicalTargetRva'))
    return cap, owner


def derive_binding(image, pins, *, typed_request, source_target, source_instruction, component, capability):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import validate_typed_usage_context
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext, closed_generic_reference_pointer_extent
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    _publication_gate(image, pins); base = image.pe.image_base
    cap, owner = _capability(component, capability)
    need('same-output-native-inputs', component.get('nativeInputs') == pins)
    validate_typed_usage_context(image, typed_request, label='actionOutputBinding.actual')
    bound = bind_typed_read(image, typed_request, method_name='ReadValue', argument=cap['typeName'], kind=21, reference=True)
    ctx = NativeReferenceContext(image)
    carrier = closed_generic_reference_pointer_extent(ctx, bound['argumentPointer'])
    need('same-own-Output-carrier', carrier['type'] == cap['typeName'] and carrier['bytes'] == 8
         and carrier['argumentTypes'] == [cap['outputType']]
         and carrier['definitionTypeIndex'] == ctx.index.types['Beyond.Gameplay.Actions.ParamOutput`1'].index
         and carrier['definitionTypeIndex'] == owner['proof']['closedCarrier']['definitionTypeIndex'])
    need('own-actual-reference-reader', bound['methodDefinition'] == cap['readerMethodDefinition']
         and type(source_target) is int and source_target-base == cap['sourceTargetRva'])
    need('actual-parent-call', isinstance(source_instruction, (list, tuple)) and len(source_instruction) == 2
         and type(source_instruction[0]) is int and type(source_instruction[1]) is str)
    raw = bytes.fromhex(source_instruction[1])
    need('actual-E8-target', len(raw) == 5 and raw[0] == 232
         and source_instruction[0]+5+int.from_bytes(raw[1:], 'little', signed=True) == source_target-base)
    image.check_instruction_windows([source_instruction], label='actionOutputBinding.actualE8')
    _publication_gate(image, pins)
    return json.loads(json.dumps(dict(schema=BINDING_SCHEMA, nativeInputs=pins, typeName=cap['typeName'],
        capability=capability, capabilitySnapshot=cap, typedRequest=typed_request,
        sourceInstruction=list(source_instruction), readerMethodDefinition=bound['methodDefinition'], sourceTargetRva=source_target-base,
        actualArgumentRawHex=image.pe.bytes_at_va(bound['argumentPointer'], 16).hex().upper(), closedCarrier=carrier,
        actualRequestProved=True, actualSourceCallProved=True, pointerEquivalenceClaimed=False,
        parentFieldAdmitted=False, parentArgumentLocalStoreFrameRequired=True, wholeOwnerAdmitted=False)))


def bind_reference(pins, join, component, capability):
    cap, owner = _capability(component, capability)
    need('same-output-native-inputs-and-parent-type', component.get('nativeInputs') == pins and join.get('typeName') == cap['typeName'])
    usage = join.get('typedRequest', {}); context = join.get('sourceContext', {}); site = usage.get('instructionRva')
    need('closed-parent-ReadValue', (usage.get('tag'), usage.get('typeName'), usage.get('methodName'),
         usage.get('classArguments'), usage.get('methodArguments')) == (6, 'MemoryPack.MemoryPackReader', 'ReadValue', [], [cap['typeName']])
         and type(site) is int and site >= 0 and isinstance(usage.get('methodSpec'), list)
         and len(usage['methodSpec']) == 3 and all(type(n) is int for n in usage['methodSpec']))
    raw = bytes.fromhex(context.get('argumentRawHex', ''))
    need('actual-Output21-reference-context', len(raw) == 16 and raw[10:12] == bytes((21, 0))
         and (context.get('methodOwner'), context.get('methodName'), context.get('fullTypeName'), context.get('register'), context.get('typeKind'))
         == ('MemoryPack.MemoryPackReader', 'ReadValue', cap['typeName'], 'rdx', 21)
         and type(context.get('typeKind')) is int
         and (context.get('instructionRva'), context.get('instructionHex'), context.get('methodSpec'))
         == (site, usage.get('instructionHex'), usage['methodSpec']))
    bound = component.get('parentBindings', {}).get(str(site), {})
    need('fresh-output-parent-binding', bound.get('schema') == BINDING_SCHEMA and bound.get('nativeInputs') == pins
         and bound.get('typeName') == cap['typeName'] and bound.get('capability') == capability
         and bound.get('capabilitySnapshot') == cap and bound.get('typedRequest') == usage
         and bound.get('sourceInstruction') == join.get('sourceInstruction')
         and bytes.fromhex(bound.get('actualArgumentRawHex', '')) == raw
         and bound.get('actualRequestProved') is True and bound.get('actualSourceCallProved') is True
         and bound.get('pointerEquivalenceClaimed') is False and bound.get('parentFieldAdmitted') is False)
    carrier = bound.get('closedCarrier', {}); original = owner['proof']['closedCarrier']
    need('same-Output-definition-and-runtime-type-argument', carrier.get('type') == cap['typeName']
         and type(carrier.get('bytes')) is int and carrier['bytes'] == 8
         and carrier.get('argumentTypes') == [cap['outputType']]
         and carrier.get('definitionTypeIndex') == original.get('definitionTypeIndex')
         and carrier.get('definitionTypeRecordHex') == original.get('definitionTypeRecordHex'))
    instruction = join.get('sourceInstruction'); target = join.get('sourceTargetRva')
    need('same-actual-output-source-target', isinstance(instruction, list) and len(instruction) == 2
         and type(instruction[0]) is int and type(target) is int and target > 0
         and bound.get('readerMethodDefinition') == usage['methodSpec'][0] == cap['readerMethodDefinition']
         and bound.get('sourceTargetRva') == target == cap['sourceTargetRva'])
    encoded = bytes.fromhex(instruction[1])
    need('same-E8-source-target', len(encoded) == 5 and encoded[0] == 232
         and instruction[0]+5+int.from_bytes(encoded[1:], 'little', signed=True) == target)
    return dict(fieldName=join['fieldName'], typeName=cap['typeName'], capability=capability,
                readerMethodDefinition=cap['readerMethodDefinition'], sourceTargetRva=cap['sourceTargetRva'],
                sourceReferenceKind=21, referenceOutputBytes=8, closedCarrierProved=True,
                actualCallbackEqualsProvedChildRequired=True, parentArgumentLocalStoreFrameRequired=True, parentFieldAdmitted=False)
