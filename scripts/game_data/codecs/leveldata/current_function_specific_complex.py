"""Finite complex SpecificData wrapper cursor; no native opener or owner gate."""
from scripts.game_data.memorypack import leveldata_function_specific_complex_sources as source
from scripts.game_data.codecs.leveldata import current_condition,current_lang_key

NODE_LIMIT=16384


def condition_for_reader(reader,child):
    """Use one exact graph's budget across independently proved host parents."""
    selected=getattr(reader,'condition_cap',None)
    if selected is None:return child
    current_condition.validate(selected)
    if({k:v for k,v in selected.items()if k!='parentBindings'}!=
            {k:v for k,v in child.items()if k!='parentBindings'}):
        raise ValueError('currentSpecificComplex.exact-owning-condition-graph')
    return selected


def validate(name,cap):
    if not isinstance(cap,dict):raise ValueError('currentSpecificComplex.missing-child-capability')
    plan=source.PLANS.get(name)
    if (plan is None or cap.get('typeName')!=name or type(cap.get('memberCount'))is not int or cap['memberCount']!=len(plan)
            or any(cap.get(k)is not True for k in('nullAdmitted','positiveAdmitted','profileAdmitted','finiteFloatProfile',
                'wrapperWireGrammarAdmitted','actualCallbackEqualsProvedChildRequired'))
            or any(cap.get(k)is not False for k in('wholeGrammarAdmitted','liveFormatterSelectionObserved','parentFieldAdmitted','wholeOwnerAdmitted'))
            or cap.get('concreteOriginalAdapterUsed')is not(name==source.ENTRY)
            or cap.get('ordinaryAdapterAdmitted')is not(name==source.ENTRY)):
        raise ValueError('currentSpecificComplex.exact-wrapper-child:'+str(name))
    declared=dict(wrappedType=name,orderedSourceReads=[dict(fieldName=n,declaredType=t)for n,t,k in plan])
    program=cap.get('program');source.bind_program(name,declared,program,[])
    enums=cap.get('enumBackings',{});wanted={n:t for n,t,k in plan if k=='scalar32'and t!='int'}
    if set(enums)!=set(wanted):raise ValueError('currentSpecificComplex.exact-enum-set')
    for field,typename in wanted.items():
        row=enums[field]
        if row.get('typeName')!=typename or row.get('backing')not in('int','uint')or row.get('field')!=[typename,row.get('backing'),16]:
            raise ValueError('currentSpecificComplex.exact-enum-backing:'+typename)
    children=cap.get('childCapabilities',{})
    expected={source.OPERATIONS[k]for n,t,k in plan if k in source.OPERATIONS}
    if name==source.CHILDREN[14]:expected.add(source.ENTRY_CAP)
    if not isinstance(children,dict)or set(children)!=expected:raise ValueError('currentSpecificComplex.exact-child-set')
    if source.ENTRY_CAP in children:validate(source.ENTRY,children[source.ENTRY_CAP])
    for binding in program['childBindings']:
        key=binding['capability'];child=children[key]
        if (type(binding.get('readerMethodDefinition'))is not int or binding['readerMethodDefinition']<0
                or type(binding.get('sourceTargetRva'))is not int or binding['sourceTargetRva']<=0):
            raise ValueError('currentSpecificComplex.literal-child-binding')
        if key==source.language.CAP:
            current_lang_key.validate(child)
            if ((binding['readerMethodDefinition'],binding['sourceTargetRva'])!=(child['readerMethodDefinition'],child['sourceTargetRva'])
                    or type(binding.get('managedBytes'))is not int or binding['managedBytes']!=16 or binding.get('referenceLaneOffsets')!=[0,8]
                    or(binding.get('wireMemberCount'),binding.get('positiveWireBytes'),binding.get('nullWireBytes'))!=(1,5,1)
                    or any(binding.get(k)is not True for k in('nonserializedRawText','actualCallbackEqualsProvedChildRequired','completeFieldTransferAndFrameProved'))):
                raise ValueError('currentSpecificComplex.exact-two-reference-LangKey-parent')
        elif key==source.conditions.CAP:
            current_condition.validate(child)
            if ((binding['readerMethodDefinition'],binding['sourceTargetRva'])!=(child['referenceReaderMethodDefinition'],child['referenceReaderTargetRva'])
                    or binding.get('admittedRouteTags')!=list(source.conditions.TAGS)
                    or binding.get('actualCallbackEqualsProvedChildRequired')is not True):
                raise ValueError('currentSpecificComplex.exact-condition-parent')
        else:
            if ((child.get('packableReaderMethodDefinition'),child.get('packableReaderTargetRva'))!=(binding['readerMethodDefinition'],binding['sourceTargetRva'])
                    or type(binding.get('countLimit'))is not int or binding['countLimit']!=source.LIMIT
                    or type(child.get('countLimit'))is not int or child['countLimit']!=source.LIMIT
                    or any(child.get(k)is not True for k in('nullable','positiveCountsAdmitted'))):
                raise ValueError('currentSpecificComplex.exact-collection-source')
            if key==source.STRING_CAP:
                if ((child.get('closedListType'),child.get('elementType'),child.get('elementValueType'))!=(source.STRINGS,'string',False)
                        or any(child.get(k)is not True for k in('elementGrammarAdmitted','actualCallbackEqualsPooledStringRequired'))
                        or binding.get('actualCallbackEqualsPooledStringRequired')is not True):
                    raise ValueError('currentSpecificComplex.exact-pooled-string-list')
            else:
                typename,element,width={source.ULONG_CAP:(source.ULONGS,'ulong',8),source.vectors.CAP:(source.vectors.LIST,source.vectors.TYPE,12),
                    source.ENTRY_LIST_CAP:(source.ENTRIES,source.ENTRY,None)}[key]
                if ((child.get('typeName'),child.get('elementType'),child.get('countRange'))!=(typename,element,[-1,source.LIMIT])
                        or any(child.get(k)is not True for k in('actualCallbackEqualsProvedChildRequired',))
                        or binding.get('actualCallbackEqualsProvedChildRequired')is not True
                        or(width is not None and(type(child.get('elementWireBytes'))is not int or child['elementWireBytes']!=width
                            or child.get('initiallyNullListRequired',child.get('initiallyNullOutputRequired'))is not True
                            or child.get('rawBitsPreserved')is not True))
                        or(key==source.vectors.CAP and child.get('finiteFloatProfile')is not True)
                        or(key==source.ENTRY_LIST_CAP and child.get('finiteElementProfileAdmitted')is not True)):
                    raise ValueError('currentSpecificComplex.exact-nominal-list-child')


def _read(reader,field,name,cap,budget,*,charge_node=True):
    if charge_node:
        if budget[0]<=0:raise ValueError(field+':specific-node-limit')
        budget[0]-=1
    start=reader.offset;marker=reader.number('<B',field+'.memberCount')
    if marker==255:return None
    if marker!=len(source.PLANS[name]):raise ValueError(field+':specific-member-count')
    out=dict(startOffset=start,recordType=name,memberCount=marker);spans={};children=cap['childCapabilities']
    for member,declared,kind in source.PLANS[name]:
        at=reader.offset;path=field+'.'+member
        if kind=='scalar32':value=reader.number('<I'if cap['enumBackings'].get(member,{}).get('backing')=='uint'else'<i',path)
        elif kind=='float32-bits':value=reader.single(path)
        elif kind=='bool-byte':value=reader.boolean(path)
        elif kind=='lang-key':value=current_lang_key.read(reader,path,children[source.language.CAP])
        elif kind=='condition-runtime':value=current_condition.read(reader,path,condition_for_reader(reader,children[source.conditions.CAP]))
        elif kind in('uint64-list','pooled-string-list','vector3-list','scene-entry-list'):
            count=reader.number('<i',path+'.count')
            if not -1<=count<=source.LIMIT:raise ValueError(path+':specific-count-limit')
            minimum={'uint64-list':8,'pooled-string-list':4,'vector3-list':12,'scene-entry-list':1}[kind]
            reader.need(max(count,0)*minimum,path+'.elements')
            values=[]
            for index in range(max(count,0)):
                item=path+f'[{index}]'
                if kind=='uint64-list':data=str(reader.number('<Q',item))
                elif kind=='pooled-string-list':data=reader.string(item)
                elif kind=='vector3-list':data={axis:reader.single(item+'.'+axis)for axis in'xyz'}
                else:data=_read(reader,item,source.ENTRY,children[source.ENTRY_CAP],budget)
                values.append(data)
            value=dict(startOffset=at,endOffset=reader.offset,count=count,rows=None if count==-1 else values)
        else:raise ValueError(path+':closed-specific-child-operation:'+kind)
        out[member]=value;spans[member]=[at,reader.offset]
    out.update(endOffset=reader.offset,fieldRanges=spans);return out


def read(reader,field,name,cap):
    validate(name,cap)
    state=getattr(reader,'_current_specific_complex_budget',None)
    if state is None:state=(cap,[NODE_LIMIT]);reader._current_specific_complex_budget=state
    elif state[0]is not cap:raise ValueError(field+':mixed-current-specific-capability')
    return _read(reader,field,name,cap,state[1])
