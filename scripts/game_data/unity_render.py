"""Read stored Endfield MeshFilter/MeshRenderer bodies through EOF.

The reviewed serialized layout is a prerequisite, not a native/rendering claim.
The final Enlighten stream is retained from raw bytes even when typed JSON
omits it. Resource selection and effective runtime rendering remain separate.
"""
from __future__ import annotations

import json
import struct

from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.unity_scene import _Reader


def layouts():
    contract = json.loads((CONTRACTS_DIR/'unity_render_layouts.json').read_bytes())
    if contract['schema'] != 'endfield.unity-render-layouts.v1' or contract['status'] != 'reviewed':
        raise ValueError('unsupported Unity renderer layout contract')
    return contract['layouts']


def read_render_object(kind: str, raw: bytes) -> dict:
    reader = _Reader(raw)
    out = dict(m_GameObject=reader.pointer('m_GameObject'))
    if kind == 'MeshFilter':
        out['m_Mesh'] = reader.pointer('m_Mesh')
    elif kind == 'MeshRenderer':
        out['m_Enabled'] = reader.boolean('m_Enabled')
        for name in ('CastShadows', 'ReceiveShadows', 'DynamicOccludee', 'StaticShadowCaster',
                     'RealtimeShadowCaster', 'SubMeshRenderMode', 'CharacterIndex', 'MotionVectors',
                     'LightProbeUsage', 'ReflectionProbeUsage', 'RayTracingMode', 'RayTraceProcedural',
                     'RenderFoliageOccluder'):
            out['m_'+name], = reader.unpack('B', 'm_'+name)
        reader.align()
        for name, fmt in (('PlatformSpecificCastShadows','I'), ('RenderingLayerMask','I'),
                          ('RendererPriority','i'), ('LightmapIndex','H'), ('LightmapIndexDynamic','H')):
            out['m_'+name], = reader.unpack(fmt, 'm_'+name)
        out['m_LightmapTilingOffset'] = reader.vector(4, 'm_LightmapTilingOffset')
        out['m_LightmapTilingOffsetDynamic'] = reader.vector(4, 'm_LightmapTilingOffsetDynamic')
        out['m_Materials'] = reader.pointers('m_Materials')
        first, count = reader.unpack('HH', 'm_StaticBatchInfo')
        out['m_StaticBatchInfo'] = dict(firstSubMesh=first, subMeshCount=count)
        for name in ('StaticBatchRoot', 'ProbeAnchor', 'LightProbeVolumeOverride', 'ShadowProxyMesh'):
            out['m_'+name] = reader.pointer('m_'+name)
        out['m_SortingLayerID'], out['m_SortingLayer'], out['m_SortingOrder'] = reader.unpack('Ihh', 'sorting')
        out['m_EnableCharacterOutline'] = reader.boolean('m_EnableCharacterOutline')
        out['m_EnablePerRendererLighting'] = reader.boolean('m_EnablePerRendererLighting')
        reader.align()
        out['m_PerRendererLightingOffset'] = reader.vector(3, 'm_PerRendererLightingOffset')
        out['m_PerRendererLightingAnchor'] = reader.pointer('m_PerRendererLightingAnchor')
        out['m_LightModeMask'], = reader.unpack('I', 'm_LightModeMask')
        out['m_RendererSortingFudge'], = reader.vector(1, 'm_RendererSortingFudge')
        reader.align()
        out['m_AdditionalVertexStreams'] = reader.pointer('m_AdditionalVertexStreams')
        out['m_EnlightenVertexStream'] = reader.pointer('m_EnlightenVertexStream')
    else:
        raise ValueError(f'unsupported stored render component: {kind}')
    reader.finish()
    return out


def check_typed(body: dict, document: dict, kind: str) -> None:
    """Compare every retained constructor field with independent raw decoding."""
    for name, value in body.items():
        # The dedicated constructor omits this field. Keep the independently
        # decoded tail; compare it too if a future exporter publishes it.
        if name == 'm_EnlightenVertexStream' and name not in document:
            continue
        typed = document[name]
        if name == 'm_Materials':
            typed = [(p['m_FileID'], p['m_PathID']) for p in typed]
        elif isinstance(value, tuple):
            if name in ('m_LightmapTilingOffset', 'm_LightmapTilingOffsetDynamic', 'm_PerRendererLightingOffset'):
                typed = tuple(struct.unpack('<f',struct.pack('<f',typed[axis]))[0] for axis in 'XYZW'[:len(value)])
            else:
                typed = (typed['m_FileID'], typed['m_PathID'])
        elif name == 'm_RendererSortingFudge':
            typed = struct.unpack('<f',struct.pack('<f',typed))[0]
        if typed != value:
            raise ValueError(f'{kind} raw {name} differs from typed JSON: expected={value!r}; actual={typed!r}')
