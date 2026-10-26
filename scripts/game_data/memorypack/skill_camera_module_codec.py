"""Finite thirteen-route camera module and record/list cursor programs.

Every field and nested curve is guarded by its own freshly authenticated
capability. Short tags, canonical FF and signed collection counts retain their
separate framing. This driver grants no export/root admission or runtime camera
semantics; callback/provider and normal native conditions stay with the owners.
"""
import struct

from scripts.game_data.memorypack import skill_camera_module_components as source

BY_CAPABILITY={spec['capability']:name for name,spec in source.RECORDS.items()}


def need(check,condition):
    if not condition:raise ValueError('skillCameraModuleCodec.'+check)


def require_record(cap,name):
    need('finite-record',name in BY_CAPABILITY);nominal=BY_CAPABILITY[name];spec=source.RECORDS[nominal];order=source.ordered_reads(nominal)
    need('complete-exact-concrete-record',(cap.get('typeName'),cap.get('wrapperName'))==(nominal,spec['wrapperName'])
        and type(cap.get('memberCount'))is int and cap['memberCount']==len(order)and cap.get('orderedReads')==order
        and all(type(r.get('memberIndex'))is int for r in cap['orderedReads'])
        and type(cap.get('nullMarker'))is int and cap['nullMarker']==255
        and all(cap.get(k)is True for k in('nullable','nullAdmitted','wholeGrammarAdmitted','ownConcreteGetterSemanticsProved',
            'ownConcreteFactorySemanticsProved','generatedWrapperOnly'))
        and cap.get('ordinaryOriginalReadValueAdmitted')is False)
    return cap


def require_union(cap):
    need('complete-exact-base-union',(cap.get('typeName'),cap.get('wrapperName'))==(source.TYPE,source.WRAPPER)
        and type(cap.get('nullMarker'))is int and cap['nullMarker']==255
        and all(cap.get(k)is True for k in('nullable','nullAdmitted','wholeGrammarAdmitted','ordinaryOriginalReadValueAdmitted',
            'baseGetterSemanticsProved','concreteChildGrammarsProved','allConcreteFactoriesProved'))
        and cap.get('extendedTagsAdmitted')is False and cap.get('reservedMarkersAdmitted')is False
        and type(cap.get('referenceReaderMethodDefinition'))is int and cap['referenceReaderMethodDefinition']>0
        and type(cap.get('referenceReaderTargetRva'))is int and cap['referenceReaderTargetRva']>0)
    tags=cap.get('supportedShortTags',[]);routes=cap.get('routes',[])
    need('literal-thirteen-route-domain',tags==list(range(13))and all(type(t)is int for t in tags)
        and len(routes)==13 and[r.get('tag')for r in routes]==tags and all(type(r.get('tag'))is int for r in routes))
    need('exact-finite-nominal-routes',{r.get('wrappedType')for r in routes}==set(source.RECORDS)
        and all((r.get('wrapperName'),r.get('childCapability'))==(source.RECORDS[r['wrappedType']]['wrapperName'],
            source.RECORDS[r['wrappedType']]['capability'])for r in routes))
    return cap


def require_collection(cap):
    need('exact-reference-list',cap.get('elementType')==source.TYPE and cap.get('elementValueType')is False
        and cap.get('closedListType')=='System.Collections.Generic.List`1<'+source.TYPE+'>'
        and cap.get('elementCapability')==source.CAPABILITY and cap.get('collectionCounts')==[-1,0]
        and all(type(n)is int for n in cap['collectionCounts'])
        and type(cap.get('countLimit'))is int and cap['countLimit']==10000
        and all(cap.get(k)is True for k in('nullable','positiveCountsAdmitted','elementGrammarAdmitted'))
        and type(cap.get('packableReaderMethodDefinition'))is int and cap['packableReaderMethodDefinition']>0
        and type(cap.get('packableReaderTargetRva'))is int and cap['packableReaderTargetRva']>0)
    return cap


class CameraModuleReader:
    def __init__(self,reader):self.reader=reader

    def record(self,name,depth=0):
        need('depth',type(depth)is int and 0<=depth<=64);r=self.reader;cap=require_record(r.operation.child(name),name)
        start=r.pos;fields=[];null=r.peek()==255
        if null:r.take(1,name+'.null')
        else:
            r.header(cap['memberCount']);nominal=BY_CAPABILITY[name]
            for field,typ in source.RECORDS[nominal]['members']:
                at=r.pos
                if typ==source.CURVE:
                    need('curve-depth',depth+1<=64)
                    from scripts.game_data.memorypack.skill_animation_curve_codec import require_capability
                    require_capability(r.operation.child('curve-profile'));r._profile('curve_profile','curve-profile',depth+1)
                else:r.take(1 if typ=='bool'else 4,name+'.'+field)
                fields.append(dict(fieldName=field,start=at,end=r.pos))
        result=dict(kind=name,start=start,end=r.pos,isNull=null,fields=fields);r.records.append(result);return result

    def union(self,depth=0):
        need('depth',type(depth)is int and 0<=depth<=64);r=self.reader;cap=require_union(r.operation.child(source.CAPABILITY));start=r.pos
        tag=r.peek()
        if tag==255:r.take(1,source.CAPABILITY+'.null');result=dict(kind=source.CAPABILITY,start=start,end=r.pos,isNull=True)
        else:
            need('literal-supported-short-tag',0<=tag<13);need('child-depth',depth+1<=64);route=cap['routes'][tag]
            require_record(r.operation.child(route['childCapability']),route['childCapability'])
            r.take(1,source.CAPABILITY+'.tag');child=self.record(route['childCapability'],depth+1)
            result=dict(kind=source.CAPABILITY,start=start,end=r.pos,isNull=False,tag=tag,child=child)
        r.records.append(result);return result

    def collection(self,depth=0):
        need('depth',type(depth)is int and 0<=depth<=64);r=self.reader;cap=require_collection(r.operation.child(source.LIST));start=r.pos
        need('complete-signed-count',r.pos+4<=r.limit);count=struct.unpack_from('<i',r.data,r.pos)[0]
        need('bounded-signed-count',-1<=count<=cap['countLimit'])
        if count>0:
            need('element-depth',depth+1<=64);require_union(r.operation.child(source.CAPABILITY))
        r.take(4,source.LIST+'.count')
        for _ in range(max(0,count)):self.union(depth+1)
        result=dict(kind=source.LIST,start=start,end=r.pos,count=count,isNull=count==-1);r.records.append(result);return result
