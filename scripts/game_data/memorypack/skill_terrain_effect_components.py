"""Own the nominal two-pooled-field TerrainEffectData reference component.

The actual enclosing array and EffectActionCfg callers remain independent.
Stored effect names/tags do not establish asset resolution, terrain behavior or
runtime playback. Matching coherent callbacks/contexts, normal typed allocation
and disabled collector/buffered disjoint storage remain conditions.
"""
import json

from scripts.game_data.memorypack.skill_root_child_bindings import need

TYPE='Beyond.Gameplay.TerrainEffectData'
CAPABILITY='skill-terrain-effect-data'


def capability(source,program,abi):
    need('exact-terrain-effect-type',TYPE,source['wrappedType'])
    need('exact-terrain-effect-pooled-order',[('effectName','byte-payload'),('tag','byte-payload')],
        [(read['fieldName'],read['kind'])for read in program['reads']])
    need('two-source-owned-terrain-effect-fields',2,program['memberCount'])
    need('terrain-effect-pool-dependency',['byte-payload'],program['requiredCapabilities'])
    need('literal-terrain-reference-identity',True,type(abi.get('referenceReaderMethodDefinition'))is int
        and type(abi.get('referenceReaderTargetRva'))is int)
    return dict(typeName=TYPE,wrapperName=source['wrapperName'],memberCount=2,
        orderedReads=program['reads'],nullAdmitted=True,nullMarker=255,wholeGrammarAdmitted=True,
        ordinaryOriginalReadValueAdmitted=True,ownConcreteGetterSemanticsProved=True,
        ownConcreteFactorySemanticsProved=True,**{key:abi[key]for key in('referenceReaderMethodDefinition','referenceReaderTargetRva')},
        positiveWireBytes=9,nullWireBytes=1,wholeEffectActionCfgAdmitted=False)


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack import generated_reader_sources,pooled_source_helper
    from scripts.game_data.memorypack.generated_record_components import compile_member_program
    from scripts.game_data.memorypack.pointer_param import methods
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.skill_root_child_bindings import reference_reader_abi
    _publication_gate(image,pins)
    wrapper,=[w for w in image.memorypack_wrappers.values()if w.wrapped_type==TYPE]
    source=generated_reader_sources.derive(image,pins,wrapper.name)
    program,pending=compile_member_program(source,pins,wrapper_name=wrapper.name,type_name=TYPE,value4={})
    need('complete-two-pooled-terrain-grammar',[],pending)
    pair=derive_pair(image,TYPE,wrapper.name);adapter=derive_adapter(image,pins,pair,wrapper)
    need('same-terrain-own-getter',image.method_pointer_va(methods(image,wrapper)['GetValue'])-image.pe.image_base,adapter['getterMethod'][3])
    pooled={}
    for read in source['orderedSourceReads']:
        target=read['sourceTargetRva']
        if target not in pooled:pooled[target]=pooled_source_helper.validate_on_image(image,image.pe.image_base+target,pins)
    abi=reference_reader_abi(image,pins);cap=capability(source,program,abi);_publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-terrain-effect-components.v1',nativeInputs=pins,
        status='validated-conditional-terrain-effect-record',capabilities={CAPABILITY:cap},
        requiredExternalCapabilities=['byte-payload'],proof=dict(source=source,pair=pair,adapter=adapter,
            referenceABI=abi,pooledSources=pooled,compiledProgram=program),wholeEffectActionCfgAdmitted=False,
        evidenceBoundary=dict(exact='Complete current TerrainEffectData MC2/new/existing/FF source, effectName/tag pooled indexes, own factories/getter and ordinary adapter.',
            conditional=__doc__,structuralOnly='Stored effect name/tag.',
            unresolved=['actual enclosing array/EffectActionCfg source joins','runtime meaning/playback','whole owner/EOF']))))


def bind_array(pins,typed_request,call_target_rva,array,element):
    need('same-terrain-array-inputs',pins,array['nativeInputs']);need('same-terrain-element-inputs',pins,element['nativeInputs'])
    need('exact-terrain-array-status','validated-conditional-reference-array-component',array['status'])
    need('exact-terrain-array-type',(TYPE,False,TYPE+'[]'),tuple(array.get(k)for k in('elementType','elementValueType','closedArrayType')))
    need('actual-terrain-array-request',typed_request,array['typedRequest'])
    need('actual-terrain-array-call',call_target_rva,array['arrayReaderTargetRva'])
    need('actual-terrain-array-definition',typed_request['methodSpec'][0],array['arrayReaderMethodDefinition'])
    need('fresh-bounded-terrain-array',True,type(array.get('countLimit'))is int and array['countLimit']==10000
        and array.get('positiveCountsAdmitted')is True and array.get('nullable')is True and array.get('collectionCounts')==[-1,0]
        and all(array.get(key)is False for key in('elementGrammarAdmitted','parentFieldAdmitted','wholeOwnerAdmitted')))
    cap=element['capabilities'][CAPABILITY];nominal=array['elementNominalReference']
    need('whole-ordinary-terrain-element',True,cap.get('typeName')==TYPE
        and all(cap.get(key)is True for key in('wholeGrammarAdmitted','ordinaryOriginalReadValueAdmitted',
            'ownConcreteGetterSemanticsProved','ownConcreteFactorySemanticsProved')))
    need('exact-terrain-array-element-reference',(TYPE,cap['wrapperName'],cap['referenceReaderMethodDefinition'],cap['referenceReaderTargetRva']),
        tuple(nominal.get(k)for k in('typeName','wrapperName','referenceReaderMethodDefinition','referenceReaderTargetRva')))
    need('same-terrain-array-canonical-adapter',element['proof']['adapter']['callbackBinding']['canonicalTargetRva'],
        nominal['callbackBinding']['canonicalTargetRva'])
    return dict(elementType=TYPE,elementValueType=False,closedArrayType=TYPE+'[]',collectionCounts=[-1,0],
        countLimit=10000,positiveCountsAdmitted=True,nullable=True,elementCapability=CAPABILITY,
        elementGrammarAdmitted=True,arrayReaderMethodDefinition=array['arrayReaderMethodDefinition'],
        arrayReaderTargetRva=call_target_rva,wholeGrammarAdmitted=True,parentFieldAdmitted=False,wholeEffectActionCfgAdmitted=False)


def derive_array(image,pins,*,typed_request,call_target):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.skill_reference_array_sources import derive as array_source
    _publication_gate(image,pins);element=derive(image,pins)
    array=array_source(image,pins,typed_request=typed_request,call_target=call_target,element_type=TYPE,count_limit=10000)
    cap=bind_array(pins,typed_request,call_target-image.pe.image_base,array,element)
    caps=dict(element['capabilities']);caps['skill-terrain-effect-array']=cap;_publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-terrain-effect-array-components.v1',nativeInputs=pins,
        status='validated-conditional-terrain-effect-array',capabilities=caps,requiredExternalCapabilities=['byte-payload'],
        proof=dict(array=array,element=element),parentFieldAdmitted=False,wholeEffectActionCfgAdmitted=False,
        evidenceBoundary=dict(exact='Actual nominal TerrainEffectData ReadArray source/context/callback and fresh count induction through10000, joined to complete ordinary MC2/pooled element.',
            conditional=__doc__+' Fresh arrays and the exact canonical element callback/provider first-probe conditions remain required.',
            structuralOnly='Stored terrain effect records.',unresolved=['complete enclosing EffectActionCfg source/framing','runtime selection/meaning','whole owner/EOF']))))
