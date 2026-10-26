"""Current DamageUnit codec with independently owned delegated child programs.

Only a selected operation with the complete nominal source-owned capability
can invoke this reader. It opens no native input and admits neither an action
nor a Skill root. Effect, union, list, sound-event and pool gates remain at
their reached fields; authored damage configuration is not runtime behavior.
"""
from scripts.game_data.memorypack.skill_damage_unit_sources import TYPE,DECLARATIONS
from scripts.game_data.memorypack.skill_timeline_current_sequence import ATOMIC_KINDS

CAPABILITY='skill-damage-unit'
HIT_SOUND='damage-hit-sound-data'
LABEL='skillDamageCodec'
REFERENCES={
    'atkCalculation':('damage-union','damage-calculation-union'),
    'atkScale':('blackboard-double','scalar-payload'),
    'effectData':('effect-profile','skill-effect-action-config'),
    'hitSoundData':('damage-hit-sound','damage-hit-sound-data'),
    'poiseCalculation':('damage-union','damage-calculation-union'),
}
LISTS={
    'costDataList':('damage-list','damage-cost-data-list'),
    'damageProcessors':('damage-list','damage-processor-list'),
    'damageTags':('damage-tag-list','damage-gameplay-tag-list'),
}


def ordered_reads():
    atoms={'bool':'bool-byte','enum':'enum32','int64':'scalar64-bits','single':'float32-bits'}
    result=[]
    for index,(field,typename,kind)in enumerate(DECLARATIONS):
        if kind in atoms:wire,child=atoms[kind],None
        elif kind=='pool':wire,child='byte-payload','byte-payload'
        else:wire,child=(REFERENCES if kind=='reference'else LISTS)[field]
        result.append(dict(memberIndex=index,fieldName=field,kind=wire,childCapability=child))
    return result


def need(check,valid):
    if not valid:raise ValueError(LABEL+'.'+check)


class DamageUnitReader:
    def __init__(self,reader):self.reader=reader

    def _depth(self,depth):need('depth',type(depth)is int and 0<=depth<=64)

    def _reference(self,name,typename,count):
        cap=self.reader.operation.child(name)
        need('exact-reference:'+name,cap.get('typeName')==typename
            and type(cap.get('memberCount'))is int and cap['memberCount']==count
            and all(cap.get(k)is True for k in('wholeGrammarAdmitted','ordinaryOriginalReadValueAdmitted',
                'ownConcreteGetterSemanticsProved','ownConcreteFactorySemanticsProved','nullAdmitted'))
            and type(cap.get('nullMarker'))is int and cap['nullMarker']==255)
        return cap

    def hit_sound(self,depth=0):
        self._depth(depth);cap=self._reference(HIT_SOUND,TYPE+'+HitSoundData',1)
        expected=[dict(memberIndex=0,fieldName='soundEvent',kind='pooled-string',childCapability='byte-payload')]
        need('exact-pooled-hit-sound-program',cap.get('orderedReads')==expected)
        r=self.reader;start=r.pos
        if r.peek()==255:r.take(1,HIT_SOUND+'.null')
        else:r.header(1);r._profile('byte_payload','byte-payload',depth+1)
        r.records.append(dict(kind=HIT_SOUND,start=start,end=r.pos))

    def require_damage_capability(self):
        cap=self._reference(CAPABILITY,TYPE,34)
        expected=ordered_reads()
        need('complete-source-owned-DamageUnit34',cap.get('completeSourceOwnedProgram')is True
            and cap.get('orderedReads')==expected
            and all(type(read.get('memberIndex'))is int for read in cap['orderedReads']))
        return cap

    def damage(self,depth=0):
        self._depth(depth);self.require_damage_capability();expected=ordered_reads()
        r=self.reader;start=r.pos
        if r.peek()==255:r.take(1,CAPABILITY+'.null')
        else:
            from scripts.game_data.memorypack.skill_damage_children_codec import DamageChildrenReader
            from scripts.game_data.memorypack.skill_effect_codec import EffectReader
            children=DamageChildrenReader(r);effects=EffectReader(r);r.header(34);fields=[]
            for read in expected:
                at=r.pos;kind=read['kind'];child=read['childCapability']
                if kind in ATOMIC_KINDS:r.take(ATOMIC_KINDS[kind],TYPE+'.'+read['fieldName']+'.'+kind)
                elif kind=='byte-payload':r._profile('byte_payload',child,depth+1)
                elif kind=='blackboard-double':r._profile('scalar_payload',child,depth+1)
                elif kind=='damage-union':children.union(child,depth+1)
                elif kind=='damage-list':children.collection(child,depth+1)
                elif kind=='damage-tag-list':children.tag_list(depth+1)
                elif kind=='damage-hit-sound':self.hit_sound(depth+1)
                else:effects.effect(depth+1)
                fields.append(dict(fieldName=read['fieldName'],start=at,end=r.pos))
            r.records.append(dict(kind=CAPABILITY,start=start,end=r.pos,fields=fields));return
        r.records.append(dict(kind=CAPABILITY,start=start,end=r.pos,isNull=True))
