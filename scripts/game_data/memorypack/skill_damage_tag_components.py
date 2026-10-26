"""Actual DamageUnit damageTags field and the generated GameplayTag list.

The selected closed list uses MC1/Int32 GameplayTag values, not the distinct
raw unmanaged four-byte Query array. Actual parent type/MethodSpec/call and
fresh complete list/callback/Add/count proofs join here. Runtime callback
selection, normal helpers and fresh or reused-empty lists remain conditions;
the other DamageUnit fields and whole owner are independent.
"""
import json

from scripts.game_data.memorypack.skill_root_child_bindings import need

FIELD='damageTags'
TYPE='Beyond.Gameplay.Core.GameplayTag'
ELEMENT='skill-root-gameplay-tag'
LIST='skill-root-gameplay-tag-value-list'


def bind(pins,join,component):
    need('same-damage-tag-native-inputs',pins,component['nativeInputs'])
    need('exact-damage-tag-component','validated-conditional-components',component['status'])
    need('actual-damage-tag-field',FIELD,join['fieldName'])
    cap=component['capabilities'][LIST];element=component['capabilities'][ELEMENT]
    closed='System.Collections.Generic.List`1<'+TYPE+'>'
    request=join['typedRequest']
    need('actual-damage-tag-closed-request',('MemoryPack.MemoryPackReader','ReadPackable',[],[closed]),
        tuple(request.get(key)for key in('typeName','methodName','classArguments','methodArguments')))
    need('same-damage-tag-list-source',(closed,request['methodSpec'][0],join['sourceTargetRva']),
        (cap['closedListType'],cap['packableReaderMethodDefinition'],cap['packableReaderTargetRva']))
    need('same-damage-tag-field-type',closed,join['typeName'])
    need('exact-generated-damage-tag-wire',True,element.get('typeName')==TYPE
        and element.get('memberCount')==1 and element.get('managedBytes')==4
        and element.get('positiveWireBytes')==5 and element.get('nullWireBytes')==1
        and element.get('nullReturnsDefaultValue')is True
        and element.get('rawUnmanagedTagGrammarUsed')is False
        and element.get('orderedReads')==[dict(fieldName='tagId',kind='int32')])
    need('exact-generated-damage-tag-list',True,cap.get('elementType')==TYPE
        and cap.get('elementValueType')is True and cap.get('managedElementBytes')==4
        and cap.get('elementCapability')==ELEMENT and cap.get('elementGrammarAdmitted')is True
        and cap.get('positiveCountsAdmitted')is True and cap.get('collectionCounts')==[-1,0]
        and type(cap.get('countLimit'))is int and cap['countLimit']==10000)
    return dict(fieldName=FIELD,kind='value-list',childCapability=LIST,
        sourceTargetRva=join['sourceTargetRva'],methodDefinition=request['methodSpec'][0],
        rawUnmanagedTagGrammarUsed=False,wholeDamageUnitAdmitted=False)


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.skill_damage_unit_sources import derive as parent_source
    from scripts.game_data.memorypack.skill_gameplay_tag_lists import derive as list_source
    _publication_gate(image,pins);parent=parent_source(image,pins)
    join,=[row for row in parent['requiredChildJoins']if row['fieldName']==FIELD]
    child=list_source(image,pins,typed_request=join['typedRequest'],
        call_target=image.pe.image_base+join['sourceTargetRva'],count_limit=10000)
    binding=bind(pins,join,child);_publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-damage-tag-components.v1',nativeInputs=pins,
        status='validated-conditional-damage-tag-list',capabilities=child['capabilities'],
        proof=dict(parent=parent,child=child,parentBinding=binding),wholeDamageUnitAdmitted=False,
        evidenceBoundary=dict(exact='Actual DamageUnit damageTags closed type, MethodSpec and E8 joined to generated MC1/Int32 Tag callback/Add/count source through10000.',
            conditional=__doc__,structuralOnly='Stored generated damage tags.',
            unresolved=['other DamageUnit fields','runtime meaning/selection','whole owner/physical EOF']))))
