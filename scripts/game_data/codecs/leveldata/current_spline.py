"""Pure bounded current Spline7 profile; source authority stays in its owner."""
from scripts.game_data.memorypack import leveldata_spline_sources as source


def validate(cap):
    program=cap.get('program',{});child=lambda t:source.COLLECTIONS[t][0]if t in source.COLLECTIONS else None
    if (cap.get('typeName')!=source.TYPE or type(cap.get('memberCount'))is not int or cap['memberCount']!=7
            or any(cap.get(k)is not True for k in('nullAdmitted','positiveAdmitted','profileAdmitted','finiteFloatProfile','actualCallbackEqualsProvedChildRequired'))
            or any(cap.get(k)is not False for k in('wholeGrammarAdmitted','standaloneBezierElementAdmitted','liveFormatterSelectionObserved'))
            or program.get('memberCount')!=7
            or any(type(r.get('memberIndex'))is not int for r in program.get('reads',[]))
            or[(r.get('memberIndex'),r.get('fieldName'),r.get('kind'),r.get('childCapability'))for r in program.get('reads',[])]!=[
                (i,n,k,child(t))for i,(n,t,k)in enumerate(source.PLAN)]
            or program.get('requiredCapabilities')!=sorted(v[0]for v in source.COLLECTIONS.values())
            or set(cap.get('collections',{}))!={v[0]for v in source.COLLECTIONS.values()}):
        raise ValueError('currentSpline.exact-finite-profile')
    bindings=program.get('childBindings',[])
    if [(r.get('fieldName'),r.get('typeName'),r.get('capability'))for r in bindings]!=[
            (n,t,child(t))for n,t,k in source.PLAN if child(t)]:
        raise ValueError('currentSpline.exact-child-bindings')
    for binding in bindings:
        declared=binding['typeName'];key,kind,element,width=source.COLLECTIONS[declared];selected=cap['collections'][key]
        if (selected.get('typeName')!=declared or selected.get('elementType')!=element or selected.get('elementWireBytes')!=width
                or any(selected.get(k)is not True for k in('nullable','positiveCountsAdmitted','actualCallbackEqualsProvedChildRequired'))
                or type(selected.get('countLimit'))is not int or selected['countLimit']!=source.LIMIT
                or type(selected.get('readerMethodDefinition'))is not int or selected['readerMethodDefinition']<0
                or type(selected.get('sourceTargetRva'))is not int or selected['sourceTargetRva']<=0
                or(binding.get('readerMethodDefinition'),binding.get('sourceTargetRva'))!=(selected['readerMethodDefinition'],selected['sourceTargetRva'])
                or binding.get('countLimit')!=source.LIMIT or binding.get('actualCallbackEqualsProvedChildRequired')is not True):
            raise ValueError('currentSpline.exact-collection-profile:'+declared)
        if element==source.BEZIER and(selected.get('inlineElementSource')is not True
                or selected.get('closedElementRegistrationEquivalenceProved')is not False):
            raise ValueError('currentSpline.exact-inline-Bezier-boundary')


def read(reader,field,cap):
    validate(cap);start=reader.offset
    if not reader.header(source.TYPE,7,field):return None
    result=dict(startOffset=start,recordType=source.TYPE,memberCount=7);spans={}
    for name,declared,kind in source.PLAN:
        path=field+'.'+name;at=reader.offset
        if kind=='bool-byte':value=reader.boolean(path)
        elif kind=='scalar32':value=reader.number('<i',path)
        elif kind=='unity-vector3-raw12':value={axis:reader.single(path+'.'+axis)for axis in'xyz'}
        else:
            count=reader.number('<i',path+'.count')
            if not -1<=count<=source.LIMIT:reader.refuse(path,'current-Spline-count-limit',count)
            width=source.COLLECTIONS[declared][3];reader.need(max(count,0)*width,path+'.elements');values=[]
            for index in range(max(count,0)):
                child=path+f'[{index}]'
                if kind=='int32-list':row=reader.number('<i',child)
                elif kind=='float32-list':row=reader.single(child)
                elif kind=='bezier56-list':
                    knot_start=reader.offset;row={}
                    for slot in('Position','TangentIn','TangentOut'):
                        row[slot]={axis:reader.single(child+'.'+slot+'.'+axis)for axis in'xyz'}
                    row['Rotation']={axis:reader.single(child+'.Rotation.'+axis)for axis in'xyzw'}
                    row['Width']=reader.single(child+'.Width');row.update(startOffset=knot_start,endOffset=reader.offset)
                else:reader.refuse(path,'closed-Spline-list-operation',kind)
                values.append(row)
            value=dict(startOffset=at,endOffset=reader.offset,count=count,rows=None if count==-1 else values)
        result[name]=value;spans[name]=[at,reader.offset]
    result.update(endOffset=reader.offset,fieldRanges=spans);return result
