"""Finite condition leaf cursors; only an authenticated owner supplies caps."""
from scripts.game_data.memorypack.leveldata_condition_leaf_sources import PLANS
from scripts.game_data.memorypack.leveldata_condition_runtime_sources import CHILDREN
from scripts.game_data.memorypack import leveldata_condition_components as source
from scripts.game_data.codecs.levelscript.param_graph import ParamGraphDecodeError


def validate_leaf(name,cap):
    plan=PLANS.get(name);program=cap.get('program',{})
    if (plan is None or cap.get('typeName')!=name or type(cap.get('memberCount'))is not int or cap['memberCount']!=len(plan)
            or any(cap.get(k)is not True for k in('nullAdmitted','positiveAdmitted','wholeGrammarAdmitted','actualCallbackEqualsProvedChildRequired'))
            or cap.get('liveFormatterSelectionObserved')is not False or program.get('memberCount')!=len(plan)
            or any(type(r.get('memberIndex'))is not int for r in program.get('reads',[]))
            or[(r.get('memberIndex'),r.get('fieldName'),r.get('kind'),r.get('childCapability'))for r in program.get('reads',[])]!=[
                (i,n,k,'byte-payload'if k=='byte-payload'else None)for i,(n,t,k)in enumerate(plan)]
            or program.get('requiredCapabilities')!=['byte-payload']or program.get('childBindings')!=[]):
        raise ParamGraphDecodeError('currentCondition.exact-nominal-leaf-program:'+name)
    wanted={n:t for n,t,k in plan if k=='scalar32'};enums=cap.get('enumBackings',{})
    if set(enums)!=set(wanted):raise ParamGraphDecodeError('currentCondition.exact-enum-set:'+name)
    for field,typename in wanted.items():
        row=enums[field]
        if (row.get('typeName')!=typename or row.get('backing')not in('int','uint')
                or row.get('field')!=[typename,row.get('backing'),16]):
            raise ParamGraphDecodeError('currentCondition.exact-nominal-enum:'+typename)


def read_leaf(reader,field,name,cap):
    """Read only the explicitly compiled nominal leaf, including its own FF."""
    validate_leaf(name,cap);start=reader.offset;marker=reader.number('<B',field+'.memberCount')
    if marker==255:return None
    expected=len(PLANS[name])
    if marker!=expected:raise ParamGraphDecodeError(f'{field}:member-count,offset={start},expected={expected},actual={marker}')
    out=dict(startOffset=start,recordType=name,memberCount=expected);spans={}
    for member,declared,kind in PLANS[name]:
        at=reader.offset;path=field+'.'+member
        if kind=='byte-payload':value=reader.string(path)
        elif kind=='scalar32':value=reader.number('<i'if cap['enumBackings'][member]['backing']=='int'else'<I',path)
        else:raise ParamGraphDecodeError('currentCondition.closed-leaf-operation:'+kind)
        out[member]=value;spans[member]=[at,reader.offset]
    out.update(endOffset=reader.offset,fieldRanges=spans);return out


def validate(cap):
    routes=cap.get('routes')
    if (cap.get('typeName')!=source.TYPE
            or any(cap.get(k)is not True for k in('nullAdmitted','positiveAdmitted','profileAdmitted','actualCallbackEqualsProvedChildRequired'))
            or cap.get('wholeGrammarAdmitted')is not False or cap.get('liveFormatterSelectionObserved')is not False
            or cap.get('admittedRouteTags')!=list(source.TAGS)or not isinstance(routes,dict)or set(routes)!={str(tag)for tag in source.TAGS}
            or any(type(cap.get(k))is not int or cap[k]!=value for k,value in(
                ('countLimit',source.COUNT_LIMIT),('nodeLimit',source.NODE_LIMIT),('depthLimit',source.DEPTH_LIMIT)))
            or type(cap.get('referenceReaderMethodDefinition'))is not int or cap['referenceReaderMethodDefinition']<0
            or type(cap.get('referenceReaderTargetRva'))is not int or cap['referenceReaderTargetRva']<=0):
        raise ParamGraphDecodeError('currentCondition.exact-finite-recursive-capability')
    # Validate the profile independently from selecting any serialized tag.
    # In particular, canonical FF never indexes the route map.
    tags=[]
    for key,route in routes.items():
        tag=route.get('tag');name=route.get('typeName');child=route.get('capability',{})
        if (type(tag)is not int or tag not in CHILDREN or key!=str(tag)or name!=CHILDREN[tag]
                or not isinstance(route.get('wrapperName'),str)or not route['wrapperName']
                or type(route.get('wrapperNullAdmitted'))is not bool
                or route.get('actualWrapperCallbackEqualsProvedConcreteRequired')is not True):
            raise ParamGraphDecodeError('currentCondition.exact-selected-route')
        tags.append(tag)
        if tag!=0:validate_leaf(name,child);continue
        program=child.get('program',{});listing=child.get('listCollection',{});enum=child.get('enumBacking',{})
        if (child.get('typeName')!=source.COMBINED or type(child.get('memberCount'))is not int or child['memberCount']!=3
                or any(child.get(k)is not True for k in('nullAdmitted','positiveAdmitted','profileAdmitted','actualCallbackEqualsProvedChildRequired'))
                or child.get('wholeGrammarAdmitted')is not False or child.get('liveFormatterSelectionObserved')is not False
                or program.get('memberCount')!=3
                or any(type(r.get('memberIndex'))is not int for r in program.get('reads',[]))
                or[(r.get('memberIndex'),r.get('fieldName'),r.get('kind'),r.get('childCapability'))for r in program.get('reads',[])]!=[
                    (i,n,k,source.LIST_CAP if k=='condition-runtime-list'else None)for i,(n,t,k)in enumerate(source.COMBINED_PLAN)]
                or program.get('requiredCapabilities')!=[source.LIST_CAP]
                or enum.get('typeName')!=source.COMBINED_PLAN[0][1]or enum.get('backing')not in('int','uint')
                or enum.get('field')!=[source.COMBINED_PLAN[0][1],enum.get('backing'),16]
                or listing.get('typeName')!=source.LIST or listing.get('elementType')!=source.TYPE
                or any(listing.get(k)is not True for k in('nullable','positiveCountsAdmitted','actualCallbackEqualsProvedChildRequired'))
                or type(listing.get('countLimit'))is not int or listing['countLimit']!=source.COUNT_LIMIT):
            raise ParamGraphDecodeError('currentCondition.exact-combined-program')
        bindings=program.get('childBindings',[])
        if (len(bindings)!=1 or(bindings[0].get('fieldName'),bindings[0].get('typeName'),bindings[0].get('capability'))!=('subConditions',source.LIST,source.LIST_CAP)
                or type(listing.get('readerMethodDefinition'))is not int or listing['readerMethodDefinition']<0
                or type(listing.get('sourceTargetRva'))is not int or listing['sourceTargetRva']<=0
                or(bindings[0].get('readerMethodDefinition'),bindings[0].get('sourceTargetRva'))!=(listing['readerMethodDefinition'],listing['sourceTargetRva'])
                or bindings[0].get('countLimit')!=source.COUNT_LIMIT or bindings[0].get('actualCallbackEqualsProvedChildRequired')is not True):
            raise ParamGraphDecodeError('currentCondition.exact-recursive-list-binding')
    if sorted(tags)!=list(source.TAGS):
        raise ParamGraphDecodeError('currentCondition.exact-route-key-identity')


def read(reader,field,cap):
    """One cursor, bounded recursion, canonical short tags and a separate FF."""
    validate(cap)
    def condition(path,depth,budget):
        if depth>=cap['depthLimit']or budget[0]<=0:
            raise ParamGraphDecodeError(f'{path}:condition-resource-limit,offset={reader.offset}')
        budget[0]-=1;start=reader.offset;tag=reader.number('<B',path+'.unionTag')
        if tag==255:return None
        if tag==250:raise ParamGraphDecodeError(f'{path}:extended-condition-tag-unproved,offset={start}')
        if 251<=tag<=254:raise ParamGraphDecodeError(f'{path}:reserved-union-marker,offset={start},actual={tag}')
        if tag not in source.TAGS:raise ParamGraphDecodeError(f'{path}:current-condition-tag-unproved,offset={start},actual={tag}')
        route=cap['routes'][str(tag)];selected=route['capability']
        reader.need(1,path+'.memberCount')
        if reader.data[reader.offset]==255 and route['wrapperNullAdmitted']is not True:
            raise ParamGraphDecodeError(f'{path}:current-condition-wrapper-null-unproved,offset={reader.offset}')
        if tag!=0:value=read_leaf(reader,path+'.value',route['typeName'],selected)
        else:
            child_start=reader.offset;marker=reader.number('<B',path+'.value.memberCount')
            if marker==255:value=None
            else:
                if marker!=3:raise ParamGraphDecodeError(f'{path}:member-count,offset={child_start},expected=3,actual={marker}')
                at=reader.offset;operator=reader.number('<i'if selected['enumBacking']['backing']=='int'else'<I',path+'.conditionOperator')
                reverse=reader.boolean(path+'.reverse');count_start=reader.offset;count=reader.number('<i',path+'.subConditions.count')
                if not -1<=count<=cap['countLimit']:
                    raise ParamGraphDecodeError(f'{path}:current-condition-count-limit,offset={count_start},actual={count}')
                reader.need(max(count,0),path+'.subConditions.elements')
                rows=[condition(path+f'.subConditions[{i}]',depth+1,budget)for i in range(max(count,0))]
                value=dict(startOffset=child_start,endOffset=reader.offset,recordType=source.COMBINED,memberCount=3,
                    conditionOperator=operator,reverse=reverse,subConditions=dict(startOffset=count_start,endOffset=reader.offset,
                        count=count,rows=None if count==-1 else rows),fieldRanges=dict(conditionOperator=[at,at+4],reverse=[at+4,at+5],subConditions=[count_start,reader.offset]))
        return dict(startOffset=start,endOffset=reader.offset,tag=tag,recordType=route['typeName'],value=value)
    state=getattr(reader,'_current_condition_budget',None)
    if state is None:
        state=(cap,[cap['nodeLimit']]);reader._current_condition_budget=state
    elif state[0]is not cap:
        raise ParamGraphDecodeError(f'{field}:mixed-condition-capability,offset={reader.offset}')
    return condition(field,0,state[1])


def validate_parent(cap,owner,field):
    """Only independently joined current parent fields select this profile."""
    validate(cap)
    if (owner,field)not in(('Beyond.Gameplay.LevelData','buildableCondition'),
            ('Beyond.Gameplay.LevelInteractiveData','progressLockCondition')):
        raise ParamGraphDecodeError('currentCondition.closed-current-parent')
    binding=cap.get('parentBindings',{}).get(owner+'::'+field,{})
    if (binding.get('ownerType')!=owner or binding.get('fieldName')!=field or binding.get('typeName')!=source.TYPE
            or binding.get('capability')!=source.CAP
            or(binding.get('readerMethodDefinition'),binding.get('sourceTargetRva'))!=(
                cap['referenceReaderMethodDefinition'],cap['referenceReaderTargetRva'])
            or binding.get('actualCallbackEqualsProvedChildRequired')is not True):
        raise ParamGraphDecodeError('currentCondition.exact-current-parent-binding:'+owner+'::'+field)


def validate_area(record_cap,condition_cap):
    """The exact ConditionData parent requires its actual union source join."""
    validate(condition_cap);program=record_cap.get('program',{});bindings=program.get('childBindings',[])
    if (record_cap.get('typeName')!=source.AREA_RECORD or type(record_cap.get('memberCount'))is not int or record_cap['memberCount']!=2
            or any(record_cap.get(k)is not True for k in('nullAdmitted','positiveAdmitted','profileAdmitted','actualCallbackEqualsProvedChildRequired'))
            or record_cap.get('wholeGrammarAdmitted')is not False or record_cap.get('liveFormatterSelectionObserved')is not False
            or program.get('memberCount')!=2 or program.get('requiredCapabilities')!=[source.CAP]
            or[(r.get('memberIndex'),r.get('fieldName'),r.get('kind'),r.get('childCapability'))for r in program.get('reads',[])]!=[
                (0,'conditionRuntimeBase','condition-runtime',source.CAP),(1,'uniqueId','scalar64-bits',None)]
            or any(type(r.get('memberIndex'))is not int for r in program.get('reads',[]))
            or len(bindings)!=1 or(bindings[0].get('fieldName'),bindings[0].get('typeName'),bindings[0].get('capability'))!=('conditionRuntimeBase',source.TYPE,source.CAP)
            or(bindings[0].get('readerMethodDefinition'),bindings[0].get('sourceTargetRva'))!=(
                condition_cap['referenceReaderMethodDefinition'],condition_cap['referenceReaderTargetRva'])
            or bindings[0].get('admittedRouteTags')!=list(source.TAGS)or bindings[0].get('profileAdmitted')is not True
            or bindings[0].get('wholeGrammarAdmitted')is not False or bindings[0].get('actualCallbackEqualsProvedChildRequired')is not True):
        raise ParamGraphDecodeError('currentCondition.exact-FunctionArea-condition-parent')
def read_area(reader,field,record_cap,condition_cap):
    validate_area(record_cap,condition_cap)
    start=reader.offset;marker=reader.number('<B',field+'.memberCount')
    if marker==255:return None
    if marker!=2:raise ParamGraphDecodeError(f'{field}:member-count,offset={start},expected=2,actual={marker}')
    value=read(reader,field+'.conditionRuntimeBase',condition_cap);identity=str(reader.number('<Q',field+'.uniqueId'))
    return dict(startOffset=start,endOffset=reader.offset,recordType=source.AREA_RECORD,memberCount=2,
        conditionRuntimeBase=value,uniqueId=identity)
