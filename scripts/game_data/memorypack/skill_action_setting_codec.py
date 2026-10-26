"""Exact finite duration/keyword setting codecs under one selected operation."""
from scripts.game_data.memorypack.skill_action_setting_sources import RECORDS,ordered_reads

CAPABILITIES={v['capability']:t for t,v in RECORDS.items()}


def need(check,condition):
    if not condition:raise ValueError('skillActionSettingCodec.'+check)


class ActionSettingReader:
    def __init__(self,reader):self.reader=reader

    def record(self,name,depth=0):
        need('depth',type(depth)is int and 0<=depth<=64);need('known-setting',name in CAPABILITIES)
        typename=CAPABILITIES[name];order=ordered_reads(typename);r=self.reader
        require_capability(r.operation.child(name),name)
        start=r.pos;fields=[];null=r.peek()==255
        if null:r.take(1,name+'.null')
        else:
            r.header(len(order))
            for read in order:
                at=r.pos;kind=read['kind'];child=read['childCapability']
                if kind=='enum32':r.take(4,name+'.'+read['fieldName'])
                elif kind=='byte-payload':r.byte_payload()
                elif kind=='root-pooled-string-list':
                    from scripts.game_data.memorypack.skill_root_children_codec import RootChildrenReader
                    RootChildrenReader(r).pooled_strings(child,depth+1)
                else:
                    need('depth',depth+1<=64);scalar=r.operation.child(child)
                    need('exact-ordinary-BlackboardDouble',scalar.get('typeName')=='Beyond.Blackboard+BlackboardDouble'
                        and all(scalar.get(k)is True for k in('wholeGrammarAdmitted','ordinaryOriginalReadValueAdmitted',
                            'ownConcreteGetterSemanticsProved','ownConcreteFactorySemanticsProved'))
                        and type(scalar.get('referenceReaderMethodDefinition'))is int and scalar['referenceReaderMethodDefinition']>0
                        and type(scalar.get('referenceReaderTargetRva'))is int and scalar['referenceReaderTargetRva']>0)
                    r._profile('scalar_payload',child,depth+1)
                fields.append(dict(fieldName=read['fieldName'],start=at,end=r.pos))
        out=dict(kind=name,start=start,end=r.pos,isNull=null,fields=fields);r.records.append(out);return out


def require_capability(cap,name):
    need('known-setting',name in CAPABILITIES)
    typename=CAPABILITIES[name];order=ordered_reads(typename)
    need('exact-source-owned-setting',cap.get('typeName')==typename and cap.get('orderedReads')==order
        and type(cap.get('memberCount'))is int and cap['memberCount']==len(order)
        and all(type(read.get('memberIndex'))is int for read in cap['orderedReads'])
        and type(cap.get('nullMarker'))is int and cap['nullMarker']==255
        and all(cap.get(k)is True for k in('nullAdmitted','wholeGrammarAdmitted','ordinaryOriginalReadValueAdmitted',
            'ownConcreteGetterSemanticsProved','ownConcreteFactorySemanticsProved','completeSourceOwnedProgram'))
        and type(cap.get('referenceReaderMethodDefinition'))is int and cap['referenceReaderMethodDefinition']>0
        and type(cap.get('referenceReaderTargetRva'))is int and cap['referenceReaderTargetRva']>0)
    return cap
