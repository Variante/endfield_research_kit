"""Finite ExtraData record/ordinary-adapter joins below the animation owner.

Only complete current concrete source programs enter this composer. Every
managed child retains its own nominal source, field/frame binder and wire cap.
The selected reference adapter supplies the original callback identity; neither
that identity nor an eight-byte reference supplies a record's wire grammar.
Containing arrays/dictionaries, runtime animation and public selection remain
separate joins.
"""
import json

PREFIX='Beyond.Gameplay.View.Animation.'
SCHEMA='endfield.animation-extra-record-components.v1'
WIRE='animation-extra-record'
PLANS={
    PREFIX+'CharacterAnimExtraData+CharHurtAnimConfig':(('rootMotionCurve','Beyond.FAnimationCurve'),('rootMotionScaledTime','UnityEngine.Vector2'),('skMorphMotionSetting','Beyond.Gameplay.Core.SkMorphPlaySetting')),
    PREFIX+'CharacterAnimExtraData+CharMoveAdditiveAnimConfig':(('idleClipInfo','Beyond.Montage.AnimationClipAsyncInfo'),('runClipInfo','Beyond.Montage.AnimationClipAsyncInfo'),('skMorphMotionSetting','Beyond.Gameplay.Core.SkMorphPlaySetting'),('sprintClipInfo','Beyond.Montage.AnimationClipAsyncInfo'),('walkClipInfo','Beyond.Montage.AnimationClipAsyncInfo')),
    PREFIX+'EnemyAnimExtraData+EnemyBlowOffAnimConfig':(('animTotalTime','float'),('rootMotionCurvePosY','Beyond.FAnimationCurve'),('rootMotionCurvePosZ','Beyond.FAnimationCurve')),
    PREFIX+'EnemyAnimExtraData+EnemyHurtAnimEntry':(('customDeadAnimOffset','float'),('customDeadDelay','float'),('immobilizedTime','float'),('overrideDeadDelay','bool'),('rootMotionCurve','Beyond.FAnimationCurve'),('rootMotionScaledTime','UnityEngine.Vector2'),('unmovableTime','float')),
    PREFIX+'EnemyAnimExtraData+EnemyTurnStartData':(('duration','float'),('totalYawRotationDegrees','float')),
    PREFIX+'AnimationConfigExtraData+AnimatedShaderPropertyConfig':(('shaderProps',PREFIX+'AnimationConfigExtraData+ShaderPropertyEntry[]'),),
    PREFIX+'AnimationConfigExtraData+AnimationEventPlayEffectConfig':(('entries',PREFIX+'AnimationConfigExtraData+AnimationEventPlayEffectEntry[]'),),
    PREFIX+'AnimationConfigExtraData+AnimationEventRendererVisibilityConfig':(('entries',PREFIX+'AnimationConfigExtraData+AnimationEventRendererVisibilityEntry[]'),),
}
VALUES={'Beyond.FAnimationCurve':('beyond-curve-value','beyond-curve-value'),
    'Beyond.Gameplay.Core.SkMorphPlaySetting':('animation-sk-morph-setting','animation-sk-morph-setting')}
from scripts.game_data.memorypack.animation_extra_record_plans import ADDITIONAL
PLANS.update(ADDITIONAL)


def need(check,condition,detail=None):
    if not condition:raise ValueError('animationExtraRecordComponents.'+check+(':'+json.dumps(detail,sort_keys=True)[:1800]if detail is not None else''))


def normalized(v):return json.loads(json.dumps(v))


def record_key(name):
    need('finite-reference-record',name in PLANS);return 'animation-extra-record:'+name


def _original_definition(source):
    allocations=[f.get('originalAllocation',{})for f in source.get('lifecycle',{}).get('factories',[])]
    raw=[bytes.fromhex(a.get('typeRawHex',''))for a in allocations]
    need('own-complete-original-class-carriers',len(raw)==2
        and all(a.get('typeName')==source.get('wrappedType')for a in allocations)
        and all(len(r)==16 and r[10:12]==bytes.fromhex('1200')for r in raw)
        and raw[0]==raw[1])
    return int.from_bytes(raw[0][:8],'little')


def compose_record(source,pins,*,children=None,value_binder=None,typed_requests=None):
    """Compile a complete own wrapper; adapters are added by fresh derive."""
    from scripts.game_data.memorypack.generated_record_components import compile_member_program
    from scripts.game_data.memorypack.beyond_curve_value_bindings import bind as bind_curve
    name=source.get('wrappedType');need('finite-nominal-source',name in PLANS
        and source.get('schema')=='endfield.generated-concrete-reader-source.v1'
        and source.get('nativeInputs')==pins and source.get('completeSelectedCallerAdmitted')is True
        and source.get('childGrammarAdmitted')is False and source.get('wholeOwnerAdmitted')is False)
    reads=source.get('orderedSourceReads',[]);need('exact-owned-member-order',
        [(r.get('fieldName'),r.get('declaredType'))for r in reads]==list(PLANS[name]))
    scope=source['sourceScope'];children={}if children is None else children
    need('literal-member-child-map',isinstance(children,dict)and all(type(k)is int or isinstance(k,str)and k.isdecimal()for k in children))
    children={int(k):v for k,v in children.items()}
    from scripts.game_data.memorypack import animation_extra_array_components as value_arrays
    from scripts.game_data.memorypack import animation_extra_dictionary_components as dictionaries
    from scripts.game_data.memorypack import animation_extra_int_array_components as int_arrays
    from scripts.game_data.memorypack import animation_enemy_hurt_enum_lists as enum_lists
    from scripts.game_data.memorypack import animation_extra_reference_lists as ref_lists
    array_types={t+'[]'for t in value_arrays.TYPES}
    list_types={ref_lists.list_type(t)for t in ref_lists.TYPES}|{enum_lists.LIST}
    supported=set(VALUES)|array_types|set(PLANS)|set(dictionaries.CAPABILITIES)|{'int[]'}|list_types
    need('owned-member-child-map',len(children)==len(set(children))and set(children)<={r['memberIndex']for r in reads if r['declaredType']in supported})
    requests={}if typed_requests is None else{int(k):v for k,v in typed_requests.items()}
    selected={};operations={};raw8={};arrays={};array_children={};references={};reference_children={};static={};static_children={};collections={};collection_children={}
    for r in reads:
        index=r['memberIndex'];typ=r['declaredType']
        if typ in VALUES and index in children:
            cap,wire=VALUES[typ];operations[typ]=(cap,wire,cap);selected[index]=children[index]
            requests[index]=scope['managedValueSources'][str(index)]['proof']['typedRequest']
        elif typ=='UnityEngine.Vector2':raw8.setdefault(typ,{})[str(index)]=scope['primitiveSources'][str(index)]
        elif typ in array_types and index in children:
            component=children[index];own=value_arrays.validate_component(component,pins);cap=own['capability']
            arrays[typ]=(cap,value_arrays.WIRE,cap);array_children[index]=component;selected[index]=component
            requests[index]=component['proof']['arraySource']['typedRequest']
        elif typ=='int[]'and index in children:
            component=children[index];own=int_arrays.validate_component(component,pins);cap=own['capability']
            arrays[typ]=(cap,int_arrays.WIRE,cap);array_children[index]=component;selected[index]=component
            requests[index]=component['proof']['arraySource']['proof']['context']['typedRequest']
        elif typ in list_types and index in children:
            component=children[index]
            if typ==enum_lists.LIST:
                enum_lists.validate_component(pins,component);cap=enum_lists.CAPABILITY;wire='animation-extra-enum-list'
                requests[index]=component['actualBindings'][r['fieldName']]['typedRequest']
            else:
                own=ref_lists.validate_component(component,pins);cap=own['capability'];wire=ref_lists.WIRE
                requests[index]=component['proof']['listSource']['proof']['source']['witnessComponent']['typedRequest']
            collections[typ]=(cap,wire,cap);collection_children[index]=component;selected[index]=component
        elif typ in dictionaries.CAPABILITIES and index in children:
            component=children[index];own=dictionaries.validate_component(component,pins,value_binder=value_binder);cap=dictionaries.CAPABILITIES[typ]
            need('exact-own-static-dictionary-child',cap==dictionaries.CAPABILITIES[typ])
            static[typ]=(cap,dictionaries.WIRE,cap);static_children[index]=component;selected[index]=component
            requests[index]=scope['staticReferenceSources'][str(index)]['context']['typedRequest']
        elif typ in PLANS and index in children:
            component=children[index];own=validate_component(component,pins,value_binder=value_binder);cap=own['capability']
            need('exact-own-reference-record-child',cap==record_key(typ)and own['capabilities'][cap]['typeName']==typ)
            need('fresh-own-reference-member-request',index in requests)
            references[typ]=(cap,WIRE,cap);reference_children[typ]=component;selected[index]=component
    def binder(parent,owned_scope,read,selected_pins,usage,child,capability):
        if read['declaredType']=='Beyond.FAnimationCurve':return bind_curve(parent,owned_scope,read,selected_pins,usage,child,capability)
        need('independent-SkMorph-value-binder',read['declaredType']=='Beyond.Gameplay.Core.SkMorphPlaySetting')
        selected_binder=value_binder
        if selected_binder is None:
            from scripts.game_data.memorypack.sk_morph_value_bindings import bind
            selected_binder=bind
        need('callable-only-value-binder',callable(selected_binder))
        return selected_binder(parent,owned_scope,read,selected_pins,usage,child,capability)
    def collection_binder(selected_pins,join,child,capability):
        matching=[r for r in reads if r['fieldName']==join['fieldName']and r['declaredType']==join['typeName']]
        need('one-own-collection-member',len(matching)==1);read,=matching
        if read['declaredType']==enum_lists.LIST:
            binding=enum_lists.bind_member(source,scope,read,selected_pins,join['typedRequest'],child,capability)
            return dict(binding,capability=capability,readerMethodDefinition=binding['packableReaderMethodDefinition'])
        return ref_lists.bind_member(source,scope,read,selected_pins,join['typedRequest'],child,capability)
    compiled,pending=compile_member_program(source,pins,wrapper_name=source['wrapperName'],type_name=name,
        value4={},value8=raw8,typed_requests=requests,typed_values=operations,
        value_children={i:c for i,c in selected.items()if reads[i]['declaredType']in VALUES},value_binder=binder,arrays=arrays,array_children=array_children,
        references=references,reference_children=reference_children,static_references=static,static_reference_children=static_children,
        collections=collections,collection_children=collection_children,collection_binder=collection_binder)
    need('all-owned-child-programs-closed',not pending and compiled['memberCount']==len(PLANS[name]))
    capability=record_key(name)
    cap=dict(typeName=name,wrapperName=source['wrapperName'],memberCount=len(PLANS[name]),orderedReads=compiled['reads'],
        nullable=True,nullMarker=255,wholeGrammarAdmitted=True,directWrapperGrammarAdmitted=True,
        ordinaryOriginalReadValueAdmitted=False,ordinaryOriginalCallbackAdmitted=False,valueStorageKind='reference8',actualContainingRouteAdmitted=False,
        originalTypeDefinition=_original_definition(source),wholeOwnerAdmitted=False)
    caps={capability:cap};required=set(compiled['requiredCapabilities'])
    for component in selected.values():
        need('same-independent-child-pins',component.get('nativeInputs')==pins)
        for key,row in component.get('capabilities',{}).items():
            need('coherent-own-child',key not in caps or caps[key]==row);caps[key]=row
        required.update(component.get('requiredExternalCapabilities',[]))
    return dict(schema=SCHEMA,status='compiled-conditional-animation-extra-reference-record',nativeInputs=pins,
        typeName=name,capability=capability,capabilities=caps,compiled=compiled,
        requiredExternalCapabilities=sorted(required-set(caps)),parentFieldAdmitted=False,wholeOwnerAdmitted=False)


def validate_component(component,pins,*,value_binder=None):
    """Pure replay of the compiled record plus exact own ordinary identities."""
    from scripts.game_data.memorypack import animation_enemy_shake_value_components as shake
    if component.get('schema')==shake.SCHEMA:return shake.validate_component(component,pins)
    from scripts.game_data.memorypack import shader_property_value_components as shader
    if component.get('schema')==shader.SCHEMA:return shader.validate_component(component,pins)
    from scripts.game_data.memorypack import animation_extra_value32_components as value32
    if component.get('schema')==value32.SCHEMA:return value32.validate_component(component,pins)
    from scripts.game_data.memorypack import animation_renderer_value_components as renderer
    if component.get('schema')==renderer.SCHEMA:return renderer.validate_component(component,pins)
    need('native-composed-own-record',component.get('schema')==SCHEMA
        and component.get('status')=='validated-conditional-animation-extra-record-components'
        and component.get('nativeInputs')==pins and component.get('parentFieldAdmitted')is False
        and component.get('wholeOwnerAdmitted')is False)
    proof=component.get('proof',{});source=proof.get('source',{});name=source.get('wrappedType')
    replay=compose_record(source,pins,children=proof.get('memberChildren',proof.get('valueChildren',{})),value_binder=value_binder,typed_requests=proof.get('typedRequests'))
    key=replay['capability'];basecap=replay['capabilities'][key];cap=component.get('capabilities',{}).get(key,{})
    pair=proof.get('pair',{});adapter=proof.get('adapter',{});faces=pair.get('composition',{}).get('interfaces',[])
    pair_matches=normalized(adapter.get('pair'))==normalized(pair)
    cap_differences={k:dict(expected=v,actual=cap.get(k))for k,v in basecap.items()
        if k not in('ordinaryOriginalReadValueAdmitted','ordinaryOriginalCallbackAdmitted')and cap.get(k)!=v}
    need('same-complete-record-program',component.get('typeName')==name and component.get('capability')==key
        and component.get('compiled')==replay['compiled']and component.get('requiredExternalCapabilities')==replay['requiredExternalCapabilities']
        and all(cap.get(k)==v for k,v in basecap.items()if k not in('ordinaryOriginalReadValueAdmitted','ordinaryOriginalCallbackAdmitted'))
        and cap.get('ordinaryOriginalReadValueAdmitted')is True and cap.get('ownConcreteGetterSemanticsProved')is True
        and cap.get('ordinaryOriginalCallbackAdmitted')is True
        and cap.get('ownConcreteFactorySemanticsProved')is True and type(cap.get('originalTypeDefinition'))is int
        and cap.get('originalTypeDefinition')>=0 and cap.get('valueStorageKind')=='reference8',
        dict(typeName=name,typeMatches=component.get('typeName')==name,capabilityMatches=component.get('capability')==key,
            compiledMatches=component.get('compiled')==replay['compiled'],requiredMatches=component.get('requiredExternalCapabilities')==replay['requiredExternalCapabilities'],
            capabilityDifferences=cap_differences,ownFlags={k:cap.get(k)for k in('ordinaryOriginalReadValueAdmitted','ordinaryOriginalCallbackAdmitted',
                'ownConcreteGetterSemanticsProved','ownConcreteFactorySemanticsProved','originalTypeDefinition','valueStorageKind')}))
    need('own-ordinary-adapter-and-canonical-callback',adapter.get('schema')=='endfield.reference-object-adapter-source.v1'
        and adapter.get('nativeInputs')==pins and adapter.get('typeName')==name and adapter.get('wrapperName')==source.get('wrapperName')
        and pair_matches and adapter.get('getterMethod')==source['lifecycle']['GetValue']['method']
        and adapter.get('pairForwarder',{}).get('readerMethod')==source['method']and len(faces)==1
        and cap.get('canonicalAdapterTargetRva')==adapter.get('callbackBinding',{}).get('canonicalTargetRva')
        and type(cap.get('canonicalAdapterTargetRva'))is int and cap['canonicalAdapterTargetRva']>0
        and cap.get('formatterDeserializeMethodDefinition')==faces[0].get('formatterDeserializeMethodIndex')
        and source['lifecycle']['GetValue']['program'].get('fullReferenceOutput')is True,
        dict(typeName=name,schema=adapter.get('schema'),pinsMatch=adapter.get('nativeInputs')==pins,
            adapterType=adapter.get('typeName'),adapterWrapper=adapter.get('wrapperName'),expectedWrapper=source.get('wrapperName'),
            pairMatches=pair_matches,getterActual=adapter.get('getterMethod'),getterExpected=source['lifecycle']['GetValue']['method'],
            readerActual=adapter.get('pairForwarder',{}).get('readerMethod'),readerExpected=source['method'],interfaceCount=len(faces),
            canonicalActual=cap.get('canonicalAdapterTargetRva'),canonicalExpected=adapter.get('callbackBinding',{}).get('canonicalTargetRva'),
            formatterActual=cap.get('formatterDeserializeMethodDefinition'),formatterExpected=faces[0].get('formatterDeserializeMethodIndex')if faces else None,
            fullReferenceOutput=source['lifecycle']['GetValue']['program'].get('fullReferenceOutput')))
    expected=dict(replay['capabilities']);expected[key]=cap
    need('all-and-only-independently-composed-capabilities',component.get('capabilities')==expected)
    return dict(capability=key,capabilities=normalized(component['capabilities']),
        requiredExternalCapabilities=list(component['requiredExternalCapabilities']))


def derive_selected(image,pins,*,source,children=None,value_binder=None):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.skill_root_child_bindings import reference_reader_abi
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    _publication_gate(image,pins);requests={}
    for read in source['orderedSourceReads']:
        if read['declaredType']in PLANS and read['memberIndex']in(children or{}):
            context=read.get('context',{});need('actual-reference-context',type(context.get('instructionRva'))is int)
            requests[read['memberIndex']]=derive_typed_usage_context(image,context['instructionRva'],label='animationExtraRecord.reference')
    record=compose_record(source,pins,children=children,value_binder=value_binder,typed_requests=requests)
    wrapper,=[w for w in image.memorypack_wrappers.values()if w.name==source['wrapperName']]
    method=source['method'];actual=image.metadata.methods[method[0]]
    need('fresh-method-and-owned-members',image.type_name(actual.declaring_type)==wrapper.name
        and image.metadata.string(actual.name_index)=='Deserialize'and image.method_pointer_va(actual)==image.pe.image_base+method[3]
        and wrapper.wrapped_type==source['wrappedType']and not image.metadata.methods[method[0]].flags&0x400
        and [(m.name,m.declared_type)for m in wrapper.members]==list(PLANS[source['wrappedType']]))
    image.check_windows(source['codeWindows'],label='animationExtraRecord.retained-complete-source')
    life=source['lifecycle'];owned=life.get('directHolderMode')is not True and'ownedCoherentGetter'in life['GetValue']
    pair=normalized(derive_pair(image,source['wrappedType'],wrapper.name,owned_getter_family=owned))
    adapter=derive_adapter(image,pins,pair,wrapper);references=reference_reader_abi(image,pins)
    face,=pair['composition']['interfaces'];cap=record['capabilities'][record['capability']]
    cap.update(ordinaryOriginalReadValueAdmitted=True,ordinaryOriginalCallbackAdmitted=True,ownConcreteGetterSemanticsProved=True,ownConcreteFactorySemanticsProved=True,
        originalTypeDefinition=image.named_types[source['wrappedType']].index,
        canonicalAdapterTargetRva=adapter['callbackBinding']['canonicalTargetRva'],
        formatterDeserializeMethodDefinition=face['formatterDeserializeMethodIndex'],
        **{k:references[k]for k in('referenceReaderMethodDefinition','referenceReaderTargetRva')})
    record.update(status='validated-conditional-animation-extra-record-components',
        proof=dict(source=source,valueChildren={}if children is None else children,pair=pair,adapter=adapter,referenceReaders=references))
    if requests:record['proof']['typedRequests']=requests
    validate_component(record,pins,value_binder=value_binder);_publication_gate(image,pins)
    return normalized(record)


def derive(image,pins,*,type_names,children=None,value_binder=None):
    from scripts.game_data.memorypack.generated_reader_sources import derive_many
    need('finite-distinct-selection',isinstance(type_names,(tuple,list))and bool(type_names)
        and len(type_names)==len(set(type_names))and set(type_names)<=set(PLANS))
    wrappers={w.wrapped_type:w for w in image.memorypack_wrappers.values()if w.wrapped_type in type_names}
    need('all-current-own-wrappers',set(wrappers)==set(type_names));owners=[]
    rows=derive_many(image,pins,[wrappers[n].name for n in type_names])['owners']
    for name,row in zip(type_names,rows,strict=True):
        try:
            need('complete-own-source:'+name,row['status']=='complete-reader-source-proved')
            component=derive_selected(image,pins,source=row['proof'],children=(children or{}).get(name),value_binder=value_binder)
            owners.append(dict(typeName=name,status=component['status'],proof=component))
        except(ValueError,KeyError,IndexError,TypeError)as error:owners.append(dict(typeName=name,status='pendingReview',reason=str(error)[:2000]))
    return dict(schema=SCHEMA,nativeInputs=pins,owners=owners,parentFieldAdmitted=False,wholeOwnerAdmitted=False)
