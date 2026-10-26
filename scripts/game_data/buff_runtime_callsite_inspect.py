"""Join paired Buff sequence observations to selected compiled direct callsites.

Recorded return-address agreement does not independently authenticate loaded
instructions, source nodes, receiver lifetime or final gameplay effects.
"""
from __future__ import annotations
import argparse
import json
import struct
from pathlib import Path

from scripts.common import check_installed_native_inputs
from scripts.game_data import mission_trace_inspect as trace
from scripts.game_data.buff_runtime_trace_inspect import checked_pin, fingerprint
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.il2cpp.native_image import open_native_image

BASE = 'buff.AbilityAction.Execute'
CORE = 'Beyond.Gameplay.Core.'
BOUNDARY = ('Recorded caller RVA agrees with a selected compiled direct callsite. '
    'Nearest instrumented ancestors may contain unobserved intermediates; no '
    'independent loaded-image, runtime-type, serialized-node, lifetime or effect admission.')


def join_callsites(events, callsites):
    opened, stacks, groups = {}, {}, {}
    for row in events:
        if row['phase'] == 'entry':
            continue
        identity = row['invocationId']; stack = stacks.setdefault(row['threadId'], [])
        if row['phase'] == 'enter':
            trace.require(identity not in opened and row['parentInvocationId'] == (stack[-1] if stack else 0), 'Buff callsites: entry ancestry')
            owner = next((i for i in reversed(stack) if opened[i]['entry']['hook'] == BASE), None)
            buff = next((opened[i]['entry'] for i in reversed(stack) if opened[i]['entry']['hook'] == 'buff.Buff._ExecuteBuffAction'), None)
            fields = {f['label']:f.get('value') for f in buff['fields']} if buff else {}
            opened[identity] = {'entry':row, 'owner':owner, 'buffIdAtAncestorEntry':fields.get('entryDataId'), 'selected':[]}
            stack.append(identity)
            continue
        trace.require(row['phase'] == 'return' and stack and stack[-1] == identity, 'Buff callsites: return ancestry')
        current = opened.pop(identity); entry = current['entry']
        trace.require(row['hook'] == entry['hook'] and row['parentInvocationId'] == entry['parentInvocationId'], 'Buff callsites: pair binding')
        site = callsites.get(entry.get('callerGameAssemblyRva'))
        if site is not None:
            trace.require(entry['hook'] == site['hook'], 'Buff callsites: caller/callee mismatch')
            item = {'role':site['role'],'returned':row['returnValue'],'invocationId':identity,
                'callerReturnRva':entry['callerGameAssemblyRva'],'entrySequence':entry['sequence'],'returnSequence':row['sequence']}
            if current['owner'] is not None:
                opened[current['owner']]['selected'].append(item)
            else:
                key=json.dumps(['without-outer',site['role'],row['returnValue']])
                group=groups.setdefault(key,{'outerObserved':False,'role':site['role'],'returned':row['returnValue'],'calls':0,'examples':[]})
                group['calls']+=1
                if len(group['examples'])<2:group['examples'].append(item)
        if entry['hook'] == BASE and current['selected']:
            signature={'outerObserved':True,'buffIdAtAncestorEntry':current['buffIdAtAncestorEntry'],
                'outerReturned':row['returnValue'],'selectedSequenceReturns':[{'role':i['role'],'returned':i['returned']} for i in current['selected']]}
            key=json.dumps(signature,sort_keys=True)
            trace.require(len(groups)<65536,'Buff callsites: grouping budget')
            group=groups.setdefault(key,{**signature,'calls':0,'examples':[]});group['calls']+=1
            if len(group['examples'])<2:group['examples'].append({'outerInvocationId':identity,'sequences':current['selected']})
        stack.pop()
    trace.require(not opened and all(not s for s in stacks.values()),'Buff callsites: open invocations')
    return sorted(groups.values(),key=lambda row:-row['calls'])


def inspect_callsites(analysis_dir, gameassembly, metadata, output):
    trace.require(not output.exists(),'Buff callsites: output must be new')
    analysis_path=analysis_dir/'buff-paired-analysis.json'; analysis_pin=fingerprint(analysis_path)
    analysis=trace.read_object(analysis_path,32*1024**2)
    trace.require(analysis.get('recordedPairTransportComplete') is True,'Buff callsites: complete pairs required')
    pins=[analysis_pin,*analysis['inputs']]
    for pin in pins:checked_pin(pin)
    profile_path=next(Path(p['path']) for p in pins if Path(p['path']).name=='mission-trace-build-manifest.json')
    profile=trace.read_object(profile_path,32*1024**2)
    gate=check_installed_native_inputs(profile['files']['gameAssembly']['sha256'],profile['files']['metadata']['sha256'],gameassembly=gameassembly,metadata=metadata)
    trace.require(gate.validated,'Buff callsites: native '+gate.status+': '+gate.detail)
    image=open_native_image(gate.gameassembly,gate.metadata);index=BodyIndex(image)
    body=index.body(CORE+'IfElseAction','_DoExecute');sites={}
    for row in body.rows:
        if not row['text'].startswith('call '):continue
        raw=bytes.fromhex(row['bytes'])
        if len(raw)!=5 or raw[0]!=0xe8:continue
        va=int(row['va'],16);target=va+5+struct.unpack_from('<i',raw,1)[0]
        trace.require(row['text']==f'call 0x{target:x}','Buff callsites: direct-call bytes')
        names=index.names_of(target)
        for callee,role,hook in ((CORE+'SequenceAction.ExecuteInstant','condition-sequence','buff.SequenceAction.ExecuteInstant'),
            (CORE+'SequenceAction.Execute','selected-branch-sequence','buff.SequenceAction.Execute')):
            if callee in names:
                rva=va+5-image.pe.image_base
                trace.require(rva not in sites,'Buff callsites: duplicate caller RVA')
                sites[rva]={'role':role,'hook':hook,'caller':body.symbol,'callee':callee,'callBytes':raw.hex(),'returnRva':rva}
    trace.require(len(sites)==2,'Buff callsites: expected unique condition and branch direct calls')
    decoded=next(Path(p['path']) for p in pins if Path(p['path']).name=='decoded.events.jsonl')
    def events():
        with decoded.open('rb') as stream:
            for number,line in enumerate(stream,1):
                trace.require(number<=trace.Limits().rows and len(line)<=trace.Limits().output_line_bytes and line.endswith(b'\n'),'Buff callsites: row budget')
                yield trace.parse_json(line,'Buff callsite row')
    groups=join_callsites(events(),sites)
    for pin in pins:checked_pin(pin)
    after=check_installed_native_inputs(gate.gameassembly_sha256,gate.metadata_sha256,gameassembly=gate.gameassembly,metadata=gate.metadata)
    trace.require(after.validated,'Buff callsites: native drift after join')
    result={'schema':'endfield.buff-runtime-callsite-observations.v1','inputs':pins,'nativeInputs':profile['files'],
        'sites':list(sites.values()),'groups':groups,'boundary':BOUNDARY,'runtimeNodeSelectionExact':False,'loadedImageIndependentlyAuthenticated':False}
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2)+'\n')
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--analysis-dir',type=Path,required=True);parser.add_argument('--gameassembly',type=Path,required=True)
    parser.add_argument('--metadata',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(argv)
    from scripts.repo_paths import REPO_ROOT
    if not any(args.output.resolve().is_relative_to(REPO_ROOT/root) for root in ('reports','scratch','tmp')):parser.error('--output must be under reports/, scratch/ or tmp/')
    try:result=inspect_callsites(args.analysis_dir,args.gameassembly,args.metadata,args.output)
    except (trace.InspectionError,OSError,ValueError,KeyError,TypeError) as exc:
        print('[buff_runtime_callsite_inspect] failed: '+str(exc));return 1
    print(json.dumps({'groups':len(result['groups']),'outerInvocations':sum(r['calls'] for r in result['groups'] if r['outerObserved'])}));return 0


if __name__=='__main__':raise SystemExit(main())
