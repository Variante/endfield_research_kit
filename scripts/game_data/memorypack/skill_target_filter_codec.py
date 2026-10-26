"""Finite TargetFilter bytes under the enclosing authenticated operation."""
from scripts.game_data.memorypack.skill_target_filter_sources import TYPE,CAPABILITY,QUERY_CAP,ORDER


def need(check,condition):
    if not condition:raise ValueError('skillTargetFilterCodec.'+check)


def require_capability(cap):
    need('exact-own-ordinary-source',cap.get('typeName')==TYPE and cap.get('orderedReads')==ORDER
        and type(cap.get('memberCount'))is int and cap['memberCount']==10
        and all(type(r.get('memberIndex'))is int for r in cap['orderedReads'])
        and type(cap.get('nullMarker'))is int and cap['nullMarker']==255
        and all(cap.get(k)is True for k in('nullable','nullAdmitted','wholeGrammarAdmitted',
            'ordinaryOriginalReadValueAdmitted','ownConcreteGetterSemanticsProved',
            'ownConcreteFactorySemanticsProved','completeSourceOwnedProgram'))
        and type(cap.get('referenceReaderMethodDefinition'))is int and cap['referenceReaderMethodDefinition']>0
        and type(cap.get('referenceReaderTargetRva'))is int and cap['referenceReaderTargetRva']>0)
    return cap


class TargetFilterReader:
    def __init__(self,reader):self.reader=reader

    def read(self,depth=0):
        need('depth',type(depth)is int and 0<=depth<=64);r=self.reader
        cap=require_capability(r.operation.child(CAPABILITY));start=r.pos;fields=[];null=r.peek()==255
        if null:r.take(1,CAPABILITY+'.null')
        else:
            r.header(10)
            for field in cap['orderedReads']:
                at=r.pos
                if field['kind']=='root-record':
                    need('nested-query-depth',depth+1<=64)
                    from scripts.game_data.memorypack.skill_root_children_codec import RootChildrenReader
                    RootChildrenReader(r).record(QUERY_CAP,depth+1)
                else:r.take({'bool-byte':1,'scalar32':4}[field['kind']],CAPABILITY+'.'+field['fieldName'])
                fields.append(dict(fieldName=field['fieldName'],start=at,end=r.pos))
        out=dict(kind=CAPABILITY,start=start,end=r.pos,isNull=null,fields=fields);r.records.append(out);return out
