"""Exact List<KeywordEnhanceEdit>, independently of any enclosing action.

The actual closed ReadPackable MethodInfo and E8 select the separately proved
reference-list count/constructor/callback/Add and bounded induction programs.
Its ordinary element ReadValue definition and actual Reader target join the
fresh nominal KeywordEnhanceEdit source, concrete construction/getter and
canonical adapter. The MC3 child owns its pooled-string list, enum32 and
BlackboardDouble; reference stride8 supplies none of their wire widths.
Ready compatible closed contexts, normal callbacks/helpers, zeroed fresh or
initially empty reused lists with enough capacity, disabled collector and
disjoint storage remain conditions. Nonempty reuse/growth/refill, runtime
selection, the enclosing action/union and physical EOF remain unresolved.
"""
import json

from scripts.game_data.memorypack.skill_root_child_bindings import need
from scripts.game_data.memorypack.skill_action_reference_list_sources import (
    compose_reference_list,bind_reference_reader,bind_parent_request,
)

TYPE='Beyond.Gameplay.Core.KeywordEnhanceEdit'
CAPABILITY='skill-action-keyword-edit-list'
ELEMENT_CAPABILITY='skill-keyword-enhance-edit'
SCHEMA='endfield.skill-keyword-edit-list-sources.v1'


def _derive_on_child(image,pins,child,*,typed_request,call_target,count_limit=10000):
    """Internal reuse of one freshly derived ordinary child on this image."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.reference_list_induction_sources import derive as list_source
    _publication_gate(image,pins)
    nominal='System.Collections.Generic.List`1<'+TYPE+'>'
    need('keyword-list-finite-nominal',[nominal],typed_request.get('methodArguments'))
    collection=list_source(image,pins,typed_request=typed_request,call_target=call_target,element_type=TYPE,count_limit=count_limit)
    parent=bind_parent_request(collection,typed_request,call_target,image.pe.image_base,label='keyword-edit-list')
    reader=bind_reference_reader(image,pins,collection,child,element_capability=ELEMENT_CAPABILITY,label='keyword-edit-list')
    cap=compose_reference_list(collection,child,pins,element_type=TYPE,element_capability=ELEMENT_CAPABILITY,label='keyword-edit-list')
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-keyword-edit-list',nativeInputs=pins,
        capabilities={CAPABILITY:cap,ELEMENT_CAPABILITY:child['capabilities'][ELEMENT_CAPABILITY]},
        requiredExternalCapabilities=[ELEMENT_CAPABILITY],proof=dict(collection=collection,child=child,
            actualParentRequestBinding=parent,listElementReadValueBinding=reader),parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Own exact closed nominal list/source request, selected signed count/callback/Add and bounded induction; independently joined ordinary Keyword element Reader and complete child grammar.',
            conditional=__doc__,structuralOnly='Stored authored enhancement configuration.',
            unresolved=['actual enclosing field/output/cursor and action union','nonempty existing Clear/growth/refill','runtime callback/provider selection','whole owner/physical EOF']))))


def derive(image,pins,*,typed_request,call_target,count_limit=10000):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.skill_action_setting_sources import derive as child_source
    _publication_gate(image,pins)
    child=child_source(image,pins,type_names=[TYPE])
    return _derive_on_child(image,pins,child,typed_request=typed_request,call_target=call_target,count_limit=count_limit)
