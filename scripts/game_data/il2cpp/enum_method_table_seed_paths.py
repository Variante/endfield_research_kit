"""Actual MethodSpec-to-key and generic-method table seed transfers.

The selected seed program visits current generic-method registration rows in
order. It resolves each row's MethodSpec, constructs a tag-zero key/value pair
from the returned method key and that same row's index triple, and calls the
actual method-table insertion entry. The independently selected cold
MethodSpec resolver reads a twelve-byte record, loads its actual class-inst
pointer from the registration pointer array, keeps the -1 method-inst null,
and passes those exact arguments with the method-definition resolver's result
to its actual key constructor. It publishes the unchanged result at the same
MethodSpec cache index. Separate hot-cache source stays explicit.

Complete source partitions/CFGs/frames and exact static placeholder rows are
checked. Reservation/insertion semantics, key-constructor/cache coherence,
method-definition descriptor construction, startup execution and actual
MemoryPack receiver/MethodInfo callback selection remain open. This is source
composition, not a concrete enum formatter or collection grammar admission.
"""
import json
import struct

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

SCHEMA='endfield.enum-method-table-seed-paths.v1'
LABEL='enumMethodTableSeedPaths'


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def seed_program(regions,entry):
    g=BytesPath(regions,entry);g.take('48895c2418','55','4883ec60');marker=g.relative('803d')+1;g.take('00')
    registration=g.relative('488b0d');g.take('48635920');g.branch('0f85',False)
    g.take('85db');g.branch('0f84',False)
    occupied=g.relative('4c8b05');g.take('493bd8');g.branch('76',False,1)
    g.take('488bd3','492bd0');reserve=g.relative('e8');need('same-registration-after-reservation',g.relative('488b0d')==registration)
    g.take('33ed','8bdd','395920');g.branch('7e',False,1)
    g.take('4889742470','8bf5','48897c2478','0f1f00');iteration=g.at
    g.take('488b7928','8b0c37');key_site=g.at;key=g.relative('e8')
    g.take('488d4e04','896c2420','4803cf','4889442428','4c8d442420','48894c2430','488d542438')
    insert_site=g.at;insert=g.relative('e8');need('same-registration-after-insertion',g.relative('488b0d')==registration)
    g.take('488d7610','ffc3','3b5920');back=g.relative('7c',1);need('same-counted-registration-backedge',back==iteration)
    g.take('488b7c2478','488b742470','488b9c2480000000','4883c460','5d','c3')
    return dict(selectedBytes=g.seen,markerCell=marker,markerByteMustBeZero=True,registrationCell=registration,
        occupiedCountCell=occupied,reserveTarget=reserve,reservationNormalReturnRequired=True,
        rowCountOffset=32,rowTableOffset=40,rowBytes=16,methodSpecIndexOffset=0,indexTripleOffset=4,
        initialCounter=0,counterRegister='ebx',initialByteCursor=0,byteCursorRegister='esi',counterStep=1,byteCursorStep=16,
        methodKeyTarget=key,methodKeyCall=key_site,methodKeyEcx='current row MethodSpec index',
        insertionTarget=insert,insertionCall=insert_site,pairTag=0,pairKeyOffset=8,pairValueOffset=16,
        pairKey='unchanged actual method-key resolver result',pairValue='address of same current row +4 index triple',
        entryRspRestored=True,nonvolatilesRestored=['rbx','rbp','rsi','rdi'],normalReturn=True,
        wholeInitializedMethodTableProved=False)


def key_program(regions,entry,*,cold=True):
    need('literal-key-cache-path',type(cold)is bool);g=BytesPath(regions,entry)
    g.take('4053','4883ec20');cache=g.relative('488b05');g.take('4863d9','48833cd800');g.branch('75',not cold,1)
    facts={}
    if cold:
        registration=g.relative('488b05');g.take('488d145b','48897c2430','488b4848','488d3c91','8b0c91')
        method_definition=g.relative('e8');g.take('33d2','4c8bc8','837f04ff','448bc2')
        need('same-registration-for-closed-class-inst',g.relative('488b05')==registration)
        g.branch('74',False,1)
        g.take('48635704','488b4818','488b14d1','837f08ff');g.branch('74',True,1)
        g.take('498bc9');construct=g.relative('e8');need('same-key-result-cache-publication',g.relative('488b0d')==cache)
        g.take('488b7c2430','488904d9');need('same-key-result-cache-return',g.relative('488b05')==cache)
        facts=dict(registrationCell=registration,methodSpecPointerOffset=72,methodSpecBytes=12,
            methodDefinitionIndexOffset=0,classInstantiationIndexOffset=4,methodInstantiationIndexOffset=8,
            classInstantiationMustNotBeMinusOne=True,methodInstantiationMustBeMinusOne=True,
            instantiationTableOffset=24,pointerStride=8,methodDefinitionTarget=method_definition,keyConstructorTarget=construct,
            constructorArguments=dict(rcx='actual method-definition resolver result',rdx='actual registered class-inst pointer',r8=0),
            unchangedKeyConstructorResultStoredAtSameSpecIndex=True,coherentNormalKeyConstructorRequired=True)
    g.take('488b04d8','4883c420','5b','c3')
    return dict(selectedBytes=g.seen,cold=cold,cacheCell=cache,cachePointerStride=8,
        returnedValue='fresh cache[signed incoming MethodSpec index]',validSpecIndexRequired=True,
        cacheAndOpaqueAliasesMustRemainCoherent=True,normalReturn=True,entryRspRestored=True,
        nonvolatilesRestored=['rbx','rdi']if cold else['rbx'],**facts)


def derive(image,pins,*,seed_entry,selection_entry,primitive_entry,**key_arguments):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.enum_instantiation_seed_paths import derive as argument_seed_source,_complete_family
    from scripts.game_data.il2cpp.enum_class_field_paths import unique
    _publication_gate(image,pins);base=image.pe.image_base
    prior=argument_seed_source(image,pins,selection_entry=selection_entry,primitive_entry=primitive_entry,**key_arguments)
    body,rows,graph,padding=_complete_family(image,seed_entry);source=seed_program(body['regions'],seed_entry)
    selection=prior['proof']['methodSelectionSource'];publication=selection['proof']['registrationAliasPublication']
    need('same-selected-primary-metadata-registration-cell',source['registrationCell']==publication['metadataRegistrationCell'])
    resolver,resolver_rows,resolver_graph,resolver_padding=_complete_family(image,source['methodKeyTarget'])
    keys=[key_program(resolver['regions'],resolver['pointer'],cold=cold)for cold in(False,True)]
    need('same-cold-key-metadata-registration',keys[1]['registrationCell']==source['registrationCell'])
    insertion,insert_rows,insert_graph,insert_padding=_complete_family(image,source['insertionTarget'])
    # This is an actual same-table source join, not an admission of its still
    # unproved reservation/resize/key-construction/insertion semantics.
    site=unique(insertion['regions'],bytes.fromhex('4c8b1d'))
    g=BytesPath(insertion['regions'],site);slots=g.relative('4c8b1d')
    need('actual-insertion-and-selection-share-table-storage',slots==selection['proof']['selectedNormalizedHit']['slotsCell'])
    reg=image.metadata_registration;need('selected-static-table-layout',
        int.from_bytes(image.pe.bytes_at_va(reg+32,4),'little')==image.registration['genericMethodTableCount']
        and image.pe.u64_at_va(reg+40)==int(image.registration['genericMethodTable'],16)
        and image.pe.u64_at_va(reg+72)==int(image.registration['methodSpecs'],16)
        and image.pe.u64_at_va(reg+24)==int(image.registration['genericInsts'],16))
    facts=[]
    for selected in selection['proof']['selectedPlaceholderRegistrations']:
        entry=selected['selectedRegistration'];spec_index=entry['methodSpecIndex'];definition=selected['methodDefinition']
        actual=struct.unpack('<iii',image.pe.bytes_at_va(int(image.registration['methodSpecs'],16)+spec_index*12,12))
        need('same-exact-placeholder-method-spec',actual==(definition,entry['classInstantiation']['index'],-1))
        row=entry['registration'];row_address=int(image.registration['genericMethodTable'],16)+row['tableIndex']*16
        raw=image.pe.bytes_at_va(row_address,16)
        need('same-current-registration-row-and-triple',raw.hex().upper()==row['rawHex']and struct.unpack('<iiii',raw)==(spec_index,*row['indices']))
        pointer=image.pe.u64_at_va(int(image.registration['genericInsts'],16)+actual[1]*8)
        need('same-actual-registered-class-instantiation-pointer',pointer==entry['classInstantiation']['record_va'])
        facts.append(dict(formatterType=selected['formatterType'],methodDefinition=definition,methodSpecIndex=spec_index,
            rawMethodSpec=actual,rawRegistrationRowHex=raw.hex().upper(),registrationRowAddress=row_address,
            actualTripleAddress=row_address+4,actualClassInstantiationPointer=pointer,actualMethodInstantiationPointer=None,
            runtimeMethodDefinitionOrConstructedKeyIdentityProved=False))
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='proved-current-source-only',nativeInputs=pins,
        proof=dict(argumentSeedSource=prior,methodSeedWindows=body['windows'],methodSeedCfg=graph,methodSeedPadding=padding,
            selectedSeedProgram=source,keyResolverWindows=resolver['windows'],keyResolverCfg=resolver_graph,
            keyResolverPadding=resolver_padding,keyResolverPrograms=keys,insertionWindows=insertion['windows'],
            insertionCfg=insert_graph,insertionPadding=insert_padding,selectedStaticMethodRows=facts),
        actualMethodRegistrationRowsAndTripleTransfersProved=True,actualColdMethodSpecClassNullMethodArgumentsProved=True,
        initializedMethodKeyTableIdentityProved=False,concreteEnumCallbackSelected=False,
        wireGrammarAdmitted=False,wholeOwnerAdmitted=False,evidenceBoundary=dict(
            exact='Complete current method-table seed/key resolver/insertion source partitions and CFGs/normal frames, selected actual row→MethodSpec→class-inst/null-method arguments→constructor/cache→pair/triple transfers and exact static placeholder rows.',
            conditional=__doc__,structuralOnly='Generic method registration rows and runtime key/pointer table.',
            unresolved=['key constructor/definition descriptor/cache semantics','method-table reservation/insertion/resize/collision population',
                'actual nominal provider/MethodInfo/callback binding','startup execution and opaque cache aliases','wire/parent/EOF']))))
