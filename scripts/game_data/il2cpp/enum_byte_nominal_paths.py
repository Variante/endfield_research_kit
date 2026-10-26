"""Finite byte-enum original-context to selected method-table source joins.

The original concrete enum and its own constructor request remain nominal.
Both class and primitive normalization use their separately proved kind5
switch arms and the independently requested System.ByteEnum cell. Canonical
argument/key tables and selected static ByteEnum rows are freshly joined.
Registry/provider/callback selection and enclosing grammar remain separate.
"""
import json

from scripts.game_data.il2cpp import enum_byte_callback_sources as byte_source
from scripts.game_data.il2cpp import enum_nominal_callback_sources as source_profile

SCHEMA='endfield.enum-byte-nominal-paths.v1'
TYPE='Beyond.Gameplay.Core.EnemyHurtShakeIntensity'
LABEL='enumByteNominalPaths'


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def _byte_publication(image,primitive):
    from scripts.game_data.il2cpp.native_cell_references import selected_qword_reference_candidates
    from scripts.game_data.il2cpp.enum_normalizer_selection_paths import publication_program
    base=image.pe.image_base;cell=primitive['placeholderCell'];choices=[]
    for candidate in selected_qword_reference_candidates(image.pe,{cell-base}):
        if candidate['kind']!='store':continue
        entry=base+candidate['siteRva']-26
        raw=image.pe.bytes_at_va(entry,33)
        try:program=publication_program([(entry,raw)],entry)
        except ValueError:continue
        if program['resultCell']!=cell:continue
        if image.pe.bytes_at_va(program['nameAddress'],9)!=b'ByteEnum\0':continue
        if image.pe.bytes_at_va(program['namespaceAddress'],7)!=b'System\0':continue
        choices.append((entry,raw,program))
    need('one-own-System-ByteEnum-publication',len(choices)==1)
    return choices[0]


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.enum_nominal_registration_paths import _select_nominal_transfers
    from scripts.game_data.il2cpp.enum_method_rgctx_paths import derive as context_source
    from scripts.game_data.il2cpp.enum_method_table_insertion_paths import derive as insertion_source
    from scripts.game_data.il2cpp import enum_method_pointer_selection as selection_owner
    from scripts.game_data.il2cpp import enum_method_table_seed_paths as seed_owner
    from scripts.game_data.il2cpp import enum_inflated_method_class_paths as original_owner
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack.pointer_param import owned
    _publication_gate(image,pins);base=image.pe.image_base
    profile=json.loads(source_profile.CONTRACT_PATH.read_bytes());source_profile.validate_profile(profile,pins)
    selected,ctor,register,ct,rt=_select_nominal_transfers(image,pins,enum_types=[TYPE])
    request=selected[TYPE]['typedUsages']['constructor'];ctx=NativeReferenceContext(image)
    need('fresh-own-byte-backed-original-enum',ctx.is_enum(TYPE)and ctx.field(TYPE+'::value__')[1:]==('byte',16))
    entries=profile['sourceEntries'];fixup=profile['fixupEntries']
    primitive_entry=base+entries['primitiveEntryRva'];body=owned(image,primitive_entry)
    primitive=byte_source.primitive_kind5_program(body['regions'],primitive_entry,image_base=base)
    publication_entry,publication_raw,publication=_byte_publication(image,primitive)
    args=dict(seed_entry=base+entries['seedEntryRva'],selection_entry=base+entries['selectionEntryRva'],
        primitive_entry=primitive_entry,enum_requests=[(TYPE,request)],enum_variant='byte',
        normalizer_entry=base+entries['normalizerEntryRva'],publication_entry=publication_entry,
        fixup_arguments=dict(loop_target=base+fixup['loopTargetRva'],record_target=base+fixup['recordTargetRva'],
            alternate_target=base+fixup['alternateTargetRva'],projection_target=base+fixup['projectionTargetRva'],
            publication_entry=base+fixup['publicationEntryRva']))
    chain=context_source(image,pins,**args);insertion=insertion_source(image,pins,**args)
    selection=source_profile._nodes(chain,selection_owner.SCHEMA)
    seed=source_profile._nodes(chain,seed_owner.SCHEMA)
    original=source_profile._nodes(chain,original_owner.SCHEMA)
    need('same-independent-Byte-method-table-seed',insertion['proof']['methodTableSeedSource']==seed)
    ctx=NativeReferenceContext(image);md=image.metadata;formatter=ctx.index.types[byte_source.FORMATTER]
    method,=[m for m in md.methods_for(formatter)if md.string(m.name_index)=='Deserialize']
    registration=GenericEntries(image).resolve(method.index,['System.ByteEnum'],[])
    selected_rows=[r for r in selection['proof']['selectedPlaceholderRegistrations']
        if r['formatterType']==byte_source.FORMATTER and r['methodDefinition']==method.index]
    need('one-exact-own-Byte-callback-row',len(selected_rows)==1
        and selected_rows[0]['selectedRegistration']==json.loads(json.dumps(registration)))
    rows=[r for r in seed['proof']['selectedStaticMethodRows']if r['methodDefinition']==method.index]
    need('same-own-Byte-static-key-triple',len(rows)==1 and rows[0]['methodSpecIndex']==registration['methodSpecIndex']
        and rows[0]['actualClassInstantiationPointer']==registration['classInstantiation']['record_va']
        and rows[0]['actualMethodInstantiationPointer']is None)
    need('same-original-Deserialize-definition-and-ABI',any(r['methodDefinition']==method.index
        and r['declaringType']==formatter.index and r['parameterCount']==2
        for r in original['proof']['intendedPlaceholderDefinitions']))
    need('actual-selected-byte-key-insertion-and-retention',insertion['actualSelectedKeyTripleInsertionAndEqualKeyRetentionProved']is True)
    _publication_gate(image,pins)
    from scripts.game_data.il2cpp.enum_constructed_class_paths import _json_set
    return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-original-byte-context-and-selected-code',nativeInputs=pins,
        typeName=TYPE,typeDefinition=ctx.index.types[TYPE].index,callbackTargetRva=registration['pointer']-base,
        proof=dict(nominalCallerSelections=selected,bytePublicationEntryRva=publication_entry-base,
            bytePublicationRawHex=publication_raw.hex(),bytePublicationProgram=publication,
            originalContextAndNormalization=chain,methodTableInsertion=insertion,selectedCallbackRegistration=registration,
            selectedStaticCallbackMethodRow=rows[0]),
        originalContextToSelectedCodeConditional=True,actualNominalRegistryAndReceiverJoinProved=False,
        actualRuntimeSelectionObserved=False,parentOrCollectionGrammarAdmitted=False,
        evidenceBoundary=dict(exact='Fresh original byte enum/constructor request, byte metadata/fixup/class/rgctx, separate kind5 normalization/name/interner and own static ByteEnum callback method-table source.',
            conditional=__doc__,structuralOnly='Original nominal context and separately selected raw-byte code.',
            unresolved=['nominal registry/provider/slot-five MethodInfo and receiver join','actual initialized runtime state/replacement','parent/EOF'])),default=_json_set))
