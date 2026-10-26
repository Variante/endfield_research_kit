"""Exact pooled Param<ObjectPtr<GlobalBuff>>, distinct from BuffPtr and BuffId.

The Param copies sixteen managed bytes. ObjectPtr's own wrapper serializes
raw uint32 cachedUid then its separately typed GlobalBuff reference. GlobalBuff
has no serialized fields: positive MC0 and FF remain distinct. Existing value
padding is transported by the hidden getter, never read from the wire or used
to invent a runtime object. Compatible closed callbacks and normal allocation,
constructor, provider, cache and disabled-collector effects are conditions.
"""
import json
import struct

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

VALUE = 'Beyond.ObjectPtr`1<Beyond.Gameplay.Core.GlobalBuff>'
TYPE = 'Beyond.Gameplay.Actions.Param`1<' + VALUE + '>'
BUFF = 'Beyond.Gameplay.Core.GlobalBuff'
SCHEMA = 'endfield.levelscript-global-buff-param-components.v1'
CAPABILITY = 'story-actionmap-global-buff-param'


def need(check, condition):
    if not condition:
        raise ValueError('globalBuffParam.' + check)


def _packet(body):
    return dict(entryVa=body['pointer'], sourceWindows=body['windows'],
                sourceRegions=[(a, b.hex().upper()) for a, b in body['regions']])


def _record(image, body, method):
    base = image.pe.image_base
    return dict(methodIndex=method.index, pointerRva=body['pointer']-base,
                instructions=[[int(r['va'], 16)-base, bytes.fromhex(r['bytes']).hex().upper()] for r in body['rows']])


def _calls(program):
    result = {}
    for call in program['calls']:
        role = call['role']; at = call['targetVa']
        need('same-repeated-helper.'+role, role not in result or result[role] == at)
        result[role] = at
    return result


def object_nominal(image, ctx, type_index):
    from scripts.game_data.il2cpp.context import type_parameter_owner
    from scripts.game_data.il2cpp.protocol import runtime_type_name
    from scripts.game_data.memorypack import scalar_param_native as scalar
    pointer = ctx.type_pointer(type_index); raw = image.pe.bytes_at_va(pointer, 16)
    scalar.ordinary(image, pointer, 21, 'globalBuffParam.closedValue')
    need('closed-ObjectPtr-name', runtime_type_name(image.pe, image.metadata, pointer) == VALUE and ctx.is_value_type(VALUE))
    carrier = int.from_bytes(raw[:8], 'little')
    definition, instance = struct.unpack('<QQ', image.pe.bytes_at_va(carrier, 16))
    scalar.ordinary(image, definition, 17, 'globalBuffParam.ObjectPtrDefinition')
    need('ObjectPtr-value-definition', runtime_type_name(image.pe, image.metadata, definition) == 'Beyond.ObjectPtr`1')
    argument, = image.instantiations.resolve_pointer(instance).arguments
    scalar.ordinary(image, argument.type_pointer_va, 18, 'globalBuffParam.GlobalBuff', reference=True)
    need('own-GlobalBuff-argument', runtime_type_name(image.pe, image.metadata, argument.type_pointer_va) == BUFF)
    td = ctx.index.types['Beyond.ObjectPtr`1']; md = image.metadata
    fields = [f for f in md.fields_for(td) if not ctx.field_attributes(f.type_index) & 16]
    need('own-open-field-declarations', [md.string(f.name_index) for f in fields] == ['obj', 'cachedUid'])
    obj, uid = fields; raw_obj = image.pe.bytes_at_va(ctx.type_pointer(obj.type_index), 16)
    scalar.ordinary(image, ctx.type_pointer(obj.type_index), 19, 'globalBuffParam.ObjectPtrOwnVAR')
    owner = type_parameter_owner(md.buf, int.from_bytes(raw_obj[:8], 'little'),
        [t.generic_container_index for t in md.types], source='globalBuffParam')
    need('reciprocal-ObjectPtr-VAR', (owner['typeIndex'], owner['ordinal']) == (td.index, 0))
    scalar.ordinary(image, ctx.type_pointer(uid.type_index), 9, 'globalBuffParam.cachedUid')
    need('own-uid-type', ctx.type_name(uid.type_index) == 'uint')
    return dict(typeName=VALUE, rawTypeHex=raw.hex().upper(), definitionTypeIndex=td.index,
                argumentType=BUFF, argumentRawTypeHex=image.pe.bytes_at_va(argument.type_pointer_va, 16).hex().upper(),
                ownGenericParameter=owner, openDefinitionOffsetsUsed=False)


def parent_call_program(regions, entry):
    g = BytesPath(regions, entry); cell = g.relative('488b15')
    g.take('488bcf', '488b1b'); at = g.at; target = g.relative('e8')
    g.take('4885db'); g.branch('74', False, 1)
    g.take('4533c0', '488bd0', '488bcb'); setter = g.relative('e8')
    return dict(selectedBytes=g.seen, usageCellVa=cell, instructionVa=at, targetVa=target,
                setterTargetVa=setter, sameReaderRdi=True, fullReferenceRaxToNamedSetter=True,
                parentHeaderAndFrameRequired=True, parentFieldAdmitted=False)


def derive(image, pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import pointer_param as pointer, primitive_param as primitive, scalar_param_native as scalar
    from scripts.game_data.memorypack import pooled_source_helper
    from scripts.game_data.memorypack.buff_ptr_param import value_methods
    from scripts.game_data.memorypack.levelscript_condition_param_sources import _reader, _reference_join
    from scripts.game_data.memorypack.levelscript_global_buff_param_programs import (
        param_program, object_program, global_program, param_factory_program, param_const_setter)
    from scripts.game_data.memorypack.levelscript_global_buff_value_sources import derive as derive_value
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    from scripts.game_data.memorypack.skill_passive_map_sources import _barrier
    from scripts.game_data.memorypack.vector_layout import vector_recorder
    from scripts.game_data.memorypack.wrapper_members import derive_from_image
    from scripts.game_data.codecs.levelscript.current_global_buff_param import validate
    _publication_gate(image, pins); base = image.pe.image_base; md = image.metadata
    ctx = NativeReferenceContext(image)
    wrappers = {}
    for type_name, members in ((TYPE, [('constValue', VALUE), ('idRef', 'int'), ('paramSource', 'int'), ('path', 'string')]),
                               (VALUE, [('cachedUid', 'uint'), ('obj', BUFF)]), (BUFF, [])):
        selected = [w for w in derive_from_image(image).values() if w.wrapped_type == type_name]
        need('one-own-wrapper.'+type_name, len(selected) == 1)
        wrapper = selected[0]; wrappers[type_name] = wrapper
        need('own-serialized-members.'+type_name, [(m.name, m.declared_type) for m in wrapper.members] == members)
        need('own-direct-wrapper-holder.'+type_name, ctx.field(wrapper.name+'::__instance') == (wrapper.name, type_name, 16))
    pw, ow, bw = (wrappers[n] for n in (TYPE, VALUE, BUFF))
    pmethods = pointer.methods(image, pw); bmethods = pointer.methods(image, bw)
    parent_bodies = {n: pointer.owned(image, image.method_pointer_va(pmethods[n])) for n in
        ('Deserialize', '.ctor', 'CreateInstance', 'set___constValue__', 'set___idRef__', 'set___paramSource__', 'set___path__')}
    records = {n: _record(image, body, pmethods[n]) for n, body in parent_bodies.items()}
    primitive.reader_abi(image, ctx, pmethods['Deserialize'], pw)
    for name in ('.ctor', 'CreateInstance'):
        scalar.owned_method_abi(image, ctx, pmethods[name].index, pw.type_definition, ('void', 1, False), [], 'globalBuffParam.factory')
    scalar.owned_method_abi(image, ctx, pmethods['GetValue'].index, pw.type_definition, (TYPE, 21, True), [], 'globalBuffParam.getter')
    pgetter = pointer.leaf(image, image.method_pointer_va(pmethods['GetValue']), ['488B4110', 'C3'])
    slots = {'constValue': 32}
    for name in ('constValue', 'idRef', 'paramSource', 'path'):
        kind, declared, reference = (21, VALUE, False) if name == 'constValue' else (14, 'string', True) if name == 'path' else (8, 'int', False)
        scalar.owned_method_abi(image, ctx, pmethods['set___'+name+'__'].index, pw.type_definition,
                               ('void', 1, False), [(declared, kind, reference)], 'globalBuffParam.setter')
        if name != 'constValue':
            rows = records['set___'+name+'__']['instructions']
            at = 4 if name == 'path' and bytes.fromhex(rows[3][1])[:1] == b'\x74' else 6
            slots[name] = bytes.fromhex(rows[at][1])[-1]
            scalar.parameter_setter(image, rows, name=name, slot=slots[name], width=4, label='globalBuffParam')
    occupied = [i for name, size in (('constValue', 16), ('idRef', 4), ('paramSource', 4), ('path', 8)) for i in range(slots[name], slots[name]+size)]
    need('disjoint-own-Param-fields', len(set(occupied)) == 32 and all(16 <= n < 128 for n in occupied))
    psource = parent_bodies['Deserialize']; ps = [param_program(psource['regions'], psource['pointer'], **option) for option in ({}, {'allocated': True}, {'null': True})]
    pcalls = _calls(ps[1]); need('same-Param-all-path-callees', all(pcalls[k] == v for path in ps for k, v in _calls(path).items()))
    for name in ('constValue', 'idRef', 'paramSource', 'path'):
        need('own-named-Param-setter.'+name, pcalls[name] == image.method_pointer_va(pmethods['set___'+name+'__']))
    need('own-Param-constructor', pcalls['constructor'] == image.method_pointer_va(pmethods['.ctor']))
    usage = derive_typed_usage_context(image, ps[0]['valueUsageSite']-base, label='globalBuffParam.constant')
    bound = bind_typed_read(image, usage, method_name='ReadValue', argument=VALUE, kind=21)
    constant_parameter, = md.parameters_for(pmethods['set___constValue__'])
    nominal = object_nominal(image, ctx, constant_parameter.type_index)
    read_argument = image.pe.bytes_at_va(bound['argumentPointer'], 16)
    setter_argument = bytes.fromhex(nominal['rawTypeHex'])
    need('same-ObjectPtr-constant-argument', read_argument[:8] == setter_argument[:8] and read_argument[10:12] == setter_argument[10:12])
    parameter_usage = None; factories = []
    for name in ('.ctor', 'CreateInstance'):
        body = parent_bodies[name]; program = param_factory_program(body['regions'], body['pointer'])
        actual = derive_typed_usage_context(image, program['allocationUsageSite']-base, label='globalBuffParam.Original')
        need('own-Param-allocation', actual['typeName'] == TYPE and program['barrierTarget'] == pcalls['barrier'])
        if parameter_usage is None:
            parameter_usage = actual
        need('same-Param-allocation-cell', actual['usageCellRva'] == parameter_usage['usageCellRva'])
        factories.append(dict(name=name, program=program, allocation=actual))
    scalar.allocation_bridge(image, ctx, dict(methods=records, ownedFieldSlots=slots, allocationContext=parameter_usage), 'globalBuffParam')
    constant_store = param_const_setter(parent_bodies['set___constValue__']['regions'], parent_bodies['set___constValue__']['pointer'])
    need('same-Param-constant-barrier', constant_store['barrierTarget'] == pcalls['barrier'])
    wrapper_allocation = derive_typed_usage_context(image, ps[1]['allocationUsageSite']-base, label='globalBuffParam.wrapper')
    need('own-Param-wrapper-allocation', (wrapper_allocation['tag'], wrapper_allocation['typeName']) == (1, pw.name))
    offsets = scalar.reader_offsets(image, 'globalBuffParam'); recorder = vector_recorder(image)
    header = recorder(pcalls['header']-base); primitive.object_header_source(image, header, offsets)
    integer = recorder(pcalls['integer']-base); scalar.integer_source(image, integer, offsets, 'globalBuffParam.integer')
    pooled = pooled_source_helper.validate_on_image(image, pcalls['pool'], pins)
    collector = _barrier(image, pcalls['barrier'])
    default_methods, omethods, osource = value_methods(image, ctx, ow, VALUE, 21)
    os = [object_program(osource['regions'], osource['pointer'], **option) for option in ({}, {'allocated': True}, {'null': True})]
    ocalls = _calls(os[1])
    need('same-ObjectPtr-all-path-callees', all(ocalls[k] == v for path in os for k, v in _calls(path).items()))
    need('same-child-helpers', all(ocalls[k] == pcalls[k] for k in ('header', 'integer', 'barrier', 'allocate')))
    obj_setter = omethods['set___obj__']
    scalar.owned_method_abi(image, ctx, obj_setter.index, ow.type_definition, ('void', 1, False), [(BUFF, 18, True)], 'globalBuffParam.objSetter')
    setter_at = image.method_pointer_va(obj_setter); raw = image.pe.bytes_at_va(setter_at, 12)
    need('exact-ObjectPtr-object-setter', raw[:8] == bytes.fromhex('4883c110488911e9')
         and setter_at+12+int.from_bytes(raw[8:], 'little', signed=True) == pcalls['barrier'] and setter_at == ocalls['obj'])
    uid = omethods['set___cachedUid__']
    scalar.owned_method_abi(image, ctx, uid.index, ow.type_definition, ('void', 1, False), [('uint', 9, False)], 'globalBuffParam.uidSetter')
    uid_store = pointer.leaf(image, image.method_pointer_va(uid), ['895118', 'C3'])
    object_allocation = derive_typed_usage_context(image, os[1]['allocationUsageSite']-base, label='globalBuffParam.ObjectWrapper')
    need('own-ObjectPtr-wrapper-allocation', (object_allocation['tag'], object_allocation['typeName']) == (1, ow.name))
    global_usage = derive_typed_usage_context(image, os[0]['referenceUsageSite']-base, label='globalBuffParam.GlobalReference')
    bind_typed_read(image, global_usage, method_name='ReadValue', argument=BUFF, kind=18, reference=True)
    reader = _reader(image, pins)
    need('same-actual-GlobalBuff-reference-reader', global_usage['methodSpec'][0] == reader['readerMethodDefinition']
         and ocalls['reference']-base == reader['sourceTargetRva'])
    bsource = pointer.owned(image, image.method_pointer_va(bmethods['Deserialize']))
    primitive.reader_abi(image, ctx, bmethods['Deserialize'], bw)
    bs = [global_program(bsource['regions'], bsource['pointer'], **option) for option in ({}, {'allocated': True}, {'null': True})]
    bcalls = _calls(bs[1])
    need('same-GlobalBuff-all-path-callees', all(bcalls[k] == v for path in bs for k, v in _calls(path).items()))
    need('same-GlobalBuff-header-and-barrier', all(bcalls[k] == pcalls[k] for k in ('header', 'barrier', 'allocate')))
    need('own-GlobalBuff-wrapper-constructor', bcalls['constructor'] == image.method_pointer_va(bmethods['.ctor']))
    buff_getter = pointer.leaf(image, image.method_pointer_va(bmethods['GetValue']), ['488B4110', 'C3'])
    scalar.owned_method_abi(image, ctx, bmethods['GetValue'].index, bw.type_definition, (BUFF, 18, True), [], 'globalBuffParam.GlobalGetter')
    pair = derive_pair(image, BUFF, bw.name); buff_adapter = derive_adapter(image, pins, pair, bw)
    # Ordinary class wrapper factories own the named original allocation and
    # constructor call; arbitrary GlobalBuff runtime fields remain unclaimed.
    from scripts.game_data.memorypack.buff_object_sources import factory_program
    buff_factories = []
    original_constructor = None
    from scripts.game_data.memorypack.buff_ptr_sources import _call
    for name in ('.ctor', 'CreateInstance'):
        method = bmethods[name]
        scalar.owned_method_abi(image, ctx, method.index, bw.type_definition, ('void', 1, False), [], 'globalBuffParam.GlobalFactory')
        body = pointer.owned(image, image.method_pointer_va(method)); actual_ctor = _call(body, 72)
        if original_constructor is None: original_constructor = actual_ctor
        need('same-GlobalBuff-original-constructor', actual_ctor == original_constructor)
        program = factory_program(body['regions'], body['pointer'], dict(barrier=pcalls['barrier'], allocate=pcalls['allocate'], originalConstructor=actual_ctor))
        original = derive_typed_usage_context(image, program['originalAllocationUsageSite']-base, label='globalBuffParam.GlobalOriginal')
        need('own-GlobalBuff-original-allocation', (original['tag'], original['typeName']) == (1, BUFF))
        buff_factories.append(dict(name=name, source=_packet(body), program=program, allocation=original))
    original_td = ctx.index.types[BUFF]
    ctors = [m for m in md.methods_for(original_td) if md.string(m.name_index) == '.ctor' and m.parameter_count == 0]
    need('one-GlobalBuff-original-constructor', len(ctors) == 1 and image.method_pointer_va(ctors[0]) == original_constructor)
    scalar.owned_method_abi(image, ctx, ctors[0].index, original_td.index, ('void', 1, False), [], 'globalBuffParam.GlobalOriginalCtor')
    object_pair = derive_pair(image, VALUE, ow.name)
    value_source = derive_value(image, pins, typed_request=usage, target=pcalls['value16'], pair=object_pair,
                                wrapper=ow, header=pcalls['header'], barrier=pcalls['barrier'])
    reference = _reference_join(image, pins, VALUE)
    need('same-Param-whole-reference-getter', reference['getterMethodDefinition'] == pmethods['GetValue'].index)
    # The finite parent site is discovered by its independently decoded typed
    # MethodSpec, then byte-replayed through its own named field setter.
    fw, = [w for w in derive_from_image(image).values() if w.wrapped_type == 'Beyond.Gameplay.Actions.FinishGlobalBuff']
    fm = pointer.methods(image, fw); fsource = pointer.owned(image, image.method_pointer_va(fm['Deserialize']))
    actual_sites = []
    for row in fsource['rows']:
        if bytes.fromhex(row['bytes'])[:3] != bytes.fromhex('488b15'): continue
        try:
            candidate = derive_typed_usage_context(image, int(row['va'], 16)-base, label='globalBuffParam.parent')
        except (ValueError, KeyError, TypeError, IndexError):
            continue
        if (candidate['tag'], candidate['methodName'], candidate['methodArguments']) == (6, 'ReadValue', [TYPE]):
            actual_sites.append(candidate)
    need('one-actual-FinishGlobalBuff-Param-request', len(actual_sites) == 1)
    parent_usage = actual_sites[0]
    bind_typed_read(image, parent_usage, method_name='ReadValue', argument=TYPE, kind=21, reference=True)
    fcall = parent_call_program(fsource['regions'], base+parent_usage['instructionRva'])
    need('same-parent-Param-reader', parent_usage['methodSpec'][0] == reader['readerMethodDefinition'] and fcall['targetVa']-base == reader['sourceTargetRva'])
    field = [m for m in fw.members if m.name.lstrip('_') == 'globalBuff']
    need('own-parent-declared-field', len(field) == 1 and field[0].declared_type == TYPE)
    setter = fm['set____globalBuff__'] if 'set____globalBuff__' in fm else fm['set___globalBuff__']
    need('own-parent-Param-setter', image.method_pointer_va(setter) == fcall['setterTargetVa'])
    scalar.owned_method_abi(image, ctx, setter.index, setter.declaring_type, ('void', 1, False), [(TYPE, 21, True)], 'globalBuffParam.ParentSetter')
    cap = dict(schema='endfield.levelscript-global-buff-param-capability.v1', typeName=TYPE, valueType=VALUE,
               memberCount=4, fieldOrder=['constValue', 'idRef', 'paramSource', 'path'], constantMemberCount=2,
               constantFieldOrder=['cachedUid', 'obj'], globalBuffType=BUFF, globalBuffMemberCount=0,
               constantManagedBytes=16, unserializedValueStorageRanges=[[12, 16]],
               uidWireKind='u32', pathEncoding='int32-pool-index', idRefWireKind='i32', paramSourceWireKind='i32',
               outerNullReference=True, constantNullDefaultsZero16=True, positiveGlobalBuffAdmitted=True,
               globalBuffNullReference=True, exactOwnNominalsProved=True,
               readerMethodDefinition=reader['readerMethodDefinition'], sourceTargetRva=reader['sourceTargetRva'],
               canonicalParamCallbackTargetRva=reference['adapter']['callbackBinding']['canonicalTargetRva'],
               valueReaderMethodDefinition=usage['methodSpec'][0], valueReaderTargetRva=pcalls['value16']-base,
               valueCallbackTargetRva=value_source['symbolRvas']['adapter'],
               canonicalGlobalCallbackTargetRva=buff_adapter['callbackBinding']['canonicalTargetRva'],
               actualParamAndValueAndGlobalCallbacksRequired=True, runtimeGlobalBuffResolutionProved=False,
               liveFormatterSelectionObserved=False, parentFieldAdmitted=False, wholeOwnerAdmitted=False)
    validate(cap); _publication_gate(image, pins)
    return json.loads(json.dumps(dict(schema=SCHEMA, status='validated-conditional-global-buff-Param', nativeInputs=pins,
        capabilities={CAPABILITY: cap}, proof=dict(nominal=nominal, referenceReader=reader, ParamReference=reference,
            ParamSource={name: _packet(body) for name, body in parent_bodies.items()}, ParamPrograms=ps,
            ParamFactories=factories, ParamSlots=slots, ParamGetter=pgetter, constantSetter=constant_store,
            ParamWrapperAllocation=wrapper_allocation, header=header, integer=integer, pooledPath=pooled, collector=collector,
            objectSource=_packet(osource), objectPrograms=os, objectMethods=default_methods, objectPair=object_pair,
            objectWrapperAllocation=object_allocation, objectReferenceUsage=global_usage,
            objectSetterBytes=raw.hex().upper(), objectUidSetter=uid_store, valueSource=value_source,
            globalSource=_packet(bsource), globalPrograms=bs, globalPair=pair, globalAdapter=buff_adapter,
            globalGetter=buff_getter, globalFactories=buff_factories,
            originalConstructorEffectsProved=False, originalConstructorNormalReturnRequired=True,
            actualParent=dict(typeName=fw.wrapped_type, wrapperName=fw.name, fieldName=field[0].name,
                              typedRequest=parent_usage, source=_packet(fsource), call=fcall)),
        parentFieldAdmitted=False, wholeOwnerAdmitted=False)))
