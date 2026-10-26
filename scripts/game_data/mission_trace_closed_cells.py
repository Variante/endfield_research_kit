"""Derive passive capture cells from typed generated setter prefixes.

The selected image is authenticated by the capture preparer. This proves storage
lanes only; installed-format source transfer has its own, stronger validators.
"""
from __future__ import annotations

import json
import re
import struct

from .contracts import CONTRACTS_DIR


def setter_cell(rows, *, slot: int, kind: str) -> dict:
    """Prove the uninterrupted nonnull path through its first typed store."""
    if len(rows) < 5:
        raise ValueError('closed capture cell: truncated setter prefix')
    if not 16 <= slot <= 127:
        raise ValueError('closed capture cell: wrapper reference outside disp8 bound')
    text = [r['text'] for r in rows]
    if text[:1] == ['sub rsp, 0x28']:
        load = re.fullmatch(r'mov (rax|rcx), \[rcx\+0x([0-9a-f]+)\]', text[1])
        if not load or int(load[2], 16) != slot or text[2] != f'test {load[1]}, {load[1]}':
            raise ValueError('closed capture cell: typed wrapper load/null test differs')
        register = load[1]
        index = 4
        null = re.fullmatch(r'j(e|ne) 0x([0-9a-f]+)', text[3])
        if not null:
            raise ValueError('closed capture cell: null branch missing')
        if null[1] == 'ne':
            if (len(rows) < 7 or not text[4].startswith('call 0x') or text[5] != 'int3'
                    or int(null[2], 16) != int(rows[6]['va'], 16)):
                raise ValueError('closed capture cell: nonnull target differs')
            index = 6
        elif int(null[2], 16) <= int(rows[index]['va'], 16):
            raise ValueError('closed capture cell: null path reaches the store')
    elif kind == 'string' and text[:3] == ['mov [rsp+0x10], rbx', 'push rdi', 'sub rsp, 0x20']:
        if len(rows) < 8:
            raise ValueError('closed capture cell: truncated reference setter prefix')
        if text[3:5] != [f'mov rbx, [rcx+0x{slot:x}]', 'test rbx, rbx']:
            raise ValueError('closed capture cell: saved reference receiver differs')
        null = re.fullmatch(r'je 0x([0-9a-f]+)', text[5])
        if not null or not re.fullmatch(r'cmp \[rip\+.*\], 0x0', text[6]):
            raise ValueError('closed capture cell: reference null/barrier prefix differs')
        register = 'rbx'
        index = 7
        if int(null[1], 16) <= int(rows[index]['va'], 16):
            raise ValueError('closed capture cell: reference null path reaches store')
    else:
        raise ValueError('closed capture cell: unsupported setter entry')
    lane = {'string': 'rdx', 'int': 'edx', 'bool': 'dl', 'float': 'xmm1'}.get(kind)
    opcode = 'movss' if kind == 'float' else 'mov'
    store = re.fullmatch(rf'{opcode} \[{register}\+0x([0-9a-f]+)\], {lane}', text[index])
    if lane is None or not store or not 16 <= int(store[1], 16) <= 127:
        raise ValueError('closed capture cell: unchanged typed parameter store differs')
    return {'offset': int(store[1], 16), 'prefix': rows[:index+1],
            'evidence':'typed wrapper instance load and uninterrupted nonnull setter store',
            'sourceTransferProved':False,'runtimeTypeObserved':False}


def layout(selected, wrapper: str) -> dict:
    """Cache proved cells only within the preparer's single opened image."""
    if not hasattr(selected, '_capture_closed_cells'):
        selected._capture_closed_cells = {}
    if wrapper in selected._capture_closed_cells:
        return selected._capture_closed_cells[wrapper]
    contract = json.loads((CONTRACTS_DIR / 'capture_closed_cells.json').read_bytes())
    if contract['schema'] != 'endfield.capture-closed-cell-claims.v1' or contract['status'] != 'reviewed':
        raise ValueError('closed capture cell: reviewed claims required')
    spec = contract['wrappers'].get(wrapper)
    if spec is None:
        raise ValueError('closed capture cell: unsupported concrete wrapper')
    instance = selected.field(wrapper + '::' + spec['instanceField'])
    if instance[:2] != (wrapper, spec['closedType']):
        raise ValueError('closed capture cell: closed instance type differs')
    if 'concreteReceiver' in spec and selected.parent(spec['concreteReceiver']) != spec['closedType']:
        raise ValueError('closed capture cell: concrete receiver ancestry differs')
    metadata = selected.image.metadata
    td = selected.index.types[spec['genericDefinition']]
    section = metadata.sections['genericContainers']
    at = section.offset + td.generic_container_index * 16
    if td.generic_container_index < 0 or not section.offset <= at <= section.offset + section.size - 16:
        raise ValueError('closed capture cell: generic container bounds differ')
    owner, count, is_method, start = struct.unpack_from('<iiii', metadata.buf, at)
    if (owner, count, is_method) != (td.index, len(spec['arguments']), 0) or start < 0:
        raise ValueError('closed capture cell: owned generic arguments differ')
    declared = {metadata.string(f.name_index): f for f in metadata.fields_for(td)
                if not selected.field_attributes(f.type_index) & 0x10}
    result = {'wrapper': wrapper, 'instanceField': list(instance), 'fields': {},
              'boundary': contract['evidenceBoundary']['direct']}
    wrapper_td = selected.index.types[wrapper]
    for name, field in spec['fields'].items():
        actual = declared.get(name)
        expected = f'VAR[{start+field["argument"]}]' if 'argument' in field else field['type']
        typ = spec['arguments'][field['argument']] if 'argument' in field else field['type']
        if actual is None or selected.type_name(actual.type_index) != expected:
            raise ValueError('closed capture cell: declared field/VAR owner differs: ' + name)
        methods = [m for m in metadata.methods_for(wrapper_td)
                   if metadata.string(m.name_index) == 'set___' + name + '__']
        if len(methods) != 1:
            raise ValueError('closed capture cell: unique named setter required: ' + name)
        method = methods[0]
        params = list(metadata.parameters_for(method))
        if (method.flags & 0x10 or len(params) != 1 or selected.type_name(params[0].type_index) != typ
                or selected.type_name(method.return_type) != 'void'):
            raise ValueError('closed capture cell: typed instance setter signature differs: ' + name)
        kind = typ
        if selected.is_enum(typ):
            kind = selected.field(typ + '::value__')[1]
        pointer = selected.image.method_pointer_va(method)
        if not pointer:
            raise ValueError('closed capture cell: named setter pointer absent')
        raw = selected.image.pe.bytes_at_va(pointer, 128)
        rows = selected.image.mapper.decode_x64_subset(raw, pointer, stop_offset=len(raw))
        proof = setter_cell(rows, slot=instance[2], kind=kind)
        result['fields'][name] = {'type': typ, 'methodIndex': method.index,
                                  'setterRva': pointer - selected.image.pe.image_base, **proof}
    widths = {'string': 8, 'int': 4, 'bool': 1, 'float': 4}
    spans = sorted((r['offset'], r['offset'] + widths.get(r['type'], 4))
                   for r in result['fields'].values())
    if any(a[1] > b[0] for a, b in zip(spans, spans[1:])):
        raise ValueError('closed capture cell: overlapping typed destinations')
    selected._capture_closed_cells[wrapper] = result
    return result
