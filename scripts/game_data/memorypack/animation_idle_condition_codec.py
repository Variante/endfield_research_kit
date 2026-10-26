"""Bounded canonical idle tags and six independently owned concrete records."""
from scripts.game_data.memorypack.animation_idle_condition_components import CAPABILITY
from scripts.game_data.memorypack.animation_idle_condition_sources import TYPE,TYPES


def need(check,condition):
    if not condition:raise ValueError('animationIdleConditionCodec.'+check)


def require_capability(cap):
    routes=cap.get('selectedRoutes',[])
    need('all-six-own-routes',cap.get('typeName')==TYPE and cap.get('wholeGrammarAdmitted')is True
        and cap.get('nullable')is True and cap.get('nullMarker')==255 and cap.get('tagEncoding')=='short-byte'
        and cap.get('wideTagsAdmitted')is False and cap.get('declaredUnionEntries')==6 and cap.get('allDeclaredTagsCovered')is True
        and len(routes)==6 and[r.get('tag')for r in routes]==list(range(6))and[r.get('typeName')for r in routes]==TYPES
        and cap.get('ordinaryBaseAdapterAdmitted')is True and cap.get('inheritedBaseConversionsAdmitted')is True
        and cap.get('ordinaryOriginalReadValueAdmitted')is True and cap.get('ordinaryOriginalCallbackAdmitted')is True
        and cap.get('compatibleExistingWrapperAdmitted')is False and cap.get('collectionParentAdmitted')is False
        and cap.get('wholeOwnerAdmitted')is False and cap.get('valueStorageKind')=='reference8'
        and type(cap.get('originalTypeDefinition'))is int and cap['originalTypeDefinition']>=0
        and type(cap.get('canonicalAdapterTargetRva'))is int and cap['canonicalAdapterTargetRva']>0
        and type(cap.get('formatterDeserializeMethodDefinition'))is int)
    return cap


def read(reader,*,depth=0,budget=None):
    need('bounded-depth',type(depth)is int and 0<=depth<64)
    cap=require_capability(reader.operation.child(CAPABILITY))
    for route in cap['selectedRoutes']:
        child=reader.operation.child(route['childCapability'])
        need('own-whole-concrete-child',child.get('typeName')==route['typeName']and child.get('wrapperName')==route['wrapperName']
            and child.get('memberCount')==route['memberCount']and child.get('wholeGrammarAdmitted')is True
            and child.get('ordinaryOriginalReadValueAdmitted')is True and child.get('directWrapperGrammarAdmitted')is True)
    if budget is None:budget=dict(remaining=16384)
    need('shared-budget-before-consumption',isinstance(budget,dict)and set(budget)=={'remaining'}
        and type(budget['remaining'])is int and 0<budget['remaining']<=16384)
    need('owned-record-cursor',callable(getattr(reader,'extra_record',None)))
    tag=reader.peek();need('canonical-tag-or-null',tag in(0,1,2,3,4,5,255))
    start=reader.pos;budget['remaining']-=1;reader.take(1,CAPABILITY+'.tag')
    record=None if tag==255 else reader.extra_record(cap['selectedRoutes'][tag]['childCapability'],depth=depth+1,budget=budget)
    result=dict(kind=CAPABILITY,typeName=TYPE,start=start,end=reader.pos,isNull=tag==255,
        tag=None if tag==255 else tag,record=record,containingOwnerClaimed=False,runtimeAnimationProved=False)
    reader.records.append(result);return result
