"""Own current DamageAction.HitEnvData ordinary-reference source and grammar.

The selected MC4 source stores an unchanged Int64 mask, two bool bytes and the
actual nominal CalculationBase reference. Named fields, complete new/existing
and FF source/frame paths, own holder16 getter/factory, ordinary canonical
adapter and actual Reader MethodSpec/E8 are independently joined. Calculation
routes retain their own finite source and element semantics; no evaluated hit
or damage behavior follows. Initialized coherent callbacks, normal compatible
typed allocation/helpers, disabled collector and disjoint buffered storage are
conditions. Runtime selection/evaluation, malformed/refill paths and enclosing
DamageAction/SkillData/physical EOF remain unresolved.
"""
import json

from scripts.game_data.memorypack.skill_root_child_bindings import need

TYPE='Beyond.Gameplay.Core.DamageAction+HitEnvData'
WRAPPER='Beyond.MemoryPack.Beyond_Gameplay_Core_DamageAction_HitEnvDataForMemoryPack'
CAPABILITY='skill-hit-env-data'
CALCULATION='Beyond.Gameplay.Core.CalculationBase'
CHILD='damage-calculation-union'
ORDER=[dict(memberIndex=i,fieldName=name,kind=kind,childCapability=child)for i,(name,kind,child)in enumerate((
    ('damageDecorateMask','scalar64-bits',None),('dontHitImportInteractive','bool-byte',None),
    ('inheritFirstDamageMask','bool-byte',None),('valueCalculation','damage-union',CHILD)))]


def require_source(source,pins):
    need('hit-env-nominal-source',True,source.get('schema')=='endfield.generated-concrete-reader-source.v1'
        and source.get('nativeInputs')==pins and source.get('wrappedType')==TYPE and source.get('wrapperName')==WRAPPER
        and source.get('completeSelectedCallerAdmitted')is True and source.get('childGrammarAdmitted')is False
        and source.get('wholeOwnerAdmitted')is False)
    need('hit-env-actual-field-order',[(n,t)for n,t in(('damageDecorateMask','long'),('dontHitImportInteractive','bool'),
        ('inheritFirstDamageMask','bool'),('valueCalculation',CALCULATION))],
        [(r['fieldName'],r['declaredType'])for r in source['orderedSourceReads']])
    life=source['lifecycle']
    need('hit-env-plain-owned-holder',True,life.get('directHolderMode')is True and life.get('typedCache')is None
        and life.get('baseHolder')==[WRAPPER,TYPE,16])
    paths=source['programs']
    need('hit-env-all-source-paths',True,len(paths)==4 and all(type(p.get('existing'))is bool
        and type(p.get('wrapperNull'))is bool and p.get('frame',{}).get('entryRspRestored')is True
        and p['frame'].get('allWin64IntegerNonvolatilesRestored')is True for p in paths)
        and{(p['existing'],p['wrapperNull'])for p in paths}=={(False,False),(True,False),(False,True),(True,True)})


def bind_program(compiled):
    need('hit-env-literal-count',True,type(compiled.get('memberCount'))is int and compiled['memberCount']==4)
    need('hit-env-exact-compiled-program',True,compiled.get('reads')==ORDER
        and all(type(r.get('memberIndex'))is int for r in compiled['reads']))
    need('hit-env-exact-child-domain',[CHILD],compiled['requiredCapabilities'])
    return ORDER


def _derive_on_calculation(image,pins,calculation):
    """Internal same-image composition; caller freshly derives finite calculation."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.generated_reader_sources import derive as caller_source
    from scripts.game_data.memorypack.generated_record_components import compile_member_program
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.pointer_param import leaf
    from scripts.game_data.memorypack.skill_root_child_bindings import reference_reader_abi
    _publication_gate(image,pins);source=caller_source(image,pins,WRAPPER);require_source(source,pins)
    read=source['orderedSourceReads'][3]
    usage=derive_typed_usage_context(image,read['context']['instructionRva'],label='skillHitEnvSources')
    compiled,pending=compile_member_program(source,pins,wrapper_name=WRAPPER,type_name=TYPE,value4={},
        references={CALCULATION:(CHILD,'damage-union',CHILD)},reference_children={CALCULATION:calculation},typed_requests={3:usage})
    need('hit-env-no-pending-calculation',[],pending);order=bind_program(compiled)
    wrapper,=[w for w in image.memorypack_wrappers.values()if w.name==WRAPPER]
    pair=derive_pair(image,TYPE,WRAPPER);adapter=derive_adapter(image,pins,pair,wrapper)
    need('hit-env-own-adapter-GetValue',source['lifecycle']['GetValue']['method'],adapter['getterMethod'])
    need('hit-env-own-adapter-reader',source['method'],adapter['pairForwarder']['readerMethod'])
    getter=leaf(image,image.pe.image_base+adapter['getterMethod'][3],['488B4110','C3'])
    reader=reference_reader_abi(image,pins);child=calculation['capabilities'][CHILD]
    identity={key:child[key]for key in('typeName','referenceReaderMethodDefinition','referenceReaderTargetRva')}
    cap=dict(typeName=TYPE,wrapperName=WRAPPER,memberCount=4,nullMarker=255,nullWireBytes=1,nullable=True,nullAdmitted=True,
        wholeGrammarAdmitted=True,ordinaryOriginalReadValueAdmitted=True,ownConcreteGetterSemanticsProved=True,
        ownConcreteFactorySemanticsProved=True,orderedReads=order,completeSourceOwnedProgram=True,
        **{key:reader[key]for key in('referenceReaderMethodDefinition','referenceReaderTargetRva')},
        callbackSelectionConditional=True,wholeDamageActionAdmitted=False,wholeSkillDataAdmitted=False)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-hit-env-sources.v1',status='validated-conditional-hit-env-data',
        nativeInputs=pins,capabilities={CAPABILITY:cap},requiredExternalCapabilities=[CHILD],
        requiredExternalCapabilityIdentities={CHILD:identity},proof=dict(source=source,compiled=compiled,
            pair=pair,adapter=adapter,getter=getter,referenceReaders=reader,calculation=calculation,typedRequest=usage),
        wholeDamageActionAdmitted=False,wholeSkillDataAdmitted=False,evidenceBoundary=dict(
            exact='Named Int64/bool/bool/calculation MC4 complete source/new/existing/FF/frame, own plain holder16 lifecycle and canonical ordinary reference source, exact selected CalculationBase MethodSpec/E8 and finite child grammar.',
            conditional=__doc__,structuralOnly='Stored environment-hit configuration.',
            unresolved=['actual enclosing DamageAction/list/union joins','runtime hit/damage evaluation/provider choice','cold/refill/error paths','whole SkillData/physical EOF']))))


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.skill_damage_union_components import derive as calculation_source
    _publication_gate(image,pins);source=calculation_source(image,pins)
    return _derive_on_calculation(image,pins,dict(nativeInputs=pins,
        capabilities={CHILD:source['families']['CalculationBase']},proof=source))
