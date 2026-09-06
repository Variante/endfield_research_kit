"""Current VFS BuffData provenance and anonymous suffix-candidate census.

The legacy reader's field labels are not promoted to serialization semantics.
All matching filename-string anchors are retained, including rejected anchors.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import struct
from collections import Counter
from pathlib import Path

from . import corpus_gate as vfs
from .buff import decode_buff_post_id_prefix_at, buff_post_id_result_is_exact_tail, decode_buff_pre_id_modifier_prefix
from .buff_actions import event_prefix

PREFIX='Data/Json/BuffData/'
PATTERN=re.compile(r'^Data/Json/BuffData/[^/]+[.]json$')
BOUNDARY=('Authenticated current VFS logical bytes and a 30-member envelope witness only. '
          'Filename-string anchors and reader-accepted suffixes are candidates, not proven top-level '
          'field ownership. The prefix and reader-internal opaque bodies remain unresolved. '
          'No field labels, runtime behavior or whole-schema exactness are promoted.')


def select_rows(rows, *, expected_input):
    return vfs.family_rows(rows,expected_input=expected_input,prefix=PREFIX,pattern=PATTERN,label='buff')


def frame_candidates(data: bytes, *, source: str) -> dict:
    result={'wholeSchemaExact':False,'candidates':[],'candidateCount':0,'eventPrefixStatus':'unsupported'}
    if not data or data[0]!=30:
        return {**result,'coverageStatus':'unsupported','diagnostic':{'source':source,'offset':0,'expected':30,'actual':data[0] if data else None}}
    value=Path(source).stem;encoded=value.encode('utf-8')
    marker=len(encoded).to_bytes(4,'little')+encoded
    positions=[];start=1
    while (start:=data.find(marker,start))>=0:
        positions.append(start);start+=1
        if len(positions)>64:
            return {**result,'coverageStatus':'unsupported','diagnostic':{'source':source,'offset':start-1,'expected':'at most 64 anchors; no subset selection','actual':'>64'}}
    for at in positions:
        decoded=decode_buff_post_id_prefix_at(data,value,at)
        accepted=buff_post_id_result_is_exact_tail(decoded)
        end=decoded.get('endOffset')
        if accepted and (not isinstance(end,str) or int(end,0)!=len(data)):
            vfs._fail('buff-reader-false-eof',source=source,offset=at,expected=len(data),actual=end)
        prefix_probe=None;current_prefix=None
        if accepted:
            current_prefix=event_prefix(data,source=source,limit=at)
            prefix=decode_buff_pre_id_modifier_prefix(data,at)
            prefix_end=prefix.get('endOffset')
            stop=int(prefix_end,0) if isinstance(prefix_end,str) else None
            if stop is not None and not 1<=stop<=at:
                vfs._fail('buff-prefix-range-overlap',source=source,offset=stop,expected=f'1 <= end <= {at}',actual=stop)
            prefix_probe={'readerStatus':prefix['status'],'readerEnd':stop,
                'readerAcceptedPrefix':prefix['status']=='parsed-through-attribute-modifier',
                'remainingGapRange':[stop,at] if stop is not None else None,
                'diagnostic':prefix.get('error') or prefix.get('abilityEventActionDecodeError'),
                'semanticStatus':'structural-only; legacy labels not promoted'}
        result['candidates'].append({'anchorOffset':at,'suffixStart':at+len(marker),
            'readerStatus':decoded.get('status'),'readerTailStatus':decoded.get('tailParseStatus'),
            'readerAcceptedThroughEof':accepted,'readerEndOffset':end,
            'opaquePrefixRange':[1,at],
            'readerInternalOpaqueRangesCertified':False,
            'prefixProbe':prefix_probe,
            'currentEventPrefix':current_prefix,
            'diagnostic':decoded.get('tailParseError') or decoded.get('error')})
    count=sum(row['readerAcceptedThroughEof'] for row in result['candidates'])
    current=[c['currentEventPrefix'] for c in result['candidates'] if c['currentEventPrefix'] is not None]
    event_status=('failed' if any(c['status']=='failed' for c in current) else
                  'ambiguous' if count>1 else
                  'success' if count==1 and current[0]['status']=='supported-prefix' else 'unsupported')
    return {**result,'candidateCount':count,'anchorCount':len(positions),
        'eventPrefixStatus':event_status,
        'coverageStatus':'unsupported' if count==0 else 'ambiguous' if count>1 else 'unique'}


def join_and_frame(ledger, stream, *, stderr):
    by_path={row['virtualPath']:row for row in ledger};seen=set();results=[]
    if len(by_path)!=len(ledger):vfs._fail('duplicate-buff-ledger',source='join')
    for index,row in enumerate(stream):
        path=row.get('fileName')
        if not isinstance(path,str) or path not in by_path:vfs._fail('unexpected-stream-identity',source=f'stream[{index}]',actual=path)
        if path in seen:vfs._fail('duplicate-stream-identity',source=path)
        seen.add(path);identity=by_path[path]
        if (row.get('blockType'),row.get('blockTypeValue'))!=('JsonData',19):vfs._fail('stream-block-mismatch',source=path)
        encoded=row.get('dataBase64')
        if not isinstance(encoded,str):vfs._fail('stream-base64-missing',source=path)
        try:data=base64.b64decode(encoded,validate=True)
        except ValueError as exc:vfs._fail('stream-base64-invalid',source=path,actual=str(exc))
        length=vfs._require_int(row.get('length'),source=path+'.length',minimum=1)
        if len(data)!=length or length!=identity['length']:vfs._fail('stream-length-mismatch',source=path,expected=identity['length'],actual=[length,len(data)])
        md5=hashlib.md5(data).hexdigest().upper()
        if md5!=identity['recomputedFileDataMd5']:vfs._fail('stream-ledger-md5-mismatch',source=path,expected=identity['recomputedFileDataMd5'],actual=md5)
        try:framed=frame_candidates(data,source=path)
        except (ValueError,IndexError,KeyError,OverflowError,struct.error) as exc:
            framed={'coverageStatus':'failed','wholeSchemaExact':False,'candidateCount':0,
                'diagnostic':getattr(exc,'diagnostic',{'source':path,'offset':None,'expected':'bounded suffix-candidate reader','actual':f'{type(exc).__name__}: {exc}'})}
        results.append({'identity':identity,'logicalSha256':hashlib.sha256(data).hexdigest().upper(),**framed})
    missing=sorted(set(by_path)-seen)
    if missing:vfs._fail('stream-missing-identities',source='BuffData stream',actual=missing[:10])
    matches=re.findall(r'(?m)^Streamed ([0-9]+) files\s*$',stderr)
    if len(matches)!=1 or int(matches[0])!=len(stream):vfs._fail('stream-terminal-count-mismatch',source='BuffData stream',expected=len(stream),actual=matches)
    return sorted(results,key=lambda row:row['identity']['virtualPath'])


def _stream_command(cli_path: Path, outer) -> list[str]:
    """Own the BuffData stream request instead of mutating another family's."""
    return [
        str(cli_path.resolve()), 'stream',
        '--streaming-assets', str(outer['primaryAssets']),
        '--fallback-assets', str(outer['fallbackAssets']),
        '--block-type', 'json-data',
        '--verify-md5',
        '--file-regex', PATTERN.pattern,
    ]


def _read_stream_rows(command: list[str]) -> tuple[list[dict], str]:
    process = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', check=False)
    rows = []
    for line_number, line in enumerate(process.stdout.splitlines(), 1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            vfs._fail('stream-json-invalid', source='AnimeStudio stream stdout', offset=line_number, actual=str(exc))
        if not isinstance(row, dict):
            vfs._fail('stream-row-not-object', source='AnimeStudio stream stdout', offset=line_number, actual=type(row).__name__)
        rows.append(row)
    if process.returncode != 0:
        vfs._fail('stream-process-failed', source=command[0], expected=0,
                  actual={'returnCode': process.returncode, 'stderr': process.stderr[-4000:]})
    return rows, process.stderr


def build_current_census(*,outer_path,ledger_path,cli_path,expected_input_set_sha256,outputs=()):
    expected=expected_input_set_sha256.upper()
    outer,_,files,provenance=vfs._read_outer_and_ledger(outer_path,ledger_path,expected_input_set_sha256=expected)
    selected=select_rows(files,expected_input=expected)
    def snapshot():
        return {'selectedChunkFingerprints':vfs._chunk_fingerprints(selected),
            'selectedChunkResolution':vfs._chunk_selection_snapshot(selected,outer),
            'streamToolFingerprints':vfs._stream_tool_snapshot(cli_path),
            'parser':vfs._parser_source_snapshots(),'corpusGate':vfs._fingerprint(Path(__file__))}
    before=snapshot()
    if os.path.normcase(str(cli_path.resolve())) not in {os.path.normcase(str(Path(r['path']).resolve())) for r in provenance['buildFingerprints']}:
        vfs._fail('stream-cli-not-in-outer-build-fingerprints',source=str(cli_path))
    protected=[outer_path,ledger_path,Path(outer['primaryAssets']),Path(outer['fallbackAssets'])]
    # Many logical files share a chunk; protect every distinct physical input once.
    protected += [Path(path) for path in sorted({r['physicalChunkPath'] for r in files if r.get('physicalChunkPath')})]
    for group in (provenance['sourceFingerprints'],provenance['buildFingerprints'],before['streamToolFingerprints'],before['parser']):
        protected += [Path(r['path']) for r in group]
    def guard():
        for output in outputs:vfs._guard_output_path(output,protected+[p for p in outputs if p!=output])
        if len({str(p.resolve()) for p in outputs})!=len(outputs):vfs._fail('duplicate-output',source='BuffData outputs')
    guard()
    stream,stderr=_read_stream_rows(_stream_command(cli_path,outer))
    rows=join_and_frame(selected,stream,stderr=stderr)
    _,_,end_files,end_provenance=vfs._read_outer_and_ledger(outer_path,ledger_path,expected_input_set_sha256=expected)
    after=snapshot()
    comparisons={'outer':(provenance,end_provenance),'selectedLedger':(selected,select_rows(end_files,expected_input=expected))}
    comparisons.update({key:(value,after[key]) for key,value in before.items()})
    for role,(old,new) in comparisons.items():
        if old!=new:
            vfs._fail('buff-corpus-input-drift',source='BuffData census.'+role,
                expected=vfs._canonical_sha256(old),actual=vfs._canonical_sha256(new))
    guard();counts=Counter(row['coverageStatus'] for row in rows)
    prefix_counts=Counter(c['prefixProbe']['readerStatus'] for row in rows for c in row.get('candidates',[])
        if c.get('prefixProbe') is not None)
    event_counts=Counter(row.get('eventPrefixStatus','failed') for row in rows)
    categories={status:Counter(c['currentEventPrefix']['diagnostic']['category']
        for row in rows for c in row.get('candidates',[])
        if c.get('currentEventPrefix') and c['currentEventPrefix']['status']==status)
        for status in ('failed','unsupported')}
    event_summary={'total':len(rows),**{s:event_counts[s] for s in ('success','failed','unsupported','ambiguous')},
        'failureCategories':{s:dict(sorted(v.items())) for s,v in categories.items()},
        'boundary':'Success means the supported anonymous first collection ended before its candidate anchor. Scalar spans plus an explicit physical-file remainder tile EOF; the remainder is opaque, not decoded. Unknown unions stop at their first byte. No legacy names or whole-schema success.'}
    failed=bool(counts['failed'] or event_counts['failed'])
    return {'format':'animestudio-buffdata-current-vfs-corpus','schemaVersion':1,
        'inputSetSha256':expected,'status':'failed' if failed else 'complete',
        'publicationEligible':not failed,'wholeSchemaExact':False,
        'provenance':{**provenance,**before},'evidenceBoundary':BOUNDARY,
        'summary':{'filesSelected':len(selected),'filesSucceeded':counts['unique']+counts['ambiguous'],
            'filesFailed':counts['failed'],'filesUnsupported':counts['unsupported'],
            'filesUnique':counts['unique'],'filesAmbiguous':counts['ambiguous'],
            'filesWithMultipleAnchors':sum(row.get('anchorCount',0)>1 for row in rows),
            'acceptedSuffixPrefixStatusCounts':dict(sorted(prefix_counts.items())),
            'currentEventPrefix':event_summary,
            'logicalBytes':sum(row['length'] for row in selected)},
        'identitySetSha256':vfs._canonical_sha256([{'identity':r['identity'],'logicalSha256':r['logicalSha256']} for r in rows]),'files':rows}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--outer-summary',type=Path,default=vfs.DEFAULT_OUTER)
    parser.add_argument('--outer-ledger',type=Path,default=vfs.DEFAULT_LEDGER)
    parser.add_argument('--cli',type=Path,default=vfs.DEFAULT_CLI)
    parser.add_argument('--expected-input-set-sha256',required=True)
    parser.add_argument('--output-json',type=Path,required=True)
    parser.add_argument('--output-md',type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        report=build_current_census(outer_path=args.outer_summary,ledger_path=args.outer_ledger,
            cli_path=args.cli,expected_input_set_sha256=args.expected_input_set_sha256,
            outputs=(args.output_json,args.output_md))
    except vfs.CensusGateError as exc:
        print(json.dumps({'status':'failed','diagnostic':exc.diagnostic}));return 1
    vfs._atomic_write_json(args.output_json,report)
    args.output_md.parent.mkdir(parents=True,exist_ok=True)
    args.output_md.write_text('# BuffData current VFS corpus\n\n'+report['inputSetSha256']+'\n\n'+
        json.dumps(report['summary'],ensure_ascii=False)+'\n\n'+BOUNDARY+'\n',encoding='utf-8')
    print(json.dumps({'status':report['status'],'summary':report['summary']}))
    return int(report['status']=='failed')


if __name__=='__main__':raise SystemExit(main())
