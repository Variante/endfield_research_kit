"""Actual primitive-normalization caller and conditional method-pointer hit.

The full selected current resolver has an independently checked owned CFG and
normal frames. One complete selected original-miss/primitive-normalized-hit
path preserves the incoming method key and output, normalizes the actual class
and method instantiations separately, compares all three pointer keys, and
forwards the selected native registration index triple to its actual pointer
projection helper. The independently checked projection bounds primary and
invoker indices and obtains pointers from the selected published code
registration; an absent adjustor reuses primary. Its invalid branch is checked
as well. Static placeholder registration triples are joined bidirectionally.

The hit path requires coherent initialized interning and method-key tables;
content-equal type records alone cannot satisfy its pointer comparisons. Table
population, startup execution, cache aliases, incoming runtime MethodInfo and
concrete MemoryPack provider/slot5 selection remain separate obligations. This
component does not turn a possible normalized hit into a selected enum wire
grammar or whole owner.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

SCHEMA='endfield.enum-method-pointer-selection.v1'
LABEL='enumMethodPointerSelection'


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def _same_registration(left,right):
    # GenericEntries retains native parsed tuples; composed proofs have crossed
    # the explicit JSON boundary. Normalize representation, never field scope.
    return json.loads(json.dumps(left))==json.loads(json.dumps(right))


def program(regions,entry):
    g=BytesPath(regions,entry)
    g.take('488bc4','48895818','48895010','48894808','55','56','57','4154','4155','4156','4157','4883ec50')
    state=g.relative('488b2d');g.take('0f57c0');other=g.relative('48392d')
    g.take('4d8be0','4d8b30','488bd9','4d8b7808','f30f7f40a0','4c8970a0','4c8978a8','48895098');g.branch('0f84',False)
    g.take('8b4a48','498bc6');capacity=g.relative('488b35');g.take('4533d2')
    slots=g.relative('4c8b1d');empty_key=g.relative('4c8b2d');sentinel=g.relative('488b3d')
    g.take('48c1e803','488d5eff','4803c8','498bc7','4c69c9dba2fa1c','48c1e803','4c03c8','4c23cb',
        '4b8d0449','413b3cc3');g.branch('74',True,1)
    g.take('85ff');g.branch('75',True,1)
    g.take('488d0476','488b9c2490000000','498d14c3','488d0476','498d0cc3','483bd1');g.branch('0f85',False)
    g.take('498b0c24');class_site=g.at;normalizer=g.relative('e8')
    g.take('498b4c2408','4889442428');method_site=g.at
    need('same-actual-class-and-method-normalizer',g.relative('e8')==normalizer)
    need('same-normalized-state-reload',g.relative('488b2d')==state)
    g.take('4c8bf0');need('same-normalized-other-state-compare',g.relative('48392d')==other)
    g.take('4889442430');g.branch('0f84',False)
    g.take('4c8b7c2420','4533d2','488b542428');need('same-normalized-capacity',g.relative('488b35')==capacity)
    g.take('488bc2');need('same-normalized-slots',g.relative('4c8b1d')==slots)
    g.take('418b4f48');need('same-normalized-empty-key',g.relative('4c8b2d')==empty_key)
    need('same-normalized-sentinel',g.relative('488b3d')==sentinel)
    g.take('488d5eff','48c1e803','4803c8','498bc6','4c69c9dba2fa1c','48c1e803','4c03c8','4c23cb',
        '4b8d0449','413b3cc3');g.branch('74',False,1)
    g.take('4885ed');g.branch('0f85',False)
    g.take('4b8d0449','41833cc300');g.branch('0f84',True)
    g.take('498b4cc308','4c3b39');g.branch('0f85',False)
    g.take('483b5108');g.branch('0f85',False)
    g.take('4c3b7110');g.branch('0f85',False)
    g.take('b001','84c0');g.branch('0f84',False)
    g.take('4983f9ff');g.branch('0f84',False)
    g.take('4b8d0449');g.jump('e9')
    g.take('498d14c3','488d0476','498d0cc3','483bd1');g.branch('0f85',True)
    g.take('4533c0','488b5210','488b8c2490000000');projection_site=g.at;projection=g.relative('e8')
    g.take('488b842490000000','488b9c24a0000000','4883c450','415f','415e','415d','415c','5f','5e','5d','c3')
    return dict(selectedBytes=g.seen,stateCell=state,otherStateCell=other,capacityCell=capacity,slotsCell=slots,
        emptyKeyCell=empty_key,sentinelCell=sentinel,entryArguments=dict(rcx='pointer projection output',rdx='method definition key',r8='class/method instantiation pair'),
        originalFirstSlotMustBeEmpty=True,sentinelMustBeNonzero=True,normalizedStateCellMustBeZero=True,
        normalizedSlotState=0,slotBytes=24,slotKeyPointerOffset=8,slotValuePointerOffset=16,
        keyQwordOffsets=[0,8,16],keyValues=['unchanged incoming method key','actual class-normalizer result','actual method-normalizer result'],
        everyKeyPointerComparedExactly=True,pointerComparisonReplacedByTypeContentEquality=False,
        normalizerTarget=normalizer,classNormalizationCall=class_site,methodNormalizationCall=method_site,
        classInstantiationFromInputPairOffset=0,methodInstantiationFromInputPairOffset=8,
        selectedIndexMustNotBeMinusOne=True,selectedSlotMustNotBeCapacityEnd=True,
        projectionTarget=projection,projectionCall=projection_site,projectionFlagLowByte=0,
        projectionInput='same matched slot value pointer',returnedOriginalOutputPointer=True,
        entryRspRestored=True,nonvolatilesRestored=['rbx','rbp','rsi','rdi','r12','r13','r14','r15'],normalReturn=True,
        initializedMethodKeyTableIdentityProved=False)


def registration_alias_program(regions,entry,*,code_registration,metadata_registration):
    """Actual six-instruction publication; aliases share source registers."""
    g=BytesPath(regions,entry)
    need('selected-static-code-registration',g.relative('488d0d')==code_registration);code_cell=g.relative('48890d')
    need('selected-static-metadata-registration',g.relative('488d05')==metadata_registration);metadata_cell=g.relative('488905')
    code_alias=g.relative('48890d');metadata_alias=g.relative('488905')
    need('distinct-declared-registration-cells',len({code_cell,metadata_cell,code_alias,metadata_alias})==4)
    return dict(selectedBytes=g.seen,start=entry,end=g.at,codeRegistrationCell=code_cell,metadataRegistrationCell=metadata_cell,
        codeRegistrationAliasCell=code_alias,metadataRegistrationAliasCell=metadata_alias,
        bothCodeCellsReceiveSameUnchangedSelectedStaticAddress=True,bothMetadataCellsReceiveSameUnchangedSelectedStaticAddress=True,
        opaqueCalls=0,completeStartupControlProved=False,publicationExecutionObserved=False)


def derive(image,pins,*,selection_entry,primitive_entry,**key_arguments):
    from scripts.game_data.il2cpp.enum_source_variants import select
    variant=select(key_arguments.get("enum_variant"))
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.enum_primitive_normalizer_paths import derive as primitive_source
    from scripts.game_data.il2cpp.enum_name_lookup_paths import _owned_graph
    from scripts.game_data.il2cpp.method_carrier_resolution import _project
    from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    _publication_gate(image,pins);base=image.pe.image_base
    primitive=primitive_source(image,pins,entry=primitive_entry,**key_arguments)
    body,graph=_owned_graph(image,selection_entry);source=program(body['regions'],selection_entry)
    need('actual-primitive-normalizer-caller-not-class-normalizer',source['normalizerTarget']==primitive_entry)
    projection,projection_graph=_owned_graph(image,source['projectionTarget'])
    g=BytesPath(projection['regions'],source['projectionTarget']);g.take('48895c2408');cell=g.relative('4c8b1d')
    contract=dict(globals=dict(codeRegistrationCellRva=cell-base),projectionLayout=dict(savedRbxHome=8,
        primaryCount=16,invokerCount=40,primaryPointers=24,adjustorPointers=32,invokerPointers=48))
    from scripts.game_data.il2cpp.enum_underlying_instructions import decode_enum_underlying_instructions
    from scripts.game_data.il2cpp.owned_partition import checked_rows
    rows=[]
    for at,raw in projection['regions']:rows+=checked_rows(decode_enum_underlying_instructions(image.mapper,raw,at),raw,LABEL)
    rows.sort(key=lambda row:int(row['va'],16));projection_program=_project(rows,base,contract)
    fields=primitive['proof']['nameAndInternerSource']['proof']['internerSource']['proof']['placeholderTypeSource']
    keys=fields['proof']['argumentKeySource'];selection=keys['proof']['normalizerSelection']
    publication=selection['proof']['classFieldSource']['proof']['typeDataFixup']['proof']['publicationSlice']
    publication_entry=publication['selectedBytes'][0][0]
    alias=registration_alias_program([(publication_entry,image.pe.bytes_at_va(publication_entry,42))],publication_entry,
        code_registration=image.code_registration,metadata_registration=image.metadata_registration)
    need('same-actual-primary-and-alias-code-registration-publication',
        alias['codeRegistrationCell']==publication['codeRegistrationCell']and cell==alias['codeRegistrationAliasCell'])
    from scripts.game_data.levelscript_two_routes_native import _window
    alias_window=_window(image,publication_entry,alias['end'],'Exact primary/alias registration publication slice; enclosing startup control/execution unproved')
    entries=GenericEntries(image);registered=[]
    for observed in fields['proof']['registeredPlaceholderEntries']:
        owner=observed['formatterType'];selected=entries.resolve(observed['methodDefinition'],[variant['placeholderType']],[])
        need('same-fresh-placeholder-registration:'+owner,_same_registration(selected,observed['registration']))
        indices=selected['registration']['indices'];need('selected-primary-invoker-bounds-and-no-adjustor',
            0<=indices[0]<entries.code['genericMethodPointersCount']<1<<31
            and 0<=indices[1]<entries.code['invokerPointersCount']<1<<31 and indices[2]==-1)
        primary=image.pe.u64_at_va(image.code_registration+24);invoker=image.pe.u64_at_va(image.code_registration+48)
        need('same-selected-code-registration-array-layout',primary==int(entries.code['genericMethodPointers'],16)
            and invoker==int(entries.code['invokerPointers'],16)
            and image.pe.u64_at_va(primary+indices[0]*8)==selected['pointer'])
        registered.append(dict(formatterType=owner,methodDefinition=observed['methodDefinition'],selectedRegistration=selected,
            primaryPointerVa=selected['pointer'],invokerPointerVa=image.pe.u64_at_va(invoker+indices[1]*8),adjustorEqualsPrimary=True,
            actualMethodKeyTableValueIsSelectedTripleProved=False))
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='proved-current-source-only',nativeInputs=pins,
        proof=dict(primitiveNormalizerSource=primitive,selectionWindows=body['windows'],selectionCfg=graph,selectedNormalizedHit=source,
            projectionWindows=projection['windows'],projectionCfg=projection_graph,projectionProgram=projection_program,
            projectionLayout=contract['projectionLayout'],codeRegistrationCellVa=cell,registrationAliasPublication=alias,
            registrationAliasPublicationWindow=alias_window,selectedPlaceholderRegistrations=registered),
        actualPrimitiveNormalizationCallerProved=True,conditionalNormalizedHitPointerProjectionProved=True,
        initializedMethodKeyTableIdentityProved=False,actualConcreteMethodInfoIdentityProved=False,
        concreteEnumCallbackSelected=False,wireGrammarAdmitted=False,wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Full owned selector/projection CFGs and frames, complete selected original-miss/normalized-hit source with all three pointer comparisons, independently byte-proved primary/invoker/adjustor projection and selected static placeholder triples.',
            conditional=__doc__,structuralOnly='Runtime normalized method keys and native pointer triples.',
            unresolved=['static registration to initialized method-key table/population and canonical interner identity',
                'actual incoming nominal MethodInfo/MemoryPack provider and slot5 receiver/callback binding',
                'startup execution/opaque cache aliases','wire framing/parent/EOF']))))
