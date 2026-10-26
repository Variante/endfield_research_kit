"""Own BuffFilterSettings and its actual ordinary BuffFindSettings child call.

Both stored fields require complete current generated source, lifecycle and
unchanged setters. The nested BuffFind component retains its pooled list and
Query source conditions. Matching coherent nominal callbacks/typed contexts,
normal allocation/helpers, disabled collectors and disjoint buffered storage
remain conditions. Stored stack filtering supplies no runtime filter result,
enclosing selector union, Skill owner or physical EOF admission.
"""
import json

from scripts.game_data.memorypack.skill_root_child_bindings import need

TYPE='Beyond.Gameplay.Core.BuffFilterSettings'
CHILD='Beyond.Gameplay.Core.BuffFindSettings'
CAPABILITY='skill-selector-buff-filter-settings'
CHILD_CAPABILITY='skill-root-buff-find-settings'
ORDER=[dict(memberIndex=i,fieldName=n,kind=k,childCapability=c)for i,n,k,c in(
    (0,'buffSettings','buff-find-settings',CHILD_CAPABILITY),(1,'buffStackNumType','scalar32',None))]


def capability(source,pins,program,abi,child):
    need('same-BuffFilter-native-inputs',pins,source['nativeInputs'])
    need('same-BuffFind-native-inputs',pins,child['nativeInputs'])
    need('own-BuffFilter-nominal-source',TYPE,source['wrappedType'])
    need('BuffFilter-exact-two-field-order',ORDER,program['reads'])
    need('BuffFilter-exact-child-dependency',[CHILD_CAPABILITY],program['requiredCapabilities'])
    need('BuffFilter-two-members',2,program['memberCount'])
    life=source['lifecycle']
    need('BuffFilter-own-direct-holder',True,life.get('directHolderMode')is True
        and life.get('typedCache')is None and life.get('baseHolder')==[source['wrapperName'],TYPE,16])
    need('BuffFilter-literal-ordinary-reader',True,type(abi.get('referenceReaderMethodDefinition'))is int
        and abi['referenceReaderMethodDefinition']>=0 and type(abi.get('referenceReaderTargetRva'))is int
        and abi['referenceReaderTargetRva']>0)
    return dict(typeName=TYPE,wrapperName=source['wrapperName'],memberCount=2,orderedReads=ORDER,
        nullAdmitted=True,nullMarker=255,wholeGrammarAdmitted=True,ordinaryOriginalReadValueAdmitted=True,
        ownConcreteGetterSemanticsProved=True,ownConcreteFactorySemanticsProved=True,
        **{k:abi[k]for k in('referenceReaderMethodDefinition','referenceReaderTargetRva')},wholeSkillDataAdmitted=False)


def derive(image,pins,*,buff_find_component=None):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack import generated_reader_sources
    from scripts.game_data.memorypack.generated_record_components import compile_member_program
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.skill_root_child_bindings import reference_reader_abi
    from scripts.game_data.memorypack.pointer_param import leaf
    _publication_gate(image,pins)
    if buff_find_component is None:
        from scripts.game_data.memorypack.skill_root_buff_find_components import derive as child_source
        buff_find_component=child_source(image,pins)
    need('strong-current-BuffFind-component',True,buff_find_component.get('schema')=='endfield.skill-root-buff-find-components.v1'
        and buff_find_component.get('status')=='validated-conditional-components'and buff_find_component.get('nativeInputs')==pins)
    wrapper,=[w for w in image.memorypack_wrappers.values()if w.wrapped_type==TYPE]
    source=generated_reader_sources.derive(image,pins,wrapper.name)
    requests={r['memberIndex']:derive_typed_usage_context(image,r['context']['instructionRva'],label='skillSelectorBuffFilter')
        for r in source['orderedSourceReads']if r['kind']=='reference:'+CHILD}
    program,pending=compile_member_program(source,pins,wrapper_name=wrapper.name,type_name=TYPE,value4={},
        references={CHILD:(CHILD_CAPABILITY,'buff-find-settings',CHILD_CAPABILITY)},
        reference_children={CHILD:buff_find_component},typed_requests=requests)
    need('complete-BuffFilter-child-grammar',[],pending)
    pair=derive_pair(image,TYPE,wrapper.name);adapter=derive_adapter(image,pins,pair,wrapper)
    need('BuffFilter-same-owned-getter',source['lifecycle']['GetValue']['method'],adapter['getterMethod'])
    getter=leaf(image,image.pe.image_base+adapter['getterMethod'][3],['488B4110','C3'])
    abi=reference_reader_abi(image,pins);cap=capability(source,pins,program,abi,buff_find_component)
    nominal=buff_find_component['capabilities'][CHILD_CAPABILITY]
    identity={k:nominal[k]for k in('typeName','referenceReaderMethodDefinition','referenceReaderTargetRva')}
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-selector-buff-filter-components.v1',nativeInputs=pins,
        status='validated-conditional-BuffFilter-components',capabilities={CAPABILITY:cap},
        requiredExternalCapabilities=[CHILD_CAPABILITY],requiredExternalCapabilityIdentities={CHILD_CAPABILITY:identity},
        proof=dict(source=source,child=buff_find_component,compiledProgram=program,pair=pair,adapter=adapter,
            getter=getter,referenceABI=abi),wholeSkillDataAdmitted=False,
        evidenceBoundary=dict(exact='Complete current MC2/new/existing/FF source, actual BuffFind ReadValue/context and scalar32, own holder/factory/getter and canonical ordinary reference adapter.',
            conditional=__doc__,structuralOnly='Stored buff filter settings.',
            unresolved=['runtime selection/filter result','enclosing selector and Skill source joins']))))
