"""Finite CharAnim/Clip/Sequence record programs below their raw owners.

These are concrete record components. CharInteract and AnimationConfig must
separately prove their actual containing union and collection before public
opt-in; a complete record never selects a route by its type name.
"""
import json

SCHEMA='endfield.animation-record-components.v1'
PLANS={
    'Beyond.Gameplay.Core.CharInteractPerform.CharAnimActionData':('char-anim-action-record',31),
    'Beyond.Montage.ClipMontageData':('clip-montage-record',26),
    'Beyond.Montage.SequenceMontageData':('sequence-montage-record',20),
}
VALUE_OPERATIONS={
    'Beyond.Gameplay.BodyTypeDef':('body-type-def-value','body-type-def-value'),
    'Beyond.Gameplay.View.Animation.AlphaBlend':('skill-alpha-blend','alpha-blend-value'),
    'Beyond.FAnimationCurve':('beyond-curve-value','beyond-curve-value'),
}
TRANSFORM='Beyond.Gameplay.TransformDesc'


def need(check,condition):
    if not condition:raise ValueError('animationRecordComponents.'+check)


def bind_value(source,scope,read,pins,usage,component,capability):
    name=read.get('declaredType')
    if name=='Beyond.Gameplay.BodyTypeDef':
        from scripts.game_data.memorypack.body_type_value_bindings import bind
    elif name=='Beyond.Gameplay.View.Animation.AlphaBlend':
        from scripts.game_data.memorypack.alpha_blend_value_bindings import bind
    elif name=='Beyond.FAnimationCurve':
        from scripts.game_data.memorypack.beyond_curve_value_bindings import bind
    else:raise ValueError('animationRecordComponents.unowned-value:'+str(name))
    return bind(source,scope,read,pins,usage,component,capability)


def compose(source,pins,*,value_children,reference_children=None,reference_operations=None):
    """Pure complete-record compiler; no native image or containing admission."""
    from scripts.game_data.memorypack.generated_record_components import compile_member_program
    name=source.get('wrappedType');need('finite-own-record',name in PLANS)
    capability,count=PLANS[name];scope=source.get('sourceScope',{});reads=source.get('orderedSourceReads',[])
    need('literal-current-record-count',len(reads)==scope.get('memberCount')==count
        and source.get('nativeInputs')==pins and source.get('completeSelectedCallerAdmitted')is True)
    requests={};values={};selected={};value4={};value8={}
    for read in reads:
        index=read['memberIndex'];kind=read['kind'];declared=read['declaredType']
        if kind.startswith('managed:')and declared in VALUE_OPERATIONS:
            if index not in value_children:continue
            cap,wire=VALUE_OPERATIONS[declared];values[declared]=(cap,wire,cap);selected[index]=value_children[index]
            requests[index]=scope['managedValueSources'][str(index)]['proof']['typedRequest']
        elif kind.startswith('value4:'):
            value4[declared]=scope['primitiveSources'][str(index)]
        elif kind=='value8:UnityEngine.Vector2':
            value8.setdefault(declared,{})[str(index)]=scope['primitiveSources'][str(index)]
        elif kind.startswith('reference:')and read.get('context')is not None:
            context=read['context'];requests[index]=dict(instructionRva=context['instructionRva'],instructionHex=context['instructionHex'],
                methodSpec=context['methodSpec'],tag=6,typeName=context['methodOwner'],methodName=context['methodName'],
                classArguments=[],methodArguments=[declared])
    reference_children=reference_children or{}
    reference_operations=reference_operations or{}
    need('finite-owned-reference-children',set(reference_children)<=set(reference_operations)<={TRANSFORM})
    reference_bindings={}
    for read in reads:
        if read['declaredType']!=TRANSFORM or TRANSFORM not in reference_children:continue
        from scripts.game_data.memorypack.animation_transform_desc_components import bind_parent,CAPABILITY,WIRE
        need('exact-TransformDesc-reference-operation',reference_operations.get(TRANSFORM)==(CAPABILITY,WIRE,CAPABILITY))
        index=read['memberIndex'];reference_bindings[index]=bind_parent(source,scope,read,pins,requests[index],reference_children[TRANSFORM])
    def bind_reference(selected_pins,join,child,capability):
        index,=[read['memberIndex']for read in reads if read['declaredType']==TRANSFORM and read['fieldName']==join['fieldName']]
        need('same-domain-owned-TransformDesc-child',selected_pins==pins and child==reference_children[TRANSFORM]
            and capability==reference_bindings[index]['capability'])
        return reference_bindings[index]
    compiled,pending=compile_member_program(source,pins,wrapper_name=source['wrapperName'],type_name=name,value4=value4,value8=value8,
        typed_requests=requests,typed_values=values,value_children=selected,value_binder=bind_value,
        references=reference_operations,reference_children=reference_children,
        reference_binder=bind_reference if reference_bindings else None)
    if pending:return dict(schema=SCHEMA,status='pendingReview',nativeInputs=pins,typeName=name,capability=capability,
        pending=pending,wholeGrammarAdmitted=False,containingOwnerAdmitted=False)
    need('complete-exact-current-program',compiled['memberCount']==count and len(compiled['reads'])==count
        and[(r['memberIndex'],r['fieldName'])for r in compiled['reads']]==[(r['memberIndex'],r['fieldName'])for r in reads])
    cap=dict(typeName=name,wrapperName=source['wrapperName'],memberCount=count,orderedReads=compiled['reads'],nullable=True,
        nullMarker=255,wholeGrammarAdmitted=True,directWrapperGrammarAdmitted=True,ordinaryOriginalReadValueAdmitted=False,
        actualContainingRouteAdmitted=False,wholeOwnerAdmitted=False)
    capabilities={capability:cap};required=set(compiled['requiredCapabilities'])
    for component in list(selected.values())+list(reference_children.values()):
        need('same-current-independent-child-inputs',component.get('nativeInputs')==pins)
        for child_name,child_cap in component.get('capabilities',{}).items():
            need('coherent-same-named-child-grammar',child_name not in capabilities or capabilities[child_name]==child_cap)
            capabilities[child_name]=child_cap
        required.update(component.get('requiredExternalCapabilities',[]))
    return dict(schema=SCHEMA,status='compiled-conditional-direct-wrapper-animation-record',nativeInputs=pins,typeName=name,
        capability=capability,capabilities=capabilities,compiled=compiled,pending=[],referenceBindings=reference_bindings,
        requiredExternalCapabilities=sorted(required-set(capabilities)),ordinaryOriginalAdapterAdmitted=False,
        containingOwnerAdmitted=False,wholeOwnerAdmitted=False)


def _children(image,pins,source):
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack import alpha_blend_value_bindings as alpha
    from scripts.game_data.memorypack import body_type_value_components as body
    from scripts.game_data.memorypack import beyond_curve_value_components as beyond
    result={};base=image.pe.image_base
    for read in source['orderedSourceReads']:
        index=read['memberIndex'];name=read['declaredType']
        if name not in VALUE_OPERATIONS:continue
        if name==alpha.TYPE:
            result[index]=alpha.derive(image,pins,parent_source=source,member_index=index)['proof']['childComponent']
        elif name=='Beyond.Gameplay.BodyTypeDef':result[index]=body.derive(image,pins)
        else:
            usage=derive_typed_usage_context(image,read['context']['instructionRva'],label='animationRecordComponents.Beyond')
            result[index]=beyond.derive(image,pins,typed_request=usage,source_target=base+read['sourceTargetRva'],count_limit=10000)
    return result


def _references(image,pins,source):
    """Fresh independent nominal reference children for the selected record."""
    if not any(read.get('declaredType')==TRANSFORM for read in source['orderedSourceReads']):return {},{}
    from scripts.game_data.memorypack import generated_reader_sources as reader,animation_transform_desc_components as transform
    need('same-exact-TransformDesc-owner',transform.TYPE==TRANSFORM)
    wrappers=[w for w in image.memorypack_wrappers.values()if w.wrapped_type==TRANSFORM]
    need('one-current-TransformDesc-wrapper',len(wrappers)==1)
    child_source=reader.derive(image,pins,wrappers[0].name)
    child=transform.derive(image,pins,source=child_source)
    return {TRANSFORM:child},{TRANSFORM:(transform.CAPABILITY,transform.WIRE,transform.CAPABILITY)}


def _attribute(image,pins,source):
    """Retain passed semantics while rebinding this exact current source."""
    need('retained-complete-current-source',source.get('schema')=='endfield.generated-concrete-reader-source.v1'
        and source.get('nativeInputs')==pins and source.get('completeSelectedCallerAdmitted')is True
        and source.get('childGrammarAdmitted')is False and source.get('wholeOwnerAdmitted')is False
        and source.get('wrappedType')in PLANS)
    wrappers=[w for w in image.memorypack_wrappers.values()if w.name==source.get('wrapperName')]
    need('one-current-nominal-wrapper',len(wrappers)==1 and wrappers[0].wrapped_type==source['wrappedType'])
    wrapper=wrappers[0];method=source.get('method',[]);md=image.metadata
    need('literal-current-reader-identity',len(method)==4 and type(method[0])is int and 0<=method[0]<len(md.methods))
    selected=md.methods[method[0]]
    need('same-current-reader-and-members',image.type_name(selected.declaring_type)==wrapper.name
        and md.string(selected.name_index)=='Deserialize'and selected.flags&16
        and method[1:3]==[wrapper.name,'Deserialize']and image.method_pointer_va(selected)==image.pe.image_base+method[3]
        and [(m.name,m.declared_type)for m in wrapper.members]==[(r['fieldName'],r['declaredType'])for r in source['orderedSourceReads']])
    image.check_windows(source['codeWindows'],label='animationRecordComponents.retained-complete-source')
    return wrapper,dict(method=method,codeWindows=source['codeWindows'],freshMethodAndMemberAttribution=True,
        retainedCompleteSourceSemanticsReused=True,sourceProgramSemanticsReproved=False)


def _ordinary(image,pins,source,record,wrapper):
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.skill_root_child_bindings import reference_reader_abi
    life=source['lifecycle'];owned=life.get('directHolderMode')is not True and'ownedCoherentGetter'in life['GetValue']
    pair=derive_pair(image,source['wrappedType'],wrapper.name,owned_getter_family=owned)
    adapter=derive_adapter(image,pins,pair,wrapper)
    need('same-own-reader-and-getter',adapter['getterMethod']==life['GetValue']['method']
        and adapter['pairForwarder']['readerMethod']==source['method'])
    references=reference_reader_abi(image,pins);cap=record['capabilities'][record['capability']]
    cap.update(ordinaryOriginalReadValueAdmitted=True,ownConcreteGetterSemanticsProved=True,
        ownConcreteFactorySemanticsProved=True,callbackSelectionConditional=True,
        originalTypeDefinition=image.named_types[source['wrappedType']].index,
        referenceReaderMethodDefinition=references['referenceReaderMethodDefinition'],
        referenceReaderTargetRva=references['referenceReaderTargetRva'])
    return dict(pair=pair,adapter=adapter,referenceReaders=references)


def derive_selected(image,pins,*,sources,value_children,reference_children=None,reference_operations=None):
    """Compose passed native proofs and freshly prove only the ordinary joins.

    Callers own authenticated input-report bookends. This API reattributes the
    selected retained source and replays every domain field binder; it never
    selects a containing route or reopens unchanged full reader semantics.
    """
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    need('finite-distinct-retained-owner-selection',isinstance(sources,dict)and bool(sources)
        and set(sources)<=set(PLANS)and set(value_children)==set(sources))
    _publication_gate(image,pins);owners=[]
    for name,source in sources.items():
        try:
            wrapper,attribution=_attribute(image,pins,source)
            need('same-explicit-owner-selection',source['wrappedType']==name)
            children=value_children[name];refs=(reference_children or{}).get(name,{})
            record=compose(source,pins,value_children=children,reference_children=refs,
                reference_operations=(reference_operations or{}).get(name,{}))
            if record['pending']:owners.append(dict(typeName=name,status='pendingReview',proof=record));continue
            ordinary=_ordinary(image,pins,source,record,wrapper)
            record.update(status='validated-conditional-animation-record-components',ordinaryOriginalAdapterAdmitted=True,
                proof=dict(source=source,valueChildren=children,referenceChildren=refs,sourceAttribution=attribution,**ordinary))
            owners.append(dict(typeName=name,status=record['status'],proof=record))
        except(ValueError,KeyError,IndexError,TypeError)as error:
            owners.append(dict(typeName=name,status='pendingReview',reason=str(error)[:2200]))
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,nativeInputs=pins,owners=owners,
        containingOwnerAdmitted=False,wholeOwnerAdmitted=False,
        evidenceBoundary='Retained complete current source semantics with fresh method/member/window attribution, independent exact field/child grammar replay, then fresh ordinary adapters. No CharInteract/AnimationConfig union or collection selection, enclosing EOF, publication or runtime animation claim.')))


def derive(image,pins,*,type_names=None):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack import generated_reader_sources as reader
    names=list(PLANS)if type_names is None else list(type_names)
    need('finite-distinct-selection',bool(names)and len(names)==len(set(names))and set(names)<=set(PLANS));_publication_gate(image,pins)
    wrappers={w.wrapped_type:w for w in image.memorypack_wrappers.values()if w.wrapped_type in names}
    need('exact-current-wrappers',set(wrappers)==set(names))
    generated=reader.derive_many(image,pins,[wrappers[n].name for n in names]);owners=[]
    for name,row in zip(names,generated['owners'],strict=True):
        try:
            need('complete-own-reader:'+name,row['status']=='complete-reader-source-proved');source=row['proof']
            children=_children(image,pins,source);refs,operations=_references(image,pins,source)
            record=compose(source,pins,value_children=children,reference_children=refs,reference_operations=operations)
            if record['status']=='pendingReview':owners.append(dict(typeName=name,status='pendingReview',proof=record));continue
            ordinary=_ordinary(image,pins,source,record,wrappers[name])
            record.update(status='validated-conditional-animation-record-components',ordinaryOriginalAdapterAdmitted=True,
                proof=dict(source=source,valueChildren=children,referenceChildren=refs,**ordinary))
            owners.append(dict(typeName=name,status=record['status'],proof=record))
        except(ValueError,KeyError,IndexError,TypeError)as error:
            owners.append(dict(typeName=name,status='pendingReview',reason=str(error)[:2200]))
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,nativeInputs=pins,owners=owners,
        containingOwnerAdmitted=False,wholeOwnerAdmitted=False,
        evidenceBoundary='Complete independently selected concrete source and all child wire joins, then own ordinary adapter. No CharInteract/AnimationConfig union or collection route, enclosing EOF, publication or animation behavior is admitted.')))
