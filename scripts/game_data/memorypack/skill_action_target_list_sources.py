"""Closed List<TargetSettings> parent source and independently strong EC child.

The actual ReadPackable MethodSpec/E8 selects the nominal reference list;
fresh and reused-empty/spare-capacity loops admit signed -1/0 and bounded
positive counts. Every selected Target element retains its own complete
ordinary reference/custom wire owner. Matching normal callbacks, initialized
coherent contexts, compatible allocation/collector/helper effects and stable
disjoint buffered storage remain conditions. No parent action, runtime target
selection, nonempty reused/growth/refill path or enclosing EOF is admitted.
"""
import json

from scripts.game_data.memorypack.skill_root_child_bindings import need

TYPE='Beyond.Gameplay.Core.TargetSettings'
LIST='System.Collections.Generic.List`1<'+TYPE+'>'
CAPABILITY='skill-action-target-settings-list'


def compose(collection,target,pins):
    """Pure exact nominal/count/element join; native derive owns both sources."""
    from scripts.game_data.memorypack.skill_action_reference_list_sources import compose_reference_list
    return compose_reference_list(collection,target,pins,element_type=TYPE,element_capability='target-profile',label='target-list')


def _derive_on_target(image,pins,target,*,typed_request,call_target,count_limit=10000):
    """Operation-local join; caller freshly derives the EC child on this image.

    Public derive always obtains that source itself. This internal composition
    still freshly authenticates the actual list body, nominal contexts and
    bounded count induction, and makes no enclosing-owner admission.
    """
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.reference_list_induction_sources import derive as list_source
    _publication_gate(image,pins)
    collection=list_source(image,pins,typed_request=typed_request,call_target=call_target,element_type=TYPE,count_limit=count_limit)
    from scripts.game_data.memorypack.skill_action_reference_list_sources import bind_reference_reader,bind_parent_request
    parent=bind_parent_request(collection,typed_request,call_target,image.pe.image_base,label='target-list')
    binding=bind_reference_reader(image,pins,collection,target,element_capability='target-profile',label='target-list')
    cap=compose(collection,target,pins)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-action-target-list-sources.v1',status='validated-conditional-target-settings-list',
        nativeInputs=pins,capabilities={CAPABILITY:cap,'target-profile':target['capabilities']['target-profile']},
        requiredExternalCapabilities=['target-profile'],proof=dict(collection=collection,target=target,
            actualParentRequestBinding=parent,listElementReadValueBinding=binding),
        parentFieldAdmitted=False,wholeOwnerAdmitted=False,evidenceBoundary=dict(
            exact='Actual closed ReadPackable list source/count/callback/Add programs and bounded induction, independently complete TargetSettings ordinary ABI and finite EC grammar.',
            conditional=__doc__,structuralOnly='Stored target-setting collection.',
            unresolved=['actual enclosing action field/union','runtime provider/target/callback choice','nonempty reused/growth/refill paths','enclosing owner/physical EOF']))))


def derive(image,pins,*,typed_request,call_target,count_limit=10000):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.skill_ec_components import derive as target_source
    _publication_gate(image,pins)
    return _derive_on_target(image,pins,target_source(image,pins),typed_request=typed_request,call_target=call_target,count_limit=count_limit)
