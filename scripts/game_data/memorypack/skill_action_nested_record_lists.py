"""Finite action-owned reference lists of independently proved nested records.

The actual ReadPackable<List<T>> request/E8 and selected count/callback/Add
loop are independent of the own ordinary record's canonical adapter, lifecycle,
Reader and wire fields. Eight-byte list references supply no serialized child
width. Fresh zeroed or initially empty reused lists with spare capacity,
matching normal callbacks/helpers, coherent selected contexts, disabled
collector and disjoint stable buffered storage remain conditions. Nonempty
reuse/growth/refill, live provider choice and enclosing action/root/EOF remain
unresolved. This source owner supplies no parser or native admission by itself.
"""
import json

from scripts.game_data.memorypack.skill_root_child_bindings import need
from scripts.game_data.memorypack.skill_action_reference_list_sources import compose_reference_list,bind_parent_request,bind_reference_reader

TYPES={
 'Beyond.Gameplay.Core.Selector+HitBoxFinder+ShapeData':('skill-selector-hitbox-shape-list','skill-selector-hitbox-shape'),
 'Beyond.Gameplay.Core.LaunchProjectile+PresetPointDef':('skill-action-projectile-preset-point-list','skill-action-projectile-preset-point'),
 'Beyond.Gameplay.Core.ComboCacheAction+Data+BattleCmdMappingModifierData':('skill-action-battle-command-mapping-list','skill-action-battle-command-mapping-modifier'),
 'Beyond.Gameplay.Core.OverrideRawAttributeAction+AttributeOverrideEntry':('skill-action-attribute-override-list','skill-action-attribute-override-entry'),
 'Beyond.Gameplay.Core.ReadSkillSettingData+ReadData':('skill-action-read-skill-setting-list','skill-action-read-skill-setting'),
 'Beyond.Gameplay.Core.SwitchAction+Option':('skill-action-switch-option-list','skill-action-switch-option'),
}


def selection(typed_request):
    names=[name for name in TYPES if typed_request.get('methodArguments')==['System.Collections.Generic.List`1<'+name+'>']]
    need('nested-list-finite-closed-element',1,len(names));return names[0]


def _derive_on_child(image,pins,child,*,typed_request,call_target,count_limit=10000):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.reference_list_induction_sources import derive as list_source
    _publication_gate(image,pins);name=selection(typed_request);capability,element=TYPES[name]
    listing=list_source(image,pins,typed_request=typed_request,call_target=call_target,element_type=name,count_limit=count_limit)
    parent=bind_parent_request(listing,typed_request,call_target,image.pe.image_base,label='nested-action-list')
    reader=bind_reference_reader(image,pins,listing,child,element_capability=element,label='nested-action-list')
    cap=compose_reference_list(listing,child,pins,element_type=name,element_capability=element,label='nested-action-list')
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-action-nested-record-list.v1',status='validated-conditional-action-nested-record-list',
        nativeInputs=pins,capabilities={capability:cap,element:child['capabilities'][element]},requiredExternalCapabilities=[element],
        proof=dict(collection=listing,child=child,actualParentRequestBinding=parent,listElementReadValueBinding=reader),parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Actual finite nominal closed list request/E8, independently selected signed count/callback/Add/induction and complete ordinary nominal record source/Reader.',
            conditional=__doc__,structuralOnly='Stored action settings collection.',unresolved=['enclosing action/union/root/EOF','live callback/provider selection','nonempty reused/growth/refill']))))


def derive(image,pins,*,typed_request,call_target,count_limit=10000):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.skill_action_nested_record_sources import derive as child_source
    _publication_gate(image,pins);name=selection(typed_request)
    return _derive_on_child(image,pins,child_source(image,pins,type_names=[name]),
        typed_request=typed_request,call_target=call_target,count_limit=count_limit)
