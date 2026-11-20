"""Build conditional simulator tail cases from admitted observed request pairs.

These cases start at the recorded AllowNext boundary. They do not reconstruct
missing construction operands or claim independent native/transport validation.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path


def need(ok, message):
    if not ok:
        raise ValueError('battleInputRefreshCases: '+message)


def build_cases(inspection, tail, tick, layout):
    need(inspection.get('status')=='observed', 'observed inspection required')
    facts=inspection.get('sourceContext',{}).get('inspection',{}).get('receiptFacts',{})
    need(all(facts.get(k)is True for k in ('captureCompleteClaim','healthyClaim','allJournalRowsAccounted',
        'strictTransitionReceiptsConsistent','nativeInputHashesBoundToProfile')) and
        facts.get('collectionBoundFailureMarkers')==[], 'complete healthy bound receipt required')
    need(tail.get('status')=='validated-conditional-fragments' and tick.get('status')=='validated',
         'matching conditional tail and prior validated Tick evidence required')
    files=inspection['sourceContext']['nativeInputs']
    for proof in (tail,tick):
        for name,role in (('GameAssembly.dll','gameAssembly'),('global-metadata.dat','metadata')):
            need(proof['nativeInputs'][name].lower()==files[role]['sha256'].lower(),'native input mismatch')
    rules=tail['rules']
    need(rules.get('scope')=='successful-postconstruction-only' and
         rules.get('deltaArgumentsFloat32Hex')==['00000000']*3 and
         rules.get('refreshReturnsTrueAfterDispatch')is True, 'unsupported tail rule')
    need(tick['rules']['tickDispatchesSkill']is False, 'Tick dispatch boundary differs')
    threshold=int.from_bytes(bytes.fromhex(tick['tickExpiryThreshold']['bitsHex']),'little')
    site=tail['callSites']['tickAllow']['returnRva']
    children={};cases=[];evidence=[];skipped=0
    for o in inspection['observations']:
        if o['hook']=='battle.Combo.AllowNext':
            children.setdefault((o['threadId'],o['enter']['parentInvocationId']),[]).append(o)
    def raw(event):
        fs=[f for f in event['fields'] if f['label']=='requestSnapshot']
        need(len(fs)==1 and fs[0]['state']==1,'exact request bytes required')
        return bytes.fromhex(fs[0]['rawHex'])
    for parent in inspection['observations']:
        if parent['hook']!='battle.Combo.Refresh':continue
        if parent.get('booleanReturn')is False:
            skipped+=1;continue
        need(parent.get('booleanReturn')is True, 'normal Boolean refresh return required')
        cs=children.get((parent['threadId'],parent['invocationId']),[])
        need(len(cs)==1, 'one explicit direct AllowNext child required')
        child=cs[0];before=child['cacheSnapshots']['before'];after=parent['cacheSnapshots']['after']
        need(parent['enter']['sequence']<child['enter']['sequence']<child['exit']['sequence']<parent['exit']['sequence'],
             'child enclosure differs')
        need(child['enter']['callerGameAssemblyRva']==site and
             parent['enter']['rawArgs'][0]==child['enter']['rawArgs'][0], 'Tick callsite or controller differs')
        need(before['present']is True and after['present']is True and type(before['inputDataPresent'])is bool and
             child['enter']['rawArgs'][1]==before['nextSkillIdPointer'], 'selected retained request binding differs')
        allowed=child.get('booleanReturn');need(type(allowed)is bool,'observed AllowNext Bool required')
        a,b,z=raw(child['enter']),raw(child['exit']),raw(parent['exit'])
        need(a==b and len(a)==layout['byteCount'],'child snapshot stability/extent differs')
        expected_bytes=bytearray(a);expected_bytes[layout['offsets']['allowToCastNextSkill']]=int(allowed)
        need(bytes(expected_bytes)==z,'return copyback differs beyond selected allow byte')
        expected=dict(refreshReturned=True,tickRequested=True,tickTimeArgumentsRaw32=[0,0,0],
            tick=dict(requestPresent=True,remainingRaw32=int.from_bytes(bytes.fromhex(after['remainingTimeBits']),'little'),
                allowToCastNextSkill=after['allowToCastNextSkill'],allowCheckRequested=True,
                disposeInputRequested=False,requestCleared=False,dispatchRequested=False,playerCommandAcceptanceProved=False),
            runtimeDispatchSelectionProved=False,playerCommandAcceptanceProved=False)
        cases.append(dict(id='refresh-'+str(parent['invocationId']),operation='refresh-constructed-request-tail',
            inputs=dict(request_present=True,remaining_single=dict(raw32=int.from_bytes(bytes.fromhex(before['remainingTimeBits']),'little')),
                expiry_threshold_single=dict(raw32=threshold),allow_next_result=allowed,input_present=before['inputDataPresent']),expected=expected))
        evidence.append(dict(caseId=cases[-1]['id'],allowInvocationId=child['invocationId'],
            childCallsiteObserved=True,sameControllerObserved=True,wholeSnapshotConforms=True,
            virtualTargetLoadObserved=False,receiverContinuityProved=False))
    need(bool(cases),'no selected successful tail cases')
    return dict(schema='endfield.conditional-timing-cases.v1',conditions=dict(
        original_path='Selected Refresh successful-construction tail and ordinary Combo Tick, normal returns, generic dispatch branch and carrier continuity are explicit premises; live virtual target and IFix are not proved.',
        operand_binding='Exact direct-child AllowNext callsite/controller/string-pointer and paired raw request snapshots from admitted inspection; construction helper inputs remain unobserved.',
        delta_and_sample_sources='Three zero Single arguments from selected tail fragment; caller-receiver path remains conditional. Expiry evidence reuses the matching previously validated Tick contract.',
        precision='RNE IEEE754 Single subtraction/comparison; all recorded times supplied as raw32.'),
        cases=cases,caseEvidence=evidence,excludedFalseRefresh=skipped,
        boundary='Conditional postconstruction model regression only; no full input replay, runtime readiness or cross-frame request admission.')


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('inspection','tail-evidence','tick-evidence','manifest','output'):
        parser.add_argument('--'+key,type=Path,required=True)
    args=parser.parse_args(argv)
    from scripts.repo_paths import REPO_ROOT
    need(args.output.resolve().is_relative_to(REPO_ROOT/'reports'),'output must be under reports/')
    paths=[args.inspection,args.tail_evidence,args.tick_evidence,args.manifest]
    need(args.output.resolve()not in [p.resolve()for p in paths],'output must not replace inputs')
    sources=[];docs=[]
    for path in paths:
        need(path.stat().st_size<=128*1024**2,'input byte budget exceeded')
        raw=path.read_bytes();need(len(raw)<=128*1024**2,'input grew beyond budget')
        sources.append((path,raw));docs.append(json.loads(raw))
    from scripts.game_data.battle_input_capture_sources import REQUEST,validate_read_layouts
    layout=docs[3]['battleReadLayouts'];validate_read_layouts(layout)
    need(docs[3]['files']==docs[0]['sourceContext']['nativeInputs'],'manifest native inputs differ')
    result=build_cases(*docs[:3],layout['values'][REQUEST])
    result['sources']=[dict(path=str(p.resolve()),sha256=hashlib.sha256(raw).hexdigest())for p,raw in sources]
    need(all(p.read_bytes()==raw for p,raw in sources),'source changed during case projection')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(cases=len(result['cases']),excludedFalseRefresh=result['excludedFalseRefresh'])))
    return 0


if __name__=='__main__':raise SystemExit(main())
