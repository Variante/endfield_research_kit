"""Own reference Param<EntityPtr> array; reference stride is not element wire size.

Only this exact kind21 Param carrier is admitted. The existing CLASS18 array
owner is unchanged. Each element independently uses the complete current
four-member EntityPtr Param and its own MC3/default40 constant formatter.
Actual compatible provider/callback selection, normal typed allocation and
disabled collector remain conditions; gameplay pointer resolution is absent.
"""
import json

SCHEMA = 'endfield.levelscript-entity-param-array-components.v1'
CAPABILITY = 'story-actionmap-entity-param-array'
VALUE = 'Beyond.Gameplay.Core.EntityPtr'
ELEMENT = 'Beyond.Gameplay.Actions.Param`1<' + VALUE + '>'
PARENT = 'Beyond.Gameplay.Actions.ListMakeEntityPtr'


def need(check, condition):
    if not condition:
        raise ValueError('entityParamArray.' + check)


def require_carrier(carrier):
    raw = bytes.fromhex(carrier.get('declaredTypeRecordHex', '')) if isinstance(carrier, dict) else b''
    definition = bytes.fromhex(carrier.get('definitionTypeRecordHex', '')) if isinstance(carrier, dict) else b''
    need('exact-closed-reference-Param-carrier', isinstance(carrier, dict)
         and carrier.get('type') == ELEMENT and carrier.get('bytes') == 8
         and type(carrier.get('definitionTypeIndex')) is int
         and carrier.get('argumentTypes') == [VALUE]
         and len(raw) == len(definition) == 16
         and raw[10:12] == b'\x15\x00' and definition[10:12] == b'\x12\x00')


def capability(child, *, reader_definition, reader_target, canonical_target, count_limit=4096):
    from scripts.game_data.codecs.levelscript.current_entity_param_array import validate
    cap = dict(schema='endfield.levelscript-entity-param-array-capability.v1',
               elementType=ELEMENT, closedArrayType=ELEMENT + '[]', countLimit=count_limit,
               countWireBytes=4, nullCount=-1, freshArrayRequired=True,
               elementReferenceKind=21, referenceSlotBytes=8, elementWireBytes=None,
               elementCapability=child, readerMethodDefinition=reader_definition,
               sourceTargetRva=reader_target, canonicalCallbackTargetRva=canonical_target,
               elementGrammarAdmitted=True, positiveCountsAdmitted=True,
               actualElementCallbackEqualsProvedParamRequired=True,
               actualProviderEqualsProvedProviderRequired=True,
               liveFormatterSelectionObserved=False, runtimeEntityResolutionProved=False,
               parentFieldAdmitted=False, wholeOwnerAdmitted=False)
    validate(cap)
    return cap


def derive(image, pins, *, count_limit=4096):
    from scripts.game_data import levelscript_list_make_entity_ptr_native as legacy
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import (
        derive_typed_usage_context, validate_generic_contexts, validate_typed_usage_context)
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext, closed_generic_reference_pointer_extent
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.memorypack import pointer_param as pointer, scalar_param_native as scalar
    from scripts.game_data.memorypack.array_reference_sources import validate_read_array_context
    from scripts.game_data.memorypack.buff_ptr_sources import _call
    from scripts.game_data.memorypack.levelscript_condition_storage_param_components import derive_many
    from scripts.game_data.memorypack.skill_cost_data_list_sources import _load
    from scripts.game_data.memorypack.skill_passive_map_sources import _barrier
    from scripts.game_data.memorypack.skill_reference_array_sources import array_program, provider_program, induction
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    need('exact-count-domain', type(count_limit) is int and count_limit == 4096)
    _publication_gate(image, pins)
    base = image.pe.image_base
    ctx = NativeReferenceContext(image)
    before = legacy.DEFAULT_CONTRACT.read_bytes()
    parent = legacy._contract(legacy.DEFAULT_CONTRACT)
    need('same-parent-native-inputs', parent['nativeInputs'] == pins)
    # Native-only replay. Historical source receipts are neither read nor
    # refreshed and confer no current corpus authority on this child.
    legacy._validate_native(image, parent)
    need('one-own-final-array-member', parent['route']['typeName'] == PARENT
         and parent['route']['fields'][-1] == ['list', 'Param<EntityPtr>[]'])
    recorded, = parent['nestedContexts']
    usage = derive_typed_usage_context(image, recorded['instructionRva'], label='entityParamArray.actual')
    validate_typed_usage_context(image, usage, label='entityParamArray.actual')
    bound = bind_typed_read(image, usage, method_name='ReadArray', argument=ELEMENT, kind=21, reference=True)
    carrier = closed_generic_reference_pointer_extent(ctx, bound['argumentPointer'])
    require_carrier(carrier)
    need('own-Param-definition', carrier['definitionTypeIndex'] == ctx.index.types['Beyond.Gameplay.Actions.Param`1'].index)
    event = parent['orderedReads'][-1]
    need('same-actual-last-member', event['memberIndex'] == 7 and event['fieldName'] == 'list'
         and event['readKind'] == 'Param<EntityPtr>[]')
    instruction = [event['sourceCallsiteRva'], event['sourceCallHex']]
    target = legacy._call_target(image, instruction[0], instruction[1]) + base
    need('same-recorded-array-target', target - base == event['sourceTargetRva'])
    array = pointer.owned(image, target)
    helpers = {name: _call(array, offset) for name, offset in dict(arrayAllocate=247, provider=373, prepare=435).items()}
    offsets = scalar.reader_offsets(image, 'entityParamArray')
    offsets['totalLength'] = ctx.field('MemoryPack.MemoryPackReader::totalLength')[2] - 16
    programs = [array_program(array['regions'], target, offsets, helpers, count=n, count_limit=3) for n in range(-1, 4)]
    loop = induction(programs, count_limit=count_limit)
    children = derive_many(image, pins, [VALUE])
    owners = [owner for owner in children['owners'] if owner.get('status') == 'validated-conditional-Param-child']
    need('one-complete-own-Param-child', len(owners) == 1 and owners[0]['typeName'] == ELEMENT)
    owner = owners[0]
    child = owner['capability']
    need('same-owned-Param-carrier', all(owner['proof']['closedCarrier'][key] == carrier[key]
         for key in ('type', 'bytes', 'definitionTypeIndex', 'argumentTypes', 'definitionTypeRecordHex')))
    contexts = ContextSymbols(image)
    first = contexts.context(usage['methodSpec'][0], is_method=True)
    second = contexts.context(first['entries'][0]['methodSpec'][0], is_method=True)
    validate_generic_contexts(image, [first, second], label='entityParamArray.contexts')
    context = validate_read_array_context(image, [first, second], usage, GenericEntries(image),
        bound['argumentPointer'], children['referenceReader']['valueContext']['formatterDeserializeDefinition'],
        fail=lambda k, e, a: need(k, e == a))
    provider = pointer.owned(image, helpers['provider'])
    provider_helpers = {name: _call(provider, offset) for name, offset in dict(
        classFromType=88, hash=145, compare=238, backend=376, indexedType=393, assignable=409).items()}
    provider_proof = provider_program(provider['regions'], provider['pointer'], provider_helpers)
    reader = children['referenceReader']['program']
    need('same-independent-Param-provider-cache',
         (reader['providerClassCell'], reader['cacheCell']) ==
         (provider_proof['providerClassCell'], provider_proof['cache']['cacheGlobalCell']))
    provider_usages = []
    for program in programs:
        site = program['providerUsageInstruction']
        if site is None:
            continue
        actual = derive_typed_usage_context(image, site - base, label='entityParamArray.provider')
        need('actual-provider-class', (actual['tag'], actual['typeName']) == (1, 'MemoryPack.MemoryPackFormatterProvider')
             and actual['usageCellRva'] + base == provider_proof['providerClassCell'])
        provider_usages.append(actual)
    collector = _load('model_view_state_controller_native.json', pins)
    barrier = _barrier(image, collector['collector']['entryRva'] + base)
    need('one-disabled-collector', all(program['collectorFlag'] == base + barrier['result']['disabledFlagRva'] for program in programs))
    cap = capability(child, reader_definition=usage['methodSpec'][0], reader_target=target-base,
                     canonical_target=child['canonicalCallbackTargetRva'], count_limit=count_limit)
    need('parent-native-contract-bookend', legacy.DEFAULT_CONTRACT.read_bytes() == before)
    _publication_gate(image, pins)
    return json.loads(json.dumps(dict(schema=SCHEMA, status='validated-conditional-entity-Param-array', nativeInputs=pins,
        capabilities={CAPABILITY: cap}, proof=dict(parentNative={k: v for k, v in parent.items() if k != 'sourceReceipts'},
            actualRequest=usage, actualInstruction=instruction, closedCarrier=carrier,
            sourceWindows=array['windows'], sourceRegions=[(a, b.hex().upper()) for a, b in array['regions']],
            readerOffsets=offsets, helperRvas={k: v-base for k, v in helpers.items()}, programs=programs, induction=loop,
            contexts=[first, second], arrayContext=context, ParamSource=children,
            providerWindows=provider['windows'], providerRegions=[(a, b.hex().upper()) for a, b in provider['regions']],
            providerProgram=provider_proof, providerHelperRvas={k: v-base for k, v in provider_helpers.items()},
            actualProviderUsages=provider_usages, barrier=barrier),
        sourceReceiptAuthority=False, currentVfsCorpus=False, parentFieldAdmitted=False, wholeOwnerAdmitted=False)))
