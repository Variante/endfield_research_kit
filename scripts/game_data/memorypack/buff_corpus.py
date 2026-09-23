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

from scripts.game_data.memorypack import corpus_gate as vfs
from scripts.game_data.memorypack.buff import (
    buff_post_id_result_is_exact_tail,
    decode_buff_post_id_prefix_at,
    decode_buff_pre_id_modifier_prefix,
)
from scripts.game_data.memorypack.buff_actions import event_prefix
from scripts.game_data.memorypack.buff_icon_config import validate_current_native_contract
from scripts.game_data.memorypack import buff_named_schema
from scripts.game_data.memorypack.buff_residual_actions import (
    frame_buff_named_middle,
    root_continuation,
    validate_current_native_contract as validate_residual_native_contract,
)
from scripts.game_data import buff_frontiers_native as buff_frontiers
from scripts.common import canonical_json_sha256

PREFIX='Data/Json/BuffData/'
PATTERN=re.compile(r'^Data/Json/BuffData/[^/]+[.]json$')
BOUNDARY=('Authenticated current VFS logical bytes and the current generated 30-field wrapper order. '
          'The first six fields and supported middle fields advance real cursors; the accepted id marker '
          'starts the named field-15-to-29 suffix that closes at EOF. Positive modifier lists and nested '
          'damage/heal modifier and action bodies remain explicit opaque or unsupported boundaries. The nested '
          '19-member iconConfig is exact under its current-build native contract. Runtime behavior and '
          'whole-schema exactness are not promoted.')


def _profile_boundary(profile, *, file_length):
    if profile is None:return None
    if not all(key in profile for key in ('status','consumedEnd','readLimit')):return profile
    status=profile['status']
    profile['boundaryClass']={'supported-prefix':'structural-prefix',
        'unsupported':'unsupported','failed':'failed'}.get(status,'unsupported')
    cursor=profile['consumedEnd'];hard_limit=profile['readLimit']
    profile['parserCursor']=cursor;profile['hardLimit']=hard_limit
    opaque=[]
    if cursor<hard_limit:opaque.append({'start':cursor,'end':hard_limit,'kind':'opaque-before-hard-limit'})
    if hard_limit<file_length:opaque.append({'start':hard_limit,'end':file_length,'kind':'opaque-after-hard-limit'})
    profile['opaqueByteRanges']=opaque
    for record in profile.get('completedRecords',[]):
        if record.get('kind')=='union':
            record['boundaryClass']='exact-closed'
            record['hardLimit']=hard_limit
    profile['exactClosedActionRecords']=sum(
        record.get('kind')=='union' for record in profile.get('completedRecords',[]))
    return profile


def select_rows(rows, *, expected_input):
    return vfs.family_rows(rows,expected_input=expected_input,prefix=PREFIX,pattern=PATTERN,label='buff')


def frame_candidates(data: bytes, *, source: str) -> dict:
    result={'wholeSchemaExact':False,'candidates':[],'candidateCount':0,
            'eventPrefixStatus':'unsupported','rootContinuationStatus':'unsupported'}
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
        prefix_probe=None;current_prefix=None;continuation=None;named_middle=None;named_suffix=None
        if accepted:
            current_prefix=event_prefix(data,source=source,limit=at)
            _profile_boundary(current_prefix,file_length=len(data))
            if current_prefix['status']=='supported-prefix':
                continuation=root_continuation(
                    data,source=source,start=current_prefix['consumedEnd'],limit=at,
                )
                _profile_boundary(continuation,file_length=len(data))
                if continuation['status']=='supported-prefix':
                    named_middle=frame_buff_named_middle(
                        data,continuation['consumedEnd'],at,
                    )
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
            named_suffix={
                'status':'named-exact-to-eof',
                'startOffset':at,
                'endOffset':len(data),
                'namedFieldOrder':[
                    'id','igniteEventAction','ignoreCooldownWhenAdding','ignoreTagImmune',
                    'lifeType','maxTriggerCnt','onlyUseSelfTimeDilation','poiseModifier',
                    'shieldConfigs','stackingSettings','tagsAfterTriggerExtendBuffAction',
                    'timelineActions','triggerInterval','useTimeDilationDt',
                    'waitFirstTriggerInterval',
                ],
                'opaqueNestedRanges':buff_named_schema.suffix_opaque_ranges(decoded,length=len(data)),
                'fieldOrderSource':'current generated BuffDataForMemoryPack setter order',
                'opaqueNestedFields':[
                    name for name,key in (
                        ('igniteEventAction','igniteEventActionBodyStatus'),
                        ('poiseModifier','poiseModifierBodyStatus'),
                        ('shieldConfigs','shieldConfigsBodyStatus'),
                        ('timelineActions','timelineActionsBodyStatus'),
                    ) if decoded.get(key)
                ] + (['stackingSettings.stackEffects']
                     if (decoded.get('stackingSettings') or {}).get('stackEffectsCount', 0) > 0 else []),
                'boundary':(
                    'The unique accepted id marker and sequential named suffix reader close at EOF; '
                    'reported opaque child bodies do not gain nested field semantics.'
                ),
            }
        selected_profile=continuation or current_prefix
        candidate_class=(selected_profile or {}).get('boundaryClass','rejected-anchor')
        result['candidates'].append({'anchorOffset':at,'suffixStart':at+len(marker),
            'readerStatus':decoded.get('status'),'readerTailStatus':decoded.get('tailParseStatus'),
            'readerAcceptedThroughEof':accepted,'readerEndOffset':end,
            'opaquePrefixRange':[1,at],
            'readerInternalOpaqueRangesCertified':False,
            'boundaryClass':candidate_class,
            'startOffset':selected_profile.get('startOffset',0) if selected_profile else 0,
            'hardLimit':at,
            'parserCursor':selected_profile.get('parserCursor') if selected_profile else None,
            'byteRanges':selected_profile.get('ranges',[]) if selected_profile else [],
            'opaqueByteRanges':selected_profile.get('opaqueByteRanges',[]) if selected_profile else [],
            'exactClosedActionRecords':sum(profile.get('exactClosedActionRecords',0)
                for profile in (current_prefix,continuation) if profile),
            'prefixProbe':prefix_probe,
            'currentEventPrefix':current_prefix,
            'currentRootContinuation':continuation,
            'currentNamedMiddle':named_middle,
            'currentNamedSuffix':named_suffix,
            'diagnostic':decoded.get('tailParseError') or decoded.get('error')})
        candidate=result['candidates'][-1]
        if accepted:
            candidate['opaqueByteRanges']=buff_named_schema.compose_opaque_ranges(candidate,length=len(data))
            candidate['namedSchemaReceipt']=buff_named_schema.named_schema_receipt(
                candidate,source=source,length=len(data))
    count=sum(row['readerAcceptedThroughEof'] for row in result['candidates'])
    current=[c['currentEventPrefix'] for c in result['candidates'] if c['currentEventPrefix'] is not None]
    event_status=('failed' if any(c['status']=='failed' for c in current) else
                  'ambiguous' if count>1 else
                  'success' if count==1 and current[0]['status']=='supported-prefix' else 'unsupported')
    continuations=[c['currentRootContinuation'] for c in result['candidates'] if c['currentRootContinuation'] is not None]
    root_status=('failed' if event_status=='failed' or any(c['status']=='failed' for c in continuations) else
                 'ambiguous' if count>1 else
                 'success' if count==1 and len(continuations)==1 and continuations[0]['status']=='supported-prefix' else 'unsupported')
    boundary_class=('failed' if root_status=='failed' else 'ambiguous' if root_status=='ambiguous' else
                    'structural-prefix' if root_status=='success' else 'unsupported')
    accepted_candidates=[candidate for candidate in result['candidates'] if candidate['readerAcceptedThroughEof']]
    named_outer_frame=(
        len(accepted_candidates)==1
        and (accepted_candidates[0].get('currentNamedMiddle') or {}).get('status')=='named-through-iconConfig'
        and (accepted_candidates[0].get('currentNamedMiddle') or {}).get('iconConfigStatus')=='exact'
        and (accepted_candidates[0].get('currentNamedSuffix') or {}).get('status')=='named-exact-to-eof'
    )
    return {**result,'candidateCount':count,'anchorCount':len(positions),
        'eventPrefixStatus':event_status,
        'rootContinuationStatus':root_status,
        'namedOuterFrameStatus':'named_exact_frame' if named_outer_frame else 'bounded_partial',
        'boundaryClass':boundary_class,
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
        logical_sha=hashlib.sha256(data).hexdigest().upper()
        for candidate in framed.get('candidates',[]):
            context={'inputSetSha256':identity['inputSetSha256'],
                'logicalFileIdentity':identity['virtualPath'],'logicalSha256':logical_sha,
                'startOffset':candidate['startOffset'],'hardLimit':candidate['hardLimit']}
            candidate['boundaryContext']=context
            for profile in (candidate.get('currentEventPrefix'),candidate.get('currentRootContinuation')):
                if profile is not None:
                    profile['boundaryContext']=context
                    for record in profile.get('completedRecords',[]):
                        if record.get('boundaryClass')=='exact-closed':
                            record['boundaryContext']={**context,
                                'recordRange':[record['start'],record['end']]}
        results.append({'identity':identity,'logicalSha256':logical_sha,**framed})
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


def boundary_evidence_summary(rows):
    candidates=[candidate for row in rows for candidate in row.get('candidates',[])]
    exact_closed=sum(candidate.get('exactClosedActionRecords',0) for candidate in candidates)
    structural_prefix=sum(candidate.get('boundaryClass')=='structural-prefix' for candidate in candidates)
    opaque_bytes=sum(span['end']-span['start'] for candidate in candidates
        for span in candidate.get('opaqueByteRanges',[]))
    return {'exactClosedActionRecords':exact_closed,
        'structuralPrefixCandidates':structural_prefix,
        'opaqueBytesByCandidate':opaque_bytes,
        'unsupportedCandidates':sum(candidate.get('boundaryClass')=='unsupported' for candidate in candidates),
        'failedCandidates':sum(candidate.get('boundaryClass')=='failed' for candidate in candidates),
        'rejectedAnchorCandidates':sum(candidate.get('boundaryClass')=='rejected-anchor' for candidate in candidates),
        'ambiguousFiles':sum(row.get('boundaryClass')=='ambiguous' for row in rows),
        'boundary':'Ranges are zero-based and half-open. Exact closures count completed anonymous union records only. Structural-prefix candidates '
        'do not establish whole-record or whole-file completion. Opaque bytes are composed unresolved ranges after '
        'downstream cursor coverage, retaining opaque nested bodies; stage-local remainders are not added again. '
        'Anonymous framed interiors remain separate naming obligations. Alternate ambiguous candidates are counted separately. Rejected filename anchors '
        'with no current parser run are reported separately from unsupported parser results.'}


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
    native_validation=validate_current_native_contract()
    residual_validation=validate_residual_native_contract()
    expected_frontier_rows={
        'residual':[0x21,0x100,0x15F],
        'frontier6':[0x2A,0x9E,0xD7,0xE4,0x111,0x12F,0x18D],
        'frontier7':[0xFF,0x106,0x109,0x149,0x162,0x170,0x173,0x195],
        'frontier8':[0x09,0x14,0x1E,0x2D,0x4D,0x5F,0xAF,0xC2,0xD9,0x107,0x10D,0x114],
        'frontier9':[0x1D,0x82,0x97,0xB5,0xB8,0xBE,0xC8,0xD1,0xDD,
                     0xE5,0xE9,0x104,0x108,0x11B,0x141,0x143,0x17D,0x17E,0x191],
    }
    frontier_validations={}
    for name,expected_rows in expected_frontier_rows.items():
        source=str(buff_frontiers.contract_path(name))
        rows,validation=buff_frontiers.load_rows(name)
        frontier_validations[name]=validation
        if validation.get('status')!='validated':
            vfs._fail(f'buff-{name}-native-validation',source=source,expected='validated',actual=validation)
        if sorted(rows)!=expected_rows:
            vfs._fail(f'buff-{name}-row-set',source=source,expected=expected_rows,actual=sorted(rows))
    outer,_,files,provenance=vfs._read_outer_and_ledger(outer_path,ledger_path,expected_input_set_sha256=expected)
    selected=select_rows(files,expected_input=expected)
    def snapshot():
        return {'selectedChunkFingerprints':vfs._chunk_fingerprints(selected),
            'selectedChunkResolution':vfs._chunk_selection_snapshot(selected,outer),
            'streamToolFingerprints':vfs._stream_tool_snapshot(cli_path),
            'parser':vfs._parser_source_snapshots(Path(__file__)),
            'buffFrontiersNative':[vfs._fingerprint(Path(buff_frontiers.__file__))]+[
                vfs._fingerprint(spec.path) for spec in buff_frontiers.FRONTIERS.values()],
            'buffNamedSchema':vfs._fingerprint(Path(buff_named_schema.__file__)),
            'corpusGate':vfs._fingerprint(Path(__file__))}
    before=snapshot()
    if os.path.normcase(str(cli_path.resolve())) not in {os.path.normcase(str(Path(r['path']).resolve())) for r in provenance['buildFingerprints']}:
        vfs._fail('stream-cli-not-in-outer-build-fingerprints',source=str(cli_path))
    protected=[outer_path,ledger_path,Path(outer['primaryAssets']),Path(outer['fallbackAssets'])]
    protected.append(Path(buff_named_schema.__file__))
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
                expected=canonical_json_sha256(old),actual=canonical_json_sha256(new))
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
    root_counts=Counter(row.get('rootContinuationStatus','failed') for row in rows)
    root_categories={status:Counter((c.get('currentRootContinuation') or c.get('currentEventPrefix'))['diagnostic']['category']
        for row in rows for c in row.get('candidates',[])
        if (c.get('currentRootContinuation') or c.get('currentEventPrefix'))
        and (c.get('currentRootContinuation') or c.get('currentEventPrefix'))['status']==status)
        for status in ('failed','unsupported')}
    root_summary={'total':len(rows),**{s:root_counts[s] for s in ('success','failed','unsupported','ambiguous')},
        'failureCategories':{s:dict(sorted(v.items())) for s,v in root_categories.items()},
        'boundary':'Success means only a structural prefix: a supported first collection followed by selected root members 2-6. '
        'Continuation ranges begin at currentEventPrefix.consumedEnd. The remaining physical-file bytes '
        'stay opaque; neither suffix-anchor ownership nor whole-schema EOF is established.'}
    named_middle_counts=Counter(
        (candidate.get('currentNamedMiddle') or {}).get('status','not-reached')
        for row in rows for candidate in row.get('candidates',[])
        if candidate.get('readerAcceptedThroughEof')
    )
    named_middle_stops=Counter(
        (candidate.get('currentNamedMiddle') or {}).get('diagnostic','unknown').split('=')[0]
        for row in rows for candidate in row.get('candidates',[])
        if candidate.get('readerAcceptedThroughEof')
        and (candidate.get('currentNamedMiddle') or {}).get('status')=='unsupported'
    )
    named_middle_summary={
        'total':len(rows),
        'namedThroughIconConfig':named_middle_counts['named-through-iconConfig'],
        'exactIconConfig':sum(
            (candidate.get('currentNamedMiddle') or {}).get('iconConfigStatus')=='exact'
            for row in rows for candidate in row.get('candidates',[])
            if candidate.get('readerAcceptedThroughEof')
        ),
        'unsupported':named_middle_counts['unsupported'],
        'notReached':named_middle_counts['not-reached'],
        'stopCategories':dict(sorted(named_middle_stops.items())),
        'boundary':(
            'Supported rows name fields 6-14. Every reached field advances an exact cursor; iconConfig '
            'uses its authenticated current-build 19-member reader and ends at the independently accepted id marker.'
        ),
    }
    failed=bool(counts['failed'] or event_counts['failed'] or root_counts['failed'])
    return {'format':'animestudio-buffdata-current-vfs-corpus','schemaVersion':1,
        'inputSetSha256':expected,'status':'failed' if failed else 'complete',
        'publicationEligible':not failed,'wholeSchemaExact':False,
        'provenance':{**provenance,**before,
            'buffIconConfigNativeValidation':native_validation,
            'buffResidualActionsNativeValidation':residual_validation,
            'buffFrontiersNativeValidation':frontier_validations},'evidenceBoundary':BOUNDARY,
        'summary':{'filesSelected':len(selected),'filesSucceeded':counts['unique']+counts['ambiguous'],
            'filesFailed':counts['failed'],'filesUnsupported':counts['unsupported'],
            'filesUnique':counts['unique'],'filesAmbiguous':counts['ambiguous'],
            'filesWithMultipleAnchors':sum(row.get('anchorCount',0)>1 for row in rows),
             'filesWithNamedOuterFrame':sum(
                 row.get('namedOuterFrameStatus')=='named_exact_frame' for row in rows
             ),
             'acceptedSuffixPrefixStatusCounts':dict(sorted(prefix_counts.items())),
             'currentEventPrefix':event_summary,
             'currentRootContinuation':root_summary,
             'currentNamedMiddle':named_middle_summary,
             'byteBoundaryEvidence':boundary_evidence_summary(rows),
             'namedSchemaReceipts':buff_named_schema.summarize_receipts(rows),
             'logicalBytes':sum(row['length'] for row in selected)},
        'identitySetSha256':canonical_json_sha256([{'identity':r['identity'],'logicalSha256':r['logicalSha256']} for r in rows]),'files':rows}


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
