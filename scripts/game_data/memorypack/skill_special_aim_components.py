"""Finite SpecialAim union with its independently source-proved sector.

The parent calls ReadPackable of the concrete wrapper, so no unused concrete
Original adapter is required. Its typed cache/factory/GetValue must agree with
the inherited base holder and conversion. Two ordinary BlackboardDouble fields
retain their exact independent wire/Reader identities. The abstract-base list
has its own count/callback/Add induction; an abstract constructor is never
claimed as a concrete factory. Runtime provider/compatible callback choice,
normal typed allocation/helpers, disabled collector and disjoint stable
buffered storage remain conditions. No enclosing action/root/EOF is admitted.
"""
import json

from scripts.game_data.memorypack.skill_root_child_bindings import need
from scripts.game_data.memorypack.skill_special_aim_union_sources import TYPE,WRAPPER,CHILD,CHILD_WRAPPER

CAPABILITY='skill-special-aim-shape-edit'
SECTOR='skill-special-aim-sector'
LIST='skill-action-special-aim-shape-list'
DOUBLE='Beyond.Blackboard+BlackboardDouble'
ORDER=[dict(memberIndex=i,fieldName=n,kind=k,childCapability=c)for i,n,k,c in(
    (0,'forwardType','scalar32',None),(1,'angle','blackboard-double','scalar-payload'),
    (2,'radius','blackboard-double','scalar-payload'))]


def bind_sector(pins,union,source,compiled):
    need('SpecialAim-own-transport',True,union.get('schema')=='endfield.skill-special-aim-union-sources.v1'
        and union.get('status')=='validated-conditional-special-aim-union-caller'and union.get('nativeInputs')==pins
        and(union.get('typeName'),union.get('wrapperName'),union.get('childTypeName'),union.get('childWrapperName'))==
            (TYPE,WRAPPER,CHILD,CHILD_WRAPPER)
        and union.get('baseGetterSemanticsAdmitted')is True and all(union.get(k)is False for k in
            ('concreteGetterSemanticsAdmitted','concreteFactorySemanticsAdmitted','concreteChildGrammarAdmitted','wholeUnionAdmitted','wholeOwnerAdmitted')))
    positive=union['proof']['positive']
    need('SpecialAim-actual-tag0-null-output',True,type(positive.get('tag'))is int and positive['tag']==0
        and positive.get('outputInitiallyNull')is True and positive.get('normalReturn')is True
        and positive.get('existingOutputByrefPathAdmitted')is False
        and union['proof']['typedRequest'].get('methodArguments')==[CHILD_WRAPPER])
    need('SpecialAim-own-complete-sector-source',True,source.get('schema')=='endfield.generated-concrete-reader-source.v1'
        and source.get('nativeInputs')==pins and(source.get('wrappedType'),source.get('wrapperName'))==(CHILD,CHILD_WRAPPER)
        and source.get('completeSelectedCallerAdmitted')is True and source.get('childGrammarAdmitted')is False
        and source.get('wholeOwnerAdmitted')is False)
    need('SpecialAim-sector-named-order',[(n,t)for n,t in(('forwardType','Beyond.Gameplay.Core.BattleManager+SpecialAimForwardType'),
        ('angle',DOUBLE),('radius',DOUBLE))],[(r['fieldName'],r['declaredType'])for r in source['orderedSourceReads']])
    need('SpecialAim-sector-wire-program',True,type(compiled.get('memberCount'))is int and compiled['memberCount']==3
        and compiled.get('reads')==ORDER and all(type(r.get('memberIndex'))is int for r in compiled['reads'])
        and compiled.get('requiredCapabilities')==['scalar-payload'])
    life=source['lifecycle'];getter=life.get('coherentGetter',{})
    need('SpecialAim-same-inherited-holder-and-own-cache',True,life.get('baseHolder')==[WRAPPER,TYPE,16]
        and life.get('typedCache')==[CHILD_WRAPPER,CHILD,24]
        and getter.get('baseHolder')==life['baseHolder']and getter.get('typedCache')==life['typedCache']
        and getter.get('coherentNonNullSamePointerReturn')is True)
    need('SpecialAim-own-typed-GetValue',True,life['GetValue']['method'][1:3]==[CHILD_WRAPPER,'GetValue']
        and life['concreteFormatter']['method'][0]>=0 and life.get('originalRegistrationRequired')is False)
    paths=source['programs']
    need('SpecialAim-sector-complete-four-frames',True,len(paths)==4 and all(type(p.get('existing'))is bool
        and type(p.get('wrapperNull'))is bool and p.get('frame',{}).get('entryRspRestored')is True
        and p['frame'].get('allWin64IntegerNonvolatilesRestored')is True for p in paths)
        and{(p['existing'],p['wrapperNull'])for p in paths}=={(False,False),(True,False),(False,True),(True,True)})
    factories=life.get('factories',[])
    need('SpecialAim-both-own-concrete-factories',True,len(factories)==2
        and{f['method'][2]for f in factories}=={'.ctor','CreateInstance'}
        and all(f.get('originalAllocation',{}).get('typeName')==CHILD for f in factories))
    return dict(typeName=CHILD,wrapperName=CHILD_WRAPPER,memberCount=3,orderedReads=ORDER,nullable=True,nullMarker=255,
        nullAdmitted=True,wholeGrammarAdmitted=True,ownConcreteGetterSemanticsProved=True,
        ownConcreteFactorySemanticsProved=True,generatedWrapperOnly=True,ordinaryOriginalReadValueAdmitted=False,
        callbackSelectionConditional=True,wholeOwnerAdmitted=False)


def _derive_on_double(image,pins,double):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack.skill_special_aim_union_sources import derive as union_source
    from scripts.game_data.memorypack.generated_reader_sources import derive as sector_source
    from scripts.game_data.memorypack.generated_record_components import compile_member_program
    from scripts.game_data.memorypack.skill_root_child_bindings import reference_reader_abi
    _publication_gate(image,pins);union=union_source(image,pins);source=sector_source(image,pins,CHILD_WRAPPER)
    requests={r['memberIndex']:derive_typed_usage_context(image,r['context']['instructionRva'],label='SpecialAim.sector')
        for r in source['orderedSourceReads']if r['declaredType']==DOUBLE}
    compiled,pending=compile_member_program(source,pins,wrapper_name=CHILD_WRAPPER,type_name=CHILD,value4={},
        references={DOUBLE:('skill-blackboard-double','blackboard-double','scalar-payload')},
        reference_children={DOUBLE:double},typed_requests=requests)
    need('SpecialAim-two-complete-ordinary-double-joins',[],pending);sector=bind_sector(pins,union,source,compiled)
    need('SpecialAim-two-exact-typed-field-bindings',['angle','radius'],[b['fieldName']for b in compiled['childBindings']])
    reader=reference_reader_abi(image,pins);cap=dict(typeName=TYPE,wrapperName=WRAPPER,nullable=True,nullMarker=255,
        nullAdmitted=True,wholeGrammarAdmitted=True,ordinaryOriginalReadValueAdmitted=True,
        baseGetterSemanticsProved=True,concreteChildGrammarsProved=True,allConcreteFactoriesProved=True,
        supportedShortTags=[0],extendedTagsAdmitted=False,reservedMarkersAdmitted=False,
        routes=[dict(tag=0,wrappedType=CHILD,wrapperName=CHILD_WRAPPER,childCapability=SECTOR)],
        **{k:reader[k]for k in('referenceReaderMethodDefinition','referenceReaderTargetRva')},
        callbackSelectionConditional=True,wholeOwnerAdmitted=False)
    scalar=double['capabilities']['skill-blackboard-double']
    identity={k:scalar[k]for k in('typeName','referenceReaderMethodDefinition','referenceReaderTargetRva')}
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-special-aim-components.v1',status='validated-conditional-special-aim-union',
        nativeInputs=pins,capabilities={CAPABILITY:cap,SECTOR:sector},requiredExternalCapabilities=['scalar-payload'],
        requiredExternalCapabilityIdentities={'scalar-payload':identity},proof=dict(union=union,sector=source,
            compiled=compiled,typedRequests=requests,blackboardDouble=double,referenceReaders=reader),wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Own abstract union tag0/FF, complete concrete sector source/lifecycle and independent angle/radius ordinary Double joins, inherited base-interface conversion and actual reference Reader.',
            conditional=__doc__,structuralOnly='Stored authored aim-shape configuration.',
            unresolved=['actual parent list/action/root/EOF','existing-output union alternative','runtime aim/provider selection']))))


def derive(image,pins):
    from scripts.game_data.memorypack.skill_blackboard_double_sources import derive as child
    return _derive_on_double(image,pins,child(image,pins))
