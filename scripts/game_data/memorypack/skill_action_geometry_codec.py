"""Finite operation-scoped collider and physics-source record bytes."""
from scripts.game_data.memorypack.skill_action_geometry_sources import RECORDS,ordered_reads

CAPABILITIES={spec['capability']:name for name,spec in RECORDS.items()}


def need(check,condition):
    if not condition:raise ValueError('skillActionGeometryCodec.'+check)


def require_capability(cap,name):
    need('finite-geometry-capability',name in CAPABILITIES)
    nominal=CAPABILITIES[name];order=ordered_reads(nominal)
    need('complete-exact-ordinary-source',cap.get('typeName')==nominal and cap.get('orderedReads')==order
        and type(cap.get('memberCount'))is int and cap['memberCount']==len(order)
        and type(cap.get('nullMarker'))is int and cap['nullMarker']==255
        and all(cap.get(k)is True for k in('nullable','nullAdmitted','wholeGrammarAdmitted',
            'ordinaryOriginalReadValueAdmitted','ownConcreteGetterSemanticsProved','ownConcreteFactorySemanticsProved'))
        and type(cap.get('referenceReaderMethodDefinition'))is int and cap['referenceReaderMethodDefinition']>0
        and type(cap.get('referenceReaderTargetRva'))is int and cap['referenceReaderTargetRva']>0)
    return cap


class GeometryReader:
    def __init__(self,reader):self.reader=reader

    def record(self,name,depth=0):
        need('depth',type(depth)is int and 0<=depth<=64);r=self.reader;cap=require_capability(r.operation.child(name),name)
        start=r.pos;fields=[];null=r.peek()==255
        if null:r.take(1,name+'.null')
        else:
            r.header(cap['memberCount'])
            for read in cap['orderedReads']:
                at=r.pos;kind=read['kind'];child=read['childCapability']
                if kind=='pooled-string':r.byte_payload()
                elif kind=='blackboard-vector3':
                    need('depth',depth+1<=64);r._profile('vector_payload',child,depth+1)
                else:r.take({'bool':1,'enum32':4,'single-bits':4,'unity-vector3-raw12':12}[kind],name+'.'+read['fieldName'])
                fields.append(dict(fieldName=read['fieldName'],start=at,end=r.pos))
        row=dict(kind=name,start=start,end=r.pos,isNull=null,fields=fields);r.records.append(row);return row
