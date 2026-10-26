"""Ordinary MultiAim LookAtTargetInfo and its independently selected list.

The named MC4 source stores MountPoint enum32, one bool, the exact ordinary
TargetSettings reference and Single bits. Complete new/existing/FF frames,
own holder16 construction/getter and canonical adapter precede the actual
Reader/MethodSpec/E8 joins. The list separately owns signed count, typed
callback, capacity construction, Add and fresh/reused-empty bounded induction.
Neither the record nor list supplies enclosing MultiAim framing or file EOF.

Coherent initialized contexts, matching callbacks, normal typed allocation and
helpers, disabled collector and stable sufficient disjoint storage remain
conditions. Live provider selection, camera behavior, nonempty reuse, growth,
refill and error paths remain unresolved. Managed reference stride is not wire
width; TargetSettings retains its own finite recursive source/child domain.
"""
import json

from scripts.game_data.memorypack.skill_root_child_bindings import need

SCHEMA='endfield.skill-look-at-target-sources.v1'
TYPE='Beyond.Gameplay.Core.LockCameraMultiAimAction+LookAtTargetInfo'
WRAPPER='Beyond.MemoryPack.Beyond_Gameplay_Core_LockCameraMultiAimAction_LookAtTargetInfoForMemoryPack'
CAPABILITY='skill-look-at-target-info'
LIST='skill-look-at-target-info-list'
TARGET='Beyond.Gameplay.Core.TargetSettings'
CHILD='target-profile'
MEMBERS=(('mountPoint','Beyond.Gameplay.MountPoint'),('overrideTarget','bool'),
    ('targetSettings',TARGET),('weight','float'))
ORDER=[dict(memberIndex=i,fieldName=n,kind=k,childCapability=c)for i,(n,k,c)in enumerate((
    ('mountPoint','scalar32',None),('overrideTarget','bool-byte',None),
    ('targetSettings',CHILD,CHILD),('weight','float32-bits',None)))]


def require_source(source,pins):
    need('look-at-own-complete-source',True,source.get('schema')=='endfield.generated-concrete-reader-source.v1'
        and source.get('nativeInputs')==pins and(source.get('wrappedType'),source.get('wrapperName'))==(TYPE,WRAPPER)
        and source.get('completeSelectedCallerAdmitted')is True and source.get('childGrammarAdmitted')is False
        and source.get('wholeOwnerAdmitted')is False)
    need('look-at-named-field-order',list(MEMBERS),
        [(r.get('fieldName'),r.get('declaredType'))for r in source.get('orderedSourceReads',[])])
    life=source['lifecycle']
    need('look-at-own-direct-holder',True,life.get('directHolderMode')is True and life.get('typedCache')is None
        and life.get('baseHolder')==[WRAPPER,TYPE,16])
    paths=source.get('programs',[])
    need('look-at-four-complete-frames',True,len(paths)==4 and all(type(p.get('existing'))is bool
        and type(p.get('wrapperNull'))is bool and p.get('frame',{}).get('entryRspRestored')is True
        and p['frame'].get('allWin64IntegerNonvolatilesRestored')is True for p in paths)
        and{(p['existing'],p['wrapperNull'])for p in paths}=={(False,False),(True,False),(False,True),(True,True)})


def bind_program(compiled):
    need('look-at-literal-count',True,type(compiled.get('memberCount'))is int and compiled['memberCount']==4)
    need('look-at-complete-program',True,compiled.get('reads')==ORDER
        and all(type(r.get('memberIndex'))is int for r in compiled['reads'])
        and compiled.get('requiredCapabilities')==[CHILD])
    return ORDER


def _derive_on_target(image,pins,target):
    """Internal same-image join; caller freshly derives the finite EC owner."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.generated_reader_sources import derive as caller
    from scripts.game_data.memorypack.generated_record_components import compile_member_program
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.pointer_param import leaf
    from scripts.game_data.memorypack.skill_root_child_bindings import reference_reader_abi
    from scripts.game_data.memorypack.skill_look_at_target_codec import require_target
    _publication_gate(image,pins);need('look-at-target-same-native-inputs',pins,target['nativeInputs'])
    child=require_target(target['capabilities'][CHILD])
    source=caller(image,pins,WRAPPER);require_source(source,pins);read=source['orderedSourceReads'][2]
    usage=derive_typed_usage_context(image,read['context']['instructionRva'],label='skillLookAtTarget')
    compiled,pending=compile_member_program(source,pins,wrapper_name=WRAPPER,type_name=TYPE,value4={},
        references={TARGET:(CHILD,CHILD,CHILD)},reference_children={TARGET:target},typed_requests={2:usage})
    need('look-at-all-child-joins',[],pending);bind_program(compiled)
    binding,=compiled['childBindings']
    need('look-at-same-actual-child-source',True,binding['fieldName']=='targetSettings'
        and binding['typeName']==TARGET and binding['capability']==CHILD
        and binding['readerMethodDefinition']==usage['methodSpec'][0]==child['referenceReaderMethodDefinition']
        and binding['sourceTargetRva']==read['sourceTargetRva']==child['referenceReaderTargetRva'])
    wrapper,=[w for w in image.memorypack_wrappers.values()if w.name==WRAPPER]
    pair=derive_pair(image,TYPE,WRAPPER);adapter=derive_adapter(image,pins,pair,wrapper)
    need('look-at-same-own-getter',source['lifecycle']['GetValue']['method'],adapter['getterMethod'])
    need('look-at-same-own-reader',source['method'],adapter['pairForwarder']['readerMethod'])
    getter=leaf(image,image.pe.image_base+adapter['getterMethod'][3],['488B4110','C3'])
    reader=reference_reader_abi(image,pins)
    cap=dict(typeName=TYPE,wrapperName=WRAPPER,memberCount=4,orderedReads=ORDER,nullable=True,nullMarker=255,
        nullAdmitted=True,wholeGrammarAdmitted=True,ordinaryOriginalReadValueAdmitted=True,
        ownConcreteGetterSemanticsProved=True,ownConcreteFactorySemanticsProved=True,completeSourceOwnedProgram=True,
        **{k:reader[k]for k in('referenceReaderMethodDefinition','referenceReaderTargetRva')},
        callbackSelectionConditional=True,wholeOwnerAdmitted=False)
    identity={k:child[k]for k in('typeName','referenceReaderMethodDefinition','referenceReaderTargetRva')}
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-look-at-target',nativeInputs=pins,
        capabilities={CAPABILITY:cap},requiredExternalCapabilities=[CHILD],
        requiredExternalCapabilityIdentities={CHILD:identity},requiredExternalCapabilityShapes={CHILD:child},
        proof=dict(source=source,compiled=compiled,typedRequest=usage,target=target,pair=pair,adapter=adapter,
            getter=getter,referenceReaders=reader),parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Named complete MC4 source, own ordinary lifecycle/adapter/Reader, actual nominal TargetSettings call and finite child program.',
            conditional=__doc__,structuralOnly='Stored MultiAim target configuration.',
            unresolved=['actual enclosing MultiAim/list/root/EOF','runtime camera/provider selection','refill/error paths']))))


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.skill_ec_components import derive as target
    _publication_gate(image,pins)
    return _derive_on_target(image,pins,target(image,pins))


def _derive_list_on_child(image,pins,child,*,typed_request,call_target,count_limit=10000):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.reference_list_induction_sources import derive as collection_source
    from scripts.game_data.memorypack.skill_action_reference_list_sources import compose_reference_list,bind_parent_request,bind_reference_reader
    from scripts.game_data.memorypack.skill_look_at_target_codec import require_record
    _publication_gate(image,pins);require_record(child['capabilities'][CAPABILITY])
    source=collection_source(image,pins,typed_request=typed_request,call_target=call_target,element_type=TYPE,count_limit=count_limit)
    parent=bind_parent_request(source,typed_request,call_target,image.pe.image_base,label='look-at-target-list')
    reader=bind_reference_reader(image,pins,source,child,element_capability=CAPABILITY,label='look-at-target-list')
    cap=compose_reference_list(source,child,pins,element_type=TYPE,element_capability=CAPABILITY,label='look-at-target-list')
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-look-at-target-list',nativeInputs=pins,
        capabilities={**child['capabilities'],LIST:cap},requiredExternalCapabilities=child['requiredExternalCapabilities'],
        requiredExternalCapabilityIdentities=child['requiredExternalCapabilityIdentities'],
        requiredExternalCapabilityShapes=child['requiredExternalCapabilityShapes'],
        proof=dict(child=child,collection=source,actualParentRequestBinding=parent,listElementReaderBinding=reader),
        parentFieldAdmitted=False,wholeOwnerAdmitted=False,evidenceBoundary=dict(
            exact='Independent signed count/callback/Add/fresh and reused-empty induction with own ordinary MC4 child and exact supplied parent request/E8.',
            conditional=__doc__,structuralOnly='Stored target collection.',unresolved=['enclosing owner/EOF','runtime callback selection','growth/nonempty reuse/refill']))))


def derive_list(image,pins,*,typed_request,call_target,count_limit=10000):
    return _derive_list_on_child(image,pins,derive(image,pins),typed_request=typed_request,call_target=call_target,count_limit=count_limit)
