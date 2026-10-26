"""Compose Query's own MC2/FF value16 and raw4 bulk-array grammar.

The actual typed caller's fixed-slot5 target composes its independent callback,
wrapper/interface/GetValue transfer and concrete Query source. The named tags
field independently supplies its typed unmanaged-array request and actual E8;
that source owns count, allocation/data pointer, bounded copy and four Reader
updates. No array or managed-size declaration substitutes for child bytes.
Runtime selection and surrounding parent/root framing remain conditional and
unresolved until their own exact source/cursor joins.
"""
import json

from scripts.game_data.memorypack.skill_root_tag_query_sources import need,VALUE,ELEMENT

CAPABILITY='skill-root-gameplay-tag-query'
ARRAY='skill-root-gameplay-tag-array'
ORDER=[dict(fieldName='queryType',kind='enum32',childCapability=None),
    dict(fieldName='tags',kind='unmanaged-array',childCapability=ARRAY)]


def derive(image,pins,*,typed_request,dispatcher_target):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.skill_root_tag_query_sources import derive as child_source
    from scripts.game_data.memorypack.skill_root_tag_query_transfer import derive as transfer_source
    from scripts.game_data.memorypack.skill_gameplay_tag_array_sources import derive as array_source
    child=child_source(image,pins)
    array=array_source(image,pins,typed_request=child['arrayUsage'],call_target=image.pe.image_base+child['symbolRvas']['array'])
    transfer=transfer_source(image,pins,typed_request=typed_request,dispatcher_target=dispatcher_target,child=child)
    for name,component in(('array',array),('transfer',transfer)):need('same-component-native:'+name,pins,component['nativeInputs'])
    cap=array['capabilities'][ARRAY]
    need('actual-declared-array-context',(ELEMENT,child['arrayUsage']['methodSpec'][0],child['symbolRvas']['array']),
        (cap['elementType'],cap['arrayReaderMethodDefinition'],cap['arrayReaderTargetRva']))
    caps=dict(array['capabilities']);caps[CAPABILITY]=dict(typeName=VALUE,memberCount=2,managedBytes=16,
        nullable=True,nullMarker=255,nullWireBytes=1,positiveWireBytes=None,wireBytes=None,
        nullReturnsDefaultValue=True,wholeGrammarAdmitted=True,orderedReads=ORDER,
        ownConcreteGetterSemanticsProved=True,ownConcreteFactorySemanticsProved=True,
        valueReaderMethodDefinition=transfer['readerMethodDefinition'],valueDispatcherTargetRva=transfer['dispatcherTargetRva'],
        callbackSelectionConditional=True,wholeSkillDataAdmitted=False)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-root-tag-query-components.v1',nativeInputs=pins,
        status='validated-conditional-components',capabilities=caps,proof=dict(child=child,array=array,transfer=transfer),
        parentFieldAdmitted=False,evidenceBoundary=dict(
            exact='Current nominal Query MC2/FF/fresh source, complete managed16 getter/canonical callback/default conversion, actual typed tag-array call, array counts -1/0/1..64 with raw4 elements, bounded copy and exact return/counters.',
            conditional=__doc__,structuralOnly='Stored tag query.',unresolved=['actual enclosing source/cursor binding','runtime selection','whole owner/physical EOF']))))
