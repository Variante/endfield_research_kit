"""UIRangeHintData and its complete SkillHintShapeData source composition.

The finite named MC3 and MC21 programs own generated new/existing/FF source,
constructors, setters/holder getters, canonical reference adapters and actual
ordinary Reader identities. Each Vector2 field joins its own actual typed
ReadUnmanaged/SSE bit-lane/counter program and separately registered canonical
source; no managed width or pointer alias supplies wire8. Pooled strings and
all primitive actual helper identities remain gated. These are stored shape
configuration, with no runtime UI/target meaning, root or EOF admission. Ready
coherent selected callbacks, normal compatible helpers/allocations, selected
exported StringPool, disabled GC and disjoint buffered storage are conditions.
"""
import json

from scripts.game_data.memorypack.skill_root_child_bindings import need
from scripts.game_data.memorypack.skill_root_attribute_components import reference_cap

SHAPE='Beyond.Gameplay.SkillHintShapeData'
TYPE='Beyond.Gameplay.Core.UIRangeHintData'
SHAPE_CAP='skill-root-skill-hint-shape'
CAPABILITY='skill-root-ui-range-hint'
LIST_CAP='skill-root-ui-range-hint-list'
DECLARED={
 SHAPE:['float','string','bool','UnityEngine.Vector2','string','string','UnityEngine.Vector2','string','string',
    'bool','float','string','bool','Beyond.Gameplay.SkillHintShape','bool','bool','bool','bool','bool','float','string'],
 TYPE:['bool',SHAPE,'Beyond.Gameplay.Core.FactionType'],
}


def order(name):
    from scripts.game_data.memorypack.skill_root_children_codec import REFERENCE_RECORDS
    return [dict(fieldName=n,kind=k,childCapability=c)for n,k,c in REFERENCE_RECORDS[name][1]]


def bind_compiled(compiled,expected):
    aliases={'bool-byte':'bool','byte-payload':'pooled-string','float32-bits':'single-bits','scalar32':'enum32',
        'vector2-raw8':'vector2-raw8','record':'record'}
    need('UIRange-finite-compiled-kinds',True,all(r['kind']in aliases for r in compiled['reads']))
    need('UIRange-exact-source-program',expected,[dict(fieldName=r['fieldName'],kind=aliases[r['kind']],
        childCapability=r['childCapability'])for r in compiled['reads']])
    need('UIRange-literal-member-indices',True,all(type(r['memberIndex'])is int for r in compiled['reads'])
        and[r['memberIndex']for r in compiled['reads']]==list(range(len(expected))))


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack.generated_reader_sources import derive_many
    from scripts.game_data.memorypack.generated_record_components import compile_member_program
    from scripts.game_data.memorypack.skill_root_generated_reference import derive as reference_source
    wrappers=[]
    for typ in(SHAPE,TYPE):
        wrapper,=[w for w in image.memorypack_wrappers.values()if w.wrapped_type==typ];wrappers.append(wrapper.name)
    generated=derive_many(image,pins,wrappers);records={};caps={}
    for result,typ,name in zip(generated['owners'],(SHAPE,TYPE),(SHAPE_CAP,CAPABILITY),strict=True):
        need('UIRange-full-generated-source:'+typ,'complete-reader-source-proved',result['status'])
        source=result['proof'];reads=source['orderedSourceReads'];expected=order(name)
        need('UIRange-exact-finite-member-names',[r['fieldName']for r in expected],[r['fieldName']for r in reads])
        need('UIRange-exact-finite-declared-types',DECLARED[typ],[r['declaredType']for r in reads])
        values={str(r['memberIndex']):source['sourceScope']['primitiveSources'][str(r['memberIndex'])]
            for r in reads if r['kind']=='value8:UnityEngine.Vector2'}
        references={SHAPE:(SHAPE_CAP,'record',SHAPE_CAP)}if typ==TYPE else{}
        children={SHAPE:dict(nativeInputs=pins,capabilities=caps)}if typ==TYPE else{}
        requests={r['memberIndex']:derive_typed_usage_context(image,r['context']['instructionRva'],label='UIRange.shape')
            for r in reads if r['declaredType']==SHAPE}
        compiled,pending=compile_member_program(source,pins,wrapper_name=source['wrapperName'],type_name=typ,
            value4={},value8={'UnityEngine.Vector2':values}if values else{},references=references,
            reference_children=children,typed_requests=requests)
        need('UIRange-complete-child-program',[],pending);bind_compiled(compiled,expected)
        if typ==SHAPE:need('UIRange-exact-two-Vector2-members',{'3','6'},set(values))
        reference=reference_source(image,pins,source)
        descriptor=dict(typeName=typ,wrapperName=source['wrapperName'],memberCount=len(expected))
        cap=reference_cap(descriptor,reference,expected);cap['ordinaryOriginalReadValueAdmitted']=True;caps[name]=cap
        records[typ]=dict(source=source,reference=reference,compiled=compiled)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-root-ui-range-components.v1',nativeInputs=pins,
        status='validated-conditional-components',capabilities=caps,requiredExternalCapabilities=['byte-payload'],
        proof=dict(records=records),evidenceBoundary=dict(
            exact='UIRangeHintData MC3/FF and SkillHintShapeData MC21/FF complete generated source/lifecycle/ordinary reference adapters, actual named Shape reference and independent Vector2 typed SSE/raw8 source joins, primitive/pool helper identities.',
            conditional=__doc__,structuralOnly='Stored UI range/shape configuration.',unresolved=['runtime UI/target meaning','enclosing root/EOF']))))


def derive_list(image,pins,*,typed_request,call_target,count_limit=10000):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.reference_list_induction_sources import derive as list_source
    child=derive(image,pins)
    collection=list_source(image,pins,typed_request=typed_request,call_target=call_target,element_type=TYPE,count_limit=count_limit)
    witness=collection['witnessComponent'];caps=dict(child['capabilities'])
    caps[LIST_CAP]=dict(elementType=TYPE,elementValueType=False,closedListType='System.Collections.Generic.List`1<'+TYPE+'>',
        collectionCounts=[-1,0],nullable=True,countLimit=count_limit,positiveCountsAdmitted=True,
        elementCapability=CAPABILITY,elementGrammarAdmitted=True,
        packableReaderMethodDefinition=witness['typedRequest']['methodSpec'][0],packableReaderTargetRva=witness['callTargetRva'],
        callbackSelectionConditional=True,wholeSkillDataAdmitted=False)
    _publication_gate(image,pins)
    return dict(schema='endfield.skill-root-ui-range-list-components.v1',nativeInputs=dict(pins),status='validated-conditional-components',
        capabilities=caps,proof=dict(child=child,collection=collection),requiredExternalCapabilities=['byte-payload'],
        parentFieldAdmitted=False,wholeOwnerAdmitted=False,evidenceBoundary=child['evidenceBoundary'])
