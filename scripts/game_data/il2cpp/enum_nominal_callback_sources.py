"""Finite conditional nominal enum callback selection, never an Int32 alias.

The reviewed profile supplies selected native helper entry declarations, not a
prevalidated proof. Each derive freshly proves own nominal formatter requests,
ordinary eager registration/registry transport, original type/class/MethodInfo
context transfers, distinct primitive code normalization, selected static
interner/method-table insertion and normalized lookup, slot5 metadata and the
actual selected placeholder callback's complete raw DWORD source program.

The original nominal class and MethodInfo context remain nominal while the
separately selected code pointer can use the exact Int32Enum registration.
Conditions retain coherent initialized original keys and source-selected
canonical interner/method-table state, successful normal helper/cast/lock
effects, the selected ordinary eager formatter and no intervening replacement.
Runtime state, startup execution and replacement behavior are not observed.
The capability proves the callback only under these stated source selections;
an enclosing dispatcher must independently bind its actual callback/pair and
typed nominal context. No List, dictionary, parent or EOF follows from it.
"""
import json

from scripts.game_data.contracts import CONTRACTS_DIR

SCHEMA='endfield.enum-nominal-callback-sources.v1'
PROFILE_SCHEMA='endfield.enum-nominal-callback-profile.v1'
CONTRACT_PATH=CONTRACTS_DIR/'enum_nominal_callbacks_native.json'
LABEL='enumNominalCallbacks'
ENTRY_KEYS={'seedEntryRva','selectionEntryRva','primitiveEntryRva','normalizerEntryRva','placeholderPublicationEntryRva'}
FIXUP_KEYS={'loopTargetRva','recordTargetRva','alternateTargetRva','projectionTargetRva','publicationEntryRva'}
CONDITION_KEYS={'originalNominalFormatterRequired','originalNominalMethodInfoClassAndContextRequired',
    'selectedStaticRegistrationsInitializedRequired','coherentCanonicalInternerAndMethodTableRequired',
    'providerRegistryEagerRegistrationRequired','noInterveningRuntimeFormatterReplacementRequired','actualRuntimeSelectionObserved'}


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def validate_profile(profile,pins,*,reviewed=True):
    need('profile-schema',profile.get('schema')==PROFILE_SCHEMA)
    need('profile-review-state',profile.get('status')in(('reviewed',)if reviewed else('pendingReview','reviewed')))
    need('same-selected-native-inputs',profile.get('nativeInputs')==pins)
    names=profile.get('nominalEnums');need('finite-unique-nominals',type(names)is list and 0<len(names)<=32
        and all(type(n)is str and n for n in names)and names==sorted(set(names)))
    need('exact-ordinary-formatter-slot5-dword-ABI',profile.get('formatterType')=='MemoryPack.Formatters.UnmanagedFormatter`1'
        and profile.get('callbackMethod')=='Deserialize'and type(profile.get('callbackSlot'))is int and profile['callbackSlot']==5
        and type(profile.get('wireBytes'))is int and profile['wireBytes']==4
        and profile.get('readerByref')is True and profile.get('outputByref')is True)
    for role,keys in(('sourceEntries',ENTRY_KEYS),('fixupEntries',FIXUP_KEYS)):
        entries=profile.get(role);need('exact-'+role,type(entries)is dict and set(entries)==keys
            and all(type(v)is int and 0<v<1<<32 for v in entries.values()))
    conditions=profile.get('selectionConditions');need('literal-source-selection-conditions',type(conditions)is dict
        and set(conditions)==CONDITION_KEYS and all(conditions[k]is(k!='actualRuntimeSelectionObserved')for k in CONDITION_KEYS))
    need('explicit-evidence-boundary',type(profile.get('evidenceBoundary'))is dict
        and set(profile['evidenceBoundary'])=={'exact','conditional','structuralOnly','unresolved'})
    return profile


def _nodes(value,schema):
    found=[]
    def visit(node):
        if type(node)is dict:
            if node.get('schema')==schema and not any(node==old for old in found):found.append(node)
            for child in node.values():visit(child)
        elif type(node)is list:
            for child in node:visit(child)
    visit(value);need('one-fresh-source-node-'+schema+': count='+str(len(found)),len(found)==1);return found[0]


def _derive_on_profile(image,pins,profile):
    """Candidate helper: a profile declaration is always re-proved, never trusted."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.enum_registry_publication_paths import derive as registry_source
    from scripts.game_data.il2cpp.enum_method_rgctx_paths import derive as context_source
    from scripts.game_data.il2cpp.enum_placeholder_callback_paths import derive as callback_source
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.formatter_composition import _vtable
    from scripts.game_data.il2cpp import enum_method_pointer_selection as selection_owner
    from scripts.game_data.il2cpp import enum_method_table_seed_paths as seed_owner
    from scripts.game_data.il2cpp import enum_method_table_insertion_paths as insertion_owner
    from scripts.game_data.il2cpp import enum_inflated_method_class_paths as original_owner
    _publication_gate(image,pins);validate_profile(profile,pins,reviewed=False);base=image.pe.image_base
    registry=registry_source(image,pins,enum_types=profile['nominalEnums'])
    nominal=registry['proof']['nominalRegistrationSource']['proof']['nominals']
    requests=[(name,nominal[name]['typedUsages']['constructor'])for name in profile['nominalEnums']]
    entries=profile['sourceEntries'];fixup=profile['fixupEntries']
    source_arguments=dict(seed_entry=base+entries['seedEntryRva'],
        selection_entry=base+entries['selectionEntryRva'],primitive_entry=base+entries['primitiveEntryRva'],
        normalizer_entry=base+entries['normalizerEntryRva'],publication_entry=base+entries['placeholderPublicationEntryRva'],
        enum_requests=requests,fixup_arguments=dict(loop_target=base+fixup['loopTargetRva'],
            record_target=base+fixup['recordTargetRva'],alternate_target=base+fixup['alternateTargetRva'],
            projection_target=base+fixup['projectionTargetRva'],publication_entry=base+fixup['publicationEntryRva']))
    chain=context_source(image,pins,**source_arguments)
    insertion=insertion_owner.derive(image,pins,**source_arguments)
    callback=callback_source(image,pins);proof=callback['proof'];method=proof['methodDefinition']
    ctx=NativeReferenceContext(image);formatter=ctx.index.types[profile['formatterType']]
    _vtable(image,formatter.index,5,method,LABEL)
    selection=_nodes(chain,selection_owner.SCHEMA);seed=_nodes(chain,seed_owner.SCHEMA)
    original=_nodes(chain,original_owner.SCHEMA)
    need('same-independent-selected-method-table-seed',insertion['proof']['methodTableSeedSource']==seed)
    selected=[r for r in selection['proof']['selectedPlaceholderRegistrations']
        if r['formatterType']==profile['formatterType']and r['methodDefinition']==method]
    need('one-exact-callback-code-registration',len(selected)==1);selected,=selected
    need('same-independent-code-registration-and-slot5-source',selected['selectedRegistration']==proof['registration']
        and selected['primaryPointerVa']==proof['registration']['pointer'])
    seeded=[r for r in seed['proof']['selectedStaticMethodRows']if r['methodDefinition']==method]
    need('same-static-methodspec-instantiation-and-triple',len(seeded)==1
        and seeded[0]['methodSpecIndex']==proof['registration']['methodSpecIndex']
        and seeded[0]['actualClassInstantiationPointer']==proof['registration']['classInstantiation']['record_va']
        and seeded[0]['actualMethodInstantiationPointer']is None)
    need('same-original-definition-ABI-and-separate-code-context',any(
        r['methodDefinition']==method and r['declaringType']==formatter.index and r['parameterCount']==2
        for r in original['proof']['intendedPlaceholderDefinitions']))
    need('actual-selected-table-insertion-and-key-retention',insertion['actualSelectedKeyTripleInsertionAndEqualKeyRetentionProved']is True)
    need('same-original-provider-lazy-context-entry',
        registry['proof']['selectedGenericProvider']['actualMethodContextInitializer']==chain['proof']['selectedColdProvider']['actualMethodContextInitializer'])
    _publication_gate(image,pins)
    conditions=[
        'Original allocated ordinary UnmanagedFormatter<the exact nominal enum> is registered and selected; no intervening runtime replacement.',
        'Actual callback MethodInfo has that original nominal class/instantiation and the selected Deserialize definition; original contexts are coherent and initialized.',
        'Selected static metadata/code registrations and loaded metadata agree; normal selected startup/fixup/seed paths have completed.',
        'The source-proved canonical instantiation and method-key insertion/lookup paths select the declared static registration row; coherent tables/interner and stable disjoint storage are required.',
        'The proved nominal registry insertion/hit source and compatible normal allocation, lock, cleanup, hash, equality, class/RGCTX and cast effects hold; collector is disabled on the selected paths.',
        'Actual enclosing dispatcher independently binds this callback target and original MethodInfo pair to its typed nominal request.'
    ]
    caps={name:dict(schema=SCHEMA,status='validated-conditional-callback',nativeInputs=pins,typeName=name,
        typeDefinition=nominal[name]['typeDefinition'],wireBytes=4,callbackTargetRva=proof['registration']['pointer']-base,
        formatterType=profile['formatterType'],formatterMethodDefinition=method,callbackSlot=5,
        readerByref=True,outputByref=True,conditions=conditions,actualRuntimeSelectionObserved=False,
        unconditionalCallbackSelectionProved=False,parentOrCollectionGrammarAdmitted=False,
        evidenceBoundary=dict(exact='Fresh exact nominal request/metadata, own formatter slot5/VAR ABI and complete raw DWORD callback; source-joined selected normalizer/registration/MethodInfo/registry paths.',
            conditional=__doc__,structuralOnly='Original nominal context and separately selected code pointer.',
            unresolved=['actual runtime state and replacement','nonselected source/cache/collector paths','enclosing parent/collection/EOF']))
        for name in profile['nominalEnums']}
    return dict(schema=SCHEMA,status='validated-conditional-callback-sources',nativeInputs=pins,capabilities=caps,
        proof=dict(nominalRegistrySource=registry,normalizationClassMethodAndContextSource=chain,
            methodTableInsertionSource=insertion,selectedCallbackSource=callback,selectedCallbackMethodRow=seeded[0]),
        actualRuntimeSelectionObserved=False,wholeOwnerAdmitted=False,evidenceBoundary=profile['evidenceBoundary'])


def derive(image,pins,*,type_name):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    _publication_gate(image,pins)
    try:profile=json.loads(CONTRACT_PATH.read_bytes())
    except OSError as error:raise ValueError(LABEL+'.reviewed-profile-missing')from error
    validate_profile(profile,pins);need('explicit-reviewed-nominal',type_name in profile['nominalEnums'])
    result=_derive_on_profile(image,pins,profile)
    return dict(schema=SCHEMA,status=result['status'],nativeInputs=pins,capability=result['capabilities'][type_name],
        proof=result['proof'],evidenceBoundary=result['evidenceBoundary'])
