"""Inspect current Buff call pairs without promoting snapshots to effects.

The maintained generic trace reader binds and decodes original session files.
This view adds same-invocation Boolean results and entry/return field changes;
it neither substitutes a legacy receipt nor infers ownership from pointers.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import math
import struct
from pathlib import Path
from typing import Iterable

from scripts.game_data import mission_trace_inspect as trace
from scripts.game_data.mission_trace_invocations import Invocations, InvocationError


def floating_return(return_type, raw):
    """Keep IEEE bits, signed zero and nonfinite class; emit strict JSON values."""
    if return_type not in {'float', 'double'} or raw is None:
        return None
    bits = 32 if return_type == 'float' else 64
    trace.require(type(raw) is int and 0 <= raw < 1 << bits, 'Buff pair: floating return width')
    value = struct.unpack('<f' if bits == 32 else '<d', raw.to_bytes(bits // 8, 'little'))[0]
    return {'bits': f'0x{raw:0{bits // 4}x}', 'value': value if math.isfinite(value) else None,
            'class': 'finite' if math.isfinite(value) else 'nan' if math.isnan(value) else 'infinity',
            'signBit': raw >> (bits - 1)}


def snapshot_differences(before, after):
    """Keep exact/null snapshots separate from unavailable fields and writes."""
    first={f['label']:f for f in before};second={f['label']:f for f in after}
    trace.require(len(first)==len(before) and len(second)==len(after) and first.keys()==second.keys(),
                  'Buff pair: duplicate or differing field labels')
    changed=[];unavailable=[]
    for label,a in first.items():
        b=second[label]
        if a.get('state') not in (1,4) or b.get('state') not in (1,4):
            unavailable.append({'label':label,'entryState':a.get('state'),'returnState':b.get('state')})
            continue
        keys=('type','raw64','state','valueBits','storageType','valueRepresentation')
        trace.require(all(a.get(k)==b.get(k) for k in ('type','storageType','valueRepresentation')) and
                      ('valueBits' not in a or 'valueBits' not in b or a['valueBits']==b['valueBits']),
                      'Buff pair: descriptor drift between phases')
        if any(a.get(k)!=b.get(k) for k in ('raw64','state','text')):
            changed.append({'label':label,'entry':{k:a[k] for k in (*keys,'text','value') if k in a},
                            'return':{k:b[k] for k in (*keys,'text','value') if k in b}})
    return changed,unavailable


def paired_records(events: Iterable[dict], hooks: list[dict], summary: dict):
    """Yield exact recorded pairs while retaining unfinished/unwound coverage."""
    invocations=Invocations();opened={};counts=Counter();results=Counter();changes=Counter();unreadable=Counter()
    for row in events:
        index=row.get('hookIndex')
        trace.require(type(index) is int and 0<=index<len(hooks),'Buff pair: hook index')
        hook=hooks[index]
        trace.require(hook['name'].startswith('buff.') and row.get('hook')==hook['name'],'Buff pair: hook/name binding')
        bound={**row,'args':row['rawArgs']}
        closed=invocations.observe(bound,hook);phase=row['phase'];counts[(hook['name'],phase)]+=1
        identity=row['invocationId']
        if phase=='enter':
            opened[identity]=row
        elif phase in ('return','unwind'):
            entry=opened.pop(identity)
            changed,missing=(snapshot_differences(entry['fields'],row['fields']) if phase=='return' else ([],[]))
            if phase=='return' and hook['returnType']=='bool':results[(hook['name'],row['returnValue'])]+=1
            for f in changed:changes[(hook['name'],f['label'])]+=1
            for f in missing:unreadable[(hook['name'],f['label'])]+=1
            yield {'schema':'endfield.buff-recorded-call-pair.v1','hook':hook['name'],
                'threadId':row['threadId'],'invocationId':identity,'parentInvocationId':row['parentInvocationId'],
                'depth':row['depth'],'entrySequence':entry['sequence'],'endSequence':row['sequence'],
                'entryQpc':entry['qpc'],'endQpc':row['qpc'],'durationQpc':closed['durationQpc'],
                'receiverArgumentBits':entry['rawArgs'][hook['receiverIdentity']['arg']] if hook.get('receiverIdentity') else None,
                'returnType':hook['returnType'],'recordedReturnValue':row['returnValue'],
                'recordedFloatingReturn':floating_return(hook['returnType'],row['returnValue']),
                'returnedNormally':phase=='return','changedSnapshots':changed,'unavailableSnapshots':missing,
                'specificWriteOrEffectProved':False,'runtimeOwnershipExact':False,
                'boundary':'Recorded same-thread invocation and sequential snapshots only; no attribution to an intermediate write, descendant or server effect.'}
    summary.update(invocations=invocations.finish(False),
        hookPhases=[{'hook':h,'phase':p,'rows':n} for (h,p),n in sorted(counts.items())],
        booleanResults=[{'hook':h,'returnedFalse':results[(h,0)],'returnedTrue':results[(h,1)]}
                        for h in sorted({h for h,_ in results})],
        changedSnapshots=[{'hook':h,'label':label,'pairs':n} for (h,label),n in sorted(changes.items())],
        unavailableSnapshots=[{'hook':h,'label':label,'pairs':n} for (h,label),n in sorted(unreadable.items())])


def _pin(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        while raw:=stream.read(1024*1024):digest.update(raw)
    return {'path':path.resolve().as_posix(),'bytes':path.stat().st_size,'sha256':digest.hexdigest()}


def inspect_runtime(session: Path, output_dir: Path):
    output_dir=output_dir.resolve();session=session.resolve(strict=True)
    trace.require(not output_dir.exists() or output_dir.is_dir() and not any(output_dir.iterdir()),
                  'Buff pair: output directory must be new or empty')
    trace_report=trace.inspect_session(session,output_dir/'trace',local_files=True)
    profile_path=session/'private/mission-trace-build-manifest.json'
    decoded_path=output_dir/'trace'/trace_report['decodedOutput']
    summary_path=session/'mission-trace/summary.json'
    journal=session/'mission-trace/events.jsonl'
    paths=(profile_path,summary_path,journal,decoded_path,output_dir/'trace/analysis.json')
    pins=[_pin(p) for p in paths]
    trace.require(pins[0]['sha256']==trace_report['profileSha256'] and
                  pins[1]['sha256']==trace_report['providerSummarySha256'], 'Buff pair: inspected profile/summary changed')
    profile=trace.read_object(profile_path,32*1024*1024);hooks=profile['missionTraceHooks']
    summary=trace.read_object(summary_path,32*1024*1024)
    trace.require(summary.get('schema')=='endfieldCapture.missionTraceSummary.v3','Buff pair: paired summary required')
    report={'schema':'endfield.buff-runtime-paired-analysis.v1','status':'failed','session':str(session),
        'nativeValidationReproved':False,'legacyCaptureAdmission':False,'runtimeOwnershipExact':False,
        'specificWriteOrEffectProved':False,'traceAnalysis':pins[-1],'inputs':pins}
    partial=output_dir/'buff-pairs.partial.jsonl';final=output_dir/'buff-pairs.jsonl'
    def events():
        with decoded_path.open('rb') as stream:
            count=0
            while line:=stream.readline(trace.Limits().output_line_bytes+1):
                trace.require(line.endswith(b'\n') and len(line)<=trace.Limits().output_line_bytes,'Buff pair: decoded line budget')
                count+=1;trace.require(count<=trace.Limits().rows,'Buff pair: row budget')
                yield trace.parse_json(line,'decoded Buff phase')
            trace.require(count==trace_report['decodedRows'],'Buff pair: decoded row count changed')
    try:
        written=0
        with partial.open('xb') as sink:
            for pair in paired_records(events(),hooks,report):
                payload=(json.dumps(pair,ensure_ascii=True,allow_nan=False)+'\n').encode('ascii')
                written+=len(payload);trace.require(written<=trace.Limits().output_bytes,'Buff pair: output byte budget')
                sink.write(payload)
        trace.require(pins==[_pin(p) for p in paths],'Buff pair: inputs changed during analysis')
        facts=trace_report['receiptFacts'];calls=report['invocations']
        report['recordedPairTransportComplete']=(facts.get('captureCompleteClaim') is True and
            facts.get('healthyClaim') is True and facts.get('allJournalRowsAccounted') is True and
            facts.get('strictTransitionReceiptsConsistent') is True and not facts.get('collectionBoundFailureMarkers') and
            calls['openCount']==0 and calls['unwound']==0 and not report['unavailableSnapshots'])
        report['receiptFacts']=facts
        report['status']='locally-analyzed-recorded-pairs';report['pairsOutput']=final.name
        report['boundary']='Raw saved file consistency and recorded invocation results; no independent loaded-image, allocation-lifetime, intermediate-write or server-effect admission.'
        partial.rename(final)
    except (trace.InspectionError,InvocationError,OSError,KeyError,TypeError,ValueError) as exc:
        report['failure']=str(exc)[:2048]
        for key in ('invocations','hookPhases','booleanResults','changedSnapshots','unavailableSnapshots'):report.pop(key,None)
        (output_dir/'buff-paired-analysis.json').write_text(json.dumps(report,indent=2)+'\n')
        raise trace.InspectionError(report['failure']) from exc
    (output_dir/'buff-paired-analysis.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session',type=Path,required=True);parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args(argv)
    try:report=inspect_runtime(args.session,args.output_dir)
    except (trace.InspectionError,OSError) as exc:
        print('[buff_runtime_paired_inspect] failed: '+str(exc));return 1
    print(json.dumps({'status':report['status'],'completedPairs':report['invocations']['completed'],
        'recordedPairTransportComplete':report['recordedPairTransportComplete']}));return 0


if __name__=='__main__':raise SystemExit(main())
