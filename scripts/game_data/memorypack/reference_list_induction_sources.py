"""Bounded induction for the independently authenticated reference-list source.

The nominal parent transfer and concrete element grammar remain the caller's
obligations. This composes strict zero/one/two/three-iteration byte programs,
both fresh and reused-empty lists, with the same actual closed contexts and
capacity/Clear/provider/adapter proofs. No reference stride becomes wire width.
"""
from scripts.game_data.memorypack.counted_loop_sources import prove_induction


def _certificate(component,*,count_limit):
    """Pure loop declaration; only derive re-proves its native component."""
    if type(count_limit)is not int or not 3<=count_limit<=10000:
        raise ValueError('referenceListInduction.count-domain')
    if (component.get('status')!='validated-conditional-reference-list-component'
            or component.get('countLimit')!=3 or component.get('elementGrammarAdmitted')is not False
            or component.get('parentFieldAdmitted')is not False or component.get('wholeOwnerAdmitted')is not False):
        raise ValueError('referenceListInduction.component-scope')
    proof=prove_induction(component['programs'],initial='33f6',increment='ffc6',comparison='3b742468',
        counter='esi',saved_count='rsp+104',max_count=count_limit)
    return dict(elementType=component['elementType'],
        witnessComponent=component,induction=proof,nullable=True,countRange=[-1,count_limit],
        freshListsAdmitted=True,reusedListsRequireInitialCount=0,reusedListsRequireCapacityAtLeastCount=True,
        elementGrammarAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        evidenceBoundary=__doc__+' Matching ready typed contexts/canonical callbacks, zeroed fresh allocations '+
        'or reused-empty lists with spare capacity, normal Win64 helper effects, disabled collectors and '+
        'valid disjoint source/output/frame storage are explicit conditions; growth/refill/live selection stays unobserved.')


def derive(image,pins,*,typed_request,call_target,element_type,count_limit=10000):
    """Fresh same-image native/source component; no cached component admission."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.skill_shared_sequence_sources import selected_inputs
    from scripts.game_data.memorypack.skill_cost_data_list_sources import derive_reference_list_component
    selected_inputs(pins)
    if type(count_limit)is not int or not 3<=count_limit<=10000:
        raise ValueError('referenceListInduction.count-domain')
    _publication_gate(image,pins)
    component=derive_reference_list_component(image,pins,typed_request=typed_request,call_target=call_target,
        element_type=element_type,count_limit=3)
    result=_certificate(component,count_limit=count_limit)
    _publication_gate(image,pins)
    return dict(status='validated-bounded-reference-list-induction',nativeInputs=dict(pins),**result)
