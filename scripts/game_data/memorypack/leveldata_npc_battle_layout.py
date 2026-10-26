"""Finite pure NPC battle profile compiled from independent current sources."""
import copy

from scripts.game_data.memorypack.leveldata_npc_battle_components import (
    BATTLE,SKILL,COLLIDER,PAIR,PLANS,COLLIDER_CAP,SKILL_CAP,SKILL_LIST_CAP,PAIR_CAP,COUNT_LIMIT)
from scripts.game_data.memorypack.leveldata_extended_record_sources import STRING_CAP

BATTLE_CAP='story-npc-battle'
CHILDREN={'byte-payload':'byte-payload','record':COLLIDER_CAP,'data-pair-list':PAIR_CAP,
    'skill-blackboard-list':SKILL_LIST_CAP,'pooled-string-list':STRING_CAP}


def make_profile(component):
    """Retain only finite codec declarations; this is not a native gate."""
    profile=dict(profileId='current-owner-npc-battle',profileAdmitted=True,wholeGrammarAdmitted=False,
        requiresFreshCurrentOwnerScope=True,liveFormatterSelectionObserved=False,finiteFloatProfile=True,
        records=copy.deepcopy(component['capabilities']),
        colliderEnumBackings=copy.deepcopy(component['records'][COLLIDER]['enumBackings']),
        dataPairChild=copy.deepcopy(component['collections']['dataPairList']['component']['capabilities']['skill-root-data-pair']))
    validate_profile(profile)
    return profile


def validate_profile(profile):
    if (not isinstance(profile,dict)or profile.get('profileId')!='current-owner-npc-battle'
            or profile.get('profileAdmitted')is not True or profile.get('wholeGrammarAdmitted')is not False
            or profile.get('requiresFreshCurrentOwnerScope')is not True
            or profile.get('finiteFloatProfile')is not True
            or profile.get('liveFormatterSelectionObserved')is not False
            or set(profile.get('records',{}))!={COLLIDER_CAP,SKILL_CAP,BATTLE_CAP}):
        raise ValueError('currentNpcBattle.exact-current-profile')
    for name,key in((COLLIDER,COLLIDER_CAP),(SKILL,SKILL_CAP),(BATTLE,BATTLE_CAP)):
        cap=profile['records'][key];plan=PLANS[name]
        if (cap.get('typeName')!=name or type(cap.get('memberCount'))is not int or cap['memberCount']!=len(plan)
                or any(cap.get(k)is not True for k in('profileAdmitted','positiveAdmitted','nullAdmitted','actualCallbackEqualsProvedChildRequired'))
                or cap.get('wholeGrammarAdmitted')is not False
                or any(type(cap.get(k))is not int or cap[k]<=0 for k in('referenceReaderMethodDefinition','referenceReaderTargetRva'))
                or [(r.get('memberIndex'),r.get('fieldName'),r.get('kind'),r.get('childCapability'))for r in cap.get('orderedReads',[])]!=[
                    (i,n,k,CHILDREN.get(k))for i,(n,_,k)in enumerate(plan)]):
            raise ValueError('currentNpcBattle.exact-record-program:'+name)
    enums=profile.get('colliderEnumBackings',{})
    if set(enums)!={'_shape'}:raise ValueError('currentNpcBattle.exact-enum-set')
    enum=enums['_shape'];typename='Beyond.Gameplay.ColliderShape'
    if (enum.get('typeName')!=typename or enum.get('backing')not in('int','uint')
            or enum.get('field')!=[typename,enum.get('backing'),16]):
        raise ValueError('currentNpcBattle.exact-nominal-enum-backing')
    # Reuse the shared managed32 child codec's independent literal checks.
    from scripts.game_data.memorypack.skill_root_children_codec import RootChildrenReader
    class Child:
        def child(self,key):
            if key!='skill-root-data-pair':raise ValueError('currentNpcBattle.unknown-value-child')
            return profile.get('dataPairChild',{})
    class Reader:operation=Child()
    RootChildrenReader(Reader())._record_cap('skill-root-data-pair')


def extend_layout(base,profile):
    validate_profile(profile);result=copy.deepcopy(base)
    if any(name in result['records']for name in PLANS):raise ValueError('currentNpcBattle.old-record-collision')
    strings=lambda:dict(wire='items',countLimit=COUNT_LIMIT,element=dict(type='string',wire='pool'))
    result['records'][COLLIDER]=[
        dict(name=n,type=t,wire='vector3'if k=='unity-vector3-raw12'else'pool'if k=='byte-payload'
            else'f32'if k=='float32-bits'else'bool'if k=='bool-byte'else
            'u32'if profile['colliderEnumBackings'][n]['backing']=='uint'else'i32')
        for n,t,k in PLANS[COLLIDER]]
    result['records'][SKILL]=[
        dict(name='blackboard',type='System.Collections.Generic.List`1<'+PAIR+'>',wire='items',countLimit=COUNT_LIMIT,
            element=dict(type=PAIR,wire='current-data-pair')),
        dict(name='skillId',type='string',wire='pool')]
    result['records'][BATTLE]=[
        dict(name='activeSkillId',type=PLANS[BATTLE][0][1],**strings()),
        dict(name='battleShapeData',type=COLLIDER,wire='record',nullable=True),
        dict(name='blackboard',type=PLANS[BATTLE][2][1],wire='items',countLimit=COUNT_LIMIT,
            element=dict(type=SKILL,wire='record',nullable=True)),
        dict(name='passiveSkillId',type=PLANS[BATTLE][3][1],**strings())]
    rows=[r for r in result['root']if r['name']=='battleData']
    if len(rows)!=1 or(rows[0].get('type'),rows[0].get('wire'))!=(BATTLE,'null'):
        raise ValueError('currentNpcBattle.exact-old-null-parent')
    rows[0].update(wire='record',nullable=True)
    return result
