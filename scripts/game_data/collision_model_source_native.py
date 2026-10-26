"""Selected Model framing for Collision capture filters, without asset joins.

This narrower contract does not authenticate the other DynamicStreaming fields
or replace the full Model/manifest corpus gates.
"""
from __future__ import annotations

import hashlib
import struct

from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.dynamic_streaming import _bounded_vector, _field_span, _root_layout, _table_layout
from scripts.game_data.il2cpp.native_image import read_reviewed_contract

CONTRACT = CONTRACTS_DIR / "collision_model_source_native.json"
SCHEMA = "endfield.collision-model-source-native.v1"


def load(image, inputs):
    contract, _ = read_reviewed_contract(CONTRACT, schema=SCHEMA, label="collision-model-source", status="reviewed")
    if {k: v.lower() for k, v in contract['nativeInputs'].items()} != {k: v.lower() for k, v in inputs.items()}:
        raise ValueError('collision-model-source: selected native inputs differ')
    if [row['method'] for row in contract['methods']] != ['Grids', 'get_UniqueId', 'Model', 'StartModelVector', 'get_PathHash']:
        raise ValueError('collision-model-source: named source programme coverage differs')
    for row in contract['methods']:
        image.validate_method_row([row['index'], row['type'], row['method'], row['rva']], label='collision-model-source')
        for window in row['windows']:
            if not 0 < window['bytes'] <= 4096:
                raise ValueError('collision-model-source: unbounded native window')
            raw = image.pe.bytes_at_va(image.pe.image_base + window['rva'], window['bytes'])
            if hashlib.sha256(raw).hexdigest().lower() != window['sha256'].lower():
                raise ValueError('collision-model-source: native window differs: ' + row['method'])
        for probe in row['probes']:
            expected = bytes.fromhex(probe['bytes'])
            address = row['rva'] + probe['offset']
            covered = any(w['rva'] <= address and address + len(expected) <= w['rva'] + w['bytes'] for w in row['windows'])
            if not expected or not covered or image.pe.bytes_at_va(image.pe.image_base + address, len(expected)) != expected:
                raise ValueError('collision-model-source: source framing witness differs: ' + row['method'])
    layout = contract['layout']
    if not (type(layout['modelWidth']) is int and 8 <= layout['modelWidth'] <= 4096 and
            type(layout['pathHashOffset']) is int and 0 <= layout['pathHashOffset'] <= layout['modelWidth'] - 8 and
            all(type(layout[k]) is int and 0 <= layout[k] < 256 for k in ('rootGridField', 'gridIdField', 'gridModelField'))):
        raise ValueError('collision-model-source: unsafe selected layout')
    return layout


def selected_models(raw: bytes, layout: dict, *, source: str, path_hash: str) -> list[dict]:
    """Frame only the reviewed vectors; all other stored fields stay opaque."""
    wanted = int(path_hash, 16)
    root = _root_layout(raw)
    grids, count, _ = _bounded_vector(raw, root, layout['rootGridField'], 4)
    result = []
    for grid in range(count):
        slot = grids + grid * 4
        relative = struct.unpack_from('<I', raw, slot)[0]
        if not relative:
            raise ValueError('collision-model-source: invalid grid table reference')
        table = _table_layout(raw, slot + relative)
        identity = _field_span(raw, table, layout['gridIdField'], 4)
        start, length, _ = _bounded_vector(raw, table, layout['gridModelField'], layout['modelWidth'])
        for ordinal in range(length):
            at = start + ordinal * layout['modelWidth']
            if struct.unpack_from('<Q', raw, at + layout['pathHashOffset'])[0] != wanted:
                continue
            result.append(dict(
                source=source,
                gridOrdinal=grid,
                uniqueId=struct.unpack_from('<I', raw, identity)[0] if identity is not None else 0,
                ordinal=ordinal,
                byteOffset=at,
                pathHashHex=f'{wanted:016X}',
            ))
    return result
