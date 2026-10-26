"""Read the Endfield player AssetBundle container/preload prefix.

The dedicated AnimeStudio reader documents this prefix. Remaining bytes are
retained as an opaque tail; container membership is not preload ownership.


Evidence and admission boundary
-------------------------------
Exact prefix framing bounds preload spans and retains unrelated tail bytes
opaquely. A container's actual GameObject PPtr can label a checked hierarchy
root; preload adjacency cannot. Raw/JSON prefix agreement proves stored prefab
membership, not live loading, placement or ownership of every dependency.
"""
from __future__ import annotations

import hashlib

from scripts.game_data.unity_scene import _Reader


def read_container_prefix(data: bytes) -> dict:
    reader = _Reader(data)

    def string(label: str) -> str:
        length, = reader.unpack('i', label+'.length')
        result = reader.take(length, label).decode('utf-8', errors='strict')
        reader.align()
        return result

    name = string('m_Name'); flags, = reader.unpack('i', 'm_PathFlags')
    preload = reader.pointers('m_PreloadTable')
    count, = reader.unpack('i', 'm_Container.count')
    if not 0 <= count <= (len(data)-reader.offset)//24:
        raise ValueError('AssetBundle m_Container count cannot fit remaining bytes')
    containers = []
    for index in range(count):
        path = string(f'm_Container[{index}].path')
        start, size = reader.unpack('ii', f'm_Container[{index}].preload')
        pointer = reader.pointer(f'm_Container[{index}].asset')
        if start < 0 or size < 0 or start+size > len(preload):
            raise ValueError(f'AssetBundle m_Container[{index}] preload span outside table')
        containers.append(dict(path=path, preloadIndex=start, preloadSize=size, asset=pointer))
    tail = data[reader.offset:]
    return dict(name=name, pathFlags=flags, preload=preload, containers=containers,
                consumedPrefixBytes=reader.offset, opaqueTailBytes=len(tail),
                opaqueTailSha256=hashlib.sha256(tail).hexdigest())
