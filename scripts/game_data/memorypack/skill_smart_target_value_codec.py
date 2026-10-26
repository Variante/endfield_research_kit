"""Finite MC4/FF SmartTarget value codec behind an authenticated capability."""
from scripts.game_data.memorypack.skill_smart_target_value_sources import TYPE,CAPABILITY,ORDER

LABEL='skillSmartTargetValueCodec'


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def require_capability(cap):
    need('exact-nominal-value',isinstance(cap,dict)and cap.get('typeName')==TYPE
        and all(type(cap.get(k))is int and cap[k]==v for k,v in
            (('memberCount',4),('managedBytes',40),('nullMarker',255),('nullWireBytes',1)))
        and cap.get('referenceLaneOffsets')==[8,24,32]
        and all(type(n)is int for n in cap['referenceLaneOffsets']))
    need('complete-own-source-and-default',all(cap.get(k)is True for k in
        ('nullable','nullReturnsDefaultValue','wholeGrammarAdmitted','ownConcreteGetterSemanticsProved',
            'ownConcreteFactorySemanticsProved','actualValueReadValueAdmitted','callbackSelectionConditional'))
        and cap.get('ordinaryOriginalReadValueAdmitted')is False
        and cap.get('wireBytes')is None and cap.get('positiveWireBytes')is None)
    need('exact-ordered-child-grammar',cap.get('orderedReads')==ORDER)
    need('actual-value-reader-identities',all(type(cap.get(k))is int and cap[k]>0 for k in
        ('valueReaderMethodDefinition','valueSourceTargetRva','valueDispatcherTargetRva')))
    return cap


class SmartTargetValueReader:
    def __init__(self,reader):self.reader=reader

    def record(self,depth=0):
        from scripts.game_data.memorypack.skill_root_children_codec import RootChildrenReader
        need('bounded-depth',type(depth)is int and 0<=depth<=64)
        r=self.reader;cap=require_capability(r.operation.child(CAPABILITY));start=r.pos
        if r.peek()==255:
            r.take(1,CAPABILITY+'.default')
            out=dict(start=start,end=r.pos,kind=CAPABILITY,isNull=True,returnsDefaultValue=True,fields=[])
        else:
            r.header(cap['memberCount']);children=RootChildrenReader(r);fields=[]
            for field,kind,child in((row['fieldName'],row['kind'],row['childCapability'])for row in ORDER):
                at=r.pos
                if kind=='record':children.record(child,depth+1)
                elif kind=='value-list':children.collection(child,depth+1)
                else:r.take(4,CAPABILITY+'.'+field+'.enum32')
                fields.append(dict(fieldName=field,start=at,end=r.pos))
            out=dict(start=start,end=r.pos,kind=CAPABILITY,isNull=False,memberCount=4,fields=fields)
        r.records.append(out);return out
