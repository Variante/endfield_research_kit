"""Finite current FunctionArea-specific cursor; unsupported children stop it."""
from scripts.game_data.memorypack import leveldata_function_specific_components as source
from scripts.game_data.memorypack.leveldata_function_specific_leaves import bind_program,PLANS
from scripts.game_data.codecs.leveldata import current_function_specific_complex as complex_child


def validate_leaf(name,cap):
    plan=PLANS.get(name)
    if (plan is None or cap.get('typeName')!=name or type(cap.get('memberCount'))is not int or cap['memberCount']!=len(plan)
            or any(cap.get(k)is not True for k in('nullAdmitted','positiveAdmitted','profileAdmitted','finiteFloatProfile',
                'wrapperWireGrammarAdmitted','actualCallbackEqualsProvedChildRequired'))
            or any(cap.get(k)is not False for k in('wholeGrammarAdmitted','liveFormatterSelectionObserved','concreteOriginalAdapterUsed'))):
        raise ValueError('currentFunctionSpecific.exact-wrapper-child:'+str(name))
    declared=dict(wrappedType=name,orderedSourceReads=[dict(fieldName=n,declaredType=t)for n,t,k in plan])
    bind_program(name,declared,cap.get('program'),[])
    expected={n:t for n,t,k in plan if k=='scalar32'and t!='int'};enums=cap.get('enumBackings',{})
    if set(enums)!=set(expected):raise ValueError('currentFunctionSpecific.exact-enum-fields')
    for field,typename in expected.items():
        row=enums[field]
        if row.get('typeName')!=typename or row.get('backing')not in('int','uint')or row.get('field')!=[typename,row['backing'],16]:
            raise ValueError('currentFunctionSpecific.exact-enum-backing:'+typename)


def validate(cap):
    if not isinstance(cap,dict):raise ValueError('currentFunctionSpecific.missing-capability')
    routes=cap.get('routes');binding=cap.get('listParent',{});profile=cap.get('profileId')
    if(type(profile)is not str or profile not in source.PROFILES):raise ValueError('currentFunctionSpecific.explicit-profile')
    tags=source.PROFILES[profile]
    if (cap.get('typeName')!=source.TYPE or cap.get('admittedRouteTags')!=list(tags)
            or type(cap.get('admittedRouteTags'))is not list or any(type(tag)is not int for tag in cap['admittedRouteTags'])
            or not isinstance(routes,dict)or set(routes)!={str(t)for t in tags}
            or any(cap.get(k)is not True for k in('profileAdmitted','nullAdmitted','positiveAdmitted','actualCallbackEqualsProvedChildRequired'))
            or any(cap.get(k)is not False for k in('wholeGrammarAdmitted','liveFormatterSelectionObserved','concreteOriginalAdapterUsed'))
            or any(type(cap.get(k))is not int or cap[k]!=v for k,v in(('nodeLimit',source.NODE_LIMIT),('countLimit',source.COUNT_LIMIT)))
            or any(binding.get(k)!=v for k,v in dict(ownerType=source.PARENT,fieldName='specificDatas',typeName=source.LIST,
                capability=source.LIST_CAP,elementType=source.TYPE,countLimit=source.COUNT_LIMIT).items())
            or any(binding.get(k)is not True for k in('nullable','positiveCountsAdmitted','actualCallbackEqualsProvedChildRequired'))
            or type(binding.get('countLimit'))is not int
            or type(binding.get('readerMethodDefinition'))is not int or binding['readerMethodDefinition']<0
            or type(binding.get('sourceTargetRva'))is not int or binding['sourceTargetRva']<=0):
        raise ValueError('currentFunctionSpecific.exact-finite-profile-and-parent')
    for key,route in routes.items():
        tag=route.get('tag');name=route.get('typeName')
        if (type(tag)is not int or tag not in tags or key!=str(tag)or name!=source.CHILDREN[tag]
                or type(route.get('wrapperNullAdmitted'))is not bool
                or not isinstance(route.get('wrapperName'),str)or not route['wrapperName']
                or route.get('capability',{}).get('wrapperName')!=route['wrapperName']
                or route.get('actualWrapperCallbackEqualsProvedConcreteRequired')is not True):
            raise ValueError('currentFunctionSpecific.exact-route-identity')
        if tag in source.COMPLEX_TAGS:complex_child.validate(name,route.get('capability',{}))
        else:validate_leaf(name,route.get('capability',{}))


def _read(reader,field,cap):
    state=getattr(reader,'_current_specific_budget',None)
    if state is None:state=(cap,[cap['nodeLimit']]);reader._current_specific_budget=state
    elif state[0]is not cap:raise ValueError(field+':mixed-current-specific-capability')
    if state[1][0]<=0:raise ValueError(field+':specific-node-limit')
    state[1][0]-=1;start=reader.offset;tag=reader.number('<B',field+'.unionTag')
    if tag==255:return None
    if tag==250:raise ValueError(field+':extended-specific-tag-unproved')
    if 251<=tag<=254:raise ValueError(field+':reserved-union-marker')
    if tag not in source.PROFILES[cap['profileId']]:raise ValueError(field+':specific-child-grammar-unproved:'+str(tag))
    route=cap['routes'][str(tag)];child=route['capability'];name=route['typeName']
    at=reader.offset;reader.need(1,field+'.memberCount')
    if reader.data[at]==255 and route['wrapperNullAdmitted']is not True:
        raise ValueError(field+':specific-wrapper-null-unproved')
    if tag in source.COMPLEX_TAGS:
        value=complex_child._read(reader,field,name,child,state[1],charge_node=False)
        return dict(startOffset=start,endOffset=reader.offset,tag=tag,recordType=name,value=value)
    marker=reader.number('<B',field+'.memberCount')
    if marker==255:value=None
    else:
        if marker!=len(PLANS[name]):raise ValueError(field+':specific-member-count')
        value=dict(startOffset=at,recordType=name,memberCount=marker);spans={}
        for member,declared,kind in PLANS[name]:
            before=reader.offset;path=field+'.'+member
            if kind=='bool-byte':data=reader.boolean(path)
            elif kind=='float32-bits':data=reader.single(path)
            elif kind=='byte-payload':data=reader.string(path)
            elif kind=='scalar64-bits':data=str(reader.number('<Q',path))
            elif kind=='scalar32':data=reader.number('<I'if child['enumBackings'].get(member,{}).get('backing')=='uint'else'<i',path)
            elif kind=='gameplay-tag32':data=reader.number('<I',path)
            elif kind=='unity-vector3-raw12':data={axis:reader.single(path+'.'+axis)for axis in'xyz'}
            else:raise ValueError(field+':closed-specific-operation:'+kind)
            value[member]=data;spans[member]=[before,reader.offset]
        value.update(endOffset=reader.offset,fieldRanges=spans)
    return dict(startOffset=start,endOffset=reader.offset,tag=tag,recordType=name,value=value)


def read(reader,field,cap):validate(cap);return _read(reader,field,cap)


def read_list(reader,field,cap):
    validate(cap);start=reader.offset;count=reader.number('<i',field+'.count')
    if not -1<=count<=cap['countLimit']:raise ValueError(field+':specific-count-limit')
    reader.need(max(count,0),field+'.elements')
    rows=[_read(reader,field+f'[{i}]',cap)for i in range(max(count,0))]
    return dict(startOffset=start,endOffset=reader.offset,count=count,rows=None if count==-1 else rows)
