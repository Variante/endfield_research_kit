"""Three finite LevelWide record programs; union/maps are independent joins."""
import json

PREFIX='Beyond.Gameplay.'
DOCK=PREFIX+'BambooRaftDockInfo'
DOCK_CONFIG=PREFIX+'BambooRaftDockWideConfig'
RAFT_CONFIG=PREFIX+'BambooRaftWideConfig'
CONDITION=PREFIX+'ConditionRuntimeBase'
LANG='Beyond.LangKey'
LIST='System.Collections.Generic.List`1<'+DOCK+'>'
LIST_CAP='story-levelwide-dock-list'
LIMIT=4096
PLANS={
    DOCK:(('bambooRaftDockLogicId','ulong','scalar64-bits'),('dockName',LANG,'lang-key'),
        ('filterCondition',CONDITION,'condition-runtime'),('nodeIndex','int','scalar32')),
    DOCK_CONFIG:(('configKey','string','byte-payload'),('bambooRaftDockInfo',LIST,'levelwide-dock-list')),
    RAFT_CONFIG:(('configKey','string','byte-payload'),('bambooRaftLogicId','ulong','scalar64-bits'),('movingSplineId','int','scalar32')),
}


def need(check,condition):
    if not condition:raise ValueError('levelwideRecords.'+check)


def record_key(name):
    need('own-finite-record-key',name in PLANS)
    return 'story-levelwide-record:'+name


def operation(declared,kind):
    if kind=='lang-key':return 'story-lang-key'
    if kind=='condition-runtime':return 'story-condition-runtime'
    if kind=='levelwide-dock-list':return LIST_CAP
    if kind=='byte-payload':return 'byte-payload'
    return None


def bind_collection(pins,join,child,key):
    cap=child.get('capabilities',{}).get(key,{});usage=join.get('typedRequest',{})
    need('exact-dock-list-parent',key==LIST_CAP and child.get('nativeInputs')==pins
        and join.get('typeName')==cap.get('typeName')==LIST and cap.get('elementType')==DOCK
        and type(cap.get('countLimit'))is int and cap['countLimit']==LIMIT and cap.get('headerBytes')==4
        and all(cap.get(k)is True for k in ('nullable','positiveCountsAdmitted','elementGrammarAdmitted',
            'initiallyNullListRequired','actualCallbackEqualsProvedChildRequired'))
        and cap.get('liveFormatterSelectionObserved')is False
        and usage.get('methodName')=='ReadPackable'and usage.get('methodArguments')==[LIST]
        and (cap.get('packableReaderMethodDefinition'),cap.get('packableReaderTargetRva'))==
            (usage.get('methodSpec',[None])[0],join.get('sourceTargetRva')))
    return dict(fieldName=join['fieldName'],typeName=LIST,capability=LIST_CAP,countLimit=LIMIT,
        readerMethodDefinition=usage['methodSpec'][0],sourceTargetRva=join['sourceTargetRva'],
        initiallyNullListRequired=True,actualCallbackEqualsProvedChildRequired=True)


def bind_program(name,source,program,pending):
    plan=PLANS.get(name)
    need('exact-finite-record-program:'+str(name),plan is not None and not pending and type(program)is dict
        and source.get('wrappedType')==name and [(r.get('fieldName'),r.get('declaredType'))for r in source.get('orderedSourceReads',[])]==[(n,t)for n,t,k in plan]
        and type(program.get('memberCount'))is int and program['memberCount']==len(plan)
        and [(r.get('memberIndex'),r.get('fieldName'),r.get('kind'),r.get('childCapability'))for r in program.get('reads',[])]==
            [(i,n,k,operation(t,k))for i,(n,t,k)in enumerate(plan)]
        and program.get('requiredCapabilities')==sorted({operation(t,k)for n,t,k in plan if operation(t,k)is not None})
        and [(r.get('fieldName'),r.get('typeName'),r.get('capability'))for r in program.get('childBindings',[])]==
            [(n,t,operation(t,k))for n,t,k in plan if k in ('lang-key','condition-runtime','levelwide-dock-list')])


def compose(source,pins,*,lang_key=None,condition=None,dock_list=None):
    """Pure actual-parent compiler; supplies no ordinary or containing route."""
    from scripts.game_data.memorypack.generated_record_components import compile_member_program
    from scripts.game_data.memorypack import leveldata_lang_key_components as language
    from scripts.game_data.memorypack import leveldata_condition_components as conditions
    from scripts.game_data.memorypack import leveldata_levelwide_condition as condition_scope
    name=source.get('wrappedType');need('explicit-record',name in PLANS)
    requests={};values={};value_children={};references={};reference_children={};collections={};collection_children={}
    for read,(member,declared,kind)in zip(source.get('orderedSourceReads',[]),PLANS[name],strict=True):
        if kind not in ('lang-key','condition-runtime','levelwide-dock-list'):continue
        index=read['memberIndex'];context=read['context']
        usage=dict(instructionRva=context['instructionRva'],instructionHex=context['instructionHex'],
            tag=6,methodSpec=context['methodSpec'],typeName=context['methodOwner'],methodName=context['methodName'],
            classArguments=[],methodArguments=[declared])
        if kind=='lang-key':usage=source['sourceScope']['managedValueSources'][str(index)]['proof']['typedRequest']
        requests[index]=usage
        if kind=='lang-key':
            need('independent-LangKey-child-required',type(lang_key)is dict)
            values[LANG]=(language.CAP,'lang-key',language.CAP);value_children[index]=lang_key
        elif kind=='condition-runtime':
            need('independent-condition-child-required',type(condition)is dict)
            references[CONDITION]=(conditions.CAP,'condition-runtime',conditions.CAP);reference_children[CONDITION]=condition
        else:
            need('independent-dock-list-required',type(dock_list)is dict)
            collections[LIST]=(LIST_CAP,'levelwide-dock-list',LIST_CAP);collection_children[index]=dock_list
    program,pending=compile_member_program(source,pins,wrapper_name=source['wrapperName'],type_name=name,value4={},
        typed_requests=requests,typed_values=values,value_children=value_children,value_binder=language.bind_value if values else None,
        references=references,reference_children=reference_children,reference_binder=condition_scope.bind_reference,
        collections=collections,collection_children=collection_children,collection_binder=bind_collection)
    bind_program(name,source,program,pending)
    return dict(typeName=name,memberCount=len(PLANS[name]),program=program,nullAdmitted=True,positiveAdmitted=True,
        profileAdmitted=True,ordinaryAdapterAdmitted=False,wholeGrammarAdmitted=False,
        actualCallbackEqualsProvedChildRequired=True,liveFormatterSelectionObserved=False,
        containingUnionOrMapAdmitted=False)


def attribute_source(image,pins,source):
    """Fresh exact identity/windows; unchanged complete source semantics reused.

    The caller authenticates the retained proof report and its source/resource
    bookends. This function does not upgrade an unauthenticated external JSON.
    """
    name=source.get('wrappedType');md=image.metadata
    need('retained-complete-owned-source',name in PLANS and source.get('nativeInputs')==pins
        and source.get('schema')=='endfield.generated-concrete-reader-source.v1'
        and source.get('completeSelectedCallerAdmitted')is True and source.get('wholeOwnerAdmitted')is False)
    wrapper,=[w for w in image.memorypack_wrappers.values()if w.wrapped_type==name]
    method=source['method'];need('same-reader-and-nominal-members',method[1:3]==[wrapper.name,'Deserialize']
        and source.get('wrapperName')==wrapper.name and type(method[0])is int and 0<=method[0]<len(md.methods)
        and image.type_name(md.methods[method[0]].declaring_type)==wrapper.name
        and md.string(md.methods[method[0]].name_index)=='Deserialize'and md.methods[method[0]].flags&16
        and image.method_pointer_va(md.methods[method[0]])==image.pe.image_base+method[3]
        and [(m.name,m.declared_type)for m in wrapper.members]==[(r['fieldName'],r['declaredType'])for r in source['orderedSourceReads']])
    image.check_windows(source['codeWindows'],label='levelwideRecords.retained-complete-source')
    return wrapper


def derive(image,pins,*,sources,condition):
    """Own records/ordinary joins only; dictionaries and union compose later."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack import leveldata_lang_key_components as language
    from scripts.game_data.memorypack.reference_list_induction_sources import derive as reference_list
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.skill_root_child_bindings import reference_reader_abi
    _publication_gate(image,pins);need('exact-three-retained-records',set(sources)==set(PLANS));base=image.pe.image_base
    abi=reference_reader_abi(image,pins);records={};caps={};proofs={}
    for name in (DOCK,DOCK_CONFIG,RAFT_CONFIG):
        source=sources[name];wrapper=attribute_source(image,pins,source);lang=None;listing=None
        if name==DOCK:
            read=source['orderedSourceReads'][1];usage=derive_typed_usage_context(image,read['context']['instructionRva'],label='levelwideRecords.actualLangKey')
            lang=language.derive(image,pins,typed_request=usage,source_target=base+read['sourceTargetRva']);proofs['langKey']=lang
        if name==DOCK_CONFIG:
            read=source['orderedSourceReads'][1];usage=derive_typed_usage_context(image,read['context']['instructionRva'],label='levelwideRecords.actualDockList')
            listing=reference_list(image,pins,typed_request=usage,call_target=base+read['sourceTargetRva'],element_type=DOCK,count_limit=LIMIT)
            cap=dict(typeName=LIST,elementType=DOCK,countLimit=LIMIT,headerBytes=4,nullable=True,
                positiveCountsAdmitted=True,elementGrammarAdmitted=True,initiallyNullListRequired=True,
                actualCallbackEqualsProvedChildRequired=True,liveFormatterSelectionObserved=False,
                packableReaderMethodDefinition=usage['methodSpec'][0],packableReaderTargetRva=listing['witnessComponent']['callTargetRva'])
            listing_child=dict(nativeInputs=pins,capabilities={LIST_CAP:cap});proofs['dockList']=listing
        else:listing_child=None
        cap=compose(source,pins,lang_key=lang,condition=condition,dock_list=listing_child)
        pair=derive_pair(image,name,wrapper.name);adapter=derive_adapter(image,pins,pair,wrapper)
        need('same-concrete-getter-and-whole-original',source['lifecycle']['GetValue']['method']==adapter['getterMethod']
            and source['lifecycle']['GetValue']['program'].get('fullReferenceOutput')is True)
        cap.update(ordinaryAdapterAdmitted=True,referenceReaderMethodDefinition=abi['referenceReaderMethodDefinition'],
            referenceReaderTargetRva=abi['referenceReaderTargetRva'])
        caps[name]=cap;records[name]=dict(source=source,capability=cap,pair=pair,adapter=adapter)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(nativeInputs=pins,records=records,capabilities=caps,children=proofs,
        containingUnionOrMapAdmitted=False,wholeOwnerAdmitted=False)))
