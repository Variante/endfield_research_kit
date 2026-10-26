"""Join admitted stored programs to saved graphics draw observations.

Evidence and admission boundary
-------------------------------
Exact stored-body re-admission precedes saved shader archive/draw comparison.
Creation/registration is not a draw, and program equality cannot identify a
source Material. Constant prefixes must cover declared spans within bound ranges.
Compressed texture content requires immutable hash-checked preview inputs and
complete mip tails; same-draw content additionally needs copy phase, call/Present
and bound object/view, not merely a frame-wide draw-local flag. Retained Lab
shared-program examples do not close texture content for the studied preview;
the lifter candidate cohort has no retained draw. Effective constants, formats,
mip ranges, samplers and source ownership remain unresolved.
"""
import argparse
from collections import Counter,defaultdict
import hashlib
import json
from pathlib import Path
from scripts.common import write_json
from scripts.game_data import unity_scene_corpus as scenes,unity_source_directory_corpus as sources
from scripts.game_data.shader.capture import selected_archive,observed_constants
from scripts.game_data.shader.disassembler import Disassembler
from scripts.game_data.shader.dxbc import read_dxbc
from scripts.game_data.shader.instructions import read_disassembly,bind_parameters
from scripts.game_data.shader.programs import read_shader
from scripts.game_data.shader.metadata import analyze_shader
from scripts.game_data.unity_scene import scene_identity
from scripts.repo_paths import REPO_ROOT


def collect(scene_receipt,source_receipts,sessions_root):
    scene=scenes.validate_receipt(scene_receipt.resolve());admissions=[];lookup=defaultdict(list)
    for path in source_receipts:
        receipt,bodies=sources.validate_receipt(path.resolve(),scene);admissions.append(receipt)
        for source in receipt['objects']:
            if source['classId']!=48:continue
            body=bodies[scene_identity(source['identity'])];parsed=read_shader(body);a=analyze_shader(body,parsed)
            for v in a['variants']:
                for snippet in v['snippets']:
                    if snippet['stage']!='fragment':continue
                    lookup[snippet['sha256']].append(dict(shader=a['name'],sourceIdentity=source['identity'],rawSha256=source['rawSha256'],
                        passName=v['passName'],shaderLOD=v['shaderLOD'],keywords=v['keywords'],layout=a['parameterLayouts'][v['layoutId']]))
    if not lookup:raise ValueError('no admitted fragment programs selected')
    decoder=Disassembler();decoded={};counts=Counter();sessions=[];failures=[]
    for manifest in sorted(sessions_root.glob('*/graphics/shaders/manifest.json')):
        try:
            archive,provenance=selected_archive(manifest.parent,lookup);draws=[];registered={v['sha256'] for v in archive.values()};frames=0
            for path in sorted(manifest.parent.parent.glob('frames/*/metadata.json')):
                raw=path.read_bytes();m=json.loads(raw)
                if m.get('schema')!='endfieldCapture.graphicsFrame.v2':raise ValueError('unsupported saved frame schema')
                frames+=1
                for draw in m['drawRecords']:
                    ps=[s for s in draw['shaders'] if s['stage']==4]
                    if len(ps)!=1:continue
                    shader=archive.get((4,ps[0]['identityHash'],ps[0]['bytecodeSize']))
                    if shader is None:continue
                    h=shader['sha256']
                    if h not in decoded:decoded[h]=read_disassembly(decoder.disassemble(shader['bytecode']),read_dxbc(shader['bytecode']))
                    e=decoded[h];constants={}
                    for key,decl in e['declarations'].items():
                        if decl['kind']=='cb':constants[key]=observed_constants(draw,4,decl['index'],decl['rows']*16)
                    candidates=[]
                    for source in lookup[h]:
                        binding=bind_parameters(e,source['layout'])
                        candidates.append(dict({k:v for k,v in source.items() if k!='layout'},registerJoinStatus=binding['status']))
                    draws.append(dict(metadata=str(path),metadataSha256=hashlib.sha256(raw).hexdigest(),drawOrdinal=draw['drawOrdinal'],
                        presentEpoch=draw.get('presentEpoch'),unifiedCallOrdinal=draw.get('unifiedCallOrdinal'),bytecodeSha256=h,
                        constants=constants,sourceProgramCandidates=candidates,
                        resourcePayloadDrawLocal=m.get('resourcePayloadDrawLocal',False),resourcePayloadTiming=m.get('resourcePayloadTiming'),
                        boundResources=draw.get('resources',[]),pipelineState=draw.get('pipelineState'),
                        evidenceBoundary='Exact archived bytecode joined through the recorded draw shader identity. Source program candidates do not identify the source Material. Frame-end payloads cannot prove same-draw texture contents.'))
            sessions.append(dict(session=manifest.parts[-4],archive=provenance,registeredSelectedPrograms=len(registered),frames=frames,draws=draws))
            counts['archives']+=1;counts['registeredSelectedPrograms']+=len(registered);counts['frames']+=frames;counts['matchingDraws']+=len(draws)
        except (OSError,ValueError,KeyError,TypeError,OverflowError) as e:failures.append(dict(session=manifest.parts[-4],reason=str(e)[:1000]))
    decoder.check();scenes.check_receipt_snapshot(scene)
    for a in admissions:scenes.check_receipt_snapshot(a)
    return dict(schema='endfield.selected-shader-saved-draw-corpus.v1',status='partial' if failures else 'complete',counts=dict(counts),sessions=sessions,failures=failures,
        evidenceBoundary='Admitted stored Shader bodies and byte-exact saved archive programs, with bounded draw metadata joins. Program registration is separate from observed draws. Constant prefixes do not prove source Material ownership; frame-end resource payloads, unrecorded samplers and absent draws remain gaps.')


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--scene-receipt',type=Path,required=True);p.add_argument('--source-receipt',type=Path,action='append',required=True)
    p.add_argument('--sessions-root',type=Path,required=True);p.add_argument('--output-json',type=Path,default=REPO_ROOT/'reports/assets/stored_shader_saved_draws_current.json');args=p.parse_args(argv)
    if not args.output_json.resolve().is_relative_to((REPO_ROOT/'reports').resolve()):p.error('generated reports belong under reports/')
    try:
        r=collect(args.scene_receipt,args.source_receipt,args.sessions_root);write_json(args.output_json,r)
        print('Saved Shader draws:',r['status'],r['counts'],'failures',len(r['failures']),flush=True);return 0 if not r['failures'] else 1
    except (OSError,ValueError,KeyError,TypeError,OverflowError) as e:print('Saved Shader draw census failed:',str(e)[:1600],flush=True);return 1


if __name__=='__main__':raise SystemExit(main())
