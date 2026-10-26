"""Read observed PGS response without inventing source, lifetime or step joins.

Evidence and admission boundary
-------------------------------
Direct positive accumulated normal response is established by admitted same-call
post-original-solve windows through the selected PGS scalar consumer, wrapper/core,
dispatch tag and descriptor/header/count/point-to-array proof. It may include warm
starting or earlier iterations: it is not newly generated impulse, force in world
units or a source/step owner. Clipped arrays stay unknown. Archive chunks can cover
a complete scalar only under the same call/root, with each read time retained;
no other callback repairs a missing word or makes the sample atomic.

Only proved body vector lanes participate in response classification; the older
larger prefix may include padding/neighbors. Without recorded read-success flags,
vector differences remain conditional even when archived constraint response is
direct. New per-side actor/shape prefixes, larger response windows and before/after
copy-success bits do not upgrade historical samples. Missing same-lifetime owners,
reused actor versions and nonzero updates without original task generations leave
the positive source/step join unresolved, rather than absence of physical work.
"""
from __future__ import annotations
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import struct

from scripts.common import sha256_file
from scripts.game_data.collision_solver_response_native import load
from scripts.game_data.collision_runtime_mesh import load_admission, WindowView, WindowGap, _output_path
from scripts.game_data.corpus_common import atomic_write_text


def constraint_response(view, address, descriptor_bytes, variant, contract):
    h=contract['layout']['header'];limits=contract['limits']
    if not 0<descriptor_bytes<=limits['maxConstraintBytes'] or descriptor_bytes<h['bytes']:
        raise ValueError(f'solver-response descriptor extent: actual={descriptor_bytes}, minimum={h["bytes"]}, maximum={limits["maxConstraintBytes"]}')
    header=view.read(address,h['bytes'],'solver.response.header')
    if header[0] not in variant['constraintTags']:
        raise ValueError(f'solver-response original dispatch/header tag differs: actual={header[0]}, expected={variant["constraintTags"]}')
    count=header[h['normalCount']];friction=header[h['frictionCount']]
    offset=h['bytes']+count*h['pointStride'];size=count*h['forceStride']
    if count>limits['maxNormals'] or offset+size>descriptor_bytes:
        raise ValueError(f'solver-response normal-force extent exceeds descriptor: normals={count}, end={offset+size}, descriptor={descriptor_bytes}')
    values=[]
    if count:
        try:
            values=list(struct.unpack('<'+'f'*count,view.read(address+offset,size,'solver.response.accumulatedNormal')))
        except WindowGap:
            # Exact spans are archived in chunks. Each complete scalar must be
            # present in this same call/root; a missing word still withholds the
            # whole result. Preserve each read time rather than claim atomicity.
            values=[view.scalar(address+offset+i*h['forceStride'],'f',f'solver.response.accumulatedNormal[{i}]') for i in range(count)]
    if any(not math.isfinite(v) or v<0 for v in values):
        bad=next((i,v) for i,v in enumerate(values) if not math.isfinite(v) or v<0)
        raise ValueError(f'solver-response nonfinite/negative accumulated normal scalar: index={bad[0]}, actual={bad[1]}')
    return dict(constraintTag=header[0],normalCount=count,frictionCount=friction,
        accumulatedNormal=values,positiveAccumulatedNormal=any(v>0 for v in values),reads=view.reads,
        boundary='Observed post-solve accumulated normal response; no newly-generated impulse, world-force units, source or step claim.')


def copied_body_lanes(row, side, contract, read_mask=None):
    before=bytes.fromhex(row['model'])[side*48:side*48+48];after=bytes.fromhex(row['world'])[:48]
    if side not in (0,1) or len(before)!=48 or len(after)!=48:
        raise ValueError('solver-response copied body framing')
    lanes=[];consumed=set()
    for name,offset in contract['layout']['body'].items():
        consumed.update(range(offset,offset+12));a,b=before[offset:offset+12],after[offset:offset+12]
        lanes.append(dict(lane=name,beforeBits=a.hex(),afterBits=b.hex(),changed=a!=b))
    changed=any(x['changed'] for x in lanes)
    if read_mask is not None and (type(read_mask) is not int or read_mask&~7):raise ValueError('solver-response body read mask')
    complete=read_mask is None or bool(read_mask&(1<<side) and read_mask&4)
    return dict(lanes=lanes,consumedVectorsChanged=changed if complete else None,
        onlyUnconsumedBytesChanged=before!=after and not changed if complete else None,
        readCompleteness='not_recorded' if read_mask is None else 'complete' if complete else 'partial_read',
        boundary='Separately timed consumed-vector copies; missing read-success evidence stays conditional or unknown, and unconsumed neighboring bytes do not count as body response.')


def decode(calls, observations, windows, archive, contract):
    variants={v['kind']:v for v in contract['variants']};rows=[]
    for pair in observations['solvePairs']:
        parent=calls[pair['solveCall']];variant=variants.get(parent['kind'])
        if variant is None:continue
        row=calls[pair['call']]['returnRecord'];desc=bytes.fromhex(pair['afterDescriptorHex']);d=contract['layout']['descriptor']
        address=struct.unpack_from('<Q',desc,d['constraint'])[0];extent=struct.unpack_from('<H',desc,d['length'])[0]*16
        item=dict(call=pair['call'],solveCall=pair['solveCall'],side=pair['side'],kind=parent['kind'],
            constraint=f'{address:016x}',descriptorBytes=extent,routePrepCall=pair['routePrepCall'],routeState=pair['routeState'],
            bodyCopy=copied_body_lanes(row,pair['side'],contract,pair.get('bodyReadMask')),sourceAndStep='unresolved')
        item['sampledActor']=pair.get('provenance',{}).get('actor') if pair.get('provenance') else None
        item['stableVersionedEcsIdentity']=pair.get('stableEcsIdentity',False)
        if not pair['stableDescriptorKey']:
            item.update(status='changed_descriptor_key',gap='Copied key changed around original solve; no constraint response join.')
        else:
            view=WindowView(windows,archive,call=pair['call'],root=f'{address:016x}',role='solverConstraint')
            try:
                response=constraint_response(view,address,extent,variant,contract)
                # Archive reads must be within this original post-solve observation.
                first=parent['returnRecord'];q=bytes.fromhex(first['queryHex']);returned=struct.unpack_from('<Q',q,184)[0]
                if not returned<=calls[pair['call']]['qpc'] or any(not calls[pair['call']]['qpc']<=x['qpc']<=row['qpc'] for x in view.reads):
                    raise ValueError('solver-response archive outside original post-solve interval')
                item.update(status='observed_post_solve_response',response=response)
            except WindowGap as error:
                item.update(status='uncaptured_response_range',gap=str(error))
            except ValueError as error:
                raise ValueError(f'solver-response sample call={pair["call"]}, solve={pair["solveCall"]}, side={pair["side"]}, constraint={address:016x}: {error}') from error
        rows.append(item)
    positive={x['solveCall'] for x in rows if x.get('response',{}).get('positiveAccumulatedNormal')}
    return dict(samples=rows,coverage=dict(Counter(x['status'] for x in rows)),positiveSolveCalls=sorted(positive),
        bodyLaneChanges=sum(x['bodyCopy']['consumedVectorsChanged'] is True for x in rows),
        excludedNeighborChanges=sum(x['bodyCopy']['onlyUnconsumedBytesChanged'] is True for x in rows),
        boundary=contract['evidenceBoundary'])


def audit(root, *, game_root=None):
    root=root.resolve();result=dict(schema='endfield.collision-runtime-solver-response.v1',status='failed',session=str(root),diagnostics=[])
    try:
        calls={};admitted,profile,receipt,_=load_admission(root,game_root=game_root,calls_out=calls)
        directory=game_root.parent if game_root and game_root.name=='Endfield_Data' else game_root
        paths={n:directory/r['relativePath'] if directory else Path(r['path']) for n,r in profile['files'].items()}
        contract,gate=load(gameassembly=paths['gameAssembly'],metadata=paths['metadata'],unityplayer=paths['unityPlayer']);result['nativeGate']=gate
        if contract is None:raise ValueError('solver-response selected native gate:'+gate['status'])
        for key,name in (('gameAssemblySha256','gameAssembly'),('metadataSha256','metadata'),('unityPlayerSha256','unityPlayer')):
            if contract['nativeInputs'][key].lower()!=profile['files'][name]['sha256'].lower():raise ValueError('solver-response capture/native build differs:'+name)
        from scripts.game_data.collision_capture_stages import decode_stages
        stages=decode_stages(calls,profile,receipt)
        if stages!=admitted['physicsStages']:raise ValueError('solver-response cached stage observations differ')
        report=decode(calls,stages,admitted['nativeMemory']['windows'],(root/'native-memory.bin').read_bytes(),contract)
        if sha256_file(root/'events.jsonl')!=admitted['journalSha256'] or sha256_file(root/'native-memory.bin')!=admitted['nativeMemory']['sha256']:
            raise ValueError('solver-response capture changed during audit')
        result.update(report,status='validated_response_boundary',journalSha256=admitted['journalSha256'],archiveSha256=admitted['nativeMemory']['sha256'])
    except (OSError,ValueError,KeyError,TypeError,RuntimeError,struct.error) as error:
        result.update(status='failed',diagnostics=[dict(check='solver_response',detail=str(error)[:1600])])
    return result


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--session',type=Path,required=True);p.add_argument('--game-root',type=Path);p.add_argument('--output',type=Path);args=p.parse_args(argv)
    r=audit(args.session,game_root=args.game_root);out=_output_path(args.output or args.session/'collected/runtime-solver-response.json')
    atomic_write_text(out,json.dumps(r,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:r[k] for k in ('status','diagnostics')}|dict(coverage=r.get('coverage',{}),positiveSolveCalls=len(r.get('positiveSolveCalls',[])))))
    return int(r['status']=='failed')


if __name__=='__main__':raise SystemExit(main())
