"""Join manifest candidates to fresh Bundle main-asset Mesh PPtrs.

This proves the stored container relation in selected physical Bundles. A
manifest ##subasset suffix and actual native resource-map selection remain
separate; no name match chooses a Mesh or a live collider.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import json
from pathlib import Path

from scripts.common import sha256_file_upper
from scripts.game_data.cooked_collision_corpus import _selected_ledger, inspect_exports
from scripts.game_data.corpus_common import atomic_write_text
from scripts.game_data.streaming.corpus import snapshot_outer_fingerprints
from scripts.game_data.unity_scene import scene_identity
from scripts.game_data.unity_scene_corpus import audit_selection
from scripts.repo_paths import REPO_ROOT


def bind_candidates(candidates, scene, meshes, logical_files):
    """Only exact physical identity and a local container asset PPtr bind."""
    index=defaultdict(list); source={scene_identity(r['identity']):r for r in scene['rawSources']}
    geometry={scene_identity(r['identity']):r for r in meshes['objects']}
    for bundle in scene['assetBundlePrefixes']:
        owner=scene_identity(bundle['source']['identity'])
        logical=logical_files.get(owner[:2])
        if logical is None:raise ValueError('collision mesh: Bundle has no authenticated logical file')
        for entry in bundle['prefix']['containers']:
            file_id,path_id=entry['asset'];target=(*owner[:3],path_id&0xffffffffffffffff)
            if file_id != 0 or path_id == 0:continue
            obj=source.get(target)
            if obj is None or obj['type'] != 'Mesh':continue
            mesh=geometry.get(target)
            if mesh is None or mesh['status'] == 'failed':continue
            index[logical['fileName'],entry['path']].append(dict(
                containerAsset=entry['asset'],assetBundleIdentity=bundle['source']['identity'],
                meshIdentity=mesh['identity'],meshRawSha256=mesh['rawSha256'],name=mesh['name'],
                renderVertexCount=mesh['renderVertexCount'],collisionOnly=mesh['collisionOnly'],
                baked=mesh['baked'],convex=mesh['convex'],geometryStatus=mesh['status'],geometry=mesh['payloads']))
    result={}
    for key,paths in candidates.items():
        rows=[]
        for candidate in paths:
            base,separator,subasset=candidate['path'].partition('##')
            for target in index.get((candidate['bundle'],base),[]):
                rows.append(dict(manifestCandidate=candidate,containerPath=base,requestedSubasset=subasset if separator else None,
                    subassetSelectionStatus='unresolved-native-subasset-selection' if separator else 'container-main-asset',
                    storedContainerBinding=target,
                    evidenceBoundary='direct stored container main-asset PPtr; full64 manifest equality and resource/subasset selection remain conditional candidates; no live actor ownership'))
        if rows:result[key]=rows
    return result


def audit(*, collision_receipt: Path, scene_receipt: Path, output: Path, game_root: Path):
    receipt=json.loads(collision_receipt.read_bytes())
    if (receipt.get('schema') != 'endfield.streaming-collision-corpus.v2' or receipt.get('status') != 'validated'
            or receipt.get('diagnostics') or not receipt.get('publicationEligible') or not receipt.get('manifestCandidateGate')):
        raise ValueError('collision mesh: validated collision projection with manifest candidates required')
    provenance=receipt['provenance'];rows_path=Path(receipt['rows']['path'])
    inputs=[collision_receipt,scene_receipt,rows_path,Path(provenance['rootReport']),Path(provenance['outerSummary']),Path(provenance['ledger']),Path(__file__)]
    hashes={str(p.resolve()):sha256_file_upper(p) for p in inputs}
    if hashes[str(rows_path.resolve())] != receipt['rows']['sha256']:raise ValueError('collision mesh: projection rows SHA256 mismatch')
    for key,path in (('rootReport',Path(provenance['rootReport'])),('outerSummary',Path(provenance['outerSummary'])),('ledger',Path(provenance['ledger']))):
        if sha256_file_upper(path) != provenance['authenticatedInputs'][key]:raise ValueError('collision mesh: authenticated input changed:'+key)
    outer=json.loads(Path(provenance['outerSummary']).read_bytes());failures=[]
    install=game_root.resolve()
    if install.name == 'Endfield_Data':install=install.parent
    native_paths=dict(gameAssemblySha256=install/'GameAssembly.dll',metadataSha256=install/'Endfield_Data/il2cpp_data/Metadata/global-metadata.dat',unityPlayerSha256=install/'UnityPlayer.dll')
    native_hashes={name:sha256_file_upper(path).lower() for name,path in native_paths.items()}
    if native_hashes != provenance['nativeInputHashes']:raise ValueError('collision mesh: selected native inputs differ from projection')
    if outer['inputSetSha256'] != receipt['inputSetSha256']:raise ValueError('collision mesh: current VFS input set differs')
    snapshot_outer_fingerprints(outer,failures,'candidate-start')
    if failures:raise ValueError('collision mesh: current audit fingerprints differ:'+json.dumps(failures[:2]))
    previous=json.loads(scene_receipt.read_bytes());selection=Path(previous['selection']['path'])
    scene_summary=Path(previous['provenance']['outerSummaryPath']);scene_ledger=Path(previous['provenance']['outerLedger'])
    if (scene_summary.resolve() != Path(provenance['outerSummary']).resolve()
            or scene_ledger.resolve() != Path(provenance['ledger']).resolve()):raise ValueError('collision mesh: scene and projection audits differ')
    # Preserve the original spelling for the scene receipt's strict provenance
    # comparison, after independently proving both spellings resolve identically.
    current=audit_selection(selection_path=selection,summary_path=scene_summary,ledger_path=scene_ledger,
                            expected_input_set=receipt['inputSetSha256'],work_root=REPO_ROOT/'tmp/animestudio/streaming_mesh_candidates',reuse_path=scene_receipt)
    if current['status'] != 'complete':raise ValueError('collision mesh: fresh scene receipt failed:'+json.dumps(current['failures'][:2]))
    command=current['extraction']['command'];json_root=Path(command[2]);raw_root=Path(command[command.index('--secondary_export_path')+1])
    meshes=inspect_exports(json_root/'Mesh',raw_root/'Mesh')
    if meshes['status'] != 'complete':raise ValueError('collision mesh: complete Mesh decoding required')
    _,_,logical,_=_selected_ledger(Path(provenance['outerSummary']),Path(provenance['ledger']),json.loads(selection.read_bytes()),receipt['inputSetSha256'])
    candidates={};occurrences=Counter();examples=defaultdict(list); source_files=0
    with gzip.open(rows_path,'rt',encoding='utf-8') as stream:
        for line in stream:
            file=json.loads(line);source_files+=1
            for definition in file['rows']:
                for mesh in definition['meshInputs']:
                    key=mesh['resourceKey64Hex'];paths=mesh.get('manifestCandidates',[])
                    if key in candidates and candidates[key] != paths:raise ValueError('collision mesh: resource key candidates differ across source rows')
                    candidates[key]=paths;occurrences[key]+=1
                    if len(examples[key])<3:examples[key].append(dict(virtualPath=file['virtualPath'],outerRowIndex=definition['outerRowIndex'],bodySha256=definition['bodySha256'],meshSlot=mesh['meshSlot']))
    if source_files != receipt['rows']['files']:raise ValueError('collision mesh: source row file count differs')
    bindings=bind_candidates(candidates,current,meshes,logical)
    rows=[dict(resourceKey64Hex=key,sourceOccurrences=occurrences[key],sourceExamples=examples[key],bindings=bindings[key]) for key in sorted(bindings)]
    snapshot_outer_fingerprints(outer,failures,'candidate-end')
    if (failures or hashes != {str(p.resolve()):sha256_file_upper(p) for p in inputs}
            or native_hashes != {name:sha256_file_upper(path).lower() for name,path in native_paths.items()}):raise ValueError('collision mesh: inputs changed during join')
    result=dict(schema='endfield.streaming-collision-mesh-candidates.v1',status='validated-candidate-bindings',
        inputSetSha256=receipt['inputSetSha256'],sourceHashes=hashes,
        selection=current['selection'],extraction=current['extraction'],
        summary=dict(sourceResourceKeys=len(candidates),selectedBundleMainMeshKeys=len(bindings),
                     sourceOccurrences=sum(occurrences[k] for k in bindings),freshMeshes=len(meshes['objects'])),rows=rows,
        evidenceBoundary='exact current source/Bundle/raw Mesh bytes and complete supported cooked geometry; direct container main-asset PPtrs; conditional full64 manifest candidates; native resource/subasset selection, activation and runtime hit ownership unresolved')
    atomic_write_text(output,json.dumps(result,indent=2)+'\n')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--collision-receipt',type=Path,required=True);p.add_argument('--scene-receipt',type=Path,required=True)
    p.add_argument('--game-root',type=Path,required=True)
    p.add_argument('--output',type=Path,default=REPO_ROOT/'reports/animestudio/streaming_collision_mesh_candidates_latest.json')
    args=p.parse_args();output=args.output.resolve()
    if not any(output.is_relative_to(REPO_ROOT/name) for name in ('reports','tmp','scratch')):p.error('generated output must be under reports/, tmp/ or scratch/')
    try:
        r=audit(collision_receipt=args.collision_receipt,scene_receipt=args.scene_receipt,output=output,game_root=args.game_root)
        print(json.dumps(dict(status=r['status'],summary=r['summary'],output=str(output))));return 0
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print(json.dumps(dict(status='failed',diagnostics=[dict(check='streaming_mesh_candidates',detail=str(exc)[:1600])])));return 1


if __name__=='__main__':raise SystemExit(main())
