"""Authenticated manifest candidates for stored collision resource keys.

Full-key equality is retained as a candidate relation. Resource-map population
and actual asset selection require separate native/runtime evidence.

Evidence and admission boundary
-------------------------------
The plaintext manifest must match its current VFS row and native layout before
full-width numeric keys join authored path/Bundle candidates. This is an exact
numeric relation with ambiguous candidates preserved, not a proved resource
namespace or selected object. Selected Bundle main-asset PPtrs and complete
cooked Meshes need their independent gates. Names, preload membership and
##subasset suffixes never choose a Mesh. Collision-only Meshes may have complete
cooked geometry, zero render vertices and no ordinary MeshCollider in the Bundle;
Streaming ECS definitions are therefore another legitimate empty-OBJ source.
"""
from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

from scripts.game_data.bundle_manifest_native import audit_bundle_manifest_native
from scripts.game_data.dynamic_model_native import manifest_assets


def load_candidates(*, manifest: Path, ledger: Path, expected_input_set: str, game_root: Path):
    root=game_root.resolve()
    if root.name == 'Endfield_Data':root=root.parent
    rows=[]
    with gzip.open(ledger,'rt',encoding='utf-8') as stream:
        for line in stream:
            row=json.loads(line)
            if row.get('recordType') == 'file' and row.get('fileName') == 'Data/Bundles/Windows/manifest.hgmmap':rows.append(row)
    if len(rows) != 1:raise ValueError(f'collision-manifest: expected one selected manifest row, actual={len(rows)}')
    source=rows[0]
    if (source.get('status') != 'verified' or source.get('boundaryStatus') != 'boundary_verified'
            or source.get('inputSetSha256','').upper() != expected_input_set.upper()):
        raise ValueError('collision-manifest: unverified/stale manifest source')
    raw=manifest.read_bytes();md5=hashlib.md5(raw,usedforsecurity=False).hexdigest().upper()
    if len(raw) != source['length'] or md5 != source['recomputedFileDataMd5'].upper():
        raise ValueError(f"collision-manifest: plaintext length/MD5: expected={source['length']}/{source['recomputedFileDataMd5']}, actual={len(raw)}/{md5}")
    native=audit_bundle_manifest_native(manifest=manifest,gameassembly=root/'GameAssembly.dll',metadata=root/'Endfield_Data/il2cpp_data/Metadata/global-metadata.dat')
    if native['status'] != 'validated':raise ValueError(f"collision-manifest: native gate={native['status']}, detail={native.get('detail')}")
    candidates=manifest_assets(raw)
    if manifest.read_bytes() != raw:raise ValueError('collision-manifest: plaintext changed during decode')
    audit=dict(status='validated-candidate-index',manifestPath=str(manifest.resolve()),manifestSha256=hashlib.sha256(raw).hexdigest().upper(),
               source={key:source[key] for key in ('fileName','physicalChunkPath','physicalChunkSource','offset','length','recomputedFileDataMd5','inputSetSha256')},
               nativeGate=native,keys=len(candidates),
               evidenceBoundary='structuralOnly: exact full64 equality to native-validated manifest AssetInfo keys; resource namespace/load selection and Unity object ownership require separate proof')
    return candidates,audit


def join_candidates(meshes, candidates):
    """Do not collapse collisions, choose one path or infer a Unity PPtr."""
    for mesh in meshes:
        rows=candidates.get(int(mesh['resourceKey64Hex'],16),[])
        mesh['manifestCandidates']=[dict(row) for row in rows]
        mesh['manifestCandidateStatus']='unique-full64-key-candidate' if len(rows)==1 else 'ambiguous-full64-key-candidates' if rows else 'unmatched-full64-key'
