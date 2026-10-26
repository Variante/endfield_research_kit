"""Named GameplayTagList MC1 reference record with its generated Tag list child.

The parent actual ReadPackable<List<GameplayTag>> MethodSpec/E8 joins the full
closed value-list proof. Its positive elements use MC1/tagId records, while the
separate Query raw4 array grammar has no admission here. Own original/wrapper
factories, getter and canonical ordinary reference adapter/reader are re-proved;
matching runtime selection/normal helper effects remain conditions. Stored tag
configuration conveys no runtime meaning, and enclosing root/EOF stays open.
"""
import json

from scripts.game_data.memorypack.skill_root_child_bindings import need,reference_record_abi
from scripts.game_data.memorypack.skill_root_attribute_components import reference_cap

TYPE='Beyond.Gameplay.Core.GameplayTagList'
CAPABILITY='skill-root-gameplay-tag-list'
LIST_CAP='skill-root-gameplay-tag-value-list'
ORDER=[dict(fieldName='predefinedTag',kind='value-list',childCapability=LIST_CAP)]


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.skill_root_record_sources import derive as record_sources
    from scripts.game_data.memorypack.skill_gameplay_tag_lists import derive as list_source
    record=record_sources(image,pins,types=[TYPE])['records'][TYPE]
    reference=reference_record_abi(image,pins,record)
    join,=record['requiredChildJoins'];need('exact-owned-list-field','predefinedTag',join['fieldName'])
    child=list_source(image,pins,typed_request=join['typedRequest'],call_target=image.pe.image_base+join['sourceTargetRva'])
    need('same-selected-child-pins',pins,child['nativeInputs']);cap=child['capabilities'][LIST_CAP]
    need('same-actual-parent-list',(join['typeName'],join['typedRequest']['methodSpec'][0],join['sourceTargetRva']),
        (cap['closedListType'],cap['packableReaderMethodDefinition'],cap['packableReaderTargetRva']))
    caps=dict(child['capabilities']);caps[CAPABILITY]=reference_cap(record,reference,ORDER)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-root-gameplay-tag-list-components.v1',nativeInputs=pins,
        status='validated-conditional-components',capabilities=caps,proof=dict(parent=record,parentReference=reference,
            child=child,parentBinding=dict(fieldName='predefinedTag',capability=LIST_CAP)),
        evidenceBoundary=dict(exact='Current GameplayTagList MC1/FF/new source, own factory/getter/reference adapter and actual typed closed generated GameplayTag value-list source/callback/Add join.',
            conditional=__doc__,structuralOnly='Stored tag configuration.',unresolved=['enclosing root typed call/EOF','runtime meaning/selection']))))
