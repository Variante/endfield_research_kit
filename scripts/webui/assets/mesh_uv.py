"""Project admitted stored UV1 into mesh OBJs beside the original publication.

Evidence and admission boundary
-------------------------------
Fresh admitted Mesh buffers must reproduce the immutable published neutral UV0
OBJ byte-for-byte before only texture coordinates change to stored UV1. This
is an exact stored-channel projection, not live UV selection, shading or renewed
renderer admission.
"""
if __name__=='__main__' and not __package__:
    raise SystemExit('Run python -m scripts.webui.assets.mesh_uv from the repository root')
import argparse
import json
from pathlib import Path
import tempfile

from scripts.common import write_json,sha256_file,rel_path
from scripts.game_data import unity_scene_corpus as scenes,unity_source_directory_corpus as sources
from scripts.game_data.unity_mesh import read_surface
from scripts.game_data.unity_scene import scene_identity
from scripts.repo_paths import REPO_ROOT
from scripts.webui.assets.collision_render_assets import _obj
from scripts.webui.assets.shader_analysis import _published_identity

SCHEMA='endfield.assets-stored-mesh-uv.v2'


def project(index,rows,bodies,*,root=REPO_ROOT):
    artifacts={}
    for e in index['entries']:
        for p in e.get('cl',{}).get('renderers',{}).get('prefabs',[]):
            for renderer in p['records']:
                target=renderer['mesh'].get('target',{})
                if target.get('asset'):artifacts[_published_identity(target['identity'])]=target
    destination=root/'webui/data/assets/mesh_uv';destination.mkdir(parents=True,exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix='selection-',dir=destination.resolve()));bindings={};unavailable=[]
    for row in rows:
        if row['classId']!=43:continue
        key=scene_identity(row['identity']);target=artifacts.get(key)
        if target is None:continue
        asset=target['asset']
        if row['rawSha256']!=target['rawSha256']:raise ValueError('Mesh source/raw hash differs from published reference')
        resource=row.get('resource');stream=Path(row['rawPath']).parent/resource['file'] if resource and resource['status']=='exact_owner_archive_span' else None
        surface=read_surface(bodies[key],stream.read_bytes() if stream else None)
        if surface['uv1'] is None:
            unavailable.append(dict(rel=asset['rel'],reason='stored UV1 absent'));continue
        original=root/index['sourceRoots']['StoredRender']/asset['rel'].split('/')[-1]
        if sha256_file(original).lower()!=asset['sha256']:raise ValueError('Published Mesh artifact hash differs')
        check=stage/'uv0-check.obj'
        baseline=_obj(check,[(row['name'],surface,surface['vertices'],surface['submeshes'])])
        if baseline['sha256']!=asset['sha256']:raise ValueError('Admitted Mesh UV0 projection differs from published OBJ')
        check.unlink()
        projected=dict(surface,uv0=surface['uv1']);name=asset['rel'].split('/')[-1]
        result=_obj(stage/name,[(row['name'],projected,projected['vertices'],projected['submeshes'])])
        result.update(rel='StoredUV/'+name,submeshCount=asset['submeshCount'],hasUV0=True,uvSet=1,originalMeshArtifactSha256=asset['sha256'],originalMeshRawSha256=row['rawSha256'])
        bindings[asset['rel']]=result
    return dict(schema=SCHEMA,status='validated',sourceRoot=rel_path(stage,root),originalStoredRenderRoot=index['sourceRoots']['StoredRender'],bindings=bindings,unavailable=unavailable,
        evidenceBoundary='Fresh admitted stored Mesh body and complete render buffers reproduce the published UV0 OBJ byte-for-byte before UV1 replaces only vt coordinates. No live vertex overrides, shading or UV selection.')


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--scene-receipt',type=Path,required=True);p.add_argument('--source-receipt',type=Path,action='append',required=True);args=p.parse_args(argv)
    try:
        scene=scenes.validate_receipt(args.scene_receipt.resolve());rows=[];bodies={};receipts=[]
        for path in args.source_receipt:
            report,decoded=sources.validate_receipt(path.resolve(),scene);rows.extend(report['objects']);bodies.update(decoded);receipts.append(report)
        path=REPO_ROOT/'webui/data/assets/index.json';raw=path.read_bytes()
        result=project(json.loads(raw),rows,bodies)
        scenes.check_receipt_snapshot(scene)
        for report in receipts:scenes.check_receipt_snapshot(report)
        if path.read_bytes()!=raw:raise ValueError('Asset index changed during UV publication')
        write_json(REPO_ROOT/'webui/data/assets/mesh_uv/index.json',result);write_json(REPO_ROOT/'reports/assets/stored_mesh_uv_current.json',result)
        print('Stored UV1 projections:',len(result['bindings']),'; unavailable:',len(result['unavailable']),flush=True);return 0
    except (OSError,ValueError,KeyError,TypeError,OverflowError) as e:print('Stored Mesh UV projection failed:',str(e)[:1600],flush=True);return 1


if __name__=='__main__':raise SystemExit(main())
