"""Selected-build witnesses for state Param cells and two-lane event values.

No open generic offset is used. Param cells come from authenticated concrete
setter programs; EventData layout is independently derived from its selected
sequential declaration and checked against the complete native callback.
"""
from __future__ import annotations
import json
import hashlib
import re
import struct
from .contracts import CONTRACTS_DIR


def state_index(selected):
    if not hasattr(selected, '_state_index'):
        from .mission_shared_native import OwnedBodyIndex
        selected._state_index = OwnedBodyIndex(selected.image)
        for key in ('types', 'names_by_pointer', 'extents', 'chained_fragments'):
            if key in selected.index.__dict__:
                selected._state_index.__dict__[key] = selected.index.__dict__[key]
    return selected._state_index


def param_layout(selected, wrapper: str) -> dict:
    if not hasattr(selected, '_state_param_layouts'):
        from .mission_expression_native import evaluate
        proof = evaluate(image=selected.image, index=state_index(selected))
        if proof['status'] != 'validated':
            raise ValueError(f"state Param witness: {proof['status']}: {proof.get('diagnostics', [])[:1]}")
        raw = (CONTRACTS_DIR / 'mission_expression_native.json').read_bytes()
        # This joins a generated evaluation to the bytes it evaluated. There is
        # no recorded/pinned digest of a tracked contract in this consumer.
        if hashlib.sha256(raw).hexdigest().upper() != proof['contract']['sha256']:
            raise ValueError('state Param witness: reviewed declaration changed during validation')
        contract = json.loads(raw)
        selected._state_param_layouts = {row['wrapper']: row for row in contract['wrapperFields']}
        selected._state_param_proof = {'status': proof['status'], 'nativeGate': proof['nativeGate'],
                                      'nativeGateAfter': proof['nativeGateAfter']}
    row = selected._state_param_layouts.get(wrapper)
    if row is None:
        raise ValueError('state Param witness: unsupported concrete wrapper')
    return row


def param_field(selected, qualified: str, wrapper: str, current_type: str):
    row = param_layout(selected, wrapper)
    owner, separator, name = qualified.partition('::')
    if not separator or owner != current_type or owner != row['instanceField'][1]:
        raise ValueError('state Param witness: typed receiver or field owner differs')
    field_types = {'constValue': row['argument'], 'idRef': 'int', 'paramSource': 'int', 'path': 'string'}
    if name not in field_types:
        raise ValueError('state Param witness: unsupported cell')
    return (owner, field_types[name], row[name+'Offset'],
            {'wrapper': wrapper, 'closedType': owner, 'field': name, 'fieldType': field_types[name],
             'offset': row[name+'Offset'], 'evidence': row['boundary'], 'runtimeTypeObserved': False})


def event_layout(selected, name: str) -> dict:
    match = re.fullmatch(r'Beyond.EventData`2<string,(Beyond.Gameplay.MissionSystem\+(?:QuestState|MissionState))>', name)
    td = selected.index.types.get('Beyond.EventData`2')
    if (not match or td is None or selected.parent(name) != 'System.ValueType'
            or td.flags & 0x18 != 8 or td.bitfield & 0xc00 != 0xc00 or td.field_count != 2):
        raise ValueError('state EventData witness: sequential two-field default-size value required')
    section = selected.image.metadata.sections['genericContainers']
    at = section.offset + td.generic_container_index * 16
    if td.generic_container_index < 0 or not section.offset <= at <= section.offset + section.size - 16:
        raise ValueError('state EventData witness: generic container outside metadata')
    owner, count, method, parameter = struct.unpack_from('<iiii', selected.image.metadata.buf, at)
    fields = list(selected.image.metadata.fields_for(td))
    if (owner != td.index or count != 2 or method != 0 or parameter < 0
            or [selected.type_name(f.type_index) for f in fields] != [f'VAR[{parameter}]', f'VAR[{parameter+1}]']
            or any(selected.field_attributes(f.type_index) & 0x10 for f in fields)
            or selected.field(match[1]+'::value__')[1] != 'int'):
        raise ValueError('state EventData witness: declaration or enum storage drift')
    return {'closedType': name, 'unboxedBytes': 16,
            'fields': {selected.image.metadata.string(f.name_index): {'type': t, 'offset': off}
                       for f, t, off in zip(fields, ['string', match[1]], [0, 8])},
            'evidence': 'selected sequential default-layout string/Int32 enum fields; Win64 alignment, not open offsets'}


def event_argument_proof(selected, hook, arg):
    if arg != 1:
        raise ValueError('state EventData witness: expected instance callback argument RDX')
    from .il2cpp.mission_condition_flow import prove_state_callback
    index = state_index(selected)
    body = index.body(hook['type'], hook['method'])
    proof = prove_state_callback(index, body)
    return {'status': 'validated', 'mode': 'indirectValue', 'completeCallback': proof,
            'evidence': 'complete callback proof retains incoming RDX pointer and reads raw lanes zero/eight'}
