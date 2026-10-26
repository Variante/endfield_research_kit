"""Finite SpecialAim union/sector/list bytes under an authenticated operation."""
from scripts.game_data.memorypack.skill_special_aim_components import TYPE,CHILD,CHILD_WRAPPER,CAPABILITY,SECTOR,LIST,ORDER


def need(check,condition):
    if not condition:raise ValueError('skillSpecialAimCodec.'+check)


def require_union(cap):
    need('own-complete-finite-union',cap.get('typeName')==TYPE and all(cap.get(k)is True for k in
        ('nullable','nullAdmitted','wholeGrammarAdmitted','ordinaryOriginalReadValueAdmitted',
            'baseGetterSemanticsProved','concreteChildGrammarsProved','allConcreteFactoriesProved'))
        and type(cap.get('nullMarker'))is int and cap['nullMarker']==255 and cap.get('supportedShortTags')==[0]
        and all(type(n)is int for n in cap['supportedShortTags'])and cap.get('extendedTagsAdmitted')is False
        and cap.get('reservedMarkersAdmitted')is False and cap.get('routes')==[
            dict(tag=0,wrappedType=CHILD,wrapperName=CHILD_WRAPPER,childCapability=SECTOR)]
        and type(cap.get('referenceReaderMethodDefinition'))is int and cap['referenceReaderMethodDefinition']>0
        and type(cap.get('referenceReaderTargetRva'))is int and cap['referenceReaderTargetRva']>0)
    return cap


def require_sector(cap):
    need('own-complete-wrapper-only-sector',cap.get('typeName')==CHILD and cap.get('wrapperName')==CHILD_WRAPPER
        and type(cap.get('memberCount'))is int and cap['memberCount']==3 and cap.get('orderedReads')==ORDER
        and all(type(r.get('memberIndex'))is int for r in cap['orderedReads'])
        and all(cap.get(k)is True for k in('nullable','nullAdmitted','wholeGrammarAdmitted',
            'ownConcreteGetterSemanticsProved','ownConcreteFactorySemanticsProved','generatedWrapperOnly'))
        and cap.get('ordinaryOriginalReadValueAdmitted')is False and type(cap.get('nullMarker'))is int and cap['nullMarker']==255)
    return cap


class SpecialAimReader:
    def __init__(self,reader):self.reader=reader

    def sector(self,depth=0):
        need('depth',type(depth)is int and 0<=depth<=64);r=self.reader;require_sector(r.operation.child(SECTOR))
        start=r.pos;null=r.peek()==255;fields=[]
        if null:r.take(1,SECTOR+'.null')
        else:
            r.header(3);at=r.pos;r.take(4,SECTOR+'.forwardType');fields.append(dict(fieldName='forwardType',start=at,end=r.pos))
            for name in('angle','radius'):
                need('double-depth',depth+1<=64);at=r.pos;r._profile('scalar_payload','scalar-payload',depth+1)
                fields.append(dict(fieldName=name,start=at,end=r.pos))
        out=dict(kind=SECTOR,start=start,end=r.pos,isNull=null,fields=fields);r.records.append(out);return out

    def union(self,depth=0):
        need('depth',type(depth)is int and 0<=depth<=64);r=self.reader;require_union(r.operation.child(CAPABILITY))
        start=r.pos;tag=r.peek();need('supported-canonical-short-tag',tag in(0,255))
        if tag==255:r.take(1,CAPABILITY+'.null');out=dict(kind=CAPABILITY,start=start,end=r.pos,isNull=True)
        else:
            need('sector-depth',depth+1<=64);require_sector(r.operation.child(SECTOR));r.take(1,CAPABILITY+'.tag0')
            child=self.sector(depth+1);out=dict(kind=CAPABILITY,start=start,end=r.pos,isNull=False,tag=0,child=child)
        r.records.append(out);return out

    def collection(self,depth=0):
        need('depth',type(depth)is int and 0<=depth<=64);r=self.reader;cap=r.operation.child(LIST)
        need('own-bounded-list',cap.get('elementType')==TYPE and cap.get('closedListType')=='System.Collections.Generic.List`1<'+TYPE+'>'
            and cap.get('elementValueType')is False and cap.get('elementCapability')==CAPABILITY
            and cap.get('collectionCounts')==[-1,0]and all(type(n)is int for n in cap['collectionCounts'])
            and type(cap.get('countLimit'))is int and 3<=cap['countLimit']<=10000
            and all(cap.get(k)is True for k in('nullable','positiveCountsAdmitted','elementGrammarAdmitted'))
            and type(cap.get('packableReaderMethodDefinition'))is int and cap['packableReaderMethodDefinition']>0
            and type(cap.get('packableReaderTargetRva'))is int and cap['packableReaderTargetRva']>0)
        require_union(r.operation.child(CAPABILITY));start=r.pos;count=r.count(cap['countLimit'],nullable=True)
        need('element-depth',count<=0 or depth+1<=64)
        for _ in range(max(count,0)):self.union(depth+1)
        out=dict(kind=LIST,start=start,end=r.pos,count=count);r.records.append(out);return out
