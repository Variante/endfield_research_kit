"""Independent pooled-string and Int32 callbacks for animation dictionaries.

This module supplies no enum, Single, list or dictionary grammar. Every actual
dispatcher is selected separately from the nominal callback, with exact slot5
and MethodInfo transfer. Runtime receiver/provider choice stays conditional.
"""
import hashlib
import json

from scripts.game_data.il2cpp.formatter_value_paths import deserialize_slot


def need(check, condition):
    if not condition:
        raise ValueError('animationCustomDictionaryCallback.'+check)


def regions(windows, values, base, label):
    need(label+'-exact-window-region-set', bool(windows) and len(windows) == len(values)
        and len({a for a, _ in values}) == len(values))
    result = []
    for at, hex_bytes in values:
        raw = bytes.fromhex(hex_bytes)
        matching = [w for w in windows if w.get('startRva') == at and w.get('endRva', 0)-at == len(raw)]
        need(label+'-native-byte-hash', len(matching) == 1
            and hashlib.sha256(raw).hexdigest().upper() == matching[0].get('sha256'))
        result.append((base+at, raw))
    return result


def derive_integer(image, pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.context import type_parameter_owner
    from scripts.game_data.il2cpp.formatter_composition import _vtable
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import pointer_param as pointer, scalar_param_native as scalar, int_list_sources
    _publication_gate(image, pins); base = image.pe.image_base; md = image.metadata; ctx = NativeReferenceContext(image)
    owner = ctx.index.types['MemoryPack.Formatters.UnmanagedFormatter`1']
    methods = [m for m in md.methods_for(owner) if md.string(m.name_index) == 'Deserialize']
    need('one-owned-int-formatter-method', len(methods) == 1)
    method, = methods; parameters = list(md.parameters_for(method))
    need('own-instance-void-two', not method.flags & 16 and ctx.type_name(method.return_type) == 'void'
        and method.parameter_count == len(parameters) == 2)
    _vtable(image, owner.index, 5, method.index, 'animationCustomDictionaryInt')
    reader = image.pe.bytes_at_va(ctx.type_pointer(parameters[0].type_index), 16)
    output = image.pe.bytes_at_va(ctx.type_pointer(parameters[1].type_index), 16)
    need('Reader-byref-and-owned-VAR-out', ctx.type_name(parameters[0].type_index) == 'MemoryPack.MemoryPackReader'
        and reader[10:12] == bytes((17, 32)) and output[10:12] == bytes((19, 32)))
    parameter = type_parameter_owner(md.buf, int.from_bytes(output[:8], 'little'),
        [t.generic_container_index for t in md.types], source='animationCustomDictionaryInt')
    need('sole-own-class-parameter', (parameter.get('typeIndex'), parameter.get('ordinal')) == (owner.index, 0))
    registered = GenericEntries(image).resolve(method.index, ['int'], [])
    arg, = registered['classInstantiation']['arguments']
    scalar.ordinary(image, arg['type_pointer_va'], 8, 'animationCustomDictionaryInt.argument')
    need('closed-Int32-carrier', bytes.fromhex(arg['raw_type_record_hex'])[10:12] == bytes((8, 128)))
    actual = pointer.owned(image, registered['pointer']); offsets = scalar.reader_offsets(image, 'animationCustomDictionaryInt')
    program = int_list_sources.integer(actual['regions'], registered['pointer'], offsets)
    result = dict(schema='endfield.animation-custom-Int32-callback.v1', status='validated-conditional-callback',
        nativeInputs=dict(pins), typeName='int', wireBytes=4, outputBytes=4, callbackSlot=5,
        callbackMethodDefinition=method.index, callbackTargetRva=registered['pointer']-base,
        numericConversion=False, actualRuntimeSelectionObserved=False,
        proof=dict(registration=registered, readerParameterRawHex=reader.hex().upper(),
            outputParameterRawHex=output.hex().upper(), outputParameterOwner=parameter,
            windows=actual['windows'], regions=[[at-base, b.hex()] for at, b in actual['regions']],
            program=program, readerOffsets=offsets),
        conditions=['Exact ready provider receiver selects this independently registered Int32 slot5 callback and coherent MethodInfo.',
            'Sufficient coherent disjoint buffered input/output, nonwrapping Reader updates and normal Win64 returns.'])
    _publication_gate(image, pins); return json.loads(json.dumps(result))


def derive_string(image, pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.contracts import CONTRACTS_DIR
    from scripts.game_data.memorypack.pooled_string_list_sources import validate_string_components, pooled_string
    _publication_gate(image, pins)
    path = CONTRACTS_DIR/'levelscript_pooled_string_list_native.json'; before = path.read_bytes(); fact = json.loads(before)
    need('current-reviewed-string-source', fact.get('schema') == 'endfield.levelscript-pooled-string-list-native.v1'
        and fact.get('status') == 'exact-current-build' and fact.get('nativeInputs') == pins)
    result = validate_string_components(image, fact)
    selected = [p for p in fact['programs'] if p['role'] == 'string']
    need('one-independently-owned-string-callback', len(selected) == 1
        and result.get('stringFormatterSlot') == 5 and result.get('wireBytes') == 4
        and result.get('managedReferenceBytes') == 8 and result.get('liveProviderSelectionProved') is False)
    methods = [m for m in fact['methods'] if m[1:3] == ['MemoryPack.BeyondStringFormatter', 'Deserialize']]
    need('one-owned-string-Deserialize-metadata', len(methods) == 1)
    method, = methods; callback, = selected
    need('own-BeyondStringFormatter-Deserialize', method[3] == callback['entryRva'])
    windows = callback['windows']; base = image.pe.image_base
    actual = [[w['startRva'], image.pe.bytes_at_va(base+w['startRva'], w['endRva']-w['startRva']).hex()] for w in windows]
    pool_path = CONTRACTS_DIR/'memorypack_pooled_string_reader_native.json'; pool_before = pool_path.read_bytes()
    pool = json.loads(pool_before); need('same-current-pool-native-inputs', pool.get('nativeInputs') == pins)
    symbols = dict(pool=pool['inlineSymbols']['pool'], empty=pool['inlineSymbols']['empty'], lookup=pool['lookupRva'])
    owned = [(base+at, bytes.fromhex(h)) for at,h in actual]
    programs = [pooled_string(owned, base+method[3], {k:base+v for k,v in symbols.items()}, mode=mode)
        for mode in ('lookup', 'empty', 'null')]
    need('reviewed-string-source-bookend', before == path.read_bytes() and pool_before == pool_path.read_bytes())
    _publication_gate(image, pins)
    return json.loads(json.dumps(dict(schema='endfield.animation-custom-pooled-string-callback.v1', status='validated-conditional-callback',
        nativeInputs=dict(pins), typeName='string', wireBytes=4, outputBytes=8, callbackSlot=5,
        callbackMethodDefinition=method[0], callbackTargetRva=method[3], encoding='int32-pool-index',
        emptyIndex=-1, nullIndex=-2, actualRuntimeSelectionObserved=False,
        proof=dict(stringComponents=result, windows=windows, regions=actual, reviewedStringFact=fact,
            symbolRvas=symbols, programs=programs),
        conditions=['The actual ready provider receiver selects the independently owned BeyondStringFormatter slot5 and coherent MethodInfo.',
            'Matching selected initialized StringPool and normal lookup ABI; pool-absent inline UTF8, refill and errors excluded.'])))


def bind_dispatch(image, pins, source, callback):
    """Fresh actual key helper, without registration-pointer equivalence."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.memorypack import pointer_param as pointer
    _publication_gate(image, pins); base = image.pe.image_base
    need('same-actual-key-type-and-pins', callback.get('nativeInputs') == source.get('nativeInputs') == pins
        and callback.get('typeName') == source.get('keyType'))
    target = base+source['proof']['symbolRvas']['keyDispatch']; actual = pointer.owned(image, target)
    calls = [control_transfer(r)['target'] for r in actual['rows'] if bytes.fromhex(r['bytes'])[:1] == b'\xe8']
    need('actual-dispatch-preparation', bool(calls))
    selected = base+callback['callbackTargetRva']
    if callback['typeName'] == 'int':
        from scripts.game_data.memorypack.int_list_sources import dispatcher
        program = dispatcher(actual['regions'], target, source['proof']['readerOffsets'], prepare=calls[0], callback=selected)
    else:
        program = deserialize_slot(actual['regions'], target, prepare=calls[0], callback=selected)
    result = dict(sourceTargetRva=target-base, callbackTargetRva=selected-base,
        windows=actual['windows'], regions=[[at-base, b.hex()] for at, b in actual['regions']], program=program,
        callbackSelectionConditional=True, runtimeSelectionObserved=False)
    _publication_gate(image, pins); return json.loads(json.dumps(result))
