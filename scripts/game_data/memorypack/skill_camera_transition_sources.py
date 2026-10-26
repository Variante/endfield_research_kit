"""Finite ordinary camera transition records and two independent list levels.

The MC5 condition owns its bool/pool/enum/enum/Single sources. The MC1 And
record owns a separate actual ReadPackable<List<Condition>> source. Each list
independently proves its signed count, callback, construction, Add and loop.
Matching initialized canonical callbacks, coherent concrete originals, normal
typed allocation/helpers, disabled collector and stable disjoint buffered
storage remain conditions. Stored conditions prove no live camera behavior,
provider selection, enclosing action/root or physical EOF.
"""
import json

from scripts.game_data.memorypack.skill_root_child_bindings import need

CONDITION='Beyond.Gameplay.View.CameraControlState+TransitionCondition'
TYPE='Beyond.Gameplay.View.CameraControlState+TransitionConditionAnd'
WRAPPER='Beyond.MemoryPack.Beyond_Gameplay_View_CameraControlState_TransitionConditionAndForMemoryPack'
LEAF='skill-camera-transition-condition'
CAPABILITY='skill-camera-transition-and'
INNER_LIST='skill-camera-transition-condition-list'
LIST='skill-action-camera-transition-and-list'
ORDER=[dict(memberIndex=0,fieldName='and',kind='camera-transition-list',childCapability=INNER_LIST)]


def require_source(source,pins):
    need('camera-own-complete-source',True,source.get('schema')=='endfield.generated-concrete-reader-source.v1'
        and source.get('nativeInputs')==pins and(source.get('wrappedType'),source.get('wrapperName'))==(TYPE,WRAPPER)
        and source.get('completeSelectedCallerAdmitted')is True and source.get('childGrammarAdmitted')is False
        and source.get('wholeOwnerAdmitted')is False)
    need('camera-own-exact-list-field',[('and','System.Collections.Generic.List`1<'+CONDITION+'>')],
        [(r.get('fieldName'),r.get('declaredType'))for r in source.get('orderedSourceReads',[])])
    life=source['lifecycle']
    need('camera-own-direct-holder',True,life.get('directHolderMode')is True and life.get('typedCache')is None
        and life.get('baseHolder')==[WRAPPER,TYPE,16])
    paths=source.get('programs',[])
    need('camera-own-four-return-frames',True,len(paths)==4 and all(type(p.get('existing'))is bool
        and type(p.get('wrapperNull'))is bool and p.get('frame',{}).get('entryRspRestored')is True
        and p['frame'].get('allWin64IntegerNonvolatilesRestored')is True for p in paths)
        and{(p['existing'],p['wrapperNull'])for p in paths}=={(False,False),(True,False),(False,True),(True,True)})


def bind_program(program):
    need('camera-own-literal-count',True,type(program.get('memberCount'))is int and program['memberCount']==1)
    need('camera-own-complete-list-program',True,program.get('reads')==ORDER
        and all(type(r.get('memberIndex'))is int for r in program['reads'])
        and program.get('requiredCapabilities')==[INNER_LIST])


def bind_inner(pins,join,child,capability):
    need('camera-inner-native-inputs',pins,child['nativeInputs'])
    need('camera-inner-capability',INNER_LIST,capability)
    nominal='System.Collections.Generic.List`1<'+CONDITION+'>';cap=child['capabilities'][INNER_LIST]
    usage=join['typedRequest']
    need('camera-inner-owned-nominal',('and',nominal),(join['fieldName'],join['typeName']))
    need('camera-inner-actual-request',(6,'MemoryPack.MemoryPackReader','ReadPackable',[],[nominal]),
        tuple(usage.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments')))
    need('camera-inner-actual-reader',True,type(usage['methodSpec'][0])is int
        and usage['methodSpec'][0]==cap['packableReaderMethodDefinition']
        and type(join.get('sourceTargetRva'))is int and join['sourceTargetRva']==cap['packableReaderTargetRva'])
    witness=child['proof']['collection']['witnessComponent']
    need('camera-inner-same-owned-context',usage,witness['typedRequest'])
    need('camera-inner-same-owned-call',join['sourceTargetRva'],witness['callTargetRva'])
    return dict(fieldName='and',typeName=nominal,capability=capability,
        readerMethodDefinition=cap['packableReaderMethodDefinition'],sourceTargetRva=cap['packableReaderTargetRva'],
        collectionCapabilityShape=cap,elementCapabilityShape=child['capabilities'][LEAF])


def _list_on_child(image,pins,child,*,typed_request,call_target,outer,count_limit=10000):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.reference_list_induction_sources import derive
    from scripts.game_data.memorypack.skill_action_reference_list_sources import compose_reference_list,bind_parent_request,bind_reference_reader
    _publication_gate(image,pins);need('camera-list-literal-level',True,type(outer)is bool)
    nominal,element,capability=(TYPE,CAPABILITY,LIST)if outer else(CONDITION,LEAF,INNER_LIST)
    source=derive(image,pins,typed_request=typed_request,call_target=call_target,element_type=nominal,count_limit=count_limit)
    parent=bind_parent_request(source,typed_request,call_target,image.pe.image_base,label='camera-transition-list')
    reader=bind_reference_reader(image,pins,source,child,element_capability=element,label='camera-transition-list')
    cap=compose_reference_list(source,child,pins,element_type=nominal,element_capability=element,label='camera-transition-list')
    _publication_gate(image,pins)
    return dict(nativeInputs=pins,capabilities={**child['capabilities'],capability:cap},
        proof=dict(collection=source,child=child,actualParentRequestBinding=parent,listElementReaderBinding=reader),
        parentFieldAdmitted=False,wholeOwnerAdmitted=False)


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.skill_action_reference_components import derive as leaf_source
    from scripts.game_data.memorypack.generated_reader_sources import derive as caller
    from scripts.game_data.memorypack.generated_record_components import compile_member_program
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.pointer_param import leaf
    from scripts.game_data.memorypack.skill_root_child_bindings import reference_reader_abi
    _publication_gate(image,pins);condition=leaf_source(image,pins,type_names=[CONDITION])
    source=caller(image,pins,WRAPPER);require_source(source,pins);read,=source['orderedSourceReads']
    request=derive_typed_usage_context(image,read['context']['instructionRva'],label='cameraTransition.inner')
    inner=_list_on_child(image,pins,condition,typed_request=request,call_target=image.pe.image_base+read['sourceTargetRva'],outer=False)
    nominal='System.Collections.Generic.List`1<'+CONDITION+'>'
    compiled,pending=compile_member_program(source,pins,wrapper_name=WRAPPER,type_name=TYPE,value4={},
        typed_requests={0:request},collections={nominal:(INNER_LIST,'camera-transition-list',INNER_LIST)},
        collection_children={0:inner},collection_binder=bind_inner)
    need('camera-all-inner-source-joins',[],pending);bind_program(compiled)
    wrapper,=[w for w in image.memorypack_wrappers.values()if w.name==WRAPPER]
    pair=derive_pair(image,TYPE,WRAPPER);adapter=derive_adapter(image,pins,pair,wrapper)
    need('camera-same-owned-getter',source['lifecycle']['GetValue']['method'],adapter['getterMethod'])
    getter=leaf(image,image.pe.image_base+adapter['getterMethod'][3],['488B4110','C3'])
    need('camera-same-owned-reader',source['method'],adapter['pairForwarder']['readerMethod'])
    abi=reference_reader_abi(image,pins)
    cap=dict(typeName=TYPE,wrapperName=WRAPPER,memberCount=1,orderedReads=ORDER,nullable=True,nullMarker=255,
        nullAdmitted=True,wholeGrammarAdmitted=True,ordinaryOriginalReadValueAdmitted=True,
        ownConcreteGetterSemanticsProved=True,ownConcreteFactorySemanticsProved=True,completeSourceOwnedProgram=True,
        **{k:abi[k]for k in('referenceReaderMethodDefinition','referenceReaderTargetRva')})
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-camera-transition-sources.v1',
        status='validated-conditional-camera-transitions',nativeInputs=pins,
        capabilities={**inner['capabilities'],CAPABILITY:cap},requiredExternalCapabilities=['byte-payload'],
        proof=dict(source=source,compiled=compiled,condition=condition,inner=inner,pair=pair,adapter=adapter,getter=getter,referenceReader=abi),
        parentFieldAdmitted=False,wholeOwnerAdmitted=False,evidenceBoundary=dict(
            exact='Own ordinary five-field condition, actual separately induced inner list and own ordinary one-field And record, complete new/existing/FF frames and independent canonical adapters/Reader.',
            conditional=__doc__,structuralOnly='Stored camera transition conditions.',
            unresolved=['actual outer list/action/root/physical EOF','runtime camera/provider choice']))))


def _derive_list_on_child(image,pins,child,*,typed_request,call_target,count_limit=10000):
    result=_list_on_child(image,pins,child,typed_request=typed_request,call_target=call_target,outer=True,count_limit=count_limit)
    result.update(schema='endfield.skill-camera-transition-list-sources.v1',status='validated-conditional-camera-transition-list',
        requiredExternalCapabilities=['byte-payload'])
    return json.loads(json.dumps(result))


def derive_list(image,pins,*,typed_request,call_target,count_limit=10000):
    return _derive_list_on_child(image,pins,derive(image,pins),typed_request=typed_request,call_target=call_target,count_limit=count_limit)
