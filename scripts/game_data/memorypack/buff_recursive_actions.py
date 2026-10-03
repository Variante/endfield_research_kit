"""Reusable recursive action composition using reviewed typed child joins.

The caller must independently prove its parent map/sequence typed join. Positive
target recursion, selectors with unsupported processors/validators, inherited skill lists,
and unresolved EffectActionCfg terrain-effect arrays still refuse the action.
"""
from __future__ import annotations
import struct
from typing import Any
from scripts.game_data.memorypack import (
    buff_blackboard_double_child_receipt as blackboard,
    buff_create_buff_action_receipt as create,
    buff_create_icon_duration_child_receipt as icon_duration,
    buff_create_input_child_receipt as create_input,
    buff_direction_settings_child_receipt as direction,
    buff_selector_data_child_receipt as selector,
    buff_selector_finder_character_team as character_team,
    buff_target_settings_child_receipt as target,
    buff_effect_action_receipt as effect,
    buff_effect_vector_child_receipt as vector,
    buff_set_super_armor_action_receipt as armor,
    buff_super_armor_blackboard_child_receipt as armor_values,
    buff_finish_buff_advanced_action_receipt as finish,
    buff_find_settings_child_receipt as find,
    buff_direct_target_actions as direct_target_actions,
    buff_selector_finder_owner_spawned as owner_spawned,
)

from scripts.game_data.memorypack import buff_selector_shared_children as selector_children
from scripts.game_data.memorypack import buff_recursive_control_actions as control
from scripts.game_data.memorypack import buff_selector_geometry as geometry
from scripts.game_data.memorypack import buff_find_target_action as find_target
from scripts.game_data.memorypack.buff_actions import SEQUENCE_RECURSION_LIMIT

LABEL = "buffRecursiveActions"
SUPPORTED_TAGS = frozenset((create.TAG, effect.TAG, armor.TAG, finish.TAG)) | direct_target_actions.supported_tags() | control.SUPPORTED_TAGS | find_target.supported_tags()

def validate_current_native_contract() -> dict[str, Any]:
    children = {"create": create.validate_current_native_contract(),
                "iconDuration": icon_duration.validate_current_native_contract(),
                "createInput": create_input.validate_current_native_contract(),
                "blackboard": blackboard.validate_current_native_contract(),
                "target": target.validate_current_native_contract(),
                "effect": effect.validate_current_native_contract(),
                "effectVectors": vector.validate_current_native_contract()}
    children["direction"] = direction.validate_current_native_contract(target_native=children["target"])
    children["selector"] = selector.validate_current_native_contract(target_native=children["target"])
    children["characterTeamFinder"] = character_team.validate_current_native_contract(selector_native=children["selector"])
    children["finish"] = children["target"]["parentNative"][finish.TAG]
    children["findSettings"] = find.validate_current_native_contract()
    children["armorValues"] = armor_values.validate_current_native_contract()
    children["armor"] = children["armorValues"]["parentNative"]
    children["directTargetActions"] = direct_target_actions.validate_current_native_contract()
    children["ownerSpawnedFinder"] = owner_spawned.validate_current_native_contract(selector_native=children["selector"])
    children["zeroValidators"] = selector_children.zero_owner.validate_current_native_contract(selector_native=children["selector"])
    children["tagQueryValidator"] = selector_children.tag_owner.validate_current_native_contract(selector_native=children["selector"])
    selector_children.query_parent_binding(children["tagQueryValidator"], children["findSettings"])
    children["ifElse"] = control.conditional.validate_current_native_contract()
    children["compare"] = control.compare.validate_current_native_contract()
    children["modify"] = children["blackboard"]["parentNative"][control.modify.TAG]
    children["checkStack"] = control.stack.validate_current_native_contract()
    children["buffIdActions"] = control.ids.validate_current_native_contract()
    children["blackboardString"] = control.strings.child.validate_current_native_contract()
    children["selectorGeometry"] = geometry.validate_current_native_contract(
        selector_native=children["selector"], vector_native=children["effectVectors"])
    armor_target_binding(children["armor"], children["target"])
    finish_settings_binding(children["finish"], children["findSettings"])
    expected = children["create"]["nativeInputs"]
    for name, child in children.items():
        if (child.get("status") != "validated"
                or any(child.get("nativeInputs", {}).get(key) != expected.get(key)
                       for key in ("GameAssembly.dll", "global-metadata.dat"))):
            raise ValueError(f"{LABEL}.native:{name}-unvalidated-or-build-drift")
    return {"status": "validated", "nativeInputs": expected, "children": children}

def decode_create_action(
    data: bytes, source: str, digest: str, start: int, end: int,
    native: dict[str, Any],
) -> dict[str, Any]:
    children = native["children"]
    parent = create.decode_create_buff_action_receipt(
        data, source=source, logical_sha256=digest, start=start, end=end,
        native_validation=children["create"],
    )
    if (parent.get("wholeActionByteSpanExact") is not True
            or [field["fieldName"] for field in parent["namedFields"]]
            != ["isEnable", "priorityLevel", "priorityOffset", "serverActionIndex",
                "asChildBuff", "autoFinishByAction", "buffIconDurationSource",
                "buffs", "buffSource", "contextKey", "count",
                "finishWithNextSkillIfNotInherited", "inheritSkillIdList",
                "inheritSourceSkillCastId", "inheritSourceSkillCastInfo", "isExtra",
                "overrideBuffIconDuration", "passTargetGroupsToBuff", "targetSettings"]):
        raise ValueError(f"{LABEL}.action:parent-field-order")
    fields = {field["fieldName"]: field for field in parent["namedFields"]}
    icon_field = fields["buffIconDurationSource"]
    icon = icon_duration.decode_icon_duration_child(
        data, source=source, logical_sha256=digest,
        start=icon_field["start"], end=icon_field["end"],
        native_validation=children["iconDuration"],
    )
    input_field = fields["buffs"]
    inputs = create_input.decode_create_buff_input_list(
        data, source=source, logical_sha256=digest,
        start=input_field["start"], end=input_field["end"],
        native_validation=children["createInput"],
    )
    if (inputs.get("wholeStoredSpanExact") is not True
            or inputs.get("namedDirectMembersExact") is not True
            or inputs.get("start") != input_field["start"]
            or inputs.get("end") != input_field["end"]
            or len(inputs.get("inputs") or []) != max(0, inputs["count"])
            or any(item.get("status") not in ("named-five-member-exact-span", "exact-null-wrapper")
                   for item in inputs.get("inputs") or [])):
        raise ValueError(f"{LABEL}.action:input-list-not-exact")
    if (fields["inheritSkillIdList"]["end"] - fields["inheritSkillIdList"]["start"] != 4
            or struct.unpack_from("<i", data, fields["inheritSkillIdList"]["start"])[0] != 0):
        raise ValueError(f"{LABEL}.action:inherit-list-not-empty")
    blackboard_child = blackboard.decode_blackboard_double_action_child_receipt(
        data, source=source, logical_sha256=digest, start=start, end=end,
        tag=create.TAG, native_validation=children["blackboard"],
    )
    target_child = target.decode_target_settings_action_child_receipt(
        data, source=source, logical_sha256=digest, start=start, end=end,
        tag=create.TAG, native_validation=children["target"],
    )
    direction_child = direction.decode_direction_settings_action_child_receipt(
        data, source=source, logical_sha256=digest, start=start, end=end,
        tag=create.TAG, native_validation=children["direction"],
    )
    selector_child = selector.decode_selector_data_action_child_receipt(
        data, source=source, logical_sha256=digest, start=start, end=end,
        tag=create.TAG, native_validation=children["selector"],
    )
    if (blackboard_child.get("parentField") != "count"
            or blackboard_child.get("wholeProviderByteSpanExact") is not True
            or len(target_child.get("targetChildren") or []) != 1
            or len(direction_child.get("directionChildren") or []) != 1
            or len(selector_child.get("selectorChildren") or []) != 1):
        raise ValueError(f"{LABEL}.action:shared-child-cardinality")
    target_row = target_child["targetChildren"][0]
    direction_row = direction_child["directionChildren"][0]
    selector_row = selector_child["selectorChildren"][0]
    if (target_row.get("start") != fields["targetSettings"]["start"]
            or target_row.get("end") != fields["targetSettings"]["end"]
            or target_row.get("status") != "named-direct-members-exact-span"
            or direction_row.get("status") != "named-direct-members-exact-span"
            or selector_row.get("status") != "named-direct-members-exact-span"):
        raise ValueError(f"{LABEL}.action:target-child-span")
    target_members = {member["fieldName"]: member
                      for member in target_row["namedMembers"]}
    if (len(target_members) != 13
            or [direction_row["start"], direction_row["end"]]
            != [target_members["advancedDirection"]["start"],
                target_members["advancedDirection"]["end"]]
            or [selector_row["start"], selector_row["end"]]
            != [target_members["selectorData"]["start"],
                target_members["selectorData"]["end"]]
            or any(member.get("nestedTargetStatus") != "exact-null"
                   for member in direction_row["namedMembers"]
                   if member.get("kind") == "object")):
        raise ValueError(f"{LABEL}.action:direction-or-selector-join")
    selector_members = selector_row["namedMembers"]
    if ([row["fieldName"] for row in selector_members]
            != ["finderData", "postProcessorData", "validatorData"]
            or selector_members[1].get("count") != 0):
        raise ValueError(f"{LABEL}.action:selector-collections-not-empty")
    validators = selector_members[2]
    validator_receipt = {}
    if validators.get('count') != 0:
        validator_receipt['validators'] = selector_children.decode_validator_list(data, source=source, digest=digest,
            start=validators['start'],end=validators['end'],children=children)
    finder = selector_members[0]
    finder_child = None
    if finder.get("unionTag") is None:
        if finder["end"] - finder["start"] != 1 or data[finder["start"]] != 0xFF:
            raise ValueError(f"{LABEL}.action:finder-not-null")
    elif finder.get("unionTag") == character_team.TAG:
        finder_child = character_team.decode_character_team_finder_span(
            data, source=source, logical_sha256=digest,
            start=finder["start"], end=finder["end"],
            native_validation=children["characterTeamFinder"],
        )
        if finder_child.get("status") != "named-zero-member-finder-exact-span":
            raise ValueError(f"{LABEL}.action:finder-child")
    elif finder.get("unionTag") == owner_spawned.TAG:
        finder_child = owner_spawned.decode_owner_spawned_finder_span(
            data, source=source, logical_sha256=digest, start=finder["start"], end=finder["end"],
            native_validation=children["ownerSpawnedFinder"])
    elif finder.get("unionTag") in geometry.finder_tags():
        finder_child = geometry.decode_finder(data, source=source, digest=digest, start=finder["start"], end=finder["end"], context=children)
    else:
        raise ValueError(f"{LABEL}.action:unsupported-finder={finder.get('unionTag')}")
    return {"parent": parent, "iconDuration": icon, "inputList": inputs,
            "blackboard": blackboard_child, "target": target_child,
            "direction": direction_child, "selector": selector_child,
            "finder": finder_child, "recursiveStoredSchemaExact": True, **validator_receipt}


def decode_effect_action(data: bytes, source: str, digest: str, start: int, end: int,
                         native: dict[str, Any]) -> dict[str, Any]:
    """Compose every reached EffectActionCfg and target child on exact joins."""
    children = native["children"]
    kw = dict(source=source, logical_sha256=digest, start=start, end=end)
    parent = effect.decode_effect_action_receipt(data, **kw, native_validation=children["effect"])
    if parent.get("wholeActionByteSpanExact") is not True:
        raise ValueError(f"{LABEL}.effect:parent-incomplete")
    fields = {row["fieldName"]: row for row in parent["namedFields"]}
    expected_targets = {name for name, row in fields.items() if row["kind"] == "target-profile"}
    vectors = vector.decode_effect_vector_child_receipt(
        data, **kw, native_validation=children["effectVectors"], action_native=children["effect"])
    targets = target.decode_target_settings_action_child_receipt(
        data, **kw, tag=effect.TAG, native_validation=children["target"])
    directions = direction.decode_direction_settings_action_child_receipt(
        data, **kw, tag=effect.TAG, native_validation=children["direction"])
    selectors = selector.decode_selector_data_action_child_receipt(
        data, **kw, tag=effect.TAG, native_validation=children["selector"])
    if (vectors.get("wholeConfigBlackboardChildrenExact") is not True
            or {row.get("parentField") for row in targets.get("targetChildren") or []} != expected_targets
            or len(targets.get("targetChildren") or []) != len(expected_targets)
            or len(directions.get("directionChildren") or []) != len(expected_targets)
            or len(selectors.get("selectorChildren") or []) != len(expected_targets)):
        raise ValueError(f"{LABEL}.effect:child-cardinality")
    finders = []
    validator_receipts = []
    for target_row in targets["targetChildren"]:
        parent_field = fields.get(target_row.get("parentField")) or {}
        if (target_row.get("status") != "named-direct-members-exact-span"
                or [target_row["start"], target_row["end"]]
                != [parent_field.get("start"), parent_field.get("end")]):
            raise ValueError(f"{LABEL}.effect:target-parent-join")
        members = {row["fieldName"]: row for row in target_row["namedMembers"]}
        ds = [row for row in directions["directionChildren"]
              if row.get("targetParentField") == target_row["parentField"]]
        ss = [row for row in selectors["selectorChildren"]
              if row.get("targetParentField") == target_row["parentField"]]
        if len(members) != 13 or len(ds) != 1 or len(ss) != 1:
            raise ValueError(f"{LABEL}.effect:target-child-join-cardinality")
        direction_row, selector_row = ds[0], ss[0]
        if (direction_row.get("status") != "named-direct-members-exact-span"
                or selector_row.get("status") != "named-direct-members-exact-span"
                or [direction_row["start"], direction_row["end"]]
                != [members["advancedDirection"]["start"], members["advancedDirection"]["end"]]
                or [selector_row["start"], selector_row["end"]]
                != [members["selectorData"]["start"], members["selectorData"]["end"]]
                or any(row.get("nestedTargetStatus") != "exact-null" for row in direction_row["namedMembers"]
                       if row.get("kind") == "object")):
            raise ValueError(f"{LABEL}.effect:direction-or-selector-join")
        parts = selector_row["namedMembers"]
        if ([row["fieldName"] for row in parts] != ["finderData", "postProcessorData", "validatorData"]
                or parts[1].get("count") != 0):
            raise ValueError(f"{LABEL}.effect:selector-collections-not-empty")
        if parts[2].get('count') != 0:
            validator_receipts.append(selector_children.decode_validator_list(data, source=source,digest=digest,
                start=parts[2]['start'],end=parts[2]['end'],children=children))
        finder = parts[0]
        if finder.get("unionTag") is None:
            if finder["end"] - finder["start"] != 1 or data[finder["start"]] != 0xFF:
                raise ValueError(f"{LABEL}.effect:finder-not-null")
        elif finder["unionTag"] == character_team.TAG:
            finders.append(character_team.decode_character_team_finder_span(
                data, source=source, logical_sha256=digest, start=finder["start"], end=finder["end"],
                native_validation=children["characterTeamFinder"]))
        elif finder["unionTag"] == owner_spawned.TAG:
            finders.append(owner_spawned.decode_owner_spawned_finder_span(
                data, source=source, logical_sha256=digest, start=finder["start"], end=finder["end"],
                native_validation=children["ownerSpawnedFinder"]))
        elif finder["unionTag"] in geometry.finder_tags():
            finders.append(geometry.decode_finder(data, source=source, digest=digest, start=finder["start"], end=finder["end"], context=children))
        else:
            raise ValueError(f"{LABEL}.effect:unsupported-finder={finder['unionTag']}")
    return {"parent": parent, "configVectors": vectors, "target": targets,
            "direction": directions, "selector": selectors, "finders": finders,
            "recursiveStoredSchemaExact": True, **({'validators':validator_receipts} if validator_receipts else {})}


def decode_action(data: bytes, *, source: str, digest: str, start: int, end: int,
                  tag: int, native_validation: dict[str, Any], depth: int = 0) -> dict[str, Any]:
    if depth > SEQUENCE_RECURSION_LIMIT:
        raise ValueError(f"{LABEL}.action:depth-limit")
    if native_validation.get("status") != "validated":
        raise ValueError(f"{LABEL}.native:unvalidated")
    decoders = {create.TAG: decode_create_action, effect.TAG: decode_effect_action,
                armor.TAG: decode_armor_action, finish.TAG: decode_finish_action}
    if tag in direct_target_actions.supported_tags():
        return decode_direct_target_action(data, source, digest, start, end, tag, native_validation)
    if tag in find_target.supported_tags():
        return find_target.decode_action(data, source=source, digest=digest, start=start, end=end, tag=tag, native_validation=native_validation)
    if tag not in decoders:
        return control.decode_action(data, source=source, digest=digest, start=start, end=end,
                                     tag=tag, native_validation=native_validation, depth=depth)
    result = decoders[tag](data, source, digest, start, end, native_validation)
    return {"schema": "endfield.buff-recursive-action-receipt.v1", "tag": tag,
            "start": start, "end": end, **result}



def armor_target_binding(parent_native, target_native):
    """Join the already validated last source context to the named parent slot.

    armor.validate_current_native_contract independently compares the generated
    member declared types against [priority, impact, armor, target] contexts.
    This caller additionally binds the last source read to the child reader.
    No new destination or provider identity is inferred from a byte fit.
    """
    source, catalog = armor._contracts()
    contexts = source['nestedContexts']
    names, kinds = parent_native.get('memberNames', []), parent_native.get('readKinds', [])
    expected_inputs = catalog['nativeInputs']
    if (parent_native.get('status') != 'validated' or target_native.get('status') != 'validated'
            or parent_native.get('unionTag') != armor.TAG or len(names) != 7
            or kinds != source['anonymousReadOrder']['member7']
            or kinds[-1] != 'target-profile' or names[-1] != 'targetSettings'
            or contexts[-1]['typeName'] != 'Beyond.Gameplay.Core.TargetSettings'
            or [c['typeName'] for c in contexts[1:3]]
                != ['Beyond.Gameplay.Core.BlackboardImpactValue', 'Beyond.Gameplay.Core.BlackboardSuperArmorValue']
            or any(parent_native.get('nativeInputs', {}).get(k) != target_native.get('nativeInputs', {}).get(k)
                   for k in ('GameAssembly.dll', 'global-metadata.dat'))
            or parent_native['nativeInputs']['GameAssembly.dll'] != expected_inputs['gameAssemblySha256']
            or parent_native['nativeInputs']['global-metadata.dat'] != expected_inputs['metadataSha256']):
        raise ValueError('buffRecursiveActions.armor:typed-parent-target-join')
    return {'fieldName': names[-1], 'kind': kinds[-1], 'parentFieldIndex': 6,
            'declaredType': contexts[-1]['typeName'], 'sourceContext': contexts[-1]}


def finish_settings_binding(parent_native, child_native):
    """Bind the reviewed B4 source contexts to all generated object setters."""
    contract = finish._contract(); source, _catalog = finish._dependencies()
    setters = contract['wrapper']['inheritedSetterMethods'] + contract['wrapper']['setterMethods']
    kinds = contract['orderedReadKinds']
    nested = [(index, setter, kind) for index, (setter, kind) in enumerate(zip(setters, kinds, strict=True))
              if kind in ('target-profile', 'finder-profile', 'scalar-payload')]
    contexts = source['nestedContexts'][:len(nested)]
    if (parent_native.get('status') != 'validated' or child_native.get('status') != 'validated'
            or parent_native.get('nativeInputs') != contract['nativeInputs']
            or child_native.get('nativeInputs') != contract['nativeInputs']
            or parent_native.get('unionTag') != finish.TAG
            or parent_native.get('memberCount') != len(setters)
            or len(contexts) != len(nested)
            or [row[1][-1] for row in nested] != [row['typeName'] for row in contexts]):
        raise ValueError('buffRecursiveActions.finish:typed-parent-context-join')
    joined = [(index, setter, kind, context) for (index, setter, kind), context in zip(nested, contexts)
              if setter[1] == 'set___buffSettings__']
    if (len(joined) != 1 or joined[0][2] != 'finder-profile'
            or joined[0][1][-1] != 'Beyond.Gameplay.Core.BuffFindSettings'):
        raise ValueError('buffRecursiveActions.finish:typed-parent-settings-join')
    index, _setter, kind, context = joined[0]
    return {'fieldName': 'buffSettings', 'parentFieldIndex': index, 'kind': kind,
            'declaredType': context['typeName'], 'sourceContext': context}


def target_value(data, source, digest, field, native):
    """Use the factored existing loop; the caller still owns its typed join."""
    value = target.decode_target_settings_value(data, source=source, logical_sha256=digest,
        start=field['start'], end=field['end'], native_validation=native)
    if value['status'] != 'named-direct-members-exact-span':
        raise ValueError('buffRecursiveActions.target:null-target-not-admitted')
    return value


def recursive_target(data, source, digest, field, context):
    target = target_value(data, source, digest, field, context['target'])
    fields = {m['fieldName']: m for m in target['namedMembers']}
    children = {}
    for name, module, key, decoder in (
        ('advancedDirection', direction, 'direction', direction.decode_direction_settings_value),
        ('selectorData', selector, 'selector', selector.decode_selector_data_value),
    ):
        span = fields[name]
        child = decoder(data, source=source, logical_sha256=digest, start=span['start'], end=span['end'],
                        native_validation=context[key])
        if child.get('status') != 'named-direct-members-exact-span':
            raise ValueError('buffRecursiveActions.target:child-status')
        children[name] = child
    if any(m.get('nestedTargetStatus') != 'exact-null'
           for m in children['advancedDirection']['namedMembers'] if m['kind'] == 'object'):
        raise ValueError('buffRecursiveActions.target:positive-direction-target')
    parts = children['selectorData']['namedMembers']
    if [m['fieldName'] for m in parts] != ['finderData', 'postProcessorData', 'validatorData']:
        raise ValueError('buffRecursiveActions.target:selector-members')
    if parts[1].get('count') != 0:
        raise ValueError('buffRecursiveActions.target:positive-selector-list')
    if parts[2].get('count') != 0:
        children['validators'] = selector_children.decode_validator_list(data, source=source,digest=digest,
            start=parts[2]['start'],end=parts[2]['end'],children=context)
    f = parts[0]
    if f.get('unionTag') is None:
        if data[f['start']:f['end']] != b'\xff':
            raise ValueError('buffRecursiveActions.target:null-finder')
    elif f['unionTag'] == character_team.TAG:
        children['finder'] = character_team.decode_character_team_finder_span(data, source=source,
            logical_sha256=digest, start=f['start'], end=f['end'], native_validation=context['characterTeamFinder'])
    elif f['unionTag'] == owner_spawned.TAG:
        children['finder'] = owner_spawned.decode_owner_spawned_finder_span(data, source=source,
            logical_sha256=digest, start=f['start'], end=f['end'], native_validation=context['ownerSpawnedFinder'])
    elif f["unionTag"] in geometry.finder_tags():
        children["finder"] = geometry.decode_finder(data, source=source, digest=digest, start=f["start"], end=f["end"], context=context)
    else:
        raise ValueError(f"buffRecursiveActions.target:unsupported-finder={f['unionTag']}")
    return {**target, **children, 'recursiveStoredSchemaExact': True}


def decode_armor_action(data, source, digest, start, end, native):
    context = native["children"]
    binding = armor_target_binding(context['armor'], context['target'])
    args = dict(source=source, logical_sha256=digest, start=start, end=end)
    parent = armor.decode_set_super_armor_action_receipt(data, **args, native_validation=context['armor'])
    values = armor_values.decode_super_armor_blackboard_children(data, **args,
                                                               native_validation=context['armorValues'])
    field = parent['namedFields'][binding['parentFieldIndex']]
    if (field['fieldName'] != binding['fieldName'] or field['kind'] != binding['kind']
            or len(values['children']) != 2):
        raise ValueError('buffRecursiveActions.armor:children')
    for child, index in zip(values['children'], (4, 5)):
        expected = parent['namedFields'][index]
        if (child['parentFieldName'] != expected['fieldName']
                or child['parentFieldRange'] != [expected['start'], expected['end']]
                or child.get('wholeProviderByteSpanExact') is not True):
            raise ValueError('buffRecursiveActions.armor:blackboard-parent-join')
    target = recursive_target(data, source, digest, field, context)
    return {'schema': 'endfield.buff-recursive-action-receipt.v1', 'tag': armor.TAG,
            'start': start, 'end': end, 'parent': parent, 'blackboardValues': values,
            'target': target, 'recursiveStoredSchemaExact': True}


def decode_finish_action(data, source, digest, start, end, native):
    context = native["children"]
    settings_binding = finish_settings_binding(context['finish'], context['findSettings'])
    args = dict(source=source, logical_sha256=digest, start=start, end=end)
    parent = finish.decode_finish_buff_advanced_action_receipt(data, **args, native_validation=context['finish'])
    scalar = blackboard.decode_blackboard_double_action_child_receipt(data, **args,
        tag=finish.TAG, native_validation=context['blackboard'])
    fields = {m['fieldName']: m for m in parent['namedFields']}
    setters = finish._contract()['wrapper']['setterMethods']
    target_names = [m[1].removeprefix('set___').removesuffix('__') for m in setters
                    if m[-1] == 'Beyond.Gameplay.Core.TargetSettings']
    if set(target_names) != {m['fieldName'] for m in parent['namedFields'] if m['kind'] == 'target-profile'}:
        raise ValueError('buffRecursiveActions.finish:target-parent-join')
    targets = {name: recursive_target(data, source, digest, fields[name], context) for name in target_names}
    settings_field = parent['namedFields'][settings_binding['parentFieldIndex']]
    if (settings_field['fieldName'] != settings_binding['fieldName']
            or settings_field['kind'] != settings_binding['kind']):
        raise ValueError('buffRecursiveActions.finish:settings-parent-field')
    settings = find.decode_find_settings_child_receipt(data, source=source, logical_sha256=digest,
        start=settings_field['start'], end=settings_field['end'], native_validation=context['findSettings'])
    if (settings.get('wholeChildSpanExact') is not True or scalar.get('wholeProviderByteSpanExact') is not True
            or scalar['parentFieldRange'] != [fields['finishLayerCnt']['start'], fields['finishLayerCnt']['end']]):
        raise ValueError('buffRecursiveActions.finish:settings-or-scalar-parent-join')
    return {'schema': 'endfield.buff-recursive-action-receipt.v1', 'tag': finish.TAG,
            'start': start, 'end': end, 'parent': parent, 'blackboard': scalar,
            'targets': targets, 'buffSettings': settings, 'recursiveStoredSchemaExact': True}



def decode_direct_target_action(data, source, digest, start, end, tag, native_validation):
    context = native_validation["children"]
    native = context['directTargetActions']['routes'][tag]
    if any(native['nativeInputs'][key] != context['target']['nativeInputs'][key]
           for key in ('GameAssembly.dll', 'global-metadata.dat')):
        raise ValueError('buffRecursiveActions.directTarget:native-input-join')
    parent = direct_target_actions.decode_action(data, source=source, logical_sha256=digest,
        start=start, end=end, tag=tag, native_validation=native)
    binding = native['targetBinding']; field = parent['namedFields'][binding['index']]
    if field['fieldName'] != binding['fieldName'] or field['kind'] != binding['kind']:
        raise ValueError('buffRecursiveActions.directTarget:target-parent-join')
    child = recursive_target(data, source, digest, field, context)
    return {'schema': 'endfield.buff-recursive-action-receipt.v1', 'tag': tag,
            'start': start, 'end': end, 'parent': parent, 'target': child, 'recursiveStoredSchemaExact': True}
