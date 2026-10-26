"""Canonical short tags0/1/2 or FF with independent complete record children."""
from scripts.game_data.memorypack.animation_extra_union_components import CAPABILITY,TYPES
from scripts.game_data.memorypack.animation_extra_union_sources import TYPE


def need(check,condition):
    if not condition:raise ValueError('animationExtraUnionCodec.'+check)


def require_capability(cap):
    routes=cap.get('selectedRoutes',[])
    need('all-three-current-union-routes',cap.get('typeName')==TYPE and cap.get('wholeGrammarAdmitted')is True
        and cap.get('nullable')is True and cap.get('nullMarker')==255 and cap.get('tagEncoding')=='short-byte'
        and cap.get('wideTagsAdmitted')is False and cap.get('declaredUnionEntries')==3 and cap.get('allDeclaredTagsCovered')is True
        and len(routes)==3 and[r.get('tag')for r in routes]==[0,1,2]and[r.get('typeName')for r in routes]==TYPES
        and cap.get('ordinaryBaseAdapterAdmitted')is True and cap.get('inheritedBaseConversionsAdmitted')is True
        and cap.get('selectedStoredByteGrammarAdmitted')is True and cap.get('compatibleExistingWrapperAdmitted')is False
        and cap.get('collectionParentAdmitted')is False and cap.get('wholeOwnerAdmitted')is False
        and type(cap.get('canonicalAdapterTargetRva'))is int and cap['canonicalAdapterTargetRva']>0)
    return cap


def read(reader,*,depth=0,budget=None):
    need('bounded-union-depth',type(depth)is int and 0<=depth<64)
    cap=require_capability(reader.operation.child(CAPABILITY))
    for route in cap['selectedRoutes']:
        child=reader.operation.child(route['childCapability'])
        need('own-complete-concrete-route',child.get('typeName')==route['typeName']and child.get('wrapperName')==route['wrapperName']
            and child.get('memberCount')==route['memberCount']and child.get('wholeGrammarAdmitted')is True
            and child.get('directWrapperGrammarAdmitted')is True and child.get('ordinaryOriginalReadValueAdmitted')is True)
    if budget is None:budget=dict(remaining=16384)
    need('shared-node-budget-before-consumption',isinstance(budget,dict)and set(budget)=={'remaining'}
        and type(budget['remaining'])is int and 1<=budget['remaining']<=16384)
    start=reader.pos;tag=reader.peek();need('only-canonical-owned-tag-or-null',tag in(0,1,2,255))
    need('own-record-cursor',callable(getattr(reader,'extra_record',None)))
    budget['remaining']-=1;reader.take(1,CAPABILITY+'.tag');record=None
    if tag!=255:record=reader.extra_record(cap['selectedRoutes'][tag]['childCapability'],depth=depth+1,budget=budget)
    row=dict(kind=CAPABILITY,typeName=TYPE,start=start,end=reader.pos,isNull=tag==255,tag=None if tag==255 else tag,
        record=record,containingOwnerClaimed=False,runtimeAnimationProved=False)
    reader.records.append(row);return row
