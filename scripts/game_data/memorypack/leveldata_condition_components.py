"""Finite recursive current ConditionRuntime grammar, independently composed."""
import json

from scripts.game_data.memorypack.leveldata_condition_runtime_sources import TYPE,CAP,TAGS,CHILDREN

COMBINED=CHILDREN[0]
LIST='System.Collections.Generic.List`1<'+TYPE+'>'
LIST_CAP='story-condition-runtime-list'
COUNT_LIMIT=4096
NODE_LIMIT=16384
DEPTH_LIMIT=32
COMBINED_PLAN=(('conditionOperator',COMBINED+'+ConditionOperator','scalar32'),('reverse','bool','bool-byte'),
    ('subConditions',LIST,'condition-runtime-list'))
AREA='Beyond.Gameplay.LevelFunctionAreaData'
AREA_RECORD=AREA+'+ConditionData'


def bind_collection(pins,join,child,capability):
    cap=child.get('capabilities',{}).get(capability,{});usage=join['typedRequest']
    if (capability!=LIST_CAP or child.get('nativeInputs')!=pins or join['typeName']!=LIST
            or cap.get('typeName')!=LIST or cap.get('elementType')!=TYPE
            or any(cap.get(k)is not True for k in('nullable','positiveCountsAdmitted','actualCallbackEqualsProvedChildRequired'))
            or type(cap.get('countLimit'))is not int or cap['countLimit']!=COUNT_LIMIT
            or usage.get('methodName')!='ReadPackable'or usage.get('methodArguments')!=[LIST]
            or(cap.get('readerMethodDefinition'),cap.get('sourceTargetRva'))!=(usage['methodSpec'][0],join['sourceTargetRva'])):
        raise ValueError('storyConditions.exact-recursive-list-parent')
    return dict(fieldName=join['fieldName'],typeName=LIST,capability=LIST_CAP,
        readerMethodDefinition=cap['readerMethodDefinition'],sourceTargetRva=cap['sourceTargetRva'],
        countLimit=COUNT_LIMIT,actualCallbackEqualsProvedChildRequired=True)


def derive(image,pins):
    """No prevalidated dictionaries or old union/leaf receipts grant this graph."""
    from scripts.game_data import levelscript_interactive_native
    from scripts.game_data.contracts import CONTRACTS_DIR
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import generated_reader_sources,scalar_param_native as scalar
    from scripts.game_data.memorypack.generated_record_components import compile_member_program
    from scripts.game_data.memorypack.leveldata_condition_runtime_sources import derive_transport
    from scripts.game_data.memorypack.leveldata_condition_leaf_sources import derive as derive_leaves
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.reference_list_induction_sources import derive as reference_list
    from scripts.game_data.memorypack.wrapper_members import derive_from_image
    need=lambda k,e,a:scalar.need('storyConditions',k,e,a)
    base=image.pe.image_base;ctx=NativeReferenceContext(image)
    transport=derive_transport(image,pins);leaves=derive_leaves(image,pins)
    wrappers={w.wrapped_type:w for w in derive_from_image(image).values()};wrapper=wrappers[COMBINED]
    source=generated_reader_sources.derive(image,pins,wrapper.name)
    need('exact-combined-declarations',[(n,t)for n,t,k in COMBINED_PLAN],
        [(r['fieldName'],r['declaredType'])for r in source['orderedSourceReads']])
    read,=[r for r in source['orderedSourceReads']if r['fieldName']=='subConditions']
    usage=derive_typed_usage_context(image,read['context']['instructionRva'],label='storyConditions.recursiveParent')
    listing=reference_list(image,pins,typed_request=usage,call_target=base+read['sourceTargetRva'],element_type=TYPE,count_limit=COUNT_LIMIT)
    list_cap=dict(typeName=LIST,elementType=TYPE,nullable=True,positiveCountsAdmitted=True,countLimit=COUNT_LIMIT,
        readerMethodDefinition=usage['methodSpec'][0],sourceTargetRva=listing['witnessComponent']['callTargetRva'],
        actualCallbackEqualsProvedChildRequired=True)
    program,pending=compile_member_program(source,pins,wrapper_name=wrapper.name,type_name=COMBINED,value4={},
        typed_requests={read['memberIndex']:usage},collections={LIST:(LIST_CAP,'condition-runtime-list',LIST_CAP)},
        collection_children={read['memberIndex']:dict(nativeInputs=pins,capabilities={LIST_CAP:list_cap})},collection_binder=bind_collection)
    need('complete-combined-program',[],pending)
    need('exact-combined-wire-order',[(n,k)for n,t,k in COMBINED_PLAN],[(r['fieldName'],r['kind'])for r in program['reads']])
    enum_type=COMBINED_PLAN[0][1];need('combined-operator-enum','System.Enum',ctx.parent(enum_type))
    enum=ctx.field(enum_type+'::value__');need('combined-operator-word',True,enum[1]in('int','uint'))
    pair=derive_pair(image,COMBINED);adapter=derive_adapter(image,pins,pair,wrapper)
    need('full-combined-Original',True,source['lifecycle']['GetValue']['program'].get('fullReferenceOutput'))
    need('same-combined-getter',source['lifecycle']['GetValue']['method'],adapter['getterMethod'])
    need('same-combined-slot5',source['lifecycle']['concreteFormatter']['method'][0],pair['composition']['interfaces'][0]['formatterDeserializeMethodIndex'])
    combined_cap=dict(typeName=COMBINED,memberCount=3,program=program,
        enumBacking=dict(typeName=enum_type,backing=enum[1],field=list(enum)),listCollection=list_cap,
        nullAdmitted=True,positiveAdmitted=True,profileAdmitted=True,wholeGrammarAdmitted=False,
        actualCallbackEqualsProvedChildRequired=True,liveFormatterSelectionObserved=False)
    joined={}
    for route in transport['programs']:
        tag=route['tag'];name=route['wrappedType']
        selected_source=source if tag==0 else leaves['records'][name]['source']
        selected_pair=pair if tag==0 else leaves['records'][name]['pair']
        need('selected-source-nominal-identity',(route['wrapperName'],name),(selected_source['wrapperName'],selected_source['wrappedType']))
        need('selected-owned-concrete-callback',selected_pair['composition']['interfaces'][0]['formatterDeserializeMethodIndex'],
            selected_source['lifecycle']['concreteFormatter']['method'][0])
        joined[str(tag)]=dict(tag=tag,typeName=name,wrapperName=route['wrapperName'],
            wrapperNullAdmitted=True,capability=combined_cap if tag==0 else leaves['capabilities'][name],
            actualWrapperCallbackEqualsProvedConcreteRequired=True)
    need('complete-finite-recursive-graph',list(TAGS),[row['tag']for row in joined.values()])
    # Independently re-prove the actual existing Interactive parent rather
    # than assuming every reference helper with the same nominal name aliases.
    path=CONTRACTS_DIR/'levelscript_interactive_native.json';before=path.read_bytes();fact=json.loads(before)
    need('selected-Interactive-build',pins,fact['nativeInputs']);interactive=levelscript_interactive_native._validate_native(image,fact)
    parent,=[r for r in interactive['element'][0]['typedUsages']if r['field']=='progressLockCondition']
    parent_usage=derive_typed_usage_context(image,parent['instruction']-base,label='storyConditions.InteractiveParent')
    need('exact-ReadValue-parent',('ReadValue',[TYPE]),(parent_usage['methodName'],parent_usage['methodArguments']))
    need('own-ReadValue-definition',transport['referencePackable']['valueContext']['readerMethodDefinition'],parent_usage['methodSpec'][0])
    need('exact-canonical-reference-dispatch',transport['adapter']['canonicalRoutes']['symbolRvas']['dispatch'],fact['symbols']['referenceDispatcher'])
    need('Interactive-declaration-bookend',before,path.read_bytes())
    cap=dict(typeName=TYPE,nullAdmitted=True,positiveAdmitted=True,profileAdmitted=True,wholeGrammarAdmitted=False,
        admittedRouteTags=list(TAGS),routes=joined,countLimit=COUNT_LIMIT,nodeLimit=NODE_LIMIT,depthLimit=DEPTH_LIMIT,
        referenceReaderMethodDefinition=parent_usage['methodSpec'][0],referenceReaderTargetRva=fact['symbols']['condition'],
        actualCallbackEqualsProvedChildRequired=True,liveFormatterSelectionObserved=False)
    area=_derive_area(image,pins,cap)
    return json.loads(json.dumps(dict(nativeInputs=pins,capability=cap,transport=transport,leaves=leaves,
        combined=dict(source=source,program=program,pair=pair,adapter=adapter,collection=listing),
        interactiveParent=dict(source=parent,typedRequest=parent_usage,readValueTargetRva=fact['symbols']['condition']),
        functionArea=area,
        wholeOwnerAdmitted=False,liveFormatterSelectionObserved=False)))


def bind_reference(pins,join,child,capability):
    from scripts.game_data.codecs.leveldata.current_condition import validate
    cap=child.get('capabilities',{}).get(capability,{});usage=join['typedRequest']
    if (capability!=CAP or child.get('nativeInputs')!=pins or join['typeName']!=TYPE
            or cap.get('typeName')!=TYPE or cap.get('profileAdmitted')is not True
            or cap.get('wholeGrammarAdmitted')is not False or cap.get('admittedRouteTags')!=list(TAGS)
            or cap.get('actualCallbackEqualsProvedChildRequired')is not True
            or usage.get('methodName')!='ReadValue'or usage.get('methodArguments')!=[TYPE]
            or(cap.get('referenceReaderMethodDefinition'),cap.get('referenceReaderTargetRva'))!=(usage['methodSpec'][0],join['sourceTargetRva'])):
        raise ValueError('storyConditions.exact-nominal-reference-parent')
    validate(cap)
    return dict(fieldName=join['fieldName'],typeName=TYPE,capability=CAP,
        readerMethodDefinition=cap['referenceReaderMethodDefinition'],sourceTargetRva=cap['referenceReaderTargetRva'],
        admittedRouteTags=list(TAGS),profileAdmitted=True,wholeGrammarAdmitted=False,
        actualCallbackEqualsProvedChildRequired=True)


def _derive_area(image,pins,condition):
    """Private continuation of the freshly derived graph, not a proof-cache API."""
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack import generated_reader_sources,scalar_param_native as scalar
    from scripts.game_data.memorypack.generated_record_components import compile_member_program
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.reference_list_induction_sources import derive as reference_list
    from scripts.game_data.memorypack.wrapper_members import derive_from_image
    need=lambda k,e,a:scalar.need('storyConditionArea',k,e,a)
    base=image.pe.image_base;wrappers={w.wrapped_type:w for w in derive_from_image(image).values()}
    generated=generated_reader_sources.derive_many(image,pins,[wrappers[n].name for n in(AREA_RECORD,AREA)])
    sources={}
    for name,row in zip((AREA_RECORD,AREA),generated['owners'],strict=True):
        need('complete-current-reader:'+name,'complete-reader-source-proved',row['status']if row['status']=='complete-reader-source-proved'else row)
        sources[name]=row['proof']
    source=sources[AREA_RECORD]
    need('exact-condition-record-fields',[('conditionRuntimeBase',TYPE),('uniqueId','ulong')],
        [(r['fieldName'],r['declaredType'])for r in source['orderedSourceReads']])
    read=source['orderedSourceReads'][0]
    usage=derive_typed_usage_context(image,read['context']['instructionRva'],label='storyConditionArea.conditionParent')
    program,pending=compile_member_program(source,pins,wrapper_name=wrappers[AREA_RECORD].name,type_name=AREA_RECORD,value4={},
        references={TYPE:(CAP,'condition-runtime',CAP)},reference_children={TYPE:dict(nativeInputs=pins,capabilities={CAP:condition})},
        typed_requests={0:usage},reference_binder=bind_reference)
    need('complete-condition-record-program',[],pending)
    need('exact-condition-record-order',[('conditionRuntimeBase','condition-runtime'),('uniqueId','scalar64-bits')],
        [(r['fieldName'],r['kind'])for r in program['reads']])
    pairs={};adapters={}
    for name,proof in sources.items():
        pair=derive_pair(image,name);adapter=derive_adapter(image,pins,pair,wrappers[name])
        need('same-owned-getter:'+name,proof['lifecycle']['GetValue']['method'],adapter['getterMethod'])
        need('full-original-reference:'+name,True,proof['lifecycle']['GetValue']['program'].get('fullReferenceOutput'))
        need('same-owned-slot5:'+name,proof['lifecycle']['concreteFormatter']['method'][0],
            pair['composition']['interfaces'][0]['formatterDeserializeMethodIndex'])
        pairs[name]=pair;adapters[name]=adapter
    parent=sources[AREA]
    read,=[r for r in parent['orderedSourceReads']if r['fieldName']=='functionAreaConditions']
    closed='System.Collections.Generic.List`1<'+AREA_RECORD+'>';need('exact-owned-condition-list',closed,read['declaredType'])
    request=derive_typed_usage_context(image,read['context']['instructionRva'],label='storyConditionArea.listParent')
    listing=reference_list(image,pins,typed_request=request,call_target=base+read['sourceTargetRva'],element_type=AREA_RECORD,count_limit=COUNT_LIMIT)
    record_cap=dict(typeName=AREA_RECORD,memberCount=2,program=program,nullAdmitted=True,positiveAdmitted=True,
        profileAdmitted=True,wholeGrammarAdmitted=False,actualCallbackEqualsProvedChildRequired=True,liveFormatterSelectionObserved=False)
    cap=dict(typeName=closed,headerBytes=4,countLimit=COUNT_LIMIT,allowedCounts=None,wholeGrammarAdmitted=False,
        profileAdmitted=True,actualCallbackEqualsProvedChildRequired=True,liveFormatterSelectionObserved=False,
        childBinding=dict(fieldName='functionAreaConditions',typeName=closed,capability='story-function-area-condition',
            readerMethodDefinition=request['methodSpec'][0],sourceTargetRva=read['sourceTargetRva']))
    return dict(sources=sources,pairs=pairs,adapters=adapters,conditionRequest=usage,listRequest=request,collection=listing,
        recordCapability=record_cap,capability=cap,wholeOwnerAdmitted=False,liveFormatterSelectionObserved=False)
