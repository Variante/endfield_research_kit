"""Inactive finite ordinary-map driver on the selected shared cursor/operation.

Signed array/list null consumes four bytes. Every positive element keeps its
own ordinary source and child gate; neither managed reference stride nor the
older existing-wrapper map cap supplies that gate. Enclosing source selection,
action delivery and physical EOF remain outside this codec.
"""
import struct

from scripts.game_data.memorypack import skill_ordinary_ability_map_sources as source


def need(check,condition):
    if not condition:raise ValueError('skillOrdinaryAbilityMapCodec.'+check)


def ordinary(cap,type_name):
    need('exact-ordinary-element',cap.get('typeName')==type_name
        and all(cap.get(k)is True for k in('nullAdmitted','wholeGrammarAdmitted','ordinaryOriginalReadValueAdmitted',
            'ownConcreteGetterSemanticsProved','ownConcreteFactorySemanticsProved'))
        and type(cap.get('referenceReaderMethodDefinition'))is int and cap['referenceReaderMethodDefinition']>0
        and type(cap.get('referenceReaderTargetRva'))is int and cap['referenceReaderTargetRva']>0)
    return cap


def require_capability(cap):
    ordinary(cap,source.TYPE)
    need('exact-own-map-program',cap.get('wrapperName')==source.WRAPPER
        and type(cap.get('memberCount'))is int and cap['memberCount']==2 and cap.get('orderedReads')==source.ordered_reads()
        and all(type(r.get('memberIndex'))is int for r in cap['orderedReads'])
        and cap.get('completeSourceOwnedProgram')is True and cap.get('nullable')is True
        and type(cap.get('nullMarker'))is int and cap['nullMarker']==255)
    return cap


def require_collection(cap,*,array):
    need('literal-collection-profile',type(array)is bool)
    nominal=source.SEQUENCE if array else source.TYPE;child='SequenceActionData'if array else source.CAPABILITY
    reader='arrayReader'if array else'packableReader'
    need('exact-positive-collection-source',cap.get('elementType')==nominal and cap.get('elementValueType')is False
        and cap.get('elementCapability')==child and cap.get('collectionCounts')==[-1,0]
        and all(type(n)is int for n in cap['collectionCounts'])
        and type(cap.get('countLimit'))is int and cap['countLimit']==10000
        and all(cap.get(k)is True for k in('nullable','positiveCountsAdmitted','elementGrammarAdmitted'))
        and cap.get('closedArrayType'if array else'closedListType')==(nominal+'[]'if array else'System.Collections.Generic.List`1<'+nominal+'>')
        and type(cap.get(reader+'MethodDefinition'))is int and cap[reader+'MethodDefinition']>0
        and type(cap.get(reader+'TargetRva'))is int and cap[reader+'TargetRva']>0)
    return cap


class OrdinaryMapReader:
    def __init__(self,reader):self.reader=reader

    def record(self,depth=0):
        need('depth',type(depth)is int and 0<=depth<=64);r=self.reader;cap=require_capability(r.operation.child(source.CAPABILITY))
        start=r.pos;fields=[];null=r.peek()==255
        if null:r.take(1,source.CAPABILITY+'.null')
        else:
            r.header(2);at=r.pos;r.take(4,source.CAPABILITY+'.abilityEvent')
            fields.append(dict(fieldName='abilityEvent',start=at,end=r.pos));at=r.pos;self.array(depth+1)
            fields.append(dict(fieldName='actions',start=at,end=r.pos))
        row=dict(kind=source.CAPABILITY,start=start,end=r.pos,isNull=null,fields=fields);r.records.append(row);return row

    def _count(self,cap,label):
        r=self.reader;need('complete-signed-count',r.pos+4<=r.limit)
        count=struct.unpack_from('<i',r.data,r.pos)[0]
        need('signed-count-domain',-1<=count<=cap['countLimit'])
        return count

    def array(self,depth=0):
        need('depth',type(depth)is int and 0<=depth<=64);r=self.reader;cap=require_collection(r.operation.child(source.ARRAY),array=True)
        count=self._count(cap,source.ARRAY);start=r.pos
        if count>0:
            child=ordinary(r.operation.child('SequenceActionData'),source.SEQUENCE)
            need('Sequence-array-induction',child.get('positiveCountsAdmitted')is True
                and child.get('freshArrayCountInductionProved')is True and child.get('collectionCounts')==[-1,0]
                and all(type(n)is int for n in child['collectionCounts'])
                and type(child.get('countLimit'))is int and child['countLimit']==10000)
            need('depth',depth+1<=64)
        r.take(4,source.ARRAY+'.count')
        for _ in range(max(0,count)):r._sequence(depth+1)
        row=dict(kind=source.ARRAY,start=start,end=r.pos,count=count,isNull=count==-1);r.records.append(row);return row

    def collection(self,depth=0):
        need('depth',type(depth)is int and 0<=depth<=64);r=self.reader;cap=require_collection(r.operation.child(source.LIST),array=False)
        count=self._count(cap,source.LIST);start=r.pos
        if count>0:
            require_capability(r.operation.child(source.CAPABILITY));need('depth',depth+1<=64)
        r.take(4,source.LIST+'.count')
        for _ in range(max(0,count)):self.record(depth+1)
        row=dict(kind=source.LIST,start=start,end=r.pos,count=count,isNull=count==-1);r.records.append(row);return row
