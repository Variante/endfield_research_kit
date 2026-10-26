"""Actual DamageUnit reference-list parents, induction and concrete elements.

Reference stride never supplies element wire grammar. CostData and the complete
DamageProcessor union independently own their actual ordinary ReadValue source.
Each actual DamageUnit field joins its closed ReadPackable type and call target
to fresh list/count/context/callback programs. No list closes DamageUnit itself.
"""
import json

from scripts.game_data.memorypack.skill_root_child_bindings import need

ELEMENTS={
    'costDataList':('Beyond.Gameplay.Core.CastData+CostData','skill-root-cost-data','damage-cost-data-list'),
    'damageProcessors':('Beyond.Gameplay.Core.DamageProcessorBase','damage-processor-union','damage-processor-list'),
}


def bind_list(pins,join,listing,child,*,capability):
    need('same-damage-list-native-inputs',pins,listing['nativeInputs'])
    typename=child['typeName'];closed='System.Collections.Generic.List`1<'+typename+'>'
    need('exact-damage-list-element',typename,listing['elementType'])
    need('actual-damage-list-field-type',closed,join['typeName'])
    usage=join['typedRequest'];need('actual-damage-list-request',('MemoryPack.MemoryPackReader','ReadPackable',[],[closed]),
        tuple(usage.get(key)for key in('typeName','methodName','classArguments','methodArguments')))
    witness=listing['witnessComponent']
    need('same-list-witness-native-inputs',pins,witness['nativeInputs'])
    need('same-actual-damage-list-usage',usage,witness['typedRequest'])
    need('actual-damage-list-method',witness['typedRequest']['methodSpec'][0],usage['methodSpec'][0])
    need('actual-damage-list-call',witness['callTargetRva'],join['sourceTargetRva'])
    need('complete-bounded-damage-list-scope',True,listing.get('status')=='validated-bounded-reference-list-induction'
        and listing.get('countRange')==[-1,10000]and all(type(v)is int for v in listing['countRange'])
        and all(listing.get(key)is False for key in('elementGrammarAdmitted','parentFieldAdmitted','wholeOwnerAdmitted'))
        and listing.get('freshListsAdmitted')is True and type(listing.get('reusedListsRequireInitialCount'))is int
        and listing['reusedListsRequireInitialCount']==0
        and listing.get('reusedListsRequireCapacityAtLeastCount')is True)
    need('whole-ordinary-damage-list-element',True,child.get('wholeGrammarAdmitted')is True
        and child.get('ordinaryOriginalReadValueAdmitted',True)is True)
    need('literal-damage-element-reference-identity',True,
        type(child.get('referenceReaderMethodDefinition'))is int and type(child.get('referenceReaderTargetRva'))is int)
    need('same-damage-element-reference-method',child['referenceReaderMethodDefinition'],
        witness['referenceSource']['valueContext']['readerMethodDefinition'])
    need('same-damage-element-reference-target',child['referenceReaderTargetRva'],listing['referenceReaderTargetRva'])
    return dict(elementType=typename,closedListType=closed,elementValueType=False,elementCapability=capability,
        collectionCounts=[-1,0],nullable=True,countLimit=10000,positiveCountsAdmitted=True,elementGrammarAdmitted=True,
        packableReaderMethodDefinition=usage['methodSpec'][0],packableReaderTargetRva=join['sourceTargetRva'],
        referenceReaderMethodDefinition=child['referenceReaderMethodDefinition'],referenceReaderTargetRva=child['referenceReaderTargetRva'],
        wholeGrammarAdmitted=True,wholeDamageUnitAdmitted=False)


def derive(image,pins,*,fields=None):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack import skill_damage_unit_sources,skill_root_cast_components,skill_damage_union_components
    from scripts.game_data.memorypack import reference_list_induction_sources,buff_ec_profiles_native as ec
    selected=list(ELEMENTS)if fields is None else list(fields)
    need('finite-damage-reference-list-fields',True,bool(selected)and len(selected)==len(set(selected))and set(selected)<=set(ELEMENTS))
    _publication_gate(image,pins);parent=skill_damage_unit_sources.derive(image,pins)
    caps={};proofs={};children={};reader=ec.clone_facts(image,pins)['ReadValue']
    if 'costDataList'in selected:
        component=skill_root_cast_components.derive(image,pins)
        need('same-cost-component-native-inputs',pins,component['nativeInputs'])
        children['costDataList']=component['capabilities']['skill-root-cost-data'];proofs['costData']=component
    if 'damageProcessors'in selected:
        component=skill_damage_union_components.derive(image,pins)
        need('same-processor-component-native-inputs',pins,component['nativeInputs'])
        children['damageProcessors']=component['families']['DamageProcessorBase'];proofs['unions']=component
    for name in selected:
        typename,capability,list_capability=ELEMENTS[name]
        join,=[row for row in parent['requiredChildJoins']if row['fieldName']==name]
        listing=reference_list_induction_sources.derive(image,pins,typed_request=join['typedRequest'],
            call_target=image.pe.image_base+join['sourceTargetRva'],element_type=typename,count_limit=10000)
        listing=dict(listing,referenceReaderTargetRva=reader['targetRva'])
        caps[capability]=children[name];caps[list_capability]=bind_list(pins,join,listing,children[name],capability=capability)
        proofs[name]=listing
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-damage-list-components.v1',nativeInputs=pins,
        status='validated-conditional-damage-reference-lists',capabilities=caps,
        proof=dict(parent=parent,components=proofs,referenceReader=reader),wholeDamageUnitAdmitted=False,
        evidenceBoundary=dict(exact='Each actual named DamageUnit field closed type/MethodSpec/E8, fresh signed reference-list induction and independently complete concrete element source/ordinary adapter.',
            conditional=__doc__+' Matching initialized nominal callbacks/contexts and normal typed allocation/helper effects; fresh lists or reused-empty lists with capacity, disabled collector and buffered disjoint storage.',
            structuralOnly='Stored cost and processor lists.',unresolved=['other DamageUnit fields','runtime evaluation','whole owner/physical EOF']))))
