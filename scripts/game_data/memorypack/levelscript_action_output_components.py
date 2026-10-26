"""Finite independently typed ParamOutput children and parent bindings.

ParamOutput serializes only target and pooled path. Its T argument is a runtime
output type; it contributes no stored T value or constant wire grammar. Old
existing-holder source alone is insufficient for a fresh canonical callback.
Every selected child must prove both factories and all four reader paths.
"""
import hashlib
import json
import struct

SCHEMA = 'endfield.levelscript-action-output-components.v1'
CAP_PREFIX = 'story-actionmap-param-output:'
PREFIX = 'Beyond.Gameplay.Actions.ParamOutput`1<'
DEFINITION = PREFIX[:-1]
WIRE = 'actionmap-param-output'


def need(check, condition):
    if not condition:
        raise ValueError('actionOutput.'+check)


def _packets(image, wrapper):
    from scripts.game_data.il2cpp.closed_leaf_entry import decode_closed_leaf_entry
    from scripts.game_data.memorypack.pointer_param import owned, methods
    result = {}; base = image.pe.image_base
    for name, method in methods(image, wrapper).items():
        if name not in ('.ctor', 'CreateInstance', 'GetValue', 'Deserialize'):
            continue
        row = dict(methodIndex=method.index, methodName=name)
        result[name] = row
        try:
            target = image.method_pointer_va(method); row['entryRva'] = target-base
            try:
                packet = owned(image, target)
            except (KeyError, ValueError):
                leaf = decode_closed_leaf_entry(image.mapper, image.pe.bytes_at_va(target, 512), target)
                rows = leaf['rows']; end = max(int(r['va'], 16)+len(bytes.fromhex(r['bytes'])) for r in rows)
                raw = image.pe.bytes_at_va(target, end-target)
                packet = dict(pointer=target, rows=rows, regions=[(target, raw)], windows=[dict(
                    startRva=target-base, endRva=end-base, sha256=hashlib.sha256(raw).hexdigest().upper())])
            row.update(packet=dict(entryVa=packet['pointer'], sourceWindows=packet['windows'],
                sourceRegions=[(a, raw.hex().upper()) for a, raw in packet['regions']], rows=packet['rows']),
                effectsProved=False)
        except (ValueError, KeyError, IndexError, TypeError) as error:
            row['pending'] = str(error)[:1500]
    return result


def _carrier(image, ctx, getter, type_name):
    from scripts.game_data.il2cpp.context import type_parameter_owner
    from scripts.game_data.il2cpp.reference_layouts import closed_generic_reference_extent
    carrier = closed_generic_reference_extent(ctx, getter.return_type)
    need('own-closed-ParamOutput-carrier', carrier['type'] == type_name and carrier['bytes'] == 8
         and len(carrier['argumentTypes']) == 1 and carrier['definitionTypeIndex'] == ctx.index.types[DEFINITION].index)
    td = ctx.index.types[DEFINITION]; md = image.metadata
    section = md.sections['genericContainers']; at = section.offset+td.generic_container_index*16
    need('owned-container-bounds', section.offset <= at <= section.offset+section.size-16)
    owner, count, is_method, parameter = struct.unpack_from('<iiii', md.buf, at)
    identity = type_parameter_owner(md.buf, parameter, [t.generic_container_index for t in md.types], source='actionOutput')
    need('reciprocal-ParamOutput-class-parameter', (owner, count, is_method) == (td.index, 1, 0)
         and (identity['typeIndex'], identity['ordinal']) == (td.index, 0))
    return dict(carrier, classParameter=identity)


def derive_many(image, pins, *, parameter_types):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import output_param, pointer_param as pointer
    from scripts.game_data.memorypack.levelscript_condition_param_sources import _reader
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.wrapper_members import derive_from_image
    from scripts.game_data.memorypack.levelscript_action_output_sources import derive as derive_source
    from scripts.game_data.codecs.levelscript.current_action_output_param import validate
    need('explicit-finite-distinct-output-selection', isinstance(parameter_types, (list, tuple))
         and 0 < len(parameter_types) <= 128 and len(set(parameter_types)) == len(parameter_types)
         and all(type(name) is str and name.startswith(PREFIX) and name.endswith('>') for name in parameter_types))
    _publication_gate(image, pins); ctx = NativeReferenceContext(image); reader = _reader(image, pins)
    wrappers = derive_from_image(image); owners = []; capabilities = {}
    for name in parameter_types:
        result = dict(typeName=name, status='pendingReview', proof={}, parentFieldAdmitted=False, wholeOwnerAdmitted=False)
        owners.append(result)
        try:
            selected = [w for w in wrappers.values() if w.wrapped_type == name]
            need('one-actual-closed-output-wrapper', len(selected) == 1); wrapper = selected[0]
            result['wrapperName'] = wrapper.name
            need('only-target-and-path-serialized', [(m.name, m.declared_type) for m in wrapper.members] == [('paramTarget', 'int'), ('path', 'string')])
            result['proof']['packets'] = _packets(image, wrapper)
            getter = pointer.methods(image, wrapper)['GetValue']
            carrier = _carrier(image, ctx, getter, name); result['valueType'] = carrier['argumentTypes'][0]
            result['proof']['closedCarrier'] = carrier
            existing = output_param.derive_output(image, pins, name)
            result['proof']['existingHolderSource'] = existing
            pair = derive_pair(image, name, wrapper.name)
            adapter = derive_adapter(image, pins, pair, wrapper)
            result['proof'].update(pair=pair, adapter=adapter)
            result.update(selectedExistingHolderSourceProved=True, canonicalReferenceAdapterProved=True)
            source = derive_source(image, pins, wrapper=wrapper, packets=result['proof']['packets'], existing=existing)
            result['proof']['fullSource'] = source
            output_type = carrier['argumentTypes'][0]
            cap = dict(schema='endfield.levelscript-action-output-capability.v1', typeName=name, outputType=output_type,
                memberCount=2, fieldOrder=['paramTarget', 'path'], paramTargetWireKind='i32', pathEncoding='int32-pool-index',
                nullWireBytes=1, positiveWireBytes=9, sourceReferenceKind=21, referenceOutputBytes=8,
                closedCarrierProved=True, typeArgumentSerialized=False, nullAdmitted=True, positiveAdmitted=True,
                fourPathWrapperSourceProved=True, factoryAndOriginalHolderProved=True,
                actualCallbackEqualsProvedOutputRequired=True, liveFormatterSelectionObserved=False,
                runtimeOutputWritebackProved=False, parentFieldAdmitted=False, wholeOwnerAdmitted=False,
                readerMethodDefinition=reader['readerMethodDefinition'], sourceTargetRva=reader['sourceTargetRva'],
                canonicalCallbackTargetRva=adapter['callbackBinding']['canonicalTargetRva'])
            validate(cap); capabilities[CAP_PREFIX+name] = cap
            result.update(status='validated-conditional-output-child', capability=cap, outputType=output_type)
        except (ValueError, KeyError, IndexError, TypeError) as error:
            result['reason'] = str(error)[:2400]
    _publication_gate(image, pins)
    return json.loads(json.dumps(dict(schema=SCHEMA, nativeInputs=pins, referenceReader=reader,
        owners=owners, capabilities=capabilities, parentFieldAdmitted=False, wholeOwnerAdmitted=False,
        evidenceBoundary='Exact closed Output reference carrier and reciprocal class parameter, canonical reference adapter, both typed Original factories, four MC2/FF reader paths and complete selected frames. Only target and pooled path are serialized; selected callback, initialized metadata, zero-initialized successful typed allocation and disabled collector remain conditions. No T value grammar, writeback, enclosing field or owner grant.')))


from scripts.game_data.memorypack.levelscript_action_output_bindings import derive_binding, bind_reference
