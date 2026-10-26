"""Publish current Shader analysis beside immutable published Material docs.

Only exact physical Shader identity/raw-hash matches bind a published Material
artifact. This stage owns its sidecar, not the existing asset index or renderer
admission. Material artifact hashes keep the link fail-closed after publication
changes. It never reclassifies that older publication as a fresh exporter run.
"""
if __name__=='__main__' and not __package__:
    raise SystemExit('Run python -m scripts.webui.assets.shader_analysis from the repository root')

import argparse
import hashlib
import json
from pathlib import Path
import tempfile

from scripts.common import write_json,sha256_file,rel_path
from scripts.game_data.shader.corpus import collect
from scripts.game_data.shader.instruction_corpus import collect as collect_instructions
from scripts.game_data.shader.metadata import material_shader_info
from scripts.game_data.unity_scene import scene_identity
from scripts.repo_paths import REPO_ROOT

SCHEMA='endfield.assets-shader-analysis.v3'


def _published_identity(identity):
    # Material JSON uses decimal strings for integers beyond JS precision.
    return scene_identity(dict(identity,sourceOffset=int(identity['sourceOffset']),pathId=int(identity['pathId'])))


def publish(report,*,root=REPO_ROOT,asset_dir=None):
    if report.get('status')!='complete' or report.get('failures'):raise ValueError('Shader corpus was not admitted')
    asset_dir=asset_dir or root/'webui/data/assets';path=asset_dir/'index.json';index_bytes=path.read_bytes();index=json.loads(index_bytes)
    source_root=root/index['sourceRoots']['StoredRender'];destination=asset_dir/'shader_analysis';destination.mkdir(parents=True,exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix='selection-',dir=destination.resolve()));shaders={};bindings={};snapshots={}
    for a in report['analyses']:
        key=scene_identity(a['source']['identity']);name='shader_'+a['source']['rawSha256']+'.json';write_json(stage/name,a)
        if key in shaders:raise ValueError('duplicate physical Shader analysis identity')
        shaders[key]=dict(analysis=a,url='/'+rel_path(stage/name,root/'webui'),sha256=sha256_file(stage/name).lower())
    documents={}
    for e in index['entries']:
        for p in e.get('cl',{}).get('renderers',{}).get('prefabs',[]):
            for r in p['records']:
                for ref in r['materials']:
                    material=ref.get('target',{});asset=material.get('asset')
                    if asset:
                        if asset['rel'] in documents and documents[asset['rel']]!=asset:raise ValueError('conflicting published Material descriptors')
                        documents[asset['rel']]=asset
    for rel,asset in documents.items():
        parts=rel.split('/')
        if len(parts)!=2 or parts[0]!='StoredRender' or parts[1] in ('','.', '..') or '\\' in parts[1]:raise ValueError('published Material artifact path differs')
        source=source_root/parts[1];raw=source.read_bytes();digest=hashlib.sha256(raw).hexdigest()
        if digest!=asset['sha256']:raise ValueError('published Material artifact changed')
        snapshots[source]=(source.stat().st_size,source.stat().st_mtime_ns);doc=json.loads(raw);ref=doc['shader']
        if ref['status']!='exact_selected_target_identity':continue
        target=ref['target'];shader=shaders.get(_published_identity(target['identity']))
        if shader is None or target['rawSha256']!=shader['analysis']['source']['rawSha256']:continue
        info=material_shader_info(doc['storedProperties'],shader['analysis'])
        bindings[rel]=dict(info,materialArtifactSha256=digest,shaderAnalysisUrl=shader['url'],shaderAnalysisSha256=shader['sha256'])
    if path.read_bytes()!=index_bytes:raise ValueError('asset index changed during shader sidecar publication')
    for p,snapshot in snapshots.items():
        if (p.stat().st_size,p.stat().st_mtime_ns)!=snapshot:raise ValueError('Material source artifact changed during shader publication')
    result=dict(schema=SCHEMA,status='validated',bindings=bindings,shaderCount=len(shaders),materialCount=len(bindings),
        evidenceBoundary='Current admitted Shader analyses bound only to exact Shader identity/hash references in unchanged published Material artifacts. Stored keyword candidates remain conditional; this does not renew the existing renderer/publication admission or prove runtime shading.')
    write_json(destination/'index.json',result);return result


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--scene-receipt',type=Path,required=True);p.add_argument('--source-receipt',type=Path,action='append',required=True);p.add_argument('--instructions',action='store_true',help='Recover checked executable reads with the Windows system DXBC disassembler');args=p.parse_args(argv)
    try:
        if args.instructions:
            report=collect_instructions(args.scene_receipt,args.source_receipt)
            write_json(REPO_ROOT/'reports/assets/stored_shader_instructions_current.json',report)
        else:report=collect(args.scene_receipt,args.source_receipt,output=REPO_ROOT/'reports/assets/stored_shader_programs_current.json')
        result=publish(report);write_json(REPO_ROOT/'reports/assets/shader_analysis_publication.json',result)
        print('Stored Shader sidecar:',result['shaderCount'],'shaders;',result['materialCount'],'Material artifacts',flush=True);return 0
    except (OSError,ValueError,KeyError,TypeError,OverflowError) as e:print('Shader sidecar failed:',str(e)[:1800],flush=True);return 1


if __name__=='__main__':raise SystemExit(main())
