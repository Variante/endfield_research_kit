"""Finite source-owned PolyLineShape profile; no native gate is opened here."""
from scripts.game_data.memorypack import leveldata_polyline_sources as source


def validate(cap):
    from scripts.game_data.codecs.leveldata import current_polyline_graph as graph
    if cap.get('schema')==graph.source.SCHEMA:return graph.validate(cap)
    program=cap.get('program',{});child=lambda t:source.COLLECTIONS[t][0]if t in source.COLLECTIONS else source.NULL_CAP if t==source.TREE else None
    if (cap.get('typeName')!=source.TYPE or type(cap.get('memberCount'))is not int or cap['memberCount']!=12
            or any(cap.get(k)is not True for k in('nullAdmitted','positiveAdmitted','profileAdmitted','finiteFloatProfile','actualCallbackEqualsProvedChildRequired'))
            or any(cap.get(k)is not False for k in('wholeGrammarAdmitted','positiveBvhNodesAdmitted','positiveConvexPolygonsAdmitted','positiveTreeAdmitted','liveFormatterSelectionObserved'))
            or program.get('memberCount')!=12
            or any(type(r.get('memberIndex'))is not int for r in program.get('reads',[]))
            or [(r.get('memberIndex'),r.get('fieldName'),r.get('kind'),r.get('childCapability'))for r in program.get('reads',[])]!=[
                (i,n,k,child(t))for i,(n,t,k)in enumerate(source.PLAN)]
            or program.get('requiredCapabilities')!=sorted([v[0]for v in source.COLLECTIONS.values()]+[source.NULL_CAP])
            or set(cap.get('collections',{}))!={v[0]for v in source.COLLECTIONS.values()}):
        raise ValueError('currentPolyline.exact-finite-profile')
    bindings=program.get('childBindings',[])
    if ([(r.get('fieldName'),r.get('typeName'),r.get('capability'))for r in bindings]!=[
            (n,t,child(t))for n,t,k in source.PLAN if child(t)]
            or any(type(r.get('readerMethodDefinition'))is not int or type(r.get('sourceTargetRva'))is not int
                or r['readerMethodDefinition']<0 or r['sourceTargetRva']<=0 for r in bindings)):
        raise ValueError('currentPolyline.exact-child-bindings')
    for binding in bindings:
        key=binding['capability']
        if key==source.NULL_CAP:
            if (binding.get('positiveAdmitted')is not False or type(binding.get('nullMarker'))is not int
                    or binding['nullMarker']!=255 or type(binding.get('consumedBytes'))is not int or binding['consumedBytes']!=1):
                raise ValueError('currentPolyline.exact-tree-FF-profile')
            continue
        declared=binding['typeName'];expected=source.COLLECTIONS[declared];collection=cap['collections'][key]
        if (collection.get('typeName')!=declared or collection.get('elementType')!=expected[2]
                or collection.get('nullable')is not True or collection.get('positiveCountsAdmitted')is not expected[3]
                or collection.get('elementWireBytes')!=expected[4]
                or type(collection.get('countLimit'))is not int or collection['countLimit']!=(source.LIMIT if expected[3]else 0)
                or collection.get('collectionCounts')!=[-1,0]or any(type(n)is not int for n in collection['collectionCounts'])
                or collection.get('actualCallbackEqualsProvedChildRequired')is not True
                or (collection.get('readerMethodDefinition'),collection.get('sourceTargetRva'))!=(binding['readerMethodDefinition'],binding['sourceTargetRva'])
                or binding.get('positiveCountsAdmitted')is not expected[3]or binding.get('countLimit')!=collection['countLimit']
                or binding.get('actualCallbackEqualsProvedChildRequired')is not True):
            raise ValueError('currentPolyline.exact-collection-profile:'+declared)


def read(reader,field,cap):
    from scripts.game_data.codecs.leveldata import current_polyline_graph as graph
    if cap.get('schema')==graph.source.SCHEMA:return graph.read(reader,field,cap)
    validate(cap);start=reader.offset
    if not reader.header(source.TYPE,12,field):return None
    result=dict(startOffset=start,recordType=source.TYPE,memberCount=12);ranges={}
    for name,declared,kind in source.PLAN:
        at=reader.offset;path=field+'.'+name
        if kind=='float32-bits':value=reader.single(path)
        elif kind=='bool-byte':value=reader.boolean(path)
        elif kind=='unity-vector3-raw12':value={axis:reader.single(path+'.'+axis)for axis in'xyz'}
        elif declared==source.TREE:
            marker=reader.number('<B',path)
            if marker!=255:reader.refuse(path,'current-positive-BVH-tree-unproved',marker)
            value=None
        else:
            expected=source.COLLECTIONS[declared];limit=source.LIMIT if expected[3]else 0
            count=reader.number('<i',path+'.count')
            if not -1<=count<=limit:reader.refuse(path,'current-collection-count-profile',count)
            values=[]
            if count>0:
                reader.need(count*expected[4],path+'.elements')
                for index in range(count):
                    if kind=='int32-list':values.append(reader.number('<i',path+f'[{index}]'))
                    elif kind=='vector2-list':values.append([reader.single(path+f'[{index}].'+axis)for axis in'xy'])
                    else:reader.refuse(path,'current-positive-cached-child-unproved',count)
            value=dict(startOffset=at,endOffset=reader.offset,count=count,rows=None if count==-1 else values)
        result[name]=value;ranges[name]=[at,reader.offset]
    result.update(endOffset=reader.offset,fieldRanges=ranges)
    return result
