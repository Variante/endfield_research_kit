"""Finite current ActionMap child observations, with no grammar admission.

Own native declarations, complete method packets and exact candidate request
sites are retained to prepare the separately typed Param reference array and
ObjectPtr<GlobalBuff> owners. A packet or successful observation is not a
source-program proof, callback identity, parent binding or payload authority.
"""
import json

TYPES = (
    'Beyond.Gameplay.Actions.ListMakeEntityPtr',
    'Beyond.Gameplay.Actions.FinishGlobalBuff',
    'Beyond.Gameplay.Actions.Param`1<Beyond.ObjectPtr`1<Beyond.Gameplay.Core.GlobalBuff>>',
    'Beyond.ObjectPtr`1<Beyond.Gameplay.Core.GlobalBuff>',
    'Beyond.Gameplay.Core.GlobalBuff',
)


def derive(image, pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.closed_leaf_entry import decode_closed_leaf_entry
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.memorypack.pointer_param import owned
    _publication_gate(image, pins)
    base = image.pe.image_base
    ctx = NativeReferenceContext(image)
    md = image.metadata
    wrappers = image.memorypack_wrappers
    owners = []
    for type_name in TYPES:
        selected = [w for w in wrappers.values() if w.wrapped_type == type_name]
        owner = dict(typeName=type_name, wrapperCount=len(selected), methods={}, holds=[],
                     sourceProgramProved=False, childGrammarAdmitted=False, parentFieldAdmitted=False)
        owners.append(owner)
        if len(selected) != 1:
            owner['holds'].append('exactly-one-current-generated-wrapper')
            continue
        wrapper = selected[0]
        owner.update(wrapperName=wrapper.name, wrapperTypeDefinition=wrapper.type_definition,
                     members=[dict(name=m.name, declaredType=m.declared_type, declaringWrapper=m.declaring_wrapper,
                                   kind=m.kind) for m in wrapper.members])
        for method in md.methods_for(md.types[wrapper.type_definition]):
            name = md.string(method.name_index)
            if name not in ('Deserialize', '.ctor', 'CreateInstance', 'GetValue') and not name.startswith('set___'):
                continue
            key = name + ':' + str(method.index)
            record = dict(methodIndex=method.index, owner=wrapper.name, methodName=name,
                          returnType=ctx.type_name(method.return_type),
                          parameterTypes=[ctx.type_name(p.type_index) for p in md.parameters_for(method)])
            owner['methods'][key] = record
            try:
                pointer = image.method_pointer_va(method)
                record['entryRva'] = pointer - base
                try:
                    packet = owned(image, pointer)
                except (ValueError, KeyError):
                    leaf = decode_closed_leaf_entry(image.mapper, image.pe.bytes_at_va(pointer, 512), pointer)
                    rows = leaf['rows']
                    end = max(int(r['va'], 16) + len(bytes.fromhex(r['bytes'])) for r in rows)
                    raw = image.pe.bytes_at_va(pointer, end - pointer)
                    import hashlib
                    packet = dict(pointer=pointer, regions=[(pointer, raw)], rows=rows,
                                  windows=[dict(startRva=pointer-base, endRva=end-base,
                                                sha256=hashlib.sha256(raw).hexdigest().upper())],
                                  boundary='complete selected leaf; no semantic effects inferred')
                record['packet'] = dict(packet, regions=[[at, raw.hex().upper()] for at, raw in packet['regions']])
                usages = []
                calls = []
                for row in packet['rows']:
                    at = int(row['va'], 16)
                    raw = bytes.fromhex(row['bytes'])
                    if len(raw) == 5 and raw[0] == 0xe8:
                        calls.append(dict(instruction=[at-base, raw.hex().upper()], targetRva=control_transfer(row)['target']-base))
                    if len(raw) != 7 or raw[:3] not in (b'\x48\x8b\x15', b'\x4c\x8b\x05', b'\x48\x8b\x0d'):
                        continue
                    try:
                        usage = derive_typed_usage_context(image, at-base, label='actionMapChildObservation')
                    except (ValueError, KeyError, IndexError, TypeError) as error:
                        usages.append(dict(instruction=[at-base, raw.hex().upper()], unresolved=True,
                                           reason=str(error)[:500]))
                    else:
                        usages.append(dict(typedRequest=usage, requestOnly=True, noCallOrFieldBindingProved=True))
                record.update(directCalls=calls, candidateTypedRequests=usages)
            except (ValueError, KeyError, IndexError, TypeError) as error:
                record['hold'] = str(error)[:1000]
    _publication_gate(image, pins)
    return json.loads(json.dumps(dict(schema='endfield.levelscript-actionmap-child-observations.v1',
        status='current-native-observations-only', nativeInputs=pins, owners=owners,
        sourceProgramProved=False, childGrammarAdmitted=False, parentFieldAdmitted=False,
        wholeOwnerAdmitted=False, runtimeSelectionObserved=False)))
