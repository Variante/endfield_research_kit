"""Recover executable references from admitted selected Shader bodies."""
if __name__=='__main__' and not __package__:
    raise SystemExit('Run python -m scripts.game_data.shader.instruction_corpus from the repository root')
import argparse
from collections import Counter
import json
from pathlib import Path
import tempfile

from scripts.common import write_json
from scripts.game_data import unity_scene_corpus as scenes,unity_source_directory_corpus as sources
from scripts.game_data.shader.disassembler import Disassembler
from scripts.game_data.shader.instructions import read_disassembly,bind_parameters
from scripts.game_data.shader.dependencies import output_dependencies
from scripts.game_data.shader.programs import read_shader
from scripts.game_data.shader.metadata import analyze_shader
from scripts.game_data.unity_scene import scene_identity
from scripts.repo_paths import REPO_ROOT

SCHEMA='endfield.selected-shader-instruction-corpus.v2'


def recover(rows,bodies,*,decoder,work):
    work.mkdir(parents=True,exist_ok=True);analyses=[];counts=Counter();executables={}
    for source in rows:
        if source['classId']!=48:continue
        body=bodies[scene_identity(source['identity'])];parsed=read_shader(body);analysis=analyze_shader(body,parsed)
        platforms={l['lod']:next(p for p in l['platforms'] if p['platform']==4) for l in parsed['lods'] if any(p['platform']==4 for p in l['platforms'])}
        for variant in analysis['variants']:
            record=platforms[variant['shaderLOD']]['records'][variant['codeIndex']]
            layout=analysis['parameterLayouts'].get(variant['layoutId']);summaries=[]
            for snippet in record['code']['snippets']:
                key=snippet['sha256']
                if key not in executables:
                    text=decoder.disassemble(snippet['bytecode']);executable=read_disassembly(text,snippet)
                    executable['outputDependencies']=[output_dependencies(executable,o) for o in executable['outputs']] if executable['stage']=='fragment' else []
                    path=work/(key+'.asm');path.write_text(text,encoding='utf-8');executables[key]=dict(executable,path=str(path))
                executable=executables[key]
                binding=bind_parameters(executable,layout) if layout else dict(status='missing_parameter_table',gaps=[])
                summaries.append(dict(stage=executable['stage'],bytecodeSha256=key,assemblyPath=executable['path'],
                    instructionCount=executable['instructionCount'],opcodeCounts=executable['opcodeCounts'],parameterBindings=binding))
                summaries[-1]['outputDependencies']=executable['outputDependencies']
                counts['stageReferences']+=1;counts[binding['status']]+=1;counts['bindingGaps']+=len(binding['gaps'])
            variant['instructionEvidence']=summaries
        analysis.update(schema='endfield.stored-shader-analysis.v2',source=source);analyses.append(analysis)
    counts['shaders']=len(analyses);counts['uniqueExecutables']=len(executables)
    return dict(schema=SCHEMA,status='complete',counts=dict(counts),analyses=analyses,
        evidenceBoundary='Admitted source bodies, token-framed DXBC and native disassembly. Stored named descriptors are checked against executable VS/PS register declarations and CB bounds; partial and dynamic joins remain explicit. No runtime selection, uploads, bound payloads or execution proof.')


def collect(scene_receipt,source_receipts,*,work_root=REPO_ROOT/'tmp/animestudio/shader_instructions'):
    scene=scenes.validate_receipt(scene_receipt.resolve());rows=[];bodies={};receipts=[]
    for path in source_receipts:
        report,decoded=sources.validate_receipt(path.resolve(),scene);rows.extend(report['objects']);bodies.update(decoded);receipts.append(report)
    decoder=Disassembler();work_root.mkdir(parents=True,exist_ok=True);work=Path(tempfile.mkdtemp(prefix='instructions-',dir=work_root.resolve()))
    result=recover(rows,bodies,decoder=decoder,work=work)
    decoder.check();scenes.check_receipt_snapshot(scene)
    for report in receipts:scenes.check_receipt_snapshot(report)
    result['producer']=dict(nativeDll=str(decoder.path),sha256=decoder.sha256,sceneReceipt=str(scene_receipt.resolve()),sourceReceipts=[str(p.resolve()) for p in source_receipts])
    return result


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--scene-receipt',type=Path,required=True);p.add_argument('--source-receipt',type=Path,action='append',required=True);args=p.parse_args(argv)
    try:
        r=collect(args.scene_receipt,args.source_receipt);write_json(REPO_ROOT/'reports/assets/stored_shader_instructions_current.json',r)
        print('Shader instruction census:',r['counts'],flush=True);return 0
    except (OSError,ValueError,KeyError,TypeError,OverflowError) as e:print('Shader instruction recovery failed:',str(e)[:1600],flush=True);return 1


if __name__=='__main__':raise SystemExit(main())
