"""Compose actual Calculation and DamageProcessor union children.

Every route owns its concrete complete generated reader/lifecycle, independently
proved scalar or nominal reference children, actual typed union case and base
Original interface conversion. A finite closed union admits no DamageUnit,
effect, list, enclosing action, runtime calculation or playback.
"""
import json

from scripts.game_data.memorypack.generated_record_components import compile_member_program

LABEL='skillDamageUnionComponents'
FAMILIES=('CalculationBase','DamageProcessorBase')
REFERENCES={
    'Beyond.Blackboard+BlackboardDouble':('skill-blackboard-double','blackboard-double','scalar-payload'),
    'Beyond.Gameplay.AttributeModifierData+AttributeModifier':('skill-root-attribute-modifier','record','skill-root-attribute-modifier'),
}


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def compile_child(route,concrete,pins,*,reference_children,typed_requests):
    """Pure finite member compilation; source freshness belongs to derive."""
    result,pending=compile_member_program(concrete,pins,wrapper_name=route['wrapperName'],type_name=route['wrappedType'],
        value4={},references=REFERENCES,reference_children=reference_children,typed_requests=typed_requests)
    if pending:return None,pending
    return dict(tag=route['tag'],wrapperName=route['wrapperName'],typeName=route['wrappedType'],
        memberCount=result['memberCount'],orderedReads=result['reads'],nullMarker=255,nullAdmitted=True,
        generatedWrapperOnly=True,ordinaryOriginalReadValueAdmitted=False,wholeGrammarAdmitted=True,
        requiredCapabilities=result['requiredCapabilities'],childBindings=result['childBindings']),[]


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack import current_reference_union_sources,generated_reader_sources,buff_ec_profiles_native as ec
    from scripts.game_data.memorypack import skill_blackboard_double_sources,skill_root_attribute_components,pooled_source_helper
    _publication_gate(image,pins)
    unions=current_reference_union_sources.derive(image,pins,families=FAMILIES)
    need('same-selected-union-inputs',unions['nativeInputs']==pins
        and unions['status']=='validated-reference-union-callers-and-base-adapters'
        and unions['wholeSkillDataAdmitted']is False and set(unions['families'])==set(FAMILIES))
    by_name={route['wrapperName']:route for family in unions['families'].values()for route in family['programs']}
    need('disjoint-concrete-union-children',len(by_name)==sum(len(f['programs'])for f in unions['families'].values()))
    readers=generated_reader_sources.derive_many(image,pins,list(by_name))
    need('same-selected-concrete-inputs',readers['nativeInputs']==pins and readers['wholeOwnerAdmitted']is False)
    children={'Beyond.Blackboard+BlackboardDouble':skill_blackboard_double_sources.derive(image,pins),
        'Beyond.Gameplay.AttributeModifierData+AttributeModifier':skill_root_attribute_components.derive(image,pins)}
    closed={};proofs={};pending=[];pooled={};seen=set()
    for candidate in readers['owners']:
        proof=candidate.get('proof');name=proof['wrapperName']if proof is not None else candidate['wrapperName']
        need('one-current-concrete-result',name in by_name and name not in seen);seen.add(name)
        if candidate['status']!='complete-reader-source-proved':
            pending.append(dict(wrapperName=name,stage='complete-caller-source',reason=candidate['reason']));continue
        usages={read['memberIndex']:derive_typed_usage_context(image,read['context']['instructionRva'],label=LABEL)
            for read in proof['orderedSourceReads']if read['kind'].startswith('reference:')and read['declaredType']in children}
        cap,holds=compile_child(by_name[name],proof,pins,reference_children=children,typed_requests=usages)
        if holds:
            pending.append(dict(wrapperName=name,stage='child-grammar',required=holds));continue
        for read in proof['orderedSourceReads']:
            if read['kind']=='byte-payload'and read['sourceTargetRva']not in pooled:
                target=read['sourceTargetRva'];pooled[target]=pooled_source_helper.validate_on_image(image,image.pe.image_base+target,pins)
        closed[name]=cap;proofs[name]=proof
    need('complete-concrete-result-bijection',seen==set(by_name))
    reader=ec.clone_facts(image,pins)['ReadValue'];families={}
    for name,family in unions['families'].items():
        tags=[];routes=[]
        need('owned-base-holder-semantics',family['baseGetterSemanticsAdmitted']is True and family['wholeUnionAdmitted']is False)
        for route in family['programs']:
            if route['wrapperName']not in closed:continue
            holder=proofs[route['wrapperName']]['lifecycle']['baseHolder']
            need('same-actual-union-base-holder',holder[1]==family['typeName']and holder[2]==16)
            tags.append(route['tag']);routes.append(closed[route['wrapperName']])
        families[name]=dict(typeName=family['typeName'],wrapperName=family['wrapperName'],nullAdmitted=True,nullMarker=255,
            supportedShortTags=tags,routes=routes,baseGetterSemanticsProved=True,
            concreteChildGrammarsProved=len(tags)==len(family['programs']),
            wholeGrammarAdmitted=len(tags)==len(family['programs']),
            extendedTagsAdmitted=False,reservedMarkersAdmitted=False,
            ordinaryOriginalReadValueAdmitted=len(tags)==len(family['programs']),
            referenceReaderMethodDefinition=unions['referencePackable']['valueContext']['readerMethodDefinition'],
            referenceReaderTargetRva=reader['targetRva'])
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-damage-union-components.v1',nativeInputs=pins,
        status='validated-finite-damage-union-components',families=families,pendingJoins=pending,
        requiredCapabilities=sorted({cap for child in closed.values()for cap in child['requiredCapabilities']}),
        proof=dict(unions=unions,concreteReaders=proofs,referenceChildren=children,pooledSources=pooled),
        wholeDamageUnitAdmitted=False,wholeSkillDataAdmitted=False,
        evidenceBoundary=dict(exact='Actual finite short/FF union sources and typed concrete calls, complete concrete MC/new/FF/lifecycle/member sources, exact reference-child joins and inherited base-interface GetValue conversions.',
            conditional=__doc__+' Ready compatible nominal callbacks and initialized coherent contexts; normal typed allocation/class/collector/provider effects and buffered disjoint storage. Union output begins null.',
            structuralOnly='Stored calculation and processor configuration; no evaluated result.',
            unresolved=['listed pending child joins','whole DamageUnit and actual parent fields','runtime selection/evaluation','reserved/extended tags','whole SkillData/physical EOF']))))
