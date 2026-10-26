"""Finite camera condition/And/list wire programs on the authenticated cursor."""
import struct

from scripts.game_data.memorypack import skill_camera_transition_sources as owner

LEAF_ORDER=[dict(fieldName=n,kind=k,childCapability=c)for n,k,c in(
    ('boolValue','bool',None),('buffValue','pooled-string','byte-payload'),
    ('comparator','enum32',None),('conditionType','enum32',None),('floatValue','single-bits',None))]


def need(check,condition):
    if not condition:raise ValueError('skillCameraTransitionCodec.'+check)


def _ordinary(cap,nominal):
    need('own-ordinary-record',cap.get('typeName')==nominal
        and all(cap.get(k)is True for k in('nullable','nullAdmitted','wholeGrammarAdmitted',
            'ordinaryOriginalReadValueAdmitted','ownConcreteGetterSemanticsProved','ownConcreteFactorySemanticsProved'))
        and type(cap.get('nullMarker'))is int and cap['nullMarker']==255
        and type(cap.get('referenceReaderMethodDefinition'))is int and cap['referenceReaderMethodDefinition']>0
        and type(cap.get('referenceReaderTargetRva'))is int and cap['referenceReaderTargetRva']>0)


def require_leaf(cap):
    _ordinary(cap,owner.CONDITION)
    need('exact-five-field-condition',type(cap.get('memberCount'))is int and cap['memberCount']==5
        and cap.get('orderedReads')==LEAF_ORDER)
    return cap


def require_and(cap):
    _ordinary(cap,owner.TYPE)
    need('exact-one-field-And',type(cap.get('memberCount'))is int and cap['memberCount']==1
        and cap.get('orderedReads')==owner.ORDER and all(type(r.get('memberIndex'))is int for r in cap['orderedReads'])
        and cap.get('completeSourceOwnedProgram')is True)
    return cap


def require_collection(cap,*,outer):
    need('literal-list-level',type(outer)is bool)
    nominal,element=(owner.TYPE,owner.CAPABILITY)if outer else(owner.CONDITION,owner.LEAF)
    need('own-positive-reference-list',cap.get('elementType')==nominal and cap.get('elementValueType')is False
        and cap.get('closedListType')=='System.Collections.Generic.List`1<'+nominal+'>'
        and cap.get('elementCapability')==element and cap.get('collectionCounts')==[-1,0]
        and all(type(n)is int for n in cap['collectionCounts'])
        and type(cap.get('countLimit'))is int and cap['countLimit']==10000
        and all(cap.get(k)is True for k in('positiveCountsAdmitted','nullable','elementGrammarAdmitted'))
        and type(cap.get('packableReaderMethodDefinition'))is int and cap['packableReaderMethodDefinition']>0
        and type(cap.get('packableReaderTargetRva'))is int and cap['packableReaderTargetRva']>0)
    return cap


class CameraTransitionReader:
    def __init__(self,reader):self.reader=reader

    def leaf(self,depth=0):
        need('depth',type(depth)is int and 0<=depth<=64);r=self.reader
        cap=require_leaf(r.operation.child(owner.LEAF));start=r.pos;fields=[];null=r.peek()==255
        if null:r.take(1,owner.LEAF+'.null')
        else:
            r.header(5)
            for field in cap['orderedReads']:
                at=r.pos
                if field['kind']=='pooled-string':r.byte_payload()
                else:r.take(1 if field['kind']=='bool'else 4,owner.LEAF+'.'+field['fieldName'])
                fields.append(dict(fieldName=field['fieldName'],start=at,end=r.pos))
        row=dict(kind=owner.LEAF,start=start,end=r.pos,isNull=null,fields=fields);r.records.append(row);return row

    def record(self,depth=0):
        need('depth',type(depth)is int and 0<=depth<=64);r=self.reader
        require_and(r.operation.child(owner.CAPABILITY));start=r.pos;fields=[];null=r.peek()==255
        if null:r.take(1,owner.CAPABILITY+'.null')
        else:
            need('inner-list-depth',depth+1<=64);r.header(1);at=r.pos
            self.collection(depth+1,outer=False);fields.append(dict(fieldName='and',start=at,end=r.pos))
        row=dict(kind=owner.CAPABILITY,start=start,end=r.pos,isNull=null,fields=fields);r.records.append(row);return row

    def collection(self,depth=0,*,outer=True):
        need('depth',type(depth)is int and 0<=depth<=64);r=self.reader
        name=owner.LIST if outer else owner.INNER_LIST
        cap=require_collection(r.operation.child(name),outer=outer);start=r.pos
        need('complete-signed-count',r.pos+4<=r.limit)
        count=struct.unpack_from('<i',r.data,r.pos)[0]
        need('signed-count-domain',-1<=count<=cap['countLimit'])
        if count>0:
            (require_and if outer else require_leaf)(r.operation.child(owner.CAPABILITY if outer else owner.LEAF))
            need('element-depth',depth+1<=64)
        r.take(4,name+'.count')
        for _ in range(max(0,count)):(self.record if outer else self.leaf)(depth+1)
        row=dict(kind=name,start=start,end=r.pos,count=count,isNull=count==-1);r.records.append(row);return row
