"""Finite pointer/name and synchronous request joins over an admitted inspection.

Historical pointer matches remain candidates. This module does not replay the
request cache or infer async delivery, object lifetime, input acceptance or hits.
"""
from __future__ import annotations
import argparse,collections,hashlib,json
from pathlib import Path
SCHEMA='endfield.battle-input-request-links.v1'
REQUIRED_FACTS=('captureCompleteClaim','healthyClaim','allJournalRowsAccounted','strictTransitionReceiptsConsistent','nativeInputHashesBoundToProfile')

def _require(ok,detail):
    if not ok:raise ValueError(detail)

def _fields(row):
    result={}
    for f in row.get('fields',[]):
        if f.get('state')==1 and type(f.get('state'))is int and f.get('stateName','exact')=='exact':
            key=f['label'];_require(key not in result,'duplicate exact field label');result[key]=f.get('value')
    return result

def _id(value):return type(value)is int and 0<value<2**64

def project_request_links(inspection,*,max_observations=50000,max_candidate_links=200000):
    _require(inspection.get('schema')=='endfield.battle-input-inspection.v1'and inspection.get('status')=='observed','requires admitted observed inspection')
    facts=inspection.get('sourceContext',{}).get('inspection',{}).get('receiptFacts',{})
    _require(all(facts.get(k)is True for k in REQUIRED_FACTS),'requires healthy complete accounted receipt and bound native inputs')
    _require(facts.get('collectionBoundFailureMarkers')==[],'collection failure markers are missing or present')
    _require(not inspection.get('diagnostics'),'inspection diagnostics present')
    obs=inspection['observations'];_require(type(max_observations)is int and type(max_candidate_links)is int and 0<len(obs)<=max_observations and max_candidate_links>0,'observation/candidate budget invalid or exceeded');byid={};rows=[];seen_sequences=set();candidate_links=0
    for o in obs:
        e,x=o['enter'],o.get('exit');_require(type(o['threadId'])is int and type(o['invocationId'])is int and o['invocationId']>0,'ordinary invocation identity required');key=(o['threadId'],o['invocationId'])
        _require(key not in byid and x is not None,'duplicate/open invocation')
        _require(e.get('phase')=='enter'and x.get('phase')=='return'and e['hook']==x['hook']==o['hook']and e['threadId']==x['threadId']==o['threadId']and e['invocationId']==x['invocationId']==o['invocationId'],'pair identity mismatch')
        receipt=x.get('invocationReceipt',{})
        _require(receipt.get('returnedNormally')is True and receipt.get('entrySequence')==e['sequence']and e['sequence']<x['sequence'],'normal pair receipt mismatch')
        for event in(e,x):
            _require(type(event['sequence'])is int and event['sequence']not in seen_sequences,'duplicate/noninteger sequence');seen_sequences.add(event['sequence'])
        r=dict(id=o['invocationId'],thread=o['threadId'],hook=o['hook'],enter=e['sequence'],exit=x['sequence'],receiver=e['rawArgs'][0],before=_fields(e),after=_fields(x),args=e['rawArgs'],returned=x.get('returnValue'),cache=o.get('cacheSnapshots',{}),parent=e.get('parentInvocationId',0))
        byid[key]=r;rows.append(r)
    for r in rows:
        ancestors=[];p=r['parent'];seen=set()
        while p:
            _require(p not in seen,'ancestry cycle');seen.add(p);a=byid.get((r['thread'],p));_require(a is not None and a['enter']<r['enter']<r['exit']<a['exit'],'invalid same-thread enclosure');ancestors.append(a);p=a['parent']
        r['ancestors']=ancestors;r['command']=next((a['id']for a in ancestors if a['hook']=='battle.Command.OnExecute'),None)
    rows.sort(key=lambda r:r['enter']);anchors=[];snapshots=[];costs=[];getters=[];befores=[]
    for r in rows:
        if r['hook']in('battle.Combo.AllowNext','battle.AbilitySystem.CanCastById'):
            ptr=r['args'][1];name=r['before'].get('skillId')
            if _id(ptr)and type(name)is str:anchors.append(dict(invocationId=r['id'],threadId=r['thread'],sequence=r['enter'],returnSequence=r['exit'],hook=r['hook'],pointer=ptr,text=name,returnedLow8=r['returned']&255 if type(r['returned'])is int else None,commandInvocationId=r['command']))
        for phase,key in(('before','enter'),('after','exit')):
            s=r['cache'].get(phase)
            if s is not None:
                _require(type(s.get('present'))is bool,'cache present must be explicit bool')
                if s['present']:_require(_id(s.get('nextSkillIdPointer')),'present cache needs nonnull exact pointer')
                snapshots.append(dict(invocationId=r['id'],threadId=r['thread'],sequence=r[key],hook=r['hook'],phase=phase,controllerPointer=r['receiver'],commandInvocationId=r['command'],snapshot=s))
        if r['hook']=='battle.Skill.CheckCost':costs.append(r)
        if r['hook']=='battle.Combo.NextSkillId':getters.append(r)
        if r['hook']=='battle.Ability.BeforeCast':befores.append(r)
    pointer_names={}
    for a in anchors:pointer_names.setdefault(a['pointer'],set()).add(a['text'])
    name_pointers={}
    for pointer,names in pointer_names.items():
        for name in names:name_pointers.setdefault(name,set()).add(pointer)
    # A visible Clear-after-absent is only an observed barrier, not proof that
    # an equal pointer before/after it denotes one request object or lifetime.
    barriers=[s for s in snapshots if s['hook']=='battle.Combo.Clear'and s['phase']=='after'and s['snapshot']['present']is False]
    links=[]
    for g in getters:
        ptr=g['returned'];_require(type(ptr)is int and 0<=ptr<2**64,'getter return must be raw reference identity')
        preceding=[s for s in snapshots if s['threadId']==g['thread']and s['controllerPointer']==g['receiver']and s['sequence']<g['enter']]
        barrier=max((s['sequence']for s in barriers if s['threadId']==g['thread']and s['controllerPointer']==g['receiver']and s['sequence']<g['enter']),default=0)
        candidates=[s for s in preceding if s['sequence']>barrier and s['snapshot']['present']and s['snapshot']['nextSkillIdPointer']==ptr]
        local=[s for s in candidates if g['command']is not None and s['commandInvocationId']==g['command']]
        local_anchors=[a for a in anchors if a['pointer']==ptr and a['threadId']==g['thread']and g['command']is not None and a['commandInvocationId']==g['command']and a['sequence']<g['enter']]
        candidate_links+=len(candidates)+len(local)+len(local_anchors)
        _require(candidate_links<=max_candidate_links,'candidate budget exceeded')
        links.append(dict(invocationId=g['id'],threadId=g['thread'],entrySequence=g['enter'],returnSequence=g['exit'],controllerPointer=g['receiver'],returnedPointer=ptr,textCandidates=sorted(pointer_names.get(ptr,set())),textAnchorInvocations=[a['invocationId']for a in anchors if a['pointer']==ptr],commandInvocationId=g['command'],lastObservedClearBarrierSequence=barrier,sameSegmentSnapshotCandidates=[dict(invocationId=s['invocationId'],phase=s['phase'],sequence=s['sequence'],allowToCastNextSkill=s['snapshot'].get('allowToCastNextSkill'))for s in candidates],sameCommandSnapshotCandidates=[dict(invocationId=s['invocationId'],phase=s['phase'],sequence=s['sequence'])for s in local],sameCommandExplicitStringArgumentInvocations=[a['invocationId']for a in local_anchors],pointerEqualityObserved=bool(local),requestIdentityProved=False,crossTickDeliveryProved=False))
    cast_links=[]
    for b in befores:
        skill=b['before'].get('skillIdentity');_require(_id(skill),'BeforeCast needs exact nonnull sourceSkill identity')
        historical=[c for c in costs if c['thread']==b['thread']and c['exit']<b['enter']and c['before'].get('skillIdentity')==skill]
        local=[c for c in historical if b['command']is not None and c['command']==b['command']]
        getter_local=[g for g in links if b['command']is not None and g['commandInvocationId']==b['command']and g['threadId']==b['thread']and g['returnSequence']<b['enter']]
        names=sorted({c['before']['skillId']for c in local if type(c['before'].get('skillId'))is str})
        historical_names={c['before']['skillId']for c in historical if type(c['before'].get('skillId'))is str}
        historical_getters=[g for g in links if g['threadId']==b['thread']and g['returnSequence']<b['enter']and historical_names&set(g['textCandidates'])]
        candidate_links+=len(historical)+len(historical_getters)+len(local)+len(getter_local)
        _require(candidate_links<=max_candidate_links,'candidate budget exceeded')
        cast_links.append(dict(invocationId=b['id'],threadId=b['thread'],entrySequence=b['enter'],commandInvocationId=b['command'],abilitySnapshot=b['before'],sameCommandCheckCostCandidates=[dict(invocationId=c['id'],skillIdentity=c['before'].get('skillIdentity'),skillInstId=c['before'].get('skillInstId'),skillId=c['before'].get('skillId'),returnedLow8=c['returned']&255 if type(c['returned'])is int else None)for c in local],historicalSkillPointerCheckCostInvocations=[c['id']for c in historical],historicalNameOnlyGetterCandidates=[dict(invocationId=g['invocationId'],controllerPointer=g['controllerPointer'],commandInvocationId=g['commandInvocationId'],returnedPointer=g['returnedPointer'],textIntersection=sorted(historical_names&set(g['textCandidates'])),controllerToSkillOwnerProved=False,lifetimeContinuityProved=False)for g in historical_getters],sameCommandGetterCandidates=[dict(invocationId=g['invocationId'],returnedPointer=g['returnedPointer'],textCandidates=g['textCandidates'],textIntersection=sorted(set(names)&set(g['textCandidates'])))for g in getter_local],synchronousCommonCommandObserved=bool(local and getter_local),requestToSkillTransferProved=False,acceptedInputProved=False))
    return dict(schema=SCHEMA,status='observed-links',boundary='Exact local pair/enclosure, reference-pointer and text equality observations; no async causality, unique request identity, object lifetime or replay.',inputAdmissionInherited=True,transportReproved=False,physicalInputComplete=False,fullInputExecutionChainProved=False,counts=dict(normalPairs=len(rows),stringArgumentAnchors=len(anchors),distinctStringPointers=len(pointer_names),nextSkillIdGetters=len(links),getterWithTextCandidates=sum(bool(g['textCandidates'])for g in links),getterWithSameCommandSnapshot=sum(bool(g['sameCommandSnapshotCandidates'])for g in links),getterWithMultipleSnapshotCandidates=sum(len(g['sameSegmentSnapshotCandidates'])>1 for g in links),checkCost=len(costs),beforeCast=len(cast_links),beforeCastWithSameCommandCostAndGetter=sum(b['synchronousCommonCommandObserved']for b in cast_links),observedClearAbsentBarriers=len(barriers)),cacheSnapshotObservations=snapshots,allowObservations=[dict(invocationId=r['id'],threadId=r['thread'],entrySequence=r['enter'],controllerPointer=r['receiver'],skillIdPointer=r['args'][1],skillId=r['before'].get('skillId'),returnedLow8=r['returned']&255 if type(r['returned'])is int else None,commandInvocationId=r['command'],snapshots=r['cache'])for r in rows if r['hook']=='battle.Combo.AllowNext'],pointerTextEvidence=anchors,pointerTextConflicts=[dict(pointer=p,texts=sorted(n))for p,n in pointer_names.items()if len(n)>1],equalTextDifferentPointers=[dict(text=n,pointers=sorted(p))for n,p in name_pointers.items()if len(p)>1],getterLinks=links,beforeCastLinks=cast_links,counterexamples=dict(getterWithoutSameCommandSnapshot=[g['invocationId']for g in links if not g['sameCommandSnapshotCandidates']],beforeCastWithoutSynchronousCommonCommand=[b['invocationId']for b in cast_links if not b['synchronousCommonCommandObserved']],getterAmbiguousText=[g['invocationId']for g in links if len(g['textCandidates'])!=1]),gaps=['Cache snapshots are non-atomic; observed clear barriers do not authenticate all intervening writes or request allocation.','Equal text does not prove equal managed string pointer; all conflicting/multiple matches are retained.','A shared synchronous command and matching fields do not prove a specific return value was passed into a cast helper.','No nearest-time match, synthesized state replay, absent-call rejection or cross-tick synchronous ancestry is used.'])

def inspect_request_links(path):
    path=Path(path);_require(path.stat().st_size<=256*1024*1024,'inspection byte budget exceeded');raw=path.read_bytes();_require(len(raw)<=256*1024*1024,'inspection byte budget exceeded');result=project_request_links(json.loads(raw));_require(path.read_bytes()==raw,'inspection source changed')
    result['source']=dict(path=str(path.resolve()),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest());return result

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--inspection',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args(argv)
    from scripts.repo_paths import REPO_ROOT
    p.error('output must be in reports/scratch/tmp')if not any(a.output.resolve().is_relative_to(REPO_ROOT/r)for r in('reports','scratch','tmp'))else None
    p.error('output must not replace inspection input')if a.output.resolve()==a.inspection.resolve()else None
    try:result=inspect_request_links(a.inspection)
    except(OSError,ValueError,KeyError,TypeError,IndexError)as error:result=dict(schema=SCHEMA,status='blocked',counts={},getterLinks=[],beforeCastLinks=[],diagnostics=[str(error)[:1200]])
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k]for k in('status','counts')}));return int(result['status']=='blocked')
if __name__=='__main__':raise SystemExit(main())
