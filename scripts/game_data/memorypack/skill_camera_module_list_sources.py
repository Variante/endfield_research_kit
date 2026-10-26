"""Actual closed ModuleConfig list joined to its thirteen-route ordinary union.

The abstract base owns no concrete factory. Each actual selected tag instead
uses its independently proved concrete getter/factory/wire program and inherited
base conversion. List count/callback/Add induction and parent MethodInfo/E8 are
separate. Coherent canonical callbacks, fresh or reused-empty lists with enough
capacity, disabled collector and normal compatible helpers remain conditions.
No growth/refill, live provider choice, parent/root/EOF or camera runtime claim
is admitted by a reference representation or by this list alone.
"""
import json

from scripts.game_data.memorypack import skill_camera_module_components as source
from scripts.game_data.memorypack.skill_camera_module_codec import require_union


def need(check,condition):
    if not condition:raise ValueError('skillCameraModuleListSources.'+check)


def compose(collection,union,pins):
    need('same-selected-native-inputs',collection.get('nativeInputs')==union.get('nativeInputs')==pins)
    need('independent-reference-count-induction',collection.get('status')=='validated-bounded-reference-list-induction'
        and collection.get('elementType')==source.TYPE and all(collection.get(k)is False for k in
            ('elementGrammarAdmitted','parentFieldAdmitted','wholeOwnerAdmitted'))
        and collection.get('freshListsAdmitted')is True and collection.get('nullable')is True
        and type(collection.get('reusedListsRequireInitialCount'))is int and collection['reusedListsRequireInitialCount']==0
        and collection.get('reusedListsRequireCapacityAtLeastCount')is True)
    counts=collection.get('countRange',[])
    need('literal-bounded-count-domain',len(counts)==2 and all(type(n)is int for n in counts)and counts[0]==-1 and counts[1]==10000)
    need('own-finite-module-grammar',union.get('schema')==source.SCHEMA and union.get('status')=='validated-conditional-camera-module-components'
        and union.get('wholeOwnerAdmitted')is False
        and set(union.get('capabilities',{}))=={source.CAPABILITY,*[r['capability']for r in source.RECORDS.values()]})
    cap=require_union(union['capabilities'][source.CAPABILITY]);witness=collection['witnessComponent'];usage=witness['typedRequest']
    nominal='System.Collections.Generic.List`1<'+source.TYPE+'>'
    need('actual-closed-nominal-parent',(6,'MemoryPack.MemoryPackReader','ReadPackable',[],[nominal])==
        tuple(usage.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments')))
    need('actual-list-callback-reader-definition',cap['referenceReaderMethodDefinition']==witness['referenceSource']['valueContext']['readerMethodDefinition'])
    need('literal-actual-parent-helper',type(usage['methodSpec'][0])is int and usage['methodSpec'][0]>0
        and type(witness.get('callTargetRva'))is int and witness['callTargetRva']>0)
    return dict(elementType=source.TYPE,elementValueType=False,closedListType=nominal,elementCapability=source.CAPABILITY,
        collectionCounts=[-1,0],countLimit=10000,positiveCountsAdmitted=True,nullable=True,elementGrammarAdmitted=True,
        packableReaderMethodDefinition=usage['methodSpec'][0],packableReaderTargetRva=witness['callTargetRva'],
        callbackSelectionConditional=True,wholeOwnerAdmitted=False)


def _derive_on_union(image,pins,union,*,typed_request,call_target,count_limit=10000):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.reference_list_induction_sources import derive as list_source
    from scripts.game_data.memorypack.skill_action_reference_list_sources import bind_parent_request,bind_reference_reader
    need('literal-current-resource-bound',type(count_limit)is int and count_limit==10000)
    _publication_gate(image,pins)
    collection=list_source(image,pins,typed_request=typed_request,call_target=call_target,element_type=source.TYPE,count_limit=count_limit)
    parent=bind_parent_request(collection,typed_request,call_target,image.pe.image_base,label='camera-module-list')
    reader=bind_reference_reader(image,pins,collection,union,element_capability=source.CAPABILITY,label='camera-module-list')
    cap=compose(collection,union,pins);caps=dict(union['capabilities']);caps[source.LIST]=cap
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-camera-module-list-sources.v1',status='validated-conditional-camera-module-list',nativeInputs=pins,
        capabilities=caps,requiredExternalCapabilities=union['requiredExternalCapabilities'],
        requiredExternalCapabilityIdentities=union['requiredExternalCapabilityIdentities'],
        proof=dict(collection=collection,union=union,actualParentRequestBinding=parent,listElementReaderBinding=reader),
        parentFieldAdmitted=False,wholeOwnerAdmitted=False,evidenceBoundary=dict(exact='Actual nominal signed count/callback/Add induction and parent MethodInfo/E8 joined to the complete ordinary thirteen-route union and every concrete record source/Curve.',
            conditional=__doc__,structuralOnly='Stored camera module list.',
            unresolved=['actual enclosing parent/action/root/physical EOF','live callback/provider selection','nonempty reuse/growth/refill']))))


def derive(image,pins,*,typed_request,call_target,count_limit=10000):
    return _derive_on_union(image,pins,source.derive(image,pins),typed_request=typed_request,call_target=call_target,count_limit=count_limit)
