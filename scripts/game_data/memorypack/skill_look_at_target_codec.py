"""Exact finite LookAtTargetInfo and signed-count list on one guarded cursor."""
import struct

from scripts.game_data.memorypack import skill_look_at_target_sources as owner


def need(check,condition):
    if not condition:raise ValueError('skillLookAtTargetCodec.'+check)


def require_target(cap):
    need('strong-target-child',cap.get('typeName')==owner.TARGET
        and all(cap.get(k)is True for k in('wholeGrammarAdmitted','ordinaryOriginalReadValueAdmitted',
            'ownConcreteGetterSemanticsProved','ownConcreteFactorySemanticsProved'))
        and type(cap.get('referenceReaderMethodDefinition'))is int and cap['referenceReaderMethodDefinition']>0
        and type(cap.get('referenceReaderTargetRva'))is int and cap['referenceReaderTargetRva']>0)
    return cap


def require_record(cap):
    need('own-complete-ordinary-record',cap.get('typeName')==owner.TYPE and cap.get('wrapperName')==owner.WRAPPER
        and type(cap.get('memberCount'))is int and cap['memberCount']==4 and cap.get('orderedReads')==owner.ORDER
        and all(type(r.get('memberIndex'))is int for r in cap['orderedReads'])
        and all(cap.get(k)is True for k in('nullable','nullAdmitted','wholeGrammarAdmitted','ordinaryOriginalReadValueAdmitted',
            'ownConcreteGetterSemanticsProved','ownConcreteFactorySemanticsProved','completeSourceOwnedProgram'))
        and type(cap.get('nullMarker'))is int and cap['nullMarker']==255
        and type(cap.get('referenceReaderMethodDefinition'))is int and cap['referenceReaderMethodDefinition']>0
        and type(cap.get('referenceReaderTargetRva'))is int and cap['referenceReaderTargetRva']>0)
    return cap


def require_collection(cap):
    need('own-positive-reference-list',cap.get('elementType')==owner.TYPE and cap.get('elementValueType')is False
        and cap.get('closedListType')=='System.Collections.Generic.List`1<'+owner.TYPE+'>'
        and cap.get('elementCapability')==owner.CAPABILITY and cap.get('collectionCounts')==[-1,0]
        and all(type(n)is int for n in cap['collectionCounts'])
        and type(cap.get('countLimit'))is int and 3<=cap['countLimit']<=10000
        and all(cap.get(k)is True for k in('positiveCountsAdmitted','nullable','elementGrammarAdmitted'))
        and type(cap.get('packableReaderMethodDefinition'))is int and cap['packableReaderMethodDefinition']>0
        and type(cap.get('packableReaderTargetRva'))is int and cap['packableReaderTargetRva']>0)
    return cap


class LookAtTargetReader:
    def __init__(self,reader):self.reader=reader

    def record(self,depth=0):
        need('depth',type(depth)is int and 0<=depth<=64);r=self.reader
        cap=require_record(r.operation.child(owner.CAPABILITY));require_target(r.operation.child(owner.CHILD))
        start=r.pos;fields=[];null=r.peek()==255
        if null:r.take(1,owner.CAPABILITY+'.null')
        else:
            need('target-depth',depth+1<=64);r.header(4)
            for field in cap['orderedReads']:
                at=r.pos
                if field['childCapability']==owner.CHILD:r._profile('target_profile',owner.CHILD,depth+1)
                else:r.take(1 if field['kind']=='bool-byte'else 4,owner.CAPABILITY+'.'+field['fieldName'])
                fields.append(dict(fieldName=field['fieldName'],start=at,end=r.pos))
        out=dict(kind=owner.CAPABILITY,start=start,end=r.pos,isNull=null,fields=fields);r.records.append(out);return out

    def collection(self,depth=0):
        need('depth',type(depth)is int and 0<=depth<=64);r=self.reader
        cap=require_collection(r.operation.child(owner.LIST));require_record(r.operation.child(owner.CAPABILITY))
        require_target(r.operation.child(owner.CHILD));start=r.pos
        need('complete-signed-count',r.pos+4<=r.limit);count=struct.unpack_from('<i',r.data,r.pos)[0]
        need('signed-count-domain',-1<=count<=cap['countLimit'])
        if count>0:need('element-depth',depth+1<=64)
        r.take(4,owner.LIST+'.count')
        for _ in range(max(0,count)):self.record(depth+1)
        out=dict(kind=owner.LIST,start=start,end=r.pos,count=count,isNull=count==-1);r.records.append(out);return out
