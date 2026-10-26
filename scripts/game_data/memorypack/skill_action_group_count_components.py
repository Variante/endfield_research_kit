"""Actual current ActionGroup list parents and bounded list-count induction.

Each named parent retains its current typed request/E8/field transfer. Fresh
and reused-empty list loops own their unchanged signed counter and callback
ABI; element grammars remain independent selected-operation capabilities.
Neither reference stride nor a larger count supplies a Timeline/action body.
"""
import json

from scripts.game_data.memorypack.skill_root_child_bindings import need

FIELDS={
    'passiveEventActions':('Beyond.Gameplay.Core.AbilityActionMap','passive'),
    'timelineActions':('Beyond.Gameplay.Core.TimelineAction+TimelineActionData','timeline'),
}


def bind(pins,transfer,source,induction):
    need('known-group-list-parent',True,transfer.get('memberName')in FIELDS)
    need('same-group-list-native-inputs',pins,source['nativeInputs'])
    need('same-group-induction-native-inputs',pins,induction['nativeInputs'])
    typename,prefix=FIELDS[transfer['memberName']];usage=transfer['usage'];witness=induction['witnessComponent']
    need('same-group-induction-witness-inputs',pins,witness['nativeInputs'])
    need('actual-group-list-type',typename,source['elementType'])
    need('same-group-induction-element',typename,induction['elementType'])
    need('same-group-owned-usage',usage,source['typedRequest'])
    need('same-group-fresh-induction-usage',usage,witness['typedRequest'])
    need('actual-group-list-method',('MemoryPack.MemoryPackReader','ReadPackable',[],['System.Collections.Generic.List`1<'+typename+'>']),
        tuple(usage.get(k)for k in('typeName','methodName','classArguments','methodArguments')))
    at,encoded=transfer['sourceCall'];raw=bytes.fromhex(encoded)
    need('actual-group-list-E8',True,type(at)is int and len(raw)==5 and raw[0]==232
        and at+5+int.from_bytes(raw[1:],'little',signed=True)==source['callTargetRva']==witness['callTargetRva'])
    need('complete-group-list-induction',True,induction.get('status')=='validated-bounded-reference-list-induction'
        and induction.get('countRange')==[-1,10000]and all(type(n)is int for n in induction['countRange'])
        and all(induction.get(k)is False for k in('elementGrammarAdmitted','parentFieldAdmitted','wholeOwnerAdmitted'))
        and induction.get('freshListsAdmitted')is True and type(induction.get('reusedListsRequireInitialCount'))is int
        and induction['reusedListsRequireInitialCount']==0 and induction.get('reusedListsRequireCapacityAtLeastCount')is True)
    return {prefix+'Counts':[-1,0],prefix+'PositiveCountsAdmitted':True,prefix+'CountLimit':10000,
        prefix+'ListCountInductionProved':True}


def _derive_with_parent(image,pins,parent):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.reference_list_induction_sources import derive as derive_induction
    _publication_gate(image,pins)
    need('exact-group-parent-scope',True,parent.get('wrappedType')=='Beyond.Gameplay.Core.ActionGroupData'
        and type(parent.get('memberCount'))is int and parent['memberCount']==2
        and parent.get('wholeActionGroupAdmitted')is False and parent.get('childGrammarAdmitted')is False
        and set(parent.get('lists',{}))==set(FIELDS)
        and [r.get('memberName')for r in parent.get('orderedTransfers',[])]==list(FIELDS))
    bounds={};proofs={}
    for transfer in parent['orderedTransfers']:
        name=transfer['memberName'];source=parent['lists'][name]
        induction=derive_induction(image,pins,typed_request=transfer['usage'],call_target=image.pe.image_base+source['callTargetRva'],
            element_type=FIELDS[name][0],count_limit=10000)
        bounds.update(bind(pins,transfer,source,induction));proofs[name]=induction
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-action-group-count-components.v1',nativeInputs=pins,
        status='validated-conditional-action-group-list-counts',bounds=bounds,proof=dict(parent=parent,lists=proofs),
        elementGrammarsAdmitted=False,wholeActionGroupAdmitted=False,wholeSkillDataAdmitted=False,
        evidenceBoundary=__doc__+' Matching ready canonical callbacks/initialized contexts, normal child Win64/frame/helper effects, disabled collector and buffered disjoint storage remain explicit conditions.')))


def derive(image,pins):
    from scripts.game_data.memorypack.skill_shared_sequence_sources import derive_action_group
    return _derive_with_parent(image,pins,derive_action_group(image,pins))
