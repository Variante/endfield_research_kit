"""Finite FunctionArea base projection under its current owner capability."""
from scripts.game_data.memorypack import leveldata_function_area_sources as source


def validate(cap):
    from scripts.game_data.memorypack import leveldata_factory_hide_sources as hide_source
    positive=cap.get('positiveFactoryHideDescAdmitted')
    if type(positive)is not bool:raise ValueError('functionArea.exact-factory-hide-profile')
    plan=source.plan(positive_factory_hide=positive);hide_key=hide_source.CAP if positive else source.HIDE_CAP
    program=cap.get('program',{});child=lambda t:hide_key if t==source.HIDE else source.VECTOR_CAP if t==source.VECTORS else None
    if (cap.get('typeName')!=source.TYPE or type(cap.get('memberCount'))is not int or cap['memberCount']!=15
            or any(cap.get(k)is not True for k in('nullAdmitted','positiveAdmitted','profileAdmitted','finiteFloatProfile','actualCallbackEqualsProvedChildRequired'))
            or any(cap.get(k)is not False for k in('wholeGrammarAdmitted','liveFormatterSelectionObserved'))
            or type(cap.get('countLimit'))is not int or cap['countLimit']!=source.LIMIT
            or program.get('memberCount')!=15
            or any(type(r.get('memberIndex'))is not int for r in program.get('reads',[]))
            or [(r.get('memberIndex'),r.get('fieldName'),r.get('kind'),r.get('childCapability'))for r in program.get('reads',[])]!=[
                (i,n,k,child(t))for i,(n,t,k)in enumerate(plan)]
            or program.get('requiredCapabilities')!=sorted([hide_key,source.VECTOR_CAP])):
        raise ValueError('functionArea.exact-finite-base-profile')
    enums=cap.get('enumBackings',{});wanted={n:t for n,t,k in source.PLAN if k=='scalar32'and t!='int'}
    if set(enums)!=set(wanted):raise ValueError('functionArea.exact-enum-set')
    for name,typename in wanted.items():
        enum=enums[name]
        if enum.get('typeName')!=typename or enum.get('backing')not in('int','uint')or enum.get('field')!=[typename,enum.get('backing'),16]:
            raise ValueError('functionArea.exact-nominal-enum:'+name)
    bindings=program.get('childBindings',[])
    if ([(b.get('fieldName'),b.get('typeName'),b.get('capability'))for b in bindings]!=[
            ('factoryHideDesc',source.HIDE,hide_key),('posList',source.VECTORS,source.VECTOR_CAP)]
            or any(type(b.get('readerMethodDefinition'))is not int or b['readerMethodDefinition']<0
                or type(b.get('sourceTargetRva'))is not int or b['sourceTargetRva']<=0 for b in bindings)):
        raise ValueError('functionArea.exact-child-bindings')
    null,vector=bindings;selected=cap.get('vectorCollection',{})
    if positive:
        from scripts.game_data.codecs.leveldata.current_factory_hide import validate as validate_hide
        child=cap.get('factoryHideCapability',{});validate_hide(child)
        if dict(null,ownerType=source.TYPE)!=child['parentBinding']:
            raise ValueError('functionArea.exact-positive-factory-parent')
    elif ('factoryHideCapability'in cap or null.get('positiveAdmitted')is not False
            or type(null.get('nullMarker'))is not int or null['nullMarker']!=255
            or type(null.get('consumedBytes'))is not int or null['consumedBytes']!=1):
        raise ValueError('functionArea.exact-factory-FF-profile')
    if (selected.get('typeName')!=source.VECTORS or(selected.get('elementType'),selected.get('elementWireBytes'))!=('UnityEngine.Vector2',8)
            or selected.get('nullable')is not True or selected.get('positiveCountsAdmitted')is not True
            or selected.get('actualCallbackEqualsProvedChildRequired')is not True
            or type(selected.get('countLimit'))is not int or selected['countLimit']!=source.LIMIT
            or(vector.get('readerMethodDefinition'),vector.get('sourceTargetRva'))!=(selected.get('readerMethodDefinition'),selected.get('sourceTargetRva'))
            or vector.get('countLimit')!=source.LIMIT or vector.get('actualCallbackEqualsProvedChildRequired')is not True):
        raise ValueError('functionArea.exact-Vector2-profile')


def read(reader,field,cap):
    validate(cap);start=reader.offset
    if not reader.header(source.TYPE,15,field):return None
    out=dict(startOffset=start,recordType=source.TYPE,memberCount=15);spans={}
    for name,declared,kind in source.plan(positive_factory_hide=cap['positiveFactoryHideDescAdmitted']):
        at=reader.offset;path=field+'.'+name
        if kind=='float32-bits':value=reader.single(path)
        elif kind=='bool-byte':value=reader.boolean(path)
        elif kind=='unity-vector3-raw12':value={axis:reader.single(path+'.'+axis)for axis in'xyz'}
        elif kind=='scalar32':
            backing='int'if declared=='int'else cap['enumBackings'][name]['backing']
            value=reader.number('<i'if backing=='int'else'<I',path)
        elif kind=='scalar64-bits'and declared=='ulong':value=str(reader.number('<Q',path))
        elif kind=='factory-hide-null':
            marker=reader.number('<B',path)
            if marker!=255:reader.refuse(path,'current-positive-factory-hide-unproved',marker)
            value=None
        elif kind=='factory-hide-record':
            from scripts.game_data.codecs.leveldata.current_factory_hide import read as read_hide
            value=read_hide(reader,path,cap['factoryHideCapability'])
        elif kind=='vector2-list':
            count=reader.number('<i',path+'.count')
            if not -1<=count<=source.LIMIT:reader.refuse(path,'current-Vector2-count-profile',count)
            reader.need(max(count,0)*8,path+'.elements')
            values=[[reader.single(path+f'[{i}].'+axis)for axis in'xy']for i in range(max(count,0))]
            value=dict(startOffset=at,endOffset=reader.offset,count=count,rows=None if count==-1 else values)
        else:reader.refuse(path,'closed-function-area-operation',kind)
        out[name]=value;spans[name]=[at,reader.offset]
    out.update(endOffset=reader.offset,fieldRanges=spans)
    return out
