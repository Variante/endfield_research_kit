"""Finite AttributeModifierData/AttributeModifier/array/BlackboardDouble joins.

Both generated reference records own complete MC/FF/new source, plain holder
getter and constructor. The actual parent ReadArray<AttributeModifier> has its
own reciprocal generic contexts, allocation/provider/slot5 source and bounded
induction; the element's three enum32 fields and separately proved concrete
BlackboardDouble source then compose. No array slot width supplies a wire
width. Runtime selection/normal helper effects remain conditions, and neither
these components nor an arbitrary similarly named array admit a root/EOF.
"""
import json

from scripts.game_data.memorypack.skill_root_child_bindings import need,bind_read_value,reference_record_abi

ATTRIBUTE='Beyond.Gameplay.AttributeModifierData+AttributeModifier'
PARENT='Beyond.Gameplay.AttributeModifierData'
CHILD_CAP='skill-root-attribute-modifier'
ARRAY_CAP='skill-root-attribute-modifier-array'
PARENT_CAP='skill-root-attribute-modifier-data'


def reference_cap(record,abi,order):
    return dict(typeName=record['typeName'],wrapperName=record['wrapperName'],memberCount=record['memberCount'],
        nullable=True,nullMarker=255,nullAdmitted=True,wholeGrammarAdmitted=True,orderedReads=order,
        referenceReaderMethodDefinition=abi['referenceReaderMethodDefinition'],referenceReaderTargetRva=abi['referenceReaderTargetRva'],
        ownConcreteGetterSemanticsProved=True,ownConcreteFactorySemanticsProved=True,
        callbackSelectionConditional=True,wholeSkillDataAdmitted=False)


def bind_array(pins,join,array,element):
    need('same-array-native-inputs',pins,array['nativeInputs']);need('same-element-native-inputs',pins,element['nativeInputs'])
    need('exact-reference-array',(ATTRIBUTE,False,ATTRIBUTE+'[]'),tuple(array.get(k)for k in('elementType','elementValueType','closedArrayType')))
    need('literal-reference-element-kind',True,array.get('elementValueType')is False)
    need('no-array-owner-or-element-admission',(False,False,False),tuple(array.get(k)for k in('elementGrammarAdmitted','parentFieldAdmitted','wholeOwnerAdmitted')))
    need('literal-array-no-child-owner-admission',True,all(array.get(k)is False for k in
        ('elementGrammarAdmitted','parentFieldAdmitted','wholeOwnerAdmitted')))
    need('bounded-array-count',True,type(array.get('countLimit'))is int and 3<=array['countLimit']<=10000)
    need('null-empty-and-positive-array',([-1,0],True,True),(array['collectionCounts'],array.get('positiveCountsAdmitted')is True,array.get('nullable')is True))
    need('literal-array-counts',True,all(type(n)is int for n in array['collectionCounts']))
    need('exact-parent-array-field',(ATTRIBUTE+'[]','ReadArray',[ATTRIBUTE]),
        (join['typeName'],join['typedRequest']['methodName'],join['typedRequest']['methodArguments']))
    need('exact-parent-array-method',join['typedRequest']['methodSpec'][0],array['arrayReaderMethodDefinition'])
    need('exact-parent-array-call',join['sourceTargetRva'],array['arrayReaderTargetRva'])
    child=element['capabilities'][CHILD_CAP]
    need('complete-nominal-array-element',(ATTRIBUTE,True,True,True),tuple(child.get(k)for k in
        ('typeName','wholeGrammarAdmitted','ownConcreteGetterSemanticsProved','ownConcreteFactorySemanticsProved')))
    need('literal-positive-child',True,all(child.get(k)is True for k in
        ('wholeGrammarAdmitted','ownConcreteGetterSemanticsProved','ownConcreteFactorySemanticsProved')))
    return dict(elementType=ATTRIBUTE,elementValueType=False,closedArrayType=ATTRIBUTE+'[]',collectionCounts=[-1,0],
        countLimit=array['countLimit'],positiveCountsAdmitted=True,nullable=True,elementCapability=CHILD_CAP,
        elementGrammarAdmitted=True,arrayReaderMethodDefinition=array['arrayReaderMethodDefinition'],
        arrayReaderTargetRva=array['arrayReaderTargetRva'],wholeSkillDataAdmitted=False)


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.skill_root_record_sources import derive as plain_sources
    from scripts.game_data.memorypack.skill_root_additional_records import derive as additional_sources
    from scripts.game_data.memorypack.skill_reference_array_sources import derive as arrays
    from scripts.game_data.memorypack.skill_blackboard_double_sources import derive as double_source
    from scripts.game_data.memorypack.skill_root_children_codec import REFERENCE_RECORDS
    parent=plain_sources(image,pins,types=[PARENT])['records'][PARENT]
    child=additional_sources(image,pins,types=[ATTRIBUTE])['records'][ATTRIBUTE]
    double=double_source(image,pins);bbjoin,=child['requiredChildJoins']
    binding=bind_read_value(pins,bbjoin,double,'skill-blackboard-double')
    cabi=reference_record_abi(image,pins,child);pabi=reference_record_abi(image,pins,parent)
    order=lambda name:[dict(fieldName=n,kind=k,childCapability=c)for n,k,c in REFERENCE_RECORDS[name][1]]
    caps=dict(double['capabilities']);caps[CHILD_CAP]=reference_cap(child,cabi,order(CHILD_CAP))
    element=dict(nativeInputs=pins,capabilities=caps);ajoin,=parent['requiredChildJoins']
    array=arrays(image,pins,typed_request=ajoin['typedRequest'],call_target=image.pe.image_base+ajoin['sourceTargetRva'],element_type=ATTRIBUTE)
    caps[ARRAY_CAP]=bind_array(pins,ajoin,array,element);caps[PARENT_CAP]=reference_cap(parent,pabi,order(PARENT_CAP))
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-root-attribute-components.v1',nativeInputs=pins,
        status='validated-conditional-components',capabilities=caps,
        proof=dict(parent=parent,child=child,blackboardDouble=double,blackboardJoin=binding,
            array=array,parentReference=pabi,childReference=cabi),
        evidenceBoundary=dict(exact='Current independently named MC2/MC4/FF/new original records, enum32 source/backings, exact nominal array/provider/slot5/bounded loop and concrete BlackboardDouble source/lifecycle/reference ABI.',
            conditional=__doc__,structuralOnly='Stored attribute modifier configuration.',unresolved=['runtime provider selection','enclosing root/physical EOF']))))
