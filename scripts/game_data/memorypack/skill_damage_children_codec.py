"""Finite source-owned Damage calculation/processor and collection codecs.

The enclosing selected operation supplies freshly authenticated capabilities;
this module performs no native admission. Every reached member, list element,
pool index and reference child retains that operation's gate. Neither a managed
element stride nor an enclosing cursor supplies a wire grammar. These children
do not admit DamageUnit, EffectActionCfg, an action or a Skill root themselves.
"""
import struct

from scripts.game_data.memorypack.skill_timeline_current_sequence import ATOMIC_KINDS

LABEL='skillDamageChildren'
MAX_DEPTH=64
UNIONS={
    'damage-calculation-union':('Beyond.Gameplay.Core.CalculationBase',6),
    'damage-processor-union':('Beyond.Gameplay.Core.DamageProcessorBase',11),
}
LISTS={
    'damage-cost-data-list':('Beyond.Gameplay.Core.CastData+CostData','skill-root-cost-data'),
    'damage-processor-list':('Beyond.Gameplay.Core.DamageProcessorBase','damage-processor-union'),
}
TAG_LIST='damage-gameplay-tag-list'
TAG_ELEMENT='skill-root-gameplay-tag'


def need(check,valid):
    if not valid:raise ValueError(LABEL+'.'+check)


class DamageChildrenReader:
    def __init__(self,reader):self.reader=reader

    def _capability(self,name):return self.reader.operation.child(name)

    def _depth(self,depth):need('depth',type(depth)is int and 0<=depth<=MAX_DEPTH)

    def _program(self,route):
        count=route.get('memberCount');reads=route.get('orderedReads')
        need('concrete-source-program',type(count)is int and 0<=count<250 and isinstance(reads,list)and len(reads)==count
            and route.get('generatedWrapperOnly')is True and route.get('ordinaryOriginalReadValueAdmitted')is False
            and route.get('wholeGrammarAdmitted')is True and route.get('nullAdmitted')is True
            and type(route.get('nullMarker'))is int and route['nullMarker']==255)
        for index,read in enumerate(reads):
            need('ordered-source-read',set(read)=={'memberIndex','fieldName','kind','childCapability'}
                and type(read.get('memberIndex'))is int and read['memberIndex']==index
                and isinstance(read.get('fieldName'),str)and bool(read['fieldName']))
            kind=read['kind'];child=read['childCapability']
            if kind in ATOMIC_KINDS:need('atomic-child',child is None)
            elif kind=='byte-payload':need('pooled-child',child=='byte-payload')
            elif kind=='blackboard-double':need('scalar-child',child=='scalar-payload')
            elif kind=='record':need('attribute-child',child=='skill-root-attribute-modifier')
            else:raise ValueError(LABEL+'.unproved-member-kind='+str(kind))
        return reads

    def union(self,name,depth=0):
        self._depth(depth);need('known-union',name in UNIONS)
        typename,count=UNIONS[name];cap=self._capability(name);r=self.reader;start=r.pos
        need('exact-complete-union',cap.get('typeName')==typename and cap.get('wholeGrammarAdmitted')is True
            and cap.get('baseGetterSemanticsProved')is True and cap.get('concreteChildGrammarsProved')is True
            and cap.get('ordinaryOriginalReadValueAdmitted')is True and cap.get('nullAdmitted')is True
            and type(cap.get('nullMarker'))is int and cap['nullMarker']==255
            and cap.get('extendedTagsAdmitted')is False and cap.get('reservedMarkersAdmitted')is False
            and cap.get('supportedShortTags')==list(range(count))
            and all(type(tag)is int for tag in cap['supportedShortTags']))
        routes=cap.get('routes');need('complete-union-routes',isinstance(routes,list)and len(routes)==count
            and [route.get('tag')for route in routes]==list(range(count))
            and all(type(route.get('tag'))is int for route in routes))
        tag=r.peek()
        if tag==255:
            r.take(1,name+'.null');out=dict(kind=name,start=start,end=r.pos,isNull=True);r.records.append(out);return out
        need('unproved-union-tag:'+str(tag),tag in cap['supportedShortTags'])
        route=routes[tag];reads=self._program(route)
        # Validate the complete selected program before consuming its tag.
        r.take(1,name+'.tag')
        if r.peek()==255:
            r.take(1,name+'.wrapper-null')
            out=dict(kind=name,start=start,end=r.pos,tag=tag,isNull=False,wrapperNull=True);r.records.append(out);return out
        r.header(route['memberCount']);fields=[]
        for read in reads:
            at=r.pos;kind=read['kind'];child=read['childCapability']
            if kind in ATOMIC_KINDS:r.take(ATOMIC_KINDS[kind],route['typeName']+'.'+read['fieldName']+'.'+kind)
            elif kind=='byte-payload':r.byte_payload()
            elif kind=='blackboard-double':r._profile('scalar_payload',child)
            else:
                from scripts.game_data.memorypack.skill_root_children_codec import RootChildrenReader
                RootChildrenReader(r).record(child,depth+1)
            fields.append(dict(fieldName=read['fieldName'],start=at,end=r.pos))
        out=dict(kind=name,start=start,end=r.pos,tag=tag,isNull=False,wrapperNull=False,fields=fields)
        r.records.append(out);return out

    def _count(self,name,cap,*,typename,element,value_type):
        r=self.reader
        need('list-nominal:'+name,cap.get('elementType')==typename
            and cap.get('closedListType')=='System.Collections.Generic.List`1<'+typename+'>'
            and cap.get('elementValueType')is value_type and cap.get('elementCapability')==element)
        need('list-source-scope:'+name,cap.get('collectionCounts')==[-1,0]
            and all(type(n)is int for n in cap['collectionCounts'])and cap.get('nullable')is True
            and type(cap.get('countLimit'))is int and cap['countLimit']==10000
            and cap.get('positiveCountsAdmitted')is True and cap.get('elementGrammarAdmitted')is True)
        if r.pos+4>r.limit:raise ValueError(LABEL+'.truncated-count='+name)
        count=struct.unpack_from('<i',r.data,r.pos)[0]
        need('unproved-list-count:'+name+':'+str(count),-1<=count<=cap['countLimit'])
        if count>0:
            child=self._capability(element)
            if value_type:
                from scripts.game_data.memorypack.skill_root_children_codec import RootChildrenReader
                RootChildrenReader(r)._record_cap(element)
                need('generated-Tag-wire5',element==TAG_ELEMENT and child.get('rawUnmanagedTagGrammarUsed')is False)
            else:
                need('complete-positive-list-child:'+name,child.get('typeName')==typename
                    and child.get('wholeGrammarAdmitted')is True and child.get('ordinaryOriginalReadValueAdmitted',True)is True)
        return r.count(1,nullable=True)

    def collection(self,name,depth=0):
        self._depth(depth);need('known-reference-list',name in LISTS)
        typename,element=LISTS[name];cap=self._capability(name);r=self.reader;start=r.pos
        need('complete-reference-list:'+name,cap.get('wholeGrammarAdmitted')is True)
        count=self._count(name,cap,typename=typename,element=element,value_type=False)
        for _ in range(max(0,count)):
            if element in UNIONS:self.union(element,depth+1)
            else:
                from scripts.game_data.memorypack.skill_root_children_codec import RootChildrenReader
                RootChildrenReader(r).record(element,depth+1)
        out=dict(kind=name,start=start,end=r.pos,count=count,elementType=typename);r.records.append(out);return out

    def tag_list(self,depth=0):
        self._depth(depth);r=self.reader;start=r.pos;cap=self._capability(TAG_LIST)
        count=self._count(TAG_LIST,cap,typename='Beyond.Gameplay.Core.GameplayTag',element=TAG_ELEMENT,value_type=True)
        from scripts.game_data.memorypack.skill_root_children_codec import RootChildrenReader
        child_reader=RootChildrenReader(r)
        for _ in range(max(0,count)):child_reader.record(TAG_ELEMENT,depth+1)
        out=dict(kind=TAG_LIST,start=start,end=r.pos,count=count,elementType='Beyond.Gameplay.Core.GameplayTag')
        r.records.append(out);return out
