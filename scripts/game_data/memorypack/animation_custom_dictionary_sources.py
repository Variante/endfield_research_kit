"""Actual class-only static-out animation dictionary sources.

Each finite nominal request selects its own observed E8 body. The initialized,
buffered, fresh-output programs prove framing, local/argument transfers and
bounded loop control. They do not select a live formatter or establish any
key/value grammar, insertion behavior or enclosing AnimationConfig field.
"""
import json

from scripts.game_data.memorypack import animation_custom_dictionary_programs as paths

SCHEMA = 'endfield.animation-custom-dictionary-sources.v1'
OWNER = 'Beyond.SerializeFieldDictionary`2'
PARENT = 'Beyond.Gameplay.View.Animation.AnimationConfigJson'
DOMAINS = {
    'montages': (6, 'string', 'Beyond.Montage.AnimMontageData', 'reference-Montage'),
    'syncGroupCurves': (11, 'string', 'Beyond.FAnimationCurve', 'string-BeyondCurve'),
    'timeRefCurves': (12, 'int', 'Beyond.FAnimationCurve', 'int-BeyondCurve'),
}


def need(check, condition):
    if not condition:
        raise ValueError('animationCustomDictionarySource.' + check)


def type_name(domain):
    need('finite-owned-field', domain in DOMAINS)
    _, key, value, _ = DOMAINS[domain]
    return OWNER+'<'+key+','+value+'>'


def request_shape(usage, domain):
    need('finite-request-domain', domain in DOMAINS)
    _, key, value, _ = DOMAINS[domain]
    raw = bytes.fromhex(usage.get('instructionHex', ''))
    spec = usage.get('methodSpec')
    need('actual-R8-class-only-MethodInfo', usage.get('tag') == 6
        and (usage.get('typeName'), usage.get('methodName'), usage.get('classArguments'), usage.get('methodArguments'))
        == (OWNER, 'DeserializeV2', [key, value], [])
        and len(raw) == 7 and raw[:3] == bytes.fromhex('4c8b05')
        and type(usage.get('instructionRva')) is int and usage['instructionRva'] >= 0
        and isinstance(spec, (list, tuple)) and len(spec) == 3
        and all(type(n) is int for n in spec) and spec[0] >= 0 and spec[1] >= 0 and spec[2] == -1
        and type(usage.get('methodSpecIndex')) is int and usage['methodSpecIndex'] >= 0)
    return key, value


def request_context(image, usage, domain):
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.memorypack import scalar_param_native as scalar
    key, value = request_shape(usage, domain)
    fresh = derive_typed_usage_context(image, usage['instructionRva'], label='animationCustomDictionarySource')
    need('same-fresh-actual-request', json.loads(json.dumps(fresh)) == json.loads(json.dumps(usage)))
    ctx = NativeReferenceContext(image); md = image.metadata; owner = ctx.index.types[OWNER]
    args = image.instantiations.resolve(usage['methodSpec'][1]).arguments
    need('two-closed-class-arguments', len(args) == 2)
    facts = []
    for name, arg in zip((key, value), args):
        raw = image.pe.bytes_at_va(arg.type_pointer_va, 16)
        kind = 14 if name == 'string' else 8 if name == 'int' else 17 if name == 'Beyond.FAnimationCurve' else 18
        scalar.ordinary(image, arg.type_pointer_va, kind, 'animationCustomDictionarySource.argument', reference=kind in (14, 18))
        need('actual-closed-nominal-carrier', raw[10:12] == bytes((kind, 0 if kind in (14, 18) else 128))
            and (kind in (8, 14) or int.from_bytes(raw[:8], 'little') == ctx.index.types[name].index))
        facts.append(dict(typeName=name, rawTypeRecordHex=raw.hex().upper(), typeKind=kind,
            typeDefinition=None if kind in (8, 14) else ctx.index.types[name].index))
    method = md.methods[usage['methodSpec'][0]]; parameters = list(md.parameters_for(method))
    need('own-static-void-two-ABI', method.declaring_type == owner.index and bool(method.flags & 16)
        and ctx.type_name(method.return_type) == 'void' and method.parameter_count == len(parameters) == 2)
    reader = image.pe.bytes_at_va(ctx.type_pointer(parameters[0].type_index), 16)
    output = image.pe.bytes_at_va(ctx.type_pointer(parameters[1].type_index), 16)
    need('actual-Reader-and-reference-out-byref', ctx.type_name(parameters[0].type_index) == 'MemoryPack.MemoryPackReader'
        and reader[10:12] == bytes((17, 32)) and output[10:12] == bytes((21, 32)))
    opened = ContextSymbols(image).type(ctx.type_pointer(parameters[1].type_index))
    need('output-owned-class-VARs', opened['definition']['name'] == OWNER
        and [(a['parameterOwner'].get('typeIndex'), a['parameterOwner'].get('ordinal'))
             for a in opened['classArguments']] == [(owner.index, 0), (owner.index, 1)])
    return dict(typedRequest=usage, typeName=type_name(domain), typeDefinition=owner.index,
        readerParameterRawHex=reader.hex().upper(), outputParameterRawHex=output.hex().upper(),
        outputType=opened, arguments=facts, methodInfoRegister='r8', resultAbi='void-byref-reference8')


def context_slots(image):
    """Own only the generic class slot identities, never another map's body."""
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    ctx = NativeReferenceContext(image); owner = ctx.index.types[OWNER]
    result = ContextSymbols(image).context(owner.index, slots=[5, 21, 22, 23, 24])
    entries = {e['relativeSlot']: e for e in result['entries']}
    def variables(args, ordinals):
        need('owned-open-class-parameters', [(a['parameterOwner'].get('typeIndex'),
            a['parameterOwner'].get('ordinal')) for a in args] == [(owner.index, n) for n in ordinals])
    allocated = entries[21]['type']
    need('own-allocated-dictionary-class', allocated['definition']['name'] == OWNER)
    variables(allocated['classArguments'], [0, 1])
    for slot, declaring, method, role, ordinals in (
        (5, 'System.Collections.Generic.Dictionary`2', 'set_Item', 'classArguments', [0, 1]),
        (22, OWNER, '.ctor', 'classArguments', [0, 1]),
        (23, 'MemoryPack.MemoryPackFormatterProvider', 'GetFormatter', 'methodArguments', [0]),
        (24, 'MemoryPack.MemoryPackFormatterProvider', 'GetFormatter', 'methodArguments', [1]),
    ):
        row = entries[slot]
        need('exact-helper-slot-'+str(slot), (row['typeName'], row['methodName']) == (declaring, method))
        variables(row[role], ordinals)
    return result


def caller_program(regions, usage, source_target, *, base):
    """Literal R8 MethodInfo and fresh-out-address argument setup through E8.

    The zero source, complete enclosing frame and named field transfer are
    intentionally not inferred by this bounded caller fragment.
    """
    from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
    at = base+usage['instructionRva']; g = BytesPath(regions, at)
    g.take(usage['instructionHex'])
    g.take('488d5424'); home = g.read(1)[0]
    need('owned-reference-local-home', 32 <= home < 128 and home % 8 == 0)
    g.take('488bcf'); call = g.at; g.call(source_target)
    return dict(selectedBytes=g.seen, sourceInstruction=[call-base,
        'e8'+(source_target-call-5).to_bytes(4, 'little', signed=True).hex()],
        sourceTargetRva=source_target-base, actualMethodInfoRegister='r8',
        readerRegister='rdi', outputHomeOffset=home, referenceBytes=8,
        zeroOutputAndReaderOriginRequired=True, parentFieldAdmitted=False, enclosingFrameAdmitted=False)


def parent_source(image, domain, usage, source_target):
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import pointer_param as pointer
    ctx = NativeReferenceContext(image); base = image.pe.image_base
    wrappers = [w for w in image.memorypack_wrappers.values() if w.wrapped_type == PARENT]
    need('one-current-AnimationConfig-wrapper', len(wrappers) == 1)
    wrapper, = wrappers; index = DOMAINS[domain][0]
    need('own-exact-wrapper-field', len(wrapper.members) == 15
        and (wrapper.members[index].name, wrapper.members[index].declared_type) == (domain, type_name(domain)))
    field = ctx.field(PARENT+'::'+domain)
    need('own-actual-Original-field', field[:2] == (PARENT, type_name(domain)) and type(field[2]) is int and field[2] >= 16)
    method = pointer.methods(image, wrapper)['Deserialize']; parent = pointer.owned(image, image.method_pointer_va(method))
    program = caller_program(parent['regions'], usage, source_target, base=base)
    return dict(typeName=PARENT, wrapperName=wrapper.name, memberIndex=index, fieldName=domain, originalField=list(field),
        method=[method.index, wrapper.name, 'Deserialize', parent['pointer']-base],
        windows=parent['windows'], regions=[[a-base, raw.hex()] for a, raw in parent['regions']],
        program=program, actualTypedCallProved=True, zeroLocalProved=False,
        parentFieldAdmitted=False, enclosingFrameAdmitted=False)


def programs(regions, entry, offsets, profile):
    symbols = paths.symbols(regions, profile)
    checked = [paths.montage_program(regions, entry, offsets, symbols, count=n)
        if profile == 'reference-Montage' else paths.curve_program(regions, entry, offsets, symbols,
            count=n, key_kind='string' if profile == 'string-BeyondCurve' else 'int')
        for n in (-1, 0, 1, 2, 3)]
    return symbols, checked


def induction(checked, *, count_limit):
    from scripts.game_data.memorypack.counted_loop_sources import prove_induction
    need('literal-bounded-count-domain', type(count_limit) is int and 3 <= count_limit <= 4096)
    montage = checked[0]['profile'] == 'reference-Montage'
    return prove_induction(checked[1:], initial='448bef' if montage else '4533e4',
        increment='41ffc5' if montage else '41ffc4',
        comparison='443bac2490000000' if montage else '443ba424a0000000',
        counter='r13d' if montage else 'r12d', saved_count='RSP+144' if montage else 'RSP+160',
        max_count=count_limit, mode_key='newDictionary', backedge_sites=checked[2]['backedgeSites'])


def derive(image, pins, *, domain, typed_request, source_target, count_limit=4096):
    """Fresh actual source only; callback and enclosing owner are separate."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack import pointer_param as pointer, scalar_param_native as scalar
    from scripts.game_data.memorypack.skill_passive_map_sources import _barrier
    from scripts.game_data.memorypack.vector_layout import vector_recorder
    from scripts.game_data.memorypack import primitive_param
    _publication_gate(image, pins)
    need('actual-literal-source-target', type(source_target) is int and source_target > image.pe.image_base)
    context = request_context(image, typed_request, domain); _, key, value, profile = DOMAINS[domain]
    caller = parent_source(image, domain, typed_request, source_target)
    base = image.pe.image_base; actual = pointer.owned(image, source_target)
    offsets = scalar.reader_offsets(image, 'animationCustomDictionarySource')
    selected, checked = programs(actual['regions'], source_target, offsets, profile)
    counted = induction(checked, count_limit=count_limit)
    header = None
    if 'header' in selected:
        header = vector_recorder(image)(selected['header']-base, fragments=True)
        primitive_param.object_header_source(image, header, offsets)
    barrier = _barrier(image, selected['barrier'])
    helpers = {}
    for role in ('constructor', 'keyProvider', 'valueProvider', 'keyDispatch', 'valueDispatch', 'insert'):
        if role not in selected: continue
        owned = pointer.owned(image, selected[role])
        helpers[role] = dict(entryRva=selected[role]-base, windows=owned['windows'], rows=owned['rows'],
            regions=[[at-base, raw.hex()] for at, raw in owned['regions']])
    result = dict(schema=SCHEMA, status='validated-conditional-static-out-animation-source', nativeInputs=dict(pins),
        domain=domain, typeName=type_name(domain), keyType=key, valueType=value,
        sourceTargetRva=source_target-base, staticReaderMethodDefinition=typed_request['methodSpec'][0],
        resultAbi='void-byref-reference8', referenceBytes=8, actualSourceProved=True,
        closedPointerEquivalenceProved=False, callbackGrammarAdmitted=False, wholeOwnerAdmitted=False,
        proof=dict(request=context, actualParent=caller, contextSlots=context_slots(image), actualWindows=actual['windows'],
            actualSourceRegions=[[at-base, raw.hex()] for at, raw in actual['regions']],
            programs=checked, induction=counted, symbolRvas={k:v-base for k,v in selected.items()},
            readerOffsets=offsets, header=header, barrier=barrier, helpers=helpers),
        evidenceBoundary=dict(exact='Own class-only static MethodSpec and nominal K/V carriers, reference-out ABI, exact FF/new/buffered paths, local-to-insertion transfers, saved count and bounded source induction.',
            conditional=__doc__, structuralOnly='Serialized ordered entries; duplicate-key semantic outcome is not inferred.',
            unresolved=['live provider/closed MethodInfo compatibility and callback selection',
                'exact key/value grammar and insertion effects', 'parent zero local/field/full frame',
                'reused nonnull dictionary, cold/refill/error paths', 'whole AnimationConfig/physical EOF']))
    _publication_gate(image, pins)
    return json.loads(json.dumps(result))
