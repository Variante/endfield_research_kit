"""Ordinary CreateBuffActionInput and its actual action-owned reference list.

The root union's generated-wrapper capability supplies no ordinary Original
ReadValue admission. This owner independently joins the same complete concrete
MC5 source, its own cache32 GetValue, canonical ordinary adapter and actual
reference Reader. Its inherited cache24 remains distinct. The AssignPair40
list has its own complete value grammar and count loop. Initialized coherent
contexts, matching callbacks, normal typed allocation/helpers and stable
disjoint buffered storage remain conditions. No runtime buff application,
enclosing action/union, root or physical EOF follows from these components.
"""
import json

from scripts.game_data.memorypack.skill_root_child_bindings import need

TYPE='Beyond.Gameplay.Core.CreateBuffActionInput'
WRAPPER='Beyond.MemoryPack.Beyond_Gameplay_Core_CreateBuffActionInputForMemoryPack'
CAPABILITY='skill-action-create-buff-input'
LIST_CAPABILITY='skill-action-create-buff-input-list'
LIST='System.Collections.Generic.List`1<'+TYPE+'>'
SHARED=('skill-root-assign-pair','skill-root-assign-pair-list')
ORDER=[dict(fieldName=n,kind=k,childCapability=c)for n,k,c in(
    ('assignBlackboard','bool',None),('assignItems','value-list','skill-root-assign-pair-list'),
    ('buffId','pooled-string','byte-payload'),('buffIdKey','pooled-string','byte-payload'),
    ('readIdFromBlackboard','bool',None))]


def bind_components(parent,collection,adapter,readers,pins):
    """Pure source/ordinary-adapter joins; no saved proof grants admission."""
    need('Create-ordinary-same-source-native-inputs',pins,parent.get('nativeInputs'))
    need('Create-ordinary-exact-source',(TYPE,WRAPPER),tuple(parent.get(k)for k in('typeName','wrapperName')))
    need('Create-ordinary-complete-selected-paths',[5,5,None,None,5,None,None],
        [p.get('memberCount')for p in parent['programs']])
    need('Create-ordinary-full-selected-returns',True,all(p.get('normalReturn')is True
        and p.get('entryRspRestored')is True and p.get('inheritedCachesNotEquated')is True
        and(p.get('originalHolderOffset'),p.get('ownCacheOffset'),p.get('inheritedCacheOffset'))==(16,32,24)
        for p in parent['programs']))
    need('Create-ordinary-own-cache32',32,parent['ownCacheField']['offset'])
    for role in('getterPrograms','getValuePrograms'):
        need('Create-ordinary-complete-cache-states:'+role,['coherent','empty','stale'],
            [p.get('cacheState')for p in parent[role]])
        need('Create-ordinary-cache-returns:'+role,True,all(p.get('normalReturn')is True
            and type(p.get('typedCacheOffset'))is int and p['typedCacheOffset']==32
            and type(p.get('originalHolderOffset'))is int and p['originalHolderOffset']==16
            and type(p.get('wireBytes'))is int and p['wireBytes']==0
            and p.get('returnedReference')=='same original for coherent cache; exact typed nullable cast result on refresh'
            for p in parent[role]))
    need('Create-ordinary-actual-adapter',True,adapter.get('nativeInputs')==pins
        and(adapter.get('typeName'),adapter.get('wrapperName'))==(TYPE,WRAPPER)
        and adapter.get('pair')==parent['registeredPair']
        and adapter.get('getterReturnedReferenceSemanticsProved')is False
        and tuple(adapter['getterMethod'][1:3])==(WRAPPER,'GetValue'))
    need('Create-ordinary-child-native-inputs',pins,collection.get('nativeInputs'))
    need('Create-ordinary-child-source-status','validated-conditional-components',collection.get('status'))
    join,=parent['requiredChildJoins'];cap=collection['capabilities'][SHARED[1]]
    need('Create-ordinary-actual-assignItems',('assignItems','System.Collections.Generic.List`1<Beyond.Blackboard+AssignPair>'),
        (join['fieldName'],join['typeName']))
    need('Create-ordinary-list-request',True,(join['typedRequest'].get('tag'),join['typedRequest'].get('typeName'),
        join['typedRequest'].get('methodName'),join['typedRequest'].get('classArguments'),join['typedRequest'].get('methodArguments'))==
        (6,'MemoryPack.MemoryPackReader','ReadPackable',[],[join['typeName']]))
    need('Create-ordinary-actual-list-definition',cap['packableReaderMethodDefinition'],join['typedRequest']['methodSpec'][0])
    need('Create-ordinary-actual-list-target',cap['packableReaderTargetRva'],join['sourceTargetRva'])
    need('Create-ordinary-independent-value40-child',True,cap.get('elementType')=='Beyond.Blackboard+AssignPair'
        and cap.get('elementValueType')is True and cap.get('managedElementBytes')==40
        and type(cap.get('managedElementBytes'))is int and cap.get('elementGrammarAdmitted')is True
        and cap.get('positiveCountsAdmitted')is True and cap.get('elementCapability')==SHARED[0]
        and type(cap.get('countLimit'))is int and 1<=cap['countLimit']<=4096)
    need('Create-ordinary-literal-reference-Reader',True,
        type(readers.get('referenceReaderMethodDefinition'))is int and readers['referenceReaderMethodDefinition']>0
        and type(readers.get('referenceReaderTargetRva'))is int and readers['referenceReaderTargetRva']>0)
    return dict(typeName=TYPE,wrapperName=WRAPPER,memberCount=5,nullable=True,nullMarker=255,nullAdmitted=True,
        wholeGrammarAdmitted=True,ordinaryOriginalReadValueAdmitted=True,generatedWrapperOnly=False,
        ownConcreteGetterSemanticsProved=True,ownConcreteFactorySemanticsProved=True,orderedReads=ORDER,
        referenceReaderMethodDefinition=readers['referenceReaderMethodDefinition'],
        referenceReaderTargetRva=readers['referenceReaderTargetRva'],
        callbackSelectionConditional=True,wholeSkillDataAdmitted=False)


def _derive_on_source(image,pins,parent,collection):
    """Caller freshly derives the concrete source and list on this same image."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.skill_root_child_bindings import reference_reader_abi
    from scripts.game_data.memorypack.pointer_param import owned
    _publication_gate(image,pins)
    wrapper,=[w for w in image.memorypack_wrappers.values()if w.name==WRAPPER]
    need('Create-ordinary-actual-wrapper',TYPE,wrapper.wrapped_type)
    adapter=derive_adapter(image,pins,parent['registeredPair'],wrapper)
    getter=owned(image,image.pe.image_base+adapter['getterMethod'][3])
    need('Create-ordinary-same-owned-GetValue-windows',parent['getValueWindows'],getter['windows'])
    readers=reference_reader_abi(image,pins);cap=bind_components(parent,collection,adapter,readers,pins)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-action-create-buff-input-sources.v1',
        status='validated-conditional-ordinary-create-buff-input',nativeInputs=pins,capabilities={CAPABILITY:cap},
        requiredExternalCapabilities=[*SHARED,'byte-payload'],
        requiredExternalCapabilityShapes={name:collection['capabilities'][name]for name in SHARED},
        proof=dict(parent=parent,assignPairList=collection,ordinaryAdapter=adapter,referenceReaders=readers,
            getValueWindows=getter['windows']),wholeEnclosingActionAdmitted=False,wholeSkillDataAdmitted=False,
        evidenceBoundary=dict(exact='Complete concrete MC5/FF/new/cache/setter/factory source, independently selected own Original ordinary adapter and GetValue, actual reference Reader and positive AssignPair40 list joins.',
            conditional=__doc__,structuralOnly='Stored authored buff input.',
            unresolved=['enclosing action/list/union/root/EOF','runtime callback/provider selection','buff application']))))


def derive(image,pins):
    from scripts.game_data.memorypack.skill_root_create_buff_input_sources import derive as source
    from scripts.game_data.memorypack.skill_root_assign_pair_lists import derive as list_source
    parent=source(image,pins);join,=parent['requiredChildJoins']
    collection=list_source(image,pins,typed_request=join['typedRequest'],call_target=image.pe.image_base+join['sourceTargetRva'])
    return _derive_on_source(image,pins,parent,collection)


def _derive_list_on_child(image,pins,child,*,typed_request,call_target,count_limit=10000):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.reference_list_induction_sources import derive as list_source
    from scripts.game_data.memorypack.skill_action_reference_list_sources import (
        compose_reference_list,bind_parent_request,bind_reference_reader)
    _publication_gate(image,pins)
    need('Create-list-exact-closed-nominal',[LIST],typed_request.get('methodArguments'))
    listing=list_source(image,pins,typed_request=typed_request,call_target=call_target,element_type=TYPE,count_limit=count_limit)
    request=bind_parent_request(listing,typed_request,call_target,image.pe.image_base,label='action-Create-input-list')
    reader=bind_reference_reader(image,pins,listing,child,element_capability=CAPABILITY,label='action-Create-input-list')
    cap=compose_reference_list(listing,child,pins,element_type=TYPE,element_capability=CAPABILITY,label='action-Create-input-list')
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-action-create-buff-input-list.v1',
        status='validated-conditional-action-reference-list',nativeInputs=pins,
        capabilities={LIST_CAPABILITY:cap,CAPABILITY:child['capabilities'][CAPABILITY]},requiredExternalCapabilities=[CAPABILITY],
        proof=dict(collection=listing,child=child,actualParentRequestBinding=request,listElementReadValueBinding=reader),
        parentFieldAdmitted=False,wholeOwnerAdmitted=False,evidenceBoundary=dict(
            exact='Actual action List<CreateBuffActionInput> MethodSpec/E8, bounded reference count loop and separately complete nominal ordinary element.',
            conditional=__doc__,structuralOnly='Stored authored buff inputs.',
            unresolved=['enclosing action/union/root/EOF','runtime selection/application']))))


def derive_list(image,pins,*,typed_request,call_target,count_limit=10000):
    return _derive_list_on_child(image,pins,derive(image,pins),typed_request=typed_request,
        call_target=call_target,count_limit=count_limit)
