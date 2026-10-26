"""Independent current Effect source, ordinary adapter and array child joins.

Complete source/lifecycle and nominal reference ABI do not supply delegated
blackboard or TerrainEffect grammar. Every later compiled field must bind its
actual typed source. No asset resolution, playback or live selection follows.
"""
import json

from scripts.game_data.memorypack.skill_effect_codec import TYPE,CAPABILITY,ARRAY,TERRAIN,TERRAIN_TYPE
from scripts.game_data.memorypack.skill_root_child_bindings import need


def bind_array_member(pins,join,child,capability):
    """Bind ReadArray<TerrainEffectData>, never ReadValue<TerrainEffectData[]>.

    The child owner must already have composed its actual array source and the
    independently complete ordinary TerrainEffect record on this same image.
    """
    need('same-Effect-array-native-inputs',pins,child['nativeInputs'])
    need('exact-Effect-array-capability',ARRAY,capability)
    cap=child['capabilities'][ARRAY];usage=join['typedRequest']
    need('same-source-owned-Effect-array',child['proof']['array'],join['arraySource'])
    need('literal-Effect-array-reader',True,type(cap.get('arrayReaderMethodDefinition'))is int
        and cap['arrayReaderMethodDefinition']>=0 and type(cap.get('arrayReaderTargetRva'))is int
        and cap['arrayReaderTargetRva']>0)
    need('exact-Effect-array-nominal',TERRAIN_TYPE+'[]',join['typeName'])
    need('actual-Effect-array-request',(6,'MemoryPack.MemoryPackReader','ReadArray',[],[TERRAIN_TYPE]),
        tuple(usage.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments')))
    need('exact-Effect-array-reader-definition',cap['arrayReaderMethodDefinition'],usage['methodSpec'][0])
    need('exact-Effect-array-E8-target',cap['arrayReaderTargetRva'],join['sourceTargetRva'])
    need('complete-Effect-array-scope',True,cap.get('closedArrayType')==TERRAIN_TYPE+'[]'
        and cap.get('elementType')==TERRAIN_TYPE and cap.get('elementValueType')is False
        and cap.get('elementCapability')==TERRAIN and cap.get('collectionCounts')==[-1,0]
        and all(type(v)is int for v in cap['collectionCounts'])
        and type(cap.get('countLimit'))is int and cap['countLimit']==10000
        and all(cap.get(k)is True for k in('positiveCountsAdmitted','nullable','elementGrammarAdmitted','wholeGrammarAdmitted')))
    element=child['capabilities'][TERRAIN]
    need('complete-Effect-array-element',True,element.get('typeName')==TERRAIN_TYPE
        and type(element.get('memberCount'))is int and element['memberCount']==2
        and element.get('orderedReads')==[dict(memberIndex=i,fieldName=n,kind='byte-payload',childCapability='byte-payload')
            for i,n in enumerate(('effectName','tag'))]
        and all(element.get(k)is True for k in('wholeGrammarAdmitted','ordinaryOriginalReadValueAdmitted',
            'ownConcreteGetterSemanticsProved','ownConcreteFactorySemanticsProved')))
    keys=('closedArrayType','elementType','elementValueType','elementCapability','collectionCounts','countLimit',
        'positiveCountsAdmitted','nullable','elementGrammarAdmitted','arrayReaderMethodDefinition','arrayReaderTargetRva')
    return dict(fieldName=join['fieldName'],typeName=join['typeName'],capability=capability,
        readerMethodDefinition=cap['arrayReaderMethodDefinition'],sourceTargetRva=cap['arrayReaderTargetRva'],
        arrayIdentity={k:cap[k]for k in keys},elementCapabilityShape=element)


def derive_reference(image,pins):
    """Fresh complete concrete source and ordinary ABI; no child admission."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack import generated_reader_sources
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.skill_root_child_bindings import reference_reader_abi
    _publication_gate(image,pins)
    wrapper,=[w for w in image.memorypack_wrappers.values()if w.wrapped_type==TYPE]
    source=generated_reader_sources.derive(image,pins,wrapper.name)
    need('complete-current-Effect-source-count',86,source['sourceScope']['memberCount'])
    pair=derive_pair(image,TYPE,wrapper.name);adapter=derive_adapter(image,pins,pair,wrapper)
    need('same-own-Effect-GetValue',source['lifecycle']['GetValue']['method'],adapter['getterMethod'])
    need('same-own-Effect-concrete-formatter',source['lifecycle']['concreteFormatter']['method'][0],
        pair['composition']['interfaces'][0]['formatterDeserializeMethodIndex'])
    abi=reference_reader_abi(image,pins);_publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-effect-reference-components.v1',nativeInputs=pins,
        status='validated-Effect-source-and-reference-adapter',typeName=TYPE,wrapperName=wrapper.name,memberCount=86,
        referenceReaderMethodDefinition=abi['referenceReaderMethodDefinition'],referenceReaderTargetRva=abi['referenceReaderTargetRva'],
        proof=dict(source=source,pair=pair,adapter=adapter,referenceABI=abi),
        childGrammarsAdmitted=False,wholeEffectActionCfgAdmitted=False,actualEnclosingParentAdmitted=False,
        wholeSkillDataAdmitted=False,evidenceBoundary=__doc__)))


def derive(image,pins):
    """Compose the complete finite Effect grammar on the selected image."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack import skill_terrain_effect_components as terrain
    from scripts.game_data.memorypack import skill_blackboard_double_sources,skill_blackboard_vector3_sources,pooled_source_helper
    from scripts.game_data.memorypack.generated_record_components import compile_member_program
    _publication_gate(image,pins);reference=derive_reference(image,pins);source=reference['proof']['source']
    scope=source['sourceScope'];element=terrain.derive(image,pins)
    array,=[value for value in scope['arraySources'].values()]
    cap=terrain.bind_array(pins,array['typedRequest'],array['arrayReaderTargetRva'],array,element)
    array_child=dict(nativeInputs=pins,capabilities={**element['capabilities'],ARRAY:cap},proof=dict(array=array,element=element))
    double='Beyond.Blackboard+BlackboardDouble';vector='Beyond.Blackboard+BlackboardVector3'
    children={double:skill_blackboard_double_sources.derive(image,pins),vector:skill_blackboard_vector3_sources.derive(image,pins)}
    references={double:('skill-blackboard-double','blackboard-double','scalar-payload'),
        vector:(skill_blackboard_vector3_sources.CAPABILITY,'blackboard-vector3','blackboard-vector3')}
    requests={read['memberIndex']:derive_typed_usage_context(image,read['context']['instructionRva'],label='skillEffectComponents')
        for read in source['orderedSourceReads']if read['kind'].startswith('reference:')}
    array_reads=[r for r in source['orderedSourceReads']if r.get('mode')=='typed-reference-array']
    need('one-source-owned-Terrain-array',1,len(array_reads));read=array_reads[0]
    need('same-Terrain-array-field',('effectPosData',TERRAIN_TYPE+'[]'),(read['fieldName'],read['declaredType']))
    program,pending=compile_member_program(source,pins,wrapper_name=source['wrapperName'],type_name=TYPE,value4={},
        references=references,reference_children=children,typed_requests=requests,
        arrays={TERRAIN_TYPE+'[]':(ARRAY,'terrain-effect-array',ARRAY)},
        array_children={read['memberIndex']:array_child},array_binder=bind_array_member)
    need('complete-finite-Effect-grammar',[],pending)
    pooled={}
    for read in source['orderedSourceReads']:
        if read['kind']=='byte-payload'and read['sourceTargetRva']not in pooled:
            target=read['sourceTargetRva'];pooled[target]=pooled_source_helper.validate_on_image(image,image.pe.image_base+target,pins)
    effect=dict(typeName=TYPE,wrapperName=source['wrapperName'],memberCount=86,orderedReads=program['reads'],
        wholeGrammarAdmitted=True,ordinaryOriginalReadValueAdmitted=True,ownConcreteGetterSemanticsProved=True,
        ownConcreteFactorySemanticsProved=True,completeSourceOwnedProgram=True,nullAdmitted=True,nullMarker=255,
        **{k:reference[k]for k in('referenceReaderMethodDefinition','referenceReaderTargetRva')})
    requirements=sorted(set(program['requiredCapabilities'])-set(array_child['capabilities']))
    identities={operation:{key:children[typename]['capabilities'][capability][key]
        for key in('typeName','referenceReaderMethodDefinition','referenceReaderTargetRva')}
        for typename,(capability,_,operation)in references.items()if operation in requirements}
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-effect-components.v1',status='validated-conditional-complete-Effect-grammar',
        nativeInputs=pins,capabilities={**array_child['capabilities'],CAPABILITY:effect},
        requiredExternalCapabilities=requirements,requiredExternalCapabilityIdentities=identities,
        proof=dict(reference=reference,arrayChild=array_child,referenceChildren=children,compiledProgram=program,pooledSources=pooled),
        wholeEffectActionCfgAdmitted=True,actualEnclosingParentAdmitted=False,wholeSkillDataAdmitted=False,
        evidenceBoundary=dict(exact='Complete current source/lifecycle/all4 caller paths, own ordinary adapter/Reader ABI, every literal primitive/vector capture and unchanged field store, strong blackboard sources and actual induced TerrainEffect array with pooled MC2 elements.',
            conditional=__doc__+' Initialized coherent nominal contexts and actual matching canonical callbacks, normal helper/allocator/provider/collector effects, buffered disjoint storage and fresh arrays remain conditions.',
            structuralOnly='Stored authored effect configuration; no runtime playback or asset resolution.',
            unresolved=['actual enclosing Damage/action source joins','runtime provider/callback selection','whole Skill/physical EOF']))))
