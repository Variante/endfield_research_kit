"""Actual reference-list source joined to the finite SpecialAim base union.

The abstract base has no concrete factory claim. Every actual tag's concrete
wrapper factory and inherited base conversion instead come from its fresh
finite union owner. Count/callback/Add induction and the actual parent request
remain separate proofs. Matching canonical callbacks, coherent initialized
contexts, fresh zeroed or reused-empty lists with spare capacity, normal helper
effects and disabled collector are conditions; runtime choice, growth/refill
and enclosing actions/root/EOF remain unproved.
"""
import json

from scripts.game_data.memorypack.skill_root_child_bindings import need
from scripts.game_data.memorypack.skill_special_aim_components import TYPE,CAPABILITY,SECTOR,LIST


def compose(collection,union,pins):
    need('SpecialAim-list-same-selected-inputs',True,collection.get('nativeInputs')==union.get('nativeInputs')==pins)
    need('SpecialAim-list-independent-induction',True,collection.get('status')=='validated-bounded-reference-list-induction'
        and collection.get('elementType')==TYPE and all(collection.get(k)is False for k in
            ('elementGrammarAdmitted','parentFieldAdmitted','wholeOwnerAdmitted'))
        and collection.get('freshListsAdmitted')is True and collection.get('nullable')is True
        and type(collection.get('reusedListsRequireInitialCount'))is int and collection['reusedListsRequireInitialCount']==0
        and collection.get('reusedListsRequireCapacityAtLeastCount')is True)
    counts=collection.get('countRange',[])
    need('SpecialAim-list-literal-count-bound',True,len(counts)==2 and all(type(n)is int for n in counts)
        and counts[0]==-1 and 3<=counts[1]<=10000)
    need('SpecialAim-list-own-finite-union',True,union.get('schema')=='endfield.skill-special-aim-components.v1'
        and union.get('status')=='validated-conditional-special-aim-union'and union.get('wholeOwnerAdmitted')is False
        and set(union.get('capabilities',{}))=={CAPABILITY,SECTOR})
    cap=union['capabilities'][CAPABILITY]
    need('SpecialAim-list-base-and-concrete-proof',True,cap.get('typeName')==TYPE and all(cap.get(k)is True for k in
        ('wholeGrammarAdmitted','ordinaryOriginalReadValueAdmitted','baseGetterSemanticsProved',
            'concreteChildGrammarsProved','allConcreteFactoriesProved'))
        and cap.get('supportedShortTags')==[0]and all(type(n)is int for n in cap['supportedShortTags'])
        and cap.get('extendedTagsAdmitted')is False and cap.get('reservedMarkersAdmitted')is False
        and type(cap.get('referenceReaderMethodDefinition'))is int and cap['referenceReaderMethodDefinition']>0
        and type(cap.get('referenceReaderTargetRva'))is int and cap['referenceReaderTargetRva']>0)
    witness=collection['witnessComponent'];usage=witness['typedRequest'];nominal='System.Collections.Generic.List`1<'+TYPE+'>'
    need('SpecialAim-list-actual-closed-parent',(6,'MemoryPack.MemoryPackReader','ReadPackable',[],[nominal]),
        tuple(usage.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments')))
    need('SpecialAim-list-actual-callback-Reader',cap['referenceReaderMethodDefinition'],
        witness['referenceSource']['valueContext']['readerMethodDefinition'])
    need('SpecialAim-list-literal-parent-identity',True,type(usage['methodSpec'][0])is int and usage['methodSpec'][0]>0
        and type(witness.get('callTargetRva'))is int and witness['callTargetRva']>0)
    return dict(elementType=TYPE,elementValueType=False,closedListType=nominal,elementCapability=CAPABILITY,
        collectionCounts=[-1,0],countLimit=counts[1],positiveCountsAdmitted=True,nullable=True,elementGrammarAdmitted=True,
        packableReaderMethodDefinition=usage['methodSpec'][0],packableReaderTargetRva=witness['callTargetRva'],
        callbackSelectionConditional=True,wholeOwnerAdmitted=False)


def _derive_on_union(image,pins,union,*,typed_request,call_target,count_limit=10000):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.reference_list_induction_sources import derive as source
    from scripts.game_data.memorypack.skill_action_reference_list_sources import bind_parent_request,bind_reference_reader
    _publication_gate(image,pins)
    collection=source(image,pins,typed_request=typed_request,call_target=call_target,element_type=TYPE,count_limit=count_limit)
    parent=bind_parent_request(collection,typed_request,call_target,image.pe.image_base,label='SpecialAim-list')
    reader=bind_reference_reader(image,pins,collection,union,element_capability=CAPABILITY,label='SpecialAim-list')
    cap=compose(collection,union,pins);caps=dict(union['capabilities']);caps[LIST]=cap
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-special-aim-list-sources.v1',status='validated-conditional-special-aim-list',
        nativeInputs=pins,capabilities=caps,requiredExternalCapabilities=[CAPABILITY],
        proof=dict(collection=collection,child=union,actualParentRequestBinding=parent,listElementReadValueBinding=reader),
        parentFieldAdmitted=False,wholeOwnerAdmitted=False,evidenceBoundary=dict(
            exact='Actual closed list request/E8 and independent signed count/callback/Add induction, complete finite abstract-base union and every concrete sector factory/field/ordinary Double join.',
            conditional=__doc__,structuralOnly='Stored aim-shape edit collection.',
            unresolved=['actual enclosing action/union/root/EOF','runtime provider selection','nonempty reuse/growth/refill']))))


def derive(image,pins,*,typed_request,call_target,count_limit=10000):
    from scripts.game_data.memorypack.skill_special_aim_components import derive as child
    return _derive_on_union(image,pins,child(image,pins),typed_request=typed_request,call_target=call_target,count_limit=count_limit)
