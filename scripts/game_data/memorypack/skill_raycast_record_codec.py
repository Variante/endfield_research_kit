"""Finite RayCast record driver, with per-child source gates.

Raw Vector3 bytes are admitted only by this record's complete native program.
BlackboardVector3 remains a variable three-Blackboard child; Unity curve keeps
its independently proved custom formatter. No list/action/root is selected by
this driver, and no raycast or effect execution follows from stored fields.
"""
from scripts.game_data.memorypack import skill_raycast_record_sources as source

CAPABILITIES={spec['capability']:name for name,spec in source.RECORDS.items()}


def need(check,condition):
    if not condition:raise ValueError('skillRaycastRecordCodec.'+check)


def require_capability(cap,name):
    need('finite-raycast-record',name in CAPABILITIES);nominal=CAPABILITIES[name];order=source.ordered_reads(nominal)
    need('complete-exact-own-ordinary-record',cap.get('typeName')==nominal and cap.get('wrapperName')==source.RECORDS[nominal]['wrapperName']
        and type(cap.get('memberCount'))is int and cap['memberCount']==len(order)and cap.get('orderedReads')==order
        and type(cap.get('nullMarker'))is int and cap['nullMarker']==255
        and all(cap.get(k)is True for k in('nullable','nullAdmitted','wholeGrammarAdmitted','ordinaryOriginalReadValueAdmitted',
            'ownConcreteGetterSemanticsProved','ownConcreteFactorySemanticsProved','completeSourceOwnedProgram'))
        and type(cap.get('referenceReaderMethodDefinition'))is int and cap['referenceReaderMethodDefinition']>0
        and type(cap.get('referenceReaderTargetRva'))is int and cap['referenceReaderTargetRva']>0)
    return cap


def require_child(cap,nominal):
    if nominal==source.CURVE:
        from scripts.game_data.memorypack.skill_animation_curve_codec import require_capability as curve
        return curve(cap)
    need('exact-ordinary-BlackboardVector3',nominal==source.VECTOR and cap.get('typeName')==source.VECTOR
        and all(cap.get(k)is True for k in('wholeGrammarAdmitted','ordinaryOriginalReadValueAdmitted',
            'ownConcreteGetterSemanticsProved','ownConcreteFactorySemanticsProved'))
        and type(cap.get('referenceReaderMethodDefinition'))is int and cap['referenceReaderMethodDefinition']>0
        and type(cap.get('referenceReaderTargetRva'))is int and cap['referenceReaderTargetRva']>0)
    return cap


class RaycastRecordReader:
    def __init__(self,reader):self.reader=reader

    def record(self,name,depth=0):
        need('depth',type(depth)is int and 0<=depth<=64);r=self.reader;cap=require_capability(r.operation.child(name),name)
        start=r.pos;fields=[];null=r.peek()==255
        if null:r.take(1,name+'.null')
        else:
            r.header(cap['memberCount']);nominal=CAPABILITIES[name]
            for field,type_name,kind,child in source.RECORDS[nominal]['members']:
                at=r.pos
                if type_name in source.REFERENCES:
                    need('depth',depth+1<=64);require_child(r.operation.child(child),type_name)
                    r._profile('curve_profile'if type_name==source.CURVE else'vector_payload',child,depth+1)
                else:r.take({'enum32':4,'int32':4,'bool':1,'single-bits':4,'unity-vector3-raw12':12}[kind],name+'.'+field)
                fields.append(dict(fieldName=field,start=at,end=r.pos))
        out=dict(kind=name,start=start,end=r.pos,isNull=null,fields=fields);r.records.append(out);return out
