"""Admit selected Shader bodies and independently recover compiled metadata.

Evidence and admission boundary
-------------------------------
Exact selected-source admission authenticates current bodies and compares every
compressed segment and D3D record with admitted CLI libraries through a separate
managed checker. Stored LOD/pass/player indices join code, keywords and parameter
records. Rebuilding the CLI changes exporter provenance even with unchanged game
bytes; fresh Shader admission does not renew older collision/render receipts.
Keyword-superset candidates allow additional engine/global keywords and remain
conditional; unknown valid stored keywords prevent shortlisting. Effective
variant, pass execution and live bindings remain unresolved.
"""
if __name__=='__main__' and not __package__:
    raise SystemExit('Run python -m scripts.game_data.shader.corpus from the repository root')

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

from scripts.common import write_json,sha256_file
from scripts.game_data import unity_scene_corpus as scenes,unity_source_directory_corpus as sources
from scripts.game_data.cooked_collision_corpus import _decoder_closure
from scripts.game_data.extraction.animestudio.managed_sidecar import build_sidecar
from scripts.game_data.extraction.animestudio.setup_dotnet9 import dotnet_environment
from scripts.game_data.lz4_block import decompress_lz4
from scripts.game_data.shader.programs import read_shader
from scripts.game_data.shader.metadata import analyze_shader
from scripts.game_data.unity_scene import scene_identity
from scripts.repo_paths import REPO_ROOT

SCHEMA='endfield.selected-stored-shader-corpus.v1'


def analyze_sources(rows,bodies,*,work):
    work.mkdir(parents=True,exist_ok=True);analyses={};counts=Counter();segments=[];code_records=[]
    for source in rows:
        if source['classId']!=48:raise ValueError('shader analysis source class differs')
        identity=scene_identity(source['identity']);body=bodies[identity];parsed=read_shader(body);analysis=analyze_shader(body,parsed)
        for lod in parsed['lods']:
            blob=body['subShaderBlobs'][lod['ordinal']];raw=bytes(blob['m_CompressedBlob'])
            for pi,platform in enumerate(lod['platforms']):
                for si,(start,size,expected) in enumerate(zip(blob['m_Offsets'][pi],blob['m_CompressedLengths'][pi],blob['m_DecompressedLengths'][pi])):
                    compressed=raw[start:start+size];data=decompress_lz4(compressed,expected)
                    name=f'{source["rawSha256"]}_{lod["ordinal"]}_{pi}_{si}.lz4';path=work/name;path.write_bytes(compressed)
                    segments.append(dict(input=str(path),inputSha256=hashlib.sha256(compressed).hexdigest(),decodedBytes=expected,decodedSha256=hashlib.sha256(data).hexdigest()))
                for row in platform['records']:
                    counts[row['status']]+=1
                    if row['status']=='complete_dxbc_code':
                        path=work/f'{source["rawSha256"]}_{lod["ordinal"]}_{pi}_r{row["index"]}.dat';path.write_bytes(row['raw'])
                        code_records.append(dict(input=str(path),inputSha256=row['sha256'],codeSha256=row['code']['codeSha256'],keywords=row['code']['keywords']))
        analysis.update(source=source);analyses[identity]=analysis;counts['shaders']+=1;counts['variants']+=len(analysis['variants']);counts['layouts']+=len(analysis['parameterLayouts'])
        counts['indexedGaps']+=len(analysis['gaps'])
    return analyses,dict(counts),dict(segments=segments,codeRecords=code_records)


def collect(scene_receipt,source_receipts,*,output,work_root=REPO_ROOT/'tmp/animestudio/shader_recovery'):
    scene=scenes.validate_receipt(scene_receipt.resolve());admissions=[];bodies={};objects={}
    for path in source_receipts:
        report,decoded=sources.validate_receipt(path.resolve(),scene);admissions.append(report)
        for row in report['objects']:
            if row['classId']==48:objects[scene_identity(row['identity'])]=row
        bodies.update(decoded)
    work_root.mkdir(parents=True,exist_ok=True);run=Path(tempfile.mkdtemp(prefix='shaders-',dir=work_root.resolve()))
    analyses,counts,manifest=analyze_sources(list(objects.values()),bodies,work=run/'inputs')
    if not analyses:raise ValueError('no admitted Shader bodies were selected')
    cli=Path(scene['extraction']['command'][0]);before=_decoder_closure(cli)
    helper=build_sidecar(cli,run/'helper',project=REPO_ROOT/'scripts/game_data/extraction/animestudio/shader_check/ShaderCheck.csproj',binary_name='ShaderCheck.dll')
    path=run/'parity.json';write_json(path,manifest);log=run/'parity.log';command=[helper['sdk'],helper['binary'],str(cli.parent.resolve()),str(path)]
    with log.open('wb') as stream:result=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,env=dotnet_environment(Path(helper['sdk']).parent))
    if result.returncode or log.stat().st_size:raise ValueError('Shader independent/CLI parity failed: '+log.read_text('utf-8',errors='replace')[:1600])
    if _decoder_closure(cli)!=before or _decoder_closure(Path(helper['binary']))!=helper['closure']:raise ValueError('Shader checker/CLI closure changed')
    scenes.check_receipt_snapshot(scene)
    for report in admissions:scenes.check_receipt_snapshot(report)
    report=dict(schema=SCHEMA,status='complete',failures=[],counts=counts,analyses=list(analyses.values()),
        sources=dict(scene=str(scene_receipt.resolve()),receipts=[str(p.resolve()) for p in source_receipts]),
        producer=dict(command=command,helper=helper,cliClosure=before,manifestSha256=sha256_file(path),log=str(log)),
        evidenceBoundary='Complete admitted selected Shader bodies; independent compressed segment/directory/record framing, D3D code and parameter tables, explicit opaque non-D3D coverage, stored pass/keyword/parameter joins and full LZ4/code-record parity with the unchanged admitted CLI. No live shader variant, PSO or bound-resource selection.')
    write_json(output,report);return report


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--scene-receipt',type=Path,required=True)
    p.add_argument('--source-receipt',type=Path,action='append',required=True);p.add_argument('--output-json',type=Path,default=REPO_ROOT/'reports/assets/stored_shader_programs_current.json');args=p.parse_args(argv)
    if not args.output_json.resolve().is_relative_to((REPO_ROOT/'reports').resolve()):p.error('generated shader reports belong under reports/')
    try:
        r=collect(args.scene_receipt,args.source_receipt,output=args.output_json);print('Stored shader programs:',r['status'],r['counts'],flush=True);return 0
    except (OSError,ValueError,KeyError,TypeError,OverflowError) as e:print('Stored shader program gate failed:',str(e)[:1800],flush=True);return 1


if __name__=='__main__':raise SystemExit(main())
