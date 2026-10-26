"""Finite EffectActionCfg and TerrainEffect codecs under a selected operation.

Native composition supplies the complete ordered program and exact positive
reference/array capabilities. This reader opens no native input and grants no
source admission. Managed reference strides never become stored wire widths;
effect names and authored fields establish no runtime playback or asset join.
"""
import struct

from scripts.game_data.memorypack.skill_timeline_current_sequence import ATOMIC_KINDS

TYPE='Beyond.Gameplay.EffectActionCfg'
CAPABILITY='skill-effect-action-config'
TERRAIN='skill-terrain-effect-data'
ARRAY='skill-terrain-effect-array'
TERRAIN_TYPE='Beyond.Gameplay.TerrainEffectData'
LABEL='skillEffectCodec'
CHILDREN={
    'byte-payload':('byte_payload','byte-payload'),
    'blackboard-double':('scalar_payload','scalar-payload'),
    'blackboard-vector3':('vector_payload','blackboard-vector3'),
}


def need(check,valid):
    if not valid:raise ValueError(LABEL+'.'+check)


class EffectReader:
    def __init__(self,reader):self.reader=reader

    def _cap(self,name):return self.reader.operation.child(name)

    def _depth(self,depth):need('depth',type(depth)is int and 0<=depth<=64)

    def _reference(self,name,typename,count):
        cap=self._cap(name)
        need('exact-reference:'+name,cap.get('typeName')==typename
            and type(cap.get('memberCount'))is int and cap['memberCount']==count
            and all(cap.get(k)is True for k in('wholeGrammarAdmitted','ordinaryOriginalReadValueAdmitted',
                'ownConcreteGetterSemanticsProved','ownConcreteFactorySemanticsProved','nullAdmitted'))
            and type(cap.get('nullMarker'))is int and cap['nullMarker']==255)
        return cap

    def _terrain_cap(self):
        cap=self._reference(TERRAIN,TERRAIN_TYPE,2)
        expected=[dict(memberIndex=i,fieldName=field,kind='byte-payload',childCapability='byte-payload')
            for i,field in enumerate(('effectName','tag'))]
        need('complete-terrain-pooled-program',cap.get('orderedReads')==expected
            and type(cap.get('positiveWireBytes'))is int and cap['positiveWireBytes']==9
            and type(cap.get('nullWireBytes'))is int and cap['nullWireBytes']==1)
        return cap

    def terrain(self,depth=0):
        self._depth(depth);self._terrain_cap();r=self.reader;start=r.pos
        if r.peek()==255:r.take(1,TERRAIN+'.null')
        else:
            r.header(2)
            for field in('effectName','tag'):r._profile('byte_payload','byte-payload',depth+1)
        r.records.append(dict(kind=TERRAIN,start=start,end=r.pos))

    def terrain_array(self,depth=0):
        self._depth(depth);cap=self._cap(ARRAY);r=self.reader;start=r.pos
        need('exact-terrain-array',cap.get('elementType')==TERRAIN_TYPE and cap.get('elementValueType')is False
            and cap.get('closedArrayType')==TERRAIN_TYPE+'[]'and cap.get('elementCapability')==TERRAIN
            and cap.get('collectionCounts')==[-1,0]and all(type(n)is int for n in cap['collectionCounts'])
            and all(cap.get(k)is True for k in('positiveCountsAdmitted','nullable','elementGrammarAdmitted','wholeGrammarAdmitted'))
            and type(cap.get('countLimit'))is int and cap['countLimit']==10000)
        self._terrain_cap()
        if r.pos+4>r.limit:raise ValueError(LABEL+'.truncated-array-count')
        count=struct.unpack_from('<i',r.data,r.pos)[0]
        need('unproved-array-count:'+str(count),-1<=count<=cap['countLimit'])
        actual=r.count(1,nullable=True)
        for _ in range(max(0,actual)):self.terrain(depth+1)
        r.records.append(dict(kind=ARRAY,start=start,end=r.pos,count=count))

    def _program(self,cap):
        reads=cap.get('orderedReads')
        need('complete-source-owned-program',cap.get('completeSourceOwnedProgram')is True
            and isinstance(reads,list)and len(reads)==86)
        fields=set()
        for index,read in enumerate(reads):
            need('ordered-member',isinstance(read,dict)and set(read)=={'memberIndex','fieldName','kind','childCapability'}
                and type(read.get('memberIndex'))is int and read['memberIndex']==index
                and isinstance(read.get('fieldName'),str)and bool(read['fieldName'])and read['fieldName']not in fields)
            fields.add(read['fieldName']);kind=read['kind'];child=read['childCapability']
            if kind in ATOMIC_KINDS:need('atomic-member-child',child is None)
            elif kind in CHILDREN:need('exact-reference-member-child',child==CHILDREN[kind][1])
            elif kind=='terrain-effect-array':need('exact-array-member-child',child==ARRAY)
            else:raise ValueError(LABEL+'.unproved-member-kind='+str(kind))
        return reads

    def effect(self,depth=0):
        self._depth(depth);cap=self._reference(CAPABILITY,TYPE,86);reads=self._program(cap)
        r=self.reader;start=r.pos
        if r.peek()==255:r.take(1,CAPABILITY+'.null')
        else:
            r.header(86);fields=[]
            for read in reads:
                at=r.pos;kind=read['kind']
                if kind in ATOMIC_KINDS:r.take(ATOMIC_KINDS[kind],TYPE+'.'+read['fieldName']+'.'+kind)
                elif kind in CHILDREN:r._profile(*CHILDREN[kind],depth+1)
                else:self.terrain_array(depth+1)
                fields.append(dict(fieldName=read['fieldName'],start=at,end=r.pos))
            r.records.append(dict(kind=CAPABILITY,start=start,end=r.pos,fields=fields));return
        r.records.append(dict(kind=CAPABILITY,start=start,end=r.pos,isNull=True))
