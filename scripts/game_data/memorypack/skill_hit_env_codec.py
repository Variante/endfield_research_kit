"""Source-owned HitEnvData MC4 under the enclosing authenticated operation.

The Int64 mask is eight stored bits-bytes; native object field padding does not
enter the wire. The CalculationBase child uses the same cursor, operation and
finite union gate. This codec performs no native admission or hit evaluation.
"""
from scripts.game_data.memorypack.skill_hit_env_sources import TYPE,CAPABILITY,ORDER,CHILD


def need(check,condition):
    if not condition:raise ValueError('skillHitEnvCodec.'+check)


class HitEnvReader:
    def __init__(self,reader):self.reader=reader

    def read(self,depth=0):
        need('depth',type(depth)is int and 0<=depth<=64);r=self.reader;cap=r.operation.child(CAPABILITY)
        need('exact-source-owned-record',cap.get('typeName')==TYPE and type(cap.get('memberCount'))is int and cap['memberCount']==4
            and type(cap.get('nullMarker'))is int and cap['nullMarker']==255 and cap.get('orderedReads')==ORDER
            and all(type(read.get('memberIndex'))is int for read in cap['orderedReads'])
            and all(cap.get(k)is True for k in('nullAdmitted','wholeGrammarAdmitted','ordinaryOriginalReadValueAdmitted',
                'ownConcreteGetterSemanticsProved','ownConcreteFactorySemanticsProved','completeSourceOwnedProgram'))
            and type(cap.get('referenceReaderMethodDefinition'))is int and cap['referenceReaderMethodDefinition']>0
            and type(cap.get('referenceReaderTargetRva'))is int and cap['referenceReaderTargetRva']>0)
        start=r.pos;fields=[];null=r.peek()==255
        if null:r.take(1,CAPABILITY+'.null')
        else:
            r.header(4)
            for field,width in(('damageDecorateMask',8),('dontHitImportInteractive',1),('inheritFirstDamageMask',1)):
                at=r.pos;r.take(width,TYPE+'.'+field);fields.append(dict(fieldName=field,start=at,end=r.pos))
            from scripts.game_data.memorypack.skill_damage_children_codec import DamageChildrenReader
            at=r.pos;DamageChildrenReader(r).union(CHILD,depth+1)
            fields.append(dict(fieldName='valueCalculation',start=at,end=r.pos))
        out=dict(kind=CAPABILITY,start=start,end=r.pos,isNull=null,fields=fields);r.records.append(out);return out
