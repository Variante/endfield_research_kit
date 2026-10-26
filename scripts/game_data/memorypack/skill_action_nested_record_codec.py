"""Finite action settings under the same selected cursor/pool/child operation.

This inactive domain driver admits only its declared ordinary record caps.
Every delegated ordinary child is checked before its FF or positive bytes;
Unity curve keeps its separate direct custom-formatter source gate. No list,
action union, runtime effect or whole-file framing follows from this parser.
"""
from scripts.game_data.memorypack.skill_action_nested_record_sources import RECORDS,REFERENCES,VALUE_TYPES,CURVE,SEQUENCE,LINE_END,ordered_reads

CAPABILITIES={spec['capability']:name for name,spec in RECORDS.items()}


def need(check,condition):
    if not condition:raise ValueError('skillActionNestedRecordCodec.'+check)


def require_capability(cap,name):
    need('finite-record',name in CAPABILITIES);nominal=CAPABILITIES[name];order=ordered_reads(nominal)
    need('complete-own-ordinary-record',cap.get('typeName')==nominal and cap.get('orderedReads')==order
        and type(cap.get('memberCount'))is int and cap['memberCount']==len(order)
        and type(cap.get('nullMarker'))is int and cap['nullMarker']==255
        and all(cap.get(k)is True for k in('nullable','nullAdmitted','wholeGrammarAdmitted','ordinaryOriginalReadValueAdmitted',
            'ownConcreteGetterSemanticsProved','ownConcreteFactorySemanticsProved'))
        and type(cap.get('referenceReaderMethodDefinition'))is int and cap['referenceReaderMethodDefinition']>0
        and type(cap.get('referenceReaderTargetRva'))is int and cap['referenceReaderTargetRva']>0)
    return cap


def require_child(cap,type_name):
    if type_name==CURVE:
        from scripts.game_data.memorypack.skill_animation_curve_codec import require_capability as curve
        return curve(cap)
    need('exact-ordinary-child',type_name in REFERENCES and cap.get('typeName')==type_name
        and all(cap.get(k)is True for k in('wholeGrammarAdmitted','ordinaryOriginalReadValueAdmitted',
            'ownConcreteGetterSemanticsProved','ownConcreteFactorySemanticsProved'))
        and type(cap.get('referenceReaderMethodDefinition'))is int and cap['referenceReaderMethodDefinition']>0
        and type(cap.get('referenceReaderTargetRva'))is int and cap['referenceReaderTargetRva']>0)
    return cap


class NestedRecordReader:
    def __init__(self,reader):self.reader=reader

    def record(self,name,depth=0):
        need('depth',type(depth)is int and 0<=depth<=64);r=self.reader;cap=require_capability(r.operation.child(name),name)
        start=r.pos;fields=[];null=r.peek()==255
        if null:r.take(1,name+'.null')
        else:
            nominal=CAPABILITIES[name];r.header(cap['memberCount'])
            for field,type_name,kind,child in RECORDS[nominal]['members']:
                at=r.pos
                if kind=='pooled-string':r.byte_payload()
                elif type_name in VALUE_TYPES:
                    need('depth',depth+1<=64)
                    from scripts.game_data.memorypack.skill_root_children_codec import RootChildrenReader
                    RootChildrenReader(r).record(child,depth+1)
                elif type_name in REFERENCES:
                    need('depth',depth+1<=64);require_child(r.operation.child(child),type_name)
                    if type_name==SEQUENCE:r._sequence(depth+1)
                    elif type_name==LINE_END:self.record(child,depth+1)
                    else:r._profile({'blackboard-double':'scalar_payload','blackboard-vector3':'vector_payload',
                        'target-profile':'target_profile','curve-profile':'curve_profile'}[kind],child,depth+1)
                else:r.take({'bool':1,'enum32':4,'int32':4,'single-bits':4}[kind],name+'.'+field)
                fields.append(dict(fieldName=field,start=at,end=r.pos))
        out=dict(kind=name,start=start,end=r.pos,isNull=null,fields=fields);r.records.append(out);return out
