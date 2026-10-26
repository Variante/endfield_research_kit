"""Bounded current CharInteract union tags and independently owned children."""
from scripts.game_data.memorypack.char_union_components import key,WIRE,ORDINARY
from scripts.game_data.memorypack.char_union_sources import TYPE,NESTED


def need(check,condition):
    if not condition:raise ValueError('charUnionCodec.'+check)


def require_capability(capability,cap):
    name=cap.get('typeName');rows=cap.get('selectedRoutes',[])
    need('finite-whole-own-union',name in(TYPE,)+NESTED and capability==key(name)
        and cap.get('wholeGrammarAdmitted')is True and cap.get('directWrapperGrammarAdmitted')is True
        and cap.get('allDeclaredTagsCovered')is True and type(cap.get('declaredUnionEntries'))is int
        and 1<=cap['declaredUnionEntries']<=48 and len(rows)==cap['declaredUnionEntries']
        and[r.get('tag')for r in rows]==list(range(len(rows)))and len({r.get('typeName')for r in rows})==len(rows)
        and cap.get('nullable')is True and cap.get('nullMarker')==255 and cap.get('tagEncoding')=='short-byte'
        and cap.get('wideTagsAdmitted')is False and cap.get('compatibleExistingWrapperAdmitted')is False
        and cap.get('collectionParentAdmitted')is False and cap.get('wholeOwnerAdmitted')is False)
    if name in ORDINARY:
        need('own-ordinary-reference-union',cap.get('ordinaryBaseAdapterAdmitted')is True
            and cap.get('ordinaryOriginalReadValueAdmitted')is True and cap.get('ordinaryOriginalCallbackAdmitted')is True
            and cap.get('inheritedBaseConversionsAdmitted')is True and cap.get('valueStorageKind')=='reference8'
            and all(type(cap.get(k))is int and cap[k]>0 for k in('originalTypeDefinition',
                'canonicalAdapterTargetRva','formatterDeserializeMethodDefinition')))
    for row in rows:
        need('own-finite-child-operation',row.get('childWire')in(WIRE,'char-interact-record')
            and isinstance(row.get('childCapability'),str)and bool(row['childCapability'])
            and isinstance(row.get('wrapperName'),str)and bool(row['wrapperName']))
    return cap


def read(reader,capability,*,depth=0,budget=None):
    need('bounded-depth',type(depth)is int and 0<=depth<64)
    cap=require_capability(capability,reader.operation.child(capability))
    for row in cap['selectedRoutes']:
        child=reader.operation.child(row['childCapability'])
        need('own-current-complete-child-before-consumption',child.get('typeName')==row['typeName']
            and child.get('wrapperName')==row['wrapperName']and child.get('wholeGrammarAdmitted')is True
            and child.get('directWrapperGrammarAdmitted')is True)
        if row['childWire']==WIRE:require_capability(row['childCapability'],child)
        else:
            from scripts.game_data.memorypack.char_record_codec import require_capability as record
            record(child)
    if budget is None:budget=dict(remaining=16384)
    need('shared-budget-before-consumption',type(budget)is dict and set(budget)=={'remaining'}
        and type(budget['remaining'])is int and 0<budget['remaining']<=16384)
    tag=reader.peek();need('canonical-own-tag-or-FF',type(tag)is int and(tag==255 or 0<=tag<len(cap['selectedRoutes'])))
    start=reader.pos;budget['remaining']-=1;reader.take(1,capability+'.tag');child=None
    if tag!=255:
        row=cap['selectedRoutes'][tag]
        child=read(reader,row['childCapability'],depth=depth+1,budget=budget)if row['childWire']==WIRE else reader.record(
            row['childCapability'],depth=depth+1,budget=budget)
    result=dict(kind=capability,typeName=cap['typeName'],start=start,end=reader.pos,isNull=tag==255,
        tag=None if tag==255 else tag,child=child,containingOwnerClaimed=False,runtimeAnimationProved=False)
    reader.records.append(result);return result
