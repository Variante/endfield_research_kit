"""Ordinary reference ABI for finite complete generated root child sources.

The domain owner freshly proves the generated source/lifecycle on this image.
Only the explicitly named Toggle/UIRange/SkillHint records are available here.
Their independent holder16 GetValue/factory semantics join the newly derived
exact pair, generic canonical adapter/conversion/slot5 forwarding and actual
ordinary Reader source. No source declaration alone admits delegated children,
list elements, runtime formatter choice, enclosing root or physical EOF.
"""
from scripts.game_data.memorypack.skill_root_child_bindings import need

TYPES={'Beyond.Gameplay.Core.ToggleBuffData','Beyond.Gameplay.Core.UIRangeHintData','Beyond.Gameplay.SkillHintShapeData'}


def require_source(source,pins):
    need('root-generated-finite-source',True,source.get('schema')=='endfield.generated-concrete-reader-source.v1'
        and source.get('nativeInputs')==pins and source.get('wrappedType')in TYPES
        and source.get('completeSelectedCallerAdmitted')is True and source.get('childGrammarAdmitted')is False
        and source.get('wholeOwnerAdmitted')is False)
    life=source['lifecycle']
    need('root-generated-direct-holder-lifecycle',True,life.get('directHolderMode')is True
        and life.get('typedCache')is None and life.get('baseHolder')==[source['wrapperName'],source['wrappedType'],16])
    need('root-generated-four-complete-source-paths',True,len(source['programs'])==4
        and all(type(p.get('existing'))is bool and type(p.get('wrapperNull'))is bool
            and p['frame'].get('entryRspRestored')is True and p['frame'].get('allWin64IntegerNonvolatilesRestored')is True
            for p in source['programs'])and{(p['existing'],p['wrapperNull'])for p in source['programs']}==
            {(False,False),(True,False),(False,True),(True,True)})


def derive(image,pins,source):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.skill_root_child_bindings import reference_reader_abi
    from scripts.game_data.memorypack.pointer_param import leaf
    require_source(source,pins);life=source['lifecycle'];base=image.pe.image_base
    wrapper,=[w for w in image.memorypack_wrappers.values()if w.name==source['wrapperName']]
    need('root-generated-actual-nominal-wrapper',source['wrappedType'],wrapper.wrapped_type)
    pair=derive_pair(image,source['wrappedType'],wrapper.name)
    adapter=derive_adapter(image,pins,pair,wrapper)
    need('root-generated-same-owned-getter',life['GetValue']['method'],adapter['getterMethod'])
    getter=leaf(image,base+adapter['getterMethod'][3],['488B4110','C3'])
    need('root-generated-same-owned-reader',source['method'],life['readerMethod'])
    reader=reference_reader_abi(image,pins);_publication_gate(image,pins)
    return dict(pair=pair,adapter=adapter,getter=getter,**reader,
        ownConcreteGetterSemanticsProved=True,ownConcreteFactorySemanticsProved=True,childGrammarsAdmitted=False)
