"""Selected CharAnim actions in the actual CharInteract loopActions list.

The root's existing complete sparse source owns the named field transfer.
The independent reference-list owner supplies count/Add/provider programs;
the animation union supplies its own canonical reference adapter, selected
tag and inherited conversion. Only their exact callback and nominal joins
are composed here. Other root fields retain their existing sparse profiles.
Runtime selection, nonempty reuse/growth and public opt-in remain separate.
"""
import json

TYPE='Beyond.Gameplay.Core.CharInteractPerform.CharInteractPerformActionData'
ROOT='Beyond.Gameplay.Core.CharInteractPerform.CharInteractPerformRuntimeCfg'
CAPABILITY='animation-char-loop-actions'
UNION_CAPABILITY='animation-char-selected-union'
SCHEMA='endfield.animation-char-loop-sources.v1'


def need(check,condition,detail=None):
    if not condition:raise ValueError('animationCharLoop.'+check+':'+str(detail)[:800])


def compose(collection,union,pins,*,parent_binding,callback_binding):
    """Pure selected nominal/count/callback join, preserving source conditions."""
    nominal='System.Collections.Generic.List`1<'+TYPE+'>'
    need('same-native-inputs',collection.get('nativeInputs')==union.get('nativeInputs')==pins and bool(pins))
    need('independently-proved-reference-list',collection.get('status')=='validated-bounded-reference-list-induction'
        and collection.get('elementType')==TYPE and collection.get('nullable')is True
        and collection.get('freshListsAdmitted')is True and collection.get('reusedListsRequireInitialCount')==0
        and type(collection.get('reusedListsRequireInitialCount'))is int
        and collection.get('reusedListsRequireCapacityAtLeastCount')is True
        and all(collection.get(k)is False for k in('elementGrammarAdmitted','parentFieldAdmitted','wholeOwnerAdmitted')))
    counts=collection.get('countRange')
    need('literal-bounded-counts',isinstance(counts,list)and len(counts)==2
        and all(type(n)is int for n in counts)and counts[0]==-1 and 3<=counts[1]<=10000)
    witness=collection.get('witnessComponent',{});request=witness.get('typedRequest',{})
    need('actual-closed-parent-list-request',(request.get('tag'),request.get('typeName'),request.get('methodName'),
        request.get('classArguments'),request.get('methodArguments'))==(6,'MemoryPack.MemoryPackReader','ReadPackable',[],[nominal])
        and type(request.get('methodSpec',[None])[0])is int and request['methodSpec'][0]>0
        and type(witness.get('callTargetRva'))is int and witness['callTargetRva']>0)
    cap=union.get('capabilities',{}).get(UNION_CAPABILITY,{})
    need('separate-selected-char-union',union.get('schema')=='endfield.animation-selected-union-components.v1'
        and union.get('status')=='validated-conditional-selected-animation-union-components'
        and union.get('family')=='char-animation'and union.get('capability')==UNION_CAPABILITY
        and cap.get('typeName')==TYPE and cap.get('wholeGrammarAdmitted')is True
        and cap.get('selectedStoredByteGrammarAdmitted')is True and cap.get('ordinaryBaseAdapterAdmitted')is True
        and cap.get('inheritedBaseConversionsAdmitted')is True
        and cap.get('compatibleExistingWrapperAdmitted')is False
        and cap.get('declaredUnionEntries')==48 and cap.get('allDeclaredTagsCovered')is False
        and cap.get('collectionParentAdmitted')is False and cap.get('wholeOwnerAdmitted')is False)
    routes=cap.get('selectedRoutes',[])
    need('only-actual-char-animation-tag',len(routes)==1 and routes[0].get('tag')==8
        and type(routes[0]['tag'])is int and routes[0].get('childCapability')=='char-anim-action-record')
    source=union.get('proof',{}).get('unionSource',{}).get('families',{}).get('char-animation',{})
    adapter=source.get('adapter',{});binding=adapter.get('callbackBinding',{})
    need('own-union-canonical-callback',adapter.get('schema')=='endfield.reference-object-adapter-source.v1'
        and adapter.get('nativeInputs')==pins and adapter.get('typeName')==TYPE
        and adapter.get('wrapperName')==cap.get('wrapperName')
        and binding.get('actualCallbackEqualsCanonicalRequired')is True
        and type(binding.get('canonicalTargetRva'))is int and binding['canonicalTargetRva']>0)
    need('same-actual-list-to-base-callback',callback_binding.get('canonicalTargetRva')==binding['canonicalTargetRva']
        and callback_binding.get('baseWrapper')==cap['wrapperName']
        and callback_binding.get('unionTargetRva')==int(source.get('switch',{}).get('dispatcherVa','0'),16)-callback_binding.get('imageBase',0)
        and callback_binding.get('formatterSlot')==5 and callback_binding.get('selectedMethodInfoForwarded')is True
        and callback_binding.get('sameReaderAndOutput')is True
        and callback_binding.get('runtimeSelectionObserved')is False
        and bool(callback_binding.get('dispatchProgram'))and bool(callback_binding.get('elementCallbackPrograms')))
    need('actual-named-root-field',parent_binding.get('typeName')==ROOT and parent_binding.get('fieldName')=='loopActions'
        and parent_binding.get('declaredType')==nominal and parent_binding.get('storedBytes')==8
        and parent_binding.get('typedRequest')==request and parent_binding.get('sourceTargetRva')==witness['callTargetRva']
        and parent_binding.get('completeSparseRootSourceProved')is True
        and parent_binding.get('allOtherRootFieldProfilesUnchanged')is True)
    caps=dict(union['capabilities'])
    caps[CAPABILITY]=dict(typeName=nominal,elementType=TYPE,elementValueType=False,
        elementCapability=UNION_CAPABILITY,positiveCountsAdmitted=True,elementGrammarAdmitted=True,
        nullable=True,countRange=counts,countLimit=counts[1],freshListsAdmitted=True,
        reusedListsRequireInitialCount=0,reusedListsRequireCapacityAtLeastCount=True,
        packableReaderMethodDefinition=request['methodSpec'][0],packableReaderTargetRva=witness['callTargetRva'],
        selectedElementTags=[8],nullElementMarker=255,otherElementTagsAdmitted=False,
        parentType=ROOT,parentField='loopActions',actualParentFieldAdmitted=True,wholeOwnerAdmitted=False)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-animation-char-loop',
        nativeInputs=pins,capability=CAPABILITY,capabilities=caps,
        requiredExternalCapabilities=union.get('requiredExternalCapabilities',[]),
        publicDecoderActivated=False,wholeOwnerAdmitted=False,
        proof=dict(collection=collection,union=union,parentBinding=parent_binding,callbackBinding=callback_binding),
        evidenceBoundary=__doc__)))


def _derive_on_union(image,pins,union,*,count_limit=10000):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data import char_interact_perform_sparse_native as sparse
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.formatter_value_paths import deserialize_slot
    from scripts.game_data.memorypack.reference_list_induction_sources import derive as list_source
    from scripts.game_data.memorypack.module_structure_models import bridge_list_callback
    from scripts.game_data.memorypack.animation_union_sources import _owned
    _publication_gate(image,pins);base=image.pe.image_base
    fact=json.loads(sparse.CONTRACT_PATH.read_bytes())
    need('same-current-sparse-root',fact.get('schema')=='endfield.char-interact-perform-sparse-native.v4'
        and fact.get('status')=='conditional-current-build-wire'and fact.get('nativeInputs')==pins)
    actual=sparse.derive(image,fact)
    root,=[r['proof']for r in actual['proofs']if r['model']=='root']
    chosen,=[r for r in root['fields']if r['name']=='loopActions']
    field,=[r for r in actual['fields']if r['name']=='loopActions']
    context,=chosen['contextCells']
    usage=derive_typed_usage_context(image,context['instruction']-base,label='animationCharLoop.parent')
    collection=list_source(image,pins,typed_request=usage,call_target=chosen['sourceTarget'],
        element_type=TYPE,count_limit=count_limit)
    source=union['proof']['unionSource']['families']['char-animation'];adapter=source['adapter']
    symbols=adapter['canonicalRoutes']['symbolRvas']
    need('same-root-and-union-reference-helpers',symbols==fact['profile']['referenceRoutes']['symbolRvas'])
    dispatcher=base+symbols['dispatch'];body=_owned(image,dispatcher)
    face,=adapter['pair']['composition']['interfaces']
    callback=image.method_pointer_va(image.metadata.methods[face['formatterDeserializeMethodIndex']])
    need('actual-union-slot-five',callback==int(source['switch']['dispatcherVa'],16))
    dispatch_program=deserialize_slot(body['regions'],dispatcher,prepare=base+symbols['prepare'],callback=callback)
    witness=collection['witnessComponent'];regions=[(base+w['startRva'],image.window_bytes(w))for w in witness['windows']]
    sites=sorted({site for p in witness['programs']for site in p['elementCallbackSites']})
    need('actual-positive-list-callback-site',len(sites)==1)
    bridges=[bridge_list_callback(regions,site-38,base+symbols['prepare'])for site in sites]
    parent=dict(typeName=ROOT,wrapperName=fact['profile']['wrapper'],fieldName='loopActions',declaredType=field['type'],
        storedBytes=8,typedRequest=usage,sourceTargetRva=chosen['sourceTarget']-base,
        completeSparseRootSourceProved=True,allOtherRootFieldProfilesUnchanged=True,
        actualFieldTransfer=chosen,rootSource=root)
    binding=dict(baseWrapper=source['wrapperName'],canonicalTargetRva=adapter['callbackBinding']['canonicalTargetRva'],
        imageBase=base,unionTargetRva=callback-base,formatterSlot=5,selectedMethodInfoForwarded=True,
        sameReaderAndOutput=True,runtimeSelectionObserved=False,dispatchProgram=dispatch_program,
        elementCallbackPrograms=bridges)
    result=compose(collection,union,pins,parent_binding=parent,callback_binding=binding)
    result['legacySparseProfile']=dict(nativeInputs=dict(pins),fields=actual['fields'],
        actorFields=actual['actorListOne']['fields'],actionFields=actual['actionListOne']['fields'],
        allOtherRootProfilesUnchanged=True)
    result['proof']['legacySparseSource']=actual
    _publication_gate(image,pins);return result


def derive(image,pins,*,count_limit=10000):
    """Fresh selected record, union, list, callback and root field on one image."""
    from scripts.game_data.memorypack import animation_record_components as records,animation_union_sources as unions
    from scripts.game_data.memorypack.animation_union_components import compose as union_component
    name='Beyond.Gameplay.Core.CharInteractPerform.CharAnimActionData'
    row,=records.derive(image,pins,type_names=[name])['owners']
    need('complete-selected-char-record',row.get('status')=='validated-conditional-animation-record-components',
        row.get('reason',row.get('proof',{}).get('pending')))
    union=union_component(unions.derive(image,pins,families=['char-animation']),[row['proof']],family='char-animation')
    return _derive_on_union(image,pins,union,count_limit=count_limit)
