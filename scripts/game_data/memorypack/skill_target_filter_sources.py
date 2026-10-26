"""Own ordinary TargetFilter source, with a separately framed managed Query.

Complete generated new/existing/FF callers, all field stores and frames, own
factory/GetValue and canonical ordinary adapter precede admission. The Query
member has a managed sixteen-byte transfer and an independent MC2/tag-array
wire grammar; neither that size nor another filter's layout supplies bytes.
Matching initialized contexts/callbacks, coherent compatible originals, normal
typed allocation/helpers, disabled collector and disjoint stable storage remain
conditions. This proves stored configuration, not filtering, provider choice,
an enclosing action, root or physical EOF.
"""
import json

from scripts.game_data.memorypack.skill_root_child_bindings import need

TYPE='Beyond.Gameplay.Core.TargetFilter'
WRAPPER='Beyond.MemoryPack.Beyond_Gameplay_Core_TargetFilterForMemoryPack'
CAPABILITY='skill-action-target-filter'
QUERY='Beyond.Gameplay.Core.GameplayTagQuery'
QUERY_CAP='skill-root-gameplay-tag-query'
MEMBERS=(('autoSetTargetFaction','bool','bool-byte'),('checkAlive','bool','bool-byte'),
    ('factionTarget','Beyond.Gameplay.Core.FactionTarget','scalar32'),('filterGameplayTag','bool','bool-byte'),
    ('filterObjectType','bool','bool-byte'),('filterSlot','bool','bool-byte'),
    ('objectType','Beyond.Gameplay.Core.ObjectType','scalar32'),('slotIndex','int','scalar32'),
    ('tagQuery',QUERY,'root-record'),('targetFactionType','Beyond.Gameplay.Core.FactionType','scalar32'))
ORDER=[dict(memberIndex=i,fieldName=n,kind=k,childCapability=QUERY_CAP if t==QUERY else None)
    for i,(n,t,k)in enumerate(MEMBERS)]


def require_source(source,pins):
    need('TargetFilter-own-complete-source',True,source.get('schema')=='endfield.generated-concrete-reader-source.v1'
        and source.get('nativeInputs')==pins and(source.get('wrappedType'),source.get('wrapperName'))==(TYPE,WRAPPER)
        and source.get('completeSelectedCallerAdmitted')is True and source.get('childGrammarAdmitted')is False
        and source.get('wholeOwnerAdmitted')is False)
    need('TargetFilter-exact-named-members',[(n,t)for n,t,k in MEMBERS],
        [(r['fieldName'],r['declaredType'])for r in source['orderedSourceReads']])
    life=source['lifecycle']
    need('TargetFilter-own-getter-profile',True,life.get('directHolderMode')is True
        or(life.get('coherentGetter')or{}).get('coherentNonNullSamePointerReturn')is True)
    paths=source['programs']
    need('TargetFilter-all-four-return-frames',True,len(paths)==4 and all(type(p.get('existing'))is bool
        and type(p.get('wrapperNull'))is bool and p.get('frame',{}).get('entryRspRestored')is True
        and p['frame'].get('allWin64IntegerNonvolatilesRestored')is True for p in paths)
        and{(p['existing'],p['wrapperNull'])for p in paths}=={(False,False),(True,False),(False,True),(True,True)})


def bind_program(compiled):
    need('TargetFilter-literal-complete-count',True,type(compiled.get('memberCount'))is int and compiled['memberCount']==10)
    need('TargetFilter-exact-source-wire-order',True,compiled.get('reads')==ORDER
        and all(type(r.get('memberIndex'))is int for r in compiled['reads']))
    need('TargetFilter-exact-independent-query-scope',[QUERY_CAP],compiled.get('requiredCapabilities'))
    bindings=compiled.get('childBindings',[])
    need('TargetFilter-own-query-field-transfer',True,len(bindings)==1 and bindings[0].get('fieldName')=='tagQuery'
        and bindings[0].get('typeName')==QUERY and bindings[0].get('capability')==QUERY_CAP
        and bindings[0].get('ordinaryReferenceIdentityClaimed')is False)
    return ORDER


def _derive_on_source(image,pins,source):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack.generated_record_components import compile_member_program
    from scripts.game_data.memorypack.skill_action_managed_value_bindings import TYPES,bind,require_wire_capability
    from scripts.game_data.memorypack.skill_root_tag_query_components import derive as query_source
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.skill_root_child_bindings import reference_reader_abi
    _publication_gate(image,pins);require_source(source,pins);read=source['orderedSourceReads'][8]
    need('TargetFilter-own-managed-Query-source',True,read['kind']=='managed:'+QUERY)
    actual=source['sourceScope']['managedValueSources']['8']
    usage=derive_typed_usage_context(image,read['context']['instructionRva'],label='TargetFilter.Query')
    need('TargetFilter-actual-owned-request',usage,actual['proof']['typedRequest'])
    query=query_source(image,pins,typed_request=usage,
        dispatcher_target=image.pe.image_base+actual['proof']['adapter']['dispatcherTargetRva'])
    query_cap=require_wire_capability(query,pins,QUERY,QUERY_CAP)
    compiled,pending=compile_member_program(source,pins,wrapper_name=WRAPPER,type_name=TYPE,value4={},
        typed_requests={8:usage},typed_values={QUERY:TYPES[QUERY]},value_children={8:query},value_binder=bind)
    need('TargetFilter-all-source-and-query-joins',[],pending);order=bind_program(compiled)
    wrapper,=[w for w in image.memorypack_wrappers.values()if w.name==WRAPPER]
    pair=derive_pair(image,TYPE,WRAPPER,owned_getter_family=source['lifecycle'].get('directHolderMode')is not True)
    adapter=derive_adapter(image,pins,pair,wrapper)
    need('TargetFilter-own-canonical-GetValue',source['lifecycle']['GetValue']['method'],adapter['getterMethod'])
    need('TargetFilter-own-canonical-reader',source['method'],adapter['pairForwarder']['readerMethod'])
    reader=reference_reader_abi(image,pins)
    cap=dict(typeName=TYPE,wrapperName=WRAPPER,memberCount=10,orderedReads=order,nullable=True,nullMarker=255,
        nullAdmitted=True,wholeGrammarAdmitted=True,ordinaryOriginalReadValueAdmitted=True,
        ownConcreteGetterSemanticsProved=True,ownConcreteFactorySemanticsProved=True,completeSourceOwnedProgram=True,
        callbackSelectionConditional=True,wholeSkillDataAdmitted=False,
        **{k:reader[k]for k in('referenceReaderMethodDefinition','referenceReaderTargetRva')})
    caps=dict(query['capabilities']);caps[CAPABILITY]=cap
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-target-filter-sources.v1',
        status='validated-conditional-target-filter',nativeInputs=pins,capabilities=caps,
        requiredExternalCapabilities=[QUERY_CAP],requiredExternalManagedValueIdentities={QUERY_CAP:query_cap},
        proof=dict(source=source,compiled=compiled,query=query,typedRequest=usage,pair=pair,adapter=adapter,referenceReader=reader),
        wholeOwnerAdmitted=False,evidenceBoundary=dict(
            exact='Own complete ten-member generated source and frames, actual Query managed transfer/Reader/dispatcher and independent Query/tag-array wire grammar, own factory/GetValue/canonical ordinary adapter.',
            conditional=__doc__,structuralOnly='Stored target-filter configuration.',
            unresolved=['actual enclosing action/union/root/EOF','runtime filtering and provider choice','cold/refill/error paths']))))


def derive(image,pins):
    from scripts.game_data.memorypack.generated_reader_sources import derive as caller
    from scripts.game_data.memorypack.target_filter_factory_sources import prove
    return _derive_on_source(image,pins,caller(image,pins,WRAPPER,direct_factory_prover=prove))
